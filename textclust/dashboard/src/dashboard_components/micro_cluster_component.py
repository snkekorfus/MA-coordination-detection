import dash
import dash_html_components as html
import dash_core_components as dcc
import dash_daq as daq
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import plotly.express as px

import numpy as np
import plotly.graph_objects as go
from helpers import cluster_helpers


def micro_cluster_layout():
    data_init = []
    figureInit = go.Figure(dict(data=data_init)) \
        .update_layout(
            height=400,
            plot_bgcolor="rgb(255,255, 255)",
            title="Entwicklung der Themen (Cluster)",
            xaxis_title="Time",
            yaxis_title="Cluster weight",
            legend_title="Top Clusters / Themen",

    )

    figureInit.update_xaxes(fixedrange=False)

    return html.Div([
        html.Div(id="traceRangeWrapper", children=[
            html.Span("Anzahl der Cluster: "),
            dcc.Input(
                id="traceRange",
                type="number",
                value=10,
                min=1,
                max=100,
                step=1,
            ),
            daq.BooleanSwitch(id='sus-clusters', on=False, label="Zeige nur auffällige Cluster"),
        ]),
        dcc.Graph(
            id='graph-extendable',
            figure=figureInit
        ),
        dcc.Store("snapshot-options"),
        dcc.Store("timestamp", data=0)
    ])


def register_callback(app, API_IP, API_PORT):
    # TODO: timestamp zu store umschreiben statt div zu nehmen
    # TODO: timestamp updaten um cluster zu selecten
    @ app.callback(Output('graph-extendable', 'figure'),
                   Output('timestamp', 'data'),
                   Output('snapshot-options', 'data'),
                   [Input('running-timer', 'n_intervals'),
                   Input('traceRange', 'value'),
                   Input('clusterSessionID', 'data'),
                   Input('sus-clusters', 'on')],
                   [State('graph-extendable', 'figure'),
                   State('timestamp', 'data'),
                   State('selectedCluster', 'options')])
    def check_new_microclusters(n_new, max_shown, sessionID, suspicious, existing, timestamp, options):
        n = 0
        ctx = dash.callback_context
        input_id = ctx.triggered[0]['prop_id'].split('.')[0]
        past_loader = False
        # differnetiate multiple contexts --> live updating or past session loading or changing the time range or clearing the graph
        # clear the graph
        if sessionID == None:
            existing["data"] = []
            return existing, 0, []
        # live updating
        elif input_id == "running-timer" : 
            n = n_new
        # seleting time range
        elif input_id == "traceRange" or input_id == 'clusterSessionID' or input_id == "sus-clusters":
            n = 1
            timestamp = 0
            existing["data"] = []

        # if n > 0 new data is fetched
        if n is not None and n > 0:
            updated = False
            timestamp_return = timestamp
            timestamp_string = timestamp

            current_shown_cluster_traces = existing["data"]
            trace_visibility = {cluster["meta"][0]: cluster.get("visible") for cluster in existing["data"]}

            # check if and when the clustering session was last updated and get infos about realtimefading for display concerns
            updated, last_update, rtf = cluster_helpers.cluster_updated(sessionID, timestamp, API_IP, API_PORT)
            if updated:
                # resseting the options
                options = []

                if not suspicious:
                    # fetching the currently highest weighted microclusters
                    max_weighted_cluster_id_list = cluster_helpers.get_max_weight_cluster_ids(
                        sessionID, timestamp_string, max_shown, rtf, API_IP, API_PORT)
                    print(f"max_weight: {max_weighted_cluster_id_list}", flush=True)
                else:
                    max_weighted_cluster_id_list = cluster_helpers.get_suspicious_cluster_ids(
                        sessionID, timestamp_string, max_shown, rtf, API_IP, API_PORT)

                # defining the currently displayed microclusters inside of the graph
                current_shown_cluster_id_list = [d["name"] for d in current_shown_cluster_traces]
                #  defining the microclusters, which just need attachment of new data points --> already in the graph and still top weighted
                to_append_clusters = list(set(max_weighted_cluster_id_list) & set(current_shown_cluster_id_list))
                #  defining the microclusters, which need all their data poitns fetched --> not in the graph and new to the lit of top weighted microclusters
                to_fetch_clusters = list(set(max_weighted_cluster_id_list) - set(current_shown_cluster_id_list))

                # fetch the newly ascended microcluster weight-time series
                if len(to_fetch_clusters) > 0:

                    # fetching is requested to the backend
                    new_time_series_cluster_data = cluster_helpers.get_weight_time_series(
                        sessionID, to_fetch_clusters, API_IP, API_PORT, rtf)

                else:
                    new_time_series_cluster_data = []

                # fetch the partially weight-time series, which can be attachet to already existing traces in the graph
                if len(to_append_clusters) > 0:
                    append_time_series_cluster_data = cluster_helpers.get_new_cluster_data_since(
                        sessionID, timestamp_string, to_append_clusters, API_IP, API_PORT)
                else:
                    append_time_series_cluster_data = []

                # strucure data in dict form
                append_time_series_cluster_dict = {}
                for timeserie in append_time_series_cluster_data:
                    append_time_series_cluster_dict[str(timeserie["_id"])] = timeserie

                # calculating maximal weighted trace for fading colors of all traces
                max_weight = 0
                for timeserie in append_time_series_cluster_data:
                    current_weight_cluster = timeserie["weight_serie"][-1]
                    if current_weight_cluster > max_weight:
                        max_weight = current_weight_cluster

                for timeserie in new_time_series_cluster_data:
                    current_weight_cluster = timeserie["weight_serie"][-1]
                    if current_weight_cluster > max_weight:
                        max_weight = current_weight_cluster


                # take the fetched microcluster informations from the backend and append them to the traces already existing
                new_shown_cluster_traces = []
                for i, traceDict in enumerate(current_shown_cluster_traces):
                    cluster_id = traceDict["name"]
                    if cluster_id in to_append_clusters:
                        # append old and new data to weight-time series
                        x_list = traceDict["x"]
                        if rtf == "true":
                            x_list = np.append(np.array(x_list, dtype='datetime64'), np.array(
                                append_time_series_cluster_dict[str(cluster_id)]["timestamp_serie"], dtype='datetime64'))
                            x_list = x_list + np.timedelta64(0, 'h')
                        else:
                            x_list = x_list + \
                                append_time_series_cluster_dict[str(
                                    cluster_id)]["timestamp_serie"]
                        y_list = traceDict["y"]

                        y_list = y_list + \
                            append_time_series_cluster_dict[str(
                                cluster_id)]["weight_serie"]

                        # append ids to cluster id dropdown options
                        options.append(cluster_id)

                        # calculating color of trace
                        current_weight_cluster = y_list[-1]
                        opacity = max((current_weight_cluster / max_weight), 0.2)

                        # creating new scatter plot with old and new data combined, formating hover data with template
                        traceToAppend = go.Scatter(x=x_list, y=y_list, name=cluster_id, meta=[cluster_id], mode="lines+markers", marker=dict(
                            color='rgba(47,79,79, {})'.format(str(opacity))),
                            hovertemplate="<br>".join([
                                "Zeit: %{x}",
                                "Gewicht: %{y}",
                                "Cluster-ID: %{meta[0]",
                                "<extra></extra>"
                            ]))
                        # append trace to the final list of microcluster traces
                        new_shown_cluster_traces.append(traceToAppend)

                # take the fetched microcluster informations from the backend and create new traces
                for traceData in new_time_series_cluster_data:
                    y_list = traceData["weight_serie"]
                    if rtf == "true":
                        x_list = np.array(traceData["timestamp_serie"], dtype='datetime64')
                        x_list = x_list + np.timedelta64(0, 'h')
                    else:
                        x_list = traceData["timestamp_serie"]

                    cluster_id = traceData["_id"]
                    # append ids to cluster id dropdown options
                    options.append(cluster_id)

                    # calculating color of trace
                    current_weight_cluster = y_list[-1]
                    opacity = max((current_weight_cluster / max_weight), 0.2)

                    # creating new scatter plot with only new data, formating hover data with template
                    traceToAppend = go.Scatter(x=x_list, y=y_list, name=cluster_id, meta=[cluster_id], mode="lines+markers", marker=dict(
                        color='rgba(47,79,79, {})'.format(str(opacity))),
                        hovertemplate="<br>".join([
                            "Zeit: %{x}",
                            "Gewicht: %{y}",
                            "Cluster-ID: %{meta[0]}",
                            "<extra></extra>"
                        ]),
                        visible= trace_visibility.get(cluster_id))
                    # append trace to the final list of microcluster traces
                    new_shown_cluster_traces.append(traceToAppend)
                # updating the final figure of the graph and insert all calculated time-weight series microcluster traces
                highest_cluster_ids = filter_highest_clusters(new_shown_cluster_traces)
                new_shown_cluster_traces = adapt_traces_colors(new_shown_cluster_traces, highest_cluster_ids)
                new_shown_cluster_traces = sorted(new_shown_cluster_traces, key=lambda traces: traces['y'][-1], reverse=True)
                existing["data"] = new_shown_cluster_traces
                timestamp_return = last_update
            else:
                raise PreventUpdate

            if past_loader:
                # resetting whole figure, if session from the past is loaded --> otherwise displaying different time ranges is incorrect
                existing = go.Figure(dict(data=new_shown_cluster_traces)).update_layout(height=400, plot_bgcolor="rgb(250,250, 250)",
                                                                                        title="Micro-Cluster Overview", xaxis_title="time", yaxis_title="micro-cluster weight", legend_title="Top Micro-Cluster",)
            return existing, timestamp_return, options
        else:
            raise PreventUpdate

    # callback function to update the timestamp options and selected timestamp and selected cluster id , if the user clicks
    # into the microcluster time-weight series graph on a specific trace or chooses manual values from the dropdown options
    @app.callback(Output('selectedCluster', 'value'),
                  Output('selectedClusterTime', 'value'),
                  Output('selectedClusterTime', 'options'),
                  Output('graph-extendable', 'clickData'),
                  [Input('graph-extendable', 'clickData'),
                  Input('selectedClusterTime', 'value'),
                  Input('selectedCluster', 'value'),
                  Input('selectedCluster', 'options'),
                  Input('clusteredKeywords', 'value')],
                  [State('graph-extendable', 'figure')])
    def display_click_data(click_data, selected_time, selected_cluster_id, selected_cluster_options, clusteredKeywords, existing):
        # differentiate the contexts of clicking in the graph or selecting
        # manually cluster ids and timstamps from the dropwdown options
        ctx = dash.callback_context
        input_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if selected_cluster_options == []:
            return dash.no_update, None, [], dash.no_update
    	
        # Reset cluster to None if we change the stream
        if input_id == "clusteredKeywords":
            return None, None, [], dash.no_update

        # context of click event
        if input_id == "graph-extendable":
            # looking into the specific trace of the cluster and get the cluster id and timestamp of the datapoint
            curve_number = click_data['points'][0]['curveNumber']
            trace_name = existing['data'][curve_number]['name']
            clicked_date = click_data['points'][0]["x"]

            # checking if data is int or datetime format
            if isinstance(clicked_date, int):
                current_shown_cluster_traces = existing["data"]
                for traceDict in current_shown_cluster_traces:

                    # updating time options
                    cluster_id = traceDict["name"]
                    if cluster_id == trace_name:
                        time_options = [{'label': date, 'value': date}
                                        for date in traceDict["x"]]
            else:
                clicked_date = np.datetime64(clicked_date)
                current_shown_cluster_traces = existing["data"]
                for traceDict in current_shown_cluster_traces:

                    # updating time options
                    cluster_id = traceDict["name"]
                    if cluster_id == trace_name:
                        time_options = [{'label': date[:19].replace("T", " "), 'value': date}
                                        for date in traceDict["x"]]

            return trace_name, clicked_date, time_options, dash.no_update
        # context of manually selected cluster id
        if input_id == "selectedCluster" and selected_cluster_id is not None:
            current_shown_cluster_traces = existing["data"]

            # updating time options
            for traceDict in current_shown_cluster_traces:

                cluster_id = traceDict["name"]
                time_options = [{'label': date[:19].replace("T", ""), 'value': date}
                                for date in traceDict["x"]]

                return dash.no_update, dash.no_update, time_options, dash.no_update

        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    def filter_highest_clusters(traces):
        max_cluster_ids = {}
        for elem in traces:
            if len(max_cluster_ids) != 10:
                max_cluster_ids[elem['meta'][0]] = max(elem['y'])
            else:
                min_key = min(max_cluster_ids, key=max_cluster_ids.get)
                if max_cluster_ids[min_key] < max(elem['y']):
                    max_cluster_ids.pop(min_key)
                    max_cluster_ids[elem['meta'][0]] = max(elem['y'])
        return sorted(max_cluster_ids.keys())

    def adapt_traces_colors(traces, ids):
        i = 0
        for elem in traces:
            if elem['meta'][0] in ids:
                #elem['marker']['color'] = i
                elem['marker']['color'] = px.colors.qualitative.Plotly[i]
                i += 1
        return traces
