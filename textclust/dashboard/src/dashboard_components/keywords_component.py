from requests.api import options
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
import requests
import dash_table
import dash


def keyword_layout():
    return html.Div(children=[
        dcc.Store(id="clusterSessionID", data=None),
        #html.Span(children="Twitter Stream:", style={"font-weight": "bold"}),
        dcc.Dropdown(id="clusteredKeywords", optionHeight=100, style={"margin-bottom":"10px", "width": "300px"}, placeholder="Wählen Sie einen Twitter Stream..."),
        html.Div(id="lastSessionsWrapper", children=[
            html.Span(children="Last Sessions: "),
            dcc.Dropdown(id="lastSessions",
                         optionHeight=60,
                         placeholder="Select Session"),
            html.Button(id="lastSessionsSelect", children=[
                "Last Sessions Infos"]),
            html.Button(id="pastSessionLoader"),
            html.Div(id="prevSessionsInfos")
        ])
    ], style={"display": "flex"})


def register_callbacks(app, API_IP, API_PORT):
    # callback function to load last sessions into the dropdown options for clustering session selection
    @app.callback(Output("clusteredKeywords", "options"),
                  [Input("dummyInput", "n_clicks")])
    def fetch_running_sessions(n):
        # api request for requesting clustering session information
        URL = "http://{}:{}/getPrevClusterSessions".format(API_IP, API_PORT)
        r = requests.get(url=URL)
        prevSessionMeta = r.json()
        options = []
        for session in prevSessionMeta:
            if session['status'] == 'running':
                options.append({'label': session['terms'], 'value': session['id']})
        return options

    @app.callback(Output("lastSessions", "options"),
                  [Input("dummyInput", "n_clicks")])
    def fetch_last_sessions(n):

        # api request for requesting clustering session information
        URL = "http://{}:{}/getPrevClusterSessions".format(API_IP, API_PORT)
        r = requests.get(url=URL)
        prevSessionMeta = r.json()
        options = []

        # structuring information in list of dict for options of session ids to select
        for prevSession in prevSessionMeta:
            if prevSession['status'] == 'finished':
                options.append({'label': prevSession["id"], 'value': prevSession["id"]})
        return options

    @app.callback(Output("clusterSessionID", "data"),
                  [Input("clusteredKeywords", "value")])
    def set_clusterSessionId(session):
        return session


    # callback function to load last sessions into the regarding table of session meta information
    # TODO: Change select button so it becomes more clear, that there is a button. A checkmark is very bland
    # Done
    @app.callback(Output("prevSessionsInfos", "children"),
                  [Input("lastSessionsSelect", "n_clicks")],
                  State("prevSessionsInfos", "children"), prevent_initial_call=True)
    def fetch_last_sessions_meta(n_open, prevSessions):
        # fetching information from api endpoint
        URL = "http://{}:{}/getPrevClusterSessions".format(API_IP, API_PORT)
        request = requests.get(url=URL)
        prevSessionMeta = request.json()

        tableDiv = html.Div(id="prevSessionsTableWrapper", children=[
            html.Button(id="prevCloser", children=[html.Img(
                src=app.get_asset_url("./icons/close.svg"))]),
            # dash data table with conditional rendering for running sessions --> green and conerting addionally date formats
            dash_table.DataTable(
                id='lastSessionsTable',
                columns=[{"name": "Session ID", "id": "id"}, {"name": "Mode", "id": "mode"}, {"name": "clustering date", "id": "clustering_date"}, {"name": "running time", "id": "running_time"}, {"name": "status", "id": "status"},
                         {"name": "data time beginning", "id": "data_beginning"}, {"name": "data time end", "id": "data_end"}, {"name": "data horizont", "id": "data_time_horizont"}, {"name": "texts processed", "id": "number_texts"}],
                style_cell={'textAlign': 'left',
                            'overflow': 'hidden',
                            'textOverflow': 'ellipsis',
                            "padding": "5px"},
                style_table={'width': "100%", "padding-top": "55px"},
                style_data_conditional=[
                    {'if': {'column_id': "clustering_date"},
                     "whiteSpace": "no-wrap"},
                    {'if': {'column_id': "running_time"},
                     "whiteSpace": "break-spaces"},
                    {'if': {'column_id': "data_beginning"},
                     "whiteSpace": "no-wrap"},
                    {'if': {'column_id': "data_end"},
                     "whiteSpace": "no-wrap"},
                    {'if': {'column_id': "data_time_horizont"},
                     "whiteSpace": "break-spaces"},
                    {'if': {'filter_query': '{status} = running'},
                     'color': 'green'}
                ],
                page_action="native",
                page_current=0,
                page_size=5,
                editable=True,
                sort_action="native",
                sort_mode="multi",
                row_selectable="single",
                data=prevSessionMeta
            ),
            # button for confirming to select clustering session for later view
            html.Button(id="prevChecker", children=[html.Img(
                src=app.get_asset_url("./icons/check.svg"))]),
        ])
        # returns whole Div of elements --> dynamic inserted into the layout
        return tableDiv

    # callback function showing and hiding the table of session information --> css adapts display style to "none" or "flex"
    # Done
    @app.callback(Output("prevSessionsInfos", "style"),
                  Output("lastSessions", "value"),
                  Input("prevCloser", "n_clicks"),
                  Input("prevChecker", "n_clicks"),
                  State("prevSessionsInfos", "style"),
                  State("lastSessionsTable", "selected_rows"),
                  State("lastSessionsTable", "data"),
                  State("lastSessions", "value"))
    def close_last_sessions_meta(n_close, n_check, current_style, selected, data, old_session_id):
        # input context checker --> prev closer --> close windwow | prev checker ---> close window and update selected id vaue
        ctx = dash.callback_context
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if selected is not None and button_id == "prevChecker":
            selected, = selected
            session_id = data[selected]["id"]
        else:
            session_id = old_session_id

        # selecting the correct click context value
        if button_id == "prevCloser":
            n = n_close
        if button_id == "prevChecker":
            n = n_check

        if n is not None and n > 0:
            return {"display": "none"}, session_id
        else:
            return {"display": "flex"}, session_id

    # callback function for the storage of clustering session ids into an invisble div in the background for data fetching requests
    # TODO: Rewrite to use store for cluster session ID instead of an div
    # Done
    @app.callback(Output("clusteredKeywords", "value"),
                  [Input("pastSessionLoader", "n_clicks")],
                  State('lastSessions', 'value'))
    def update_session_div(n, prev_session):
        # differiante the contexts --> loading past sessions and view static or change session id for new sessions
        return prev_session