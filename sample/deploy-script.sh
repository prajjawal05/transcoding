# Move the zip file back to the original directory if needed
wsk action create sampleaction1 action1.py --docker docker.io/prajjawal05/transcoder:latest --insecure
wsk action create sampleaction2 action2.py --docker docker.io/prajjawal05/transcoder:latest --insecure
wsk action create sampleaction3 action3.py --docker docker.io/prajjawal05/transcoder:latest --insecure
