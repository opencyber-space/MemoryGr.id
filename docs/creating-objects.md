Certainly. Below is the **technical documentation** for the FrameDB gRPC-based object service, including a full overview, API description, architecture, and usage examples.

---

# **FrameDB Object Service Documentation**

---

## **1. Service Overview**

The FrameDB Object Service is a gRPC-based distributed storage abstraction layer designed to support **three types of data sinks**:

* **In-memory**: Redis-based fast key-value access
* **Persistent storage**: TiDB-based durable storage
* **Streams**: Redis-based list queues for producer-consumer pipelines

It integrates with the **FrameDBClusterClient** and **Routing Service APIs** to dynamically resolve data storage locations and manages efficient connection handling using an **LFU cache** for performance.

---

## **2. Functionalities**

The FrameDB Object Service exposes the following functionalities via gRPC:

| Operation   | Description                                                   |
| ----------- | ------------------------------------------------------------- |
| `SetObject` | Stores an object in the appropriate backend based on its type |
| `GetObject` | Retrieves an object by its key using routing resolution       |

---

## **3. gRPC API Definitions**

### **Message: Object**

```proto
message Object {
  string key = 1;
  string framedb_id = 2;
  bytes data = 3;
  string metadata = 4;  // JSON-encoded metadata
  string type = 5;      // one of: "in-memory", "storage", "stream"
}
```

### **Service: ObjectService**

```proto
service ObjectService {
  rpc SetObject(SetObjectRequest) returns (SetObjectResponse);
  rpc GetObject(GetObjectRequest) returns (GetObjectResponse);
}
```

### **SetObjectRequest / Response**

```proto
message SetObjectRequest {
  Object object = 1;
}

message SetObjectResponse {
  bool success = 1;
  string message = 2;
  string key = 3; // returned key (generated if empty)
}
```

### **GetObjectRequest / Response**

```proto
message GetObjectRequest {
  string key = 1;
}

message GetObjectResponse {
  bool found = 1;
  Object object = 2;
  string message = 3;
}
```

---

## **4. Architecture and Internal Behavior**

### **4.1 Key Components**

* **FrameDBClusterClient**: Resolves FrameDB instance metadata using HTTP APIs.
* **ObjectRoutingClient / StreamRoutingClient**: Registers and queries object and stream routing metadata.
* **RedisInterface / TiDBInterface**: Backend interfaces for Redis and TiDB connectivity.
* **LFU Connection Cache**: Caches Redis and TiDB client instances per `framedb_id`, with size controlled by the environment variable `CONNECTIONS_CACHE_ENV_SIZE`.

### **4.2 Data Flow for `SetObject`**

1. If `key` is empty, a UUIDv4 key is generated.
2. FrameDB instance is fetched from the cluster service.
3. If the instance's cluster matches `CLUSTER_ID`, its `local_url` is used; otherwise, `public_url`.
4. Depending on `type`:

   * `in-memory` → Redis `SET`
   * `storage` → TiDB `REPLACE`
   * `stream` → Redis `LPUSH`
5. Routing service is updated via the appropriate client.

### **4.3 Data Flow for `GetObject`**

1. The object key is first resolved using the ObjectRoutingClient.

   * If not found, a fallback to StreamRoutingClient is attempted.
2. A preferred copy from the current cluster is selected.
3. The associated FrameDB instance is resolved.
4. Depending on `type`:

   * `in-memory` → Redis `GET`
   * `storage` → TiDB `SELECT`
   * `stream` → Redis `RPOP`

---

## **5. gRPC Usage Examples (Python)**

### **5.1 Set Object to Memory**

```python
import grpc
import framedb_pb2
import framedb_pb2_grpc

channel = grpc.insecure_channel("localhost:50051")
stub = framedb_pb2_grpc.ObjectServiceStub(channel)

response = stub.SetObject(framedb_pb2.SetObjectRequest(
    object=framedb_pb2.Object(
        key="",  # let server generate
        framedb_id="memory-db-01",
        data=b"sample-data",
        metadata='{"source": "test-client"}',
        type="in-memory"
    )
))
print(response.success, response.key)
```

---

### **5.2 Set Object to Persistent Storage**

```python
response = stub.SetObject(framedb_pb2.SetObjectRequest(
    object=framedb_pb2.Object(
        key="my-storage-key",
        framedb_id="persistent-db-01",
        data=b"important-data",
        metadata='{"ttl": 3600}',
        type="storage"
    )
))
print(response.success, response.message)
```

---

### **5.3 Push to Stream**

```python
response = stub.SetObject(framedb_pb2.SetObjectRequest(
    object=framedb_pb2.Object(
        key="stream-queue-123",
        framedb_id="stream-db-01",
        data=b"event-payload",
        metadata='{"event_type": "signal"}',
        type="stream"
    )
))
print(response.success, response.message)
```

---

### **5.4 Retrieve Object**

```python
get_response = stub.GetObject(framedb_pb2.GetObjectRequest(
    key="my-storage-key"
))
if get_response.found:
    print(get_response.object.data, get_response.object.type)
else:
    print("Object not found:", get_response.message)
```

---

## **6. Environment Variables**

| Variable                     | Description                              | Example          |
| ---------------------------- | ---------------------------------------- | ---------------- |
| `CLUSTER_ID`                 | Identifier of the current cluster        | `cluster-west-1` |
| `CONNECTIONS_CACHE_ENV_SIZE` | Maximum size of the LFU connection cache | `100`            |

---

## **7. Summary**

This service abstracts the storage of binary objects across multiple backend types while allowing flexible, scalable, and cluster-aware routing. It ensures:

* Efficient routing using metadata
* Transparent storage logic
* LFU connection reuse for performance
* Clean gRPC contract for client integration

---

