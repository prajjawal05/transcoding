mkdir deployment

# Copy required files to the temporary directory
# need to rename the action file
cp train-intent-classifier.py deployment/__main__.py
cp Intent.json deployment/
cp ../constants.py deployment/

# Zip the contents of the temporary directory
cd deployment
zip -r action.zip *

# creating openwhisk action
wsk action create train-classifier action.zip --docker docker.io/prajjawal05/chatbot:latest --insecure

rm action.zip

# Clean up the temporary directory
cd ..
rm -rf deployment