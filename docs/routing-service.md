
# Routing Service

The **Routing Service** maintains a registry of objects and streaming queues that are distributed across multiple MemoryGrid instances in the network. It also tracks the replicas of each object that may exist across different FrameDBs under the same object ID.

### Core Functions of the Routing Service:

1. Maintain a list of object IDs currently stored across all MemoryGrid instances in the network.

2. Store metadata associated with each object to enable search and discovery.

3. Record the MemoryGrid instance ID for each object, allowing querying services to locate the object efficiently.

4. Maintain a list of in-memory streaming queues along with their associated metadata.

## Routing service APIs:

Certainly! Below is the **technical API documentation** for the **Routing Service APIs**, specifically covering the **FrameDBObjectDatabase-related endpoints**. This documentation is structured and suitable for inclusion in developer docs, OpenAPI references, or Postman collections.

---

## Routing Service APIs for objects

These APIs manage the routing metadata for object entries (`FrameDBObject`) across distributed MemoryGrid instances.


### `POST /framedb/objects`

### Create a new MemoryGrid object routing entry

**Description**:
Registers a new object in the routing database, along with its primary MemoryGrid instance and metadata.

**Request Body** (JSON):

```json
{
  "object_id": "obj-1234",
  "framedb_id": "framedb-persistent-1",
  "framedb_type": "persistent",
  "size": 2048,
  "copies": [
    { "framedb_id": "framedb-memory-2", "framedb_type": "memory" }
  ],
  "metadata": {
    "tags": ["image", "raw"],
    "owner": "user_abc"
  }
}
```

**Response**:

* `201 Created` – On successful insertion
* `400 Bad Request` – If input validation or insertion fails

---

### `POST /framedb/objects/<object_id>/update`

#### Update fields of an existing object

**Description**:
Updates metadata or routing fields for an existing object entry.

**Path Parameter**:

* `object_id`: ID of the object to update

**Request Body** (Partial updates allowed):

```json
{
  "framedb_id": "framedb-persistent-2",
  "metadata": { "last_modified": "2025-05-07T12:00:00Z" }
}
```

**Response**:

* `200 OK` – On successful update
* `400 Bad Request` – If no update performed or request is invalid

---

### `DELETE /framedb/objects/<object_id>`

#### Delete a routing entry

**Description**:
Removes the routing metadata for the specified object.

**Path Parameter**:

* `object_id`: ID of the object to delete

**Response**:

* `200 OK` – If deletion was successful
* `404 Not Found` – If no such object exists

---

### `GET /framedb/objects/<object_id>`

#### Retrieve object routing information

**Description**:
Returns all routing and metadata information for a given object.

**Response**:

```json
{
  "success": true,
  "data": {
    "object_id": "obj-1234",
    "framedb_id": "framedb-persistent-1",
    "framedb_type": "persistent",
    "copies": [
      { "framedb_id": "framedb-memory-2", "framedb_type": "memory" }
    ],
    "size": 2048,
    "metadata": { "tags": ["image", "raw"] }
  }
}
```

* `200 OK` – If found
* `404 Not Found` – If not found

---

### `GET /framedb/objects`

#### Query routing entries

**Description**:
Returns a list of routing objects matching an optional filter.

**Request Body** (optional):

```json
{
  "metadata.tags": "image"
}
```

**Response**:

* `200 OK` – On successful query
* `400 Bad Request` – If query format is invalid

---

### `POST /framedb/objects/<object_id>/add-copy`

#### Add a new replica location

**Description**:
Appends a new copy location to the object.

**Request Body**:

```json
{
  "framedb_id": "framedb-backup-3",
  "framedb_type": "persistent"
}
```

**Response**:

* `200 OK` – If added
* `400 Bad Request` – If already exists or invalid

---

### `POST /framedb/objects/<object_id>/remove-copy`

#### Remove a replica location

**Request Body**:

```json
{
  "framedb_id": "framedb-backup-3"
}
```

**Response**:

* `200 OK` – If removed
* `404 Not Found` – If not present

---

### `GET /framedb/objects/<object_id>/copy-exists/<framedb_id>`

#### Check if a copy exists

**Description**:
Returns whether a given `framedb_id` is listed as a replica location for the object.

**Response**:

```json
{
  "success": true,
  "message": "Copy exists"
}
```

* `200 OK` – If found
* `404 Not Found` – If not found

Great — here is the **technical API documentation** for the **Streaming APIs** of the Routing Service, covering `StreamsObject` operations. These APIs manage stream queue registrations, metadata, and updates across MemoryGrid in-memory instances.

---

## Routing Service API — Streaming (StreamsObject) Endpoints

These endpoints manage list in-memory **stream queues** and their metadata in the MemoryGrid network.


### `POST /framedb/streams`

#### Register a new stream queue

**Description**:
Registers a new in-memory stream queue, mapping a unique `queue_name` to a `framedb_id` and optional metadata.

**Request Body**:

```json
{
  "queue_name": "video-stream-abc",
  "framedb_id": "framedb-memory-1",
  "metadata": {
    "source": "camera-12",
    "stream_type": "video",
    "tags": ["live", "HD"]
  }
}
```

**Response**:

* `201 Created` – If inserted successfully
* `400 Bad Request` – If input is invalid or `queue_name` already exists

---

### `POST /framedb/streams/<queue_name>/update`

#### Update an existing stream’s routing or metadata

**Description**:
Updates the routing information or metadata associated with a registered stream queue.

**Path Parameter**:

* `queue_name`: The unique name of the stream

**Request Body**:

```json
{
  "framedb_id": "framedb-memory-2",
  "metadata": {
    "stream_type": "video",
    "last_updated": "2025-05-07T11:30:00Z"
  }
}
```

**Response**:

* `200 OK` – If the stream was updated
* `400 Bad Request` – If update failed or stream not found

---

### `DELETE /framedb/streams/<queue_name>`

#### Deregister a stream queue

**Description**:
Deletes the routing entry for the given stream queue.

**Path Parameter**:

* `queue_name`: The stream queue to delete

**Response**:

* `200 OK` – If deleted successfully
* `404 Not Found` – If the stream queue does not exist

---

### `GET /framedb/streams/<queue_name>`

#### Retrieve stream queue metadata and location

**Description**:
Fetches full metadata and routing information for a specific stream.

**Response**:

```json
{
  "success": true,
  "data": {
    "queue_name": "video-stream-abc",
    "framedb_id": "framedb-memory-1",
    "metadata": {
      "source": "camera-12",
      "stream_type": "video"
    }
  }
}
```

* `200 OK` – If stream is found
* `404 Not Found` – If not registered

---

### `GET /framedb/streams`

#### List all or filtered stream queues

**Description**:
Returns all stream routing entries or filtered ones based on metadata.

**Request Body** (optional, only for JSON request):

```json
{
  "metadata.source": "camera-12"
}
```

**Response**:

* `200 OK` – List of matched streams
* `400 Bad Request` – If query is malformed

---