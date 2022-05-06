import requests


# function for sending request to the api to validate the clustering session id --> given or running or clear
def check_session_id(cluster_session_id, API_IP, API_PORT):
    URL = "http://{}:{}/validateClusterSessionId?session={}".format(
        API_IP, API_PORT, cluster_session_id)
    r = requests.get(url=URL)
    session_meta = r.json()
    return session_meta
