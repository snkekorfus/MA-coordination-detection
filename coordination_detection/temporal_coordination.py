import datetime
import pandas as pd
import numpy as np
from dtaidistance import dtw

from . import similarity_calculation

# Function to calculate the temporal coordination between users
def calculate_temporal_coordination(tweets):
    print("start calculating temporal coordination")
    # Fix the timestamps of the tweets to be the right format
    tweets['created_at'] = tweets['created_at'].values.astype('datetime64[m]')
    tweets = tweets.astype({'created_at': 'datetime64[m]'})
    # Filter to only have tweets in a 24 hour periode
    start = tweets["created_at"].max()
    end = start - datetime.timedelta(days=1)
    tweets = tweets[tweets["created_at"] > end]

    # Create time series for the users
    time_series = __create_tweet_time_series(tweets, start, end)
    time_series = time_series[time_series.sum(axis=1) > 9]
    # Check that at least two users have more than 9 tweets to be considered
    # for the coordination calculation. Otherwise return an empty dataframe.
    if len(time_series) < 2:
        return pd.DataFrame(columns=["User1", "User2", "Weight", "Method"])

    # Calculate the pairwise similarities between users based on DTW
    distances = pd.DataFrame(similarity_calculation.pairwise_similarity_calculation(time_series, metric=__calculate_dtw_distance), columns=time_series.index.values, index=time_series.index.values)

    np.fill_diagonal(distances.values, max(distances.values.flatten()))
    similarity = 1 - distances / max(distances.values.flatten())

    np.fill_diagonal(similarity.values, np.nan)
    similarity = similarity.where(np.triu(np.ones(similarity.shape)).astype(np.bool))
    similarity = similarity.stack().reset_index()
    similarity["Method"] = "Temporal"
    similarity.columns = ["User1", "User2", "Weight", "Method"]
    return similarity


# Function that creates the time series for the users based on the tweets
def __create_tweet_time_series(tweets: pd.DataFrame, end_timestamp: datetime.datetime, start_timestamp: datetime.datetime):
    end = end_timestamp.replace(second=0, microsecond=0)
    start = start_timestamp.replace(second=0, microsecond=0)
    date_ranges = pd.date_range(start=start, end=end, freq='1min')
    # The pandas cut function puts the tweets in pre-specified bins of 1 minute time frames
    bins = pd.cut(tweets['created_at'], bins=date_ranges, right=False, labels=[x for x in range(0,len(date_ranges)-1)])
    groups = tweets.groupby(['user_screen_name', bins])
    return groups.size().unstack()


# Helper function that applies the DTW distance
def __calculate_dtw_distance(x, y):
    distance = dtw.distance(x.astype('double'), y.astype('double'), window=2, use_c=True)
    return distance
    
