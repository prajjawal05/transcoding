## Create Action

Creating action in openwhisk is really simple. You just need action files which you will deploy. Before doing any of that, first of all create a folder in the root directory of this repository which will store every file related to your action.

The documentation below has been divided into two subsections - action and orchestrator. Writing an orchestrator is completely optional as there might not be a need for that in your application.

### Action

#### Action files

Action files are the ones that will be run on openwhisk platform. Below are some points to make note of:

##### Request/Response

- Ensure your action file has a main() function expecting an argument.
- This argument can be treated as the main json body that was passed when invoking the action and all the attributes of the json can be accessed directly.
- If you are using the BaseOrchestrator through your own orchestrator (which will be discussed in the next section) note these points
  - A context object containing action_id and orch_id will be included as a part of main args.
  - If there is an error be sure to catch it, and return it as:
  ```
  "error": {
      'code': getattr(e, 'code', None),
      "message": str(e),
      'meta': getattr(e, 'meta', None)
  }
  ```
- Return a json object (or dict) because openwhisk is not able to parse the response otherwise.
- Due to the previous point, always make sure to catch the error.

##### Code tools

- If you need an object store, import it from object_store.
- A thing to note about object store - it will create all the bucket that you pass to it during initiation. No need to worry about it.
- Make sure to pass the context that you got from args['context'] to object store functions.
- Use all the host, port and access details from constants.py in the root directory.
- If you need mongo for some reason, you can use its host and port from constants.py as well.

##### Testing

Use the file `run-action-local.py` in the root directory to test your actions. Using this will help resolve dependencies of `object_store` and `constants.py`.

#### Deployment Dependency resolution

_(build-docker.sh)_

- List out the requirements in requirements.txt
- If you plan on using Docker:
  - You can specify the installation there.
  - For object_store follow,
  ```
  1. Copy setup.py and object_store to the current directory.
  2. run `python3 setup.py sdist`
  3. In docker file include:
      COPY dist/object_store-0.1.tar.gz .
      RUN pip install object_store-0.1.tar.gz
  4. remove the object_store and setup.py file
  ```
- If you do not plan on using docker:
  - install all requirements locally using `-t` flag
  - use object_store folder directly

#### Deployment

_(deploy-script.sh)_

- If you have just a single action file with no dependency files. You can use:
  `wsk action create <actionname_you_want> <filename>.py`

- If you have multiple files, you would need to zip the files with entrypoint named as `__main__.py`. You can use:
  `wsk action create <actionname_you_want> action.zip --insecure`

- If you have a docker image that you want to use add an extra flag with the above command:
  `--docker <docker-image-url>`

### Orchestrator (Optional)

As the name suggests, it will help you to orchestrate the actions that have been deployed in openwhisk. There is a [BaseOrchestrator.py](https://github.com/prajjawal05/transcoding/blob/main/BaseOrchestrator.py) file which acts as a boilerplate and helps with many functionalities, the details of which are present [here](https://github.com/prajjawal05/transcoding/blob/main/README.md#base-orchestrator).

#### Building

Steps that will help you with BaseOrchestrator:

- Initialise the BaseOrchestrator class with an auth tuple. Use `wsk property get --auth` to get the data for it.
- As soon as you start your orchestrator, call the `start` function, this will initialise your orchestrator with an orch_id along with a few other things.
- Call `prepare_action` function to get the body for calling actions, something like `orch.prepare_action(action_name, params)`
- Invoke the action by calling `orch.make_action`. This is an asynchronous function and will take in the parameters like list of actions, concurrency limit, retries and object ownership.
- If object ownership is false, i.e, there are many actions which are writing onto a single object sequentially, handling retries would be slower in that case.
- Response would be a list of action response where each item will be a dict. The dict would have a boolean attribute called success which will signify if the action succeeded or not.
- If multiple actions were passed there could be a possibility that the response would have some success result while some failure results.
- Once everything is done, call the `start` function. This will mark the orchestration as completed and will output some metrics.

#### Running

- Make sure your actions are deployed.
- Install the requirements present in `requirements.txt` present in the root level.
- Orchestrator needs MongoDB and the object_store.
  - Ensure your constants.py have the correct value required for both of them.
  - For running minio use: `minio server miniodata`.
  - For mongod use: `mongod --config /usr/local/etc/mongod.conf --fork`.
- Modify `run-orchestrator.py` file and run your orchestrator.
