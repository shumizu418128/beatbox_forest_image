FROM python:3.11
USER root

ENV LANG ja_JP.UTF-8
ENV LANGUAGE ja_JP:ja
ENV LC_ALL ja_JP.UTF-8
ENV TZ JST-9
ENV TERM xterm
RUN /usr/local/bin/python -m pip install --upgrade pip
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-jpn \
    libtesseract-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY main.py main.py
COPY mobile_check.py mobile_check.py
COPY keep_alive.py keep_alive.py
COPY analyze.py analyze.py
COPY template_black.png template_black.png
COPY template_white.png template_white.png
COPY makesomenoise-4243a19364b1.json makesomenoise-4243a19364b1.json
COPY eng.traineddata eng.traineddata
COPY jpn.traineddata jpn.traineddata

RUN tesseract -v

CMD ["python", "-u", "main.py"]
ARG EnvironmentVariable
