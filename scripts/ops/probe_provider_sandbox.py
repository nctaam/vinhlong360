#!/usr/bin/env python3
"""Exercise provider ambiguity handling without contacting a real provider."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
AGENT = ROOT / "agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))


def _command() -> str:
    return subprocess.list2cmdline([sys.executable, *sys.argv])


def _head_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "0" * 40
    value = result.stdout.strip()
    return value if result.returncode == 0 and len(value) == 40 else "0" * 40


def run_deterministic_scenarios() -> dict[str, object]:
    """Run accepted, timeout-after-accept, and explicit rejection scenarios."""

    from sms_provider import EsmsProvider

    accepted_calls = 0

    def accepted(_url, _payload):
        nonlocal accepted_calls
        accepted_calls += 1
        return {"CodeResult": "100", "TransactionId": "sandbox-accepted"}

    timeout_calls = 0

    def timeout(_url, _payload):
        nonlocal timeout_calls
        timeout_calls += 1
        raise TimeoutError("deterministic provider timeout")

    rejected_calls = 0

    def rejected(_url, _payload):
        nonlocal rejected_calls
        rejected_calls += 1
        return {"CodeResult": "400"}

    # The rejection path is intentionally exercised through the real provider
    # implementation, but its backoff is suppressed to keep this probe fast.
    with patch("sms_provider.time.sleep", lambda _seconds: None):
        logging.disable(logging.CRITICAL)
        try:
            accepted_result = EsmsProvider(
                api_key="sandbox-key", secret="sandbox-secret", brandname="VL360", poster=accepted
            ).send("0901234567", "sandbox", delivery_key="sandbox-accepted")
            timeout_result = EsmsProvider(
                api_key="sandbox-key", secret="sandbox-secret", brandname="VL360", poster=timeout
            ).send("0901234567", "sandbox", delivery_key="sandbox-timeout")
            rejected_result = EsmsProvider(
                api_key="sandbox-key", secret="sandbox-secret", brandname="VL360", poster=rejected
            ).send("0901234567", "sandbox", delivery_key="sandbox-rejected")
        finally:
            logging.disable(logging.NOTSET)

    assert accepted_result.delivered and accepted_result.state == "accepted"
    assert not timeout_result.delivered and timeout_result.state == "ambiguous"
    assert timeout_result.retryable is False and timeout_calls == 1
    assert not rejected_result.delivered and rejected_result.state == "rejected"

    return {
        "status": "pass",
        "external_calls": 0,
        "scenarios": {
            "accepted": {"state": accepted_result.state, "calls": accepted_calls},
            "timeout": {
                "state": timeout_result.state,
                "calls": timeout_calls,
                "retryable": timeout_result.retryable,
            },
            "rejected": {"state": rejected_result.state, "calls": rejected_calls},
        },
    }


def _write_receipt(path: Path, *, result: dict[str, object], exit_code: int,
                   verdict: str, nodeids: list[str], started: datetime) -> dict[str, object]:
    output = json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    receipt = {
        "probe_id": "provider-sandbox",
        "head_sha": _head_sha(),
        "environment_id": "local-deterministic-provider-sandbox",
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
    parser.add_argument("--mode", choices=("deterministic", "live"), default="live")
    parser.add_argument(
        "--receipt",
        type=Path,
        default=ROOT / "artifacts" / "staging-evidence" / "provider-sandbox-receipt.json",
    )
    args = parser.parse_args(argv)
    started = datetime.now(timezone.utc)
    if args.mode != "deterministic":
        result = {"status": "unavailable", "reason": "live provider sandbox is not authorized by this probe"}
        receipt = _write_receipt(
            args.receipt,
            result=result,
            exit_code=2,
            verdict="UNAVAILABLE",
            nodeids=[],
            started=started,
        )
        print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
        return 2

    try:
        result = run_deterministic_scenarios()
    except Exception as exc:  # noqa: BLE001 - probe must emit a receipt on failure
        result = {"status": "failed", "error": type(exc).__name__}
        receipt = _write_receipt(
            args.receipt,
            result=result,
            exit_code=1,
            verdict="BLOCKED",
            nodeids=[],
            started=started,
        )
        print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
        return 1

    receipt = _write_receipt(
        args.receipt,
        result=result,
        exit_code=0,
        verdict="PASS",
        nodeids=[
            "provider-sandbox::accepted",
            "provider-sandbox::timeout-after-accept",
            "provider-sandbox::rejected",
        ],
        started=started,
    )
    print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
