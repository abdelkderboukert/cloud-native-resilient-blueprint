# Operations & Day-2 Management Runbook

This guide details routine administrative workflows, scaling, maintenance, and observability procedures for the platform.

---

## 1. Scaling Workloads

### 1.1 Scaling the Django Application Tier
The Django REST Framework tier is stateless and auto-scales via HPA:
```bash
# Check current autoscaler status
kubectl -n app-tier get hpa django-api-hpa

# Manual scaling override
kubectl -n app-tier scale deployment django-api --replicas=5
```

### 1.2 Scaling CloudNativePG Instances
To expand PostgreSQL read-replicas from 3 to 5:
1. Update `instances: 5` in `deploy/kubernetes/01-data-tier/cnpg-cluster.yaml`.
2. Apply the update:
   ```bash
   kubectl apply -k deploy/kubernetes/01-data-tier/
   ```
3. CNPG orchestrates automated replica provisioning and Longhorn PVC binding with zero primary downtime.

---

## 2. Secrets Rotation

### 2.1 Database Credentials Rotation
1. Update the password in `deploy/kubernetes/01-data-tier/cnpg-secret.yaml`.
2. Apply the updated secret:
   ```bash
   kubectl apply -f deploy/kubernetes/01-data-tier/cnpg-secret.yaml
   ```
3. Update `DATABASE_URL` in `deploy/kubernetes/03-app-tier/django-secret.yaml`.
4. Trigger a rolling restart of the Django pods:
   ```bash
   kubectl -n app-tier rollout restart deployment django-api
   ```

### 2.2 RustFS S3 Credentials Rotation
1. Update `rustfs-secret` in `data-tier`.
2. Restart `rustfs-storage` StatefulSet.
3. Reload CNPG backup configuration to adopt the new credentials.

---

## 3. Storage Maintenance & Volume Expansion

To expand persistent volume size (e.g., expanding PostgreSQL storage from 20Gi to 50Gi):
1. In `cnpg-cluster.yaml`, change `spec.storage.size` from `20Gi` to `50Gi`.
2. Apply the manifest:
   ```bash
   kubectl apply -k deploy/kubernetes/01-data-tier/
   ```
3. Longhorn automatically resizes the underlying block device online without unmounting the volume.
