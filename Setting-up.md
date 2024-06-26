## Setting Up

### Local Setup

If you are using an existing action, following are the steps that will be required:

1. Run `pip3 install -r requirements.txt`.
2. Change the details for third party services like storage in `constants.py`.
3. You would need minio object store running somewhere.

- For running minio use: `minio server miniodata`

3. MongoDB is also required for storing action states.

- For mongod use: `mongod --config /usr/local/etc/mongod.conf --fork`.

4. Go over to the respective action folder for any more details.

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
