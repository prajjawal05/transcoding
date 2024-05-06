FROM alexmerenstein/orchaction:latest

RUN apk update && apk add ffmpeg

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt