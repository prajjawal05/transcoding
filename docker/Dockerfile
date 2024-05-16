FROM openwhisk/python3action:latest

COPY requirements.txt requirements.txt

COPY build/orchestration-0.1.tar.gz .
COPY build/config.ini /etc/orchestration/config.ini
COPY pythonrunner.py /pythonAction/pythonrunner.py
RUN pip install -r requirements.txt
