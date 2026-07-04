#!/usr/bin/env python3
"""Static guard matrix for internal/sensitive backend routes.

This intentionally avoids importing the FastAPI app. It reads server.py and
checks that the central gate middleware still covers every sensitive prefix
that release smoke depends on.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "agent" / "server.py"


@dataclass(frozen=True)
class GuardCheck:
    route: str
    reason: str
    token: str

@dataclass(frozen=True)
class EndpointGuardCheck:
    route: str
    function: str
    reason: str
    tokens: tuple[str, ...]


CHECKS = [
    GuardCheck("/metrics", "Prometheus metrics", 'path == "/metrics"'),
    GuardCheck("/vectors/stats", "Vector internals", 'path == "/vectors/stats"'),
    GuardCheck("/system/*", "System logs, traces, costs, judges, agents", 'path.startswith("/system")'),
    GuardCheck("/analytics/*", "Internal analytics summaries", 'path.startswith("/analytics")'),
    GuardCheck("/checkpoints/*", "Checkpoint state", 'path.startswith("/checkpoints")'),
    GuardCheck("/confirmations/*", "Confirmation state", 'path.startswith("/confirmations")'),
    GuardCheck("/confirm/*", "Write confirmation shortcut", 'path.startswith("/confirm/")'),
    GuardCheck("/reject/*", "Write rejection shortcut", 'path.startswith("/reject/")'),
    GuardCheck("/ab-testing/*", "Experiment internals", 'path.startswith("/ab-testing")'),
    GuardCheck("/prompt-cache/*", "Prompt cache internals", 'path.startswith("/prompt-cache")'),
    GuardCheck("/freshness/*", "Freshness scanner internals", 'path.startswith("/freshness")'),
]

ENDPOINT_CHECKS = [
    EndpointGuardCheck(
        "/vectors/build",
        "build_vectors",
        "Embedding rebuild is compute-heavy and internal",
        ('require_admin_scope', '"ops.deploy"'),
    ),
    EndpointGuardCheck(
        "/vectors/search",
        "vector_search_endpoint",
        "Raw vector scoring must not be a public discovery API",
        ('require_admin_scope', '"ops.deploy"'),
    ),
    EndpointGuardCheck(
        "/image/recognize",
        "image_recognize_endpoint",
        "Vision calls can spend LLM budget",
        ('require_admin_scope', '"ops.deploy"'),
    ),
]


def gate_source(text: str) -> str:
    start = text.find("async def gate_internal_endpoints")
    if start < 0:
        return ""
    end = text.find('\n@app.middleware("http")', start + 1)
    if end < 0:
        end = text.find("\nasync def ", start + 1)
    return text[start:end if end > start else len(text)]

def function_source(text: str, name: str) -> str:
    start = text.find(f"async def {name}(")
    if start < 0:
        return ""
    end = text.find("\n@app.", start + 1)
    return text[start:end if end > start else len(text)]


def main() -> int:
    source = SERVER.read_text(encoding="utf-8", errors="replace")
    gate = gate_source(source)
    failures: list[str] = []

    if not gate:
        failures.append("missing gate_internal_endpoints middleware")
    if "verify_admin_key" not in gate:
        failures.append("gate_internal_endpoints must call verify_admin_key")
    if "404" not in gate:
        failures.append("gate_internal_endpoints must hide sensitive paths with 404")

    print("Sensitive route guard matrix")
    print("============================")
    for check in CHECKS:
        ok = check.token in gate
        print(f"{'OK' if ok else 'FAIL'} {check.route:20} {check.reason}")
        if not ok:
            failures.append(f"{check.route} missing token {check.token}")

    for check in ENDPOINT_CHECKS:
        block = function_source(source, check.function)
        ok = bool(block) and all(token in block for token in check.tokens)
        print(f"{'OK' if ok else 'FAIL'} {check.route:20} {check.reason}")
        if not block:
            failures.append(f"{check.route} missing function {check.function}")
        elif not ok:
            failures.append(f"{check.route} missing endpoint guard tokens {check.tokens}")

    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
