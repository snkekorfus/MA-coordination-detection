FROM ubuntu:latest

RUN apt-get update -y
RUN apt-get install -y python3-dev python3-pip

WORKDIR /textclust-flask-api
ADD . /textclust-flask-api

RUN pip3 install -r requirements.txt


ENV FLASK_ENV=development
ENV FLASK_RUN_THREADED=true
#CMD ["python3", "-m", "app"]