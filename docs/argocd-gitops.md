# Declarative GitOps with ArgoCD & Helm

This guide outlines how to manage and continuously deploy the **Enterprise Event-Driven Micro-Platform (EEMP)** using ArgoCD and the Helm chart repository.

---

## 1. Architectural Overview

```mermaid
flowchart LR
    Dev["Developer Git Push"] -->|PR / Merge| Repo["Git Repository<br/>(deploy/helm/enterprise-platform)"]
    Repo -->|Webhook / Polling| ArgoCD["ArgoCD Controller<br/>(namespace: argocd)"]
    ArgoCD -->|Sync & Self-Heal| K8s["Kubernetes Control Plane"]

    subgraph K8s["Target Namespaces"]
        Infra["00-infrastructure<br/>(Longhorn SC, NetPol)"]
        Data["01-data-tier<br/>(RustFS, CNPG)"]
        Msg["02-messaging-tier<br/>(Kafka KRaft)"]
        App["03-app-tier<br/>(Django API)"]
        Edge["04-edge-routing<br/>(Kong Ingress)"]
    end

    ArgoCD -. Reconciles .-> Infra
    ArgoCD -. Reconciles .-> Data
    ArgoCD -. Reconciles .-> Msg
    ArgoCD -. Reconciles .-> App
    ArgoCD -. Reconciles .-> Edge
```

---

## 2. Installing ArgoCD in the Cluster

If ArgoCD is not yet provisioned in your Kubernetes cluster:

```bash
# 1. Create ArgoCD namespace
kubectl create namespace argocd

# 2. Install official ArgoCD manifests
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.10.4/manifests/install.yaml

# 3. Wait for ArgoCD server rollout
kubectl -n argocd rollout status deployment/argocd-server --timeout=180s

# 4. Access the ArgoCD Web UI (port-forward)
kubectl -n argocd port-forward svc/argocd-server -n argocd 8080:443
```

Retrieve the initial `admin` credentials:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
```

---

## 3. Registering the EEMP AppProject

The `AppProject` isolates permissions and enforces destination namespace whitelisting.

```bash
kubectl apply -f deploy/argocd/appproject.yaml
```

Inspect the project:
```bash
kubectl -n argocd get appproject enterprise-platform
```

---

## 4. Bootstrapping the Helm Application

Deploy the declarative ArgoCD `Application` to synchronize the Helm chart:

### Production Deployment:
```bash
kubectl apply -f deploy/argocd/application.yaml
```

### Development Deployment:
```bash
kubectl apply -f deploy/argocd/application-dev.yaml
```

### Inspect Sync Status via CLI:
```bash
# Check application status
kubectl -n argocd get application enterprise-platform-prod

# Trigger manual synchronization
argocd app sync enterprise-platform-prod
```

---

## 5. Automated Sync, Self-Healing & Pruning

The production application manifest defines:
* **`automated.prune: true`**: Automatically removes obsolete Kubernetes resources when deleted from the Helm chart.
* **`automated.selfHeal: true`**: Reconciles manual drift or `kubectl edit` interventions back to the desired Git state.
* **`syncOptions`**:
  - `CreateNamespace=true`: Automatically provisions namespaces before template application.
  - `ApplyOutOfSyncOnly=true`: Optimizes sync speed by only applying resources that have drifted.
  - `PruneLast=true`: Ensures new deployments are healthy before pruning old workloads.

---

## 6. Trivy DevSecOps Security Gate

Every Git commit pushed to `main` or pull request triggers the CI pipeline:
1. **Secret & Pattern Gate**: Gitleaks and Trivy filesystem secret scans.
2. **Dependency Audit**: `pip-audit` checks Python dependencies against vulnerability databases.
3. **Helm Misconfiguration Gate**: Trivy config scanner audits the Helm chart for security risks (e.g. root execution, privilege escalation, unconstrained resources).
4. **Container Scan & Release**: Builds Django image, scans with Trivy, and pushes to `ghcr.io` for ArgoCD to pull.
