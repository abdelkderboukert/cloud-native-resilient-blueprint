#!/usr/bin/env bash
# Install or update the platform Helm release.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
CHART_DIR="${PROJECT_ROOT}/deploy/helm/enterprise-platform"
VALUES_FILE="${1:-${CHART_DIR}/values.yaml}"
RELEASE_NAME="enterprise-platform"
RELEASE_NAMESPACE="default"

if [[ "${VALUES_FILE}" != /* ]]; then
    VALUES_FILE="${PROJECT_ROOT}/${VALUES_FILE}"
fi

if [[ ! -f "${VALUES_FILE}" ]]; then
    echo "[ERROR] Helm values file not found: ${VALUES_FILE}" >&2
    exit 1
fi

if ! kubectl cluster-info > /dev/null 2>&1; then
    echo "[ERROR] Cannot reach Kubernetes cluster via kubectl. Please check your kubeconfig." >&2
    exit 1
fi

echo "Deploying ${RELEASE_NAME} from Helm chart: ${CHART_DIR}"
echo "Using values: ${VALUES_FILE}"

helm upgrade --install "${RELEASE_NAME}" "${CHART_DIR}" \
    --namespace "${RELEASE_NAMESPACE}" \
    --create-namespace \
    --values "${VALUES_FILE}"

echo "Waiting for platform workloads..."
kubectl -n data-tier rollout status statefulset/rustfs-storage --timeout=180s
kubectl -n messaging-tier rollout status statefulset/kafka-broker --timeout=180s
kubectl -n app-tier rollout status deployment/django-api --timeout=180s

echo "Deployment completed successfully."
kubectl get pods -A -l "app.kubernetes.io/part-of=enterprise-event-driven-micro-platform"
