# MemoryGrid

**MemoryGrid** is a distributed/decentralized, multi-modal data store for storing blobs such as video streams, images, multimedia, high-resolution and sensory data. It offers unified support for **in-memory**, **persistent**, and **streaming** backends—making it ideal for high-performance AI pipelines, ingestion workflows, and real-time analytics.

> Designed for Kubernetes-native environments with first-class support for dynamic deployment, service discovery, and multi-cluster routing.

---

## 🚀 Features

- 🔁 **Unified Read/Write API** across Redis, TiDB, and stream queues
- 📦 **Object abstraction** with typed backends: `in-memory`, `storage`, `stream`
- 🌐 **Multi-cluster routing** for object and stream metadata
- ⚙️ **Kubernetes-native deployments** with dynamic service provisioning
- 💡 **Built-in support for GStreamer video pipelines** and GPU decoding

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
- **Writer Client**: Python SDK and gRPC interface for direct object writes
- **Object Service**: gRPC interface for universal Set/Get operations
- **Video Ingestion**: GStreamer-based decoding pipelines deployed on GPUs

---

## 🎥 Video Ingestion with GStreamer

MemoryGrid provides built-in support for video pipelines via **GStreamer**. Decoder pods run on GPU-enabled Kubernetes nodes and can be managed via a REST API.

### Pipeline Modes

| Mode     | Usage                             |
|----------|-----------------------------------|
| Live     | Real-time RTSP camera ingestion   |
| Stored   | Archived video file playback      |

---

## 🧭 Roadmap

- [ ] Storage quota management
- [ ] Integration with Policies SDK for fine-grained management and governance
- [ ] Security, IAM, RBAC for MemoryGrid

---

## 📚 Related Docs

- [MemoryGrid Architecture](./docs/intro.md)
- [Installation](./docs/installation.md)
- [Creating In-memory Instances](./docs/creation-in-memory.md)
- [Routing API](./docs/routing-service.md)
- [Creating Persistent Storage Instances](./docs/creation-storage.md)
- [Object Service API](./docs/creating-objects.md)
- [MemoryGrid Write Client SDK for Applications](./docs/framedb-writer-service.md)
- [MemoryGrid python SDK](./docs/client-sdk.md)
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
