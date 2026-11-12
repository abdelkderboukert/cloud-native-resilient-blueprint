#!/usr/bin/env python3
"""
Helm Chart Structure and Template Syntax Validator
Validates the enterprise-platform Helm chart without requiring local Helm installation.
"""

import sys
import re
from pathlib import Path

CHART_DIR = Path(__file__).resolve().parent.parent / "deploy" / "helm" / "enterprise-platform"


def validate_chart():
    errors = []
    print(f"[*] Validating Helm Chart at: {CHART_DIR}")

    chart_yaml = CHART_DIR / "Chart.yaml"
    if not chart_yaml.exists():
        return ["Chart.yaml is missing!"]

    content = chart_yaml.read_text(encoding="utf-8")
    for field in ["apiVersion: v2", "name: enterprise-platform", "version:", "appVersion:"]:
        if field not in content:
            errors.append(f"Chart.yaml missing expected field: '{field}'")
    print("  [OK] Chart.yaml metadata verified.")

    values_yaml = CHART_DIR / "values.yaml"
    if not values_yaml.exists():
        return ["values.yaml is missing!"]

    v_content = values_yaml.read_text(encoding="utf-8")
    for block in ["global:", "dataTier:", "messagingTier:", "appTier:", "edgeRouting:", "infrastructure:"]:
        if block not in v_content:
            errors.append(f"values.yaml missing configuration block: '{block}'")
    print("  [OK] values.yaml structure verified.")

    templates_dir = CHART_DIR / "templates"
    if not templates_dir.exists():
        return ["templates directory is missing!"]

    template_files = list(templates_dir.rglob("*.yaml"))
    print(f"  [*] Checking {len(template_files)} template files...")

    for t_file in sorted(template_files):
        t_content = t_file.read_text(encoding="utf-8")

        # Helm control blocks must have matching end statements.
        ifs = len(re.findall(r"\{\{-?\s*if\s+", t_content))
        withs = len(re.findall(r"\{\{-?\s*with\s+", t_content))
        ranges = len(re.findall(r"\{\{-?\s*range\s+", t_content))
        defines = len(re.findall(r"\{\{-?\s*define\s+", t_content))
        ends = len(re.findall(r"\{\{-?\s*end\s*-?\}\}", t_content))

        open_blocks = ifs + withs + ranges + defines
        if open_blocks != ends:
            errors.append(
                f"{t_file.relative_to(CHART_DIR)}: Template block mismatch (opened: {open_blocks}, closed: {ends})"
            )
        else:
            print(f"    [OK] {t_file.relative_to(CHART_DIR)}")

    return errors


def main():
    errors = validate_chart()
    if errors:
        print(f"\n[!] Helm Validation Failed with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\n[+] All Helm chart templates, metadata, and values passed validation successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
