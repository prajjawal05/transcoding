# Openwhisk Orchestration

### Openwhisk

Apache OpenWhisk is an open source, distributed Serverless platform that executes functions (fx) in response to events at any scale. You can run function you want in there. OpenWhisk supports a growing list of your favorite languages such as Go, Java, NodeJS, .NET, PHP, Python, Ruby, Rust, Scala, Swift.

### Repository

This repository is structured in a way it can hold multiple actions.

#### Actions

At the time this readme was written, it had three sample applications: [chatbot](https://github.com/prajjawal05/transcoding/tree/main/chatbot), [transcoder](https://github.com/prajjawal05/transcoding/tree/main/transcoder) and a [sample](https://github.com/prajjawal05/transcoding/tree/main/sample). Each of those will be explained in detail inside the directories.

#### Object Store

At the root level there is an `object_store` package which connects application to any object store. This is added in the middle to aid with instrumentation and minimal changes at the application level in case there is a need to change the object store. `setup.py` helps distribute this folder as a package.

#### Base Orchestrator

There is a file called `BaseOrchestrator.py`. Application owners who want to write an orchestrator for their action or even just a caller can use this file. There are a few things which have been built into this file some of which are listed below:

1. You can call/invoke Openwhisk actions using the functions in this file instead of making some api call.
2. If the actions are asynchronous, it would even poll for their completion status.
3. Multiple actions can be invoke at a time with the option to control the concurrency and the retries.
4. In case retries > 0 is given, it would rerun the actions which are failing. If there is a `NoSuchKeyExists` error it would rerun the actions which were responsible for creating the object in the first place which in turn would follow the same retry principle as it goes up the chain.
5. It tries to instrument as many things as possible in a MongoDB collection.
6. It logs information in a file along with the orchestration ID generated for each orchestration.

#### Constants

`constants.py` has the details related to hosts and port used for document storage and object storage layer as well as any access keys if present.

#### Kind Cluster

Kind should be running somewhere probably over docker.

To setup cluster, run:
`sh start-cluster.sh`.

To delete cluster, run:
`kind delete cluster --name kind`

### Existing action

If you plan on running existing actions follow this [document](https://github.com/prajjawal05/transcoding/blob/main/Setting-up.md).

### Creating Action

If you plan on running existing actions follow this [document](https://github.com/prajjawal05/transcoding/blob/main/Create-Action.md).
