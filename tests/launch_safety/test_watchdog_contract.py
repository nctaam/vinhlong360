from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WATCHDOG = ROOT / "scripts" / "ops" / "watchdog.sh"
SERVICE = ROOT / "ops" / "systemd" / "vl-watchdog.service"
TIMER = ROOT / "ops" / "systemd" / "vl-watchdog.timer"


def test_watchdog_checks_maintenance_before_probes_and_before_restart():
    source = WATCHDOG.read_text(encoding="utf-8")

    guard_calls = []
    offset = 0
    for line in source.splitlines(keepends=True):
        if line.strip() == "guard_against_maintenance":
            guard_calls.append(offset)
        offset += len(line)
    first_probe = source.index("curl ")
    first_restart = source.index("systemctl restart")

    assert len(guard_calls) == 2
    assert guard_calls[0] < first_probe < guard_calls[1] < first_restart


def test_watchdog_guard_is_fail_closed_for_enabled_or_unknown_selector():
    source = WATCHDOG.read_text(encoding="utf-8")

    assert "server-enabled.conf" in source
    assert "server-disabled.conf" in source
    assert "maintenance guard is unknown" in source
    assert "maintenance is active" in source


def test_watchdog_paths_are_overridable_for_unprivileged_contract_tests():
    source = WATCHDOG.read_text(encoding="utf-8")

    assert "VL360_MAINTENANCE_SELECTOR" in source
    assert "VL360_WATCHDOG_LOG" in source
    assert "VL360_WATCHDOG_STAMP" in source


def test_watchdog_systemd_units_pin_the_guard_and_explicit_timer_unit():
    service = SERVICE.read_text(encoding="utf-8")
    timer = TIMER.read_text(encoding="utf-8")

    assert (
        "Environment=VL360_MAINTENANCE_SELECTOR="
        "/etc/nginx/vl360-maintenance/active-server.conf"
    ) in service
    assert "ExecStart=/bin/bash /opt/vinhlong360/scripts/ops/watchdog.sh" in service
    assert "Unit=vl-watchdog.service" in timer
    assert "Persistent=false" in timer
