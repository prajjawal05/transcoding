mkdir deployment

# Copy transcodingActions.py and constants.py to the temporary directory
# need to rename actions.py to __main__.pyu
cp actions.py deployment/__main__.py
cp ../constants.py deployment/

# Zip the contents of the temporary directory
cd deployment
zip -r action.zip *

# Move the zip file back to the original directory if needed
wsk action create splitter action.zip --docker docker.io/prajjawal05/transcoder:latest --insecure
wsk action create transcoder action.zip --docker docker.io/prajjawal05/transcoder:latest --insecure
wsk action create combiner action.zip --docker docker.io/prajjawal05/transcoder:latest --insecure

rm action.zip

# Clean up the temporary directory
cd ..
rm -rf deployment
