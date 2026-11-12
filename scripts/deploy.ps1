<#
.SYNOPSIS
    Enterprise Event-Driven Micro-Platform (EEMP) PowerShell Deployment Orchestrator
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$K8sDir = Join-Path $ProjectRoot "deploy\kubernetes"

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host " Starting Enterprise Platform Deployment Orchestration" -ForegroundColor Cyan
Write-Host " Target Manifests: $K8sDir" -ForegroundColor Cyan
Write-Host "==============================================================================" -ForegroundColor Cyan

# Validate kubectl connection
try {
    kubectl cluster-info | Out-Null
} catch {
    Write-Warning "Could not connect to Kubernetes cluster via kubectl. Verify kubeconfig."
}

Write-Host "`n[1/5] Deploying Infrastructure Layer (Namespaces, Longhorn SC, Network Policies)..." -ForegroundColor Yellow
kubectl apply -k (Join-Path $K8sDir "00-infrastructure")

Write-Host "`n[2/5] Deploying Data Tier (RustFS Object Storage & CloudNativePG)..." -ForegroundColor Yellow
kubectl apply -k (Join-Path $K8sDir "01-data-tier")

Write-Host "`n[3/5] Deploying Messaging Tier (Apache Kafka KRaft StatefulSet & Topics)..." -ForegroundColor Yellow
kubectl apply -k (Join-Path $K8sDir "02-messaging-tier")

Write-Host "`n[4/5] Deploying Application Tier (Django REST Framework Microservice)..." -ForegroundColor Yellow
kubectl apply -k (Join-Path $K8sDir "03-app-tier")

Write-Host "`n[5/5] Deploying Edge Routing Layer (Kong Ingress & Plugins)..." -ForegroundColor Yellow
kubectl apply -k (Join-Path $K8sDir "04-edge-routing")

Write-Host "`n------------------------------------------------------------------------------"
Write-Host " Waiting for Pod rollouts..." -ForegroundColor Green
Write-Host "------------------------------------------------------------------------------"

kubectl rollout status statefulset/rustfs-storage -n data-tier --timeout=180s
kubectl rollout status statefulset/kafka-broker -n messaging-tier --timeout=180s
kubectl rollout status deployment/django-api -n app-tier --timeout=180s

Write-Host "`n[+] Deployment process finished." -ForegroundColor Green
