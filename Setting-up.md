## Setting Up

Install prerequisites:

apt install -y docker.io python3-pip

https://kind.sigs.k8s.io/docs/user/quick-start/

https://helm.sh/docs/intro/install/

https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/

https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/

https://github.com/apache/openwhisk-cli/releases

### Local Setup

Start kind:
```
bash start-kind.sh
```

Start OpenWhisk:

```
bash start-cluster.sh
```

Configure wsk:
```
wsk property set --apihost 172.18.0.4:31001 --auth "23bc46b1-71f6-4ed5-8c54-816aa4f8c502:123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP"
```

Run MinIO and MongoDB:
```
kubectl apply -f deploy/minio.yaml -f deploy/mongo.yaml
```

Install Orchestrator:
```
pip3 install -r requirements.txt
python3 -m pip install .
```

Update and install config:
```
mkdir -p /etc/orchestration
cp config/host-config.ini /etc/orchestration/config.ini
```

### Local Running

1. To run a specific action, go over to `run-action-local.py` and change the import accordingly. You will be able to run the action and debug it for any extra information.

2. To run a specific orchestrator, go over to `run-orchestrator.py` and change the import accordingly. You will be able to run the orchestrator, along with the set of actions locally once you have made changes in the orchestrator to call actions instead of invoking them and debug it for any extra information.

### Deployment

Follow the steps inside the respective folder.

### Remote Running

1. Run `pip3 install -r requirements.txt`.
2. Change the details for third party services like storage in `constants.py`.
3. You would need minio object store running somewhere.

- For running minio use: `minio server miniodata`

3. MongoDB is also required for storing action states.

- For mongod use: `mongod --config /usr/local/etc/mongod.conf --fork`.

4. To run a specific orchestrator, go over to `run-orchestrator.py` and change the import accordingly. You will be able to run the orchestrator, voila.
