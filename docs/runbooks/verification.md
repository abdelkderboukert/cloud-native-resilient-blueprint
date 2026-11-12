# Platform Verification & Quality Assurance Runbook

This document details verification steps to ensure every tier of the Enterprise Event-Driven Micro-Platform is functioning according to the specification.

---

## 1. Automated Verification Checks

### 1.1 Helm Chart Validation
Lint and render the Helm chart to verify its templates and default values:
```bash
make validate
```

### 1.2 Django Application Test Suite
Run the automated test suite testing health probes, Kafka event producer resilience, Article API CRUD/publish lifecycle, and User registration:
```bash
make test
```
Expected output:
```
Ran 10 tests in 0.5s
OK
```
The article API tests verify that repeated list/detail reads are served from
cache and successful updates invalidate cached data.

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
