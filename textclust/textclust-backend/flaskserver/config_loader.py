import os

def load_config():
    config = {}
    
    config["RADIUS"] = float(os.getenv("RADIUS"))
    config["MODEL"] = str(os.getenv("MODEL")) if len(os.getenv("MODEL")) != 0 else None
    config["FADING_FACTOR"] = float(os.getenv("FADING_FACTOR"))
    config["VERBOSE"] = True if os.getenv("VERBOSE") == "True" else False
    config["TERMFADING"] = True if os.getenv("TERMFADING") == "True" else False
    config["REALTIME"] = True if os.getenv("REALTIME") == "True" else False
    config["AUTO_RADIUS"] = True if os.getenv("AUTO_RADIUS") == "True" else False
    config["AUTO_MERGE"] = True if os.getenv("AUTO_MERGE") == "True" else False
    config["TIME_GAP"] = int(os.getenv("TIME_GAP"))
    config["MICRO_CLUSTER_DISTANCE_METRIC"] = str(os.getenv("MICRO_CLUSTER_DISTANCE_METRIC"))
    config["MACRO_CLUSTER_DISTANCE_METRIC"] = str(os.getenv("MACRO_CLUSTER_DISTANCE_METRIC"))
    config["MACRO_NUMBER"] = int(os.getenv("MACRO_NUMBER"))
    config["MINIMUM_MICRO_CLUSTER_WEIGHT"] = float(os.getenv("MINIMUM_MICRO_CLUSTER_WEIGHT"))
    config["IDF"] = True if os.getenv("IDF") == "True" else False

    config["LANGUAGE"] = str(os.getenv("LANGUAGE"))
    config["N_GRAMS"] = int(os.getenv("N_GRAMS"))
    config["STEMMING"] = True if os.getenv("STEMMING") == "True" else False
    config["HASHTAG_REMOVEL"] = True if os.getenv("HASHTAG_REMOVEL") == "True" else False
    config["USERNAMES_REMOVEL"] = True if os.getenv("USERNAMES_REMOVEL") == "True" else False
    config["STOPWORD_REMOVEL"] = True if os.getenv("STOPWORD_REMOVEL") == "True" else False
    config["PUNCTUATION_REMOVAL"] = True if os.getenv("PUNCTUATION_REMOVAL") == "True" else False
    config["URLS_REMOVE"] = True if os.getenv("URLS_REMOVE") == "True" else False
    config["EXCLUDE_TOKENS"] = str(os.getenv("EXCLUDE_TOKENS")).split(",")

    config["KEYWORDS"] = str(os.getenv("KEYWORDS")).split(",")
    config["LANGUAGES"] = str(os.getenv("LANGUAGES"))

    config["TIME_UNIT"] = str(os.getenv("TIME_UNIT"))
    config["WINDOW_SIZE"] = int(os.getenv("WINDOW_SIZE"))
    config["ANALYSIS"] = True if os.getenv("ANALYSIS") == "True" else False
    return config

if __name__ == "__main__":
    load_config()