from collections import defaultdict, namedtuple
import os
from typing import Any
import minio
from pymongo import MongoClient, collection
from bson import ObjectId
import configparser

from datetime import datetime

client = None

DEFAULT_CONFIG_FILE='/etc/orchestration/config.ini'

def get_default_config():
    assert os.path.exists(DEFAULT_CONFIG_FILE), f'Config file {DEFAULT_CONFIG_FILE} missing'
    c = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    c.read(DEFAULT_CONFIG_FILE)
    return c

def get_mongo_client(config=None):
    global client

    if client is not None:
        return client

    if config is None:
        c = get_default_config()
        MONGO_HOST = c.get('mongo', 'host')
        MONGO_PORT = c.getint('mongo', 'port')
    else:
        MONGO_HOST = config.get('MONGO_HOST')
        MONGO_PORT = config.get('MONGO_PORT')

    print('Using Mongo host: {}'.format(MONGO_HOST))

    client = MongoClient(MONGO_HOST, MONGO_PORT)
    return client


class ObjectStore:
    """
    A simple class that is used connecting to the object store while also storing some metrics in MongoDB.
    """
    client = None
    endpoint = None
    access_key = None
    secret_key = None

    def __init__(self, buckets=[], config = None, db_config=None):
        """
        Initializes object store

        Parameters
        ----------
        config: contains configuration details for connecting to Object store.
        bucket : str[]
            The buckets that you want to create, if it does not already exists.
        db_config : str
            contains configuration details for the document store where metrics will be stored.

        Returns
        -------
        None

        """
        if config is None:
            c = get_default_config()
            self.endpoint = c['minio']['endpoint']
            self.access_key = c['minio']['aws_access_key_id']
            self.secret_key = c['minio']['aws_secret_access_key']
        else:
            self.endpoint = config.get("STORAGE_ENDPOINT")
            self.access_key = config.get("AWS_ACCESS_KEY_ID")
            self.secret_key = config.get("AWS_SECRET_ACCESS_KEY")
        self.db_collection: collection.Collection = get_mongo_client(db_config)['openwhisk']['action_store']

        if not self.endpoint:
            return
        print('Initialising Minio client')

        for bucket in buckets:
            os.makedirs(bucket, exist_ok=True)
        try:
            self.client = minio.Minio(
                self.endpoint, access_key=self.access_key, secret_key=self.secret_key, secure=False)
            for bucket in buckets:
                try:
                    self.client.make_bucket(bucket)
                    print(f"Created bucket: {bucket}")
                except Exception as error:
                    if error.code == "BucketAlreadyOwnedByYou":
                        continue
                    raise error
            print('Initialised Minio client')
        except Exception as e:
            print('Some issue with minio client: ' + e)

    def __mark_object(self, context, object_path, object_size, method):
        action_id = ObjectId(context['action_id'])
        orch_id = ObjectId(context['orch_id'])
        update_changes = {
            '$set': {**context},
            '$push': {
                f"objects_{method}": {
                    'orch_id': orch_id,
                    'object': object_path,
                    'size': object_size,
                    'time': datetime.utcnow()
                }
            }
        }
        self.db_collection.update_one(
            {'_id': action_id},
            update_changes,
            upsert=True
        )

    def __mark_error_get(self, context, object_path):
        action_id = ObjectId(context['action_id'])
        orch_id = ObjectId(context['orch_id'])
        update_changes = {
            '$set': {**context},
            '$push': {
                'error_get': {
                    'orch_id': orch_id,
                    'object': object_path,
                    'time': datetime.utcnow()
                }
            }
        }
        self.db_collection.update_one(
            {'_id': action_id},
            update_changes,
            upsert=True
        )

    def put_sync(self, context, bucket, file_name):
        """
        From the "bucket/file_name" directory, puts the object into bucket and file.

        Parameters
        ----------
        context: contains details for orchestration and action
        bucket : str
            The bucket which has the object
        file_name : str
            The file_name which is the object

        Returns
        -------
        None

        """
        if not self.client:
            return
        object_path = f"{bucket}/{file_name}"
        self.client.fput_object(bucket, file_name, object_path)
        self.__mark_object(context, object_path,
                           os.path.getsize(object_path), 'put')

    def get_sync(self, context, bucket, file_name):
        """
        From the bucket and file, puts the object into "bucket/file_name"

        Parameters
        ----------
        context: contains details for orchestration and action
        bucket : str
            The bucket which has the object
        file_name : str
            The file_name which is the object

        Returns
        -------
        None

        """
        if not self.client:
            return
        object_path = f"{bucket}/{file_name}"
        try:
            object = self.client.fget_object(bucket, file_name, object_path)
            self.__mark_object(context, object_path, object.size, 'get')
        except Exception as e:
            self.__mark_error_get(context, object_path)
            if e.code == 'NoSuchKey':
                raise NoSuchKeyException(e)
            raise e

    def remove_object(self, context, bucket, file_name):
        if not self.client:
            return
        # object_path = f"{bucket}/{file_name}"
        self.client.remove_object(bucket, file_name)

    def get_action_ids_for_objects(self, keys):
        """
        Fetches the action_id that was responsible for writing data to the object store for each key.
        It is generally required for retrying an action when NoSuchKey exception is found.

        Parameters
        ----------
        keys : str[]
            List of object keys for which action ids are required

        Returns
        -------
        str[]
            action id responsible for writing to the object

        """
        objects = []
        for key in keys:
            result = self.db_collection.find_one({"objects_put.object": key})
            if result:
                objects.append(result)

        return list(map(lambda action: ObjectId(action['action_id']), objects))

    def get_all_action_ids_for_objects(self, keys):
        """
        Fetches the action_id that was responsible for writing data to the object store for each key.
        It is generally required for retrying an action when NoSuchKey exception is found and the object ownership is False.


        Parameters
        ----------
        keys : str[]
            List of object keys for which action ids are required

        Returns
        -------
        str[][]
            List of action ids for each key responsible for writing to the object.
            Each individual list is sorted by timestamp.

        """
        objects = []
        for key in keys:
            object_for_key = []
            result = self.db_collection.find({"objects_put.object": key})
            # result = list(self.db_collection.find({"error_get": "*"}))
            for res in result:
                curr = {}
                for obj in res['objects_put']:
                    if obj['object'] == key:
                        curr = {'action_id': res['action_id'], **obj}
                if curr:
                    object_for_key.append(curr)
            object_for_key = sorted(object_for_key, key=lambda x: x['time'])
            if object_for_key:
                objects.append(
                    list(map(lambda action: ObjectId(action['action_id']), object_for_key)))

        return objects

    def get_objects_involved(self, orch_id: ObjectId):
        orch_info = list(self.db_collection.find(
            {'orch_id': str(orch_id)}))
        objects_read = set()
        objects_written = set()

        for info in orch_info:
            for object_read in info.get('objects_get', []):
                if not object_read['orch_id'] == orch_id:
                    continue
                objects_read.add(object_read['object'])
            for object_wrote in info.get('objects_put', []):
                if not object_wrote['orch_id'] == orch_id:
                    continue
                objects_written.add(object_wrote['object'])

        return {
            'objects_read': objects_read,
            'objects_written': objects_written,
        }

    def get_metrics_for_actions(self, orch_id=None, action_ids=[]):
        """
        Fetches the size and number of objects read/write for action and orchestration.

        Parameters
        ----------
        orch_id : str
            Orchestration Id for which metrics is required
        action_ids : str[]
            List of action_ids

        Returns
        -------
        object
            An object consisting of number of object read/write and the total size that is read/write. 
            It also consists of the details action wise.

        """
        actions_info = list(self.db_collection.find(
            {'_id': {'$in': action_ids}}))
        action_metrics = dict()
        objects_read = set()
        objects_written = set()
        total_object_read_sz = 0
        total_object_write_sz = 0

        for info in actions_info:
            object_read_sz = 0
            object_write_sz = 0

            if 'objects_get' in info:
                for object_read in info['objects_get']:
                    if orch_id and not object_read['orch_id'] == orch_id:
                        continue
                    objects_read.add(object_read['object'])
                    object_read_sz += object_read['size']
            if 'objects_put' in info:
                for object_wrote in info['objects_put']:
                    if orch_id and not object_wrote['orch_id'] == orch_id:
                        continue
                    objects_written.add(object_wrote['object'])
                    object_write_sz += object_wrote['size']

            total_object_read_sz += object_read_sz
            total_object_write_sz += object_write_sz

            action_metrics[info['_id']] = {
                'action_id': info['_id'],
                'object_read_sz': object_read_sz,
                'object_write_sz': object_write_sz
            }

        return {
            'objects_read': objects_read,
            'objects_written': objects_written,
            'metrics': action_metrics,
            'total_object_read_sz': total_object_read_sz,
            'total_object_write_sz': total_object_write_sz,
        }

    def get_metrics_for_objects(self, orch_id=None, objects=[]):
        """
        Fetches the earliest put time and latest get time for a pair of object and orchestration.

        Parameters
        ----------
        orch_id : str
            Orchestration Id for which metrics is required
        objects : str[]
            Objects for which metrics is required.

        Returns
        -------
        array_like
            An array of objects, where each element is an object.

        """
        result = []
        for object in objects:
            objects_put_info = self.db_collection.find(
                {"objects_put.object": object})
            put_time = None
            put_size = 0
            for info in objects_put_info:
                if not 'objects_put' in info:
                    continue
                for obj in info['objects_put']:
                    if orch_id and not obj['orch_id'] == orch_id:
                        continue
                    if not obj['object'] == object:
                        continue
                    if not put_time or put_time > obj['time']:
                        put_time = obj['time']
                        put_size += obj['size']

            objects_get_info = self.db_collection.find(
                {"objects_get.object": object})
            get_time = None
            get_size = 0
            for info in objects_get_info:
                if not 'objects_get' in info:
                    continue
                for obj in info['objects_get']:
                    if orch_id and not obj['orch_id'] == orch_id:
                        continue
                    if not obj['object'] == object:
                        continue
                    if not get_time or get_time < obj['time']:
                        get_time = obj['time']
                        get_size += obj['size']

            lifetime = None
            if get_time and put_time:
                lifetime = get_time - put_time
            if not get_time and not put_time:
                continue

            result.append({
                'object': object,
                'put_time': put_time,
                'get_time': get_time,
                'lifetime': lifetime,
                'put_size': put_size,
                'get_size': get_size,
            })

        return result

    def get_putmetrics_for_action_across_orchs(self, orch_ids=[], action_ids=[]):
        """
        Fetches the size write for action and orchestration.

        Parameters
        ----------
        orch_ids : str[]
            Orchestration Ids for which metrics is required
        action_ids : str[]
            List of action_ids

        Returns
        -------
        object
            An object consisting of number object written and their size.

        """
        actions_info = self.db_collection.find({'_id': {'$in': action_ids}})
        metrics = {}
        for info in actions_info:
            action_id = info['_id']
            objects_put = info.get('objects_put', [])

            for object_wrote in objects_put:
                orch_id = object_wrote['orch_id']
                if orch_ids and orch_id not in orch_ids:
                    continue
                object_name = object_wrote['object']

                if orch_id not in metrics:
                    metrics[orch_id] = {}
                if action_id not in metrics[orch_id]:
                    metrics[orch_id][action_id] = {}
                metrics[orch_id][action_id][object_name] = {
                    'object': object_name,
                    'size': object_wrote['size'],
                    'put_time': object_wrote['time']
                }

        return metrics

    def get_details_object_write(self, orch_id, object):
        result = self.db_collection.find_one(
            {"objects_put.object": object, "objects_get.orch_id": orch_id})
        return result

    def get_action_details(self, action_id):
        if not isinstance(action_id, ObjectId):
            action_id = ObjectId(action_id)

        result = self.db_collection.find_one(
            {"_id": action_id})
        return result


class NoSuchKeyException(Exception):
    def __init__(self, e):
        super().__init__(e)
        self.original_exception = e
        self.code = getattr(e, 'code', None)
        self.meta = {
            'key': e._resource[1:]
        }

    def __str__(self) -> str:
        return str(self.original_exception)