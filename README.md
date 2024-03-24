# Openwhisk Orchestration

There are multiple actions in this repository. Go to respective folder.

#### Pre-requisites

For orchestrator:

1. Run `pip3 install -r requirements.txt`.
2. You would need minio object store running somewhere.

- For running minio use: `minio server miniodata`

3. MongoDB is also required for storing action states.

- For mongod use: `mongod --config /usr/local/etc/mongod.conf --fork`.

#### Kind Cluster

Kind should be running somewhere probably over docker.
To setup cluster, run:
`sh start-cluster.sh`.

#### Setup Action and Orchestrator

Replace env constants for DB and Object store in `constants.py`.

#### Run

- To test the action: `python3 run-action-local.py`.
- To run the orchestrator: `python3 run-orchestrator.py`.

#### Delete cluster

Use: `kind delete cluster --name kind`
