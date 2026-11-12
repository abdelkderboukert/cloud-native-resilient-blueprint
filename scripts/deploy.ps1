<#
.SYNOPSIS
    Deploy the Enterprise Event-Driven Micro-Platform Helm chart.
.PARAMETER ValuesFile
    Optional values file. Defaults to the chart's values.yaml.
#>
param(
    [string]$ValuesFile
)

$ErrorActionPreference = "Stop"

function Invoke-CheckedCommand {
    param(
        [string]$Program,
        [string[]]$Arguments
    )

    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "'$Program $($Arguments -join ' ')' failed with exit code $LASTEXITCODE."
    }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$ChartDir = Join-Path $ProjectRoot "deploy\helm\enterprise-platform"

if ([string]::IsNullOrWhiteSpace($ValuesFile)) {
    $ValuesFile = Join-Path $ChartDir "values.yaml"
} elseif (-not [System.IO.Path]::IsPathRooted($ValuesFile)) {
    $ValuesFile = Join-Path $ProjectRoot $ValuesFile
}

if (-not (Test-Path -LiteralPath $ValuesFile -PathType Leaf)) {
    throw "Helm values file not found: $ValuesFile"
}

Invoke-CheckedCommand kubectl @("cluster-info")
Invoke-CheckedCommand helm @(
    "upgrade", "--install", "enterprise-platform", $ChartDir,
    "--namespace", "default", "--create-namespace", "--values", $ValuesFile
)
Invoke-CheckedCommand kubectl @(
    "-n", "data-tier", "rollout", "status", "statefulset/rustfs-storage", "--timeout=180s"
)
Invoke-CheckedCommand kubectl @(
    "-n", "messaging-tier", "rollout", "status", "statefulset/kafka-broker", "--timeout=180s"
)
Invoke-CheckedCommand kubectl @(
    "-n", "app-tier", "rollout", "status", "deployment/django-api", "--timeout=180s"
)
Invoke-CheckedCommand kubectl @(
    "get", "pods", "-A", "-l", "app.kubernetes.io/part-of=enterprise-event-driven-micro-platform"
)
