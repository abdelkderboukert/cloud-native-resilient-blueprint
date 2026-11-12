#!/usr/bin/env python3
"""
Manifest Syntax and Architecture Validator (Standard Library Only)
Validates Kubernetes manifests against the Enterprise Event-Driven Micro-Platform specification.
"""

import sys
import re
from pathlib import Path

MANIFEST_DIR = Path(__file__).resolve().parent.parent / "deploy" / "kubernetes"

REQUIRED_TIERS = [
    "00-infrastructure",
    "01-data-tier",
    "02-messaging-tier",
    "03-app-tier",
    "04-edge-routing",
]

EXPECTED_STORAGE_CLASS = "enterprise-longhorn-sc"


def validate_file(file_path: Path):
    errors = []
    content = file_path.read_text(encoding="utf-8")
    docs = content.split("---")

    for i, doc in enumerate(docs):
        doc = doc.strip()
        if not doc or doc.startswith("#"):
            continue

        # Check required fields
        has_api_version = re.search(r"^apiVersion:\s*([^\s]+)", doc, re.MULTILINE)
        has_kind = re.search(r"^kind:\s*([^\s]+)", doc, re.MULTILINE)
        has_name = re.search(r"^\s+name:\s*([^\s]+)", doc, re.MULTILINE) or re.search(r"^metadata:\s*\n\s+name:\s*([^\s]+)", doc, re.MULTILINE)

        if not has_api_version:
            errors.append(f"{file_path.name} [doc #{i}]: Missing 'apiVersion'")
        if not has_kind:
            errors.append(f"{file_path.name} [doc #{i}]: Missing 'kind'")
        if not has_name:
            errors.append(f"{file_path.name} [doc #{i}]: Missing 'metadata.name'")

        kind = has_kind.group(1) if has_kind else ""

        # Specific architecture checks
        if kind == "StorageClass":
            if 'numberOfReplicas: "2"' not in doc and "numberOfReplicas: '2'" not in doc and "numberOfReplicas: 2" not in doc:
                errors.append(f"{file_path.name}: StorageClass must specify numberOfReplicas: '2'")
            if "reclaimPolicy: Retain" not in doc:
                errors.append(f"{file_path.name}: StorageClass must specify reclaimPolicy: Retain")

        if kind in ("StatefulSet", "Cluster"):
            if "volumeClaimTemplates" in doc or kind == "Cluster":
                if f'storageClassName: "{EXPECTED_STORAGE_CLASS}"' not in doc and f"storageClass: {EXPECTED_STORAGE_CLASS}" not in doc and f"storageClassName: {EXPECTED_STORAGE_CLASS}" not in doc:
                    errors.append(f"{file_path.name}: {kind} missing reference to expected StorageClass '{EXPECTED_STORAGE_CLASS}'")

    return errors


def main():
    print(f"[*] Scanning manifests in {MANIFEST_DIR}...")
    all_errors = []
    total_files = 0

    if not MANIFEST_DIR.exists():
        print(f"[!] Manifest directory does not exist: {MANIFEST_DIR}")
        sys.exit(1)

    for tier in REQUIRED_TIERS:
        tier_dir = MANIFEST_DIR / tier
        if not tier_dir.exists():
            all_errors.append(f"Missing required tier directory: {tier}")
            continue

        for yaml_file in sorted(tier_dir.glob("*.yaml")):
            if yaml_file.name == "kustomization.yaml":
                continue
            total_files += 1
            errors = validate_file(yaml_file)
            if errors:
                all_errors.extend(errors)
            else:
                print(f"  [OK] {tier}/{yaml_file.name}")

    print(f"\n[*] Validation complete: {total_files} manifest files evaluated.")
    if all_errors:
        print(f"[!] Found {len(all_errors)} error(s):")
        for err in all_errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("[+] All manifests conform to the Enterprise Architecture Specification!")
        sys.exit(0)


if __name__ == "__main__":
    main()
