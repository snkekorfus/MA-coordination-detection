FROM ubuntu:20.04
RUN apt-get update -y
RUN apt-get install -y python3-dev python3-pip python3-venv python3-wheel

# set the working directory in the container
WORKDIR /textclust-backend

# copy the dependencies file to the working directory
ADD textClustPy /textclust-backend/textClustPy
ADD requirements.txt /textclust-backend
WORKDIR /textclust-backend/textClustPy

RUN pip3 install .

WORKDIR /textclust-backend
RUN pip3 install -r requirements.txt

ADD flaskserver /textclust-backend/flaskserver
WORKDIR /textclust-backend/flaskserver
RUN [ "python3", "-m", "spacy", "download", "de_core_news_sm"]
RUN [ "python3", "-m", "spacy", "download", "en_core_web_sm"]
RUN [ "python3", "-c", "import nltk; nltk.download('stopwords')" ]
RUN [ "python3", "-c", "import nltk; nltk.download('punkt')" ]
