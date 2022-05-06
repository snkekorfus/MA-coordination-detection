import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
import dash_daq as daq
import base64
import json
from urllib.parse import quote


def textClustSetting_layout():
    return dcc.Tab(label='textClust', children=[
        # uplaoding config json
        html.Div(className="dropdownWrapper", children=[
            html.P("Configuration file:"),
            dcc.Upload(
                id='dropdownJson',
                children=html.Div([
                    'Drag and Drop or ',
                    html.A('Select Config.json'),
                    html.Div(id="fileUploaded")
                ])
            )
        ]),
        # various config parameter in different kind of components such as sliders, inputs, dropdowns...
        html.Div(id="clustConfigContainer", children=[
            # left side
            html.Div(id="leftSideClustConfig", children=[
                "Radius:",
                dcc.Input(
                    id="radiusInput",
                    debounce=True,
                    type="number",
                    placeholder="0.5",
                    value=0.5,
                    min=0,
                    max=1,
                    step=0.01
                ),
                dcc.Slider(
                    id='radiusSlider',
                    min=0,
                    max=1,
                    step=0.01,
                    value=0.5,
                    marks={
                        0: '0',
                        0.5: '0.5',
                        1: '1'
                    }
                ),
                "Fading factor:",
                dcc.Input(
                    id="fadingFactorInput",
                    debounce=True,
                    type="number",
                    placeholder=0.0005,
                    value=0.0005,
                    min=0,
                    max=0.1,
                    step=0.0001
                ),
                dcc.Slider(
                    id='fadingFactorSlider',
                    min=0,
                    max=0.1,
                    step=0.0001,
                    value=0.0005,
                    marks={
                        0: '0',
                        0.05: '0.005',
                        0.1: '0.1'
                    },
                ),
                "Time gap:",
                dcc.Input(
                    id="timeInput",
                    type="number",
                    value=100,
                    min=0,
                    step=5
                ),
                html.P("Micro-cluster distance metric:"),
                dcc.Dropdown(
                    id="microMetric",
                    options=[
                        {'label': 'Cosine',
                         'value': 'tfidf_cosine_distance'}
                    ],
                    value="tfidf_cosine_distance",
                    placeholder="Select a metric",
                )
            ]),

            # right side
            html.Div(id="rightSideClustConfig", children=[
                "Model:",
                dcc.Input(
                    id="modelInput",
                    type="text",
                    placeholder="searchwords",
                    value=None
                ),
                html.Div(id="clustSwitchWrapper", children=[
                    # boolean switches
                    daq.BooleanSwitch(
                        className="preSwitchClust",
                        id="verboseInput",
                        on=False,
                        label="verbose",
                        labelPosition="bottom",
                        color="#090088"
                    ),
                    daq.BooleanSwitch(
                        className="preSwitchClust",
                        id="termfadingInput",
                        on=False,
                        label="termfading",
                        labelPosition="bottom",
                        color="#090088"
                    ),
                    daq.BooleanSwitch(
                        className="preSwitchClust",
                        id="realtimeInput",
                        on=True,
                        label="realtime",
                        labelPosition="bottom",
                        color="#090088"
                    ),
                    daq.BooleanSwitch(
                        className="preSwitchClust",
                        id="autoRadiusInput",
                        on=False,
                        label="auto radius",
                        labelPosition="bottom",
                        color="#090088"
                    ),
                    daq.BooleanSwitch(
                        className="preSwitchClust",
                        id="autoMergeInput",
                        on=True,
                        label="auto merge",
                        labelPosition="bottom",
                        color="#090088"
                    )
                ]),

                # macro config for future implementations
                html.Details(id="macroClusterConfig", children=[
                    html.Summary("Macro Recluster Config"),
                    "Macro-cluster distance metric:",
                    dcc.Dropdown(
                        id="macroMetric",
                        value="tfidf_cosine_distance",
                        placeholder="Select a metric",
                        options=[
                            {'label': 'Cosine',
                             'value': 'tfidf_cosine_distance'},
                        ]
                    ),
                    "Macro Numbers:",
                    dcc.Input(
                        id="macroNumInput",
                        type="number",
                        value=3,
                        min=0,
                        step=1
                    ),
                    html.P("Minimum Micro Cluster Weight:"),
                    dcc.Input(
                        id="microWeightInput",
                        type="number",
                        value=0,
                        min=0,
                        step=1
                    ),
                    daq.BooleanSwitch(
                        id="idfInput",
                        className="preSwitchClust",
                        on=True,
                        label="idf",
                        labelPosition="bottom",
                        color="#090088"
                    ),
                ]),

                # download button for current config
                html.A(
                    'Download Configuration',
                    id='downloadLink',
                    download="textclust.json",
                    href="",
                    target="_blank"
                )
            ])
        ])
    ])


def register_callback(app):
    # callback for the manual drop of a textclust object configuration file, all parameters are set to the file values
    # TODO: outsource fading and radius into own callback functions
    # Done
    @app.callback(
        Output('fadingFactorInput', 'value'),
        Output('termfadingInput', 'on'),
        Output('timeInput', 'value'),
        Output('radiusInput', 'value'),
        Output('realtimeInput', 'on'),
        Output('microMetric', 'value'),
        Output('macroMetric', 'value'),
        Output('modelInput', 'value'),
        Output('idfInput', 'on'),
        Output('macroNumInput', 'value'),
        Output('microWeightInput', 'value'),
        Output('autoRadiusInput', 'on'),
        Output('autoMergeInput', 'on'),
        Input("dropdownJson", "filename"),
        Input("dropdownJson", "contents"),
        Input('radiusSlider', 'value'),
        Input('fadingFactorSlider', 'value'))
    def update_clust_config(filename, contents, radius, fading):

        # differentiate the contexts of uploading a config json or updating configuration slides to their parallel input values (circular dependency)
        ctx = dash.callback_context
        input_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # updating all clust related configuration settings towards this json file
        if input_id == "dropdownJson":
            if contents is not None:

                # decoding content of dropped/uploaded json file
                content_type, content_string = contents.split(',')
                decoded = base64.b64decode(content_string).decode("UTF-8")
                configDict = json.loads(decoded.replace("\n", ""))

                radius = configDict["radius"]
                fadingFactor = configDict["lambda"]
                termfading = configDict["termfading"]
                time = configDict["tgap"]
                realtime = configDict["realtimefading"]
                micro = configDict["micro_distance"]
                macro = configDict["macro_distance"]
                model = configDict["model"]
                idf = configDict["idf"]
                macroNum = configDict["num_macro"]
                microWeight = configDict["minWeight"]
                autoRadius = configDict["auto_r"]
                autoMerge = configDict["auto_merge"]

                return fadingFactor, termfading, time, radius, realtime, micro, macro, model, idf, macroNum, microWeight, autoRadius, autoMerge

        radiusOutput = dash.no_update
        fadingOutput = dash.no_update
        # updating radius value to its slider value
        if input_id == "radiusSlider":
            radiusOutput = radius
        # updating fading factor value to fading factor slider value
        if input_id == "fadingFactorSlider":
            fadingOutput = fading
        return fadingOutput, dash.no_update, dash.no_update, radiusOutput, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # simple callback for matching radius and radius slider
    # Done
    @app.callback(
        Output('radiusSlider', 'value'),
        Input('radiusInput', 'value'))
    def display_radius_slider(value):
        return value

    # simple callback for matching fading factor and  fading factor slider
    # TODO: Fix circular dependency
    # Done
    @app.callback(
        Output('fadingFactorSlider', 'value'),
        Input('fadingFactorInput', 'value'))
    def display_fading_slider(value):
        return value

    # callback function to converting all current clust configuration setting to an encoded string, which results in a textclust.json, if the download config button is pressed
    # TODO: find better solution than storing the json in the link
    # Done
    @ app.callback(
        Output('downloadLink', 'href'),
        Input('fadingFactorInput', 'value'),
        Input('termfadingInput', 'on'),
        Input('timeInput', 'value'),
        Input('radiusInput', 'value'),
        Input('realtimeInput', 'on'),
        Input('microMetric', 'value'),
        Input('macroMetric', 'value'),
        Input('modelInput', 'value'),
        Input('idfInput', 'on'),
        Input('macroNumInput', 'value'),
        Input('microWeightInput', 'value'),
        Input('autoRadiusInput', 'on'),
        Input('autoMergeInput', 'on'))
    def create_config(fadingFactor, termFading, timeGap, radius, realtimefading, microDistance, macroDistance, model, idf, macroNum, microWeight, autoRadius, autoMerge):
        config_template_string = '{{\n"lambda":{},\n"termfading":{},\n"tgap":{},\n"radius":{},\n"realtimefading":{},\n"micro_distance":"{}",\n"macro_distance":"{}",\n"model":null,\n"idf": {},\n"num_macro":{},\n"minWeight": {},\n"auto_r": {},\n"auto_merge": {}\n}}'
        # formatting string
        config_string = config_template_string.format(fadingFactor, str(termFading).lower(), timeGap, radius, str(
            realtimefading).lower(), microDistance, macroDistance, str(idf).lower(), macroNum, microWeight, str(autoRadius).lower(), str(autoMerge).lower())
        # encode to a charset data format
        config_href_string = "data:text/csv;charset=utf-8," + \
            quote(config_string)
        return config_href_string
