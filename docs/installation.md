# Installing FrameDB Management Services

FrameDB includes two key management services:

1. **FrameDB Config Service** – Responsible for deploying and configuring FrameDB local cluster services, including both in-memory and persistent storage instances.

2. **Routing Service** – Maintains metadata about objects (if sharing is enabled) and tracks all streaming queues across the FrameDB network.

## Installing the Database

To install the database, run the following steps:

```sh
# From the project root
cd kubernetes/installer

# Usage: ./install_db.sh <replica-count> [storage-size]
./install_db.sh 3 5Gi
```

The above command provisions the FrameDB database with 3 replicas, each with 5Gi of storage.

## Installing the Services

To deploy the management services, run the installer script:

```sh
# From the project root
cd kubernetes/installer

./install.sh
```

This will deploy both the FrameDB Config Service and the Routing Service.

---

Here is the final section with a table listing the deployed services and their respective NodePorts:

---

## Services

The following services are deployed as part of the FrameDB management system:

| Service Name          | Namespace          | Description                                                        | Port  | NodePort |
| --------------------- | ------------------ | ------------------------------------------------------------------ | ----- | -------- |
| `framedb-config-svc`  | `framedb-services` | FrameDB Config Service for managing FrameDB clusters and instances | 5000  | 30610    |
| `routing-service-svc` | `framedb-services` | Routing Service to track object locations and streaming queues     | 5000  | 30611    |


> **Note:** Only the management services (`framedb-config-svc`, `routing-service-svc`) are exposed via NodePort for external access. MongoDB replicas are internally accessible within the cluster.

---

## Local cluster services

Following services are deployed on the local clusters through config service (refer config service documentation to understand how to spin up these services).


| Component                        | NodePort Range / Port | Internal Service URL                                          |
| -------------------------------- | --------------------- | ------------------------------------------------------------- |
| **FrameDB Config Service**       | `32566`               | `http://framedb-config.framedb-config.svc.cluster.local:5000` |
| **Objects API**                  | `32567`               | `http://objects.framedb-config.svc.cluster.local:50051`       |
| **Decoder Scheduler**                  | `32568`               | `http://decoder-scheduler.framedb-config.svc.cluster.local:5000`       |
| **FrameDB In-Memory Instances**  | `30700–30900`         | Dynamic service URLs (one per in-memory instance, 200 instances per cluster)             |
| **FrameDB Persistent Instances** | `30900–30999`         | Dynamic service URLs (one per persistent instance, 99 instances per cluster)            |

> **Note:** All FrameDB instances are assigned dynamic service names based on their deployment ID and exposed via unique NodePorts within the specified ranges.

---
