from flask import current_app
from datetime import datetime
from textClustPy import Preprocessor
from textClustPy import textclust
from textClustPy import CSVInput
from textClustPy import TwitterInput
import pymongo
import json
import os


celery = current_app.config['celery']
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
        microclusters = list(clust["microclusters"].values())
        timestamp = datetime.utcnow()
        documentList = []

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
                                stemming=stemming, punctuation=punctuation, hashtag=hashtag, username=username, url=url)

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
    text_coll = current_app.config['db']["texts_{}".format(cluster_session_id)]
    text_coll.create_index("general.text_id")
    mc_coll = current_app.config['db']["mc_{}".format(cluster_session_id)]
    mc_coll.create_index([("id", pymongo.ASCENDING),("timestamp", pymongo.ASCENDING)])

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
        current_app.config['db']["textclust_sessions_meta"].insert_one(meta)
        csv_input_instance = CSVInput(csvfile=csv_path, textclust=clust, preprocessor=preprocessor, delimiter=delimeter,
                                      quotechar=quotechar, newline=newline, col_id=col_id, col_time=col_time, col_text=col_text, col_label=2, callback=insert_input_db, timeformat=timeformat)
        csv_input_instance.run()

    # twitter input related configuration
    if input["mode"] == "TWT":
        terms = input["terms"]
        # running the actual twt input instance with all parameters
        current_app.config['db']["textclust_sessions_meta"].insert_one(meta)
        TwitterInput(current_app.config['api_key'], current_app.config['api_secret'], current_app.config['access_token'], current_app.config['access_secret'], textclust=clust,
                     preprocessor=preprocessor, terms=terms, callback=insert_input_db)