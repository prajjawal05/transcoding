#!/bin/bash

TAG="${TAG:-docker.io/alexmerenstein/orchaction:latest}"

mkdir -p build

TOPLEVEL=$(git rev-parse --show-toplevel)

# TODO: check if tarball exists, 
# if not tell user to run python setup.py sdist
cp ${TOPLEVEL}/dist/orchestration-0.1.tar.gz build
cp ${TOPLEVEL}/config/in-pod-config.ini build/config.ini

docker build . -t $TAG

rm -rf build