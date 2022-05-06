import datetime
import pandas as pd
import tweepy

# Use billiard so that it works with celery
from billiard import Pool
from tqdm import tqdm
import os

# Function to extract the tweets for the users in a dataframe
def extract_last_tweets_for_users_from_timestamp(users, timestamp):
    # Load the Twitter access secrets from the environment variables
    config = {
        "BEARER_TOKEN": os.getenv("BEARER_TOKEN"),
        "API_KEY": os.getenv("API_KEY"),
        "API_SECRET": os.getenv("API_SECRET"),
        "ACCESS_TOKEN": os.getenv("ACCESS_TOKEN"),
        "ACCESS_SECRET": os.getenv("ACCESS_SECRET")
    }
    
    # Create a pool of 6 parallel processes used to fetch the tweets from the Twitter API
    pool = Pool(processes=6)
    jobs = [pool.apply_async(func=__extract_last_tweets_per_user_from_timestamp, args=(user, timestamp, config)) for _, user in users.iterrows()]
    pool.close()
    responses = []
    # Execude the jobs that fetch the tweets from a users timeline
    for job in tqdm(jobs):
        responses.append(job.get())

    tweets = pd.DataFrame(columns=["user_screen_name", "user_id", "id", "text", "created_at"])
    # Concatenate the responses from the Twitter API into one dataframe
    for response in responses:
        tweets = pd.concat([tweets, response], ignore_index=True)
    del responses
    return tweets


# Helper function that handles the communication with Twitter
def __extract_last_tweets_per_user_from_timestamp(user, timestamp, config):
    # Specify the 24 hour period between which the tweets had to be created
    end_time = timestamp.isoformat("T","seconds") + "Z"
    start_time = timestamp - datetime.timedelta(days=1)
    start_time = start_time.isoformat("T","seconds") + "Z"
    data = pd.DataFrame(columns=["user_screen_name", "user_id", "id", "text", "created_at"])
    # Initialize the Twitter client with tweepy
    client = tweepy.Client(bearer_token=config.get("BEARER_TOKEN"), consumer_key=config.get("API_KEY"), consumer_secret=config.get("API_SECRET"), access_token=config.get("ACCESS_TOKEN"), access_token_secret=config.get("ACCESS_SECRET"), wait_on_rate_limit=True)
    # Load the tweets from a users timeline
    user_tweets = client.get_users_tweets(id=user['id_str'], end_time=end_time, start_time=start_time, max_results=100, tweet_fields=["created_at"])
    if user_tweets.data is None:
        return
    tweets_list = []
    for tweet in user_tweets.data:
        referenced_tweets = tweet.referenced_tweets
        if referenced_tweets is not None:
            referenced_tweets = [{'id': ref.id, 'type':ref.type} for ref in referenced_tweets]
        tweets_list.append({"user_screen_name": user['screen_name'],
                            "user_id": user['id_str'],
                            "id": tweet.id,
                            "text": tweet.text,
                            "created_at": tweet.created_at
                           })
    temp = pd.DataFrame.from_records(tweets_list)
    data = pd.concat([data, temp], ignore_index=True)
    del tweets_list
    del temp
    return data
