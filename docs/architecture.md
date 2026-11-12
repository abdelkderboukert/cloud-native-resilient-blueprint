# System Architecture Deep Dive: Enterprise Event-Driven Micro-Platform (EEMP)

This specification defines the formal engineering architecture for deploying the Enterprise Event-Driven Micro-Platform across high-availability Kubernetes clusters.

---

## 1. Global Infrastructure & Storage Topology (Longhorn & Cross-Node Replication)

### 1.1 Storage Orchestration & CSI Driver
Longhorn serves as the cloud-native Container Storage Interface (CSI) plugin, pooling block storage distributed across Kubernetes worker nodes into resilient, fault-tolerant block volumes.

```mermaid
flowchart TD
    subgraph K8sCluster["Kubernetes Cluster Failure Domain"]
        subgraph WorkerNode1["Worker Node 1 (Rack A / AZ 1)"]
            Pod1["CNPG Instance 1 / Kafka Pod"]
            Engine1["Longhorn Volume Engine"]
            Replica1["Longhorn Replica 1 (ext4)"]
        end

        subgraph WorkerNode2["Worker Node 2 (Rack B / AZ 2)"]
            Pod2["CNPG Instance 2"]
            Replica2["Longhorn Replica 2 (ext4)"]
        end

        subgraph WorkerNode3["Worker Node 3 (Rack C / AZ 3)"]
            Pod3["CNPG Instance 3"]
            Replica3["Longhorn Replica 3 (Spare/Standby)"]
        end
    end

    Engine1 -. Synchronous Block IO .-> Replica1
    Engine1 -. Cross-Node Network IO .-> Replica2
```

### 1.2 Storage Isolation & Node Anti-Affinity
* **Replication Factor ($n=2$ / $n=3$):** Stateful volumes for CloudNativePG (20Gi), Kafka (15Gi), and RustFS (50Gi) are provisioned via `enterprise-longhorn-sc`.
* **Failure Domain Isolation:** Replicas are scheduled across discrete physical or virtual nodes (`numberOfReplicas: "2"` with `staleReplicaTimeout: "2880"`). Even if an entire node experiences a sudden power loss or hardware failure, the remaining replica maintains continuous data availability without IO corruption.
* **Volume Expansion & Reclaim:** Dynamic volume expansion (`allowVolumeExpansion: true`) enables scaling persistent storage without cluster downtime. Volumes are retained on release (`reclaimPolicy: Retain`) to prevent accidental data loss.

---

## 2. Component Specifications & Declarative Architecture

```mermaid
graph TB
    Client["Client / External Edge"]
    Kong["Kong API Gateway<br/>(Edge Routing: Port 80/443)"]
    Django["Django REST Framework API<br/>(App Tier: Port 8000)"]
    CNPG["CloudNativePG PostgreSQL 16<br/>(3 HA Instances: Port 5432)"]
    Kafka["Apache Kafka Broker<br/>(KRaft Mode: Port 9092)"]
    RustFS["RustFS S3 Storage<br/>(Object Tier: Port 9000)"]

    Client -->|HTTP/HTTPS| Kong
    Kong -->|CoreDNS TCP 8000| Django
    Django -->|psycopg3 TCP 5432| CNPG
    Django -->|Event Stream TCP 9092| Kafka
    CNPG -.->|Continuous WAL Archiving Port 9000| RustFS

    classDef edge fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef app fill:#0f766e,stroke:#2dd4bf,stroke-width:2px,color:#fff;
    classDef data fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff;
    classDef msg fill:#701a75,stroke:#f472b6,stroke-width:2px,color:#fff;

    class Client,Kong edge;
    class Django app;
    class CNPG,RustFS data;
    class Kafka msg;
```

### 2.1 Object Storage Layer: RustFS
* **Purpose:** S3-compatible, memory-safe high-performance storage engine.
* **Responsibilities:**
  - WAL (Write-Ahead Log) archiving from the CloudNativePG PostgreSQL cluster.
  - Scheduled base backups (`postgres-daily-backup`).
  - Storage repository for static assets and Django media uploads.
* **Persistence:** Provisioned with a 50Gi Longhorn volume (`rustfs-data`) mounted at `/data`.
* **Service Resolution:** Exposed internally as `rustfs-service.data-tier.svc.cluster.local:9000` with headless binding `rustfs-headless`.

### 2.2 Stateful Database Layer: CloudNativePG (CNPG)
* **Purpose:** Production-grade PostgreSQL 16 HA cluster with unsupervised automated failover.
* **Topology:** 3 pods (`postgres-cluster-1`, `postgres-cluster-2`, `postgres-cluster-3`).
* **Connection Routing:**
  - Primary Read-Write: `postgres-cluster-rw.data-tier.svc.cluster.local:5432`
  - Read-Only Replicas: `postgres-cluster-ro.data-tier.svc.cluster.local:5432`
* **Backup & Continuous Archiving:** Barman object store integration streaming PostgreSQL WAL files continuously to `s3://postgres-backups/` on RustFS.

### 2.3 Event Streaming Layer: Apache Kafka (KRaft Mode)
* **Architecture:** Kafka 3.6 / Confluent 7.6 running in native KRaft mode (Kafka Raft Metadata mode without ZooKeeper).
* **Quorum & Metadata:**
  - Controller Quorum: `1@kafka-broker-0.kafka-headless.messaging-tier.svc.cluster.local:9093`
  - Client Listener: `0.0.0.0:9092` (`PLAINTEXT`)
  - Controller Listener: `0.0.0.0:9093` (`CONTROLLER`)
* **Topics:**
  - `user.lifecycle.events` (3 partitions, replication factor 1/2)
  - `article.lifecycle.events` (3 partitions, replication factor 1/2)

### 2.4 Application Layer: Django REST Framework
* **Stateless Microservice:** Scaled horizontally across 2+ replicas with Pod Disruption Budget (`minAvailable: 1`) and Horizontal Pod Autoscaler.
* **Database Access:** High-performance asynchronous and pooled database connections using PostgreSQL 16 and `psycopg3`.
* **Telemetry & Event Publishing:**
  - Thread-safe `EnterpriseKafkaProducer` emitting structured CloudEvents envelopes.
  - Generates and echoes `X-Request-ID` correlation identifiers across all API boundaries.
  - Exposes Kubernetes liveness (`/healthz/`), readiness (`/readyz/`), and Prometheus telemetry (`/metrics/`).

### 2.5 Edge Routing Layer: Kong API Gateway
* **Ingress Management:** Ingress controller directing inbound external traffic matching `api.enterprise.local` to `django-service` on port 80.
* **Gateway Plugins:**
  - **Rate Limiting:** Prevents DDoS and resource exhaustion (120 req/min).
  - **Correlation ID:** Generates/propagates `X-Request-ID` across downstream services.
  - **Prometheus:** Real-time edge latency, bandwidth, and HTTP status code metrics.

---

## 3. Network & Data Flow Architecture Matrix

| Source Layer | Destination Layer | Protocol / Port | OSI Layer | Functional Description | Security Policy Enforcement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Client / Edge** | **Kong Ingress** | HTTP/HTTPS (Port 80/443) | Layer 7 | External traffic entry point, TLS termination, rate-limiting, and path routing. | Edge firewall & Ingress TLS rules |
| **Kong Ingress** | **Django Service** | TCP (Port 80 → 8000) | Layer 4/7 | Internal cluster upstream proxying via Kubernetes CoreDNS resolution (`ClusterIP`). | `app-tier-network-policy` allows port 8000 from ingress namespaces |
| **Django Service** | **CNPG Postgres** | TCP (Port 5432) | Layer 4 | ORM-backed relational transactions, connection pooling, and ACID persistence over Longhorn volumes. | `postgres-network-policy` restricts port 5432 strictly to `app.kubernetes.io/name: django-api` |
| **Django Service** | **Kafka Broker** | TCP (Port 9092) | Layer 4 | Asynchronous publishing of user/article event streams. | `kafka-network-policy` restricts port 9092 strictly to `app.kubernetes.io/name: django-api` |
| **CNPG Operator** | **RustFS S3** | HTTP REST (Port 9000) | Layer 7 | Automated Write-Ahead Log (WAL) archiving and scheduled base backups. | `rustfs-network-policy` restricts port 9000 to CNPG cluster pods |
