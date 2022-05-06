from audioop import reverse
import dash_core_components as dcc
import dash_table
from dash.dependencies import Input, Output, State
import os
import requests


def assignment_tab_layout():
    return dcc.Tab(label='Assignment', children=[
        dash_table.DataTable(
            id='textTable',
            columns=[
                {
                    "name": "Profilbild",
                    "id": "profilePicture",
                    "presentation": "markdown"
                },
                {
                    "name": "Inhalt",
                    "id": "text",
                    "presentation": "markdown"
                },
                {
                    "name": "Zeitstempel",
                    "id": "time"
                }
            ],
            style_cell={
                'textAlign': 'left',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'whiteSpace': 'normal',
            },
            style_table={'maxWidth': "100%",
                         "table-layout": "fiexed"},
            style_header={
                "color": "black"
            },
            style_cell_conditional=[
                {'if': {'column_id': "text_id"},
                    'width': '90px'},
                {'if': {'column_id': "time"}, 'width': '120px'}
            ],
            page_action="custom",
            page_current=0,
            page_count=0,
            page_size=8,
            sort_action="custom",
            filter_action="custom"
        )
    ])


def register_callback(app, API_IP, API_PORT):
    @app.callback(
        Output('textStore', 'data'),
        [Input("textTable", "page_current"),
         Input("textTable", "page_count")],
        [State('clusterSessionID', 'data'),
         State("selectedClusterTime", 'value'),
         State("textIdList", "data")],
        prevent_initial_call=True
    )
    def set_text_table(page_current, page_count, session_id, selected_cluster_time, text_id_list):
        api_password = "J2be9jPrnJSmEScF" if 'private_dashboard' in os.environ and os.environ['private_dashboard'] == "True" else ""
        if 'private_dashboard' in os.environ and os.environ['private_dashboard'] == "True" and text_id_list is not None:
            #text_id_list.sort(reverse=True)
            #start = 8 * page_current
            #end = 8 + start
            URL = "http://{}:{}/getTextData?session={}&timestamp={}&pw={}&page_current={}".format(
            API_IP, API_PORT, session_id, selected_cluster_time, api_password, page_current)
            r = requests.get(url=URL, json={"text_id_list": text_id_list})
            mc_data = r.json()
            return mc_data['text_data']
        return None
