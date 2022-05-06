import dash
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
import uuid
import requests
import dash_table
from helpers import session_helpers


def session_layout(app):
    return html.Div(id="sessionWrapper", children=[
        html.Div(
            children="",
            id="clusterSessionID",
            style={"display": "none"}
        ),
        html.Div(id="sessionIdCreatorWrapper", children=[
            html.Span(children="Current Session ID: "),
            dcc.Input(
                id="sessionIdCreator", debounce=True),
            html.Button(html.Img(src=app.get_asset_url(
                "./icons/clear.svg")), id="currentSessionClearer"),
            dbc.Alert(
                "Session ID already in use!",
                id="sessionIdCreatorWarning",
                is_open=False,
                dismissable=True,
                color="danger",
                style={
                    "position": "absolute",
                    "right": "0",
                    "top": "100%",
                    "width": "100%",
                    "margin-top": "5px"
                }
            ),
            dbc.Modal([
                dbc.ModalHeader("Running"),
                dbc.ModalBody(
                    "There exists a running Cluster Session with the given ID, do you want to load it?"),
                dbc.ModalFooter(
                    [dbc.Button("Close", id="closeRunningLoader"),
                     dbc.Button("Load", id="acceptRunningLoader")]
                )],
                id="modalLoadRunningSession"
            ),
        ]),
        html.Div(id="lastSessionsWrapper", children=[
            html.Span(children="Last Sessions: "),
            dcc.Dropdown(id="lastSessions",
                         optionHeight=60,
                         placeholder="Select Session"),
            html.Button(id="lastSessionsSelect", children=[
                "Last Sessions Infos"]),
            html.Button(id="pastSessionLoader", children=[html.Img(
                src=app.get_asset_url("./icons/update_graph.svg"))]),
            html.Div(id="prevSessionsInfos")
        ])
    ])


def register_callback(app, API_IP, API_PORT):

    # callback function for the storage of clustering session ids into an invisble div in the background for data fetching requests
    # TODO: Rewrite to use store for cluster session ID instead of an div
    # Done
    @app.callback(Output('clusterSessionID', 'children'),
                  [Input("sessionIdCreator", "value"),
                  Input("pastSessionLoader", "n_clicks")],
                  State('lastSessions', 'value'),
                  State("sessionIdCreator", "value"))
    def update_session_div(value, n, prev_session, current_session):
        # differiante the contexts --> loading past sessions and view static or change session id for new sessions
        ctx = dash.callback_context
        input_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # new session/session take over
        if input_id == "sessionIdCreator":
            if value is None:
                cluster_session_id = str(uuid.uuid1())
            else:
                cluster_session_id = value
        else:
            # past sessions
            if input_id == "pastSessionLoader" and n is not None:
                cluster_session_id = prev_session
            else:
                cluster_session_id = current_session
        return cluster_session_id

    # callback function for updating the clustering session id and hiding/showing start/stop buttons
    # Done
    @app.callback(Output("sessionIdCreator", "value"),
                  Output("sessionIdCreatorWarning", "is_open"),
                  Output("modalLoadRunningSession", "is_open"),
                  [Input("sessionIdCreator", "value"),
                  Input("closeRunningLoader", "n_clicks"),
                  Input("acceptRunningLoader", "n_clicks"),
                  Input("stopButton", "n_clicks"),
                  Input("startButton", "n_clicks"),
                  Input("currentSessionClearer", "n_clicks")])
    def update_session_id(value, n_close, n_accept, n_stop, n_start, n_clear):

        # differentiate contexts --> session clearer: new session id suggestion | start/stop button: showing or hiding, if session is running or stopped | if the running confirmation dialogue is accepted: showing stop button
        ctx = dash.callback_context
        input_id = ctx.triggered[0]['prop_id'].split('.')[0]

        # create new random clustering session id
        if input_id == "currentSessionClearer":
            cluster_session_id = ""
            cluster_session_id = str(uuid.uuid1())
        # hide start button and show stop button
        if input_id == "startButton":
            return dash.no_update, dash.no_update, False
        # hide stop button and show start button
        if input_id == "stopButton":
            return dash.no_update, dash.no_update, False
        # hide stop button and show start button
        if input_id == "closeRunningLoader" or input_id == "acceptRunningLoader" and (n_close is not None or n_accept is not None):
            return dash.no_update, dash.no_update, False
        # validate user given clustering session id against exiting ones against backend database of clustering sessions
        if input_id == "sessionIdCreator":
            if value is None:
                pass
            else:
                cluster_session_id = value
                # request validation
                session_meta = session_helpers.check_session_id(cluster_session_id, API_IP, API_PORT)
                # different cases of consequences --> jump into exstisting session or suggest to change id
                if session_meta["given"] and session_meta["ended"]:
                    return cluster_session_id, True, dash.no_update
                elif session_meta["given"] and not session_meta["ended"]:

                    return cluster_session_id, True, True
                else:
                    return cluster_session_id, False, dash.no_update
        # catch other cases and create new random session id
        cluster_session_id = str(uuid.uuid1())
        return cluster_session_id, dash.no_update, dash.no_update

    # callback function to load last sessions into the dropdown options for clustering session selection
    # Done
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
            if prevSession["id"] is not None and len(prevSession["id"]) > 0:
                options.append(
                    {'label': prevSession["id"], 'value': prevSession["id"]})
        return options

    # callback function to load last sessions into the regarding table of session meta information
    # TODO: Change select button so it becomes more clear, that there is a button. A checkmark is very bland
    # Done
    #@app.callback(Output("prevSessionsInfos", "children"),
    #              [Input("lastSessionsSelect", "n_clicks")],
    #              State("prevSessionsInfos", "children"), prevent_initial_call=True)
    #def fetch_last_sessions_meta(n_open, prevSessions):
    #    # fetching information from api endpoint
    #    URL = "http://{}:{}/getPrevClusterSessions".format(API_IP, API_PORT)
    #    request = requests.get(url=URL)
    #    prevSessionMeta = request.json()
    #
    #    tableDiv = html.Div(id="prevSessionsTableWrapper", children=[
    #        html.Button(id="prevCloser", children=[html.Img(
    #            src=app.get_asset_url("./icons/close.svg"))]),
    #        # dash data table with conditional rendering for running sessions --> green and conerting addionally date formats
    #        dash_table.DataTable(
    #            id='lastSessionsTable',
    #            columns=[{"name": "Session ID", "id": "id"}, {"name": "Mode", "id": "mode"}, {"name": "clustering date", "id": "clustering_date"}, {"name": "running time", "id": "running_time"}, {"name": "status", "id": "status"},
    #                     {"name": "data time beginning", "id": "data_beginning"}, {"name": "data time end", "id": "data_end"}, {"name": "data horizont", "id": "data_time_horizont"}, {"name": "texts processed", "id": "number_texts"}],
    #            style_cell={'textAlign': 'left',
    #                        'overflow': 'hidden',
    #                        'textOverflow': 'ellipsis',
    #                        "padding": "5px"},
    #            style_table={'width': "100%", "padding-top": "55px"},
    #            style_data_conditional=[
    #                {'if': {'column_id': "clustering_date"},
    #                 "whiteSpace": "no-wrap"},
    #                {'if': {'column_id': "running_time"},
    #                 "whiteSpace": "break-spaces"},
    #                {'if': {'column_id': "data_beginning"},
    #                 "whiteSpace": "no-wrap"},
    #                {'if': {'column_id': "data_end"},
    #                 "whiteSpace": "no-wrap"},
    #                {'if': {'column_id': "data_time_horizont"},
    #                 "whiteSpace": "break-spaces"},
    #                {'if': {'filter_query': '{status} = running'},
    #                 'color': 'green'}
    #            ],
    #            page_action="native",
    #            page_current=0,
    #            page_size=5,
    #            editable=True,
    #            sort_action="native",
    #            sort_mode="multi",
    #            row_selectable="single",
    #            data=prevSessionMeta
    #        ),
    #        # button for confirming to select clustering session for later view
    #        html.Button(id="prevChecker", children=[html.Img(
    #            src=app.get_asset_url("./icons/check.svg"))]),
    #    ])
    #    # returns whole Div of elements --> dynamic inserted into the layout
    #    return tableDiv

    # callback function showing and hiding the table of session information --> css adapts display style to "none" or "flex"
    # Done
    #@app.callback(Output("prevSessionsInfos", "style"),
    #              Output("lastSessions", "value"),
    #              Input("prevCloser", "n_clicks"),
    #              Input("prevChecker", "n_clicks"),
    #              State("prevSessionsInfos", "style"),
    #              State("lastSessionsTable", "selected_rows"),
    #              State("lastSessionsTable", "data"),
    #              State("lastSessions", "value"))
    #def close_last_sessions_meta(n_close, n_check, current_style, selected, data, old_session_id):
    #    # input context checker --> prev closer --> close windwow | prev checker ---> close window and update selected id vaue
    #    ctx = dash.callback_context
    #    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    #
    #    if selected is not None and button_id == "prevChecker":
    #        selected, = selected
    #        session_id = data[selected]["id"]
    #    else:
    #        session_id = old_session_id
    #
    #    # selecting the correct click context value
    #    if button_id == "prevCloser":
    #        n = n_close
    #    if button_id == "prevChecker":
    #        n = n_check
    #
    #    if n is not None and n > 0:
    #        return {"display": "none"}, session_id
    #    else:
    #        return {"display": "flex"}, session_id
