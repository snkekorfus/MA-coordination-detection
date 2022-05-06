import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import dash_table
from dash.dependencies import Input, Output, State
import base64
import requests
import json


def input_layout():
    # encoding image to avoid errors of missing files
    upload_image_filename = 'assets/icons/uploadFile.svg'
    encoded_upload_image = base64.b64encode(open(upload_image_filename, 'rb').read()).decode('utf-8')

    return dcc.Tab(label='Input', children=[
        html.Div([
            html.Div(id="inputSourceWrapper", children=[
                html.Span("Mode:"),
                dcc.Dropdown(
                    id="inputSource",
                    clearable=False,
                    placeholder="Select a mode",
                    options=[
                        {'label': 'Twitter',
                         'value': 'TWT'},
                        {'label': 'CSV',
                         'value': 'CSV'},
                    ],
                )
            ]),
            html.Div(id="inputConfig", children=[
                # Twitter input mode
                html.Div(
                    id="twtSight",
                    style={"display": "none"},
                    children=[
                        html.Div(id="termsWrapper", children=[
                            html.Span("Terms:"),
                            dcc.Input(
                                id="terms",
                                placeholder="searchwords",
                                type="text",
                                value=""
                            )
                        ]),
                        # twitter trends
                        html.Div(id="trendSelectWrapper", children=[
                            html.Div(id="trendInWrapper", children=[
                                html.Span("Trending in:"),
                                dcc.Dropdown(
                                    id='woeidSelect',
                                    options=[
                                        {'label': 'Germany',
                                         'value': 23424829},
                                        {'label': 'US',
                                         'value': 23424977},
                                        {'label': 'Austria',
                                         'value': 23424750},
                                        {'label': 'Switzerland',
                                         'value': 23424957},
                                        {'label': 'Spain',
                                         'value': 23424950},
                                        {'label': 'France',
                                         'value': 23424819},
                                        {'label': 'Italy',
                                         'value': 23424853}
                                    ],
                                    value=23424829
                                )
                            ]),
                            # loading component for fetching
                            html.Div(id="loadingTrendsWrapper", children=[
                                dcc.Loading(
                                    id="trending-loading",
                                    type="circle",
                                    children=[
                                        dash_table.DataTable(
                                            id='trendTable',
                                            columns=[
                                                {"name": "term",
                                                 "id": "termcolumn"},
                                                {"name": "current tweets",
                                                 "id": "tweetcolumn"}],
                                            style_cell={
                                                'textAlign': 'left',
                                                'overflow': 'hidden',
                                                'textOverflow': 'ellipsis'},
                                            style_table={
                                                'width': "100%", "padding-top": "10px"},
                                            page_action="native",
                                            page_current=0,
                                            page_size=5
                                        )
                                    ]
                                )
                            ])
                        ]),
                    ]
                ),

                # csv input mode
                html.Div(id="csvSight", style={"display": "none"}, children=[
                    html.Div(id="csvDropdownWrapper", children=[
                        # csv uploader
                            dcc.Upload(
                                id='csvDropdown',
                                children=[
                                    html.Img(id="csvUploadImage", src='data:image/svg+xml;base64,{}'.format(encoded_upload_image)),
                                    html.Span(
                                        'Drag and Drop file here'),
                                    html.Span(
                                        'or'),
                                    html.Button(id="csvSelectButton", children=[
                                        html.A('Browse for file')])
                                ]
                            )]),
                    html.Div(
                        id="csvUploadedFileWrapper", children=[]),
                    # csv formatting with delimeter, quotechar, newline and column structure parameters
                    html.Div(id="csvSyntaxWrapper", children=[
                        html.Div(id="delimeterWrapper", children=[
                                html.Span(
                                    "Delimeter:"),
                                dcc.Input(
                                    id="delimeterInput", placeholder=";")
                        ]),
                        html.Div(id="quotecharWrapper", children=[
                            html.Span(
                                    "Quotechar:"),
                            dcc.Input(
                                id="quotecharInput", placeholder='"' + "'")
                        ]),
                        html.Div(id="newlineWrapper", children=[
                            html.Span(
                                    "Newline:"),
                            dcc.Input(
                                id="newlineInput", placeholder=r"\n")
                        ])
                    ]),
                    # column formatting
                    html.Div(id="columnFormatWrapper", children=[
                        html.Div(id="colIdWrapper", children=[
                                html.Span(
                                    "ID column:"),
                                dcc.Input(
                                    id="colIdInput", placeholder="1")
                        ]),
                        html.Div(id="colTimeWrapper", children=[
                            html.Span(
                                    "time column:"),
                            dcc.Input(
                                id="colTimeInput", placeholder="1")
                        ]),
                        html.Div(id="colTextWrapper", children=[
                            html.Span(
                                    "text column:"),
                            dcc.Input(
                                id="colTextInput", placeholder="2")
                        ]),
                    ]),
                    # time formatter
                    html.Div(id="timeFormatWrapper", children=[
                        html.Span("time format:"),
                        dcc.Input(
                            id="timeFormatInput",
                            placeholder="%Y-%m-%d %H:%M:%S",
                            value='%Y-%m-%d %H:%M:%S'
                        )
                    ]),
                    # loading component
                    dcc.Loading(
                        id="csvTableLoading",
                        type="circle",
                        fullscreen=True,
                        style={
                            "background-color": "rgba(255,255,255, 0.3)"},
                        children=[
                            html.Div(
                                id="fileCSVUploaded")
                        ]
                    )
                ])
            ]),
        ], className="configuration")
    ])


def register_callback(app, API_IP, API_PORT):
    # Helper functions
    # function for uploading CSV file towards the backend
    def saveTempfileCSV(filename, contents, session):
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        files = {"file": decoded}

        # api endpoint request, sending file decoded in file format
        URL = "http://{}:{}/uploadCSV?session={}".format(
            API_IP, API_PORT, session)
        r = requests.post(url=URL, files=files)
        # checking status
        if r.status_code == 200:
            return True
        else:
            return False

    # callback function to show and hide the different input modes such as CSV and Twitter
    # Done
    @app.callback(
        Output("twtSight", "style"),
        Output("csvSight", "style"),
        Input("inputSource", "value"))
    def update_input(value):

        # twitter modes conditional styling of display "none"
        if value == "TWT":
            csvstyle = {"display": "none"}
            twtstyle = {}
        else:
            # csv modes conditional styling of display "none"
            if value == "CSV":
                twtstyle = {"display": "none"}
                csvstyle = {}
            else:
                csvstyle = {"display": "none"}
                twtstyle = {"display": "none"}
        return twtstyle, csvstyle

    # callback function for adding infos about the csv file, which was uploaded and giving options to delete file
    # Done
    @app.callback(
        Output("csvUploadedFileWrapper", "children"),
        Input("csvDropdown", "contents"),
        State("csvDropdown", "filename"),
        State('clusterSessionID', 'data'), prevent_initial_call=True)
    def upload_csv(contents, filename, session):

        # checking if content from dash upload componetn is not none
        if contents is not None:
            # save CSV file
            saveTempfileCSV(filename, contents, session)
            returnDiv = [html.Div(id="csvUploadedFile", children=[
                html.Img(id="descriptionImg", src=app.get_asset_url(
                    "./icons/description.svg")),
                html.Div(id="csvUploadedMeta", children=[
                    html.Span(filename),
                    html.Span(),
                    dcc.Interval(id="progress-interval",
                                 n_intervals=0, interval=100),
                    # progressbar dummy animation for uploading csv file
                    dbc.Progress(id="csvProgress", color="#090088", style={
                                 "height": "5px", "width": "100%", "margin": 0}, className="mb-3"),
                ]
                ),
                html.Button(id="deleteImg", children=[html.Img(
                    src=app.get_asset_url("./icons/delete.svg"))])
            ]),

                html.Div(id="previewCSVbuttonWrapper", children=[
                    html.Button(id="previewCSVbutton",
                                children="Preview/Test CSV Config"),
                    dbc.Alert(
                        "Please define the CVV format",
                        id="csbWarning",
                        is_open=False,
                        dismissable=True,
                        duration=3000,
                        color="danger",
                        style={"width": "100%",
                               "margin-top": "5px"},
                    )
                ])]
            return returnDiv

    # callback function for giving feedback to the user to upload another file
    # Done
    @app.callback(
        Output("csvUploadedMeta", "children"),
        Input("deleteImg", "n_clicks"),
        prevent_initial_call=True)
    def upload__another_csv(n):
        # prevent intial callback on page load and feedback for wrong files is given
        if n is not None and n > 0:
            return [html.Span("upload another file!", style={"padding": "5px"})]
        else:
            raise PreventUpdate

    # callback function to warn the user about missing csv configuration
    # Done
    @app.callback(
        Output("csbWarning", "is_open"),
        Input("previewCSVbutton", "n_clicks"),
        State("delimeterInput", "value"),
        State("quotecharInput", "value"),
        State("newlineInput", "value"),
        State("colIdInput", "value"),
        State("colTimeInput", "value"),
        State("colTextInput", "value"))
    def preview_csv(n, d, q, nw, c1, c2, c3):
        if n is not None and n > 0:
            if all((value is not None and value != "") for value in [d, q, nw, c1, c2, c3]):
                pass
            else:
                return True

    # callback function for showing progess bar
    # TODO: this is fake, here is nothing calcualted based on the progress of the upload; look at dash-uploader
    # Done
    @app.callback(
        Output("csvProgress", "value"),
        [Input("progress-interval", "n_intervals")])
    def upload_csv_progress(n):
        return n * 10

    # callback function for requesting trending twitter topics and displaying them in the table of the twitter input mode configuration
    # Done
    @ app.callback(Output('trendTable', 'data'),
                   Input("woeidSelect", "value"))
    def update_trends(woeid):
        n = 8
        URL = "http://{}:{}/getTwitterTrendsByLocation?woeid={}&n={}".format(
            API_IP, API_PORT, woeid, n)
        r = requests.get(url=URL)
        trend_dict = json.loads(r.json())
        return trend_dict
