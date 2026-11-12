#!/usr/bin/env bash
# ==============================================================================
# Enterprise Event-Driven Micro-Platform (EEMP) Helm Teardown
# ==============================================================================
set -euo pipefail

RELEASE_NAME="enterprise-platform"
RELEASE_NAMESPACE="default"

if ! kubectl cluster-info > /dev/null 2>&1; then
    echo "[ERROR] Cannot reach Kubernetes cluster via kubectl. Please check your kubeconfig." >&2
    exit 1
fi

helm uninstall "${RELEASE_NAME}" \
    --namespace "${RELEASE_NAMESPACE}" \
    --ignore-not-found

echo "Helm release ${RELEASE_NAME} removed."
