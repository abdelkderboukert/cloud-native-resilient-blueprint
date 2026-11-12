#!/usr/bin/env python3
"""
Enterprise Event-Driven Micro-Platform End-to-End Smoke Test
Validates edge routing, Django API, PostgreSQL persistence, and event telemetry.
"""

import sys
import time
import argparse
import urllib.request
import urllib.error
import json
import uuid


def make_request(url, method="GET", data=None, headers=None):
    headers = headers or {}
    req_headers = {"User-Agent": "EEMP-SmokeTest/1.0", **headers}
    payload = json.dumps(data).encode("utf-8") if data else None

    req = urllib.request.Request(url, data=payload, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode("utf-8")
            res_headers = dict(response.headers)
            try:
                parsed_json = json.loads(res_body)
            except Exception:
                parsed_json = res_body
            return response.status, parsed_json, res_headers
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            parsed_json = json.loads(body)
        except Exception:
            parsed_json = body
        return e.code, parsed_json, dict(e.headers)
    except Exception as exc:
        return 0, str(exc), {}


def run_smoke_test(base_url, host_header=None):
    print("=" * 65)
    print(f"[*] Running EEMP End-to-End Smoke Test against: {base_url}")
    if host_header:
        print(f"[*] Ingress Host Header: {host_header}")
    print("=" * 65)

    default_headers = {"Content-Type": "application/json"}
    if host_header:
        default_headers["Host"] = host_header

    print("\n[Step 1] Checking Liveness Probe (/healthz/)...")
    status, body, _ = make_request(f"{base_url}/healthz/", headers=default_headers)
    print(f"  -> HTTP {status}: {body}")
    assert status == 200, f"Expected 200 from /healthz/, got {status}"
    assert body.get("status") == "healthy", "Expected healthy status"

    print("\n[Step 2] Checking Readiness Probe (/readyz/)...")
    status, body, _ = make_request(f"{base_url}/readyz/", headers=default_headers)
    print(f"  -> HTTP {status}: {body}")
    assert status in (200, 503), f"Unexpected status {status} from /readyz/"

    print("\n[Step 3] Creating Enterprise User (triggers user.registered event)...")
    test_user = f"smoke_user_{uuid.uuid4().hex[:6]}"
    user_payload = {
        "username": test_user,
        "email": f"{test_user}@enterprise.local",
        "password": "SmokeTestPassword99!",
        "tier": "enterprise",
        "department": "Platform Reliability",
    }
    status, body, headers = make_request(
        f"{base_url}/api/v1/users/",
        method="POST",
        data=user_payload,
        headers=default_headers,
    )
    print(f"  -> HTTP {status}: User created with ID {body.get('id')}")
    assert status == 201, f"Expected 201 Created for user registration, got {status}"

    print("\n[Step 4] Creating Article (triggers article.created event)...")
    article_payload = {
        "title": f"Resilience Blueprint Verification {uuid.uuid4().hex[:4]}",
        "content": "Automated verification of KRaft Kafka, CloudNativePG, and Longhorn CSI.",
        "author": test_user,
    }
    corr_id = f"smoke-corr-{uuid.uuid4().hex[:8]}"
    art_headers = {**default_headers, "X-Request-ID": corr_id}
    status, body, headers = make_request(
        f"{base_url}/api/v1/articles/",
        method="POST",
        data=article_payload,
        headers=art_headers,
    )
    print(f"  -> HTTP {status}: Article created with ID {body.get('id')}")
    assert status == 201, f"Expected 201 Created for article, got {status}"
    article_id = body.get("id")

    print(f"\n[Step 5] Publishing Article {article_id} (triggers article.published event)...")
    status, body, _ = make_request(
        f"{base_url}/api/v1/articles/{article_id}/publish/",
        method="POST",
        headers=default_headers,
    )
    print(f"  -> HTTP {status}: Article status is now: {body.get('status')}")
    assert status == 200, f"Expected 200 for article publish, got {status}"
    assert body.get("status") == "published", "Article status did not transition to published"

    print("\n[Step 6] Inspecting Prometheus Metrics (/metrics/)...")
    status, body, _ = make_request(f"{base_url}/metrics/", headers=default_headers)
    print(f"  -> HTTP {status} (Content length: {len(body)} bytes)")
    assert status == 200, f"Expected 200 from /metrics/, got {status}"
    assert "enterprise_events_published_total" in body

    print("\n" + "=" * 65)
    print("[+] All Smoke Test stages PASSED successfully!")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="EEMP End-to-End Smoke Test")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of Django API or Kong Ingress")
    parser.add_argument("--host-header", default=None, help="Host header for routing (e.g. api.enterprise.local)")
    args = parser.parse_args()

    try:
        run_smoke_test(args.base_url, args.host_header)
    except AssertionError as e:
        print(f"\n[!] Smoke Test Assertion Failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[!] Smoke Test Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
