#!/usr/bin/env python3
"""Probe a disposable loopback reverse proxy without accepting production URLs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def validate_base_url(raw: str) -> tuple[bool, str]:
    """Allow only an explicit HTTP(S) loopback endpoint for this probe."""

    if not isinstance(raw, str) or not raw.strip():
        return False, "base URL is required"
    try:
        parsed = urlsplit(raw.strip())
    except ValueError:
        return False, "base URL is invalid"
    if parsed.scheme not in {"http", "https"}:
        return False, "base URL must use http or https"
    if parsed.username or parsed.password:
        return False, "base URL must not contain credentials"
    if parsed.hostname not in _LOOPBACK_HOSTS:
        return False, "non-loopback host"
    if parsed.query or parsed.fragment:
        return False, "base URL must not contain query or fragment"
    return True, ""


def _normalise_base(raw: str) -> str:
    parsed = urlsplit(raw.rstrip("/"))
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def _fetch(base_url: str, path: str) -> dict[str, object]:
    url = f"{base_url}{path}"
    request = Request(url, headers={"Accept": "application/json,text/html;q=0.9"})
    try:
        with urlopen(request, timeout=5) as response:  # noqa: S310 - URL is loopback-validated
            return {
                "status": response.status,
                "headers": {key.lower(): value for key, value in response.headers.items()},
                "body_prefix": response.read(256).decode("utf-8", errors="replace"),
            }
    except HTTPError as exc:
        return {
            "status": exc.code,
            "headers": {key.lower(): value for key, value in exc.headers.items()},
            "body_prefix": exc.read(256).decode("utf-8", errors="replace"),
        }
    except (OSError, URLError, TimeoutError) as exc:
        return {"error": type(exc).__name__}


def probe_contract(base_url: str) -> dict[str, object]:
    """Check health, SSR and authenticated no-store boundary behaviour."""

    valid, reason = validate_base_url(base_url)
    if not valid:
        return {"status": "unavailable", "reason": reason}
    base = _normalise_base(base_url)
    health = _fetch(base, "/health")
    ssr = _fetch(base, "/")
    authenticated = _fetch(base, "/api/cases/status")
    checks = {
        "health": {
            "status_200": health.get("status") == 200,
            "no_store": "no-store" in str(health.get("headers", {}).get("cache-control", "")).lower(),
        },
        "ssr": {
            "status_200": ssr.get("status") == 200,
            "html": "text/html" in str(ssr.get("headers", {}).get("content-type", "")).lower(),
        },
        "authenticated": {
            "status_401": authenticated.get("status") == 401,
            "no_store": "no-store" in str(authenticated.get("headers", {}).get("cache-control", "")).lower(),
        },
    }
    passed = all(all(check.values()) for check in checks.values())
    return {
        "status": "pass" if passed else "fail",
        "base_url": base,
        "checks": checks,
        "responses": {"health": health, "ssr": ssr, "authenticated": authenticated},
    }


def _command() -> str:
    return subprocess.list2cmdline([sys.executable, *sys.argv])


def _head_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return "0" * 40
    value = result.stdout.strip()
    return value if result.returncode == 0 and len(value) == 40 else "0" * 40


def _write_receipt(path: Path, *, result: dict[str, object], exit_code: int,
                   verdict: str, nodeids: list[str], started: datetime) -> dict[str, object]:
    output = json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    receipt = {
        "probe_id": "proxy-contract",
        "head_sha": _head_sha(),
        "environment_id": "local-loopback-proxy",
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "command": _command(),
        "exit_code": exit_code,
        "output_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
        "captured_output": output,
        "test_nodeids": nodeids,
        "verdict": verdict,
        "result": result,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="")
    parser.add_argument(
        "--receipt",
        type=Path,
        default=ROOT / "artifacts" / "staging-evidence" / "proxy-contract-receipt.json",
    )
    args = parser.parse_args(argv)
    started = datetime.now(timezone.utc)
    result = probe_contract(args.base_url)
    if result["status"] == "unavailable":
        receipt = _write_receipt(
            args.receipt, result=result, exit_code=2, verdict="UNAVAILABLE", nodeids=[], started=started
        )
        print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
        return 2
    if result["status"] != "pass":
        receipt = _write_receipt(
            args.receipt,
            result=result,
            exit_code=1,
            verdict="BLOCKED",
            nodeids=["proxy-contract::health", "proxy-contract::ssr", "proxy-contract::authenticated"],
            started=started,
        )
        print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
        return 1
    receipt = _write_receipt(
        args.receipt,
        result=result,
        exit_code=0,
        verdict="PASS",
        nodeids=["proxy-contract::health", "proxy-contract::ssr", "proxy-contract::authenticated"],
        started=started,
    )
    print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
