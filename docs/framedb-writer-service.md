# **MemoryGrid Writer Client Documentation**

## **Overview**

`framedb_writer_client` is a Python SDK for writing data directly to FrameDB clusters. FrameDB is a distributed storage platform that supports three types of data operations:

1. **In-memory object storage** (via Redis)
2. **Persistent object storage** (via TiDB)
3. **Streaming queues** (via Redis list-based streams)

This library offers two modes of operation:

* A high-level **gRPC-based interface** via the `ObjectsAPI`
* A **low-level direct interface** via the `FrameDBWriter` class

It also provides seamless integration with the **FrameDB routing service**, which maintains metadata and storage mappings for all objects and streams.

---

## **Installation**

### Requirements

Ensure Python ≥ 3.8 is installed.

### Install from Source

Clone the repository and install using pip:

```bash
git clone <your-repo-url>
cd framedb_writer_client
pip install .
```

### Dependencies

Dependencies are managed via `requirements.txt` and include:

* `grpcio`, `grpcio-tools`, `protobuf`
* `redis`, `pymysql`, `sqlalchemy`
* `requests`, `cachetools`, `python-dotenv`

---

## **Library Components**

The library is organized into the following core components:

| Module/Class           | Description                                                          |
| ---------------------- | -------------------------------------------------------------------- |
| `ObjectsAPI`           | High-level gRPC interface for memory, storage, and stream operations |
| `FrameDBWriter`        | Direct interface for Redis/TiDB write operations via public URLs     |
| `FrameDBClusterClient` | Queries FrameDB instance metadata (cluster-wide)                     |
| `ObjectRoutingClient`  | Registers and retrieves object routing metadata                      |
| `StreamRoutingClient`  | Registers and retrieves stream (queue) routing metadata              |
| `factory.py`           | Convenience factories for client instantiation                       |

---

## **ObjectsAPI (gRPC Interface)**

### Description

The `ObjectsAPI` class wraps the gRPC `ObjectService`, allowing you to store objects and stream entries through a unified interface. It handles UUID generation, metadata serialization, and key routing automatically.

### Constructor

```python
ObjectsAPI(grpc_address: str)
```

* `grpc_address`: The gRPC endpoint (e.g., `"localhost:50051"`)

### Methods

```python
write_to_memory(framedb_id, data, key=None, metadata=None)
write_to_persistent(framedb_id, data, key=None, metadata=None)
write_to_stream(framedb_id, data, key=None, metadata=None)
```

#### Parameters:

* `framedb_id`: ID of the target FrameDB instance
* `data`: `bytes` to store
* `key`: Optional string key. If not provided, UUID is generated
* `metadata`: Optional dictionary (converted to JSON string)

#### Returns:

`SetObjectResponse`: A gRPC response with `success`, `message`, and `key`.

#### Example Usage:

```python
api = ObjectsAPI("localhost:50051")
resp = api.write_to_memory("mem-db-1", b"sensor-data")
print(resp.success, resp.key)
```

---

## **FrameDBWriter (Direct Writer Interface)**

### Description

The `FrameDBWriter` class enables low-level direct writes to Redis or TiDB by resolving FrameDB instance metadata and performing the appropriate database operations via public URLs.

### Constructor

```python
FrameDBWriter(
    cluster_client: FrameDBClusterClient,
    object_routing_client: Optional[ObjectRoutingClient],
    stream_routing_client: Optional[StreamRoutingClient]
)
```

### Method: `write(...)`

```python
write(
    key: Optional[str],
    framedb_id: str,
    data: bytes,
    type_: str,
    metadata: Optional[Dict[str, Any]] = None,
    update_routing: bool = True
) -> Dict[str, Any]
```

#### Parameters:

* `key`: Object or stream key (auto-generated if `None`)
* `framedb_id`: Target FrameDB ID
* `data`: Raw bytes to store
* `type_`: One of `"in-memory"`, `"storage"`, `"stream"`
* `metadata`: Optional metadata dict for routing
* `update_routing`: If True, updates routing metadata

#### Returns:

A dictionary with:

```python
{
  "success": bool,
  "message": str,
  "key": str
}
```

#### Example Usage:

```python
writer = FrameDBWriter(
    FrameDBClusterClient("http://config-service:5000"),
    ObjectRoutingClient("http://routing-service:5000"),
    StreamRoutingClient("http://routing-service:5000")
)

result = writer.write(
    key=None,
    framedb_id="storage-db-1",
    data=b"log-entry",
    type_="storage"
)

print(result["success"], result["key"])
```

---

## **Factory Functions**

These helpers simplify instantiation of `ObjectsAPI` and `FrameDBWriter`.

```python
from framedb_writer_client.factory import new_objects_api_client, new_framedb_writer

api = new_objects_api_client("localhost:50051")

writer = new_framedb_writer(
    routing_service_url="http://routing-service:5000",
    config_service_url="http://config-service:5000"
)
```

---

## **Internal Connection Caching**

This library maintains an LFU (Least Frequently Used) cache for connection objects to minimize repeated instantiation.

* Controlled via environment variable `CONNECTIONS_CACHE_ENV_SIZE`
* Cache maps `framedb_id` → RedisInterface / TiDBInterface
* Automatically reuses clients and cleans least-used connections

---