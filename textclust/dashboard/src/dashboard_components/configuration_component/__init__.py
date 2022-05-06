import dash_html_components as html
import dash_core_components as dcc

# Import subcomponents for the configuration tabs
from . import textClustSettings
from . import preprocessingSettings
from . import inputSettings


def configuration_layout():
    return html.Div(id="configTabsWrapper", children=[
        dcc.Tabs(id="configTabs", children=[
            textClustSettings.textClustSetting_layout(),
            preprocessingSettings.preprocessing_layout(),
            inputSettings.input_layout()
        ])
    ])
