Absolutely! Below is the **professionally rewritten, technically accurate, and fully adapted documentation for MemoryGrid Persistent (TiDB-backed) instances**, based on the structure of your original In-Memory version.

---

# Creating MemoryGrid Persistent Instances (TiDB-backed)

Persistent MemoryGrid instances use TiDB as the underlying database engine and are managed via the MemoryGrid Config Service. These instances are distributed across Kubernetes clusters, with centralized provisioning managed by a global controller and cluster-specific deployments handled by local config services.

---

## Creating MemoryGrid Local Config Service for Persistent Instances

The MemoryGrid local config service must be set up on each cluster where persistent MemoryGrid instances will be deployed. This service handles deployment, configuration, and health checks for the TiDB-based databases in response to commands proxied by the global config service.

---

## API: `POST /framedb-config/setup`

Sets up the MemoryGrid Config Service on the target Kubernetes cluster, including the TiDB-compatible infrastructure.

### Behavior

* Creates namespace `framedb-config` (if not present)
* Deploys MongoDB + MemoryGrid Config Service with:

  * Persistent storage mounted at `/data/db`
  * Internal ClusterIP service: `framedb-local-config`
  * External NodePort: `framedb-config-service` (port `32566`)

### Request

| Field          | Type   | Required | Description                              |
| -------------- | ------ | -------- | ---------------------------------------- |
| `kube_config`  | object | Yes      | Kubernetes config for the target cluster |
| `storage_size` | string | No       | MongoDB volume size (default `"1Gi"`)    |

```json
{
  "kube_config": { ... },
  "storage_size": "2Gi"
}
```

### Response

* `200 OK`: Setup successful
* `400 Bad Request`: Missing or invalid input
* `500 Internal Server Error`: Deployment failed

---

## API: `DELETE /framedb-config/remove`

Removes all components of the MemoryGrid Config Service.

### Behavior

* Deletes:

  * `mongodb`, `framedb-config` deployments
  * PVC + PV
  * Services
  * Namespace

### Request

```json
{
  "kube_config": { ... }
}
```

### Response

* `200 OK`: Cleanup successful
* `400`: Missing `kube_config`
* `500`: Internal error

---

## API: `POST /framedb-config/status`

Reports the health and presence of all MemoryGrid components in the cluster.

### Response

Returns namespace, pod, service, PVC, and deployment status for:

* `mongodb`
* `framedb-config`
* `framedb-local-config`
* `framedb-config-service`

---

## Global Management of Persistent Instances

The following APIs are used to **create, delete, query, and inspect persistent TiDB-backed MemoryGrid instances**. Global metadata is stored centrally, and cluster interaction is delegated to local config services.

---

## API: `POST /global/framedb/persistent-instances`

Creates a new persistent instance in a target cluster and stores metadata globally.

### Request Body

| Field          | Type   | Required | Description                             |
| -------------- | ------ | -------- | --------------------------------------- |
| `framedb_id`   | string | Yes      | Unique ID for the instance              |
| `node_id`      | string | Yes      | Target node label                       |
| `metadata`     | object | Yes      | Optional metadata for tracking          |
| `storage_size` | string | Yes      | Volume size for TiDB (e.g., `"2Gi"`)    |
| `cluster_id`   | string | Yes      | Cluster in which to create the instance |

```json
{
  "framedb_id": "tidb-001",
  "node_id": "node-a",
  "metadata": { "team": "analytics" },
  "storage_size": "2Gi",
  "cluster_id": "cluster-01"
}
```

### Response

```json
{
  "success": true,
  "message": "Instance created in global registry",
  "port": 30903
}
```

---

## API: `DELETE /global/framedb/persistent-instances/<framedb_id>`

Deletes a TiDB persistent instance from both the cluster and global registry.

```http
DELETE /global/framedb/persistent-instances/tidb-001
```

### Success

```json
{
  "success": true,
  "message": "Removed from global registry"
}
```

---

## Port Allocation for Persistent Instances

### NodePort Range: `30900–30999`

* Total available ports: **100**
* Strategy: Lowest available port selected by checking Kubernetes services
* Stateless: No in-memory tracking of usage
* Failure: Returns error if no ports available

---

## API: `GET /global/framedb/persistent-instances/cluster/<cluster_id>`

Returns all persistent instances deployed in the given cluster.

```http
GET /global/framedb/persistent-instances/cluster/cluster-01
```

### Sample Response

```json
{
  "success": true,
  "data": [
    {
      "framedb_id": "tidb-001",
      "node_id": "node-a",
      "cluster_id": "cluster-01",
      "port": 30903,
      "public_url": "http://cluster-01:30903",
      "local_url": "mysql://tidb-001.framedb-storage.svc.cluster.local:4000",
      "metadata": { "team": "analytics" },
      "status": "Running"
    }
  ]
}
```

---

## API: `GET /global/framedb/persistent-instances/cluster/<cluster_id>/node/<node_id>`

Returns all persistent instances on a specific node of a cluster.

---

## API: `POST /global/framedb/persistent-instances/query`

Allows flexible MongoDB-style queries:

```json
{
  "cluster_id": "cluster-01",
  "metadata.team": "analytics"
}
```

---

## API: `GET /global/framedb/persistent-instances/<framedb_id>`

Returns full instance metadata by ID.

---