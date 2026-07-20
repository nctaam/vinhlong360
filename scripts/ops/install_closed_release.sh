#!/usr/bin/env bash
# Install one verified closed tree while preserving external agent/data bytes.
set -Eeuo pipefail
umask 077

die() {
  printf 'install_closed_release: %s\n' "$1" >&2
  exit 2
}

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
VERIFY_SCRIPT="$SCRIPT_DIR/verify_closed_release.py"
ARCHIVE=''
ARCHIVE_DIGEST_FILE=''
RELEASE_ROOT=''
PERSISTENT_AGENT_DATA_ROOT=''
ENVIRONMENT_AUTHORITY=''
RUNTIME_AUTHORITY=''
MOUNT_AUTHORITY=''
EVIDENCE_DIR=''
LOCAL_REHEARSAL=false
REQUIRE_CLOSED=false

while (($#)); do
  case "$1" in
    --archive) ARCHIVE="${2:-}"; shift 2 ;;
    --archive-digest-file) ARCHIVE_DIGEST_FILE="${2:-}"; shift 2 ;;
    --release-root) RELEASE_ROOT="${2:-}"; shift 2 ;;
    --persistent-agent-data-root) PERSISTENT_AGENT_DATA_ROOT="${2:-}"; shift 2 ;;
    --environment-authority) ENVIRONMENT_AUTHORITY="${2:-}"; shift 2 ;;
    --runtime-authority) RUNTIME_AUTHORITY="${2:-}"; shift 2 ;;
    --mount-authority) MOUNT_AUTHORITY="${2:-}"; shift 2 ;;
    --evidence-dir) EVIDENCE_DIR="${2:-}"; shift 2 ;;
    --require-closed) REQUIRE_CLOSED=true; shift ;;
    --local-rehearsal) LOCAL_REHEARSAL=true; shift ;;
    *) die 'unknown-option' ;;
  esac
done

[ -n "$ARCHIVE" ] || die 'archive-required'
[ -n "$ARCHIVE_DIGEST_FILE" ] || die 'archive-sidecar-required'
[ -n "$RELEASE_ROOT" ] || die 'release-root-required'
[ -n "$PERSISTENT_AGENT_DATA_ROOT" ] || die 'persistent-agent-data-root-required'
[ -n "$ENVIRONMENT_AUTHORITY" ] || die 'environment-authority-required'
[ -n "$RUNTIME_AUTHORITY" ] || die 'runtime-authority-required'
[ -n "$EVIDENCE_DIR" ] || die 'evidence-dir-required'
[ "$REQUIRE_CLOSED" = true ] || die 'require-closed-required'
if [ "$LOCAL_REHEARSAL" = true ] && command -v cygpath >/dev/null 2>&1; then
  ARCHIVE="$(cygpath -u "$ARCHIVE")"
  ARCHIVE_DIGEST_FILE="$(cygpath -u "$ARCHIVE_DIGEST_FILE")"
  RELEASE_ROOT="$(cygpath -u "$RELEASE_ROOT")"
  PERSISTENT_AGENT_DATA_ROOT="$(cygpath -u "$PERSISTENT_AGENT_DATA_ROOT")"
  ENVIRONMENT_AUTHORITY="$(cygpath -u "$ENVIRONMENT_AUTHORITY")"
  RUNTIME_AUTHORITY="$(cygpath -u "$RUNTIME_AUTHORITY")"
  EVIDENCE_DIR="$(cygpath -u "$EVIDENCE_DIR")"
fi
[ -f "$ENVIRONMENT_AUTHORITY" ] && [ ! -L "$ENVIRONMENT_AUTHORITY" ] \
  || die 'external-environment-authority-required'
[ -d "$RUNTIME_AUTHORITY" ] && [ ! -L "$RUNTIME_AUTHORITY" ] \
  || die 'external-runtime-authority-required'
if grep -Eq '^[[:space:]]*(INDEXING_UNLOCK_KEY|SITEMAP_UNLOCK_KEY)=' "$ENVIRONMENT_AUTHORITY"; then
  die 'unlock-keys-forbidden'
fi
if [ "$LOCAL_REHEARSAL" != true ]; then
  [ -n "$MOUNT_AUTHORITY" ] && [ -x "$MOUNT_AUTHORITY" ] \
    || die 'live-mount-authority-required'
fi
PYTHON_DEPENDENCY_HOOK="${VL360_PYTHON_DEPENDENCY_HOOK:-$RUNTIME_AUTHORITY/install-python-dependencies}"
NUXT_DEPENDENCY_HOOK="${VL360_NUXT_DEPENDENCY_HOOK:-$RUNTIME_AUTHORITY/install-nuxt-production-dependencies}"
UNIT_VERIFY_HOOK="${VL360_UNIT_VERIFY_HOOK:-$RUNTIME_AUTHORITY/verify-systemd-units}"
for hook in "$PYTHON_DEPENDENCY_HOOK" "$NUXT_DEPENDENCY_HOOK" "$UNIT_VERIFY_HOOK"; do
  [ -f "$hook" ] && [ -x "$hook" ] && [ ! -L "$hook" ] \
    || die 'runtime-hook-authority-required'
done
case "${VL360_INSTALL_FAIL_AFTER:-}" in
  ''|detach-agent-data|swap-release-root) ;;
  *) die 'invalid-local-failure-injection' ;;
esac
[ "$LOCAL_REHEARSAL" = true ] || [ -z "${VL360_INSTALL_FAIL_AFTER:-}" ] \
  || die 'live-failure-injection-forbidden'

# Integrity and manifest verification must complete before extraction or mutation.
python "$VERIFY_SCRIPT" \
  --archive "$ARCHIVE" --archive-digest-file "$ARCHIVE_DIGEST_FILE" \
  --require-closed --evidence-dir "$EVIDENCE_DIR/package"

RELEASE_PARENT="$(CDPATH= cd -- "$(dirname -- "$RELEASE_ROOT")" && pwd -P)"
RELEASE_NAME="$(basename -- "$RELEASE_ROOT")"
case "$RELEASE_NAME" in ''|.|..) die 'unsafe-release-root' ;; esac
RELEASE_ROOT="$RELEASE_PARENT/$RELEASE_NAME"
[ ! -L "$RELEASE_ROOT" ] || die 'release-root-symlink-forbidden'
PERSISTENT_PARENT="$(CDPATH= cd -- "$(dirname -- "$PERSISTENT_AGENT_DATA_ROOT")" && pwd -P)"
PERSISTENT_NAME="$(basename -- "$PERSISTENT_AGENT_DATA_ROOT")"
case "$PERSISTENT_NAME" in ''|.|..) die 'unsafe-persistent-root' ;; esac
PERSISTENT_AGENT_DATA_ROOT="$PERSISTENT_PARENT/$PERSISTENT_NAME"
[ ! -L "$PERSISTENT_AGENT_DATA_ROOT" ] || die 'persistent-root-symlink-forbidden'

STAGING_ROOT="$RELEASE_PARENT/.${RELEASE_NAME}.closed-stage.$$"
OLD_ROOT="$RELEASE_PARENT/.${RELEASE_NAME}.closed-old.$$"
SNAPSHOT_BEFORE="$EVIDENCE_DIR/persistent-before.json"
SNAPSHOT_AFTER="$EVIDENCE_DIR/persistent-after.json"
mkdir -p -- "$EVIDENCE_DIR"
[ ! -e "$STAGING_ROOT" ] && [ ! -e "$OLD_ROOT" ] || die 'staging-path-exists'
mkdir -- "$STAGING_ROOT"
tar -xzf "$ARCHIVE" -C "$STAGING_ROOT" --no-same-owner --no-same-permissions
[ -f "$STAGING_ROOT/launch-release-manifest.json" ] || die 'extracted-manifest-missing'

# Re-verify extracted activation-critical bytes before any dependency hook or mutation.
python "$VERIFY_SCRIPT" \
  --installed-root "$STAGING_ROOT" --verify-config-ingress-unit-digests \
  --require-closed --evidence-dir "$EVIDENCE_DIR/staged"

record_authority_result() {
  local name="$1"
  local status="$2"
  local code="$3"
  python - "$EVIDENCE_DIR/dependency-unit-checks.json" "$name" "$status" "$code" <<'PY'
import json
from pathlib import Path
import sys

path = Path(sys.argv[1])
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except FileNotFoundError:
    payload = {
        "live_sla_proven": False,
        "observed_local_elapsed_seconds": 0.0,
        "exit_codes": {},
        "results": {},
        "schema_version": 1,
        "stage3_claim": False,
    }
payload.setdefault("results", {})
payload.setdefault("exit_codes", {})
payload["results"][sys.argv[2]] = sys.argv[3]
payload["exit_codes"][sys.argv[2]] = int(sys.argv[4])
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

run_authority_hook() {
  local name="$1"
  shift
  if "$@"; then
    record_authority_result "$name" passed 0
    return 0
  else
    local code=$?
    record_authority_result "$name" failed "$code" || true
    return "$code"
  fi
}

run_authority_hook python-dependencies "$PYTHON_DEPENDENCY_HOOK" \
  --release-root "$STAGING_ROOT" --requirements "$STAGING_ROOT/requirements.txt"
run_authority_hook nuxt-production-dependencies "$NUXT_DEPENDENCY_HOOK" \
  --project-root "$STAGING_ROOT/web-nuxt" --production-only
run_authority_hook systemd-units "$UNIT_VERIFY_HOOK" \
  --unit-root "$STAGING_ROOT/ops/systemd" \
  --manifest "$STAGING_ROOT/launch-release-manifest.json"

snapshot_tree() {
  python - "$1" "$2" <<'PY'
from hashlib import sha256
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
result = {}
if root.exists():
    if root.is_symlink() or not root.is_dir():
        raise SystemExit(2)
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise SystemExit(2)
        if path.is_file():
            raw = path.read_bytes()
            result[path.relative_to(root).as_posix()] = {
                "sha256": sha256(raw).hexdigest(),
                "size": len(raw),
            }
Path(sys.argv[2]).write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
PY
}

MUTATION_STARTED=false
PERSISTENT_DETACHED=false
OLD_ROOT_READY=false
ROOT_SWAPPED=false
PERSISTENT_RESTORED=false
INSTALL_COMPLETE=false
INSTALL_FAILURE_POINT=pre-mutation

write_recovery_evidence() {
  local status="$1"
  local root_restored="$2"
  local persistent_restored="$3"
  python - "$EVIDENCE_DIR/install-recovery.json" "$status" \
    "$INSTALL_FAILURE_POINT" "$root_restored" "$persistent_restored" <<'PY'
import json
from pathlib import Path
import sys

payload = {
    "failure_point": sys.argv[3],
    "live_sla_proven": False,
    "observed_local_elapsed_seconds": 0.0,
    "persistent_restored": sys.argv[5] == "true",
    "root_restored": sys.argv[4] == "true",
    "schema_version": 1,
    "stage3_claim": False,
    "status": sys.argv[2],
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

install_recovery() {
  local status=$?
  trap - EXIT ERR
  set +e
  local root_restored=true
  local persistent_restored=true

  if [ "$INSTALL_COMPLETE" != true ] && [ "$MUTATION_STARTED" = true ]; then
    if [ "$PERSISTENT_RESTORED" = true ]; then
      if [ "$LOCAL_REHEARSAL" = true ]; then
        rmdir -- "$PERSISTENT_AGENT_DATA_ROOT" >/dev/null 2>&1 \
          && mv -- "$RELEASE_ROOT/agent/data" "$PERSISTENT_AGENT_DATA_ROOT" \
          || persistent_restored=false
      else
        "$MOUNT_AUTHORITY" umount "$RELEASE_ROOT/agent/data" >/dev/null 2>&1 \
          || persistent_restored=false
      fi
      PERSISTENT_RESTORED=false
    fi

    if [ "$OLD_ROOT_READY" = true ]; then
      rm -rf -- "$RELEASE_ROOT" >/dev/null 2>&1 || root_restored=false
      if [ "$root_restored" = true ]; then
        mv -- "$OLD_ROOT" "$RELEASE_ROOT" >/dev/null 2>&1 || root_restored=false
      fi
      ROOT_SWAPPED=false
      OLD_ROOT_READY=false
    fi

    if [ "$PERSISTENT_DETACHED" = true ]; then
      rm -rf -- "$RELEASE_ROOT/agent/data" >/dev/null 2>&1 || persistent_restored=false
      mkdir -p -- "$RELEASE_ROOT/agent" >/dev/null 2>&1 || persistent_restored=false
      if [ "$LOCAL_REHEARSAL" = true ]; then
        if [ "$persistent_restored" = true ]; then
          mv -- "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent/data" \
            >/dev/null 2>&1 || persistent_restored=false
        fi
        mkdir -p -- "$PERSISTENT_AGENT_DATA_ROOT" >/dev/null 2>&1 \
          || persistent_restored=false
      else
        mkdir -p -- "$RELEASE_ROOT/agent/data" >/dev/null 2>&1 \
          || persistent_restored=false
        if [ "$persistent_restored" = true ]; then
          "$MOUNT_AUTHORITY" mount --bind "$PERSISTENT_AGENT_DATA_ROOT" \
            "$RELEASE_ROOT/agent/data" >/dev/null 2>&1 || persistent_restored=false
        fi
      fi
      PERSISTENT_DETACHED=false
    fi
    if [ "$root_restored" = true ] && [ "$persistent_restored" = true ]; then
      write_recovery_evidence rolled-back true true || true
    else
      write_recovery_evidence rollback-failed "$root_restored" "$persistent_restored" || true
    fi
  fi

  rm -rf -- "$STAGING_ROOT" >/dev/null 2>&1 || true
  if [ "$INSTALL_COMPLETE" = true ]; then
    rm -rf -- "$OLD_ROOT" >/dev/null 2>&1 || true
  fi
  exit "$status"
}
trap install_recovery EXIT

fail_after() {
  local point="$1"
  if [ "$LOCAL_REHEARSAL" = true ] && [ "${VL360_INSTALL_FAIL_AFTER:-}" = "$point" ]; then
    INSTALL_FAILURE_POINT="$point"
    return 73
  fi
}

verify_findmnt_file() {
  local evidence="$1"
  local source="$2"
  local target="$3"
  python - "$VERIFY_SCRIPT" "$evidence" "$source" "$target" <<'PY'
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location("task5_verify_mount", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
module.validate_findmnt_evidence(
    payload,
    expected_source=Path(sys.argv[3]),
    expected_target=Path(sys.argv[4]),
)
PY
}

CURRENT_DATA="$RELEASE_ROOT/agent/data"
if [ -e "$CURRENT_DATA" ] || [ -L "$CURRENT_DATA" ]; then
  [ -d "$CURRENT_DATA" ] && [ ! -L "$CURRENT_DATA" ] || die 'agent-data-symlink-forbidden'
  snapshot_tree "$CURRENT_DATA" "$SNAPSHOT_BEFORE"
else
  mkdir -p -- "$(dirname -- "$CURRENT_DATA")"
  mkdir -- "$CURRENT_DATA"
  snapshot_tree "$CURRENT_DATA" "$SNAPSHOT_BEFORE"
fi

# detach-agent-data
MUTATION_STARTED=true
INSTALL_FAILURE_POINT=detach-agent-data
if [ "$LOCAL_REHEARSAL" = true ]; then
  if [ -d "$PERSISTENT_AGENT_DATA_ROOT" ]; then
    [ -z "$(find "$PERSISTENT_AGENT_DATA_ROOT" -mindepth 1 -print -quit)" ] \
      || die 'local-persistent-authority-not-empty'
    rmdir -- "$PERSISTENT_AGENT_DATA_ROOT"
  fi
  mv -- "$CURRENT_DATA" "$PERSISTENT_AGENT_DATA_ROOT"
else
  "$MOUNT_AUTHORITY" findmnt --json --target "$CURRENT_DATA" > "$EVIDENCE_DIR/findmnt-before.json"
  verify_findmnt_file "$EVIDENCE_DIR/findmnt-before.json" \
    "$PERSISTENT_AGENT_DATA_ROOT" "$CURRENT_DATA"
  "$MOUNT_AUTHORITY" umount "$CURRENT_DATA"
fi
PERSISTENT_DETACHED=true
fail_after detach-agent-data

# swap-release-root
INSTALL_FAILURE_POINT=swap-release-root
[ -d "$RELEASE_ROOT" ] || die 'existing-release-root-required'
mv -- "$RELEASE_ROOT" "$OLD_ROOT"
OLD_ROOT_READY=true
mv -- "$STAGING_ROOT" "$RELEASE_ROOT"
ROOT_SWAPPED=true
mkdir -p -- "$RELEASE_ROOT/agent"
rm -rf -- "$RELEASE_ROOT/agent/data"
fail_after swap-release-root

# restore-bind-agent-data
if [ "$LOCAL_REHEARSAL" = true ]; then
  mv -- "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent/data"
  mkdir -- "$PERSISTENT_AGENT_DATA_ROOT"
else
  mkdir -- "$RELEASE_ROOT/agent/data"
  "$MOUNT_AUTHORITY" mount --bind "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent/data"
fi
PERSISTENT_RESTORED=true

# verify-agent-data-mount, including agent/data/sitemap-bundles byte evidence.
if [ "$LOCAL_REHEARSAL" != true ]; then
  "$MOUNT_AUTHORITY" findmnt --json --target "$RELEASE_ROOT/agent/data" > "$EVIDENCE_DIR/findmnt-after.json"
  verify_findmnt_file "$EVIDENCE_DIR/findmnt-after.json" \
    "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent/data"
fi
snapshot_tree "$RELEASE_ROOT/agent/data" "$SNAPSHOT_AFTER"
cmp -s -- "$SNAPSHOT_BEFORE" "$SNAPSHOT_AFTER" || die 'persistent-agent-data-bytes-changed'

VERIFY_MOUNT_ARGS=()
if [ "$LOCAL_REHEARSAL" = true ]; then
  VERIFY_MOUNT_ARGS+=(--local-rehearsal)
else
  VERIFY_MOUNT_ARGS+=(--persistent-mount-evidence "$EVIDENCE_DIR/findmnt-after.json")
fi
python "$VERIFY_SCRIPT" \
  --installed-root "$RELEASE_ROOT" --persistent-agent-data-root "$PERSISTENT_AGENT_DATA_ROOT" \
  --verify-config-ingress-unit-digests --verify-persistent-agent-data-mount \
  "${VERIFY_MOUNT_ARGS[@]}" \
  --require-closed --evidence-dir "$EVIDENCE_DIR/installed"

python - "$EVIDENCE_DIR/install-summary.json" <<'PY'
import json
from pathlib import Path
import sys

payload = {
    "closed_verified": True,
    "live_sla_proven": False,
    "observed_local_elapsed_seconds": 0.0,
    "persistent_events": [
        "detach-agent-data",
        "swap-release-root",
        "restore-bind-agent-data",
        "verify-agent-data-mount",
    ],
    "stage3_claim": False,
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

INSTALL_COMPLETE=true
exit 0
