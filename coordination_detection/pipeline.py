from datetime import datetime
from multiprocessing import Pool

import pandas as pd

from . import mongo_access
from . import twitter_access
from . import content_coordination
from . import temporal_coordination


# Function to calculate coordination between users based on data stored in the MongoDB database
def calculate_coordination_pipeline_own_data(source_uuid, cluster_id, timestamp=None):
    timestamp = __format_timestamp(timestamp)
    users = mongo_access.extract_relevant_users_from_clusters(source_uuid, cluster_id, timestamp)
    tweets = mongo_access.extract_tweets_for_users(source_uuid, users, timestamp)

    similarity = __calculate_similarity_matrix(tweets)
    return similarity


# Function to calculate coordination between users based on data fetched from data
def calculate_coordination_pipeline_twitter_data(source_uuid, cluster_id, timestamp=None):
    timestamp = __format_timestamp(timestamp)
    users = mongo_access.extract_relevant_users_from_clusters(source_uuid, cluster_id, timestamp)
    timestamp = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
    tweets = twitter_access.extract_last_tweets_for_users_from_timestamp(users[0:3000], timestamp)

    similarity = __calculate_similarity_matrix(tweets)
    return similarity


# Function to calculate the similarity matrix based on the tweets received from one of the pipeline functions
def __calculate_similarity_matrix(tweets):
    print("Spawn two processes")
    # Create a process pool to let the content and temporal coordination calculation run in parallel
    with Pool(processes=4) as pool:
        content_pool = pool.apply_async(func=content_coordination.calculate_content_coordination, args=(tweets,))
        temporal_pool = pool.apply_async(func=temporal_coordination.calculate_temporal_coordination, args=(tweets,))

        content_similarity = content_pool.get()
        temporal_similarity = temporal_pool.get()

    # Concatanate the two similarity dataframes from the conent and temporal method
    similarity = pd.concat([content_similarity, temporal_similarity])
    # Filter low weight edges below 0.6 to reduce the size of data that needs to be transfered to the frontend
    similarity = similarity[similarity["Weight"] > 0.6]
    return similarity


# Transform timestamp to isoformat string
def __format_timestamp(timestamp=None):
    timestamp = timestamp if timestamp is not None else datetime.now()
    timestamp = timestamp if type(timestamp) == str else timestamp.isoformat()

    return timestamp