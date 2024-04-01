mkdir deployment

# Copy required files to the temporary directory
# need to rename the action file
cp split-action.py deployment/__main__.py
cp Intent.json deployment/
cp ../constants.py deployment/

# Zip the contents of the temporary directory
cd deployment
zip -r action.zip *

# creating openwhisk action
wsk action create split-action action.zip --docker docker.io/prajjawal05/chatbot:latest --insecure

rm action.zip

# Clean up the temporary directory
cd ..
rm -rf deployment