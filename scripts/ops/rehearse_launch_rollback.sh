#!/usr/bin/env bash
# Execute the reviewed local rehearsal or refuse an unacknowledged host run.
set -Eeuo pipefail
umask 077

MODE="${1:---local-rehearsal}"
[ "$#" -le 1 ] || { printf 'unexpected arguments\n' >&2; exit 64; }
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)"
KNOWN_GOOD_CLOSED="${KNOWN_GOOD_CLOSED:?known-good closed package is required}"
PERSISTENT_AGENT_DATA_ROOT="${PERSISTENT_AGENT_DATA_ROOT:?external persistent agent data root is required}"
EVIDENCE_DIR="${EVIDENCE_DIR:?evidence directory is required}"
OPERATOR="${OPERATOR:?operator identity is required}"
OPERATOR_CIDR="${OPERATOR_CIDR:?operator probe CIDR is required}"
CANDIDATE_RELEASE_ID="${CANDIDATE_RELEASE_ID:?candidate release id is required}"
ROLLBACK_RELEASE_ID="${ROLLBACK_RELEASE_ID:?rollback release id is required}"
ENVIRONMENT_AUTHORITY="${ENVIRONMENT_AUTHORITY:?external environment authority is required}"
RUNTIME_AUTHORITY="${RUNTIME_AUTHORITY:?external runtime authority is required}"
MOUNT_AUTHORITY="${MOUNT_AUTHORITY:-}"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STARTED_EPOCH="$(date +%s)"
CURRENT_PHASE=initialization
TRAFFIC_STATE=unknown
REOPEN_ATTEMPTED=false
RECOVERY_TRAP_ARMED=false
WATCHDOG_TIMER_WAS_ACTIVE=false
NO_LIVE_CLAIM_JSON='{"stage3_claim": false, "live_sla_proven": false, "observed_local_elapsed_seconds": 0}'

case "$MODE" in
  --local-rehearsal)
    RELEASE_ROOT="${LOCAL_RELEASE_ROOT:?local rehearsal root is required}"
    LOCAL_COMMAND_STATE="${LOCAL_COMMAND_STATE:-$EVIDENCE_DIR/local-command-state.json}"
    LOCAL_MAINTENANCE_DIR="${LOCAL_MAINTENANCE_DIR:-$EVIDENCE_DIR/local-maintenance}"
    ;;
  --execute-on-host)
    [ "${ACKNOWLEDGE_MAINTENANCE:-}" = "launch-safety-rollback" ] || exit 64
    RELEASE_ROOT="${RELEASE_ROOT:-/opt/vinhlong360}"
    [ -n "$MOUNT_AUTHORITY" ] || { printf 'live mount authority is required\n' >&2; exit 64; }
    [ -f "$ENVIRONMENT_AUTHORITY" ] || exit 64
    [ -d "$RUNTIME_AUTHORITY" ] || exit 64
    ;;
  *)
    exit 64
    ;;
esac

record_phase() {
  local status="$1"
  local code="${2:-0}"
  python "$SCRIPT_DIR/record_rollback_phase.py" \
    --evidence-dir "$EVIDENCE_DIR" --phase "$CURRENT_PHASE" --status "$status" \
    --exit-code "$code" --traffic-state "$TRAFFIC_STATE" --operator "$OPERATOR" \
    --candidate-id "$CANDIDATE_RELEASE_ID" --rollback-id "$ROLLBACK_RELEASE_ID"
}

record_recovery_result() {
  local name="$1"
  local status="$2"
  local code="${3:-0}"
  python "$SCRIPT_DIR/record_rollback_phase.py" \
    --evidence-dir "$EVIDENCE_DIR" --phase "recovery:$name" --status "$status" \
    --exit-code "$code" --traffic-state "$TRAFFIC_STATE" --operator "$OPERATOR" \
    --candidate-id "$CANDIDATE_RELEASE_ID" --rollback-id "$ROLLBACK_RELEASE_ID"
}

run_privileged() {
  if [ "$MODE" = "--local-rehearsal" ]; then
    python "$SCRIPT_DIR/local_command_stub.py" --state "$LOCAL_COMMAND_STATE" -- "$@"
  else
    "$@"
  fi
}

maintenance_select() {
  local action="$1"
  if [ "$MODE" = "--local-rehearsal" ]; then
    local maintenance_dir="$LOCAL_MAINTENANCE_DIR"
    command -v cygpath >/dev/null 2>&1 && maintenance_dir="$(cygpath -u "$maintenance_dir")"
    VL360_MAINTENANCE_SOURCE_DIR="$PROJECT_ROOT/ops/nginx/maintenance" \
      VL360_MAINTENANCE_DIR="$maintenance_dir" \
      VL360_NGINX_BIN=true \
      "$SCRIPT_DIR/maintenance_mode.sh" "$action" --operator-cidr "$OPERATOR_CIDR"
  else
    "$SCRIPT_DIR/maintenance_mode.sh" "$action" --operator-cidr "$OPERATOR_CIDR"
  fi
}

prepare_local_maintenance_model() {
  [ "$MODE" = "--local-rehearsal" ] || return 0
  mkdir -p -- "$LOCAL_MAINTENANCE_DIR"
  cp -- "$PROJECT_ROOT/ops/nginx/maintenance/http-context.conf.template" \
    "$LOCAL_MAINTENANCE_DIR/http-context.conf"
  cp -- "$PROJECT_ROOT/ops/nginx/maintenance/server-enabled.conf" \
    "$LOCAL_MAINTENANCE_DIR/server-enabled.conf"
  cp -- "$PROJECT_ROOT/ops/nginx/maintenance/server-disabled.conf" \
    "$LOCAL_MAINTENANCE_DIR/server-disabled.conf"
  rm -f -- "$LOCAL_MAINTENANCE_DIR/active-server.conf"
  python - "$LOCAL_MAINTENANCE_DIR/active-server.conf" <<'PY'
import os
import sys

os.symlink("server-disabled.conf", sys.argv[1])
PY
}

write_blocked_evidence() {
  local destination="$1"
  local reason="$2"
  python - "$destination" "$reason" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "live_sla_proven": False,
    "observed_local_elapsed_seconds": 0.0,
    "reason": sys.argv[2],
    "stage3_claim": False,
    "verdict": "blocked",
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

write_traffic_classification() {
  local state="$1"
  local reason="$2"
  local status_code="${3:-}"
  python - "$EVIDENCE_DIR/recovery/traffic-classification.json" \
    "$state" "$reason" "$status_code" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "live_sla_proven": False,
    "observations": {"public_status": int(sys.argv[4]) if sys.argv[4] else None},
    "reason": sys.argv[3],
    "schema_version": 1,
    "stage3_claim": False,
    "traffic_state": sys.argv[2],
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

install_closed_package() {
  local package="$1"
  local evidence="$2"
  local_args=()
  [ "$MODE" != "--local-rehearsal" ] || local_args+=(--local-rehearsal)
  "$SCRIPT_DIR/install_closed_release.sh" \
    --archive "$package" --archive-digest-file "$package.sha256" \
    --release-root "$RELEASE_ROOT" \
    --persistent-agent-data-root "$PERSISTENT_AGENT_DATA_ROOT" \
    --environment-authority "$ENVIRONMENT_AUTHORITY" \
    --runtime-authority "$RUNTIME_AUTHORITY" \
    --mount-authority "$MOUNT_AUTHORITY" \
    --require-closed --evidence-dir "$evidence/install" "${local_args[@]}"
}

verify_dependencies_units_daemon_reload() {
  python -m pip check
  python "$SCRIPT_DIR/verify_closed_release.py" \
    --installed-root "$RELEASE_ROOT" \
    --persistent-agent-data-root "$PERSISTENT_AGENT_DATA_ROOT" \
    --verify-config-ingress-unit-digests --verify-persistent-agent-data-mount \
    --require-closed --evidence-dir "$EVIDENCE_DIR/runtime-authority"
  run_privileged systemctl daemon-reload
  run_privileged systemctl start vl-nuxt
}

verify_readiness_and_listeners() {
  local evidence="$1"
  mkdir -p -- "$evidence"
  if ! curl --fail --silent --show-error --max-time 3 \
    http://127.0.0.1:3000/_internal/launch-readiness \
    > "$evidence/process-local-readiness.json"; then
    write_blocked_evidence "$evidence/process-local-readiness.json" "nuxt-3000-unavailable"
    return 2
  fi
  if [ "$MODE" = "--local-rehearsal" ]; then
    local ss_output
    ss_output="$(run_privileged ss -H -ltnp)"
    python - "$SCRIPT_DIR/socket_boundary_probe.py" "$evidence/listeners.json" "$ss_output" <<'PY'
import importlib.util
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location("task44_socket_probe", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
raise SystemExit(module.main(
    ["--expect-nginx-public-only", "--expect-loopback", "3000", "--evidence", sys.argv[2]],
    collector=lambda: sys.argv[3],
))
PY
  else
    python "$SCRIPT_DIR/socket_boundary_probe.py" \
      --expect-nginx-public-only --expect-loopback 3000 \
      --evidence "$evidence/listeners.json"
  fi
}

verify_nginx_closed_boundary() {
  local evidence="$1"
  if [ -z "${NGINX_PROBE_URL:-}" ]; then
    write_blocked_evidence "$evidence" "nginx-probe-url-unavailable"
    return 2
  fi
  VL360_LAUNCH_PUBLIC_URL="$NGINX_PROBE_URL" \
    python "$SCRIPT_DIR/probe_launch_boundary.py" \
      --expect maintenance --operator-source --maintenance-probe \
      --require-rich-html --require-thin-html --require-meta-robots \
      --require-no-sitemap --require-three-empty-sitemaps --require-no-store \
      --require-no-evidence --require-no-discovery --require-public-internal-404 \
      --require-direct-bypass-denied --evidence "$evidence"
}

verify_browser_worker_cache() {
  local evidence="$1"
  if [ -z "${NGINX_PROBE_URL:-}" ]; then
    write_blocked_evidence "$evidence" "browser-server-unavailable"
    return 2
  fi
  node "$PROJECT_ROOT/scripts/launch_safety_browser_e2e.mjs" \
    --base-url "$NGINX_PROBE_URL" --profile "$EVIDENCE_DIR/chrome-profile" \
    --install-legacy-worker-first --activate-current-worker \
    --assert-policy-cache-storage-empty --assert-offline-policy-replay-denied \
    --evidence "$evidence"
}

best_effort_recovery_step() {
  local name="$1"
  shift
  if [ "$RECOVERY_CHAIN_OK" != true ]; then
    case "$name" in
      verify-nginx-closed-boundary)
        write_blocked_evidence "$EVIDENCE_DIR/recovery/nginx-closed.json" "recovery-prerequisite-failed"
        ;;
      verify-browser-worker-cache)
        write_blocked_evidence "$EVIDENCE_DIR/recovery/browser.json" "recovery-prerequisite-failed"
        ;;
    esac
    record_recovery_result "$name" skipped 0 || true
    return 0
  fi
  if "$@"; then
    record_recovery_result "$name" passed 0 || true
  else
    local code=$?
    record_recovery_result "$name" failed "$code" || true
    RECOVERY_CHAIN_OK=false
  fi
  return 0
}

redrain_step() {
  local name="$1"
  shift
  if [ "$REDRAIN_OK" != true ]; then
    record_recovery_result "$name" skipped 0 || true
    return 0
  fi
  if "$@"; then
    record_recovery_result "$name" passed 0 || true
  else
    local code=$?
    record_recovery_result "$name" failed "$code" || true
    REDRAIN_OK=false
  fi
}

classify_incomplete_redrain() {
  # Task 43 has no traffic-classifier CLI, so classify only a clear upstream.
  local status_code=''
  if [ -n "${NGINX_PROBE_URL:-}" ]; then
    status_code="$(curl --silent --output /dev/null --write-out '%{http_code}' \
      --max-time 3 "$NGINX_PROBE_URL/" || true)"
  fi
  case "$status_code" in
    2??|3??|4??)
      if [ "$status_code" != 503 ]; then
        TRAFFIC_STATE=open
        write_traffic_classification open "recognized-normal-upstream" "$status_code"
        record_recovery_result classify-traffic-state passed 0 || true
        return 0
      fi
      ;;
  esac
  TRAFFIC_STATE=unknown
  write_traffic_classification unknown "incomplete-redrain-cannot-prove-traffic-state" "$status_code"
  record_recovery_result classify-traffic-state failed 2 || true
}

keep_maintenance_and_recover() {
  original_status="${1:-1}"
  trap - ERR
  set +e
  if [ "$REOPEN_ATTEMPTED" = true ]; then
    TRAFFIC_STATE=unknown
    REDRAIN_OK=true
    redrain_step maintenance-enable maintenance_select enable
    redrain_step nginx-test-closed run_privileged nginx -t
    redrain_step nginx-reload-closed run_privileged systemctl reload nginx
    redrain_step maintenance-probe verify_nginx_closed_boundary \
      "$EVIDENCE_DIR/recovery/redrain-maintenance.json"
    if [ "$REDRAIN_OK" = true ]; then
      TRAFFIC_STATE=drained
    else
      classify_incomplete_redrain
    fi
  fi

  record_phase failed "$original_status" || true
  RECOVERY_CHAIN_OK=false
  [ "$TRAFFIC_STATE" = drained ] && RECOVERY_CHAIN_OK=true
  recovery_package="$KNOWN_GOOD_CLOSED"
  recovery_action=known-good-closed-restore
  if [ -n "${CORRECTED_CLOSED_PACKAGE:-}" ]; then
    recovery_package="$CORRECTED_CLOSED_PACKAGE"
    recovery_action=corrected-closed-roll-forward
  fi

  best_effort_recovery_step verify-recovery-package \
    python "$SCRIPT_DIR/verify_closed_release.py" \
      --archive "$recovery_package" --archive-digest-file "$recovery_package.sha256" \
      --require-closed --evidence-dir "$EVIDENCE_DIR/recovery/package"
  best_effort_recovery_step install-closed-release \
    install_closed_package "$recovery_package" "$EVIDENCE_DIR/recovery"
  best_effort_recovery_step verify-dependencies-units-daemon-reload \
    verify_dependencies_units_daemon_reload
  best_effort_recovery_step verify-readiness-and-listeners \
    verify_readiness_and_listeners "$EVIDENCE_DIR/recovery"
  best_effort_recovery_step verify-nginx-closed-boundary \
    verify_nginx_closed_boundary "$EVIDENCE_DIR/recovery/nginx-closed.json"
  best_effort_recovery_step verify-browser-worker-cache \
    verify_browser_worker_cache "$EVIDENCE_DIR/recovery/browser.json"

  recovery_status=failed
  closed_verified=false
  if [ "$RECOVERY_CHAIN_OK" = true ]; then
    recovery_status=closed-verified
    closed_verified=true
  fi
  python "$SCRIPT_DIR/record_rollback_phase.py" \
    --evidence-dir "$EVIDENCE_DIR" --phase recovery --status "$recovery_status" \
    --exit-code "$original_status" --traffic-state "$TRAFFIC_STATE" --operator "$OPERATOR" \
    --candidate-id "$CANDIDATE_RELEASE_ID" --rollback-id "$ROLLBACK_RELEASE_ID" \
    --recovery-action "$recovery_action" --recovery-status "$recovery_status" \
    --closed-verified "$closed_verified" --old-open-restored false || true
  if [ "$WATCHDOG_TIMER_WAS_ACTIVE" = true ] && [ "$TRAFFIC_STATE" = drained ]; then
    run_privileged systemctl start vl-watchdog.timer || true
  fi
  exit "$original_status"
}

CURRENT_PHASE=record-and-verify-evidence
python "$SCRIPT_DIR/verify_closed_release.py" \
  --archive "$KNOWN_GOOD_CLOSED" --archive-digest-file "$KNOWN_GOOD_CLOSED.sha256" \
  --require-closed --operator "$OPERATOR" --candidate-id "$CANDIDATE_RELEASE_ID" \
  --rollback-id "$ROLLBACK_RELEASE_ID" --evidence-dir "$EVIDENCE_DIR/package"
record_phase passed

prepare_local_maintenance_model

CURRENT_PHASE=suspend-watchdog
if run_privileged systemctl is-active --quiet vl-watchdog.timer; then
  WATCHDOG_TIMER_WAS_ACTIVE=true
fi
run_privileged systemctl stop vl-watchdog.timer
run_privileged systemctl stop vl-watchdog.service
record_phase passed

CURRENT_PHASE=enable-maintenance
maintenance_select enable
run_privileged nginx -t
run_privileged systemctl reload nginx
write_blocked_evidence "$EVIDENCE_DIR/maintenance-http-proof.json" \
  "local-selector-proven-http-proof-requires-nginx-harness"
TRAFFIC_STATE=drained
record_phase passed
RECOVERY_TRAP_ARMED=true
trap 'keep_maintenance_and_recover "$?"' ERR

CURRENT_PHASE=stop-vl-nuxt
run_privileged systemctl stop vl-nuxt
record_phase passed

CURRENT_PHASE=purge-runtime-caches
python "$SCRIPT_DIR/purge_launch_runtime.py" \
  --release-root "$RELEASE_ROOT" \
  --readiness-manifest "$RELEASE_ROOT/web-nuxt/.output/server/launch-readiness-manifest.json" \
  --policy "$PROJECT_ROOT/ops/launch-safety/cache-purge-paths.json" \
  --evidence "$EVIDENCE_DIR/cache-purge.json"
record_phase passed

CURRENT_PHASE=install-known-good-closed
install_closed_package "$KNOWN_GOOD_CLOSED" "$EVIDENCE_DIR/primary"
record_phase passed

CURRENT_PHASE=verify-dependencies-units-daemon-reload
verify_dependencies_units_daemon_reload
record_phase passed

CURRENT_PHASE=verify-readiness-and-listeners
verify_readiness_and_listeners "$EVIDENCE_DIR/primary"
record_phase passed

CURRENT_PHASE=verify-nginx-closed-boundary
verify_nginx_closed_boundary "$EVIDENCE_DIR/primary/nginx-closed.json"
record_phase passed

CURRENT_PHASE=verify-browser-worker-cache
verify_browser_worker_cache "$EVIDENCE_DIR/primary/browser.json"
record_phase passed

CURRENT_PHASE=reopen-and-recover-watchdog
REOPEN_ATTEMPTED=true
TRAFFIC_STATE=unknown
maintenance_select disable
run_privileged nginx -t
run_privileged systemctl reload nginx
python "$SCRIPT_DIR/probe_launch_boundary.py" \
  --expect closed --require-public-post-reopen-matrix \
  --evidence "$EVIDENCE_DIR/post-reopen-closed.json"
TRAFFIC_STATE=open
if [ "$WATCHDOG_TIMER_WAS_ACTIVE" = true ]; then
  run_privileged systemctl start vl-watchdog.timer
fi
record_phase passed

trap - ERR
FINISHED_EPOCH="$(date +%s)"
python "$SCRIPT_DIR/record_rollback_phase.py" \
  --evidence-dir "$EVIDENCE_DIR" --phase complete --status passed \
  --traffic-state "$TRAFFIC_STATE" --operator "$OPERATOR" \
  --candidate-id "$CANDIDATE_RELEASE_ID" --rollback-id "$ROLLBACK_RELEASE_ID" \
  --observed-local-elapsed-seconds "$((FINISHED_EPOCH - STARTED_EPOCH))"
