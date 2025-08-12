# MemoryGr.id

**MemoryGrid** is a general-purpose, distributed/decentralized object store for storing multi-modal blobs such as video streams, high-resolution images, sensor data, AI inputs/outputs and any general data. It supports unified APIs over **in-memory**, **persistent**, and **streaming** backends, making it ideal for modern data-driven applications, AI pipelines, and real-time analytics.

> MemoryGrid is Kubernetes-native, supports pluggable backends and custom serialization, and is designed for easy integration with ML/AI systems.

---

## 📚 Contents

* [Index](# MemoryGr.id

**MemoryGrid** is a general-purpose, distributed/decentralized object store for storing multi-modal blobs such as video streams, high-resolution images, sensor data, AI inputs/outputs and any general data. It supports unified APIs over **in-memory**, **persistent**, and **streaming** backends, making it ideal for modern data-driven applications, AI pipelines, and real-time analytics.

> MemoryGrid is Kubernetes-native, supports pluggable backends and custom serialization, and is designed for easy integration with ML/AI systems.

---

## 📚 Contents

* [Index](https://memorygrid-internal.pages.dev/)
* [Introduction](https://memorygrid-internal.pages.dev/intro)
* [Installation](https://memorygrid-internal.pages.dev/installation)
* [Creation - In Memory](https://memorygrid-internal.pages.dev/creation-in-memory)
* [Creation - Storage](https://memorygrid-internal.pages.dev/creation-storage)
* [Creating Objects](https://memorygrid-internal.pages.dev/creating-objects)
* [Client SDK](https://memorygrid-internal.pages.dev/client-sdk)
* [FrameDB Writer Service](https://memorygrid-internal.pages.dev/framedb-writer-service)
* [Routing Service](https://memorygrid-internal.pages.dev/routing-service)
* [Video Ingestion](https://memorygrid-internal.pages.dev/video-ingestion)


---

## 🚀 Features

- 🔁 **Unified Read/Write API** across Redis, TiDB, and stream queues
- 📦 **Object abstraction** with typed backends: `in-memory`, `storage`, `stream`
- 🧠 **Custom Serialization** support (e.g., `pickle`, `JSON`, custom codecs)
- 💾 **Backup & Restore** support for external object stores (S3, GCS, MinIO, Ceph)
- 🌐 **Multi-cluster routing** for object and stream metadata
- ⚙️ **Kubernetes-native deployments** with dynamic service provisioning
- 💡 **AI Integration Ready**: store Python objects (e.g., ML model snapshots, configs)
- 📽️ **Built-in GStreamer pipelines** with GPU acceleration for video ingestion

---

## 🧠 Core Concepts

### 📂 MemoryGrid Instances

| Type           | Backend | Use Case                          |
|----------------|---------|-----------------------------------|
| In-memory      | Redis   | Fast access, low latency data     |
| Persistent     | TiDB    | Durable, queryable blob storage   |
| Streaming      | Redis   | Producer-consumer style pipelines |

### 🔧 MemoryGrid Services

- **Config Service**: Creates and manages DB instances across clusters
- **Routing Service**: Tracks object/stream metadata and their locations
- **Writer Client SDK**: Python interface for storing, retrieving, and streaming objects
- **Object Service**: gRPC interface for Set/Get/Stream operations
- **Video Ingestion**: GStreamer-based GPU pipelines for real-time decoding

---

## 🎥 Video Ingestion with GStreamer

MemoryGrid includes GPU-accelerated pipelines for ingesting video streams in both live and stored modes. Pipelines are deployed as containers and exposed via REST endpoints.

| Mode     | Usage                             |
|----------|-----------------------------------|
| Live     | Real-time RTSP camera ingestion   |
| Stored   | Archived video file playback      |

---

## 📢 Communications

1. 📧 Email: [community@opencyberspace.org](mailto:community@opencyberspace.org)  
2. 💬 Discord: [OpenCyberspace](https://discord.gg/W24vZFNB)  
3. 🐦 X (Twitter): [@opencyberspace](https://x.com/opencyberspace)

---

## 🤝 Join Us!

This project is **community-driven**. Theory, Protocol, implementations - All contributions are welcome.

### Get Involved

- 💬 [Join our Discord](https://discord.gg/W24vZFNB)  
- 📧 Email us: [community@opencyberspace.org](mailto:community@opencyberspace.org))
* [Introduction](intro.md)
* [Installation](installation.md)
* [Creation - In Memory](creation-in-memory.md)
* [Creation - Storage](creation-storage.md)
* [Creating Objects](creating-objects.md)
* [Client SDK](client-sdk.md)
* [FrameDB Writer Service](framedb-writer-service.md)
* [Routing Service](routing-service.md)
* [Video Ingestion](video-ingestion.md)


---

## 🚀 Features

- 🔁 **Unified Read/Write API** across Redis, TiDB, and stream queues
- 📦 **Object abstraction** with typed backends: `in-memory`, `storage`, `stream`
- 🧠 **Custom Serialization** support (e.g., `pickle`, `JSON`, custom codecs)
- 💾 **Backup & Restore** support for external object stores (S3, GCS, MinIO, Ceph)
- 🌐 **Multi-cluster routing** for object and stream metadata
- ⚙️ **Kubernetes-native deployments** with dynamic service provisioning
- 💡 **AI Integration Ready**: store Python objects (e.g., ML model snapshots, configs)
- 📽️ **Built-in GStreamer pipelines** with GPU acceleration for video ingestion

---

## 🧠 Core Concepts

### 📂 MemoryGrid Instances

| Type           | Backend | Use Case                          |
|----------------|---------|-----------------------------------|
| In-memory      | Redis   | Fast access, low latency data     |
| Persistent     | TiDB    | Durable, queryable blob storage   |
| Streaming      | Redis   | Producer-consumer style pipelines |

### 🔧 MemoryGrid Services

- **Config Service**: Creates and manages DB instances across clusters
- **Routing Service**: Tracks object/stream metadata and their locations
- **Writer Client SDK**: Python interface for storing, retrieving, and streaming objects
- **Object Service**: gRPC interface for Set/Get/Stream operations
- **Video Ingestion**: GStreamer-based GPU pipelines for real-time decoding

---

## 🎥 Video Ingestion with GStreamer

MemoryGrid includes GPU-accelerated pipelines for ingesting video streams in both live and stored modes. Pipelines are deployed as containers and exposed via REST endpoints.

| Mode     | Usage                             |
|----------|-----------------------------------|
| Live     | Real-time RTSP camera ingestion   |
| Stored   | Archived video file playback      |

---

## 📢 Communications

1. 📧 Email: [community@opencyberspace.org](mailto:community@opencyberspace.org)  
2. 💬 Discord: [OpenCyberspace](https://discord.gg/W24vZFNB)  
3. 🐦 X (Twitter): [@opencyberspace](https://x.com/opencyberspace)

---

## 🤝 Join Us!

This project is **community-driven**. Theory, Protocol, implementations - All contributions are welcome.

### Get Involved

- 💬 [Join our Discord](https://discord.gg/W24vZFNB)  
- 📧 Email us: [community@opencyberspace.org](mailto:community@opencyberspace.org)
