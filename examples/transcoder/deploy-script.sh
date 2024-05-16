#!/bin/bash

pushd "$(dirname "$0")"

ACTION_TAG="${ACTION_TAG:-docker.io/alexmerenstein/transcode:0.0.4}"

docker build . -t ${ACTION_TAG}
docker push ${ACTION_TAG}

wsk action update split split.py --docker ${ACTION_TAG} --insecure
wsk action update transcode transcode.py --docker ${ACTION_TAG} --insecure
wsk action update combine concat.py --docker ${ACTION_TAG} --insecure

popd
