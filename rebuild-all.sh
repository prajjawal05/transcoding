#!/bin/bash

export TAG="${TAG:-docker.io/alexmerenstein/orchaction:latest}"

python3 setup.py sdist
python3 -m pip install .
cd docker
bash build-docker.sh
docker push ${TAG}
cd ..

find examples -name deploy-script.sh -exec bash {} \;