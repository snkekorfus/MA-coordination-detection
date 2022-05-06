import dash
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import requests
from datetime import datetime
import time
import json
from helpers import session_helpers


def start_layout():
    return html.Div([
        html.Div(id="timerHHMMSS", children=[
            "Stream läuft seit: ",
            html.Span(id="HH"),
            ":",
            html.Span(id="MM"),
            ":",
            html.Span(id="SS")
        ]),
        dcc.Interval(
            id='running-timer',
            interval=5000,
            n_intervals=0,
            disabled=True
        )
    ])


def register_callback(app, API_IP, API_PORT):

    # Callback to show the running time of a cluster run
    # Done
    @app.callback(
        Output('HH', 'children'),
        Output('MM', 'children'),
        Output('SS', 'children'),
        Input('running-timer', 'n_intervals'),
        Input('running-timer', 'disabled'))
    def display_time(value, disabled):
        if disabled:
            return str(0).zfill(2), str(0).zfill(2), str(0).zfill(2)
        else:
            # div-modulus logic to convert total seconds to HH:MM:SS format
            minutes, seconds = divmod(value, 60)
            hours, minutes = divmod(minutes, 60)
            return str(hours).zfill(2), str(minutes).zfill(2), str(seconds).zfill(2)

    # callback function for starting/stoping a new textclust clustering session, more complicated, lots of Input/Output/States and thereby contexts
    # Done
    @app.callback(
        Output('running-timer', 'disabled'),
        Output('running-timer', 'n_intervals'),
        [Input('clusterSessionID', 'data')], prevent_initial_call=True)
    def start__stop_clustering(session):
        if session==None:
            return True, 0
        session_meta = session_helpers.check_session_id(session, API_IP, API_PORT)
        print(session_meta, flush=True)
        current_time = datetime.now()

        running_time = current_time - \
            datetime.fromtimestamp(session_meta["start_date"])
        running_time = int(running_time.total_seconds())
        if session_meta["ended"] == False:
            return False, running_time
        return True, running_time
