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
LOCAL_REHEARSAL_SENTINEL="${VL360_LOCAL_REHEARSAL_SENTINEL:-}"

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
  [ -z "$LOCAL_REHEARSAL_SENTINEL" ] \
    || LOCAL_REHEARSAL_SENTINEL="$(cygpath -u "$LOCAL_REHEARSAL_SENTINEL")"
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
if [ "$LOCAL_REHEARSAL" = true ]; then
  PYTHON_DEPENDENCY_HOOK="${VL360_PYTHON_DEPENDENCY_HOOK:-$RUNTIME_AUTHORITY/install-python-dependencies}"
  NUXT_DEPENDENCY_HOOK="${VL360_NUXT_DEPENDENCY_HOOK:-$RUNTIME_AUTHORITY/install-nuxt-production-dependencies}"
  UNIT_VERIFY_HOOK="${VL360_UNIT_VERIFY_HOOK:-$RUNTIME_AUTHORITY/verify-systemd-units}"
  SYSTEMD_UNIT_DESTINATION="$RUNTIME_AUTHORITY/systemd-units"
else
  [ -z "${VL360_PYTHON_DEPENDENCY_HOOK+x}" ] \
    && [ -z "${VL360_NUXT_DEPENDENCY_HOOK+x}" ] \
    && [ -z "${VL360_UNIT_VERIFY_HOOK+x}" ] \
    || die 'live-hook-override-forbidden'
  PYTHON_DEPENDENCY_HOOK="$RUNTIME_AUTHORITY/install-python-dependencies"
  NUXT_DEPENDENCY_HOOK="$RUNTIME_AUTHORITY/install-nuxt-production-dependencies"
  UNIT_VERIFY_HOOK="$RUNTIME_AUTHORITY/verify-systemd-units"
  SYSTEMD_UNIT_DESTINATION=/etc/systemd/system
fi
for hook in "$PYTHON_DEPENDENCY_HOOK" "$NUXT_DEPENDENCY_HOOK" "$UNIT_VERIFY_HOOK"; do
  [ -f "$hook" ] && [ -x "$hook" ] && [ ! -L "$hook" ] \
    || die 'runtime-hook-authority-required'
done
case "${VL360_INSTALL_FAIL_AFTER:-}" in
  ''|detach-agent-data|swap-release-root|restore-bind-agent-data) ;;
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
if [ "$LOCAL_REHEARSAL" = true ]; then
  [ -n "$LOCAL_REHEARSAL_SENTINEL" ] \
    || die 'local-rehearsal-sentinel-required'
  [ -f "$LOCAL_REHEARSAL_SENTINEL" ] && [ ! -L "$LOCAL_REHEARSAL_SENTINEL" ] \
    || die 'local-rehearsal-sentinel-invalid'
  SENTINEL_PARENT="$(CDPATH= cd -- "$(dirname -- "$LOCAL_REHEARSAL_SENTINEL")" && pwd -P)"
  [ "$SENTINEL_PARENT" = "$RELEASE_PARENT" ] \
    || die 'local-rehearsal-sentinel-parent-mismatch'
  grep -Fxq 'vinhlong360-local-rehearsal-v1' "$LOCAL_REHEARSAL_SENTINEL" \
    || die 'local-rehearsal-sentinel-invalid'
fi
PERSISTENT_PARENT="$(CDPATH= cd -- "$(dirname -- "$PERSISTENT_AGENT_DATA_ROOT")" && pwd -P)"
PERSISTENT_NAME="$(basename -- "$PERSISTENT_AGENT_DATA_ROOT")"
case "$PERSISTENT_NAME" in ''|.|..) die 'unsafe-persistent-root' ;; esac
PERSISTENT_AGENT_DATA_ROOT="$PERSISTENT_PARENT/$PERSISTENT_NAME"
[ ! -L "$PERSISTENT_AGENT_DATA_ROOT" ] || die 'persistent-root-symlink-forbidden'

STAGING_ROOT="$RELEASE_PARENT/.${RELEASE_NAME}.closed-stage.$$"
OLD_ROOT="$RELEASE_PARENT/.${RELEASE_NAME}.closed-old.$$"
SNAPSHOT_BEFORE="$EVIDENCE_DIR/persistent-before.json"
SNAPSHOT_AFTER="$EVIDENCE_DIR/persistent-after.json"
SNAPSHOT_RECOVERY="$EVIDENCE_DIR/persistent-recovery.json"
UNIT_ATTEMPT_ROOT=''
UNIT_BACKUP_ROOT=''
UNIT_MUTATION_MARKER=''
mkdir -p -- "$EVIDENCE_DIR"
rm -f -- "$EVIDENCE_DIR/systemd-unit-mutation-armed"
rm -rf -- "$EVIDENCE_DIR/systemd-unit-backup"
for stale_attempt in "$EVIDENCE_DIR"/.systemd-unit-attempt.*; do
  [ -d "$stale_attempt" ] || continue
  [ -e "$stale_attempt/armed" ] || rm -rf -- "$stale_attempt"
done
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

record_systemd_unit_cleanup() {
  local status="$1"
  local code="$2"
  python - "$EVIDENCE_DIR/systemd-unit-cleanup.json" "$status" "$code" <<'PY'
import json
from pathlib import Path
import sys

payload = {
    "exit_code": int(sys.argv[3]),
    "live_sla_proven": False,
    "observed_local_elapsed_seconds": 0.0,
    "schema_version": 1,
    "stage3_claim": False,
    "status": sys.argv[2],
}
Path(sys.argv[1]).write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
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
PERSISTENT_ATTACHED_TO_RELEASE=true
OLD_ROOT_READY=false
INSTALL_COMPLETE=false
INSTALL_FAILURE_POINT=pre-mutation

write_recovery_evidence() {
  local status="$1"
  local root_restored="$2"
  local persistent_restored="$3"
  local systemd_units_restored="$4"
  python - "$EVIDENCE_DIR/install-recovery.json" "$status" \
    "$INSTALL_FAILURE_POINT" "$root_restored" "$persistent_restored" \
    "$systemd_units_restored" <<'PY'
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
    "systemd_units_restored": sys.argv[6] == "true",
}
Path(sys.argv[1]).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

materialize_environment_authority() {
  python - "$ENVIRONMENT_AUTHORITY" "$RELEASE_ROOT/.env" <<'PY'
import os
from pathlib import Path
import sys
import tempfile

authority = Path(sys.argv[1])
target = Path(sys.argv[2])
if authority.is_symlink() or not authority.is_file():
    raise SystemExit("environment authority is not a real file")
if target.exists() or target.is_symlink():
    raise SystemExit("closed release unexpectedly contains environment material")
raw = authority.read_bytes()
descriptor, name = tempfile.mkstemp(prefix=".env.", suffix=".tmp", dir=target.parent)
temporary = Path(name)
try:
    with os.fdopen(descriptor, "wb") as stream:
        descriptor = -1
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)
finally:
    if descriptor != -1:
        os.close(descriptor)
    temporary.unlink(missing_ok=True)
if target.is_symlink() or target.read_bytes() != raw:
    raise SystemExit("environment authority materialization verification failed")
if os.name != "nt" and target.stat().st_mode & 0o077:
    raise SystemExit("environment authority materialization permissions are too broad")
PY
}

prepare_systemd_unit_attempt() {
  [ -z "$UNIT_ATTEMPT_ROOT" ] || return 1
  UNIT_ATTEMPT_ROOT="$(mktemp -d "$EVIDENCE_DIR/.systemd-unit-attempt.XXXXXXXX")"
  UNIT_BACKUP_ROOT="$UNIT_ATTEMPT_ROOT/backup"
  UNIT_MUTATION_MARKER="$UNIT_ATTEMPT_ROOT/armed"
}

disarm_systemd_unit_attempt() {
  [ -n "$UNIT_ATTEMPT_ROOT" ] || return 0
  rm -f -- "$UNIT_MUTATION_MARKER" || true
  if rm -rf -- "$UNIT_ATTEMPT_ROOT"; then
    UNIT_ATTEMPT_ROOT=''
    UNIT_BACKUP_ROOT=''
    UNIT_MUTATION_MARKER=''
    return 0
  else
    return $?
  fi
}

install_systemd_units() {
  python - "$RELEASE_ROOT" "$SYSTEMD_UNIT_DESTINATION" "$UNIT_BACKUP_ROOT" "$UNIT_MUTATION_MARKER" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

UNIT_PATHS = (
    "ops/systemd/vl-agent.service",
    "ops/systemd/vl-nuxt.service",
    "ops/systemd/vl-bot.service",
    "ops/systemd/vl-watchdog.service",
    "ops/systemd/vl-watchdog.timer",
)

release = Path(sys.argv[1])
destination = Path(sys.argv[2])
backup = Path(sys.argv[3])
marker = Path(sys.argv[4])
manifest = json.loads((release / "launch-release-manifest.json").read_text(encoding="utf-8"))
declarations = manifest.get("members")
if not isinstance(declarations, dict):
    raise SystemExit("systemd unit manifest missing")
if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
    raise SystemExit("systemd unit destination is not a real directory")
destination.mkdir(parents=True, exist_ok=True)
backup.mkdir(parents=True, exist_ok=False)
metadata = {}
for relative in UNIT_PATHS:
    declaration = declarations.get(relative)
    source = release / relative
    target = destination / Path(relative).name
    if not isinstance(declaration, dict) or not source.is_file() or source.is_symlink():
        raise SystemExit(f"systemd unit source missing: {relative}")
    raw = source.read_bytes()
    if declaration.get("sha256") != hashlib.sha256(raw).hexdigest() or declaration.get("size") != len(raw):
        raise SystemExit(f"systemd unit source digest mismatch: {relative}")
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise SystemExit(f"systemd unit destination is unsafe: {target}")
    existed = target.exists()
    entry = {"existed": existed, "mode": target.stat().st_mode & 0o777 if existed else 0}
    if existed:
        backup_file = backup / target.name
        backup_file.write_bytes(target.read_bytes())
        entry["sha256"] = hashlib.sha256(backup_file.read_bytes()).hexdigest()
        entry["size"] = backup_file.stat().st_size
    metadata[target.name] = entry
(backup / "metadata.json").write_text(
    json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
marker.write_text("armed\n", encoding="ascii")
for relative in UNIT_PATHS:
    source = release / relative
    target = destination / Path(relative).name
    descriptor, name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=destination
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            raw = source.read_bytes()
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, target)
    finally:
        if descriptor != -1:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)
if os.name != "nt":
    descriptor = os.open(destination, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
PY
}

restore_systemd_units() {
  [ -n "$UNIT_MUTATION_MARKER" ] && [ -f "$UNIT_MUTATION_MARKER" ] || return 0
  python - "$SYSTEMD_UNIT_DESTINATION" "$UNIT_BACKUP_ROOT" <<'PY'
import json
import os
from pathlib import Path
import sys
import tempfile

destination = Path(sys.argv[1])
backup = Path(sys.argv[2])
metadata = json.loads((backup / "metadata.json").read_text(encoding="utf-8"))
for name, entry in metadata.items():
    target = destination / name
    if entry.get("existed") is True:
        raw = (backup / name).read_bytes()
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{name}.", suffix=".tmp", dir=destination
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, int(entry.get("mode", 0o644)))
            os.replace(temporary, target)
        finally:
            if descriptor != -1:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)
    elif target.exists() or target.is_symlink():
        target.unlink()
if os.name != "nt":
    descriptor = os.open(destination, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
PY
}

detach_persistent_from_release_for_recovery() {
  if [ "$LOCAL_REHEARSAL" = true ]; then
    if [ -e "$PERSISTENT_AGENT_DATA_ROOT" ] || [ -L "$PERSISTENT_AGENT_DATA_ROOT" ]; then
      [ -d "$PERSISTENT_AGENT_DATA_ROOT" ] && [ ! -L "$PERSISTENT_AGENT_DATA_ROOT" ] \
        || return 1
      [ -z "$(find "$PERSISTENT_AGENT_DATA_ROOT" -mindepth 1 -print -quit)" ] \
        || return 1
      rmdir -- "$PERSISTENT_AGENT_DATA_ROOT" || return $?
    fi
    mv -- "$RELEASE_ROOT/agent/data" "$PERSISTENT_AGENT_DATA_ROOT" || return $?
  else
    "$MOUNT_AUTHORITY" umount "$RELEASE_ROOT/agent/data" || return $?
  fi
  PERSISTENT_ATTACHED_TO_RELEASE=false
  PERSISTENT_DETACHED=true
}

attach_persistent_to_release_for_recovery() {
  local target="$RELEASE_ROOT/agent/data"
  mkdir -p -- "$RELEASE_ROOT/agent" || return $?
  if [ -e "$target" ] || [ -L "$target" ]; then
    [ -d "$target" ] && [ ! -L "$target" ] || return 1
    [ -z "$(find "$target" -mindepth 1 -print -quit)" ] || return 1
    rmdir -- "$target" || return $?
  fi
  if [ "$LOCAL_REHEARSAL" = true ]; then
    mv -- "$PERSISTENT_AGENT_DATA_ROOT" "$target" || return $?
    PERSISTENT_ATTACHED_TO_RELEASE=true
    PERSISTENT_DETACHED=false
    mkdir -- "$PERSISTENT_AGENT_DATA_ROOT" || return $?
  else
    mkdir -- "$target" || return $?
    "$MOUNT_AUTHORITY" mount --bind "$PERSISTENT_AGENT_DATA_ROOT" "$target" \
      || return $?
    PERSISTENT_ATTACHED_TO_RELEASE=true
    PERSISTENT_DETACHED=false
  fi
}

verify_recovered_persistent_state() {
  [ "$PERSISTENT_ATTACHED_TO_RELEASE" = true ] || return 1
  if [ "$LOCAL_REHEARSAL" = true ]; then
    [ -d "$PERSISTENT_AGENT_DATA_ROOT" ] && [ ! -L "$PERSISTENT_AGENT_DATA_ROOT" ] \
      || return 1
    [ -z "$(find "$PERSISTENT_AGENT_DATA_ROOT" -mindepth 1 -print -quit)" ] \
      || return 1
  else
    "$MOUNT_AUTHORITY" findmnt --json --target "$RELEASE_ROOT/agent/data" \
      > "$EVIDENCE_DIR/findmnt-recovery.json" || return $?
    verify_findmnt_file "$EVIDENCE_DIR/findmnt-recovery.json" \
      "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent/data" || return $?
  fi
  snapshot_tree "$RELEASE_ROOT/agent/data" "$SNAPSHOT_RECOVERY" || return $?
  cmp -s -- "$SNAPSHOT_BEFORE" "$SNAPSHOT_RECOVERY"
}

install_recovery() {
  local status=$?
  trap - EXIT ERR
  set +e
  local root_restored=true
  local persistent_restored=true
  local systemd_units_restored=true

  if [ "$INSTALL_COMPLETE" != true ] && [ "$MUTATION_STARTED" = true ]; then
    restore_systemd_units >/dev/null 2>&1 || systemd_units_restored=false

    if [ "$OLD_ROOT_READY" = true ] && [ "$PERSISTENT_ATTACHED_TO_RELEASE" = true ]; then
      detach_persistent_from_release_for_recovery >/dev/null 2>&1 \
        || persistent_restored=false
    fi

    if [ "$OLD_ROOT_READY" = true ]; then
      if [ "$PERSISTENT_ATTACHED_TO_RELEASE" = true ]; then
        root_restored=false
      else
        rm -rf -- "$RELEASE_ROOT" >/dev/null 2>&1 || root_restored=false
      fi
      if [ "$root_restored" = true ] && [ "$PERSISTENT_ATTACHED_TO_RELEASE" != true ]; then
        mv -- "$OLD_ROOT" "$RELEASE_ROOT" >/dev/null 2>&1 || root_restored=false
      fi
      if [ "$root_restored" = true ]; then
        OLD_ROOT_READY=false
      fi
    fi

    if [ "$root_restored" = true ] && [ "$PERSISTENT_DETACHED" = true ]; then
      attach_persistent_to_release_for_recovery >/dev/null 2>&1 \
        || persistent_restored=false
    fi

    if [ "$root_restored" = true ] && [ "$persistent_restored" = true ]; then
      verify_recovered_persistent_state >/dev/null 2>&1 \
        || persistent_restored=false
    fi

    if [ "$root_restored" = true ] \
      && [ "$persistent_restored" = true ] \
      && [ "$systemd_units_restored" = true ]; then
      write_recovery_evidence rolled-back true true true || true
    else
      write_recovery_evidence rollback-failed "$root_restored" \
        "$persistent_restored" "$systemd_units_restored" || true
    fi

    if [ -n "$UNIT_ATTEMPT_ROOT" ]; then
      rm -f -- "$UNIT_MUTATION_MARKER" >/dev/null 2>&1 || true
      if [ "$systemd_units_restored" = true ]; then
        rm -rf -- "$UNIT_ATTEMPT_ROOT" >/dev/null 2>&1 || true
      fi
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
PERSISTENT_ATTACHED_TO_RELEASE=false
fail_after detach-agent-data

# swap-release-root
INSTALL_FAILURE_POINT=swap-release-root
[ -d "$RELEASE_ROOT" ] || die 'existing-release-root-required'
mv -- "$RELEASE_ROOT" "$OLD_ROOT"
OLD_ROOT_READY=true
mv -- "$STAGING_ROOT" "$RELEASE_ROOT"
mkdir -p -- "$RELEASE_ROOT/agent"
rm -rf -- "$RELEASE_ROOT/agent/data"
fail_after swap-release-root

INSTALL_FAILURE_POINT=materialize-environment-authority
materialize_environment_authority

# restore-bind-agent-data
INSTALL_FAILURE_POINT=restore-bind-agent-data
if [ "$LOCAL_REHEARSAL" = true ]; then
  mv -- "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent/data"
  PERSISTENT_ATTACHED_TO_RELEASE=true
  PERSISTENT_DETACHED=false
  fail_after restore-bind-agent-data
  mkdir -- "$PERSISTENT_AGENT_DATA_ROOT"
else
  mkdir -- "$RELEASE_ROOT/agent/data"
  "$MOUNT_AUTHORITY" mount --bind "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent/data"
  PERSISTENT_ATTACHED_TO_RELEASE=true
  PERSISTENT_DETACHED=false
fi

# verify-agent-data-mount, including agent/data/sitemap-bundles byte evidence.
INSTALL_FAILURE_POINT=verify-agent-data-mount
if [ "$LOCAL_REHEARSAL" != true ]; then
  "$MOUNT_AUTHORITY" findmnt --json --target "$RELEASE_ROOT/agent/data" > "$EVIDENCE_DIR/findmnt-after.json"
  verify_findmnt_file "$EVIDENCE_DIR/findmnt-after.json" \
    "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent/data"
fi
snapshot_tree "$RELEASE_ROOT/agent/data" "$SNAPSHOT_AFTER"
cmp -s -- "$SNAPSHOT_BEFORE" "$SNAPSHOT_AFTER" || die 'persistent-agent-data-bytes-changed'

INSTALL_FAILURE_POINT=install-systemd-units
prepare_systemd_unit_attempt
install_systemd_units
run_authority_hook systemd-units "$UNIT_VERIFY_HOOK" \
  --unit-root "$SYSTEMD_UNIT_DESTINATION" \
  --manifest "$RELEASE_ROOT/launch-release-manifest.json"

VERIFY_MOUNT_ARGS=()
if [ "$LOCAL_REHEARSAL" = true ]; then
  VERIFY_MOUNT_ARGS+=(--local-rehearsal)
else
  VERIFY_MOUNT_ARGS+=(--persistent-mount-evidence "$EVIDENCE_DIR/findmnt-after.json")
fi
python "$VERIFY_SCRIPT" \
  --installed-root "$RELEASE_ROOT" --persistent-agent-data-root "$PERSISTENT_AGENT_DATA_ROOT" \
  --verify-config-ingress-unit-digests --verify-persistent-agent-data-mount \
  --systemd-unit-root "$SYSTEMD_UNIT_DESTINATION" --verify-systemd-unit-destination \
  --environment-authority "$ENVIRONMENT_AUTHORITY" --verify-environment-authority \
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
if disarm_systemd_unit_attempt; then
  record_systemd_unit_cleanup passed 0
else
  cleanup_status=$?
  record_systemd_unit_cleanup failed "$cleanup_status" || true
fi
exit 0
