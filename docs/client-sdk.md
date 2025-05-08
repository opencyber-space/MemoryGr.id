# MemoryGrid SDK Documentation

## Overview

`FrameDBClient` is the official Python SDK to interact with **FrameDB** — a distributed object storage system supporting:

* **In-Memory Queues** (via Redis)
* **Persistent Storage** (via TiDB or MySQL-compatible DBs)
* **Streaming Queues** (via Redis streams)
* **Backup to Object Stores** (like S3 or pluggable backends)
* **In-Memory Caching** (LFU-based cache for fast reads)

This SDK provides a simple, extensible interface to store, retrieve, back up, and stream data from various FrameDB instances.

---

## ⚙️ Initialization

```python
from framedb_sdk import FrameDBClient

client = FrameDBClient(
    cluster_url="http://framedb-cluster",
    routing_url="http://routing-service",
    cache_size_bytes=50 * 1024 * 1024,       # Optional: LFU cache for object data
    connection_cache_size=100                # Optional: LFU cache for DB connections
)
```

---

## Supported Methods

### 1. `set_object(obj: Dict)`

Store a binary object in a FrameDB instance.

```python
client.set_object({
    "key": "user123",
    "data": b"binary-data",
    "framedb_id": "framedb-inmem-1",
    "type": "in-memory",   # or "storage" or "stream"
    "metadata": {"type": "user"}
})
```

---

### 2. `get_object(object_id: str)`

Fetch an object by ID. Uses cache for fast access.

```python
res = client.get_object("user123")
print(res["object"]["data"])
```

---

### 3. `set_pythonic_object(...)`

Serialize and store any Python object (default: `pickle`).

```python
client.set_pythonic_object(
    key="model_snapshot",
    obj={"weights": [1, 2, 3]},
    framedb_id="framedb-storage-1",
    framedb_type="storage"
)
```

You can use custom serializers too (see **Customization** below).

---

### 4. `get_pythonic_object(...)`

Fetch and deserialize a Python object from FrameDB.

```python
res = client.get_pythonic_object("model_snapshot")
print(res["object"]["python_object"])
```

---

### 5. `create_backup(object_id, target_framedb_id)`

Create a backup of an object to another FrameDB instance.

```python
client.create_backup("user123", "framedb-backup-1")
```

---

### 6. `create_bulk_backup(keys: List[str], target_framedb_id)`

Backup multiple objects to another FrameDB.

```python
client.create_bulk_backup(["user123", "model_snapshot"], "framedb-backup-1")
```

---

### 7. `listen_for_stream_data(queue_name, framedb_id)`

Listen to a stream queue (infinite generator):

```python
for msg in client.listen_for_stream_data("frame-events", "framedb-stream-1"):
    print("New event:", msg)
```

---

### 8. `pull_all_stream_data(queue_name, framedb_id)`

Read and drain all messages in a queue (once):

```python
for msg in client.pull_all_stream_data("frame-events", "framedb-stream-1"):
    print(msg)
```

---

### 9. `backup_to_object_storage(...)`

Backs up FrameDB objects to external object storage.

```python
client.backup_to_object_storage(
    keys=["user123", "model_snapshot"],
    framedb_id="framedb-1",
    s3_credentials_dict={
        "bucket": "my-backups",
        "access_key": "...",
        "secret_key": "...",
        "region": "ap-south-1"
    }
)
```

---

### 10. `restore_from_backup(...)`

Restores objects from object storage back into FrameDB.

```python
client.restore_from_backup(
    keys=["user123", "model_snapshot"],
    framedb_id="framedb-restore-1",
    framedb_type="in-memory",
    s3_credentials_dict={...}
)
```

---

## Customization

### Custom Serialization

You can define your own serializer/deserializer class:

```python
import json

class JSONSerializer:
    def serialize(self, obj) -> bytes:
        return json.dumps(obj).encode()

    def deserialize(self, data: bytes):
        return json.loads(data.decode())
```

Then use:

```python
client.set_pythonic_object("my-key", {"a": 1}, "framedb-id", "in-memory", serializer=JSONSerializer())
client.get_pythonic_object("my-key", deserializer=JSONSerializer())
```

---

### Custom Backup Storage Backend

To plug in a non-S3 object storage (e.g., GCS, MinIO, Ceph), implement:

```python
class MyStorageBackend:
    def upload(self, key: str, data: bytes): ...
    def download(self, key: str) -> bytes: ...
```

And use it:

```python
client.backup_to_object_storage(
    keys=["key1"],
    framedb_id="framedb-id",
    custom_backup_storage_backend=MyStorageBackend()
)
```

---

📌 Notes

* FrameDB types: `"in-memory"`, `"storage"`, `"stream"`
* Caching is LFU-based and optimized for memory (in bytes)
* Streaming methods are generators
* Routing fallback for stream vs object is handled internally

---

## 📚 Related Modules

| Module                | Purpose                                 |
| --------------------- | --------------------------------------- |
| `RedisInterface`      | Low-level Redis connection & queue ops  |
| `TiDBInterface`       | Low-level SQL-based object access       |
| `ObjectRoutingClient` | Maintains object → FrameDB mappings     |
| `StreamRoutingClient` | Maintains stream queue mappings         |
| `LFUCache`            | Custom byte-limited LFU in-memory cache |

---
