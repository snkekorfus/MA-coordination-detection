import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_daq as daq
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_table
import plotly.express as px
import requests
import numpy as np


def all_cluster_layout():
    # init weight distribution boxplot with styling
    weight_boxplot_init = px.box(
        x=[], labels={'x': 'Gewicht'}, color_discrete_sequence=["#090088"])
    weight_boxplot_init.update_layout({
        "plot_bgcolor": "rgb(250,250, 250)",
        "height": 120,
        "margin": dict(
            l=0,
            r=0,
            b=0,
            t=0
        )})

    # global microcluster data
    return html.Div([
        dbc.Button(
            [html.Div("Gesamtübersicht der Cluster / Themen",style={"display": "inline-block", "margin-right":"5px"}), html.Div(className="fa fa-lg fa-angle-up")],
            id="all-cluster-collapse-button",
            className="mb-3",
            n_clicks=0,
            style ={"color":"white",'background-color': '#182637'}
        ),
        dbc.Collapse(
        html.Div(id="clusterMacroData", children=[
            # number of microclusters for a given timstamp
            html.Div(className="dataMetric", children=[
                html.Div(className="metricHeader", children=[
                    html.H6("Anzahl Cluster")
                ]),
                html.Div(className="metricBody metricNumber", id="clusterNumber", children=[0])
            ]),
            # weight distributio as a boxplot
            dcc.Graph(id="weightBoxPlot", figure=weight_boxplot_init,  config={"displayModeBar":False,"staticPlot":True}),
            # table of all tokens of all microclusters of a timestamp, each row is related to a single microcluster snapshot
            html.Div(id="clusterTableMacro", className="dataTable", children=[
                # config for view --> max tokens, max amount of microclusters
                html.Div(id="maxTokensWrapper", children=[
                    html.Div(id="tableClusterRangeWrapper", children=[
                        html.Span("max. Anzahl angezeigter Cluster: "),
                        dcc.Input(
                            id="tableClusterRange",
                            type="number",
                            value=10,
                            min=1,
                            max=100,
                            step=1,
                        )],
                        style={"margin-right": "30px"}
                    ),
                    html.Div(id="tableTokenRangeWrapper", children=[
                        html.Span("Schlagwörter:"),
                        dcc.Slider(
                            id='maxTokensSlider',
                            min=0,
                            max=20,
                            step=1,
                            value=10,
                            marks={
                                0: {'label': '0', },
                                10: {'label': '10'},
                                20: {'label': '20'}
                            },
                        )],
                        style={"margin-right": "30px", "width" : "250px"}
                    ),
                    daq.BooleanSwitch(
                        id="allTokenSwitch",
                        on=False,
                        label="Alle Schlagwörter (pro Cluster)",
                        labelPosition="top",
                        color="#090088"
                    )
                ]),
                # actual table with the information of all microclusters as described above
                dash_table.DataTable(
                    id='termTopTable',
                    columns=[
                        {
                            "name": "Cluster ID",
                            "id": "idcolumn"
                        },
                        {
                            "name": "Gewicht",
                            "id": "weightcolumn"
                        },
                        {
                            "name": "Schlagwörter",
                            "id": "termcolumn"
                        }
                    ],
                    style_cell={
                        'textAlign': 'left',
                        'overflow': 'hidden',
                        'textOverflow': 'ellipsis',
                        'whiteSpace': 'normal',
                    },
                    style_table={
                        'maxWidth': "100%",
                        "table-layout": "fiexed"
                    },
                    style_header={
                        "color": "black"
                    },
                    style_cell_conditional=[
                        {'if': {'column_id': "idcolumn"}, 'width': '90px'},
                        {'if': {'column_id': "weightcolumn"}, 'width': '90px'}
                    ],
                    page_action="native",
                    page_current=0,
                    page_size=12,
                    sort_action="native",
                    filter_action="native",
                )
            ]),
        ]),
        id="all-cluster-collapse",
        is_open=False
        )
    ])


def register_callback(app, API_IP, API_PORT):


    @app.callback(
        Output("all-cluster-collapse", "is_open"),
        Output("all-cluster-collapse-button", "children"),
        [Input("all-cluster-collapse-button", "n_clicks")],
        [State("all-cluster-collapse", "is_open"),
        State("all-cluster-collapse-button", "children")],
    )
    def toggle_collapse(n, is_open, children):
        if n:
            if is_open:
                return not is_open, [html.Div("Gesamtübersicht der Cluster / Themen",style={"display": "inline-block", "margin-right":"5px"}), html.Div(className="fa fa-lg fa-angle-up")]
            else:
                return not is_open, [html.Div("Gesamtübersicht der Cluster / Themen",style={"display": "inline-block", "margin-right":"5px"}), html.Div(className="fa fa-lg fa-angle-down")]
        return is_open, children



    # callback functions to reset termTopTable's pages if fitler query is applied or new data is coming in
    # otherwise, if users watch a table page, which new fetcehs metrics does not reach -> display bug
    # no content, pages must be reset to 0 ( on display page 1)
    @app.callback(Output('termTopTable', 'page_current'),
                  [Input('termTopTable', 'filter_query'),
                   Input('termTopTable', 'data')])
    def reset_to_page_0_terms_multi(filter_query, data_input):
        return 0

    # callback function for displaying the current micro-cluster number of a timestamp and their term frequencies and weight distribution
    @ app.callback(Output('clusterNumber', 'children'),
                   Output('termTopTable', 'data'),
                   Output('weightBoxPlot', 'figure'),
                   [Input("selectedClusterTime", 'value'),
                   Input('maxTokensSlider', 'value'),
                   Input('allTokenSwitch', 'on'),
                   Input('tableClusterRange', 'value'),
                   Input('clusterSessionID', 'data')], prevent_initial_call=True)
    def display_cluster_number(selected_cluster_time, n_tokens, all, max_shown, session_id):
        # avoiding empty input
        if session_id is None:
            weight_boxplot_init = px.box(x=[], labels={'x': 'weight'}, color_discrete_sequence=["#090088"])
            weight_boxplot_init.update_layout({
                "plot_bgcolor": "rgb(250,250, 250)",
                "height": 120,
                "margin": dict(
                    l=0,
                    r=0,
                    b=0,
                    t=0
                )})

            return 0, [], weight_boxplot_init
        if selected_cluster_time is None:
            raise PreventUpdate
        selected_cluster_time = np.datetime64(selected_cluster_time) - np.timedelta64(0, 'h')
        # fetching global microcluster data from the backend --> number and weight
        URL = "http://{}:{}//getGlobalClusterData?session={}&timestamp={}".format(
            API_IP, API_PORT, session_id, selected_cluster_time)
        r1 = requests.get(url=URL)
        data = r1.json()
        # number of microclusters
        clusterNumber = data["cluster_number"]
        weights = data["cluster_weights"]
        # boxplot of weights
        weight_distribution = px.box(
            x=weights, labels={'x': 'Gewicht'}, color_discrete_sequence=["#090088"])
        weight_distribution.update_layout({
            "plot_bgcolor": "rgb(250,250, 250)",
            "height": 120,
            "margin": dict(
                l=0,
                r=0,
                b=0,
                t=0
            )
        })

        # setting high number if all microclusters should be seen in the table
        if all:
            n_tokens = 999999999999999
        # fetching global microcluster data from the backend --> term frequencies
        URL = "http://{}:{}//getTopClusterData?session={}&timestamp={}&max={}&n_tokens={}".format(
            API_IP, API_PORT, session_id, selected_cluster_time, max_shown, n_tokens)
        r2 = requests.get(url=URL)
        mc_data = r2.json()

        # iterate over the microclusters and structure their termfrequencies into a list of dict for the table
        for mc in mc_data:
            string = ", ".join(
                [("{} ({})".format(term["token"], term["weight"])) for term in mc["termcolumn"]])
            mc["termcolumn"] = string

        clusterNumber = data["cluster_number"]
        return clusterNumber, mc_data, weight_distribution
