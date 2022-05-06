from flask import current_app
import tweepy
from operator import itemgetter


# function for requesting trending topics on twitter
def trending_topics(woedi, n=15):
    auth = tweepy.AppAuthHandler(current_app.config['api_key'], current_app.config['api_secret'])  # calling the api
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


# function for requesting textids as status ids of twitter input session
def getTweetIds(session, timestamp, cluster_id):
    time_id_list = current_app.config['db']["mc_{}".format(session)].find_one(
        {"timestamp": timestamp, "id": int(cluster_id)})["textids"]
    return time_id_list


# function for fetching twitter meta from mongodb
def getTwitterMeta(session, tweet_id_list):

    # make usage of references
    tweetPipeline = [
        {"$match": {"specific.id_str": {"$in": tweet_id_list}}},
    ]
    tweets = list(current_app.config['db']["texts_{}".format(session)].aggregate(tweetPipeline))
    tweeypy_stati = []
    for tweet in tweets:
        tweeypy_stati.append(tweet["specific"])

    return tweeypy_stati