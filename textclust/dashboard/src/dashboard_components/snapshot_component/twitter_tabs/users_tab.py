import dash_core_components as dcc
from dash.dependencies import Input, Output
import dash_table


def users_tab_layout():
    return dcc.Tab(label="Users", children=[
        dash_table.DataTable(
            id='usersTable',
            columns=[
                {
                    "name": "username",
                    "id": "username",
                    "presentation": "markdown"
                },
                {
                    "name": "status in mc",
                    "id": "statuses_in_cluster"
                },
                {
                    "name": "statuses",
                    "id": "statuses"
                },
                {
                    "name": "verified",
                    "id": "verified"
                },
                {
                    "name": "def. image",
                    "id": "default_image"
                },
                {
                    "name": "friends",
                    "id": "friends"
                },
                {
                    "name": "followers",
                    "id": "followers"
                },
                {
                    "name": "liked",
                    "id": "liked"
                },
                {
                    "name": "def. profile",
                    "id": "default_profile"
                }
            ],
            style_cell={'textAlign': 'left',
                        'overflow': 'hidden',
                        'textOverflow': 'ellipsis',
                        'whiteSpace': 'normal'},
            style_table={'width': "100%"},
            style_header={
                "width": "150px",
                "color": "black"
            },
            page_action="native",
            page_current=0,
            page_size=10,
            sort_action="native",
            filter_action="native"
        )
    ])


def register_callback(app):
    # callback functions to reset usersTable's pages if fitler query is applied or new data is coming in
    # otherwise, if users watch a table page, which new fetcehs metrics does not reach -> display bug
    # no content, pages must be reset to 0 ( on display page 1)
    # Done
    @app.callback(Output('usersTable', 'page_current'),
                  [Input('usersTable', 'filter_query'),
                   Input('usersTable', 'data')])
    def reset_to_page_0_users(filter_query, data_input):
        return 0
