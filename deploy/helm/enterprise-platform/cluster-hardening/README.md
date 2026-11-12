# Cluster hardening prerequisites and operations

Kubernetes control-plane configuration and Velero installation are cluster
operations; they are not installed by this application chart. This directory
keeps the self-managed etcd encryption procedure with the Helm deployment.

- Use `encryption/README.md` only for self-managed Kubernetes API servers.
  Managed cluster encryption must be enabled through the cloud provider.
- Install and configure Velero with its AWS-compatible object-store plugin,
  the node-agent enabled, and credentials for the configured RustFS endpoint.
  The chart then creates a daily Velero `Schedule` and `BackupStorageLocation`.
- The Velero credential Secret must exist in the Velero namespace and contain a
  `cloud` key in the format expected by the AWS-compatible plugin. The chart
  references that Secret; it never creates or stores object-store credentials.
  For example, create it from a protected credentials file with
  `kubectl -n velero create secret generic cloud-credentials --from-file=cloud=/secure/path/credentials`.
- RustFS is currently hosted inside this same cluster. For disaster recovery
  against cluster loss, replicate the `cluster-backups` bucket to storage
  outside the cluster or configure an external S3-compatible destination.
- The scheduled backup includes Kubernetes Secrets. etcd encryption does not
  encrypt Velero's exported backup objects; protect and encrypt the object-store
  bucket and its access credentials separately.
- File-system volume backup is enabled by default and requires Velero's
  privileged node-agent. Velero documents file-system backup as beta and notes
  that it reads live filesystems, so it is not application-consistent. Keep
  CloudNativePG's native backup/WAL archiving for PostgreSQL, and design
  application-consistent backup or snapshot procedures for other stateful
  workloads. Set `clusterBackup.velero.defaultVolumesToFsBackup: false` if you
  do not want Velero to back up pod volumes.

The DevOps auditor receives get/list/watch access to operational resources but
not Secrets or mutation subresources. Use short-lived tokens:

```bash
kubectl -n platform-ops create token enterprise-platform-auditor --duration=1h
```

The `platform-superusers` group is bound to the `cluster-admin` ClusterRole.
Map that group only to a tightly controlled identity-provider group. Do not use
a shared service-account token for human superusers. The application service
account has no Kubernetes API permissions and does not automount a token.

ResourceQuota and LimitRange policies are rendered for each platform namespace.
Tune the values in `values.yaml` or `values-dev.yaml` to match actual cluster
capacity and workload requests.
