#!/usr/bin/env bash
# ==============================================================================
# Enterprise Event-Driven Micro-Platform (EEMP) Teardown Utility
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
K8S_DIR="${PROJECT_ROOT}/deploy/kubernetes"

echo "Tearing down Enterprise Platform resources in reverse order..."

kubectl delete -k "${K8S_DIR}/04-edge-routing" --ignore-not-found
kubectl delete -k "${K8S_DIR}/03-app-tier" --ignore-not-found
kubectl delete -k "${K8S_DIR}/02-messaging-tier" --ignore-not-found
kubectl delete -k "${K8S_DIR}/01-data-tier" --ignore-not-found
kubectl delete -k "${K8S_DIR}/00-infrastructure" --ignore-not-found

echo "Teardown complete."
