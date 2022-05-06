import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_daq as daq
from dash import dcc
import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_table
from coordination_detection import pipeline

import plotly.graph_objects as go
from community import community_louvain
import networkx as nx
import pandas as pd

import os


def coordination_layout():
    data_init = []
    figureInit = go.Figure(dict(data=data_init)) \
        .update_layout(
            height=500,
            plot_bgcolor="rgb(255,255, 255)",
            title="Koordination der Nutzer"

    )

    figureInit.update_xaxes(fixedrange=False)

    return html.Div([
        html.P(id='placeholder', style={"display":"none"}),
        dbc.Row([
            dbc.Col(
                html.Div([
                    html.Label("Mode of data fetching:"),
                    daq.ToggleSwitch(
                        id="methodType",
                        label='Method: Own data',
                        labelPosition='bottom',
                        value=False,
                        style={"margin-left": "-60px"}
                    )
                ]),
                width=2
            ),
            dbc.Col(
                html.Button('Start coordination calculation', id='startCoordination', n_clicks=0),
                width=2
            )
        ], justify="start"),
        dcc.Loading(
            id="loading-coordination",
            children=[
                html.Div(
                    dbc.Row([
                        dbc.Col(
                            dcc.Graph(
                                id='coordination-graph',
                                figure=figureInit
                            ),
                            width=9
                        ),
                        dbc.Col(
                            html.Div([
                                dbc.Row(dbc.Col(html.H4("Filters"))),
                                dbc.Row([
                                    dbc.Col(
                                        html.Div([
                                            html.Label("Level of coordination"),
                                            dcc.Slider(min=60, max=100, value=60,  marks={60: {'label': '60%'}, 100: {'label': '100%'}}, tooltip={"placement": "bottom", "always_visible": True}, id='coordination-level-filter'),
                                            html.Br(),
                                            html.Label("Edge types"),
                                            dcc.RadioItems(options=["All", "Content", "Temporal"], value='All', id='edge-types-filter')
                                        ])   
                                    )
                                ]),
                            ]),
                            width=3
                        )
                    ])
                ),
                dcc.Store(id="similarity-table")
                ],
            type="circle",
        ),
        dbc.Row([
            dash_table.DataTable(
                id="coordination-level-table",
                columns=[
                    {
                        "name": "User 1",
                        "id": "User1"
                    },
                    {
                        "name": "User 2",
                        "id": "User2"
                    },
                    {
                        "name": "Weight",
                        "id": "Weight"
                    },
                    {
                        "name": "Method",
                        "id": "Method"
                    }
                ],
                page_action="native",
                page_current=0,
                page_size=10,
                sort_action="native",
                filter_action="native"
            )
        ])
    ])


def register_callback(app):
    @app.callback(
        Output('coordination-graph', 'figure'),
        Output('coordination-level-table', 'data'),
        Input('similarity-table', 'data'),
        Input('coordination-level-filter', 'value'),
        Input('edge-types-filter', 'value'),
        prevent_initial_call=True
    )
    def filter_edge_weights(similarities, coordination_level, edge_type):
        if similarities is None or similarities == []:
            raise PreventUpdate

        similarities = pd.DataFrame.from_records(similarities)
        # Filter low weighted edges
        similarities = similarities[similarities["Weight"] > round((coordination_level/100), 3)]
        if edge_type != 'All':
            similarities = similarities[similarities["Method"] == edge_type]

        print("Loaded dataframe", flush=True)

        G = nx.from_pandas_edgelist(similarities, "User1", "User2", edge_attr=["Weight", "Method"], create_using=nx.MultiGraph())

        pos = nx.spring_layout(G)
        partition = community_louvain.best_partition(G, weight="Weight")

        edge_x = []
        edge_y = []
        middle_node_edge_x = []
        middle_node_edge_y = []
        edge_text = []
        edge_users = []
        for edge in G.edges(data=True):
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_text.append(f"{edge[0]} - {edge[1]} \n Weight: {edge[2]['Weight']} \n Type: {edge[2]['Method']}")
            edge_users.append([edge[0], edge[1]])
            edge_x.append(x0)
            edge_x.append(x1)
            edge_x.append(None)
            edge_y.append(y0)
            edge_y.append(y1)
            edge_y.append(None)
            middle_node_edge_x.append((x0+x1)/2)
            middle_node_edge_y.append((y0+y1)/2)

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines')

        middle_node_trace = go.Scatter(
            x=middle_node_edge_x,
            y=middle_node_edge_y,
            customdata=edge_users,
            text=edge_text,
            mode='markers',
            hoverinfo='text',
            marker=go.Marker(
                opacity=0
            )
        )


        node_x = []
        node_y = []
        node_text = []
        node_names = []
        for node in G.nodes():
            node_text.append(node)
            node_names.append([node])
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            text=node_text,
            customdata=node_names,
            hoverinfo='text',
            marker=dict(
                showscale=False,
                colorscale='Viridis',
                reversescale=True,
                color=list(partition.values()),
                size=10,
                line_width=2)
            )

        fig = go.Figure(data=[edge_trace, node_trace, middle_node_trace],
                    layout=go.Layout(
                        title="Coordination of the users",
                        titlefont_size=16,
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        width=700
                    )
                )

        print("Finished building the figure", flush=True)
        return fig, similarities.sort_values(by=['Weight'], ascending=False).to_dict(orient="records")
        

    @app.callback(
        Output("methodType", "label"),
        [Input("methodType", "value")]
    )
    def get_method_type(methodType):
        if methodType:
            return "Method: Twitter data"
        return "Method: Own data"

    
    @app.long_callback(
        Output('similarity-table', 'data'),
        Input("startCoordination", "n_clicks"),
        State("methodType", "value"),
        State('clusterSessionID', 'data'),
        State('selectedCluster', 'value'),
        State('selectedClusterTime', 'value'),
        running=[
            (Output("startCoordination", "disabled"), True, False),
        ],
        prevent_initial_call=True,
        interval=10000
    )
    def start_coordination_calculation(startButton, methodType, sessionID, clusterID,  timestamp):
        if clusterID is None or timestamp is None:
            return
        if methodType:
            data = pipeline.calculate_coordination_pipeline_twitter_data(sessionID, int(clusterID), timestamp)
        else:
            data =  pipeline.calculate_coordination_pipeline_own_data(sessionID, int(clusterID), timestamp)

        data = data[data["Weight"] >= 0.6]

        return data.to_dict(orient="records")


    app.clientside_callback(
        """
        function(data) {
            twitter_names = data['points'][0]['customdata'];
            for (name in twitter_names){
                window.open('https://twitter.com/'+twitter_names[name], '_blank');
            }
            return ""
        }
        """,
        Output("placeholder", "children"),
        Input("coordination-graph", "clickData"),
        prevent_initial_call=True
    )