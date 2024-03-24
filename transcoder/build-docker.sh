cd ..
cp -r object_store setup.py transcoder
cd transcoder
python3 setup.py sdist
ls
docker build -t prajjawal05/transcoder .
rm -r object_store setup.py
docker push prajjawal05/transcoder