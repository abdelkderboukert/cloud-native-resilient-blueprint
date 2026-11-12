# Disaster Recovery Runbook: Enterprise Event-Driven Micro-Platform

This runbook outlines emergency recovery procedures for catastrophic cluster failures, data corruption, or worker node outages.

---

## 1. CloudNativePG (PostgreSQL) Recovery from RustFS S3 Backups

CloudNativePG continuously archives Write-Ahead Logs (WAL) and creates daily base backups in RustFS S3 (`s3://postgres-backups/`).

### 1.1 Verifying Available S3 Backups
Before initiating a restore, verify the backup contents in RustFS:
```bash
# Execute within a pod that has access to RustFS
mc alias set rustfs http://rustfs-service.data-tier.svc.cluster.local:9000 enterprise-admin-key enterprise-super-secret-key-32chars
mc ls rustfs/postgres-backups/
```

### 1.2 Full Cluster Restoration Manifest (`postgres-cluster-restore.yaml`)
To restore the database to a new or recovered cluster from the WAL archive:

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: postgres-cluster-recovered
  namespace: data-tier
spec:
  instances: 3
  imageName: ghcr.io/cloudnativepg/postgresql:16.2
  primaryUpdateStrategy: unsupervised
  storage:
    size: 20Gi
    storageClass: enterprise-longhorn-sc
  bootstrap:
    recovery:
      source: postgres-cluster-backup-source
  externalClusters:
    - name: postgres-cluster-backup-source
      barmanObjectStore:
        destinationPath: s3://postgres-backups/
        endpointURL: http://rustfs-service.data-tier.svc.cluster.local:9000
        s3Credentials:
          accessKeyId:
            name: rustfs-secret
            key: access-key
          secretAccessKey:
            name: rustfs-secret
            key: secret-key
```

Apply the recovery manifest:
```bash
kubectl apply -f postgres-cluster-restore.yaml
kubectl -n data-tier get cluster postgres-cluster-recovered -w
```

### 1.3 Point-In-Time-Recovery (PITR)
To restore the database to an exact historical timestamp (e.g., prior to an accidental table drop):
Add `recoveryTarget` under `spec.bootstrap.recovery`:
```yaml
      recoveryTarget:
        targetTime: "2026-11-12 01:00:00.000000+00"
```

---

## 2. Apache Kafka (KRaft Mode) Disaster Recovery

### 2.1 Quorum Recovery Scenario
If the KRaft metadata log becomes corrupted or the broker pod loses quorum:

1. **Scale down Kafka StatefulSet:**
   ```bash
   kubectl -n messaging-tier scale statefulset kafka-broker --replicas=0
   ```

2. **Inspect the Longhorn PV:**
   Ensure the underlying volume `kafka-data-kafka-broker-0` is healthy in the Longhorn UI.

3. **Format Metadata Log (Clean Quorum Reset):**
   If metadata storage must be re-initialized:
   ```bash
   # Re-format with cluster ID
   kafka-storage format -t "4L62EnnTQNmGQQuUhqwawA" -c /etc/kafka/kafka.properties
   ```

4. **Scale back up:**
   ```bash
   kubectl -n messaging-tier scale statefulset kafka-broker --replicas=1
   ```

5. **Re-initialize Enterprise Topics:**
   ```bash
   kubectl -n messaging-tier create job --from=cronjob/kafka-init-topics kafka-topic-repair
   ```

---

## 3. Longhorn Storage Rebuild & Replica Synchronization

### 3.1 Node Outage & Volume Rebuild
When a worker node fails, Longhorn flags the affected replica as `degraded` and automatically starts rebuilding on an available healthy worker node adhering to `numberOfReplicas: "2"`.

1. **Check Volume Status:**
   ```bash
   kubectl -n longhorn-system get volumes.longhorn.io
   ```
2. **Identify Degraded Volumes:**
   Look for volumes where `ROBUSTNESS` is `Degraded` instead of `Healthy`.
3. **Trigger Manual Replica Rebuild:**
   Navigate to the Longhorn Dashboard (`http://longhorn-frontend.longhorn-system.svc:80`), select the degraded volume, and click **Replicas -> Add Replica** to rebind to an active worker node.
4. **Volume Snapshot Restore:**
   If underlying disk corruption occurred, restore from the latest Longhorn recurring snapshot or S3 secondary backup target.
