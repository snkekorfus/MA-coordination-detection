from flask import request, session, Blueprint, current_app
from celery_task import run_textclust
from celery.app.control import Control
from datetime import datetime
import helpers
import json
import os
import pandas as pd
from operator import itemgetter


urls_blueprint = Blueprint('urls', __name__)

# checking if clustersession is is already in use and fetches meta data for overtaking running session
@urls_blueprint.route('/validateClusterSessionId', methods=['GET'])
def check_session_id():
    cluster_session_id = request.args.get('session')

    #requesting session meta from mongodb
    cluster_session_meta = list(current_app.config['db']["textclust_sessions_meta"].find(
        {"cluster_session_id": cluster_session_id}))
    
    #checking if clustersession is is already in us
    if len(cluster_session_meta) > 0:
        start_date = cluster_session_meta[0]["start_date"].timestamp()
        given = True
        #checking if session is also currently running
        if cluster_session_meta[0]["ended"]:
            ended = True
        else:
            ended = False
    else:
        given = False
        ended = False
        start_date = None
    return json.dumps({"given": given, "ended": ended, "start_date": start_date})


# route for starting textClust session
@urls_blueprint.route('/startTextClustSession', methods=['GET', 'POST'])
def start_clust():
    # reading requests post data
    data = request.get_json()
    data = json.loads(data)

    # seperating data for configuration
    preprocessing = data["preprocessing"]
    inputSource = data["inputSource"]
    #terms = data["terms"]
    cluster_session_id = data["cluster_session_id"]
    session["id"] = cluster_session_id

    data["clust"]["embedding_verification"] = False

    config = {
        "textclust": {
            "config": data["clust"]
        },
        "preprocessing": preprocessing,
        "inputSource": inputSource,
        "cluster_session_id": cluster_session_id
    }

    # starting the actual textClust clustering process, task is pushed into celery task query
    run_textclust.delay(config)
    return "CREATED"


# route for stopping textClust session
@urls_blueprint.route('/stopTextClustSession', methods=['GET'])
def stop_clust():
    cluster_session_id = request.args.get('session')
    currentControl = Control(app=current_app.config['celery'])

    # fetching celery task id for revoking task
    task_id = list(current_app.config['db']["textclust_sessions_meta"].find(
        {"cluster_session_id": cluster_session_id}))[0]["celery_task_id"]
    currentControl.revoke(task_id, terminate=True)
    end_date = datetime.utcnow()

    # updating session meta to end state
    current_app.config['db']["{}".format("textclust_sessions_meta")].find_one_and_update(
        {"cluster_session_id":  cluster_session_id, "ended": False}, {"$set": {"end_date": end_date, "ended": True}})
    return "STOPPED"


# route for fetching prev cluster session meta data
@urls_blueprint.route('/getPrevClusterSessions', methods=['GET', 'POST'])
def list_previous_sessions():

    # reqeusting all meta session infos from mongodb
    prev_sessions_meta = []
    all_past_sessions = list(current_app.config['db']["textclust_sessions_meta"].find({}))

    # structuring fetched data from sessions in list of dict
    for session in all_past_sessions:
        mode = session["input_source"]["mode"]
        terms = session["input_source"]["terms"]
        clustering_date = session["start_date"].date()

        # checking end
        if session["ended"]:
            # calc runnign time ended
            running_time = session["end_date"].replace(
                microsecond=0) - session["start_date"].replace(microsecond=0)
            status = "finished"
        else:
            # checking end running
            running_time = datetime.utcnow().replace(microsecond=0) - \
                session["start_date"].replace(microsecond=0)
            status = "running"

        # calc time horizon of clustered data 
        try:
            data_beginning = pd.to_datetime(current_app.config['db']["texts_{}".format(session["cluster_session_id"])].find_one()[
                "general"]["time"])
            if session["ended"]:
                data_end = pd.to_datetime(current_app.config['db']["texts_{}".format(session["cluster_session_id"])].find_one(
                    {}, sort=[("$natural", -1)])["general"]["time"])
                data_time_horizont = data_end.replace(
                    microsecond=0) - data_beginning.replace(microsecond=0)
            else:
                data_end = "-"
                data_time_horizont = "-"

        # fetch time calc problems
        except:
            data_beginning = "-"
            data_end = "-"
            data_time_horizont = "-"

        # reqeusting number of processed texts from mongodb
        number_texts = current_app.config['db']["texts_{}".format(
            session["cluster_session_id"])].count()

        temp_dict = {"id": session["cluster_session_id"], "mode": mode, "terms": terms, "clustering_date": clustering_date, "running_time": running_time,
                     "status": status, "data_beginning": data_beginning, "data_end": data_end, "data_time_horizont": data_time_horizont, "number_texts": number_texts}
        prev_sessions_meta.append(temp_dict)

    return_json = json.dumps(prev_sessions_meta, default=str)
    return return_json


# route for uploading CSV to csv folder
@urls_blueprint.route('/uploadCSV', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        cluster_session_id = request.args.get('session')
        print(cluster_session_id, flush=True)
        csv_file = request.files['file']
        print(csv_file, flush=True)

        csv_path = os.path.join("./csvTemp", "csv_{}".format(cluster_session_id))
        csv_file.save(csv_path)
    return "True"


# route for requesting micro-cluster meta data
@urls_blueprint.route('/getClusterMeta', methods=['GET'])
def get_cluster_texts():

    # parsing query paramters session id, clsuter id and timestamp as string
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    cluster_id = request.args.get('clusterId')

    # checking type of timetampt: datetime for realtimefadin or else int
    typePipeline = [
        {"$project": {"timestamp_type" : { "$type": "$timestamp" }}},
        {"$limit": 1},
        ]
    timestamp_type = list(current_app.config['db']["mc_{}".format(cluster_session_id)].aggregate(typePipeline))[0]["timestamp_type"]

    # transform string to int if not realtime faded and to datetime otherwise
    if timestamp_type == "int":
        timestamp_datetime = int(timestamp_string)
    else:
        timestamp_datetime = pd.to_datetime(timestamp_string)

    # mongodb aggregate pipeline for the last two microcluster snapshots
    lastWeightsPipeline = [
        {"$match": {"id": int(cluster_id), "timestamp":{"$lte": timestamp_datetime}}},
        {"$project": {"_id": 0, "weight": 1, "timestamp" : 1, "textids": 1}},
        {"$sort": {"timestamp": -1}},
        {"$limit": 2}
    ]

    lastTwoSnapshots = list(current_app.config['db']["mc_{}".format(cluster_session_id)].aggregate(lastWeightsPipeline))

    # calculating growth from last snapshot in weight and amount of texts
    try:
        weight_growth_abs = round(lastTwoSnapshots[0]["weight"] - lastTwoSnapshots[1]["weight"], 2)
        weight_growth_rel = round(weight_growth_abs / lastTwoSnapshots[1]["weight"] * 100, 2)
       
    except:
         weight_growth_rel = "0.00"
         weight_growth_abs = "0"
    try:
        text_ids_growth_abs = len(lastTwoSnapshots[0]["textids"]) - len(lastTwoSnapshots[1]["textids"])
        text_ids_growth_rel = round(text_ids_growth_abs / len(lastTwoSnapshots[1]["textids"]) * 100, 2)
    except:
        text_ids_growth_rel = "0.00"
        text_ids_growth_abs = "0"
    
    # fetching all the origin texts with aggregate mongocurrent_app.config['db'] pipeline
    micro_cluster = lastTwoSnapshots[0]
    text_id_list = micro_cluster["textids"]
    cluster_weight = micro_cluster["weight"]
    textsPipeline = [
        {"$match": {"general.text_id": {"$in": text_id_list}}},
        {"$group": {"_id": "null", "text_objects": {"$push": "$general"}}}
    ]

    texts_data = list(current_app.config['db']["texts_{}".format(cluster_session_id)].aggregate(
        textsPipeline))[0]["text_objects"]

    cluster_meta = {"texts_number": len(
        texts_data), "cluster_weight": cluster_weight,  "weight_growth_abs": weight_growth_abs, "weight_growth_rel": weight_growth_rel, "text_ids_growth_abs": text_ids_growth_abs, "text_ids_growth_rel": text_ids_growth_rel,  "texts_data": texts_data}
    return_json = json.dumps(cluster_meta, default=str)
    return return_json


# route for requesting trending topics on twitter
@urls_blueprint.route('/getTwitterTrendsByLocation', methods=['GET'])
def get_trends():
    # parsing query parameters
    woeid = request.args.get('woeid')
    n = int(request.args.get('n'))
    trending = helpers.trending_topics(woeid, n)
    jsonTrending = json.dumps(trending)
    return json.dumps(jsonTrending)


# route for requesting termfreq of all termfreq of micro-cluster of specific id
@urls_blueprint.route('/getTermFrequencies', methods=['GET'])
def getTermFrequencies():
    # parsing query paramters
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    clusterId = request.args.get('clusterId')

    # checking type of timetampt: datetime for realtimefadin or else int
    typePipeline = [
        {"$project": {"timestamp_type" : { "$type": "$timestamp" }}},
        {"$limit": 1},
        ]
    timestamp_type = list(current_app.config['db']["mc_{}".format(cluster_session_id)].aggregate(typePipeline))[0]["timestamp_type"]

     # transform string to int if not realtime faded and to datetime otherwise
    if timestamp_type == "int":
        timestamp_datetime = int(timestamp_string)
    else:
        timestamp_datetime = pd.to_datetime(timestamp_string)

    # requesting termfreq from mongodb
    termFreqDict = current_app.config['db']["mc_{}".format(cluster_session_id)].find_one(
        {"timestamp": timestamp_datetime, "id": int(clusterId)})["tf"]

    termDictList = []
    # structuring trends in table form for frontend
    for term, termValue in termFreqDict.items():
        termDict = {}
        termDict["termcolumn"] = term
        termDict["freqcolumn"] = termValue["tf"]
        termDictList.append(termDict)
    termFreqString = json.dumps(termDictList)
    return termFreqString


# route for requesting highest weightes micro-clusters id above a specific timestamp
@urls_blueprint.route('/getMaxWeightClusterIds', methods=['GET'])
def getMaxWeightClusterIds():
    # parsing query parameters
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    max_to_return = int(request.args.get('max'))
    rtf = request.args.get('rtf')

    # checking realtimefaded 
    if rtf == "true":
        if timestamp_string == "0":
            timestamp_string = "1970-01-01T00:00:00.0"
        timestamp_datetime = pd.to_datetime(timestamp_string)
    else:
        timestamp_datetime = int(timestamp_string)

    # mongodb aggregation pipeline for max weight microclusters
    pipelineMax = [
        {"$match": {"timestamp": {"$gt": timestamp_datetime}}},
        {"$group": {"_id": "$id", "last_updated": {"$last": "$timestamp"},
                    "current_weight": {"$last": "$weight"}}},
        {"$sort": {"current_weight": -1}},
        {"$limit": max_to_return}
    ]

    maxClusters = current_app.config['db']["mc_{}".format(cluster_session_id)].aggregate(pipelineMax)
    maxClusterIds = [d['_id'] for d in maxClusters]
    maxClusterIdsString = json.dumps(maxClusterIds)
    return maxClusterIdsString


# route for requesting all weight-time data of list of microcluster ids--> creating new trace data in frontend
@urls_blueprint.route('/getFullTimeWeightSeries', methods=['GET'])
def getWeightTimeSeries():
    # parsing query parameters
    cluster_session_id = request.args.get('session')
    cluster_id_list = request.get_json()["cluster-ids"]
    timestamp_min = request.args.get('minTimestamp')
    rtf = request.args.get('rtf')

    # limit returned number of weight-time data points per micro-cluster --> shorter trace
    if timestamp_min is not None:
        timestamp_min = int(timestamp_min)

        # checking for rtf
        if rtf == "true":
            timestamp_min_timestamp = datetime.fromtimestamp(
                timestamp_min).timestamp()
            
            timestamp_min_datetime = datetime.fromtimestamp(current_app.config['db']["mc_{}".format(cluster_session_id)].find_one(
            {"$query": {}, "$orderby": {"$natural": -1}})["timestamp"].timestamp() - timestamp_min_timestamp)
        else:
            
            timestamp_min_timestamp = timestamp_min
            timestamp_min_datetime = current_app.config['db']["mc_{}".format(cluster_session_id)].find_one(
            {"$query": {}, "$orderby": {"$natural": -1}})["timestamp"] - timestamp_min_timestamp

        # mongodb pipeline for requesting time weight series greater/equal than timestampmin
        timeWeigtSeriesPipeline = [
            {"$match": {"$expr" : { "$and": [{"$in":["$id", cluster_id_list]},
                        {"$gte": ["$timestamp", timestamp_min_datetime]}]}}},
            {"$group": {"_id": "$id", "weight_serie": {"$push": "$weight"},
                        "timestamp_serie": {"$push": "$timestamp"}}}
        ]
        timeWeightSeries = list(
            current_app.config['db']["mc_{}".format(cluster_session_id)].aggregate(timeWeigtSeriesPipeline))

        timeWeightSeriesString = json.dumps(timeWeightSeries, default=str)
    else:
        # mongodb pipeline for requesting complete time weight series greater/equal if no timestampmin given
        timeWeigtSeriesPipeline = [
            {"$match": {"id": {"$in": cluster_id_list}}},
            {"$group": {"_id": "$id", "weight_serie": {"$push": "$weight"},
                        "timestamp_serie": {"$push": "$timestamp"}}}
        ]
        timeWeightSeries = list(
            current_app.config['db']["mc_{}".format(cluster_session_id)].aggregate(timeWeigtSeriesPipeline))

        timeWeightSeriesString = json.dumps(timeWeightSeries, default=str)

    return timeWeightSeriesString


# route for requesting the latest weight-time updates of a list of microcluster ids and a defined timestamp --> appending new trace data in frontend
@urls_blueprint.route('/getLatestTimeWeightSeries', methods=['GET'])
def getNewClusterDataSince():
    # parsing query parameters
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    rtf = request.args.get('rtf')

    # checking for rtf( ealtiemfading)
    if rtf =="true":
        timestamp_datetime = datetime.strptime(
            timestamp_string, "%Y-%m-%dT%H:%M:%S.%f")
    else:
        timestamp_datetime = int(timestamp_string)

    cluster_id_list = request.get_json()["cluster-ids"]

     # mongodb pipeline for requesting partial time weight series greater than timestamp
    timeWeigtSeriesSincePipeline = [
        {"$match": {"$expr" : { "$and": [{"$in":["$id", cluster_id_list]},
                        {"$gt": ["timestamp", timestamp_datetime]}]}}},
        {"$group": {"_id": "$id", "weight_serie": {"$push": "$weight"},
                    "timestamp_serie": {"$push": "$timestamp"}}}
    ]

    timeWeightSeries = list(
        current_app.config['db']["mc_{}".format(cluster_session_id)].aggregate(timeWeigtSeriesSincePipeline))

    timeWeightSeriesString = json.dumps(timeWeightSeries, default=str)
    return timeWeightSeriesString


# route for checking if new microcluster snapshots were inserted into mongodb's session collection
@urls_blueprint.route('/updated', methods=['GET'])
def updated():
    # parsing query parameters
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')

    # checking type of timestamp: datetime for realtimefading or else int
    typePipeline = [
        {"$project": {"timestamp_type" : { "$type": "$timestamp" }}},
        {"$limit": 1},
        ]
    
    timestamp_type = list(current_app.config['db']["mc_{}".format(cluster_session_id)].aggregate(typePipeline))[0]["timestamp_type"]
    
    # transform string to int if not realtime faded and to datetime otherwise
    if timestamp_type == "int":
        timestamp_datetime = int(timestamp_string)
    else:
        if timestamp_string == "0":
            timestamp_string = "1970-01-01T00:00:00.0"
        timestamp_datetime = pd.to_datetime(timestamp_string)
    try:
        newest_timestamp_datetime = list(current_app.config['db']["mc_{}".format(cluster_session_id)].find(
        ).limit(1).sort([("$natural", -1)]))[0]["timestamp"]
    except:
        newest_timestamp_datetime = timestamp_datetime

    # check for updates --> higher timestamp
    if newest_timestamp_datetime > timestamp_datetime:
        updated = True
    else:
        updated = False
    # setting rtf (realtimefading) info for correct displaying of datatypes on the frontend 
    if timestamp_type == "int":
        updated_string = json.dumps(
            {"updated": updated, "last_update": newest_timestamp_datetime, "rtf": "false"})
    else:
        updated_string = json.dumps(
            {"updated": updated, "last_update": datetime.strftime(newest_timestamp_datetime, "%Y-%m-%dT%H:%M:%S.%f"), "rtf": "true"})
    return updated_string


@urls_blueprint.route('/getTwitterMeta', methods=['GET'])
def computeTwitterMetaData():
    # parsing query parameters
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    timestamp_datetime = pd.to_datetime(timestamp_string)

    clusterId = request.args.get('clusterId')

    # computing tweetIds of micro-cluster and fetching twitter meta from mongodb
    tweet_ids = helpers.getTweetIds(cluster_session_id, timestamp_datetime, clusterId)
    tweets_dict_list = helpers.getTwitterMeta(cluster_session_id, tweet_ids)
    users_meta_list = []

    # defining important storages for tweepy statuses 
    users = set()
    lang = {}
    verified_abs = 0
    acc_ages = []
    default_image_abs = 0
    default_profile_abs = 0
    friends_aggr = []
    followers_aggr = []
    liked_aggr = []
    statuses_aggr = []

    #iterating over all requestes tweepy status objects and structuring them for overview table and aggregated display
    for tweet_dict in tweets_dict_list:
        user_id = tweet_dict["user"]["id"]

        # adding users information, if not already existing
        if not user_id in users:
            username_screen = tweet_dict["user"]["screen_name"]
            friends = tweet_dict["user"]["friends_count"]
            friends_aggr.append(friends)
            followers = tweet_dict["user"]["followers_count"]
            followers_aggr.append(followers)
            liked = tweet_dict["user"]["favourites_count"]
            liked_aggr.append(liked)
            statuses_user = tweet_dict["user"]["statuses_count"]
            statuses_aggr.append(statuses_user)

            verified = tweet_dict["user"]["verified"]
            default_image = tweet_dict["user"]["default_profile_image"]
            default_profile = tweet_dict["user"]["default_profile"]
            if verified:
                verified_abs += 1
            if default_image:
                default_image_abs += 1
            if default_profile:
                default_profile_abs += 1

            
            acc_age = tweet_dict["user"]["created_at"]
            acc_ages.append(acc_age)

            statuses_in_cluster = sum(tweet_dict["user"]["id"] == user_id for tweet_dict in tweets_dict_list)
            # creating row for frontend user table, is also final user meta
            user_meta = {"username": "[{}](https://www.twitter.com/{})".format(username_screen, username_screen), "acc_age": acc_age, "statuses_in_cluster": statuses_in_cluster, "statuses": statuses_user, "verified": verified, "default_image": default_image, "default_profile": default_profile, "friends": friends, "followers": followers, "liked": liked}
            users_meta_list.append(user_meta)

        users.add(user_id)

        # collecting lang information
        if tweet_dict["lang"] != None:
            try:
                lang[tweet_dict["lang"]] = lang[tweet_dict["lang"]] + 1
            except:
                lang[tweet_dict["lang"]] = 1

    users_in = len(list(users))
    verified_rel = verified_abs / users_in

    # final returning twitter aggregated meta dict
    tweet_meta = {"users_in": users_in, "verified_abs": verified_abs, "verified_rel": verified_rel, "lang": lang, "acc_ages": acc_ages,
                  "default_image": default_image_abs, "default_profile": default_profile_abs, "friends": friends_aggr, "followers": followers_aggr, "liked": liked_aggr, "statuses": statuses_aggr}
    users_meta = users_meta_list
    return_dict = json.dumps({"tweet_meta" : tweet_meta, "users_meta" : users_meta})
    return return_dict


# route for requesting global micro-cluster snapshot data of specific timestamp
@urls_blueprint.route('/getGlobalClusterData', methods=['GET'])
def getGlobalClusterData():
    # parsing query parameters
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    
    # checking type of timetampt: datetime for realtimefadin or else int
    typePipeline = [
        {"$project": {"timestamp_type" : { "$type": "$timestamp" }}},
        {"$limit": 1},
        ]
    timestamp_type = list(current_app.config['db']["mc_{}".format(cluster_session_id)].aggregate(typePipeline))[0]["timestamp_type"]

    if timestamp_type == "int":
        timestamp_datetime = int(timestamp_string)
    else:
        timestamp_datetime = pd.to_datetime(timestamp_string)

    # mongodb aggegration pipeline for boxplot data of the frontend -> users, followers, likes...
    clusterWeightBoxplotPipeline = [
        {"$match": {"timestamp":  timestamp_datetime}},
        {"$group": {"_id": "null", "global_weights": {"$push": "$weight"}}}
    ]
    
    # fetching data for weight distribution
    cluster_weights = list(
        current_app.config['db']["mc_{}".format(cluster_session_id)].aggregate(clusterWeightBoxplotPipeline))[0]["global_weights"]
    return_dict = json.dumps({"cluster_number": len(cluster_weights), "cluster_weights": cluster_weights})
    return return_dict


# route for requestion termfreq and weights of top n microcluster
@urls_blueprint.route('/getTopClusterData', methods=['GET'])
def getTopClusterData():
    # parsing query parameters
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    n_tokens = request.args.get("n_tokens", 5, type=int)
    
    # checking type of timetampt: datetime for realtimefadin or else int
    typePipeline = [
        {"$project": {"timestamp_type" : { "$type": "$timestamp" }}},
        {"$limit": 1},
        ]
    timestamp_type = list(current_app.config['db']["mc_{}".format(cluster_session_id)].aggregate(typePipeline))[0]["timestamp_type"]

    if timestamp_type == "int":
        timestamp_datetime = int(timestamp_string)
    else:
        timestamp_datetime = pd.to_datetime(timestamp_string)

    # defining number of returning microclusters
    max_to_return = int(request.args.get('max'))

    # pipeline for requesting the microcluster from mongodb
    pipelineTop = [
        {"$match": {"timestamp":  timestamp_datetime}},
        {"$sort": {"weight": -1}},
        {"$limit": max_to_return}
    ]

    maxClusters = list(
        current_app.config['db']["mc_{}".format(cluster_session_id)].aggregate(pipelineTop))
    mc_dict_list = []
    max = 0
    
    # iterating over all fetched microclusters and reading in their weight, tf and ids
    for microcluster in maxClusters:
        cluster_id = microcluster["id"]
        weight = microcluster["weight"]

        term_freq_dict = microcluster["tf"]

        term_weight_list = []
        for term, termValue in term_freq_dict.items():
            term_weight_list.append(
                {"token": term, "weight": round(termValue["tf"])})

        # limiting the number of terms
        if len(term_weight_list) > max:
            max = len(term_weight_list)
            maxid = cluster_id
        term_weight_list.sort(key=itemgetter('weight'), reverse=True)

        # structuring the results in table form for frontend
        microClusterDict = {}
        microClusterDict["idcolumn"] = cluster_id
        microClusterDict["weightcolumn"] = round(weight, 3)
        microClusterDict["termcolumn"] = term_weight_list[0:(
            min(n_tokens, len(term_weight_list)+1))]
        mc_dict_list.append(microClusterDict)

    return_dict = json.dumps(mc_dict_list)
    return return_dict
