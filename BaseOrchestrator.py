import requests
import urllib3
import asyncio
import logging

from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient, collection, UpdateOne

from typing import List

from object_store import store
from constants import MONGO_HOST, MONGO_PORT


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
client = MongoClient(MONGO_HOST, MONGO_PORT)


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler('logfile.log')
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    fh.setFormatter(formatter)

    logger.addHandler(fh)

    return logger


class BaseOrchestrator:
    def __init__(self, auth) -> None:
        self.auth = auth
        self.url = "https://localhost:31001/api/v1/namespaces"
        self.logger = get_logger('transcoder')
        self.store = store.ObjectStore(
            db_config={'MONGO_HOST': MONGO_HOST, 'MONGO_PORT': MONGO_PORT})
        self.orch_id = None
        self.actions_ids = set()
        self.orch_collection: collection.Collection = client['openwhisk']['orchestrations']
        self.db_collection: collection.Collection = client['openwhisk']['actions']

    def start(self, name: str):
        """
        Creates an orhcestration id for associating to every action that is made.
        """
        self.orch_id = self.orch_collection.insert_one({
            'name': name,
            'creation_ts': datetime.now(),
        }).inserted_id
        self.orch_start = datetime.now()

    def __get_call(self, api_url):
        """
        Makes a GET api call to the given url with insecure flag as true.
        Used for polling and getting the data.
        Parameters
        ----------
        api_url : str
            Url to fetch

        Returns
        -------
        dict
            json response from the api call

        """
        response = requests.get(api_url, auth=self.auth, verify=False)
        return response.json()

    def __post_call(self, api_url, action_id, params):
        """
        Makes a POST api call to the given url with insecure flag as true.
        Used for invoking openwhisk action.
        Parameters
        ----------
        api_url : str
            Url to use
        action_id: ObjectId
            to be passed as a context to the action
        params: dict
            parameters to be passed to action being invoked

        Returns
        -------
        dict
            json response from the api call

        """
        headers = {"Content-Type": "application/json"}
        context = {"action_id": str(action_id), "orch_id": str(self.orch_id)}
        self.actions_ids.add(action_id)
        response = requests.post(
            api_url, headers=headers, auth=self.auth, verify=False, json={**params, "context": context})

        return response.json()

    def _get_active_ids(self):
        """    
        returns non None items in the activation_ids array.
        Used for finding the number of active actions at the time. 
        """
        return list(
            filter(lambda x: x is not None, self.activation_ids))

    def prepare_action(self, name, params):
        """
        Creates a request body that can be passed to make_action function

        Parameters
        ----------
        name : str
            The name of action
        params : obj
            The parameters which we are supposed to pass to the action.

        Returns
        -------
        object: containing the request body

        """
        return {
            'name': name,
            'body': params,
        }

    async def __poller(self, num_to_poll):
        """
        Polling function that keeps running in the event loop.

        Parameters
        ----------
        num_to_poll : number
            The number of action that the function will poll before it stops

        Returns
        -------
        dict[]
            final response from all the actions that were polled.

        """
        def _get_url(activation_id):
            """
            returns a url that can be used for polling and getting details for a particular activation id.
            """
            return "{}/guest/activations/{}".format(self.url, activation_id)

        num_polled = 0
        results = [None]*num_to_poll

        while num_polled < num_to_poll:
            self.logger.info("Polling for: {}".format(self._get_active_ids()))
            for index, act_id_object in enumerate(self.activation_ids):
                if act_id_object is None:
                    continue

                action_id = act_id_object['action_id']
                activation_id = act_id_object['activation_id']

                url = _get_url(activation_id=activation_id)

                responseData = self.__get_call(url)
                if responseData.get('end', None) is None:
                    continue

                result = responseData.get('response').get('result')
                print(result)
                time_taken = datetime.now() - self.start_times[activation_id]
                update_changes = {
                    '$push': {'attempts': {'start': self.start_times[activation_id], 'end': datetime.now(), 'time': time_taken.total_seconds(), 'orch_id': self.orch_id}}
                }
                self.db_collection.update_one(
                    {'_id': action_id}, update_changes)
                if result.get('error', None) is not None:
                    self.logger.info(
                        "[{}] Poll completed with error for: {} in: {}".format(action_id, activation_id, time_taken))
                    results[index] = {
                        'success': False,
                        'error': result.get('error'),
                        'action_id': action_id,
                    }
                else:
                    self.logger.info(
                        "[{}] Poll completed for: {} in: {}".format(action_id, activation_id, time_taken))
                    results[index] = {
                        'success': True,
                        'result': result,
                        'action_id': action_id,
                    }

                num_polled = num_polled+1
                self.activation_ids[index] = None

            await asyncio.sleep(1)

        return results

    async def __make_action(self, actions, parallelisation=2):
        """
        Invokes openwhisk actions considering parallelisation into account. Note that this has nothing to do with retry mechanisms.
        This is like a lower level of caller. This is also responsible for invoking the poller.
        Parameters
        ----------
        actions : dict[]
            A array of multiple actions each containing action_id, action_name, and action_params
        parallelisation: int
            The maximum concurrency that is allowed

        Returns
        -------
        dict[]
            response from all the actions.

        """
        self.start_times = dict()
        start = datetime.now()

        self.logger.info('Invoking Action requested for {} with {} in parallel'.format(
            len(actions), parallelisation))

        self.activation_ids = [None] * len(actions)

        poller_task = asyncio.create_task(self.__poller(len(actions)))

        def _get_url(action_name):
            return "{}/guest/actions/{}".format(self.url, action_name)

        i = 0
        while i < len(actions):
            action = actions[i]
            active_ids = self._get_active_ids()
            if len(active_ids) >= parallelisation:
                await asyncio.sleep(0.5)
                continue
            print(f"Performing action for: {action}")
            action_response = self.__post_call(
                _get_url(action['name']), action['action_id'], action['body'])
            activation_id = action_response['activationId']
            self.activation_ids[i] = {
                'activation_id': activation_id, 'action_id': action['action_id']}
            attempt_ts = datetime.now()
            update_changes = {
                '$set': {'last_attempt_ts': attempt_ts},
                '$push': {'activation_ids': activation_id}
            }
            self.db_collection.update_one(
                {'_id': action['action_id']}, update_changes)
            self.start_times[activation_id] = attempt_ts
            i += 1

        await poller_task
        results = poller_task.result()

        end = datetime.now()
        self.logger.info(
            'All the actions for this request completed in: {}'.format(end-start))
        return results

    async def __make_action_with_id_for_object_issues(self, action_key_map, retries=3, parallelisation=2, ignore_objects_error=[]):
        """
        When an action throws NoSuchKeyException this retry handler is called. It gets the action_id which was responsible for writing the object
        with that particular key and retries those actions to recreate the objects before returning the control for the main function to retry the 
        original action again. 
        This is a recursive function.

        Parameters
        ----------
        action_key_map : dict[]
            The dict is of action_id and the key that was responsible.

        retries: number
            Number of retries for the parent

        parallelisation: number
            maximum number of concurrency for parent objects to run

        ignore_object_errors: str[]
            It stores the key of all the objects for which retries have been done. This is kept as a check so that an issue for the same key should not be
            solved again and again.

        Returns
        -------
        dict[]
            response from all the parent actions.

        """
        parent_actions = self.store.get_action_ids_for_objects(
            list(map(lambda mp: mp['key'], action_key_map)))
        results = [None] * len(action_key_map)
        action_parent_map = {}
        action_index_map = {}
        for i, action_key in enumerate(action_key_map):
            action_id = action_key['action_id']
            action_index_map[action_id] = i
            action_parent_map[action_id] = parent_actions[i]

        # calling parents to create those objects
        print("action_parent_map: ", action_parent_map)
        parent_results = await self.__make_action_with_id(
            list(set(parent_actions)), retries, parallelisation, ignore_objects_error, object_ownership=True)
        parent_results_dict = {}
        for result in parent_results:
            parent_action_id = result['action_id']
            parent_results_dict[parent_action_id] = result
        retry_action_ids = []
        for action_key in action_key_map:
            action_id = action_key['action_id']
            parent_action_id = action_parent_map[action_id]
            parent_action_result = parent_results_dict[parent_action_id]
            # retrying only for those actions whose objects might be created
            if parent_action_result['success']:
                retry_action_ids.append(action_id)

        # retrying actions for which parents were successful
        retry_results = await self.__make_action_with_id(
            retry_action_ids, 0, parallelisation, ignore_objects_error, object_ownership=True)
        for result in retry_results:
            action_id = result['action_id']
            index = action_index_map[action_id]
            results[index] = result

        return results

    async def __make_action_with_id_for_multiparent_object_issues(self, action_key_map, retries=3, parallelisation=2, ignore_objects_error=[]):
        """
        Same as __make_action_with_id_for_object_issues. This function is used when object_ownership is false and is less optimal to handle lesser edge cases.

        Parameters
        ----------
        action_key_map : dict[]
            The dict is of action_id and the key that was responsible.

        retries: number
            Number of retries for the parent

        parallelisation: number
            maximum number of concurrency for parent objects to run

        ignore_object_errors: str[]
            It stores the key of all the objects for which retries have been done. This is kept as a check so that an issue for the same key should not be
            solved again and again.

        Returns
        -------
        dict[]
            response from all the parent actions.

        """

        # finding parents
        parent_actions = self.store.get_all_action_ids_for_objects(
            list(map(lambda mp: mp['key'], action_key_map)))

        parent_action_result_map = {}
        retry_action_ids = []

        # executing it one by one because inside a list item, all the action_ids are in order
        # would become too complicated if parallelism across different list items is tried
        for i, parent_action_list in enumerate(parent_actions):
            execute_child = True

            for parent_action_id in parent_action_list:
                if parent_action_id in parent_action_result_map:  # already executed befre
                    if parent_action_result_map[parent_action_id]:
                        continue
                    else:
                        execute_child = False
                        break
                else:  # if executing this parent for the first time
                    action_result = await self.__make_action_with_id([parent_action_id], retries, parallelisation, ignore_objects_error, object_ownership=False)
                    action_success = action_result[0]['success']
                    parent_action_result_map[parent_action_id] = action_success
                    if not action_success:
                        execute_child = False
                        break

            if execute_child:
                retry_action_ids.append(action_key_map[i]['action_id'])

        results = [None] * len(action_key_map)
        # retrying actions for which parents were successful

        # we can use the hashing by parent_action_result_map here - however not useful,
        # because in parent that implies it should not have been failed section as it has run once already
        retry_results = await self.__make_action_with_id(
            retry_action_ids, 0, parallelisation, ignore_objects_error, object_ownership=False)

        action_index_map = {}
        for i, action_key in enumerate(action_key_map):
            action_id = action_key['action_id']
            action_index_map[action_id] = i

        for result in retry_results:
            index = action_index_map[result['action_id']]
            results[index] = result

        return results

    async def __make_action_with_id(self, action_ids, retries=3, parallelisation=2, ignore_objects_error=[], object_ownership=True):
        """
        This function handles retries and invoking the openwhisk action.

        Parameters
        ----------
        action_ids : ObjectId[]
            List of action ids (details present in document store) which are to be invoked.

        retries: number
            Number of retries for the parent

        parallelisation: number
            maximum number of concurrency for parent objects to run

        ignore_object_errors: str[]
            It stores the key of all the objects for which retries have been done. This is kept as a check so that an issue for the same key should not be
            solved again and again.

        object_ownership: boolean
            This signifies whether there are multiple actions that write onto a single key or if a single ownership exists.

        Returns
        -------
        dict[]
            response from all the parent actions.

        """
        actions_info = list(self.db_collection.find(
            {'_id': {'$in': action_ids}}))
        actions = [{
            'action_id': info['_id'],
            'name': info['action_name'],
            'body': info['action_params']} for info in actions_info
        ]
        results = [{"success": False, "action_id": id} for id in action_ids]

        curr_original_map = [i for i in range(len(actions))]
        next_actions = [*actions]

        count = 0
        while next_actions and count <= retries:
            curr_result = await self.__make_action(next_actions, parallelisation)
            next_iteration = []
            action_results = []  # used for updating details in DB
            object_issues = []

            for i, res in enumerate(curr_result):
                original_index = curr_original_map[i]
                if not res['success']:
                    error = res['error']
                    action_results.append({
                        'error': error,
                        'success': False,
                        'action_id': res['action_id']
                    })
                    results[original_index] = res
                    # if no such key need to retry in a different way by adding it to object_issues list
                    if isinstance(error, dict) and error.get('code', 500) == 'NoSuchKey' and 'key' in error.get('meta', {}) and error['meta']['key'] not in ignore_objects_error:
                        # ignore the error for the next time
                        ignore_objects_error.append(error['meta']['key'])
                        object_issues.append(
                            {
                                'index': original_index,
                                'key': error['meta']['key']
                            }
                        )
                    else:
                        next_iteration.append(original_index)
                else:
                    results[original_index] = res
                    action_results.append(
                        {'error': None, 'success': True, 'action_id': res['action_id']})

            # if object issues need to retry the parent action to create the object again
            if object_issues:
                object_issues_actions = [
                    {
                        'action_id': actions[object['index']]['action_id'],
                        'key': object['key']
                    } for object in object_issues
                ]

                object_issue_retry_func = self.__make_action_with_id_for_multiparent_object_issues if not object_ownership \
                    else self.__make_action_with_id_for_object_issues

                object_issue_retry_result = await object_issue_retry_func(
                    object_issues_actions, retries, parallelisation, ignore_objects_error)
                for i, res in enumerate(object_issue_retry_result):
                    if not res:  # if issue from parent, does nothing
                        continue
                    action_id = res['action_id']
                    if not res['success']:
                        action_result = {
                            'error': res['error'],
                            'success': False,
                            'action_id': action_id
                        }
                    else:
                        action_result = {
                            'error': None,
                            'success': True,
                            'action_id': action_id
                        }
                    for j, result in enumerate(action_results):
                        if result['action_id'] == action_id:
                            action_results[j] = action_result

                    results[object_issues[i]['index']] = res

            update_operations = []
            for item in action_results:
                filter_criteria = {'_id': item['action_id']}
                update_operations.append(
                    UpdateOne(filter_criteria, {'$set': {'error': item['error']}}))
            self.db_collection.bulk_write(update_operations)

            curr_original_map = []
            next_actions = []
            for unsuccessful in next_iteration:
                curr_original_map.append(unsuccessful)
                next_actions.append(actions[unsuccessful])
            if next_actions:
                print("Exhausted: {} retries. Have {} actions left".format(
                    count, len(next_actions)))
            count = count + 1

        if next_actions:
            print("Retries exceeded, still have {} actions with error".format(
                len(next_actions)))
        else:
            print("All actions completed successfully")

        return results

    async def make_action(self, actions, retries=3, parallelisation=2, object_ownership=True):
        """
        This writes action records to document store and calls __make_action_with_id.

        Parameters
        ----------
        actions : ObjectId[]
            List of actions (name and parameters) which are to be invoked.

        retries: number
            Number of retries for the parent

        parallelisation: number
            maximum number of concurrency for parent objects to run

        object_ownership: boolean
            This signifies whether there are multiple actions that write onto a single key or if a single ownership exists.

        Returns
        -------
        dict[]
            response from all the parent actions.

        """
        if not self.orch_id:
            print('Orchestrator not started')
            raise Exception('Orchestrator not started')

        action_ids = self.db_collection.insert_many([{
            'orch_id': self.orch_id,
            'action_name': action['name'],
            'action_params': action['body'],
            'creation_ts': datetime.now(),
            'num_attempts': 0,
            'activation_ids': []
        } for action in actions]).inserted_ids

        results = await self.__make_action_with_id(action_ids, retries, parallelisation, object_ownership=object_ownership)
        return results

    def stop(self):
        """
        This marks the end of the orchestrator. It prints a few metrics that have been instrumented throughout and stores a few more details
        to the document store.
        """
        orch_finish_ts = datetime.now()
        self.time_taken = (orch_finish_ts - self.orch_start).total_seconds()

        self.action_time_taken = 0
        print(
            f'\nOrchestrator {self.orch_id} stopped. It ran for: {self.time_taken}s')

        action_ids = list(self.actions_ids)
        actions_info = list(self.db_collection.find(
            {'_id': {'$in': action_ids}}))
        action_object_metrics = self.store.get_metrics_for_actions(
            self.orch_id, action_ids)
        print("\n** Metrics **")
        print("=============")
        print()
        print("** Action Metrics **")
        print("--------------------")
        print(f"Number of actions: {len(action_ids)}")
        for i, info in enumerate(actions_info):
            action_id = info['_id']
            print()
            print(f"Action {i+1}:")
            print(f"Name - {info['action_name']}")
            print(f"Body - {str(info['action_params'])}")
            attempts = list(
                filter(lambda attempt: attempt['orch_id'] == self.orch_id, info['attempts']))
            print(f"Number of attempts - {len(attempts)}")
            if len(attempts) == 1:
                print(f"Time taken - {attempts[0]['time']}")
                self.action_time_taken += attempts[0]['time']
            else:
                for i, attempt in enumerate(attempts):
                    print(f"Attempt {(i+1)} - Time Taken: {attempt['time']}")
                    self.action_time_taken += attempt['time']
            if action_id in action_object_metrics['metrics']:
                print("Data read: {}".format(
                    action_object_metrics['metrics'][action_id]['object_read_sz']))
                print("Data written: {}".format(
                    action_object_metrics['metrics'][action_id]['object_write_sz']))
        print()
        print("** Object Metrics **")
        print("--------------------")
        print(
            f"Total number of objects read: {len(action_object_metrics['objects_read'])}")
        print(
            f"Total size of objects read: {action_object_metrics['total_object_read_sz']}")
        print(
            f"Total number of objects written: {len(action_object_metrics['objects_written'])}")
        print(
            f"Total size of objects written: {action_object_metrics['total_object_write_sz']}")

        object_metrics = self.store.get_metrics_for_objects(
            self.orch_id, action_object_metrics['objects_read'].union(action_object_metrics['objects_written']))
        object_metrics = sorted(
            object_metrics, key=lambda x: x['put_time'] or x['get_time'])

        output_object_metrics = []
        for object in object_metrics:
            print()
            print(f"Object name: {object['object']}")
            if object['lifetime']:
                print(f"Lifetime: {object['lifetime']}")
                print(
                    f"Object Orchestration Lifetime: {datetime.utcnow() - object['put_time']}")
            elif object['get_time']:
                print(f"Last Get: {object['get_time']}")
            elif object['put_time']:
                print(f"First Put: {object['put_time']}")
                print(
                    f"Object Orchestration Lifetime: {datetime.utcnow() - object['put_time']}")
            if object['put_size']:
                output_object_metrics.append({
                    'name': object['object'],
                    'lifetime': (datetime.utcnow() - object['put_time']).total_seconds(),
                    'size_written': object['put_size'],
                })

        self.orch_collection.update_one(
            {'_id': self.orch_id}, {'$set': {
                'finish_ts': orch_finish_ts,
                'time_taken': self.time_taken,
                'action_time_taken': self.action_time_taken,
                'object_metrics': output_object_metrics,
            }})

    def get_orch_details(self, orch_id):
        """
        This returns details that were saved at the orchestration level in the document store.

        Parameters
        ----------
        orch_id : ObjectId
            The orchestrator id for which details are required.

        Returns
        -------
        dict
            data saved for the orchestration

        """
        if not isinstance(orch_id, ObjectId):
            orch_id = ObjectId(orch_id)

        orch_details = self.orch_collection.find_one({'_id': orch_id})
        if not orch_details:
            raise Exception('Orchestration with such id does not exists.')

        return orch_details
        # print(action_object_metrics['objects_used'])

    def get_all_orchs(self, orch_name: str) -> List[ObjectId]:
        """
        This returns all the orchestration ids associated with the name

        Parameters
        ----------
        orch_name : str
            The orchestrator name for which ids are required.

        Returns
        -------
        str[]
            ids saved for the orchestration

        """
        orch_ids = []
        results = self.orch_collection.find({'name': orch_name})
        for res in results:
            orch_ids.append(res['_id'])

        return orch_ids
        # print(action_object_metrics['objects_used'])

    def get_all_actions_for_id(self, action_name: str) -> List[ObjectId]:
        """
        This returns all the action ids associated with the name

        Parameters
        ----------
        action_name : str
            The action name for which ids are required.

        Returns
        -------
        str[]
            ids saved for the action

        """
        action_ids = []
        results = self.db_collection.find({'action_name': action_name})
        for res in results:
            action_ids.append(res['_id'])

        return action_ids
        # print(action_object_metrics['objects_used'])

    def get_action_details(self, action_id: ObjectId):
        """
        This returns details that were saved at the action and the action-store level in the document store.

        Parameters
        ----------
        action_id : ObjectId
            The action id for which details are required.

        Returns
        -------
        dict
            data saved for the action

        """
        time_taken = 0
        action_info = self.db_collection.find_one({'_id': action_id})
        for attempt in action_info['attempts']:
            time_taken += attempt['time']

        time_taken /= len(action_info['attempts'])
        action_object_metrics = self.store.get_metrics_for_actions(
            action_ids=[action_id])

        if not action_object_metrics:
            return {
                "time_taken": time_taken,
                'object_metrics': [],
            }

        object_metrics = self.store.get_metrics_for_objects(
            objects=action_object_metrics['objects_written'])

        output_object_metrics = []
        for object in object_metrics:
            if object['put_size']:
                output_object_metrics.append({
                    'name': object['object'],
                    'lifetime': (datetime.utcnow() - object['put_time']).total_seconds(),
                    'size_written': object['put_size'],
                })

        return {
            'time_taken': time_taken,
            'object_metrics': output_object_metrics,
        }


async def main():
    auth = ("23bc46b1-71f6-4ed5-8c54-816aa4f8c502",
            "123zO3xZCLrMN6v2BKK1dXYFpXlPkccOFqm12CdAsMgRU4VrNZ9lyGVCGuMDGIwP")
    orch = BaseOrchestrator(auth)
    await orch.__make_action_with_id([ObjectId('65b7c55447f9174830c07c6f')], 1)


if __name__ == '__main__':
    asyncio.run(main())

# beautify the code
