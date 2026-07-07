"""
Health-check script for vinhlong360 backend.

Calls /health and optionally /health/deep, prints status, exits non-zero on failure.
Usable in CI pipelines and cron monitoring.

Usage:
    python scripts/health_check.py                          # quick check
    python scripts/health_check.py --deep                   # include /health/deep
    python scripts/health_check.py --base-url http://prod:8360
    python scripts/health_check.py --timeout 10 --json      # JSON output
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime


def _fetch(url: str, timeout: int) -> tuple[dict | None, str | None]:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return data, None
    except urllib.error.URLError as exc:
        return None, f"connection error: {exc.reason}"
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Health check for vinhlong360 backend.")
    parser.add_argument("--base-url", default="http://localhost:8360", help="backend base URL")
    parser.add_argument("--deep", action="store_true", help="also check /health/deep (LLM connectivity)")
    parser.add_argument("--timeout", type=int, default=5, help="request timeout in seconds (default: 5)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="output as JSON")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    results: dict = {"timestamp": datetime.now().isoformat(), "base_url": base, "checks": {}}
    all_ok = True

    health_data, health_err = _fetch(f"{base}/health", args.timeout)
    if health_err:
        results["checks"]["health"] = {"status": "FAIL", "error": health_err}
        all_ok = False
    else:
        status = health_data.get("status", "unknown") if health_data else "unknown"
        results["checks"]["health"] = {"status": "OK" if status == "ok" else "FAIL", "response": health_data}
        if status != "ok":
            all_ok = False

    if args.deep:
        deep_data, deep_err = _fetch(f"{base}/health/deep", max(args.timeout, 15))
        if deep_err:
            results["checks"]["health_deep"] = {"status": "FAIL", "error": deep_err}
            all_ok = False
        else:
            status = deep_data.get("status", "unknown") if deep_data else "unknown"
            results["checks"]["health_deep"] = {"status": "OK" if status == "ok" else "WARN", "response": deep_data}

    results["overall"] = "OK" if all_ok else "FAIL"

    if args.json_output:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"[health] {base}  ({results['timestamp']})")
        for name, check in results["checks"].items():
            status = check["status"]
            detail = check.get("error", "")
            if not detail and "response" in check:
                resp = check["response"]
                if isinstance(resp, dict):
                    detail = ", ".join(f"{k}={v}" for k, v in resp.items() if k != "status")
            print(f"  {name}: {status}  {detail}")
        print(f"  overall: {results['overall']}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
