#!/usr/bin/env bash
set -euo pipefail
umask 077

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <output-path>" >&2
    exit 2
fi

if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl is required to generate the encryption key." >&2
    exit 1
fi

output_path="$1"
output_dir="$(dirname "${output_path}")"
mkdir -p "${output_dir}"

if [[ -e "${output_path}" ]]; then
    echo "Refusing to overwrite existing file: ${output_path}" >&2
    exit 1
fi

temporary_file="$(mktemp "${output_path}.tmp.XXXXXX")"
trap 'rm -f "${temporary_file}"' EXIT
encryption_key="$(openssl rand -base64 32)"

cat > "${temporary_file}" <<EOF
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
- resources:
  - secrets
  providers:
  - aescbc:
      keys:
      - name: key1
        secret: ${encryption_key}
  - identity: {}
EOF

chmod 600 "${temporary_file}"
if ! ln "${temporary_file}" "${output_path}"; then
    echo "Could not safely create encryption configuration: ${output_path}" >&2
    exit 1
fi
rm "${temporary_file}"
trap - EXIT

echo "Wrote an encryption configuration with mode 0600 to ${output_path}."
echo "Protect and back up this file separately; losing its key makes encrypted Secrets unreadable."
