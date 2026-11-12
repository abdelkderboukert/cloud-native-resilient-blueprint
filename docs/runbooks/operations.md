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
1. Update `dataTier.cnpg.instances` to `5` in `deploy/helm/enterprise-platform/values-prod.yaml`.
2. Apply the Helm release update:
   ```bash
   bash scripts/deploy.sh deploy/helm/enterprise-platform/values-prod.yaml
   ```
3. CNPG orchestrates automated replica provisioning and Longhorn PVC binding with zero primary downtime.

---

## 2. Secrets Rotation

### 2.1 Database Credentials Rotation
1. Update the CNPG and Django credentials in the selected Helm values file, or preferably reference externally managed secrets.
2. Apply the updated release and trigger a rolling restart of the Django pods:
   ```bash
   bash scripts/deploy.sh deploy/helm/enterprise-platform/values-prod.yaml
   kubectl -n app-tier rollout restart deployment/django-api
   ```

### 2.2 RustFS S3 Credentials Rotation
1. Update `rustfs-secret` in `data-tier`.
2. Restart `rustfs-storage` StatefulSet.
3. Reload CNPG backup configuration to adopt the new credentials.

---

## 3. Storage Maintenance & Volume Expansion

To expand persistent volume size (e.g., expanding PostgreSQL storage from 20Gi to 50Gi):
1. In `values-prod.yaml`, change `dataTier.cnpg.storage.size` from `20Gi` to `50Gi`.
2. Apply the Helm release update:
   ```bash
   bash scripts/deploy.sh deploy/helm/enterprise-platform/values-prod.yaml
   ```
3. Longhorn automatically resizes the underlying block device online without unmounting the volume.
