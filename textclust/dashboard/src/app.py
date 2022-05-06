import coordination_detection
import dash
import dash_html_components as html
import os
import dash_core_components as dcc
import uuid

from dash.long_callback import CeleryLongCallbackManager
from dash.dependencies import Input, Output
from celery import Celery

# Import components
from dashboard_components import header_component
from dashboard_components import intro_component
from dashboard_components import configuration_component
from dashboard_components import keywords_component
from dashboard_components import session_component
from dashboard_components import start_component
from dashboard_components import micro_cluster_component
from dashboard_components import snapshot_component
from dashboard_components import all_cluster_component
from dashboard_components import coordination_component


# Initialize a dash app

celery_app = Celery(
    __name__, broker="redis://redis:6379/2", backend="redis://redis:6379/3", include=["dashboard_components.coordination_component"]
)
long_callback_manager = CeleryLongCallbackManager(celery_app)

app = dash.Dash(__name__, update_title=None, url_base_pathname=os.environ.get('BASE_URL', '/'),
                long_callback_manager=long_callback_manager,
                suppress_callback_exceptions=True,external_stylesheets=[
                "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css"
])

server = app.server

# defining title of webpage register card
app.title = "textClust Dashboard"

# allowing css and local jascript
app.scripts.config.serve_locally = True
app.css.config.serve_locally = True

def serve_layout():
    session_id = str(uuid.uuid4())
    # Build layout
    layout = html.Div([
        header_component.header_layout(app),
        dcc.Store(id='survey_storage', storage_type='session',data=session_id),
        html.Div([
            html.Div([
                html.Div([
                    intro_component.intro_layout()
                ], className="introWrapper"),
                html.Div(className="sectionWrapper", children=[
                    keywords_component.keyword_layout(),
                    #session_component.session_layout(app),
                    start_component.start_layout(),
                    micro_cluster_component.micro_cluster_layout()
                ]),
                html.Div(className="sectionWrapper", children=[
                    snapshot_component.snapshot_layout()
                ]),
                html.Div(className="sectionWrapper", children=[
                    all_cluster_component.all_cluster_layout()
                ]),
                html.Div(className="sectionWrapper", children=[
                    coordination_component.coordination_layout()
                ]),
                html.Div(
                    children="0",
                    id="min_time_stamp",
                    style={"display": "none"}
                ),
                html.Div(
                    children="0",
                    id="max_time_stamp",
                    style={"display": "none"}
                ),
                html.Div(id="dummyInput", style={"display": "none"}),
            ], className="main"),
        ], className="mainWrapper"),
        html.Footer(className="footer")
    ])
    return layout

app.layout = serve_layout

# defining ip and port of backend
API_IP = "backend"
API_PORT = "5000"

# Configure callbacks
keywords_component.register_callbacks(app, API_IP, API_PORT)
#session_component.register_callback(app, API_IP, API_PORT)
start_component.register_callback(app, API_IP, API_PORT)
micro_cluster_component.register_callback(app, API_IP, API_PORT)
snapshot_component.register_callback(app, API_IP, API_PORT)
snapshot_component.data_tabs.token_tab.register_callback(app)
snapshot_component.twitter_tabs.users_tab.register_callback(app)
snapshot_component.data_tabs.assignment_tab.register_callback(app, API_IP, API_PORT)
all_cluster_component.register_callback(app, API_IP, API_PORT)
intro_component.register_callback(app, API_IP, API_PORT)
coordination_component.register_callback(app)

if __name__ == '__main__':
    # running server on port 8050 if not defined otherwise in docker-compose.yml
    app.run_server(debug=True, port=8050, host='0.0.0.0')
