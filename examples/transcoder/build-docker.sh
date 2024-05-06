#!/bin/bash

TAG="${TAG:-docker.io/alexmerenstein/transcode:latest}"

mkdir -p build

TOPLEVEL=$(git rev-parse --show-toplevel)

# TODO: check if tarball exists, 
# if not tell user to run python setup.py sdist
cp ${TOPLEVEL}/dist/orchestration-0.1.tar.gz build
cp ${TOPLEVEL}/config/default.ini build

docker build . -t $TAG

rm -rf build