from math import ceil
from pandas.core.tools.datetimes import to_datetime
import dash
import dash_html_components as html
import dash_core_components as dcc
#from dash_extensions import Download
from dash.dependencies import Input, Output, State
import os
import json

from .data_tabs import general_tab
from .data_tabs import token_tab
from .data_tabs import assignment_tab

from .twitter_tabs import key_figures_tab
from .twitter_tabs import user_aggregation_tab
from .twitter_tabs import users_tab

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import requests
import numpy as np
import pandas as pd
import plotly.express as px


def snapshot_layout():
    def check_availability(tab_type):  
        if 'private_dashboard' in os.environ and os.environ['private_dashboard'] == "True":
            if tab_type == "user":
                return [
                    key_figures_tab.key_figures_tab_layout(),
                        # tab in tab with boxplots/histogram aggregated information about tweets and users
                        user_aggregation_tab.user_aggregation_tab_layout(),
                        users_tab.users_tab_layout()
                ]
            elif tab_type == "assignment":
                return [
                    general_tab.general_tab_layout(),
                    # tab with table inside, which will load all microcluster specific tokens/terms/ngrams
                    token_tab.token_tab_layout(),
                    assignment_tab.assignment_tab_layout()
                ]
        else:
            if tab_type == "user":
                return [
                    key_figures_tab.key_figures_tab_layout(),
                        # tab in tab with boxplots/histogram aggregated information about tweets and users
                        user_aggregation_tab.user_aggregation_tab_layout()
                ]
            elif tab_type == "assignment":
                return [
                    general_tab.general_tab_layout(),
                    # tab with table inside, which will load all microcluster specific tokens/terms/ngrams
                    token_tab.token_tab_layout()
                ]

    def check_download():
        if 'private_dashboard' in os.environ and os.environ['private_dashboard'] == "True":
            return [html.Span("Cluster-ID:",
                              style={"font-weight": "bold"}),
                    dcc.Dropdown(id="selectedCluster"),
                    html.Button("Download Micro-Cluster", id="btn_download"), dcc.Download(id="download-mc")]
        else:
            return [html.Span("Cluster-ID:",
                              style={"font-weight": "bold"}),
                    dcc.Dropdown(id="selectedCluster")]

    return html.Div([
        dbc.Button(
            [html.Div("Cluster Detailansicht",style={"display": "inline-block", "margin-right":"5px"}), html.Div(className="fa fa-lg fa-angle-up")],
            id="collapse-button-detail",
            className="mb-3",
            n_clicks=0,
            style ={"color":"white",'background-color': '#182637'}
        ),
        
        dbc.Collapse( 
        html.Div(id="clusterData", children=[
            # selecting of cluster id and clsuter timestamp through dropdowns
            html.Div(id="clusterDataSelecter", children=[
                html.Div(id="selectedClusterWrapper", children=check_download()
                ),
                html.Div(id="selectedClusterTimeWrapper", children=[
                    html.Span("Timestamp:", style={"font-weight": "bold"}),
                    dcc.Dropdown(id="selectedClusterTime", options=[])]),
            ]),
            # the actual data metric
            html.Div(id="clusterDataMetrics", children=[
                dcc.Tabs(id="clusterDataTabs", children=check_availability("assignment")),
                # wrapper for twitter related data metrics of microclusters
                html.Div(id="clusterTwitterMetrics", children=[
                    dcc.Tabs(children=check_availability("user"))
                ])
            ]),
        ]),
         is_open=False,
         id="collapse-cluster-detail"
    ),
    dcc.Store(id="textStore", data=None),
    dcc.Store(id="textIdList", data=None),
    dcc.Store(id="userStore", data=None)
    ])
   

def register_callback(app, API_IP, API_PORT):
    @app.callback(
        Output("collapse-cluster-detail", "is_open"),
        Output("collapse-button-detail", "children"),
        [Input("collapse-button-detail", "n_clicks")],
        [State("collapse-cluster-detail", "is_open"),
        State("collapse-button-detail", "children")],
    )
    def toggle_collapse(n, is_open, children):
        if n:
            if is_open:
                return not is_open, [html.Div("Cluster Detailansicht",style={"display": "inline-block", "margin-right":"5px"}), html.Div(className="fa fa-lg fa-angle-up")]
            else:
                return not is_open, [html.Div("Cluster Detailansicht",style={"display": "inline-block", "margin-right":"5px"}), html.Div(className="fa fa-lg fa-angle-down")]
        return is_open, children
    
    
    # helper
    # simple function to compute + prefix for positive values
    def score(i):
        return ("+" if float(i) > 0 else "") + str(i)

    @app.callback(Output('selectedCluster', 'options'),
                  Input('snapshot-options', 'data'))
    def update_snapshot_options(snapshot_options):
        options = [{'label': cluster_id, 'value': cluster_id} for cluster_id in snapshot_options]
        return options

    if 'private_dashboard' in os.environ and os.environ['private_dashboard'] == "True":
        @app.callback(Output('textTable', 'data'),
                      Output('usersTable', 'data'),
                      [Input("textStore", 'data'),
                       Input("userStore", 'data')])
        def activate_private_view(textStore, userStore):
            textStorage = dash.no_update
            userStorage = dash.no_update
            if textStore is not None:
                textStorage = textStore
            if userStore is not None:
                userStorage = userStore
            return textStorage, userStorage


        @ app.callback(Output("download-mc", "data"),
                        Input("btn_download", "n_clicks"),
                        [State('clusterSessionID', 'data'),
                        State("selectedClusterTime", 'value'), 
                        State("selectedCluster", 'value')],
                        prevent_initial_call=True,
                        )
        def download_micro_cluster(n_clicks,session_id,selected_cluster_time,selected_cluster):
            if selected_cluster is not None:
                api_password = "J2be9jPrnJSmEScF" if 'private_dashboard' in os.environ and os.environ['private_dashboard'] == "True" else ""
                selected_cluster_time = np.datetime64(selected_cluster_time) - np.timedelta64(0, 'h')
                # fetching metrics from the backend
                URL = "http://{}:{}/getClusterMeta?session={}&timestamp={}&clusterId={}&pw={}".format(
                API_IP, API_PORT, session_id, selected_cluster_time, selected_cluster, api_password)
                r = requests.get(url=URL)
                mc_data = r.json()

                # requesting termfrequencies of the microcluster snapshots from the backend
                URL = "http://{}:{}//getTermFrequencies?session={}&timestamp={}&clusterId={}".format(
                API_IP, API_PORT, session_id, selected_cluster_time, selected_cluster)
                r = requests.get(url=URL)
                try:
                    term_data = r.json()
                except:
                    term_data = None

                # fetching the twitter related data metrics from the backend
                URL = "http://{}:{}//getTwitterMeta?session={}&timestamp={}&clusterId={}&pw={}".format(
                API_IP, API_PORT, session_id, selected_cluster_time, selected_cluster, api_password)
                r = requests.get(url=URL)
                twitter_data = r.json()

                return (dict(content=json.dumps({"mc-data":mc_data,"term-data":term_data, "twitter-data":twitter_data}), filename="output.json"))
            else:
                return (dict(content=json.dumps({}), filename="output.json"))                





    # callback function for updating microcluster snapshot metrics
    @app.callback(Output('textNumber', 'children'),
                   Output('selectedClusterNewTextsAbs', 'children'),
                   Output('selectedClusterNewTextsRel', 'children'),
                   Output('selectedClusterWeight', 'children'),
                   Output('selectedClusterWeightChangeAbs', 'children'),
                   Output('selectedClusterWeightChangeRel', 'children'),
                   Output('termTable', 'data'),
                   Output('userStore', 'data'),
                   Output("twtAccNumber", 'children'),
                   Output("twtVerifiedUsersAbs", 'children'),
                   Output("twtVerifiedUsersRel", 'children'),
                   Output("twtNumber", 'children'),
                   Output("twtDefaultProfile", 'children'),
                   Output("twtDefaultImage", 'children'),
                   Output("followerBoxPlot", "figure"),
                   Output("likedBoxPlot", "figure"),
                   Output("userTweetsBoxPlot", "figure"),
                   Output("friendsBoxPlot", "figure"),
                   Output("accountnAgeBar", "figure"),
                   Output("mcStatusesBar", "figure"),
                   Output("wordcloud-data","data"),
                   Output("textTable", "page_count"),
                   Output('textIdList', 'data'),
                   [Input("selectedCluster", 'value'),
                   Input('selectedCluster', 'options'),
                   Input("selectedClusterTime", 'value')],
                   [State('clusterSessionID', 'data'),
                   State("selectedClusterTime", 'options'), ])
    def display_cluster_data(selected_cluster, selected_cluster_options, selected_cluster_time, session_id, time_options):

        # return 0 values, if context is triggered without full data input or wront time options
        if selected_cluster is None or selected_cluster_time is None or selected_cluster_options == []:
            return "0", "0.00%", "0", "0", "0.00%", "0", [], None, "0", "0", "0.00%", "0", "0", "0", {}, {}, {}, {}, {},{},{}, 0, None
        try:
            matching_value_option = any(
                selected_cluster_time in d['value'] or d['value'] in selected_cluster_time for d in time_options)
        except:
            matching_value_option = any(
                selected_cluster_time == d['value'] for d in time_options)
        if not matching_value_option:
            return "0", "0.00%", "0", "0", "0.00%", "0", [], None, "0", "0", "0.00%", "0", "0", "0", {}, {}, {}, {}, {},{},{}, 0, None

        api_password = "J2be9jPrnJSmEScF" if 'private_dashboard' in os.environ and os.environ['private_dashboard'] == "True" else ""

        selected_cluster_time = np.datetime64(selected_cluster_time) - np.timedelta64(0, 'h')
        # fetching metrics from the backend
        URL = "http://{}:{}/getClusterMeta?session={}&timestamp={}&clusterId={}&pw={}".format(
            API_IP, API_PORT, session_id, selected_cluster_time, selected_cluster, api_password)
        r = requests.get(url=URL)
        mc_data = r.json()

        # all kinds of data metrics related to the weight and text of the microcluster snapshots
        texts_number = mc_data["texts_number"]
        text_id_list = mc_data["text_id_list"]
        page_count = int(ceil(mc_data["texts_number"] / 8))

        #texts_data = mc_data["texts_data"]
        #if 'private_dashboard' in os.environ and os.environ['private_dashboard'] == "True":
        #    texts_data = sorted(texts_data, key= lambda comment: comment["time"], reverse=True)

        cluster_weight = round(mc_data["cluster_weight"], 2)

        weight_growth_abs = score(mc_data["weight_growth_abs"])
        weight_growth_rel = "{}%".format(score(mc_data["weight_growth_rel"]))

        text_ids_growth_abs = score(mc_data["text_ids_growth_abs"])
        text_ids_growth_rel = "{}%".format(
            score(mc_data["text_ids_growth_rel"]))

        # requesting termfrequencies of the microcluster snapshots from the backend
        URL = "http://{}:{}//getTermFrequencies?session={}&timestamp={}&clusterId={}".format(
            API_IP, API_PORT, session_id, selected_cluster_time, selected_cluster)
        r = requests.get(url=URL)
        try:
            term_data = r.json()
        except:
            term_data = None
            term_data = [{"termcolumn": "-", "freqcolumn": "-"}]
        term_data = sorted(term_data, key=lambda keyword: keyword["freqcolumn"], reverse=True)

        # fetching the twitter related data metrics from the backend
        URL = "http://{}:{}//getTwitterMeta?session={}&timestamp={}&clusterId={}&pw={}".format(
            API_IP, API_PORT, session_id, selected_cluster_time, selected_cluster, api_password)
        r = requests.get(url=URL)
        response_dict = r.json()

        # assigning fetched data towards many metric figures
        twt_data = response_dict["tweet_meta"]
        twt_users = response_dict["users_meta"]
        if 'private_dashboard' in os.environ and os.environ['private_dashboard'] == "True":
            twt_users = sorted(twt_users, key= lambda user: user['statuses_in_cluster'], reverse=True)

        users_in = twt_data["users_in"]

        cluster_statuses = twt_data["statuses_in_cluster"] 
        cluster_statuses.sort(reverse=True)
        top10 = cluster_statuses[0:10]

        verified_abs = twt_data["verified_abs"]
        verified_rel = "{}%".format(
            str(round(twt_data["verified_rel"]*100, 2)))
        lang = twt_data["lang"]

        # create different kinds of boxplots for followers, friends, ....
        acc_ages = pd.to_datetime(twt_data["acc_ages"])
        unique, counts = np.unique(acc_ages.year, return_counts=True)
        acc_ages = {'years': unique, 'counts': counts}
        acc_ages_bar = px.bar(acc_ages, x="years", y="counts", color_discrete_sequence=["#2c3e50"])
        #acc_ages_bar.update_xaxes(type='category')
        acc_ages_bar.update_layout({
            "yaxis_title":"",
            "xaxis_title":"Account Erstellungsdatum",
            "bargap":0.2,
            "plot_bgcolor": "rgb(255,255, 255)",
            "height": 150,
            "margin": dict(
                l=0,
                r=0,
                b=0,
                t=0)
        })

        # create different kinds of boxplots for followers, friends, ....
        acc_mc_statuses_bar = px.bar(x=list(range(1,len(top10)+1)),y=top10, color_discrete_sequence=["#2c3e50"])
        acc_mc_statuses_bar.update_layout({
            "yaxis_title":"",
            "xaxis_title":"Tweets der Top User",
            "bargap":0.2,
            "plot_bgcolor": "rgb(255,255, 255)",
            "height": 150,
            "margin": dict(
                l=0,
                r=0,
                b=0,
                t=0)
        })

     
        # default image/profile information
        default_image = twt_data["default_image"]
        default_profile = twt_data["default_profile"]

        friends = twt_data["friends"]
        statuses = twt_data["statuses"]
        followers = twt_data["followers"]
        liked = twt_data["liked"]

        # friends boxplot
        friends_plot = px.box(
          data_frame={"Freunde":friends}, color_discrete_sequence=["#7ccc63"], log_y=True)
        friends_plot.update_layout({
            "yaxis_title":"",
            "xaxis_title":"",
            "plot_bgcolor": "rgb(255,255, 255)",
            "height": 250,
            "margin": dict(
                l=0,
                r=0,
                b=0,
                t=0)
        })

        ## disable hover info
        friends_plot.update_traces(hoverinfo='skip',hovertemplate=None )

        # created tweets boxplot
        user_tweets_plot = px.box(
            data_frame={"Tweets":statuses},  color_discrete_sequence=["#f39c12"], log_y=True)
        user_tweets_plot.update_layout({
            "yaxis_title":"",
            "xaxis_title":"",
            "plot_bgcolor": "rgb(255,255, 255)",
            "height": 250,
            "margin": dict(
                l=0,
                r=0,
                b=0,
                t=0)
        })

        ## disable hover info
        user_tweets_plot.update_traces(hoverinfo='skip',hovertemplate=None )

        # followers boxplot
        followers_plot = px.box(data_frame={"Follower":followers}, color_discrete_sequence=["#bdc3c7"], log_y=True)
        followers_plot.update_layout({
            "yaxis_title":"",
            "xaxis_title":"",
            "plot_bgcolor": "rgb(255,255, 255)",
            "height": 250,
            "margin": dict(
                l=0,
                r=0,
                b=0,
                t=0)
        })

        ## disable hover info
        followers_plot.update_traces(hoverinfo='skip',hovertemplate=None )

        # likes boxplot
        liked_plot = px.box(
            data_frame={"Geliked":liked}, color_discrete_sequence=["#e74c3c"], log_y=True)
        liked_plot.update_layout({
            "yaxis_title":"",
            "xaxis_title":"",
            "plot_bgcolor": "rgb(255,255, 255)",
            "height": 250,
            "margin": dict(
                l=0,
                r=0,
                b=0,
                t=0)
        })
        
        ## disable hover info
        liked_plot.update_traces(hoverinfo='skip',hovertemplate=None )
       
        return texts_number, text_ids_growth_abs, text_ids_growth_rel, cluster_weight, weight_growth_abs, weight_growth_rel, term_data, twt_users, users_in, verified_abs, verified_rel, texts_number, default_profile, default_image, followers_plot, liked_plot, user_tweets_plot, friends_plot, acc_ages_bar, acc_mc_statuses_bar, term_data, page_count, text_id_list
