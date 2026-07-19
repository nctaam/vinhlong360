#!/usr/bin/env bash
# Reusable fail-closed launch admission primitive.
#
# The caller must set OPERATOR_CIDR and READINESS_EVIDENCE.  RUNNER is an
# optional single executable used by tests; without it commands execute
# directly.  No function in this file disables maintenance except
# reopen_launch_admission.

set -euo pipefail

LAUNCH_ADMISSION_OPS_DIR="${LAUNCH_ADMISSION_OPS_DIR:-$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)}"
MAINTENANCE_MODE_SCRIPT="${MAINTENANCE_MODE_SCRIPT:-$LAUNCH_ADMISSION_OPS_DIR/maintenance_mode.sh}"
LAUNCH_BOUNDARY_PROBE="${LAUNCH_BOUNDARY_PROBE:-$LAUNCH_ADMISSION_OPS_DIR/probe_launch_boundary.py}"
SOCKET_BOUNDARY_PROBE="${SOCKET_BOUNDARY_PROBE:-$LAUNCH_ADMISSION_OPS_DIR/socket_boundary_probe.py}"
LAUNCH_READINESS_URL="${LAUNCH_READINESS_URL:-http://127.0.0.1:3000/_internal/launch-readiness}"
LAUNCH_READINESS_TIMEOUT_SECONDS="${LAUNCH_READINESS_TIMEOUT_SECONDS:-45}"
LAUNCH_PUBLIC_PROBE_TIMEOUT_SECONDS="${LAUNCH_PUBLIC_PROBE_TIMEOUT_SECONDS:-8}"
RUNNER="${RUNNER:-}"

_launch_validate_timeout() {
  case "$1" in
    ''|*[!0-9]*) return 1 ;;
  esac
  [ "$1" -ge 1 ] && [ "$1" -le 300 ]
}

_launch_run() {
  if [ -n "$RUNNER" ]; then
    "$RUNNER" "$@"
  else
    "$@"
  fi
}

_launch_require_inputs() {
  : "${OPERATOR_CIDR:?OPERATOR_CIDR is required for launch admission}"
  : "${READINESS_EVIDENCE:?READINESS_EVIDENCE is required for launch admission}"
  SOCKET_BOUNDARY_EVIDENCE="${SOCKET_BOUNDARY_EVIDENCE:-$(dirname "$READINESS_EVIDENCE")/socket-boundary.json}"
  PUBLIC_BOUNDARY_EVIDENCE="${PUBLIC_BOUNDARY_EVIDENCE:-$(dirname "$READINESS_EVIDENCE")/public-closed.json}"
  _launch_validate_timeout "$LAUNCH_READINESS_TIMEOUT_SECONDS" || {
    echo "launch readiness timeout is invalid" >&2
    return 2
  }
  _launch_validate_timeout "$LAUNCH_PUBLIC_PROBE_TIMEOUT_SECONDS" || {
    echo "launch public probe timeout is invalid" >&2
    return 2
  }
  [ -f "$MAINTENANCE_MODE_SCRIPT" ] || {
    echo "launch maintenance helper is unavailable" >&2
    return 2
  }
  [ -f "$LAUNCH_BOUNDARY_PROBE" ] || {
    echo "launch boundary probe is unavailable" >&2
    return 2
  }
  [ -f "$SOCKET_BOUNDARY_PROBE" ] || {
    echo "socket boundary probe is unavailable" >&2
    return 2
  }
}

_redrain_launch_admission() {
  _launch_run "$MAINTENANCE_MODE_SCRIPT" enable --operator-cidr "$OPERATOR_CIDR" || return 1
  _launch_run nginx -t || return 1
  _launch_reload_or_stop || return 1
}

_launch_stop_nginx_and_verify_inactive() {
  local stop_status=0
  local inactive_status=0

  if _launch_run systemctl stop nginx; then
    :
  else
    stop_status=$?
  fi
  if _launch_run systemctl is-inactive --quiet nginx; then
    :
  else
    inactive_status=$?
  fi

  if [ "$stop_status" -ne 0 ] || [ "$inactive_status" -ne 0 ]; then
    echo "nginx fail-safe stop/inactive verification failed" >&2
    return 1
  fi
  return 0
}

_launch_reload_or_stop() {
  local reload_status=0
  local recovery_status=0
  if _launch_run systemctl reload nginx; then
    return 0
  else
    reload_status=$?
  fi

  # A failed reload leaves the previous public selector in place. Stop Nginx
  # and prove it is inactive rather than risking an unverified public state.
  if ! _launch_stop_nginx_and_verify_inactive; then
    echo "nginx fail-safe stop/inactive verification failed after reload failure" >&2
    recovery_status=1
  fi
  [ "$recovery_status" -eq 0 ] || return 1
  return "$reload_status"
}

close_launch_admission() {
  _launch_require_inputs
  _launch_run "$MAINTENANCE_MODE_SCRIPT" enable --operator-cidr "$OPERATOR_CIDR"
  _launch_run nginx -t
  _launch_reload_or_stop
  # The deploy caller proves the real operator source after this remote shell
  # returns; a VPS-local request cannot establish that allowlist boundary.
}

verify_before_reopen() {
  _launch_require_inputs
  umask 077
  _launch_run curl --fail --silent --show-error \
    --connect-timeout 5 \
    --max-time "$LAUNCH_READINESS_TIMEOUT_SECONDS" \
    --retry 5 --retry-delay 1 --retry-connrefused \
    --output "$READINESS_EVIDENCE" \
    "$LAUNCH_READINESS_URL"
  _launch_run python "$SOCKET_BOUNDARY_PROBE" \
    --expect-nginx-public-only --expect-loopback 3000 \
    --evidence "$SOCKET_BOUNDARY_EVIDENCE"
}

reopen_launch_admission() {
  _launch_require_inputs
  verify_before_reopen

  # This is intentionally the only maintenance disable in the launch path.
  if ! _launch_run "$MAINTENANCE_MODE_SCRIPT" disable --operator-cidr "$OPERATOR_CIDR"; then
    if ! _redrain_launch_admission; then
      echo "reopen failed and redrain did not complete" >&2
      return 1
    fi
    return 1
  fi
  if ! _launch_run nginx -t || ! _launch_reload_or_stop; then
    if ! _redrain_launch_admission; then
      echo "reopen failed and redrain did not complete" >&2
      return 1
    fi
    return 1
  fi
  if _launch_run python "$LAUNCH_BOUNDARY_PROBE" \
    --expect closed --require-public-post-reopen-matrix \
    --timeout-seconds "$LAUNCH_PUBLIC_PROBE_TIMEOUT_SECONDS" \
    --evidence "${PUBLIC_BOUNDARY_EVIDENCE:-$(dirname "$READINESS_EVIDENCE")/public-closed.json}"; then
    :
  else
    if ! _redrain_launch_admission; then
      echo "post-reopen probe failed and redrain did not complete" >&2
      return 1
    fi
    return 1
  fi
}
