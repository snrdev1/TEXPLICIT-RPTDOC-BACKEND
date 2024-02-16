# syntax=docker/dockerfile:1

FROM python:3.10
WORKDIR /texplicit02-docker

RUN /usr/local/bin/python -m pip install --upgrade pip

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt
RUN python3 -m nltk.downloader punkt -d /usr/share/nltk_data
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

COPY . .

EXPOSE 8080
ENV FLASK_APP=main.py
CMD [ "python3", "main.py", " --host=0.0.0.0"]
