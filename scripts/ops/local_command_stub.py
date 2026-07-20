#!/usr/bin/env python3
"""Model only unavailable privileged host commands for local rehearsal."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Sequence


ALLOWED_COMMANDS = {
    ("nginx", "-t"),
    ("ss", "-H", "-ltnp"),
    ("vl360-dependencies",),
    ("vl360-maintenance", "enable"),
    ("vl360-maintenance", "disable"),
    ("vl360-maintenance-probe",),
    ("vl360-readiness",),
    ("systemctl", "daemon-reload"),
    ("systemctl", "is-active", "--quiet", "vl-watchdog.timer"),
    ("systemctl", "stop", "vl-watchdog.timer"),
    ("systemctl", "start", "vl-watchdog.timer"),
    ("systemctl", "stop", "vl-watchdog.service"),
    ("systemctl", "start", "vl-watchdog.service"),
    ("systemctl", "stop", "vl-nuxt"),
    ("systemctl", "start", "vl-nuxt"),
    ("systemctl", "reload", "nginx"),
    ("systemctl", "restart", "vl-agent"),
    ("systemctl", "restart", "vl-nuxt"),
}
VARIABLE_COMMANDS = {"findmnt", "mount", "umount"}


def _default_state() -> dict[str, Any]:
    return {
        "commands": [],
        "failures": {},
        "mounts": {},
        "ss_output": (
            'LISTEN 0 511 0.0.0.0:80 0.0.0.0:* users:(("nginx",pid=1,fd=1))\n'
            'LISTEN 0 511 [::]:443 [::]:* users:(("nginx",pid=1,fd=2))\n'
            'LISTEN 0 128 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=2,fd=3))\n'
            'LISTEN 0 2048 127.0.0.1:3000 0.0.0.0:* users:(("node",pid=3,fd=4))\n'
        ),
        "maintenance": False,
        "dependency_status": "passed",
        "services": {
            "nginx": "active",
            "vl-nuxt": "active",
            "vl-watchdog.service": "inactive",
            "vl-watchdog.timer": "active",
        },
    }


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _default_state()
    if path.is_symlink() or not path.is_file():
        raise ValueError("local command state must be a real file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("local command state must be an object")
    base = _default_state()
    base.update(value)
    return base


def _save(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(state, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if descriptor != -1:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _validate(argv: tuple[str, ...]) -> None:
    if argv in ALLOWED_COMMANDS:
        return
    if not argv or argv[0] not in VARIABLE_COMMANDS:
        raise ValueError(f"local command is not allowlisted: {argv!r}")
    if argv[0] == "findmnt" and len(argv) == 4 and argv[1:3] == ("--json", "--target"):
        return
    if argv[0] == "mount" and len(argv) == 4 and argv[1] == "--bind":
        return
    if argv[0] == "umount" and len(argv) == 2:
        return
    raise ValueError(f"local command arguments are not allowlisted: {argv!r}")


def _configured_failure(state: dict[str, Any], rendered: str) -> int | None:
    configured = state.get("failures", {}).get(rendered, 0)
    if type(configured) is int and configured != 0:
        return configured
    return None


def _handle_systemctl(command: tuple[str, ...], state: dict[str, Any]) -> int | None:
    services = state.setdefault("services", {})
    if command[:2] == ("systemctl", "is-active"):
        return 0 if services.get(command[-1]) == "active" else 3
    if command[:2] in {("systemctl", "start"), ("systemctl", "restart")}:
        services[command[-1]] = "active"
        if command[-1] == "vl-nuxt":
            _set_nuxt_listener(state, active=True)
        return 0
    if command[:2] == ("systemctl", "stop"):
        services[command[-1]] = "inactive"
        if command[-1] == "vl-nuxt":
            _set_nuxt_listener(state, active=False)
        return 0
    if command == ("systemctl", "reload", "nginx"):
        return 0 if services.get("nginx") == "active" else 1
    return None


def _set_nuxt_listener(state: dict[str, Any], *, active: bool) -> None:
    """Keep the loopback listener model coupled to the Nuxt service state."""
    lines = [
        line
        for line in str(state.get("ss_output", "")).splitlines()
        if ":3000 " not in line
    ]
    if active:
        lines.append(
            'LISTEN 0 2048 127.0.0.1:3000 0.0.0.0:* users:(("node",pid=3,fd=4))'
        )
    state["ss_output"] = "\n".join(lines) + ("\n" if lines else "")


def _handle_local_authority(command: tuple[str, ...], state: dict[str, Any]) -> int | None:
    if command == ("vl360-dependencies",):
        print(json.dumps({"dependency_check": state.get("dependency_status", "passed")}))
        return 0 if state.get("dependency_status", "passed") == "passed" else 1
    if command in {
        ("vl360-maintenance", "enable"),
        ("vl360-maintenance", "disable"),
    }:
        state["maintenance"] = command[-1] == "enable"
        return 0
    if command == ("vl360-readiness",):
        if state.get("services", {}).get("vl-nuxt") != "active":
            return 7
        payload = {
            "checks": [
                {"name": "manifest-schema", "ok": True},
                {"name": "artifact-evidence", "ok": True},
                {"name": "compiled-cache-rules", "ok": True},
                {"name": "public-prerender", "ok": True},
                {"name": "service-worker-cache-purge", "ok": True},
            ],
            "live_sla_proven": False,
            "ok": True,
            "stage3_claim": False,
            "state": "closed",
        }
        print(json.dumps(payload, sort_keys=True))
        return 0
    if command == ("vl360-maintenance-probe",):
        maintenance = bool(state.get("maintenance"))
        nginx_active = state.get("services", {}).get("nginx") == "active"
        payload = {
            "operator": {"contract_passed": maintenance and nginx_active},
            "public": {"status": 503 if maintenance and nginx_active else 200},
            "traffic_state": "drained" if maintenance and nginx_active else "unknown",
        }
        print(json.dumps(payload, sort_keys=True))
        return 0 if payload["operator"]["contract_passed"] and payload["public"]["status"] == 503 else 1
    return None


def _handle_mount_command(command: tuple[str, ...], state: dict[str, Any]) -> int | None:
    mounts = state.setdefault("mounts", {})
    if command[0] == "mount":
        mounts[str(Path(command[3]).resolve())] = str(Path(command[2]).resolve())
        return 0
    if command[0] == "umount":
        mounts.pop(str(Path(command[1]).resolve()), None)
        return 0
    if command[0] == "findmnt":
        target = str(Path(command[3]).resolve())
        source = mounts.get(target)
        if source is None:
            return 1
        print(json.dumps({"filesystems": [{"source": source, "target": target, "options": "rw,bind"}]}))
        return 0
    return None


def _execute_command(command: tuple[str, ...], state: dict[str, Any]) -> int:
    if command == ("ss", "-H", "-ltnp"):
        print(state.get("ss_output", ""), end="")
        return 0
    systemctl_result = _handle_systemctl(command, state)
    if systemctl_result is not None:
        return systemctl_result
    local_authority_result = _handle_local_authority(command, state)
    if local_authority_result is not None:
        return local_authority_result
    mount_result = _handle_mount_command(command, state)
    if mount_result is not None:
        return mount_result
    return 0


def run_stub(state_path: Path, argv: Sequence[str]) -> int:
    command = tuple(argv)
    _validate(command)
    state = _load(state_path)
    rendered = " ".join(command)
    state.setdefault("commands", []).append(rendered)
    configured = _configured_failure(state, rendered)
    if configured is not None:
        _save(state_path, state)
        return configured
    result = _execute_command(command, state)
    _save(state_path, state)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command[:1] == ["--"]:
        args.command = args.command[1:]
    if not args.command:
        print("local command is required", file=os.sys.stderr)
        return 64
    try:
        return run_stub(args.state, args.command)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"local command refused: {exc}", file=os.sys.stderr)
        return 64


if __name__ == "__main__":
    raise SystemExit(main())
