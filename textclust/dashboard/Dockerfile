FROM ubuntu:latest

RUN apt-get update -y
RUN apt-get install -y python3-pip python-dev build-essential sudo

# set the working directory in the container
WORKDIR /textclust-frontend

# copy the dependencies file to the working directory
COPY requirements.txt /textclust-frontend

RUN pip3 install -r requirements.txt
RUN [ "python3", "-m", "spacy", "download", "de_core_news_sm"]
RUN [ "python3", "-m", "spacy", "download", "en_core_web_sm"]
COPY ./src /textclust-frontend

CMD ["python3", "app.py"]