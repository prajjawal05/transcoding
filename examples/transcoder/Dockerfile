FROM openwhisk/python3action:latest

RUN apk update && apk add ffmpeg

COPY requirements.txt requirements.txt

COPY build/orchestration-0.1.tar.gz .
COPY build/default.ini /etc/orchestration/config.ini
RUN pip install -r requirements.txt