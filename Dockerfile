FROM ubuntu:latest
USER root

RUN ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime

RUN apt-get update && \
    apt-get -y install python3-pip && \
    apt-get -y install git &&

RUN apt-get install -y tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-jpn \
    libtesseract-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN add-apt-repository ppa:alex-p/tesseract-ocr5
RUN apt-get update

COPY requirements.txt requirements.txt

RUN pip install -U pip && \
    pip install requirements.txt

COPY discordbot_image.py discordbot_image.py
COPY mobile_check.py mobile_check.py
COPY analyze.py analyze.py
COPY template_black.png template_black.png
COPY template_white.png template_white.png
COPY makesomenoise-4243a19364b1.json makesomenoise-4243a19364b1.json
COPY eng.traineddata eng.traineddata
COPY jpn.traineddata jpn.traineddata

RUN tesseract -v
CMD ["python", "-u", "discordbot_image.py"]
ARG EnvironmentVariable
