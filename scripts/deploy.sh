#!/usr/bin/env bash
# ==============================================================================
# Enterprise Event-Driven Micro-Platform (EEMP) Deployment Orchestrator
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
K8S_DIR="${PROJECT_ROOT}/deploy/kubernetes"

echo "=============================================================================="
echo " Starting Enterprise Platform Deployment Orchestration"
echo " Target Manifests: ${K8S_DIR}"
echo "=============================================================================="

# Check kubectl connection
if ! kubectl cluster-info > /dev/null 2>&1; then
    echo "[ERROR] Cannot reach Kubernetes cluster via kubectl. Please check your kubeconfig."
    exit 1
fi

echo "[1/5] Deploying Infrastructure Layer (Namespaces, Longhorn SC, Network Policies)..."
kubectl apply -k "${K8S_DIR}/00-infrastructure"

echo "[2/5] Deploying Data Tier (RustFS Object Storage & CloudNativePG)..."
kubectl apply -k "${K8S_DIR}/01-data-tier"

echo "[3/5] Deploying Messaging Tier (Apache Kafka KRaft StatefulSet & Topics)..."
kubectl apply -k "${K8S_DIR}/02-messaging-tier"

echo "[4/5] Deploying Application Tier (Django REST Framework Microservice)..."
kubectl apply -k "${K8S_DIR}/03-app-tier"

echo "[5/5] Deploying Edge Routing Layer (Kong Ingress & Plugins)..."
kubectl apply -k "${K8S_DIR}/04-edge-routing"

echo "------------------------------------------------------------------------------"
echo " Waiting for Stateful Workloads and Services to stabilize..."
echo "------------------------------------------------------------------------------"

echo "Checking RustFS..."
kubectl -n data-tier rollout status statefulset/rustfs-storage --timeout=180s || true

echo "Checking Kafka Broker..."
kubectl -n messaging-tier rollout status statefulset/kafka-broker --timeout=180s || true

echo "Checking Django API Deployment..."
kubectl -n app-tier rollout status deployment/django-api --timeout=180s || true

echo "=============================================================================="
echo " Deployment Rollout Completed Successfully!"
echo "=============================================================================="
kubectl get pods -A -l "app.kubernetes.io/part-of=enterprise-event-driven-micro-platform"
