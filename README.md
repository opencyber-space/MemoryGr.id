# MemoryGrid

**MemoryGrid** is a general-purpose, distributed/decentralized object store for storing multi-modal blobs such as video streams, high-resolution images, sensor data, AI inputs/outputs and any general data. It supports unified APIs over **in-memory**, **persistent**, and **streaming** backends, making it ideal for modern data-driven applications, AI pipelines, and real-time analytics.

> MemoryGrid is Kubernetes-native, supports pluggable backends and custom serialization, and is designed for easy integration with ML/AI systems.

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

## 🧭 Roadmap

- [ ] Storage quota management
- [ ] Policy-based data governance and fine-grained controls
- [ ] Security, IAM, RBAC for MemoryGrid
- [ ] Multi-format object serialization registry

---

## 📚 Related Docs

- [MemoryGrid Architecture](./docs/intro.md)
- [Installation](./docs/installation.md)
- [Creating In-memory Instances](./docs/creation-in-memory.md)
- [Routing API](./docs/routing-service.md)
- [Creating Persistent Storage Instances](./docs/creation-storage.md)
- [Object Service API](./docs/creating-objects.md)
- [Writer Client SDK](./docs/framedb-writer-service.md)
- [Python SDK Usage](./docs/client-sdk.md)
- [Video Ingestion](./docs/video-ingestion.md)

---

## 🤝 Contributing

We welcome contributions from the community! If you’d like to help:

1. Fork the repository and create a new branch.
2. Ensure your code follows our contribution guidelines and passes all checks.
3. Open a Pull Request with a clear description of your changes.
4. Discuss your ideas in the Issues section or join our community calls.

Whether it’s fixing bugs, improving documentation, or building new features—your help is appreciated!

---

## 📄 License

[APACHE 2.0](LICENSE)