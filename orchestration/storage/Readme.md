## Object Store

This acts as a client for communicating to an object store. Right now, it connects with MinIO. This also connects with mongoDB for storing some metrics.

### MinIO

MinIO is a high-performance, S3 compatible object store. It is built for large scale AI/ML, data lake and database workloads. It is software-defined and runs on any cloud or on-premises infrastructure. MinIO is dual-licensed under open source GNU AGPL v3 and a commercial enterprise license.

### Functions exposed

- For initialising, use the following snippet:

```
config = dict(
        STORAGE_ENDPOINT=STORAGE_ENDPOINT,
        AWS_ACCESS_KEY_ID=AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY=AWS_SECRET_ACCESS_KEY
    )
db_config={'MONGO_HOST': MONGO_HOST, 'MONGO_PORT': MONGO_PORT}
store = ObjectStore(config, <bucket_name_array>, db_config)
```

- For uploading a file, use:
  `put_sync(self, context, bucket, file_name)`. This will copy the file from `bucket/file_name` in the local directory of the client.
- For downloading a file, use:
  `put_sync(self, context, bucket, file_name)`. This will copy the file to `bucket/file_name` in the local directory of the client.
- `get_action_ids_for_objects`, `get_all_action_ids_for_objects`, and `get_metrics_for_actions` are all used by BaseOrchestrator for metrics and information collection. This are not supposed to be used directly by the client.
