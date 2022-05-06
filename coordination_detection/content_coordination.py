import pandas as pd
import numpy as np
from numpy import dot
from numpy.linalg import norm
import re
import string
import emoji
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer

from . import similarity_calculation

# Entry function for the coordination calculation based on textual similarity
def calculate_content_coordination(tweets):
    # Prepare tweets
    grouped_texts = __prepare_tweets_df(tweets)

    # Check if at least two users have enough tweets to be considered for the
    # coordination calculation. If not, an empty dataframe is returned
    if len(grouped_texts) < 2:
        return pd.DataFrame(columns=["User1", "User2", "Weight", "Method"])
    
    # Calculate similarity matrix
    similarity = __calculate_similarity_matrix(grouped_texts)

    return similarity


# Function to check if users have enough tweets to be considered for the textual coordination
# calculation. Furthermore, the tweets of a user get aggregated into one document.
def __prepare_tweets_df(tweets):
    # Filter users with too little tweets
    v = tweets["user_screen_name"].value_counts()
    tweets = tweets[tweets["user_screen_name"].isin(v.index[v.gt(5)])]
    tweets.reset_index(inplace=True, drop=True)

    # Adapt dateformat
    tweets['created_at'] = tweets['created_at'].values.astype('datetime64[m]')
    tweets = tweets.astype({'created_at': 'datetime64[m]'})

    # Group texts
    return tweets.groupby(["user_screen_name"]).agg({'text': ' '.join})
    

# Function that calculates the pairwise similarity between the tweets of users
def __calculate_similarity_matrix(grouped_texts):
    # Load the spacy model to use the lemmatizer function spacy
    nlp = spacy.load('en_core_web_sm', disable=['ner', 'parser'])
    # Create a scikit-learn TfidfVectorizer object. It uses the spacy tokenizer to create 
    # a list of lemmatized n-grams and a custome preproccesor function
    tf = TfidfVectorizer(preprocessor=__create_preprocessed_text, tokenizer=lambda text: __spacy_tokenizer(text, nlp), ngram_range=(1,2), max_features=20000)
    print("Fit and transform the tf-matrix", flush=True)
    # Create the tfidf vectors for the users
    tf_matrix = tf.fit_transform(grouped_texts['text'])
    # Transform the tf-idf vectors of the users into a dataframe
    tf_matrix = pd.DataFrame(tf_matrix.toarray(), index=grouped_texts.index.values)
    # Remove users that only have 0 vectors as they will result in a cosine similarity of NaN
    tf_matrix = tf_matrix.loc[~(tf_matrix==0).all(axis=1)]
    print("Calculate distances and transform to similarity", flush=True)
    # Calculate the pairwise similarities between users based on cosine similarity 
    similarity = pd.DataFrame(similarity_calculation.pairwise_similarity_calculation(tf_matrix, metric=__cosine_similarity), columns=tf_matrix.index.values, index=tf_matrix.index.values)
    np.fill_diagonal(similarity.values, np.nan)
    similarity = similarity.where(np.triu(np.ones(similarity.shape)).astype(np.bool))
    similarity = similarity.stack().reset_index()
    similarity["Method"] = "Content"
    similarity.columns = ["User1", "User2", "Weight", "Method"]

    print("Finished", flush=True)
    return similarity


# Preprocessor function to clean the tweets before creating the tfidf vectors
def __create_preprocessed_text(text):
    # Lower text
    text = text.lower()

    # Remove text wrap
    text = text.replace("\n", " ")

    # Remove URLs
    text = re.sub('((www\.[^\s]+)|(https?://[^\s]+)|(http?://[^\s]+))', '', text)
    text = re.sub(r'http\S+', '', text)

    # Remove usernames
    text = re.sub('@[^\s]+', '', text)
        
    # remove the # in #hashtag
    text = re.sub(r'#([^\s]+)', r'\1', text)

    ## remove multi exclamation mark
    text = re.sub(r"(\!)\1+", ' multiExclamation ', text)
    
    # Initialize Punctuation set
    exclude = '’“' + string.punctuation
    
    # Check char characters to see if they are in punctuation
    text = [char for char in text if char not in exclude]
    
    # Join the characters again to form the string.
    text = ''.join(text)

    # Remove emojis
    text = emoji.get_emoji_regexp().sub(r'', text)

    return text


# Function to return a list of lemmatized tokens with the help of spacy
def __spacy_tokenizer(doc, nlp):
    return [x.lemma_ for x in nlp(doc)]


# implementation of the cosine similarity
def __cosine_similarity(x, y):
    return dot(x, y)/(norm(x)*norm(y))