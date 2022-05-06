import pandas as pd
from pymongo import MongoClient

from datetime import datetime, timedelta

from tqdm import tqdm


# Function to extract the relevant users for the coordination calculation from the MongoDB database
def extract_relevant_users_from_clusters(source_uuid, cluster_id, timestamp):
    connection = MongoClient(f"mongodb://db:27017/")
    db = connection.textclustDB

    # Query to get all tweets in a cluster
    textids = db[f"mc_{source_uuid}"].find_one(
        {"id": cluster_id},
        sort=[("timestamp", -1)],
        projection={
            "_id": 0,
            "textids": 1
            }
    )

    # Query to get all users of the tweets, that are in a cluster and are not newer than a specific timestamp.
    # The maximum number of returned users is 5000
    users = db[f"texts_{source_uuid}"].find(
        {
            "$and": [
                {"general.text_id": {
                        "$in": textids["textids"]
                    }
                },
                {"$or": [
                    {"general.time": {
                        "$lte": datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
                        }
                    },
                    {"general.time": {
                        "$lte": timestamp.replace("T", " ")
                        }
                    }
                ]}
            ]
        },
        sort=[("general.time", -1)],
        projection = {
            "_id": 0,
            "user": "$specific.user"
        }
    ).limit(5000)

    # Transform the query result into a dataframe
    users = pd.DataFrame([user['user'] for user in users])
    return users.drop_duplicates(["id_str"], ignore_index=True)


# Function to extract the tweets of a user that are stored in the MongoDB database
def extract_tweets_for_users(source_uuid, users, timestamp):
    tweets = pd.DataFrame(columns=["user_screen_name", "user_id", "id", "text", "created_at"])
    
    # Loop to iterate over the users in the dataframe handed to the function.
    # For every user the tweets are extracted and are concatanated to the tweets dataframe.
    for _, user in tqdm(users.iterrows(), total=len(users)):
        response = __extract_tweets_per_user(source_uuid, user, timestamp)
        tweets = pd.concat([tweets, response], ignore_index=True)

    return tweets


# Helper function to extract the tweets for a specific user
def __extract_tweets_per_user(source_uuid, user, timestamp):
    # Set the period in which the user tweets must have been created
    timestamp_min = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
    timestamp_min = timestamp_min - timedelta(days=2)
    timestamp_min = datetime.strftime(timestamp_min, "%Y-%m-%dT%H:%M:%S")
    connection = MongoClient(f"mongodb://db:27017/")
    db = connection.textclustDB

    # Query to fetch the relevant fields of the tweets of a user from the MongoDB database.
    # The tweets must have a creation time that lays in a 2 days period specigied beforehand
    data =  db[f"texts_{source_uuid}"].find(
        {"$and": [
            {"specific.user.id": user['id']},
            # The or is used to account for different timeformats that could be handed to the function
            {"$or": [
                    {"general.time": {
                        "$lte": datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
                        }
                    },
                    {"general.time": {
                        "$lte": timestamp.replace("T", " ")
                        }
                    }
                ]
            },
            {"$or": [
                    {"general.time": {
                        "$gte": datetime.strptime(timestamp_min, "%Y-%m-%dT%H:%M:%S")
                        }
                    },
                    {"general.time": {
                        "$gte": timestamp_min.replace("T", " ")
                        }
                    }
                ]
            }
        ]},
        projection={
            "_id": 0,
            "user_screen_name": "$specific.user.screen_name",
            "user_id": "$specific.user.id_str",
            "id": "$specific.user.id",
            "text": "$general.text",
            "created_at": "$general.time"
        }
        )
    return pd.DataFrame(list(data))