#!/bin/bash

# Move the zip file back to the original directory if needed
wsk action create splitter actions.py --docker docker.io/alexmerenstein/transcoder:latest --insecure
wsk action create transcoder actions.py --docker docker.io/alexmerenstein/transcoder:latest --insecure
wsk action create combiner actions.py --docker docker.io/alexmerenstein/transcoder:latest --insecure