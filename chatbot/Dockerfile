FROM openwhisk/python3action:latest

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

# object_store package
COPY dist/object_store-0.1.tar.gz .

RUN pip install object_store-0.1.tar.gz