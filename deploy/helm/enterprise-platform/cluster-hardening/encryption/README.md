# Kubernetes Secret encryption at rest

The Helm chart cannot configure encryption inside the Kubernetes API server. For
self-managed clusters, generate an API-server `EncryptionConfiguration` on
**every control-plane node** and configure each API server to use it. Do not put
the generated key in Git, Helm values, a container image, or a Kubernetes
Secret managed by the same API server.

Managed Kubernetes providers own the API-server configuration. Use the
provider's supported encryption-at-rest setting instead of editing its
control-plane nodes.

## Generate a key and configuration

Run this on a trusted administration host, then transfer the file to control
plane nodes over a protected channel:

```bash
sudo install -d -m 0700 /etc/kubernetes/enc
sudo bash deploy/helm/enterprise-platform/cluster-hardening/encryption/generate-config.sh \
  /etc/kubernetes/enc/encryption-config.yaml
```

The script refuses to overwrite an existing file, generates a fresh 256-bit
key, and writes the result with mode `0600`. Back up this file securely and
separately from the cluster. Without the key, encrypted Kubernetes Secrets
cannot be recovered.

## Enable on self-managed control planes

1. Back up the current etcd data and confirm the backup is restorable.
2. Copy the same encryption configuration to every control-plane node. Protect
   the file and its backup as cluster root credentials.
3. Configure each API server to load the file, for example by adding
   `--encryption-provider-config=/etc/kubernetes/enc/encryption-config.yaml`
   to its static-pod manifest. Follow the distribution's API-server
   configuration procedure and maintain quorum while restarting nodes one at
   a time.
4. Verify that API-server encryption is active using the Kubernetes
   distribution's documented procedure.
5. Re-write existing Secrets so they are encrypted with the configured
   provider:

   ```bash
   kubectl get secrets --all-namespaces -o json \
     | kubectl replace -f -
   ```

6. During key rotation, add the new key as the first `aescbc` key on every
   API server, restart API servers, re-write all Secrets, and only then remove
   the old key. Keep a protected backup of each key until re-encryption and
   recovery have both been verified.

The `identity` provider is deliberately retained as the final fallback so
existing unencrypted objects remain readable during migration. Do not remove it
until all existing Secrets have been re-written and verified.
