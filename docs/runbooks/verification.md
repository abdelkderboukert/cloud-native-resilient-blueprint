# Platform Verification & Quality Assurance Runbook

This document details verification steps to ensure every tier of the Enterprise Event-Driven Micro-Platform is functioning according to the specification.

---

## 1. Automated Verification Checks

### 1.1 Manifest Integrity & Kustomize Validation
Execute the manifest validator to verify all Kubernetes resources against specification constraints:
```bash
python scripts/validate-manifests.py
```
Expected output:
```
[*] Scanning manifests in deploy/kubernetes...
  [OK] 00-infrastructure/longhorn-sc.yaml
  [OK] 00-infrastructure/namespaces.yaml
  [OK] 00-infrastructure/network-policies.yaml
  [OK] 01-data-tier/...
  ...
[+] All manifests conform to the Enterprise Architecture Specification!
```

Verify Kustomize dry-run compilation:
```bash
kubectl kustomize deploy/kubernetes/ > /dev/null
```

### 1.2 Django Application Test Suite
Run the automated test suite testing health probes, Kafka event producer resilience, Article API CRUD/publish lifecycle, and User registration:
```bash
cd src/django-enterprise-api
python manage.py test
```
Expected output:
```
Ran 9 tests in 0.5s
OK
```

---

## 2. In-Cluster Verification

### 2.1 Pod Health & Ready State
Inspect pods across all architecture namespaces:
```bash
kubectl get pods -n data-tier
kubectl get pods -n messaging-tier
kubectl get pods -n app-tier
kubectl get ingress -n app-tier
```

### 2.2 End-to-End Smoke Test
Run the automated smoke test script against the deployed ingress host or local port-forward:
```bash
# Port-forward Django or Kong ingress
kubectl -n app-tier port-forward svc/django-service 8000:80

# In another terminal, run smoke test
python scripts/smoke-test.py --base-url http://localhost:8000
```

### 2.3 Network Policy Isolation Verification
Verify that pods outside the permitted network policy cannot access Postgres or Kafka directly:
```bash
# Attempt direct access to Postgres from an unauthorized pod
kubectl run test-probe --rm -it --image=busybox --restart=Never -- nc -zv postgres-cluster-rw.data-tier.svc.cluster.local 5432
# Expected: Connection timed out / refused by NetworkPolicy
```
