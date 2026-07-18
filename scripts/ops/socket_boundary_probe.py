#!/usr/bin/env python3
"""Validate that production listeners stay inside the reviewed socket boundary."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable, Sequence
from typing import NamedTuple


PROHIBITED_PUBLIC_PORTS = frozenset(
    {3000, 3001, 3100, 5432, 6379, 8360, 8361, 9080, 9090}
)
PUBLIC_HTTP_PORTS = (80, 443)
PUBLIC_SSH_PORT = 22
OWNER_PATTERN = re.compile(r'\("([^"\\]+)"')


class Listener(NamedTuple):
    host: str
    port: int
    owners: tuple[str, ...]


def _parse_endpoint(endpoint: str) -> tuple[str, int]:
    if endpoint.startswith("["):
        closing = endpoint.find("]")
        if closing == -1 or endpoint[closing + 1 : closing + 2] != ":":
            raise ValueError("invalid bracketed listener endpoint")
        host = endpoint[1:closing]
        port_text = endpoint[closing + 2 :]
    else:
        try:
            host, port_text = endpoint.rsplit(":", 1)
        except ValueError as exc:
            raise ValueError("listener endpoint has no port") from exc

    try:
        port = int(port_text)
    except ValueError as exc:
        raise ValueError("listener endpoint has an invalid port") from exc
    if not 1 <= port <= 65535:
        raise ValueError("listener port is outside the TCP range")

    host_without_zone = host.split("%", 1)[0]
    if host_without_zone == "*":
        normalized_host = "*"
    else:
        try:
            normalized_host = str(ipaddress.ip_address(host_without_zone))
        except ValueError as exc:
            raise ValueError("listener endpoint has a non-numeric address") from exc
    return normalized_host, port


def parse_ss_output(source: str) -> list[Listener]:
    """Parse numeric ``ss -H -ltnp`` output without retaining PIDs or FDs."""
    listeners: list[Listener] = []
    for line_number, raw_line in enumerate(source.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split(maxsplit=5)
        if len(fields) < 5 or fields[0] != "LISTEN":
            raise ValueError(f"unrecognized ss listener line {line_number}")
        host, port = _parse_endpoint(fields[3])
        process_field = fields[5] if len(fields) == 6 else ""
        owners = tuple(sorted(set(OWNER_PATTERN.findall(process_field))))
        listeners.append(Listener(host=host, port=port, owners=owners))
    return listeners


def _is_loopback(host: str) -> bool:
    if host == "*":
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv4Address):
        return address in ipaddress.ip_network("127.0.0.0/8")
    return address == ipaddress.IPv6Address("::1")


def _owner_label(listener: Listener) -> str:
    return ",".join(listener.owners) if listener.owners else "unowned"


def _is_nginx_owned(listener: Listener) -> bool:
    return bool(listener.owners) and all(owner.lower() == "nginx" for owner in listener.owners)


def _is_sshd_owned(listener: Listener) -> bool:
    return listener.owners == ("sshd",)


def _internal_boundary_violations(listeners: Iterable[Listener]) -> set[str]:
    return {
        f"internal-port-not-loopback:{listener.port}:{listener.host}:"
        f"{_owner_label(listener)}"
        for listener in listeners
        if listener.port in PROHIBITED_PUBLIC_PORTS and not _is_loopback(listener.host)
    }


def _missing_loopback_violations(
    listeners: Iterable[Listener],
    expected_loopback_ports: Iterable[int],
) -> set[str]:
    materialized = list(listeners)
    violations: set[str] = set()
    for port in sorted(set(expected_loopback_ports)):
        if not any(item.port == port and _is_loopback(item.host) for item in materialized):
            violations.add(f"missing-loopback-listener:{port}")
    return violations


def _public_listener_violations(listeners: Iterable[Listener]) -> set[str]:
    public = [
        listener
        for listener in listeners
        if not _is_loopback(listener.host)
    ]
    violations: set[str] = set()
    for listener in public:
        if listener.port == PUBLIC_SSH_PORT:
            if not _is_sshd_owned(listener):
                violations.add(
                    f"public-ssh-not-sshd:{listener.port}:{listener.host}:"
                    f"{_owner_label(listener)}"
                )
        elif listener.port in PUBLIC_HTTP_PORTS:
            if not _is_nginx_owned(listener):
                violations.add(
                    f"public-http-not-nginx:{listener.port}:{listener.host}:"
                    f"{_owner_label(listener)}"
                )
        elif listener.port not in PROHIBITED_PUBLIC_PORTS:
            violations.add(
                f"unexpected-public-listener:{listener.port}:{listener.host}:"
                f"{_owner_label(listener)}"
            )

    for port in PUBLIC_HTTP_PORTS:
        if not any(listener.port == port for listener in public):
            violations.add(f"missing-public-nginx-listener:{port}")
    return violations


def validate_listeners(
    listeners: Iterable[Listener],
    *,
    expect_nginx_public_only: bool,
    expected_loopback_ports: Iterable[int],
) -> list[str]:
    """Return deterministic violation codes for the reviewed listener policy."""
    materialized = list(listeners)
    violations = _internal_boundary_violations(materialized)
    violations.update(
        _missing_loopback_violations(materialized, expected_loopback_ports)
    )

    if expect_nginx_public_only:
        violations.update(_public_listener_violations(materialized))

    return sorted(violations)


def collect_ss_output() -> str:
    result = subprocess.run(
        ["ss", "-H", "-ltnp"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise OSError("ss listener collection failed")
    return result.stdout


def _scope(host: str) -> str:
    if _is_loopback(host):
        return "loopback"
    if host in {"*", "0.0.0.0", "::"}:
        return "wildcard"
    return "nonloopback"


def _sanitized_listeners(listeners: Iterable[Listener]) -> list[dict[str, object]]:
    return [
        {
            "host": listener.host,
            "owners": list(listener.owners),
            "port": listener.port,
            "scope": _scope(listener.host),
        }
        for listener in sorted(
            listeners,
            key=lambda item: (item.port, item.host, item.owners),
        )
    ]


def _evidence_payload(
    *,
    verdict: str,
    expect_nginx_public_only: bool,
    expected_loopback_ports: Iterable[int],
    listeners: Iterable[Listener],
    violations: Iterable[str] = (),
    errors: Iterable[str] = (),
) -> dict[str, object]:
    return {
        "errors": sorted(set(errors)),
        "expect_nginx_public_only": expect_nginx_public_only,
        "expected_loopback_ports": sorted(set(expected_loopback_ports)),
        "listeners": _sanitized_listeners(listeners),
        "schema_version": 1,
        "verdict": verdict,
        "violations": sorted(set(violations)),
    }


def _write_evidence(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise OSError("refusing to replace a symlink evidence path")

    evidence = (
        json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    descriptor = -1
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary = Path(temporary_name)
        os.chmod(temporary, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(evidence)
            stream.flush()
            os.fsync(stream.fileno())

        if path.is_symlink():
            raise OSError("refusing to replace a symlink evidence path")
        os.replace(temporary, path)
        temporary = None
    finally:
        if descriptor != -1:
            os.close(descriptor)
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


def _write_requested_evidence(
    path: Path | None,
    payload: dict[str, object],
) -> bool:
    if path is None:
        return True
    try:
        _write_evidence(path, payload)
    except OSError:
        return False
    return True


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate production TCP listeners and write sanitized evidence."
    )
    parser.add_argument("--expect-nginx-public-only", action="store_true")
    parser.add_argument(
        "--expect-loopback",
        action="append",
        nargs="+",
        required=True,
        type=_port,
        metavar="PORT",
    )
    parser.add_argument("--evidence", type=Path)
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    collector: Callable[[], str] | None = None,
) -> int:
    args = _parser().parse_args(argv)
    expected_loopback_ports = [
        port for group in args.expect_loopback for port in group
    ]
    collect = collector or collect_ss_output

    try:
        listeners = parse_ss_output(collect())
    except Exception:  # noqa: BLE001 - CLI must sanitize every collection/parser failure.
        payload = _evidence_payload(
            verdict="error",
            expect_nginx_public_only=args.expect_nginx_public_only,
            expected_loopback_ports=expected_loopback_ports,
            listeners=(),
            errors=("socket-collection-failed",),
        )
        if not _write_requested_evidence(args.evidence, payload):
            return 2
        return 2

    violations = validate_listeners(
        listeners,
        expect_nginx_public_only=args.expect_nginx_public_only,
        expected_loopback_ports=expected_loopback_ports,
    )
    payload = _evidence_payload(
        verdict="fail" if violations else "pass",
        expect_nginx_public_only=args.expect_nginx_public_only,
        expected_loopback_ports=expected_loopback_ports,
        listeners=listeners,
        violations=violations,
    )
    if not _write_requested_evidence(args.evidence, payload):
        return 2

    if violations:
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
