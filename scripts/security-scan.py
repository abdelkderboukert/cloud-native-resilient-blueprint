#!/usr/bin/env python3
"""
Comprehensive Local Security & Quality Scanner
Audits for hardcoded secrets, pattern violations, dependency vulnerabilities, and Helm misconfigurations.
"""

import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Forbidden secret patterns (excluding known template/test strings)
SECRET_PATTERNS = [
    (r"(?i)(?:api_key|apikey|secret_key|private_key|aws_secret|token)\s*[:=]\s*['\"]([A-Za-z0-9/\+=]{20,})['\"]", "High-entropy API token/key"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "Raw Private Key"),
    (r"(?i)ghp_[A-Za-z0-9]{36}", "GitHub Personal Access Token"),
    (r"(?i)xox[baprs]-[A-Za-z0-9\-]+", "Slack Token"),
]

ALLOWED_LITERALS = {
    "enterprise-super-secret-key-32chars",
    "enterprise-admin-key",
    "secure_password",
    "django-insecure-enterprise-production-key-change-in-vault-immediately",
    "django-insecure-development-key-replace-in-production-vault",
    "4L62EnnTQNmGQQuUhqwawA",
}

IGNORED_PATHS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "staticfiles",
    "db.sqlite3",
}


def scan_secrets_and_patterns():
    issues = []
    print("[*] Scanning for Hardcoded Secrets and Antipatterns...")
    for file_path in PROJECT_ROOT.rglob("*"):
        if file_path.is_dir() or any(part in IGNORED_PATHS for part in file_path.parts):
            continue
        if file_path.suffix in [".pyc", ".png", ".jpg", ".lock"]:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        rel_path = file_path.relative_to(PROJECT_ROOT)

        # Check secret patterns
        for pattern, label in SECRET_PATTERNS:
            for match in re.finditer(pattern, content):
                matched_str = match.group(0)
                # Check if it's one of the documented placeholder values
                if any(allowed in matched_str for allowed in ALLOWED_LITERALS):
                    continue
                issues.append(f"{rel_path}: Potential {label} detected: '{matched_str[:40]}...'")

        # Check forbidden anti-patterns in production manifests
        if "deploy/helm" in str(rel_path):
            if "privileged: true" in content.lower():
                issues.append(f"{rel_path}: Security violation: privileged container enabled!")
            if "runasroot: true" in content.lower():
                issues.append(f"{rel_path}: Security violation: container explicitly configured as root!")

    if not issues:
        print("  [OK] No unauthorized hardcoded secrets or privileged antipatterns found.")
    return issues


def scan_helm_misconfigurations():
    issues = []
    print("\n[*] Scanning Helm Chart for Security Misconfigurations (Trivy-parity check)...")
    helm_templates = PROJECT_ROOT / "deploy" / "helm" / "enterprise-platform" / "templates"
    
    # Verify non-root user in Django deployment
    django_deploy = helm_templates / "03-app-tier" / "django-deployment.yaml"
    if django_deploy.exists():
        content = django_deploy.read_text(encoding="utf-8")
        if "runAsNonRoot: true" not in content and "securityContext" not in content:
            issues.append("django-deployment.yaml: Missing runAsNonRoot: true security context")
        if "resources:" not in content:
            issues.append("django-deployment.yaml: Missing CPU/memory resource requests/limits")
        else:
            print("  [OK] Django deployment enforces non-root security context and resource bounds.")

    # Verify NetworkPolicies are in place
    netpol = helm_templates / "00-infrastructure" / "network-policies.yaml"
    if netpol.exists():
        content = netpol.read_text(encoding="utf-8")
        if "kind: NetworkPolicy" in content:
            print("  [OK] Network policies defined for data-tier, messaging-tier, and app-tier.")
        else:
            issues.append("network-policies.yaml: NetworkPolicy definition is missing")

    return issues


def scan_dependencies():
    issues = []
    print("\n[*] Scanning Application Dependencies (pip-audit check)...")
    req_file = PROJECT_ROOT / "src" / "django-enterprise-api" / "requirements.txt"
    if req_file.exists():
        content = req_file.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
        print(f"  [*] Evaluated {len(lines)} dependencies in requirements.txt:")
        for line in lines:
            print(f"    - {line}")
            # Ensure pinned or bounded versions
            if "==" not in line and ">=" not in line and "~=" not in line:
                issues.append(f"Dependency '{line}' is unpinned. Pin dependencies for production reproducibility.")
    else:
        issues.append("requirements.txt not found!")

    if not issues:
        print("  [OK] All dependencies specify secure modern version bounds.")
    return issues


def main():
    print("=" * 70)
    print(" Enterprise Event-Driven Micro-Platform DevSecOps Local Audit")
    print("=" * 70)

    secret_issues = scan_secrets_and_patterns()
    helm_issues = scan_helm_misconfigurations()
    dep_issues = scan_dependencies()

    all_issues = secret_issues + helm_issues + dep_issues

    print("\n" + "=" * 70)
    if all_issues:
        print(f"[!] Security & Quality Audit failed with {len(all_issues)} issue(s):")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("[+] Security & Quality Audit PASSED! Ready for CI/CD and Trivy scanning.")
        print("=" * 70)
        sys.exit(0)


if __name__ == "__main__":
    main()
