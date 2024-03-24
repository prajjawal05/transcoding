# chatbot

Trains a one-vs-all classifier for the ChatBots Intent Recognition Dataset, available on Kaggle.

Based on: [AWS Lambda Benchmark](https://github.com/icanforce/Orion-OSDI22/tree/main/Benchmarks_AWS_Lambda/ChatBot)

## Pre-requisites

1. You would need to install `ffmpeg` first.
2. Run `pip3 install -r requirements.txt`.
3. You would need minio object store running somewhere.
4. MongoDB is also required for storing action states.

### Running services locally.

1. For running minio use: `minio server miniodata`.
2. For mongod use: `mongod --config /usr/local/etc/mongod.conf --fork`.

## Setup Action and Orchestrator

1. Run `wsk property get --auth` to get authorization details.
2. Use that when initialising `BaseOrchestrator`. See `orchestrator.py` for more details on how to use it.
3. Replace env constants for DB and Object store in `constants.py`.
4. To deploy your action use: `deploy-script.sh`.

## Changes to object store

If you are making any changes to object store package or adding a library, you need to run:
`sh build-docker.sh`.

### Note:

You would have to change docker remote in build-docker.sh and deploy-script.sh.

#### Transcoding action

To run transcoding action, you would need to put a `facebook.mp4` in `input-video` bucket.
To test the action: `python3 run-action-local.py`.
To run the orchestrator: `python3 run-orchestrator.py`.
