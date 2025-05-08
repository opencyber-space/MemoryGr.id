# Creating MemoryGrid In-Memory instances

In-memory MemoryGrid instances can be created using MemoryGrid config service which is deployed by default on the management cluster. Not all clusters support MemoryGrid by default, to enable MemoryGrid for a cluster you need to create the MemoryGrid local config service which takes care of executing the creation/config requests proxied to it by the global config service.


## Creating MemoryGrid local config service

MemoryGrid can be enabled on a cluster by creating the MemoryGrid local config service, the local config service takes care of deployment of creation and configuration MemoryGrid memory instances. 

Certainly. Below is the **revised, professionally written, and technically precise API documentation** for the following endpoints:

* `POST /framedb-config/setup`
* `DELETE /framedb-config/remove`
* `POST /framedb-config/status`


---

### Endpoint: `POST /framedb-config/setup`

Deploys the MemoryGrid Config Service and its supporting infrastructure on the specified Kubernetes cluster.

#### Behavior

This operation performs the following actions:

* Creates the namespace `framedb-config` (if it does not exist)
* Creates a PersistentVolume (PV) and a PersistentVolumeClaim (PVC) for MongoDB with the specified storage size
* Deploys a MongoDB instance with storage mounted at `/data/db`
* Creates a ClusterIP service named `framedb-local-config` to expose MongoDB within the cluster
* Deploys the MemoryGrid Config Service container with the environment variable `MONGO_URL` pointing to the internal MongoDB service
* Exposes the MemoryGrid Config Service via a NodePort service named `framedb-config-service` on port `32566`

#### Request

* **Method**: `POST`
* **URL**: `/framedb-config/setup`
* **Content-Type**: `application/json`

#### Request Body Parameters

| Field          | Type   | Required | Description                                                                                           |
| -------------- | ------ | -------- | ----------------------------------------------------------------------------------------------------- |
| `kube_config`  | object | Yes      | Kubernetes configuration as a dictionary. Used to connect to the target cluster.                      |
| `storage_size` | string | No       | Size of persistent storage allocated to MongoDB (e.g., `"1Gi"`). Defaults to `"1Gi"` if not provided. |

#### Example Request

```json
{
  "kube_config": { "apiVersion": "v1", "clusters": [...], "contexts": [...], ... },
  "storage_size": "2Gi"
}
```

### Responses

#### Success (200 OK)

```json
{
  "success": true,
  "message": "MemoryGrid config service setup complete"
}
```

#### Client Error (400 Bad Request)

```json
{
  "success": false,
  "error": "Missing kube_config"
}
```

#### Server Error (500 Internal Server Error)

```json
{
  "success": false,
  "error": "Detailed error message"
}
```

---

### Endpoint: `DELETE /framedb-config/remove`

Removes all resources associated with the MemoryGrid Config Service from the target Kubernetes cluster.

#### Behavior

This operation performs the following cleanup tasks:

* Deletes the MongoDB deployment (`mongodb`)
* Deletes the MemoryGrid Config Service deployment (`framedb-config`)
* Deletes the associated services:

  * `framedb-local-config` (MongoDB ClusterIP)
  * `framedb-config-service` (NodePort)
* Deletes the PersistentVolumeClaim (`framedb-mongo-pvc`)
* Deletes the PersistentVolume (`framedb-mongo-pv`)
* Deletes the namespace `framedb-config`

#### Request

* **Method**: `DELETE`
* **URL**: `/framedb-config/remove`
* **Content-Type**: `application/json`

#### Request Body Parameters

| Field         | Type   | Required | Description                                                  |
| ------------- | ------ | -------- | ------------------------------------------------------------ |
| `kube_config` | object | Yes      | Kubernetes configuration as a dictionary for cluster access. |

#### Example Request

```json
{
  "kube_config": { "apiVersion": "v1", "clusters": [...], "contexts": [...], ... }
}
```

### Responses

#### Success (200 OK)

```json
{
  "success": true,
  "message": "MemoryGrid config service removed"
}
```

#### Client Error (400 Bad Request)

```json
{
  "success": false,
  "error": "Missing kube_config"
}
```

#### Server Error (500 Internal Server Error)

```json
{
  "success": false,
  "error": "Detailed error message"
}
```

---

### Endpoint: `POST /framedb-config/status`

Retrieves the current deployment and health status of all MemoryGrid Config Service components in the specified local Kubernetes cluster.

### Behavior

This operation connects to the Kubernetes cluster using the provided `kube_config` and returns structured diagnostic information about the following components:

* **Namespace**

  * Verifies if the namespace `framedb-config` exists

* **Deployments**

  * Reports the available and desired replicas for the following deployments:

    * `mongodb`
    * `framedb-config`

* **Pods**

  * Lists the current pods in the namespace along with their phase and readiness status

* **Services**

  * Lists cluster IPs and node port mappings for:

    * `framedb-local-config` (MongoDB)
    * `framedb-config-service` (MemoryGrid Config API)

* **PersistentVolumeClaim**

  * Reports the bound status and backing volume of `framedb-mongo-pvc`

### Request

* **Method**: `POST`
* **URL**: `/framedb-config/status`
* **Content-Type**: `application/json`

#### Request Body Parameters

| Field         | Type   | Required | Description                                                  |
| ------------- | ------ | -------- | ------------------------------------------------------------ |
| `kube_config` | object | Yes      | Kubernetes configuration as a dictionary for cluster access. |

#### Example Request

```json
{
  "kube_config": { "apiVersion": "v1", "clusters": [...], "contexts": [...], ... }
}
```

### Responses

#### Success (200 OK)

```json
{
  "success": true,
  "data": {
    "namespace": "present",
    "deployments": {
      "mongodb": "1/1 available",
      "framedb-config": "1/1 available"
    },
    "pods": [
      { "name": "mongodb-xxxxx", "status": "Running", "ready": true },
      { "name": "framedb-config-yyyyy", "status": "Running", "ready": true }
    ],
    "services": {
      "framedb-local-config": {
        "cluster_ip": "10.43.0.10",
        "node_ports": []
      },
      "framedb-config-service": {
        "cluster_ip": "10.43.0.11",
        "node_ports": [32566]
      }
    },
    "pvc": {
      "status": "Bound",
      "volume_name": "framedb-mongo-pv"
    }
  }
}
```

#### Client Error (400 Bad Request)

```json
{
  "success": false,
  "error": "Missing kube_config"
}
```

#### Server Error (500 Internal Server Error)

```json
{
  "success": false,
  "error": "Detailed error message"
}
```

---

## Creating and configuring MemoryGrid In-memory instances

These API provides centralized control for provisioning and managing MemoryGrid memory instances across multiple Kubernetes clusters. It delegates instance deployment to remote clusters via API calls, while maintaining registry metadata in a global database.

All registry entries are scoped and identified using a unique `framedb_id`.

---

## Endpoint: `POST /global/framedb/instances`

Provisions a new MemoryGrid memory instance on the specified Kubernetes cluster and records the instance in the global registry.

### Request

* **Method**: `POST`
* **URL**: `/global/framedb/instances`
* **Content-Type**: `application/json`

#### Request Body Parameters

| Field           | Type             | Required | Description                                                               |
| --------------- | ---------------- | -------- | ------------------------------------------------------------------------- |
| `framedb_id`    | string           | Yes      | Unique identifier for the MemoryGrid memory instance.                        |
| `node_id`       | string           | Yes      | Node label or identifier where the instance should be deployed.           |
| `node_selector` | object           | No       | Optional override for node affinity. Defaults to `{ "nodeID": node_id }`. |
| `metadata`      | object           | Yes      | Arbitrary metadata dictionary to associate with the instance.             |
| `redis_config`  | array of strings | Yes      | Redis configuration commands to be applied on startup.                    |
| `cluster_id`    | string           | Yes      | ID of the target cluster used to resolve its config service endpoint.     |

#### Example Request

```json
{
  "framedb_id": "redis-001",
  "node_id": "node-a",
  "metadata": { "project": "analytics" },
  "redis_config": ["maxmemory 64mb", "maxmemory-policy allkeys-lru"],
  "cluster_id": "cluster-01"
}
```

### Responses

#### Success (200 OK)

```json
{
  "success": true,
  "message": "Instance created in global registry",
  "port": 30888
}
```

#### Client Error (400 Bad Request)

```json
{
  "success": false,
  "error": "Missing field: framedb_id"
}
```

#### Server Error (500 Internal Server Error)

```json
{
  "success": false,
  "error": "Detailed error message"
}
```

---

## Endpoint: `DELETE /global/framedb/instances/<framedb_id>`

Removes an existing MemoryGrid memory instance both from the target cluster and the global registry.

### Behavior

This operation performs the following actions:

1. Retrieves the global registry entry for the specified `framedb_id`.
2. Extracts the `cluster_id` and resolves the `framedb_config_url`.
3. Sends a deletion request to the corresponding cluster.
4. Deletes the registry entry if the remote removal is successful.

### Request

* **Method**: `DELETE`
* **URL**: `/global/framedb/instances/<framedb_id>`

#### Path Parameters

| Parameter    | Type   | Description                                      |
| ------------ | ------ | ------------------------------------------------ |
| `framedb_id` | string | The ID of the MemoryGrid memory instance to remove. |

#### Example Request

```http
DELETE /global/framedb/instances/redis-001
```

### Responses

#### Success (200 OK)

```json
{
  "success": true,
  "message": "Removed from global registry"
}
```

#### Client Error (404 Not Found)

```json
{
  "success": false,
  "error": "Instance not found in global registry"
}
```

#### Server Error (500 Internal Server Error)

```json
{
  "success": false,
  "error": "Detailed error message"
}
```

---

### MemoryGrid Port Allocation Scheme

MemoryGrid memory instances are exposed via a Kubernetes **NodePort service** to enable external access. The global service ensures that each deployed instance is assigned a unique and non-conflicting NodePort within a predefined range.

## Port Allocation Logic

* **Port Range**:
  MemoryGrid NodePort services are allocated from the range:

  ```
  30700–30900 (inclusive)
  ```

* **Total Available Ports**:
  The range allows **201 distinct NodePorts**, which means:

  ```
  Maximum concurrent MemoryGrid memory instances per cluster = 201
  ```

* **Conflict Avoidance**:
  Before assigning a NodePort, the system dynamically queries all existing Kubernetes services in the target namespace (`framedb`) and checks for used NodePorts within the valid range.

* **Selection Strategy**:
  The system selects the **lowest available port** in the range by scanning incrementally from `30700` upward. This ensures deterministic and minimal allocation gaps over time.

* **No Internal State**:
  Port availability is determined at runtime by querying the Kubernetes API. The system does **not maintain an in-memory or database-backed port allocation map**, making it stateless and resilient to restarts.

---

## Example

If `30700`, `30701`, and `30702` are already allocated, the next deployed instance will receive:

```json
{
  "port": 30703
}
```

If all ports in the range are exhausted, any new deployment attempt will fail with an appropriate error.

---


## Global MemoryGrid Instance Registry – Query APIs

These APIs provide capabilities to **query MemoryGrid memory instances** stored in the global registry database. Each entry includes instance-specific metadata such as `framedb_id`, `cluster_id`, `node_id`, port, connectivity URLs, deployment status, and user-defined metadata.


### 1. `GET /global/framedb/instances/cluster/<cluster_id>`

Retrieves all MemoryGrid memory instances deployed in the specified cluster.

#### Request

* **Method**: `GET`
* **URL**: `/global/framedb/instances/cluster/<cluster_id>`

#### Path Parameters

| Parameter    | Type   | Description                          |
| ------------ | ------ | ------------------------------------ |
| `cluster_id` | string | ID of the cluster to filter against. |

#### Example

```http
GET /global/framedb/instances/cluster/cluster-01
```

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": [
    {
      "framedb_id": "redis-001",
      "cluster_id": "cluster-01",
      "node_id": "node-a",
      "port": 30701,
      "public_url": "http://example.com:30701",
      "local_url": "redis://redis-001.framedb.svc.cluster.local:6379",
      "status": "Running",
      "metadata": { "env": "prod" }
    },
    ...
  ]
}
```

#### Error Response (400 or 500)

```json
{
  "success": false,
  "error": "Error message"
}
```

---

### 2. `GET /global/framedb/instances/cluster/<cluster_id>/node/<node_id>`

Retrieves all MemoryGrid instances deployed on a specific node within a given cluster.

#### Request

* **Method**: `GET`
* **URL**: `/global/framedb/instances/cluster/<cluster_id>/node/<node_id>`

#### Path Parameters

| Parameter    | Type   | Description                          |
| ------------ | ------ | ------------------------------------ |
| `cluster_id` | string | ID of the cluster to filter against. |
| `node_id`    | string | ID of the node within the cluster.   |

#### Example

```http
GET /global/framedb/instances/cluster/cluster-01/node/node-a
```

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": [
    {
      "framedb_id": "redis-002",
      "cluster_id": "cluster-01",
      "node_id": "node-a",
      "port": 30703,
      "public_url": "http://example.com:30703",
      "local_url": "redis://redis-002.framedb.svc.cluster.local:6379",
      "status": "Running",
      "metadata": { "project": "analytics" }
    }
  ]
}
```

---

### 3. `POST /global/framedb/instances/query`

Performs a flexible MongoDB-style query on the global registry using any combination of fields.

#### Request

* **Method**: `POST`
* **URL**: `/global/framedb/instances/query`
* **Content-Type**: `application/json`

#### Body Parameters

| Field                                                                 | Type   | Required | Description               |
| --------------------------------------------------------------------- | ------ | -------- | ------------------------- |
| Any registry field (e.g., `status`, `cluster_id`, `metadata.project`) | Varies | No       | Mongo-style filter object |

#### Example Request

```json
{
  "status": "Running",
  "cluster_id": "cluster-01",
  "metadata.project": "analytics"
}
```

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": [
    {
      "framedb_id": "redis-003",
      "status": "Running",
      "metadata": {
        "project": "analytics"
      },
      ...
    }
  ]
}
```

---

### 4. `GET /global/framedb/instances/<framedb_id>`

Fetches a specific MemoryGrid memory instance by its unique identifier.

### Request

* **Method**: `GET`
* **URL**: `/global/framedb/instances/<framedb_id>`

#### Path Parameters

| Parameter    | Type   | Description                         |
| ------------ | ------ | ----------------------------------- |
| `framedb_id` | string | Unique identifier for the instance. |

#### Example

```http
GET /global/framedb/instances/redis-001
```

#### Success Response (200 OK)

```json
{
  "success": true,
  "data": {
    "framedb_id": "redis-001",
    "cluster_id": "cluster-01",
    "node_id": "node-a",
    "status": "Running",
    "public_url": "http://example.com:30701",
    "local_url": "redis://redis-001.framedb.svc.cluster.local:6379",
    "metadata": {
      "owner": "platform-team"
    }
  }
}
```

#### Error Response (404 Not Found)

```json
{
  "success": false,
  "error": "Instance not found"
}
```

---

## MemoryGrid Live config update

### Endpoint: `POST /global/framedb/set-config`

Updates the runtime configuration of an existing MemoryGrid memory instance by sending Redis configuration commands to the corresponding cluster. This operation also persists the updated configuration in the global registry.

### Request

* **Method**: `POST`
* **URL**: `/global/framedb/set-config`
* **Content-Type**: `application/json`

#### Request Body Parameters

| Field        | Type             | Required | Description                                                         |
| ------------ | ---------------- | -------- | ------------------------------------------------------------------- |
| `framedb_id` | string           | Yes      | Unique identifier of the MemoryGrid memory instance.                   |
| `config`     | array of strings | Yes      | Redis configuration commands to apply (e.g., `["maxmemory 64mb"]`). |

#### Example Request

```json
{
  "framedb_id": "redis-001",
  "config": [
    "maxmemory 64mb",
    "maxmemory-policy allkeys-lru"
  ]
}
```

---

### Responses

#### Success (200 OK)

```json
{
  "success": true,
  "data": "Configuration updated"
}
```

#### Instance Not Found or Remote Failure (404 Not Found)

```json
{
  "success": false,
  "error": "Instance not found in global registry"
}
```

#### Server Error (500 Internal Server Error)

```json
{
  "success": false,
  "error": "Detailed error message"
}
```

---

