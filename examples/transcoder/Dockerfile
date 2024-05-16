FROM alexmerenstein/orchaction:0.0.4

RUN apk update && apk add ffmpeg

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt
