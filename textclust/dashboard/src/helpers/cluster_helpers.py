import requests


# function to check, if new microcluster snapshots are available in the database to fetch
def cluster_updated(session, timestamp, API_IP, API_PORT):
    URL = "http://{}:{}/updated?session={}&timestamp={}".format(
        API_IP, API_PORT, session, timestamp)
    r = requests.get(url=URL)
    updated = r.json()
    return updated["updated"], updated["last_update"], updated["rtf"]


# function to requesting the ids of the currently highest weighted microclusters of a specific timestamp
def get_max_weight_cluster_ids(sessionID, timestamp_string, max_shown, rtf, API_IP, API_PORT):
    URL = "http://{}:{}/getMaxWeightClusterIds?session={}&timestamp={}&max={}&rtf={}".format(
        API_IP, API_PORT, sessionID, timestamp_string, max_shown, rtf)
    print(URL, flush=True)
    r = requests.get(url=URL)
    max_weighted_cluster_id_list = r.json()
    return max_weighted_cluster_id_list

# function to requesting the ids of the currently highest weighted microclusters of a specific timestamp
def get_suspicious_cluster_ids(sessionID, timestamp_string, max_shown, rtf, API_IP, API_PORT):
    URL = "http://{}:{}/getSuspiciousIds?session={}&timestamp={}&max={}&rtf={}".format(
        API_IP, API_PORT, sessionID, timestamp_string, max_shown, rtf)
    r = requests.get(url=URL)
    max_weighted_cluster_id_list = r.json()
    return max_weighted_cluster_id_list


# function for requesting complete weight-time series of a given list of microcluster ids
def get_weight_time_series(sessionID, to_fetch_clusters, API_IP, API_PORT, rtf="true"):
    # differentiate bewteen request with or without selected min_time_stamps
    getWholeTimeSeriesURL = "http://{}:{}/getFullTimeWeightSeries?session={}&rtf={}".format(
        API_IP, API_PORT, sessionID, rtf)
    r = requests.get(url=getWholeTimeSeriesURL, json={
        "cluster-ids": to_fetch_clusters})
    new_time_series_cluster_data = r.json()
    return new_time_series_cluster_data


# function for requesting partial weight-time series of a given list microcluster ids from on a certain timestamp
def get_new_cluster_data_since(sessionID, timestamp_string, to_append_clusters, API_IP, API_PORT):
    getToAppendData = "http://{}:{}/getLatestTimeWeightSeries?session={}&timestamp={}".format(
        API_IP, API_PORT, sessionID, timestamp_string)
    r = requests.get(url=getToAppendData, json={
        "cluster-ids": to_append_clusters})
    append_time_series_cluster_data = r.json()
    return append_time_series_cluster_data
