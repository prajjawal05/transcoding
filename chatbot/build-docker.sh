cd ..
cp -r object_store setup.py chatbot
cd chatbot
python3 setup.py sdist
ls
docker build -t prajjawal05/chatbot .
rm -r object_store setup.py
docker push prajjawal05/chatbot