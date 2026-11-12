# 🚀 Enterprise Event-Driven Micro-Platform (EEMP)

### Resilient Cloud-Native Architecture Blueprint, Helm 3, ArgoCD GitOps & DevSecOps Suite

[![Platform CI](https://github.com/enterprise/cloud-native-resilient-blueprint/actions/workflows/ci.yaml/badge.svg)](.github/workflows/ci.yaml)
[![Helm](https://img.shields.io/badge/Helm-3.x-0F1689.svg?logo=helm&logoColor=white)](https://helm.sh)
[![ArgoCD](https://img.shields.io/badge/GitOps-ArgoCD-orange.svg?logo=argo&logoColor=white)](https://argo-cd.readthedocs.io/)
[![Trivy](https://img.shields.io/badge/Security-Trivy%20Scanned-blue.svg?logo=aquasecurity&logoColor=white)](https://trivy.dev/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-v1.28%2B-326CE5.svg?logo=kubernetes&logoColor=white)](https://kubernetes.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16.2-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Kafka](https://img.shields.io/badge/Apache%20Kafka-KRaft%20Mode-231F20.svg?logo=apachekafka&logoColor=white)](https://kafka.apache.org/)
[![Django](https://img.shields.io/badge/Django%20REST-5.0-092E20.svg?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Longhorn](https://img.shields.io/badge/Storage-Longhorn%20CSI-ff6600.svg)](https://longhorn.io/)

---

## 📌 Executive Summary (The 30-Second Elevator Pitch)

> **What is this project?**
> The **Enterprise Event-Driven Micro-Platform (EEMP)** is a complete, battle-tested blueprint for running mission-critical stateful microservices on Kubernetes.
>
> It provides an automated, zero-trust control plane integrating:
>
> 1. **Distributed Block Storage** with cross-node replication (**Longhorn CSI**).
> 2. **High-Availability PostgreSQL 16** with automated failover and continuous S3 WAL archiving (**CloudNativePG** + **RustFS S3**).
> 3. **Next-Gen Distributed Streaming** in native ZooKeeper-less mode (**Apache Kafka KRaft**).
> 4. **Resilient Application Microservice** emitting asynchronous CloudEvents envelopes (**Django REST Framework** + **Psycopg 3**).
> 5. **Edge Routing & Policy Enforcement** with rate-limiting and correlation ID tracing (**Kong API Gateway**).
> 6. **Declarative GitOps Continuous Delivery** (**ArgoCD** + **Helm 3**).
> 7. **Shift-Left DevSecOps** with automated secret detection (**Gitleaks**), CVE auditing (**pip-audit**), and Kubernetes misconfiguration scanning (**Trivy**).

---

## 🗺️ High-Level System Architecture

The platform separates compute, storage, messaging, and routing into isolated failure domains governed by Kubernetes NetworkPolicies:

```mermaid
flowchart TD
    subgraph EdgeTier["🌐 Edge Routing Tier (ingress-tier / app-tier)"]
        User(["Client / External Edge"])
        Kong["Kong API Gateway Ingress<br/>(Port 80 / 443)<br/>Plugins: RateLimit, Tracing, Prometheus"]
        User -->|HTTP / HTTPS| Kong
    end

    subgraph AppTier["⚡ Application Microservice Tier (app-tier)"]
        Django1["Django API Pod 1<br/>(Port 8000)"]
        Django2["Django API Pod 2<br/>(Port 8000)"]
        HPA["Horizontal Pod Autoscaler<br/>(Min: 2, Max: 10)"]
        Kong -->|Internal CoreDNS TCP:80| Django1
        Kong -->|Internal CoreDNS TCP:80| Django2
        HPA -. Autoscale .-> Django1
        HPA -. Autoscale .-> Django2
    end

    subgraph MessagingTier["📡 Streaming Messaging Tier (messaging-tier)"]
        Kafka["Apache Kafka Broker<br/>(KRaft Mode: Port 9092)<br/>Topics: user.events, article.events"]
        Django1 -->|Asynchronous CloudEvents TCP:9092| Kafka
        Django2 -->|Asynchronous CloudEvents TCP:9092| Kafka
    end

    subgraph DataTier["💾 Stateful Database & Object Tier (data-tier)"]
        CNPG_RW["CNPG Primary RW (Port 5432)"]
        CNPG_RO1["CNPG Replica RO 1"]
        CNPG_RO2["CNPG Replica RO 2"]
        RustFS["RustFS S3 Object Storage<br/>(Port 9000)<br/>Destination: s3://postgres-backups/"]

        Django1 -->|ACID Transactions via psycopg3| CNPG_RW
        Django2 -->|ACID Transactions via psycopg3| CNPG_RW

        CNPG_RW -. Streaming Replication .-> CNPG_RO1
        CNPG_RW -. Streaming Replication .-> CNPG_RO2
        CNPG_RW -->|Continuous Barman WAL Archiving| RustFS
    end

    subgraph StorageTier["🧱 Resilient Block Storage Layer (CSI Failure Domains)"]
        Longhorn["Longhorn CSI (enterprise-longhorn-sc)<br/>Cross-Node Replication n=2, 48h stale timeout, ext4, Retain"]
        CNPG_RW --- Longhorn
        Kafka --- Longhorn
        RustFS --- Longhorn
    end

    classDef edge fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff;
    classDef app fill:#042f2e,stroke:#2dd4bf,stroke-width:2px,color:#fff;
    classDef data fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff;
    classDef msg fill:#701a75,stroke:#f472b6,stroke-width:2px,color:#fff;
    classDef storage fill:#431407,stroke:#fb923c,stroke-width:2px,color:#fff;

    class User,Kong edge;
    class Django1,Django2,HPA app;
    class CNPG_RW,CNPG_RO1,CNPG_RO2,RustFS data;
    class Kafka msg;
    class Longhorn storage;
```

---

## 🔄 End-to-End Request & Event Lifecycle

This sequence diagram illustrates what happens when a client sends an API request (e.g., publishing a new enterprise article):

```mermaid
sequenceDiagram
    autonumber
    actor Client as External Client
    participant Kong as Kong API Gateway
    participant Django as Django REST API
    participant PG as PostgreSQL 16 (CNPG)
    participant Kafka as Kafka Broker (KRaft)
    participant S3 as RustFS S3 Storage

    Client->>Kong: POST /api/v1/articles/ (Payload)
    Note over Kong: 1. Enforces Rate-Limit (120 req/min)<br/>2. Generates & Injects X-Request-ID
    Kong->>Django: Proxy request with Correlation-ID
    Django->>PG: BEGIN Transaction (INSERT article)
    PG-->>Django: COMMIT (UUID generated)
    Django->>Kafka: Async Publish 'article.created' (CloudEvents Envelope)
    Note over Kafka: Partitions to 'article.lifecycle.events'<br/>with key=article.id
    Kafka-->>Django: ACK (acks=1)
    Django-->>Kong: 201 Created (JSON Response + X-Request-ID)
    Kong-->>Client: 201 Created (Echoes X-Request-ID downstream)

    par Background Backup & Replication
        PG->>S3: Stream Write-Ahead Log (WAL) via Barman
        S3-->>PG: WAL Segment Archived
    end
```

---

## 🛡️ Failure Domains & Physical Storage Replication (Longhorn)

How does the platform survive sudden hardware node loss without data corruption?

```mermaid
flowchart LR
    subgraph Node1["Worker Node 1 (Rack A)"]
        AppPod["CNPG Primary Pod"]
        LH_Engine["Longhorn Volume Engine"]
        ReplicaA["Replica 1 (Active ext4)"]
    end

    subgraph Node2["Worker Node 2 (Rack B)"]
        ReplicaB["Replica 2 (Synchronized ext4)"]
    end

    subgraph Node3["Worker Node 3 (Rack C)"]
        ReplicaStandby["Replica 3 (Standby Target)"]
    end

    AppPod -->|Block I/O| LH_Engine
    LH_Engine -->|Local NVMe/SSD| ReplicaA
    LH_Engine -->|Sync TCP Network I/O| ReplicaB

    Node1 -.->|"💥 Node 1 Crashes"| Failover["Automated Failover"]
    Failover -->|"CNPG promotes replica on Node 2<br/>Longhorn rebuilds Replica on Node 3"| Node2
```

- **Longhorn CSI StorageClass (`enterprise-longhorn-sc`)**:
  - `numberOfReplicas: "2"`: Guarantees synchronous multi-node persistence.
  - `volumeBindingMode: Immediate`: Provisions storage instantly to match scheduling requirements.
  - `reclaimPolicy: Retain`: Prevents catastrophic data deletion if pods or PVCs are unbound.
  - `staleReplicaTimeout: "2880"` (48 Hours): Avoids immediate disk thrashing during temporary node restarts.

---

## 🔒 Zero-Trust Network & Data Flow Matrix

Every tier is locked down using Kubernetes `NetworkPolicy` objects that deny all unauthorized cross-namespace lateral movement:

| Source Layer          | Destination Layer | Protocol / Port         | OSI Layer | Functional Role                                | Security Policy Rule                                                  |
| :-------------------- | :---------------- | :---------------------- | :-------- | :--------------------------------------------- | :-------------------------------------------------------------------- |
| **Client / Internet** | **Kong Ingress**  | `HTTP/HTTPS (80/443)`   | Layer 7   | Inbound traffic, TLS termination, DDoS defense | Edge Firewall & TLS Ingress                                           |
| **Kong Ingress**      | **Django API**    | `TCP (Port 80 → 8000)`  | Layer 4/7 | CoreDNS upstream proxying                      | `app-tier-network-policy` restricts ingress strictly to Kong          |
| **Django API**        | **CNPG Postgres** | `TCP (Port 5432)`       | Layer 4   | Relational ACID queries via `psycopg3`         | `postgres-network-policy` allows port 5432 **only** from `django-api` |
| **Django API**        | **Kafka Broker**  | `TCP (Port 9092)`       | Layer 4   | Non-blocking CloudEvents streaming             | `kafka-network-policy` allows port 9092 **only** from `django-api`    |
| **CNPG Primary**      | **RustFS S3**     | `HTTP REST (Port 9000)` | Layer 7   | Continuous WAL archiving & base backups        | `rustfs-network-policy` allows port 9000 **only** from `data-tier`    |

---

## ⚙️ Declarative GitOps Architecture (ArgoCD & Helm)

The platform follows a strict **GitOps** operating model. Nothing is applied manually with `kubectl` in production; the Git repository is the single source of truth.

```mermaid
flowchart LR
    Git["Git Repository<br/>(deploy/helm/enterprise-platform)"] -->|Webhook / Polling| ArgoCD["ArgoCD Controller<br/>(namespace: argocd)"]

    subgraph ArgoCD_Engine["ArgoCD Reconciler"]
        AppProj["AppProject: enterprise-platform<br/>Whitelists namespaces: data, messaging, app, ingress"]
        AppProd["Application: enterprise-platform-prod<br/>values.yaml + values-prod.yaml"]
    end

    ArgoCD --> ArgoCD_Engine
    ArgoCD_Engine -->|Automated Sync & Prune| K8sCluster["Kubernetes Cluster"]

    K8sCluster -. "Drift Detected" .- ArgoCD_Engine
```

### GitOps Features Configured:

- **`selfHeal: true`**: If an engineer manually alters a pod or service with `kubectl`, ArgoCD immediately detects the configuration drift and reverts the cluster back to the Git state.
- **`prune: true`**: Removing a manifest or template from Git automatically cleans up the stale Kubernetes object.
- **`ApplyOutOfSyncOnly: true`**: Highly efficient reconciliation that only updates resources whose declarative spec has changed.

---

## 🛡️ DevSecOps CI/CD Pipeline & Shift-Left Security

Every code change must pass four automated security and quality gates before being deployed:

```mermaid
flowchart TD
    Commit["Git Push / Pull Request"] --> Gate1["Gate 1: Secrets & Pattern Audit"]
    Commit --> Gate2["Gate 2: Dependency Vulnerability Audit"]
    Commit --> Gate3["Gate 3: Helm Trivy Misconfiguration Scan"]

    subgraph Gate1_Details["Gate 1 Checks"]
        Gitleaks["Gitleaks Secret Scan"]
        TrivyFS["Trivy Filesystem Secret Scan"]
        Yamllint["Yamllint Syntax Check"]
        Flake8["Flake8 Python Antipattern Check"]
    end

    subgraph Gate2_Details["Gate 2 Checks"]
        PipAudit["pip-audit (CVE Database Scan)"]
        TrivyVuln["Trivy Vulnerability Scan"]
    end

    subgraph Gate3_Details["Gate 3 Checks"]
        HelmLint["helm lint & helm template"]
        TrivyConfig["Trivy config (Kubernetes Security Posture)"]
    end

    Gate1 --> Gate1_Details --> Pass1["Clean Secrets & Syntax"]
    Gate2 --> Gate2_Details --> Pass2["Zero High/Critical CVEs"]
    Gate3 --> Gate3_Details --> Pass3["Secure Helm Manifests"]

    Pass1 & Pass2 & Pass3 --> Gate4["Gate 4: Build, Test, Scan & Push"]

    subgraph Gate4_Details["Gate 4 Pipeline"]
        DjangoTest["1. Django Unit Tests (manage.py test)"]
        DockerBuild["2. Multi-Stage Docker Build (Non-root UID 10001)"]
        TrivyImage["3. Trivy Container Image Scan (Vuln & Secrets)"]
        PushGHCR["4. Authenticated Push to GHCR (ghcr.io)"]
    end

    Gate4 --> Gate4_Details --> Release["🚀 Ready for ArgoCD Sync"]
```

---

## 💡 Top Architectural Trade-offs (Interview Cheatsheet)

When asked why this platform was designed this way, here are the key technical decisions:

```
┌─────────────────────────────────┬──────────────────────────────────┬────────────────────────────────────────────────────────┐
│ Engineering Decision            │ Alternative Considered           │ Why We Made This Choice                                │
├─────────────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Apache Kafka in KRaft Mode      │ Kafka with Apache ZooKeeper      │ Eliminates ZooKeeper operational overhead; metadata is │
│                                 │                                  │ managed internally via Raft, dramatically simplifying  │
│                                 │                                  │ controller failovers and reducing memory footprint.    │
├─────────────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ CloudNativePG (CNPG)            │ Standard PostgreSQL StatefulSet  │ Built specifically for Kubernetes; handles automated   │
│                                 │ or external managed DB           │ failover, standby election, online backup replication, │
│                                 │                                  │ and rolling minor upgrades with zero manual downtime.  │
├─────────────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Longhorn CSI Distributed Storage│ HostPath / NFS / Cloud Volumes   │ Vendor-agnostic, open-source block storage that runs   │
│                                 │                                  │ on any bare-metal or cloud k8s cluster with cross-node │
│                                 │                                  │ synchronous mirroring (n=2) and snapshots.             │
├─────────────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ RustFS / S3 WAL Offloading      │ Local disk volume archiving      │ S3-compatible, memory-safe off-cluster storage ensures  │
│                                 │                                  │ PostgreSQL can execute Point-In-Time-Recovery (PITR)   │
│                                 │                                  │ even if all PostgreSQL worker nodes are wiped out.     │
├─────────────────────────────────┼──────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Asynchronous CloudEvents Buffer │ Synchronous HTTP Webhooks        │ Decouples write transactions from downstream consumers;│
│                                 │                                  │ prevents API latency spikes if downstream message      │
│                                 │                                  │ processors slow down or crash.                         │
└─────────────────────────────────┴──────────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

## ⚡ Quickstart Guide (Run & Verify in 3 Minutes)

### Option A: Local Full-Stack Emulation (Docker Compose)

Experience the complete 5-tier architecture locally on your laptop without needing a Kubernetes cluster:

```bash
# 1. Start all tiers in the background (RustFS, Postgres 16, Kafka KRaft, Django, Kong)
docker compose up -d --build

# 2. Check running services
docker compose ps

# 3. Verify health & readiness probes
curl -i http://localhost:8000/healthz/
curl -i http://localhost:8000/readyz/

# 4. Execute the automated end-to-end smoke test
python scripts/smoke-test.py --base-url http://localhost:8000

# 5. Stop and tear down
docker compose down -v
```

---

### Option B: Kubernetes Deployment via Helm 3

Deploy the platform to any Kubernetes cluster (Minikube, Kind, EKS, GKE, AKS, or bare metal):

```bash
# 1. Inspect and lint the Helm chart
python scripts/validate-helm.py

# 2. Deploy via Helm
helm upgrade --install enterprise-platform deploy/helm/enterprise-platform \
  --values deploy/helm/enterprise-platform/values.yaml

# 3. Verify pod status across namespaces
kubectl get pods -n data-tier
kubectl get pods -n messaging-tier
kubectl get pods -n app-tier
```

---

### Option C: Declarative GitOps via ArgoCD

Synchronize directly from Git:

```bash
# 1. Register the AppProject
kubectl apply -f deploy/argocd/appproject.yaml

# 2. Deploy the ArgoCD Application
kubectl apply -f deploy/argocd/application.yaml

# 3. Watch ArgoCD synchronize all tiers
kubectl -n argocd get application enterprise-platform-prod
```

---

## 🧪 Automated Testing & Security Validation Commands

Run the full local audit suite to test code quality, secrets, dependencies, and Kubernetes manifests:

```bash
# 1. Local DevSecOps Audit (Secrets, Antipatterns, Dependencies)
python scripts/security-scan.py

# 2. Helm Chart Syntax & Template Block Balance Check
python scripts/validate-helm.py

# 3. Raw Kubernetes Manifest & Kustomize Compilation Validator
python scripts/validate-manifests.py

# 4. Django Application Unit & Integration Tests (100% pass)
cd src/django-enterprise-api
python manage.py test
```

---

## 📂 Repository Directory Layout

```
cloud-native-resilient-blueprint/
├── .github/
│   └── workflows/
│       └── ci.yaml                       # DevSecOps CI/CD Pipeline (Trivy, Gitleaks, Test, Build, Push)
├── .gitleaks.toml                        # Gitleaks rule configuration & allowlists
├── .yamllint.yml                         # YAML formatting and pattern rules
├── config/kong/kong.yml                  # Declarative Kong Gateway configuration
├── deploy/
│   ├── argocd/                           # Declarative GitOps ArgoCD Manifests
│   │   ├── appproject.yaml               # ArgoCD AppProject with destination namespace constraints
│   │   ├── application.yaml              # Production ArgoCD Application (tracking Helm)
│   │   └── application-dev.yaml          # Development ArgoCD Application
│   ├── helm/enterprise-platform/         # Enterprise Platform Helm 3 Chart
│   │   ├── Chart.yaml                    # Helm chart metadata
│   │   ├── values.yaml                   # Base values & parameterization
│   │   ├── values-dev.yaml               # Dev environment overrides
│   │   ├── values-prod.yaml              # Production environment overrides
│   │   ├── .helmignore                   # Helm packaging ignore list
│   │   └── templates/                    # Parameterized multi-tier templates
│   │       ├── _helpers.tpl              # Shared template helpers
│   │       ├── 00-infrastructure/        # StorageClass, Namespaces, NetworkPolicies
│   │       ├── 01-data-tier/             # RustFS, CNPG Cluster, S3 Backups
│   │       ├── 02-messaging-tier/        # Apache Kafka KRaft StatefulSet & Topics
│   │       ├── 03-app-tier/              # Django API Deployment, Service, HPA, PDB
│   │       ├── 04-edge-routing/          # KongIngress, Ingress, Rate-limiting, Tracing
│   │       └── NOTES.txt                 # Post-install cluster instructions
│   └── kubernetes/                       # Standard Kustomize tiered manifests
├── docs/
│   ├── architecture.md                   # Full architecture deep-dive & sequence diagrams
│   ├── argocd-gitops.md                  # Comprehensive ArgoCD GitOps setup & operations
│   ├── disaster-recovery.md              # Database PITR, Kafka quorum, Longhorn rebuild
│   └── runbooks/
│       ├── operations.md                 # Scaling, secrets rotation, volume expansion
│       └── verification.md               # QA checklist and manual verification
├── scripts/
│   ├── security-scan.py                  # Local DevSecOps secret, pattern & dependency scanner
│   ├── validate-helm.py                  # Helm chart structure and template syntax validator
│   ├── validate-manifests.py             # Manifest specification & syntax validator
│   ├── smoke-test.py                     # End-to-end integration smoke test runner
│   ├── deploy.sh / deploy.ps1            # Multi-tier deployment orchestrators
│   └── teardown.sh                       # Teardown utility
├── src/django-enterprise-api/            # Django REST Framework Microservice
│   ├── apps/                             # Core (Kafka Producer, Health, Tracing), Articles, Users
│   ├── enterprise_platform/              # Settings (psycopg3, 12-factor), URLs, WSGI, ASGI
│   ├── tests/                            # Unit and integration test suite (9 tests)
│   ├── Dockerfile                        # Multi-stage production container build
│   ├── entrypoint.sh                     # DB wait, migrations, static collection, gunicorn
│   └── requirements.txt                  # Pinned Python dependencies
├── docker-compose.yml                    # Local multi-tier environment emulator
├── .env.example                          # Environment template
├── Makefile                              # Developer convenience targets
└── README.md                             # Platform documentation
```

---

## 👨‍💻 Author & Architecture Team

Architected by the **Platform Reliability & Cloud-Native Engineering Team**.  
Licensed under the **Apache 2.0 License**.
