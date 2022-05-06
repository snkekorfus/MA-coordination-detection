from flask import Flask
from flask_cors import CORS
from flask import request
from datetime import datetime
import os
import uuid
from textClustPy import textclust
from textClustPy import Preprocessor
from textClustPy import CSVInput
from textClustPy import TwitterInput
from textClustPy import JsonTXTInput
import json
import pymongo
from pymongo import MongoClient
import uuid
import tweepy
from operator import itemgetter
import pandas as pd
from celery import Celery
from celery.app.control import Control
import config_loader
from functools import lru_cache
import numpy as np

DEBUG = True
ALLOWED_EXTENSIONS = {'json'}

# flask configuration, some random secret key is generated to secure the client session
app = Flask(__name__)
app.secret_key = uuid.uuid4().hex
app.config.from_object(__name__)

# CORS, allowing access from outside
CORS(app, resources={r'/*': {'origins': '*'}})

# connecting to MongoDB, which exists in docker network
#  PORT 27017 defined in docker-compose.yml
MONGODB_HOST = 'db'
MONGODB_PORT = 27017
connection = MongoClient(MONGODB_HOST, MONGODB_PORT)

db = connection["textclustDB"]
tweepyCll = db["tweets4"]

# celery config, PORT 6379 defined in docker-compose.yml
app.config['CELERY_BROKER_URL'] = 'redis://redis:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://redis:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

# Twitter API secret access, requeired for Twitter API access!
with open("twitter_access.json") as f:
    twitter_auth = json.load(f)

api_key = twitter_auth["api_key"]
api_secret = twitter_auth["api_secret"]
access_token = twitter_auth["access_token"]
access_secret = twitter_auth["access_secret"]

# Load config
config = config_loader.load_config()

# textclust suspicious clusters
suspicious_clusters = []


survey = db["survey"]
survey.create_index([("id", pymongo.ASCENDING)])



@app.route('/checksurvey',methods=["GET"])
def check_survey():
    session_id = request.args.get('user_session')
    #requesting session meta from mongodb
    cluster_session_meta = list(db["survey"].find(
        {"session": session_id}))

    print(cluster_session_meta)
    if len(cluster_session_meta) > 0:
        return json.dumps("True")
    else:
        return json.dumps("False")



@app.route('/submitsurvey',methods=["POST"])
def submit_survey():
    data= request.get_json()
    print(data)
    db["survey"].insert_one(data)
    return json.dumps("True")

# checking if clustersession is already in use and fetches meta data for overtaking running session
@app.route('/validateClusterSessionId', methods=['GET'])
def check_session_id():
    cluster_session_id = request.args.get('session')

    #requesting session meta from mongodb
    cluster_session_meta = list(db["textclust_sessions_meta"].find(
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
#@app.route('/startTextClustSession', methods=['GET', 'POST'])
def start_clust(preprocessing, inputSource, clustSettings):
    # reading requests post data
    clustSettings["embedding_verification"] = False

    session_id=str(uuid.uuid4())
    config = {
        "textclust": {
            "config": clustSettings
        },
        "preprocessing": preprocessing,
        "inputSource": inputSource,
        "cluster_session_id": session_id
    }

    # starting the actual textClust clustering process, task is pushed into celery task query
    run_textclust.delay(config)
    return "CREATED"

# route for stopping textClust session
@app.route('/stopTextClustSession', methods=['GET'])
def stop_clust():
    cluster_session_id = request.args.get('session')
    currentControl = Control(app=celery)

    # fetching celery task id for revoking task
    task_id = list(db["textclust_sessions_meta"].find(
        {"cluster_session_id": cluster_session_id}))[0]["celery_task_id"]
    currentControl.revoke(task_id, terminate=True)
    end_date = datetime.utcnow()

    # updating session meta to end state
    db["{}".format("textclust_sessions_meta")].find_one_and_update(
        {"cluster_session_id":  cluster_session_id, "ended": False}, {"$set": {"end_date": end_date, "ended": True}})
    return "STOPPED"

# celery task, which runs textClust algorithm
@celery.task(bind=True)
def run_textclust(self, config):

    # callback function for inserting text in mongodb
    def insert_input_db(text_id, time, text, mode_object):

        text_meta = {}
        text_meta["mode"] = input["mode"]
        text_meta["general"] = {"text_id": text_id, "time": time, "text": text}
        text_meta["specific"] = json.loads(mode_object)
        text_coll.insert_one(text_meta)

    # callback function for inserting microcluster snapshots in mongodb
    def insert_microcluster_db_single(clust):
        warmup = 200
        microclusters = list(clust["microclusters"].values())
        timestamp = datetime.utcnow()
        documentList = []

        sd_change = 0
        mean_change= np.mean([x.deltaweight for x in microclusters])

        # structuring microcluster attributes in dict
        for microcluster in microclusters:
            temp_dict = {}
            temp_dict["id"] = microcluster.id
            # checking for realtimefading: if yes --> datetime type else: --> int type
            if textclust_config["realtimefading"]:
                temp_dict["timestamp"] = datetime.fromtimestamp(
                    microcluster.time)
            else:
                temp_dict["timestamp"] = microcluster.time
            temp_dict["tf"] = microcluster.tf
            temp_dict["weight"] = microcluster.weight
            temp_dict["time"] = microcluster.time
            temp_dict["textids"] = microcluster.textids
            documentList.append(temp_dict)
            sd_change += (microcluster.deltaweight-mean_change)**2
        
        sd_change = sd_change / (len(microclusters)-1)
        sd_change = np.sqrt(sd_change)
       
        if sd_change and warmup < clust["n"]:
            global suspicious_clusters
            suspicious_clusters.extend([x.id for x in microclusters if (x.deltaweight-mean_change) > sd_change*6])
            suspicious_clusters = list(set(suspicious_clusters))
        
        # updating session meta to end state
        db["{}".format("textclust_sessions_meta")].find_one_and_update(
        {"cluster_session_id":  cluster_session_id}, {"$set": {"suspicious": suspicious_clusters}})


        mc_coll.insert_many(documentList)

    # reading given textClust configuration settings
    cluster_session_id = config["cluster_session_id"]
    textclust_config = config["textclust"]["config"]
    preprocessing = config["preprocessing"]

    # reading given preprocessor configuration settings
    max_grams = int(preprocessing["max_grams"])
    language = preprocessing["language"]
    stopword_removal = preprocessing["stopword_removal"]
    stemming = preprocessing["stemming"]
    punctuation = preprocessing["punctuation"]
    hashtag = preprocessing["hashtag"]
    username = preprocessing["username"]
    url = preprocessing["url"]
    exclude_tokens = preprocessing["exclude_tokens"]

    # reading given clust configuration settings
    _lambda = textclust_config["lambda"]
    termfading = textclust_config["termfading"]
    tgap = textclust_config["tgap"]
    radius = textclust_config["radius"]
    realtimefading = textclust_config["realtimefading"]
    micro_distance = textclust_config["micro_distance"]
    macro_distance = textclust_config["macro_distance"]
    model = textclust_config["model"]
    idf = textclust_config["idf"]
    num_macro = textclust_config["num_macro"]
    minWeight = textclust_config["minWeight"]
    embedding_verification = textclust_config["embedding_verification"]
    auto_r = textclust_config["auto_r"]
    auto_merge = textclust_config["auto_merge"]
   
    # creating preprocessor and clust objects
    preprocessor = Preprocessor(max_grams=max_grams, language=language, stopword_removal=stopword_removal,
                                stemming=stemming, punctuation=punctuation, hashtag=hashtag, username=username, url=url, exclude_tokens = exclude_tokens)

    clust = textclust(_lambda=_lambda, termfading=termfading, tgap=tgap, radius=radius, realtimefading=realtimefading, micro_distance=micro_distance, macro_distance=macro_distance,
                      model=model, idf=idf, num_macro=num_macro, minWeight=minWeight, embedding_verification=embedding_verification, auto_r=auto_r, auto_merge=auto_merge, callback=insert_microcluster_db_single)

    # reading given input configuration settings
    input = config["inputSource"]
    meta = {
        "cluster_session_id": cluster_session_id,
        "input_source": input,
        "celery_task_id": self.request.id,
        "started": True,
        "ended": False,
        "start_date": datetime.utcnow(),
        "end_date": None
    }

    # creating indexes for cluster sessions collections
    text_coll = db["texts_{}".format(cluster_session_id)]
    text_coll.create_index([("general.text_id", pymongo.DESCENDING)])
    text_coll.create_index([("general.text_id", pymongo.DESCENDING),("general.time", pymongo.DESCENDING)])
    text_coll.create_index([("general.time", pymongo.DESCENDING)])
    text_coll.create_index([("specific.user.id", pymongo.ASCENDING),("general.time", pymongo.DESCENDING)])
    text_coll.create_index([("general.time", pymongo.DESCENDING), ("general.text_id", pymongo.DESCENDING)])
    
    mc_coll = db["mc_{}".format(cluster_session_id)]
    mc_coll.create_index([("id", pymongo.DESCENDING)])
    mc_coll.create_index([("id", pymongo.DESCENDING), ("timestamp", pymongo.DESCENDING)])
    mc_coll.create_index([("timestamp", pymongo.DESCENDING)])
    mc_coll.create_index([("timestamp", pymongo.ASCENDING), ("id", pymongo.ASCENDING)])
    mc_coll.create_index([("weight", pymongo.DESCENDING), ("id", pymongo.DESCENDING), ("timestamp", pymongo.DESCENDING)])
    mc_coll.create_index([("weight", pymongo.DESCENDING), ("timestamp", pymongo.DESCENDING)])
    
    


    # csv input related configuration
    if input["mode"] == "CSV":
        csv_path = os.path.join("csvTemp", "csv_{}".format(cluster_session_id))
        delimeter = input["delimeter"].encode().decode('unicode-escape')
        quotechar = input["quotechar"].encode().decode('unicode-escape')
        newline = input["newline"].encode().decode('unicode-escape')
        col_id = int(input["colid"])
        col_time = int(input["coltime"])
        col_text = int(input["coltext"])
        timeformat = input["timeformat"].encode().decode('unicode-escape')

        # running the actual csv input instance with all parameters
        db["textclust_sessions_meta"].insert_one(meta)
        csv_input_instance = CSVInput(csvfile=csv_path, textclust=clust, preprocessor=preprocessor, delimiter=delimeter,
                                      quotechar=quotechar, newline=newline, col_id=col_id, col_time=col_time, col_text=col_text, col_label=2, callback=insert_input_db, timeformat=timeformat)
        csv_input_instance.run()

    # twitter input related configuration
    if input["mode"] == "TWT":
        terms = input["terms"]
        languages = input["languages"]
        # running the actual twt input instance with all parameters
        db["textclust_sessions_meta"].insert_one(meta)
        TwitterInput(api_key, api_secret, access_token, access_secret, textclust=clust,
                     preprocessor=preprocessor, terms=terms, languages=[languages], callback=insert_input_db)

    if input["mode"] == "JSON":
        print("Started JSON input mode")
        db["textclust_sessions_meta"].insert_one(meta)
        language = input["languages"]
        JsonTXTInput(["/data/tweets-2022-02-24.txt", "/data/tweets-2022-02-25.txt"], lang=language, textclust=clust,
                     preprocessor=preprocessor, callback=insert_input_db)

        

# route for fetching prev cluster session meta data
@app.route('/getPrevClusterSessions', methods=['GET', 'POST'])
def list_previous_sessions():

    # reqeusting all meta session infos from mongodb
    prev_sessions_meta = []
    all_past_sessions = list(db["textclust_sessions_meta"].find({}))

    # structuring fetched data from sessions in list of dict
    for session in all_past_sessions:
        mode = session["input_source"]["mode"]
        terms = session["input_source"]["stream_name"]
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
            data_beginning = pd.to_datetime(db["texts_{}".format(session["cluster_session_id"])].find_one()[
                "general"]["time"])
            if session["ended"]:
                data_end = pd.to_datetime(db["texts_{}".format(session["cluster_session_id"])].find_one(
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
        number_texts = db["texts_{}".format(
            session["cluster_session_id"])].count()

        temp_dict = {"id": session["cluster_session_id"], "mode": mode, "terms": terms, "clustering_date": clustering_date, "running_time": running_time,
                     "status": status, "data_beginning": data_beginning, "data_end": data_end, "data_time_horizont": data_time_horizont, "number_texts": number_texts}
        prev_sessions_meta.append(temp_dict)

    return_json = json.dumps(prev_sessions_meta, default=str)
    return return_json

# route for uploading CSV to csv folder
@app.route('/uploadCSV', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        cluster_session_id = request.args.get('session')
        csv_file = request.files['file']

        csv_path = os.path.join("./csvTemp", "csv_{}".format(cluster_session_id))
        csv_file.save(csv_path)
    return "True"

# route for requesting micro-cluster meta data
@app.route('/getClusterMeta', methods=['GET'])
def get_cluster_meta():
    # parsing query paramters session id, clsuter id and timestamp as string
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    cluster_id = request.args.get('clusterId')
    pw = request.args.get('pw')
    
    # checking type of timestamp: datetime for realtimefadin or else int
    timestamp_datetime = check_timestamp_type(cluster_session_id, timestamp_string)

    # mongodb aggregate pipeline for the last two microcluster snapshots
    lastWeightsPipeline = [
        {"$match": {"id": int(cluster_id), "timestamp":{"$lte": timestamp_datetime}}},
        {"$sort": {"timestamp": -1}},
        {"$project": {"_id": 0, "weight": 1, "timestamp" : 1, "textids": 1}},
        {"$limit": 2}
    ]

    lastTwoSnapshots = list(db["mc_{}".format(cluster_session_id)].aggregate(lastWeightsPipeline))

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

    # fetching all the origin texts with aggregate mongodb pipeline
    micro_cluster = lastTwoSnapshots[0]
    text_id_list = micro_cluster["textids"]
    cluster_weight = micro_cluster["weight"]

    cluster_meta = {"texts_number": len(text_id_list), "cluster_weight": cluster_weight,  "weight_growth_abs": weight_growth_abs, "weight_growth_rel": weight_growth_rel, "text_ids_growth_abs": text_ids_growth_abs, "text_ids_growth_rel": text_ids_growth_rel, "text_id_list": text_id_list}
    return_json = json.dumps(cluster_meta, default=str)
    return return_json

@app.route('/getTextData', methods=['GET'])
def get_cluster_texts():
    # parsing query paramters session id, clsuter id and timestamp as string
    cluster_session_id = request.args.get('session')
    text_id_list = request.json.get('text_id_list')
    pw = request.args.get('pw')
    page_current = int(request.args.get('page_current'))

    rtf = "true"
 
    timestamp_min = config["WINDOW_SIZE"]

    if config["TIME_UNIT"] == "days":
        timestamp_min = 60 * 60 * 24 * timestamp_min
    elif config["TIME_UNIT"] == "hours":
        timestamp_min = 60 * 60 * timestamp_min
    elif config["TIME_UNIT"] == "min":
        timestamp_min = 60 * timestamp_min

    # checking for rtf
    if rtf == "true":
        timestamp_min_datetime = datetime.fromtimestamp(datetime.now().timestamp() - timestamp_min)
    else:
        timestamp_min_timestamp = datetime.now().timestamp() - timestamp_min

    if not config["ANALYSIS"]:
        text_objects = db[f"texts_{cluster_session_id}"].find(
            {
                "$and": [
                    {"general.text_id": {"$in": text_id_list}},
                    {"general.time": {"$gte": timestamp_min_datetime}}
                ]
            }, 
            projection={
                "general": 1,
                "profilePicture": "$specific.user.profile_image_url_https"
            },
            sort=[("general.text_id", -1)]).skip(page_current * 8).limit(8)
    else:
        text_objects = db[f"texts_{cluster_session_id}"].find(
            {
                "general.text_id": {"$in": text_id_list}
            }, 
            projection={
                "general": 1,
                "profilePicture": "$specific.user.profile_image_url_https"
            },
            sort=[("general.text_id", -1)]).skip(page_current * 8).limit(8)

    texts_data = []
    for text in list(text_objects):
        temp = text['general']
        temp['profilePicture'] = text['profilePicture']
        texts_data.append(temp)

    if pw == "J2be9jPrnJSmEScF":
        for text in texts_data:
            text["text"] = f"[{text['text']}](https://twitter.com/dummyUser/status/{text['text_id']})"
            text["profilePicture"] = f"![]({text['profilePicture']})"
        return {"text_data": texts_data}
    else:
        return None

# function for requesting trending topics on twitter
def trending_topics(woedi, n=15):
    auth = tweepy.AppAuthHandler(api_key, api_secret)  # calling the api
    api = tweepy.API(auth)

    # iterating over results of woeid related trendes fetched from official Twitter API
    trends = api.trends_place(woedi)[0]["trends"]
    for dict in trends:
        for k, v in dict.items():
            if k == "tweet_volume" and v == None:
                dict[k] = 0
    # sorting results after status volume
    trendsVolumeSorted = sorted(
        trends, key=itemgetter('tweet_volume'), reverse=True)
    trendsNameVolumeList = []
    # structuring trends in table form for frontend
    for i in range(0, n):
        name = trendsVolumeSorted[i]["name"]
        volume = trendsVolumeSorted[i]["tweet_volume"]
        trendsNameVolumeList.append(
            {"termcolumn": name, "tweetcolumn": volume})
    return trendsNameVolumeList

# route for requesting trending topics on twitter
@app.route('/getTwitterTrendsByLocation', methods=['GET'])
def get_trends():
    # parsing query parameters
    woeid = request.args.get('woeid')
    n = int(request.args.get('n'))
    trending = trending_topics(woeid, n)
    jsonTrending = json.dumps(trending)
    return json.dumps(jsonTrending)

# route for requesting termfreq of all termfreq of micro-cluster of specific id
@app.route('/getTermFrequencies', methods=['GET'])
def getTermFrequencies():
    # parsing query paramters
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    clusterId = request.args.get('clusterId')

    # checking type of timetampt: datetime for realtimefadin or else int
    timestamp_datetime = check_timestamp_type(cluster_session_id, timestamp_string)

    # requesting termfreq from mongodb
    termFreqDict = db["mc_{}".format(cluster_session_id)].find_one(
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
@app.route('/getMaxWeightClusterIds', methods=['GET'])
def getMaxWeightClusterIds():
    # parsing query parameters
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    max_to_return = int(request.args.get('max', 10))
    rtf = request.args.get('rtf')

    # checking realtimefaded 
    if rtf == "true":
        if timestamp_string == "0":
            timestamp_string = "1970-01-01T00:00:00.0"
        timestamp_datetime = pd.to_datetime(timestamp_string)
    else:
        timestamp_datetime = int(timestamp_string)

    # TODO: Add analysis if statement

    # mongodb aggregation pipeline for max weight microclusters
    #pipelineMax = [
    #    {"$match": {"timestamp": {"$gt": timestamp_datetime}}},
    #    {"$group": {"_id": "$id", "last_updated": {"$last": "$timestamp"},
    #                "current_weight": {"$last": "$weight"}}},
    #    {"$sort": {"current_weight": -1}},
    #    {"$limit": max_to_return}
    #]

    # loop to get max weight cluster
    nin = []
    for _ in range(0, max_to_return):
        query = db["mc_{}".format(cluster_session_id)].find_one({"$and": [{"id": {"$nin": nin}}, {"timestamp": {"$gt": timestamp_datetime}}]}, sort=[('weight', -1)], projection={"id":1})
        if query is None:
            break
        nin.append(query['id'])

    maxClusterIdsString = json.dumps(nin)
    return maxClusterIdsString


# route for requesting highest weightes micro-clusters id above a specific timestamp
@app.route('/getSuspiciousIds', methods=['GET'])
def getSuspiciousIds():
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    max_to_return = int(request.args.get('max', 10))
    rtf = request.args.get('rtf')

    # checking realtimefaded 
    if rtf == "true":
        if timestamp_string == "0":
            timestamp_string = "1970-01-01T00:00:00.0"
        timestamp_datetime = pd.to_datetime(timestamp_string)
    else:
        timestamp_datetime = int(timestamp_string)
    
    cluster_session_meta = list(db["textclust_sessions_meta"].find(
        {"cluster_session_id": cluster_session_id}))
    
    nin = []
    for _ in range(0, max_to_return):
        query = db["mc_{}".format(cluster_session_id)].find_one({"$and": [{"id": {"$nin": nin}}, {"id": {"$in": cluster_session_meta[0]["suspicious"]}}, {"timestamp": {"$gt": timestamp_datetime}}]}, sort=[('weight', -1)], projection={"id":1})
        if query is None:
            break
        nin.append(query['id'])

    return json.dumps(nin)

# route for requesting all weight-time data of list of microcluster ids--> creating new trace data in frontend
@app.route('/getFullTimeWeightSeries', methods=['GET'])
def getWeightTimeSeries():
    # parsing query parameters
    cluster_session_id = request.args.get('session')
    cluster_id_list = request.get_json()["cluster-ids"]
    rtf = request.args.get('rtf')

    print(f"Full Time Weight series called. id_list: \n {cluster_id_list}", flush=True)

    # limit returned number of weight-time data points per micro-cluster --> shorter trace
    if config["WINDOW_SIZE"] is not None and not config["ANALYSIS"]:
        timestamp_min = config["WINDOW_SIZE"]

        if config["TIME_UNIT"] == "days":
            timestamp_min = 60 * 60 * 24 * timestamp_min
        elif config["TIME_UNIT"] == "hours":
            timestamp_min = 60 * 60 * timestamp_min
        elif config["TIME_UNIT"] == "min":
            timestamp_min = 60 * timestamp_min

        # checking for rtf
        if rtf == "true":
            timestamp_min_datetime = datetime.fromtimestamp(datetime.now().timestamp() - timestamp_min)
        else:
            timestamp_min_datetime = datetime.now().timestamp() - timestamp_min

        print(f"timestamp_min: {timestamp_min_datetime}", flush=True)

        # mongodb pipeline for requesting time weight series greater/equal than timestampmin
        timeWeigtSeriesPipeline = [
            {"$match": {"$expr" : { "$and": [{"$in":["$id", cluster_id_list]},
                        {"$gte": ["$timestamp", timestamp_min_datetime]}]}}},
            {"$group": {"_id": "$id", "weight_serie": {"$push": "$weight"},
                        "timestamp_serie": {"$push": "$timestamp"}}}
        ]
    else:
        # mongodb pipeline for requesting complete time weight series greater/equal if no timestamp min given
        timeWeigtSeriesPipeline = [
            {"$match": {"id": {"$in": cluster_id_list}}},
            {"$group": {"_id": "$id", "weight_serie": {"$push": "$weight"},
                        "timestamp_serie": {"$push": "$timestamp"}}}
        ]
    
    timeWeightSeries = list(
            db["mc_{}".format(cluster_session_id)].aggregate(timeWeigtSeriesPipeline, maxTimeMS=60000))

    timeWeightSeriesString = json.dumps(timeWeightSeries, default=str)
    print(timeWeightSeriesString, flush=True)
    return timeWeightSeriesString

# route for requesting the latest weight-time updates of a list of microcluster ids and a defined timestamp --> appending new trace data in frontend
@app.route('/getLatestTimeWeightSeries', methods=['GET'])
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
        db["mc_{}".format(cluster_session_id)].aggregate(timeWeigtSeriesSincePipeline))

    timeWeightSeriesString = json.dumps(timeWeightSeries, default=str)
    return timeWeightSeriesString

# route for checking if new microcluster snapshots were inserted into mongodb's session collection
@app.route('/updated', methods=['GET'])
def updated():
    # parsing query parameters
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')

    # checking type of timetampt: datetime for realtimefadin or else int
    timestamp_datetime = check_timestamp_type(cluster_session_id, timestamp_string)

    try:
        newest_timestamp_datetime = list(db["mc_{}".format(cluster_session_id)].find(
        ).limit(1).sort([("$natural", -1)]))[0]["timestamp"]
    except:
        newest_timestamp_datetime = timestamp_datetime

    # check for updates --> higher timestamp
    if newest_timestamp_datetime > timestamp_datetime:
        updated = True
    else:
        updated = False
    # setting rtf (realtimefading) info for correct displaying of datatypes on the frontend 
    if type(timestamp_datetime) == "int":
        updated_string = json.dumps(
            {"updated": updated, "last_update": newest_timestamp_datetime, "rtf": "false"})
    else:
        updated_string = json.dumps(
            {"updated": updated, "last_update": datetime.strftime(newest_timestamp_datetime, "%Y-%m-%dT%H:%M:%S.%f"), "rtf": "true"})
    return updated_string


@app.route('/getTwitterMeta', methods=['GET'])
def computeTwitterMetaData():
    # parsing query parameters
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    timestamp_datetime = pd.to_datetime(timestamp_string)

    clusterId = request.args.get('clusterId')
    pw = request.args.get('pw')

    # computing tweetIds of micro-cluster and fetching twitter meta from mongodb
    tweet_ids = getTweetIds(cluster_session_id, timestamp_datetime, clusterId)
    tweets_dict_list = getTwitterMeta(cluster_session_id, tweet_ids)
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

    aggregated_user_status = [x["statuses_in_cluster"] for x in users_meta_list]
    # final returning twitter aggregated meta dict
    tweet_meta = {"statuses_in_cluster":aggregated_user_status, "users_in": users_in, "verified_abs": verified_abs, "verified_rel": verified_rel, "lang": lang, "acc_ages": acc_ages,
                  "default_image": default_image_abs, "default_profile": default_profile_abs, "friends": friends_aggr, "followers": followers_aggr, "liked": liked_aggr, "statuses": statuses_aggr}
    return_dict = {"tweet_meta" : tweet_meta}
    if pw == "J2be9jPrnJSmEScF":
        return_dict["users_meta"] = users_meta_list
    else :
        return_dict["users_meta"] = None
    return json.dumps(return_dict)

# function for requesting textids as status ids of twitter input session
def getTweetIds(session, timestamp, cluster_id):
    time_id_list = db["mc_{}".format(session)].find_one(
        {"timestamp": timestamp, "id": int(cluster_id)})["textids"]
    return time_id_list

# function for fetching twitter meta from mongodb
def getTwitterMeta(session, tweet_id_list):
    timestamp_min = config["WINDOW_SIZE"]

    if config["TIME_UNIT"] == "days":
        timestamp_min = 60 * 60 * 24 * timestamp_min
    elif config["TIME_UNIT"] == "hours":
        timestamp_min = 60 * 60 * timestamp_min
    elif config["TIME_UNIT"] == "min":
        timestamp_min = 60 * timestamp_min

    timestamp_min_datetime = datetime.fromtimestamp(datetime.now().timestamp() - timestamp_min)

    if not config["ANALYSIS"]:
        tweets = db["texts_{}".format(session)].find(
            {"$and": [
                {"general.text_id":{"$in": tweet_id_list}},
                {"general.time": {"$gte": timestamp_min_datetime}}
            ]})
    else:
        tweets = db["texts_{}".format(session)].find({"general.text_id":{"$in": tweet_id_list}})
       
    tweeypy_stati = []
    for tweet in list(tweets):
        tweeypy_stati.append(tweet["specific"])

    return tweeypy_stati

# route for requesting global micro-cluster snapshot data of specific timestamp
@app.route('/getGlobalClusterData', methods=['GET'])
def getGlobalClusterData():
    # parsing query parameters
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    
    # checking type of timetampt: datetime for realtimefadin or else int
    timestamp_datetime = check_timestamp_type(cluster_session_id, timestamp_string)

    # mongodb aggegration pipeline for boxplot data of the frontend -> users, followers, likes...
    clusterWeightBoxplotPipeline = [
        {"$match": {"timestamp":  timestamp_datetime}},
        {"$group": {"_id": "null", "global_weights": {"$push": "$weight"}}}
    ]
    
    # fetching data for weight distribution
    cluster_weights = list(
        db["mc_{}".format(cluster_session_id)].aggregate(clusterWeightBoxplotPipeline))[0]["global_weights"]
    return_dict = json.dumps({"cluster_number": len(cluster_weights), "cluster_weights": cluster_weights})
    return return_dict

# route for requestion termfreq and weights of top n microcluster
@app.route('/getTopClusterData', methods=['GET'])
def getTopClusterData():
    # parsing query parameters
    cluster_session_id = request.args.get('session')
    timestamp_string = request.args.get('timestamp')
    n_tokens = request.args.get("n_tokens", 5, type=int)
    
    # checking type of timetampt: datetime for realtimefadin or else int
    timestamp_datetime = check_timestamp_type(cluster_session_id, timestamp_string)

    # defining number of returning microclusters
    max_to_return = int(request.args.get('max'))

    # pipeline for requesting the microcluster from mongodb
    pipelineTop = [
        {"$match": {"timestamp":  timestamp_datetime}},
        {"$sort": {"weight": -1}},
        {"$limit": max_to_return}
    ]

    maxClusters = list(
        db["mc_{}".format(cluster_session_id)].aggregate(pipelineTop))
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

@lru_cache(maxsize=32)
def check_timestamp_type(cluster_session_id, timestamp_string):
    typePipeline = [
        {"$project": {"timestamp_type" : { "$type": "$timestamp" }}},
        {"$limit": 1},
        ]
    timestamp_type = list(db["mc_{}".format(cluster_session_id)].aggregate(typePipeline))[0]["timestamp_type"]

    # transform string to int if not realtime faded and to datetime otherwise
    if timestamp_type == "int":
        return int(timestamp_string)
    else:
        if timestamp_string == "0":
            timestamp_string = "1970-01-01T00:00:00.0"
        return pd.to_datetime(timestamp_string)

if __name__ == "__main__":
    # set running clusters to false on startup
    db["textclust_sessions_meta"].update_many(
        {"ended": False},
        {'$set': {"ended": True, "end_date": datetime.utcnow()}}
    )

    print("Building indexes", flush=True)

    cluster_session_ids = db["textclust_sessions_meta"].find(projection={
        "_id": 0,
        "cluster_session_id": 1
    })

    # Create indexes if they do not exist yet
    for cluster_session_id in cluster_session_ids:
        text_coll = db["texts_{}".format(cluster_session_id["cluster_session_id"])]
        text_coll.create_index([("general.text_id", pymongo.DESCENDING)])
        text_coll.create_index([("general.text_id", pymongo.DESCENDING),("general.time", pymongo.DESCENDING)])
        text_coll.create_index([("general.time", pymongo.DESCENDING)])
        text_coll.create_index([("specific.user.id", pymongo.ASCENDING),("general.time", pymongo.DESCENDING)])
        text_coll.create_index([("general.time", pymongo.DESCENDING), ("general.text_id", pymongo.DESCENDING)])

    
        mc_coll = db["mc_{}".format(cluster_session_id["cluster_session_id"])]
        mc_coll.create_index([("id", pymongo.DESCENDING)])
        mc_coll.create_index([("id", pymongo.DESCENDING), ("timestamp", pymongo.DESCENDING)])
        mc_coll.create_index([("timestamp", pymongo.DESCENDING)])
        mc_coll.create_index([("timestamp", pymongo.ASCENDING), ("id", pymongo.ASCENDING)])
        mc_coll.create_index([("weight", pymongo.DESCENDING), ("id", pymongo.DESCENDING), ("timestamp", pymongo.DESCENDING)])
        mc_coll.create_index([("weight", pymongo.DESCENDING), ("timestamp", pymongo.DESCENDING)])

    # Load config variables
    config["KEYWORDS"] = [x.strip() for x in config["KEYWORDS"]]
    for keywords in  config["KEYWORDS"]:
        print(keywords)
        streamname = "Default" 
        
        streamname = keywords.split(":")[0]
        keywords = keywords.split(":")[1]
        config_template_dict = {
                    "lambda": config["FADING_FACTOR"],
                    "termfading": config["TERMFADING"],
                    "tgap": config["TIME_GAP"],
                    "radius": config["RADIUS"],
                    "realtimefading": config["REALTIME"],
                    "micro_distance": config["MICRO_CLUSTER_DISTANCE_METRIC"],
                    "macro_distance": config["MACRO_CLUSTER_DISTANCE_METRIC"],
                    "model": config["MODEL"],
                    "idf": config["IDF"],
                    "num_macro": config["MACRO_NUMBER"],
                    "minWeight": config["MINIMUM_MICRO_CLUSTER_WEIGHT"],
                    "auto_r": config["AUTO_RADIUS"],
                    "auto_merge": config["AUTO_MERGE"]
                }
        preprocess_dict = {
                    "language": config["LANGUAGE"],
                    "stopword_removal": config["STOPWORD_REMOVEL"],
                    "stemming": config["STEMMING"],
                    "punctuation": config["PUNCTUATION_REMOVAL"],
                    "hashtag": config["HASHTAG_REMOVEL"],
                    "username": config["USERNAMES_REMOVEL"],
                    "url": config["URLS_REMOVE"],
                    "max_grams": config["N_GRAMS"],
                    "exclude_tokens": config["EXCLUDE_TOKENS"]
                }

        input_dict = {"mode": "TWT", "terms": keywords.split(" "), "languages": config["LANGUAGES"], "stream_name":streamname}

        # Start the textClust algorithm at startup
        if not config["ANALYSIS"]:
            start_clust(preprocess_dict, input_dict, config_template_dict)

    app.run(host="0.0.0.0", port=5000, use_reloader=False, debug=True)