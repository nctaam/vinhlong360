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

reset_mutable_evidence() {
  local root="$1"
  [ ! -L "$root" ] || return 1
  if [ -e "$root" ]; then
    [ -d "$root" ] || return 1
  else
    mkdir -p -- "$root" || return 1
  fi
  [ -d "$root" ] && [ ! -L "$root" ] || return 1
  rm -f -- \
    "$root/dependency-unit-checks.json" \
    "$root/install-summary.json" \
    "$root/install-recovery.json" \
    "$root/systemd-unit-cleanup.json" \
    "$root/install-lock.json" \
    "$root/findmnt-before.json" \
    "$root/findmnt-after.json" \
    "$root/findmnt-recovery.json" \
    "$root/persistent-before.json" \
    "$root/persistent-after.json" \
    "$root/persistent-recovery.json" \
    "$root/install-mutation-state.json" || return 1
  rm -rf -- \
    "$root/package" \
    "$root/staged" \
    "$root/installed" || return 1
}

normalize_evidence_candidate() {
  local candidate="$1"
  local local_rehearsal="$2"
  if [ "$local_rehearsal" = true ] && command -v cygpath >/dev/null 2>&1; then
    cygpath -u "$candidate"
  else
    printf '%s\n' "$candidate"
  fi
}

ATTEMPT_ID="$(python - <<'PY'
import secrets
print(secrets.token_hex(16))
PY
)"

process_start_identity() {
  local pid="$1"
  [ -r "/proc/$pid/stat" ] || return 1
  awk '{print $22}' "/proc/$pid/stat"
}

PROCESS_START_IDENTITY="$(process_start_identity "$$" 2>/dev/null || printf 'unknown-%s\n' "$$")"
HELD_LOCK_DIRS=()
HELD_LOCK_ROOTS=()
HELD_LOCK_KEYS=()
HELD_LOCK_KINDS=()
RECLAIMED_STALE_LOCKS=0
LOCKED_EVIDENCE_DIR=''
LOCK_EVIDENCE_ENABLED=false
LOCK_TERMINAL_RECORDED=false
PENDING_STALE_RECOVERY=false

lock_spec() {
  local kind="$1"
  local authority="$2"
  local lock_root
  lock_root="$(CDPATH= cd -- "$(dirname -- "$authority")" && pwd -P)/.vl360-install-locks"
  local key
  key="$(python - "$authority" <<'PY'
import hashlib
import os
import sys

authority = os.path.normcase(os.path.realpath(sys.argv[1]))
print(hashlib.sha256(authority.encode("utf-8")).hexdigest())
PY
)"
  printf '%s|%s|%s|%s\n' "$lock_root/authority-$key.lock" "$lock_root" "$key" "$kind"
}

write_lock_owner() {
  local lock_dir="$1"
  local temporary="$lock_dir/.owner.$ATTEMPT_ID.tmp"
  printf '{"attempt_id":"%s","pid":%s,"process_start_identity":"%s"}\n' \
    "$ATTEMPT_ID" "$$" "$PROCESS_START_IDENTITY" > "$temporary" || return 1
  mv -f -- "$temporary" "$lock_dir/owner.json"
}

lock_owner_is_live() {
  local lock_dir="$1"
  [ ! -e "$lock_dir/reclaimable" ] || return 1
  local owner
  owner="$(python - "$lock_dir/owner.json" <<'PY'
import json
from pathlib import Path
import re
import sys

try:
    raw = Path(sys.argv[1]).read_text(encoding="utf-8")
except FileNotFoundError:
    raise SystemExit(2)
try:
    payload = json.loads(raw)
    pid = int(payload["pid"])
    start = str(payload["process_start_identity"])
except json.JSONDecodeError:
    pid_match = re.search(r'"pid"\s*:\s*([0-9]+)', raw)
    start_match = re.search(
        r'"process_start_identity"\s*:\s*"([^"\\]*)"', raw
    )
    if pid_match is None or start_match is None:
        raise SystemExit(2)
    pid = int(pid_match.group(1))
    start = start_match.group(1)
except (KeyError, TypeError, ValueError):
    raise SystemExit(2)
print(f"{pid}\t{start}")
PY
)" || return 2
  local owner_pid owner_start
  IFS=$'\t' read -r owner_pid owner_start <<< "$owner"
  kill -0 "$owner_pid" 2>/dev/null || return 1
  local current_start
  current_start="$(process_start_identity "$owner_pid" 2>/dev/null)" || return 0
  [ "$current_start" = "$owner_start" ]
}

remove_lock_dir() {
  local lock_dir="$1"
  local retry
  for retry in 1 2 3 4 5; do
    rm -rf -- "$lock_dir" >/dev/null 2>&1 || true
    [ ! -e "$lock_dir" ] && [ ! -L "$lock_dir" ] && return 0
    sleep 0.05
  done
  return 1
}

mark_lock_reclaimable() {
  local lock_dir="$1"
  [ -d "$lock_dir" ] || return 0
  : > "$lock_dir/reclaimable" 2>/dev/null || true
}

lock_is_owned_by_attempt() {
  local lock_dir="$1"
  local actual expected
  [ -f "$lock_dir/owner.json" ] && [ ! -L "$lock_dir/owner.json" ] || return 1
  IFS= read -r actual < "$lock_dir/owner.json" || return 1
  printf -v expected '{"attempt_id":"%s","pid":%s,"process_start_identity":"%s"}' \
    "$ATTEMPT_ID" "$$" "$PROCESS_START_IDENTITY"
  [ "$actual" = "$expected" ]
}

release_owned_lock() {
  local lock_dir="$1"
  local released="$lock_dir.released.$ATTEMPT_ID"
  local retry
  for retry in 1 2 3 4 5; do
    lock_is_owned_by_attempt "$lock_dir" || return 1
    if mv -- "$lock_dir" "$released" 2>/dev/null; then
      remove_lock_dir "$released" || true
      return 0
    fi
    sleep 0.05
  done
  if lock_is_owned_by_attempt "$lock_dir"; then
    mark_lock_reclaimable "$lock_dir"
  fi
  return 1
}

publish_owned_lock() {
  local lock_dir="$1"
  local pending="$lock_dir.pending.$ATTEMPT_ID"
  mkdir -- "$pending" 2>/dev/null || return 11
  if ! write_lock_owner "$pending"; then
    remove_lock_dir "$pending" || true
    return 11
  fi
  if mv -T -n -- "$pending" "$lock_dir" 2>/dev/null \
    && [ ! -e "$pending" ] \
    && lock_is_owned_by_attempt "$lock_dir"; then
    return 0
  fi
  remove_lock_dir "$pending" || true
  [ -e "$lock_dir" ] || [ -L "$lock_dir" ] || return 11
  return 10
}

acquire_authority_lock() {
  local kind="$1"
  local authority="$2"
  local local_rehearsal="$3"
  local spec lock_dir lock_root lock_key lock_kind
  spec="$(lock_spec "$kind" "$authority" "$local_rehearsal")" || return 11
  IFS='|' read -r lock_dir lock_root lock_key lock_kind <<< "$spec"
  [ ! -L "$lock_root" ] || return 11
  if [ -e "$lock_root" ]; then
    [ -d "$lock_root" ] || return 11
  else
    mkdir -p -- "$lock_root" || return 11
  fi
  [ -d "$lock_root" ] && [ ! -L "$lock_root" ] || return 11

  local retry owner_state publish_state tombstone
  for retry in 1 2 3; do
    if publish_owned_lock "$lock_dir"; then
      HELD_LOCK_DIRS+=("$lock_dir")
      HELD_LOCK_ROOTS+=("$lock_root")
      HELD_LOCK_KEYS+=("$lock_key")
      HELD_LOCK_KINDS+=("$lock_kind")
      return 0
    else
      publish_state=$?
    fi
    [ "$publish_state" -eq 10 ] || return "$publish_state"
    [ -d "$lock_dir" ] || continue
    if lock_owner_is_live "$lock_dir"; then
      return 10
    else
      owner_state=$?
    fi
    case "$owner_state" in 1|2) ;; *) return 10 ;; esac
    tombstone="$lock_dir.stale.$ATTEMPT_ID"
    if mv -- "$lock_dir" "$tombstone" 2>/dev/null; then
      if publish_owned_lock "$lock_dir"; then
        rm -rf -- "$tombstone" >/dev/null 2>&1 || true
        RECLAIMED_STALE_LOCKS=$((RECLAIMED_STALE_LOCKS + 1))
        HELD_LOCK_DIRS+=("$lock_dir")
        HELD_LOCK_ROOTS+=("$lock_root")
        HELD_LOCK_KEYS+=("$lock_key")
        HELD_LOCK_KINDS+=("$lock_kind")
        return 0
      else
        publish_state=$?
      fi
      rm -rf -- "$tombstone" >/dev/null 2>&1 || true
      [ "$publish_state" -eq 10 ] || return "$publish_state"
    fi
  done
  return 10
}

release_all_install_locks() {
  local release_failed=false
  local evidence_lock=''
  local evidence_root=''
  local index lock_dir lock_root lock_kind
  for ((index = ${#HELD_LOCK_DIRS[@]} - 1; index >= 0; index--)); do
    lock_dir="${HELD_LOCK_DIRS[$index]}"
    lock_root="${HELD_LOCK_ROOTS[$index]}"
    lock_kind="${HELD_LOCK_KINDS[$index]}"
    if [ "$lock_kind" = evidence ]; then
      evidence_lock="$lock_dir"
      evidence_root="$lock_root"
      continue
    fi
    if release_owned_lock "$lock_dir"; then
      rmdir -- "$lock_root" >/dev/null 2>&1 || true
    else
      release_failed=true
    fi
  done
  if [ "$LOCK_EVIDENCE_ENABLED" = true ] && [ "$LOCK_TERMINAL_RECORDED" != true ]; then
    if [ "$release_failed" = true ]; then
      record_install_lock release-failed 1 || true
    else
      record_install_lock released 0 || true
    fi
  fi
  if [ -n "$evidence_lock" ]; then
    if release_owned_lock "$evidence_lock"; then
      rmdir -- "$evidence_root" >/dev/null 2>&1 || true
    else
      release_failed=true
      if [ "$LOCK_EVIDENCE_ENABLED" = true ] && [ "$LOCK_TERMINAL_RECORDED" != true ]; then
        record_install_lock release-failed 1 || true
      fi
    fi
  fi
  HELD_LOCK_DIRS=()
  HELD_LOCK_ROOTS=()
  HELD_LOCK_KEYS=()
  HELD_LOCK_KINDS=()
  [ "$release_failed" = false ]
}

cleanup_lock_trap() {
  release_all_install_locks || true
}

prepare_evidence_dir() {
  local root="$1"
  local local_rehearsal="$2"
  [ ! -L "$root" ] || die 'evidence-dir-symlink-forbidden'
  if [ -e "$root" ]; then
    [ -d "$root" ] || die 'evidence-dir-invalid'
  else
    mkdir -p -- "$root" || die 'evidence-dir-invalid'
  fi
  [ -d "$root" ] && [ ! -L "$root" ] || die 'evidence-dir-invalid'
  if [ -z "$LOCKED_EVIDENCE_DIR" ]; then
    if acquire_authority_lock evidence "$root" "$local_rehearsal"; then
      LOCKED_EVIDENCE_DIR="$root"
      trap cleanup_lock_trap EXIT
    else
      local lock_status=$?
      [ "$lock_status" -eq 10 ] && die 'install-evidence-locked'
      die 'install-lock-acquire-failed'
    fi
  fi
  [ "$LOCKED_EVIDENCE_DIR" = "$root" ] || die 'evidence-dir-lock-mismatch'
  if [ -e "$root/install-mutation-state.json" ] \
    || [ -L "$root/install-mutation-state.json" ]; then
    PENDING_STALE_RECOVERY=true
  else
    reset_mutable_evidence "$root" || die 'evidence-dir-reset-failed'
  fi
}

# Discover a valid evidence-dir token without allowing malformed options to
# abort the scan. The strict parser below remains authoritative for all inputs.
ORIGINAL_ARGS=("$@")
DISCOVERY_LOCAL_REHEARSAL=false
for discovery_arg in "${ORIGINAL_ARGS[@]}"; do
  [ "$discovery_arg" = '--local-rehearsal' ] && DISCOVERY_LOCAL_REHEARSAL=true
done
DISCOVERED_EVIDENCE_DIR=''
for ((discovery_index = 0; discovery_index < ${#ORIGINAL_ARGS[@]}; discovery_index++)); do
  [ "${ORIGINAL_ARGS[$discovery_index]}" = '--evidence-dir' ] || continue
  discovery_value_index=$((discovery_index + 1))
  ((discovery_value_index < ${#ORIGINAL_ARGS[@]})) || continue
  discovery_value="${ORIGINAL_ARGS[$discovery_value_index]}"
  case "$discovery_value" in
    ''|--*) continue ;;
    *) DISCOVERED_EVIDENCE_DIR="$discovery_value" ;;
  esac
done
if [ -n "$DISCOVERED_EVIDENCE_DIR" ]; then
  if DISCOVERED_EVIDENCE_DIR="$(
    normalize_evidence_candidate "$DISCOVERED_EVIDENCE_DIR" \
      "$DISCOVERY_LOCAL_REHEARSAL" 2>/dev/null
  )"; then
    if [ ! -L "$DISCOVERED_EVIDENCE_DIR" ]; then
      if [ ! -e "$DISCOVERED_EVIDENCE_DIR" ]; then
        mkdir -p -- "$DISCOVERED_EVIDENCE_DIR" 2>/dev/null || true
      fi
      if [ -d "$DISCOVERED_EVIDENCE_DIR" ] && [ ! -L "$DISCOVERED_EVIDENCE_DIR" ]; then
        if acquire_authority_lock evidence "$DISCOVERED_EVIDENCE_DIR" \
          "$DISCOVERY_LOCAL_REHEARSAL"; then
          LOCKED_EVIDENCE_DIR="$DISCOVERED_EVIDENCE_DIR"
          trap cleanup_lock_trap EXIT
          if [ -e "$DISCOVERED_EVIDENCE_DIR/install-mutation-state.json" ] \
            || [ -L "$DISCOVERED_EVIDENCE_DIR/install-mutation-state.json" ]; then
            PENDING_STALE_RECOVERY=true
          else
            reset_mutable_evidence "$DISCOVERED_EVIDENCE_DIR" 2>/dev/null || true
          fi
        else
          discovery_lock_status=$?
          [ "$discovery_lock_status" -ne 10 ] || die 'install-evidence-locked'
        fi
      fi
    fi
  fi
fi

require_option_value() {
  local option="$1"
  local argument_count="$2"
  local value="${3:-}"
  local error="${option#--}-value-required"
  ((argument_count >= 2)) && [ -n "$value" ] || die "$error"
  case "$value" in
    --*) die "$error" ;;
  esac
}

while (($#)); do
  case "$1" in
    --archive)
      require_option_value "$1" "$#" "${2:-}"
      ARCHIVE="$2"
      shift 2
      ;;
    --archive-digest-file)
      require_option_value "$1" "$#" "${2:-}"
      ARCHIVE_DIGEST_FILE="$2"
      shift 2
      ;;
    --release-root)
      require_option_value "$1" "$#" "${2:-}"
      RELEASE_ROOT="$2"
      shift 2
      ;;
    --persistent-agent-data-root)
      require_option_value "$1" "$#" "${2:-}"
      PERSISTENT_AGENT_DATA_ROOT="$2"
      shift 2
      ;;
    --environment-authority)
      require_option_value "$1" "$#" "${2:-}"
      ENVIRONMENT_AUTHORITY="$2"
      shift 2
      ;;
    --runtime-authority)
      require_option_value "$1" "$#" "${2:-}"
      RUNTIME_AUTHORITY="$2"
      shift 2
      ;;
    --mount-authority)
      require_option_value "$1" "$#" "${2:-}"
      MOUNT_AUTHORITY="$2"
      shift 2
      ;;
    --evidence-dir)
      require_option_value "$1" "$#" "${2:-}"
      EVIDENCE_DIR="$2"
      shift 2
      ;;
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
prepare_evidence_dir "$EVIDENCE_DIR" "$LOCAL_REHEARSAL"
[ -f "$ENVIRONMENT_AUTHORITY" ] && [ ! -L "$ENVIRONMENT_AUTHORITY" ] \
  || die 'external-environment-authority-required'
[ -d "$RUNTIME_AUTHORITY" ] && [ ! -L "$RUNTIME_AUTHORITY" ] \
  || die 'external-runtime-authority-required'
PINNED_ENVIRONMENT_AUTHORITY=''
for ((lock_index = 0; lock_index < ${#HELD_LOCK_DIRS[@]}; lock_index++)); do
  if [ "${HELD_LOCK_KINDS[$lock_index]}" = evidence ]; then
    PINNED_ENVIRONMENT_AUTHORITY="${HELD_LOCK_DIRS[$lock_index]}/env"
    break
  fi
done
[ -n "$PINNED_ENVIRONMENT_AUTHORITY" ] || die 'environment-authority-pin-failed'
if ENVIRONMENT_AUTHORITY_SHA256="$(python - "$ENVIRONMENT_AUTHORITY" \
  "$PINNED_ENVIRONMENT_AUTHORITY" <<'PY'
from dotenv.parser import parse_stream
from hashlib import sha256
from io import StringIO
import os
from pathlib import Path
import sys

forbidden = {"INDEXING_UNLOCK_KEY", "SITEMAP_UNLOCK_KEY"}
raw = Path(sys.argv[1]).read_bytes()
for binding in parse_stream(StringIO(raw.decode("utf-8"))):
    if not binding.error and binding.key in forbidden and binding.value not in (None, ""):
        raise SystemExit(3)
pinned = Path(sys.argv[2])
if pinned.parent.is_symlink() or not pinned.parent.is_dir():
    raise SystemExit(4)
with pinned.open("xb") as stream:
    stream.write(raw)
    stream.flush()
    os.fsync(stream.fileno())
os.chmod(pinned, 0o600)
if pinned.is_symlink() or pinned.read_bytes() != raw:
    raise SystemExit(4)
if os.name != "nt" and pinned.stat().st_mode & 0o077:
    raise SystemExit(4)
print(sha256(raw).hexdigest())
PY
  )"; then
  [ -n "$ENVIRONMENT_AUTHORITY_SHA256" ] || die 'environment-authority-pin-failed'
else
  environment_status=$?
  [ "$environment_status" -eq 3 ] || die 'environment-authority-pin-failed'
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
SNAPSHOT_BEFORE="$EVIDENCE_DIR/persistent-before.json"
SNAPSHOT_AFTER="$EVIDENCE_DIR/persistent-after.json"
SNAPSHOT_RECOVERY="$EVIDENCE_DIR/persistent-recovery.json"
MUTATION_STATE="$EVIDENCE_DIR/install-mutation-state.json"
STALE_RELEASE_ROOT=''
STALE_PERSISTENT_ROOT=''
STALE_RELEASE_KEY=''
STALE_PERSISTENT_KEY=''
STALE_STAGING_ROOT=''
STALE_OLD_ROOT=''
STALE_STAGE=''
STALE_PID=''
STALE_ATTEMPT_ID=''
STALE_LOCAL_REHEARSAL=''

write_mutation_state() {
  local stage="$1"
  local release_spec persistent_spec release_key persistent_key
  release_spec="$(lock_spec release "$RELEASE_ROOT" "$LOCAL_REHEARSAL")" || return 1
  persistent_spec="$(lock_spec persistent "$PERSISTENT_AGENT_DATA_ROOT" \
    "$LOCAL_REHEARSAL")" || return 1
  IFS='|' read -r _ _ release_key _ <<< "$release_spec"
  IFS='|' read -r _ _ persistent_key _ <<< "$persistent_spec"
  MSYS2_ENV_CONV_EXCL='VL360_STATE_RELEASE_ROOT;VL360_STATE_PERSISTENT_ROOT;VL360_STATE_STAGING_ROOT;VL360_STATE_OLD_ROOT' \
    VL360_STATE_RELEASE_ROOT="$RELEASE_ROOT" \
    VL360_STATE_PERSISTENT_ROOT="$PERSISTENT_AGENT_DATA_ROOT" \
    VL360_STATE_STAGING_ROOT="$STAGING_ROOT" \
    VL360_STATE_OLD_ROOT="$OLD_ROOT" \
    VL360_STATE_LOCAL_REHEARSAL="$LOCAL_REHEARSAL" \
    python - "$MUTATION_STATE" "$stage" "$ATTEMPT_ID" "$$" \
      "$release_key" "$persistent_key" <<'PY'
import json
import os
from pathlib import Path
import sys
import tempfile

path = Path(sys.argv[1])
payload = {
    "attempt_id": sys.argv[3],
    "local_rehearsal": os.environ["VL360_STATE_LOCAL_REHEARSAL"] == "true",
    "old_root": os.environ["VL360_STATE_OLD_ROOT"],
    "persistent_key_sha256": sys.argv[6],
    "persistent_root": os.environ["VL360_STATE_PERSISTENT_ROOT"],
    "pid": int(sys.argv[4]),
    "release_key_sha256": sys.argv[5],
    "release_root": os.environ["VL360_STATE_RELEASE_ROOT"],
    "schema_version": 2,
    "stage": sys.argv[2],
    "staging_root": os.environ["VL360_STATE_STAGING_ROOT"],
}
descriptor, name = tempfile.mkstemp(prefix=".install-mutation-state.", dir=path.parent)
temporary = Path(name)
try:
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        descriptor = -1
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
finally:
    if descriptor != -1:
        os.close(descriptor)
    temporary.unlink(missing_ok=True)
PY
}

clear_mutation_state() {
  rm -f -- "$MUTATION_STATE"
}

load_stale_install_state() {
  local state release_spec persistent_spec observed_release_key observed_persistent_key
  state="$(python - "$MUTATION_STATE" <<'PY'
import json
import posixpath
from pathlib import Path
import re
import sys

sha256_re = re.compile(r"^[0-9a-f]{64}$")
try:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if payload.get("schema_version") != 2:
        raise ValueError
    attempt_id = str(payload["attempt_id"])
    pid = int(payload["pid"])
    stage = str(payload["stage"])
    local_rehearsal = payload["local_rehearsal"]
    release_root = str(payload["release_root"])
    persistent_root = str(payload["persistent_root"])
    staging_root = str(payload["staging_root"])
    old_root = str(payload["old_root"])
    release_key = str(payload["release_key_sha256"])
    persistent_key = str(payload["persistent_key_sha256"])
    values = (release_root, persistent_root, staging_root, old_root)
    if (
        not attempt_id
        or pid <= 0
        or type(local_rehearsal) is not bool
        or any(not value.startswith("/") or any(c in value for c in "\t\n|") for value in values)
        or not sha256_re.fullmatch(release_key)
        or not sha256_re.fullmatch(persistent_key)
    ):
        raise ValueError
    release_parent = posixpath.dirname(release_root)
    release_name = posixpath.basename(release_root)
    if release_name in ("", ".", ".."):
        raise ValueError
    if staging_root != f"{release_parent}/.{release_name}.closed-stage.{pid}":
        raise ValueError
    if old_root != f"{release_parent}/.{release_name}.closed-old.{pid}":
        raise ValueError
except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
    raise SystemExit(1)
print(
    "\t".join(
        (
            stage,
            str(pid),
            attempt_id,
            "true" if local_rehearsal else "false",
            release_root,
            persistent_root,
            release_key,
            persistent_key,
            staging_root,
            old_root,
        )
    )
)
PY
  )" || return 1
  IFS=$'\t' read -r STALE_STAGE STALE_PID STALE_ATTEMPT_ID \
    STALE_LOCAL_REHEARSAL STALE_RELEASE_ROOT STALE_PERSISTENT_ROOT \
    STALE_RELEASE_KEY STALE_PERSISTENT_KEY STALE_STAGING_ROOT STALE_OLD_ROOT \
    <<< "$state"
  release_spec="$(lock_spec release "$STALE_RELEASE_ROOT" \
    "$STALE_LOCAL_REHEARSAL")" || return 1
  persistent_spec="$(lock_spec persistent "$STALE_PERSISTENT_ROOT" \
    "$STALE_LOCAL_REHEARSAL")" || return 1
  IFS='|' read -r _ _ observed_release_key _ <<< "$release_spec"
  IFS='|' read -r _ _ observed_persistent_key _ <<< "$persistent_spec"
  [ "$observed_release_key" = "$STALE_RELEASE_KEY" ] \
    && [ "$observed_persistent_key" = "$STALE_PERSISTENT_KEY" ]
}

tree_matches_snapshot() {
  local root="$1"
  local snapshot="$2"
  python - "$root" "$snapshot" <<'PY'
from hashlib import sha256
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
snapshot = Path(sys.argv[2])
if root.is_symlink() or not root.is_dir() or snapshot.is_symlink() or not snapshot.is_file():
    raise SystemExit(1)
expected = json.loads(snapshot.read_text(encoding="utf-8"))
observed = {}
for path in sorted(root.rglob("*")):
    if path.is_symlink():
        raise SystemExit(1)
    if path.is_file():
        raw = path.read_bytes()
        observed[path.relative_to(root).as_posix()] = {
            "sha256": sha256(raw).hexdigest(),
            "size": len(raw),
        }
raise SystemExit(0 if observed == expected else 1)
PY
}

write_stale_mutation_state() {
  local stage="$1"
  MSYS2_ENV_CONV_EXCL='VL360_STALE_RELEASE_ROOT;VL360_STALE_PERSISTENT_ROOT;VL360_STALE_STAGING_ROOT;VL360_STALE_OLD_ROOT' \
    VL360_STALE_RELEASE_ROOT="$STALE_RELEASE_ROOT" \
    VL360_STALE_PERSISTENT_ROOT="$STALE_PERSISTENT_ROOT" \
    VL360_STALE_STAGING_ROOT="$STALE_STAGING_ROOT" \
    VL360_STALE_OLD_ROOT="$STALE_OLD_ROOT" \
    python - "$MUTATION_STATE" "$stage" "$STALE_STAGE" \
      "$STALE_ATTEMPT_ID" "$STALE_PID" "$STALE_LOCAL_REHEARSAL" \
      "$STALE_RELEASE_KEY" "$STALE_PERSISTENT_KEY" <<'PY'
import json
import os
from pathlib import Path
import sys
import tempfile

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))
expected = {
    "attempt_id": sys.argv[4],
    "local_rehearsal": sys.argv[6] == "true",
    "old_root": os.environ["VL360_STALE_OLD_ROOT"],
    "persistent_key_sha256": sys.argv[8],
    "persistent_root": os.environ["VL360_STALE_PERSISTENT_ROOT"],
    "pid": int(sys.argv[5]),
    "release_key_sha256": sys.argv[7],
    "release_root": os.environ["VL360_STALE_RELEASE_ROOT"],
    "schema_version": 2,
    "stage": sys.argv[3],
    "staging_root": os.environ["VL360_STALE_STAGING_ROOT"],
}
if payload != expected:
    raise SystemExit(1)
payload["stage"] = sys.argv[2]
descriptor, name = tempfile.mkstemp(prefix=".install-mutation-state.", dir=path.parent)
temporary = Path(name)
try:
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        descriptor = -1
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
finally:
    if descriptor != -1:
        os.close(descriptor)
    temporary.unlink(missing_ok=True)
PY
  STALE_STAGE="$stage"
}

stale_tree_state() {
  local root="$1"
  [ ! -L "$root" ] || return 3
  [ -e "$root" ] || return 1
  [ -d "$root" ] || return 3
  tree_matches_snapshot "$root" "$SNAPSHOT_BEFORE" && return 0
  [ -z "$(find "$root" -mindepth 1 -print -quit)" ] && return 2
  return 3
}

inspect_stale_mount() {
  local target="$1"
  if "$MOUNT_AUTHORITY" findmnt --json --target "$target" \
    > "$EVIDENCE_DIR/findmnt-recovery.json"; then
    python - "$VERIFY_SCRIPT" "$EVIDENCE_DIR/findmnt-recovery.json" \
      "$STALE_PERSISTENT_ROOT" "$target" <<'PY'
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location("task5_verify_stale_mount", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
module.validate_findmnt_evidence(
    payload,
    expected_source=Path(sys.argv[3]),
    expected_target=Path(sys.argv[4]),
)
PY
    return $?
  else
    local status=$?
    [ "$status" -eq 1 ] && return 1
    return 2
  fi
}

reconcile_stale_install_attempt() {
  [ "$LOCAL_REHEARSAL" = "$STALE_LOCAL_REHEARSAL" ] \
    || return 1
  [ "$CURRENT_RELEASE_KEY" = "$STALE_RELEASE_KEY" ] \
    && [ "$CURRENT_PERSISTENT_KEY" = "$STALE_PERSISTENT_KEY" ] || return 1
  [ -f "$MUTATION_STATE" ] && [ ! -L "$MUTATION_STATE" ] || return 1
  local entry_stage="$STALE_STAGE"
  local stale_stage_owner="$STALE_STAGING_ROOT.owner"
  local current_data="$STALE_RELEASE_ROOT/agent/data"
  local current_state persistent_state mount_state
  local old_present=false release_present=false mount_verified=false
  case "$STALE_STAGE" in
    detach-agent-data-armed|persistent-detached|swap-release-root-armed|\
    root-swapped|persistent-restored|\
    recovery-remove-empty-persistent-root-armed|\
    recovery-detach-persistent-armed|recovery-remove-release-root-armed|\
    recovery-restore-old-root-armed|recovery-restore-persistent-armed|\
    recovery-create-persistent-root-armed|recovery-remove-staging-armed|\
    recovery-remove-staging-owner-armed) ;;
    *) return 1 ;;
  esac

  for candidate in "$STALE_RELEASE_ROOT" "$STALE_PERSISTENT_ROOT" \
    "$STALE_STAGING_ROOT" "$STALE_OLD_ROOT" "$stale_stage_owner"; do
    [ ! -L "$candidate" ] || return 1
  done
  if [ -e "$STALE_OLD_ROOT" ]; then
    [ -d "$STALE_OLD_ROOT" ] || return 1
    old_present=true
  fi
  if [ -e "$STALE_RELEASE_ROOT" ]; then
    [ -d "$STALE_RELEASE_ROOT" ] || return 1
    release_present=true
  fi
  if [ -e "$STALE_STAGING_ROOT" ]; then
    [ -d "$STALE_STAGING_ROOT" ] || return 1
  fi

  case "$entry_stage" in
    detach-agent-data-armed|persistent-detached)
      [ "$old_present" = false ] || return 1
      ;;
    root-swapped|persistent-restored|\
    recovery-remove-empty-persistent-root-armed|\
    recovery-detach-persistent-armed|recovery-remove-release-root-armed)
      [ "$old_present" = true ] || return 1
      ;;
    recovery-restore-persistent-armed|recovery-create-persistent-root-armed|\
    recovery-remove-staging-armed|recovery-remove-staging-owner-armed)
      [ "$old_present" = false ] || return 1
      ;;
  esac

  if [ "$old_present" = true ]; then
    if [ "$release_present" = true ] && [ -e "$STALE_STAGING_ROOT" ]; then
      return 1
    fi
    if [ "$release_present" = true ]; then
      if [ "$STALE_LOCAL_REHEARSAL" = true ]; then
        if stale_tree_state "$current_data"; then
          current_state=0
        else
          current_state=$?
        fi
        if stale_tree_state "$STALE_PERSISTENT_ROOT"; then
          persistent_state=0
        else
          persistent_state=$?
        fi
        case "$current_state:$persistent_state" in
          0:1|0:2)
            if [ "$persistent_state" -eq 2 ]; then
              write_stale_mutation_state \
                recovery-remove-empty-persistent-root-armed || return 1
              rmdir -- "$STALE_PERSISTENT_ROOT" || return 1
            fi
            write_stale_mutation_state recovery-detach-persistent-armed \
              || return 1
            mv -- "$current_data" "$STALE_PERSISTENT_ROOT" || return 1
            ;;
          1:0|2:0) ;;
          *) return 1 ;;
        esac
      else
        tree_matches_snapshot "$STALE_PERSISTENT_ROOT" "$SNAPSHOT_BEFORE" \
          || return 1
        if inspect_stale_mount "$current_data"; then
          mount_state=0
        else
          mount_state=$?
        fi
        case "$entry_stage:$mount_state" in
          persistent-restored:0|recovery-detach-persistent-armed:0)
            write_stale_mutation_state recovery-detach-persistent-armed \
              || return 1
            "$MOUNT_AUTHORITY" umount "$current_data" || return 1
            ;;
          recovery-detach-persistent-armed:1|root-swapped:1|\
          swap-release-root-armed:1|recovery-remove-release-root-armed:1) ;;
          *) return 1 ;;
        esac
      fi
      case "$entry_stage" in
        recovery-remove-release-root-armed) ;;
        *) [ -f "$STALE_RELEASE_ROOT/launch-release-manifest.json" ] \
          && [ ! -L "$STALE_RELEASE_ROOT/launch-release-manifest.json" ] \
          || return 1 ;;
      esac
      write_stale_mutation_state recovery-remove-release-root-armed || return 1
      rm -rf -- "$STALE_RELEASE_ROOT" || return 1
      release_present=false
    fi
    [ "$release_present" = false ] || return 1
    write_stale_mutation_state recovery-restore-old-root-armed || return 1
    mv -- "$STALE_OLD_ROOT" "$STALE_RELEASE_ROOT" || return 1
    old_present=false
    release_present=true
  fi

  [ "$release_present" = true ] \
    && [ -d "$STALE_RELEASE_ROOT" ] && [ ! -L "$STALE_RELEASE_ROOT" ] \
    && [ ! -e "$STALE_OLD_ROOT" ] && [ ! -L "$STALE_OLD_ROOT" ] || return 1
  current_data="$STALE_RELEASE_ROOT/agent/data"
  [ ! -L "$current_data" ] || return 1
  if [ "$STALE_LOCAL_REHEARSAL" = true ]; then
    if stale_tree_state "$current_data"; then
      current_state=0
    else
      current_state=$?
    fi
    if stale_tree_state "$STALE_PERSISTENT_ROOT"; then
      persistent_state=0
    else
      persistent_state=$?
    fi
    case "$current_state:$persistent_state" in
      0:1)
        write_stale_mutation_state recovery-create-persistent-root-armed \
          || return 1
        mkdir -- "$STALE_PERSISTENT_ROOT" || return 1
        ;;
      0:2) ;;
      1:0)
        [ -d "$(dirname -- "$current_data")" ] \
          && [ ! -L "$(dirname -- "$current_data")" ] || return 1
        write_stale_mutation_state recovery-restore-persistent-armed || return 1
        mv -- "$STALE_PERSISTENT_ROOT" "$current_data" || return 1
        write_stale_mutation_state recovery-create-persistent-root-armed \
          || return 1
        mkdir -- "$STALE_PERSISTENT_ROOT" || return 1
        ;;
      *) return 1 ;;
    esac
    tree_matches_snapshot "$current_data" "$SNAPSHOT_BEFORE" || return 1
    [ -d "$STALE_PERSISTENT_ROOT" ] \
      && [ ! -L "$STALE_PERSISTENT_ROOT" ] \
      && [ -z "$(find "$STALE_PERSISTENT_ROOT" -mindepth 1 -print -quit)" ] \
      || return 1
  else
    tree_matches_snapshot "$STALE_PERSISTENT_ROOT" "$SNAPSHOT_BEFORE" \
      || return 1
    if inspect_stale_mount "$current_data"; then
      mount_state=0
      mount_verified=true
    else
      mount_state=$?
    fi
    case "$mount_state" in
      0) ;;
      1)
        [ -d "$current_data" ] && [ ! -L "$current_data" ] \
          && [ -z "$(find "$current_data" -mindepth 1 -print -quit)" ] \
          || return 1
        write_stale_mutation_state recovery-restore-persistent-armed || return 1
        "$MOUNT_AUTHORITY" mount --bind "$STALE_PERSISTENT_ROOT" "$current_data" \
          || return 1
        inspect_stale_mount "$current_data" || return 1
        mount_verified=true
        ;;
      *) return 1 ;;
    esac
    [ "$mount_verified" = true ] || return 1
    tree_matches_snapshot "$current_data" "$SNAPSHOT_BEFORE" || return 1
  fi

  local stage_owner_valid=false
  if [ -e "$stale_stage_owner" ]; then
    [ -f "$stale_stage_owner" ] && [ ! -L "$stale_stage_owner" ] \
      && grep -Fxq "$STALE_ATTEMPT_ID" "$stale_stage_owner" || return 1
    stage_owner_valid=true
  fi
  if [ -e "$STALE_STAGING_ROOT" ] || [ -L "$STALE_STAGING_ROOT" ]; then
    [ -d "$STALE_STAGING_ROOT" ] && [ ! -L "$STALE_STAGING_ROOT" ] || return 1
    [ "$stage_owner_valid" = true ] || return 1
    write_stale_mutation_state recovery-remove-staging-armed || return 1
    rm -rf -- "$STALE_STAGING_ROOT" || return 1
  fi
  if [ -e "$stale_stage_owner" ] || [ -L "$stale_stage_owner" ]; then
    [ "$stage_owner_valid" = true ] || return 1
    write_stale_mutation_state recovery-remove-staging-owner-armed || return 1
    rm -f -- "$stale_stage_owner" || return 1
  fi
  clear_mutation_state
}

record_install_lock() {
  local status="$1"
  local code="$2"
  python - "$EVIDENCE_DIR/install-lock.json" "$status" "$code" \
    "$RECLAIMED_STALE_LOCKS" "${CONFLICT_LOCK_KEY:-}" "${HELD_LOCK_KEYS[@]}" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

keys = sys.argv[6:]
payload = {
    "authority_keys_sha256": keys,
    "conflict_key_sha256": sys.argv[5] or None,
    "exit_code": int(sys.argv[3]),
    "live_sla_proven": False,
    "observed_local_elapsed_seconds": 0.0,
    "reclaimed_stale_locks": int(sys.argv[4]),
    "schema_version": 1,
    "stage3_claim": False,
    "status": sys.argv[2],
    "target_key_sha256": hashlib.sha256("\0".join(sorted(keys)).encode("utf-8")).hexdigest(),
}
Path(sys.argv[1]).write_text(
    json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
PY
}

LOCK_EVIDENCE_ENABLED=true
if [ "$PENDING_STALE_RECOVERY" = true ] && ! load_stale_install_state; then
  record_install_lock recovery-required 2 || true
  LOCK_TERMINAL_RECORDED=true
  die 'stale-install-recovery-required'
fi
TARGET_LOCK_KEYS=()
declare -A TARGET_LOCK_AUTHORITIES=()
declare -A TARGET_LOCK_KINDS=()
add_target_lock_request() {
  local kind="$1"
  local authority="$2"
  local expected_key="${3:-}"
  local spec key existing_kind
  spec="$(lock_spec "$kind" "$authority" "$LOCAL_REHEARSAL")" || return 1
  IFS='|' read -r _ _ key _ <<< "$spec"
  [ -z "$expected_key" ] || [ "$key" = "$expected_key" ] || return 1
  if [ -n "${TARGET_LOCK_AUTHORITIES[$key]+x}" ]; then
    existing_kind="${TARGET_LOCK_KINDS[$key]}"
    if [ "$existing_kind" != "$kind" ]; then
      CONFLICT_LOCK_KEY="$key"
      return 12
    fi
    return 0
  fi
  TARGET_LOCK_KEYS+=("$key")
  TARGET_LOCK_AUTHORITIES["$key"]="$authority"
  TARGET_LOCK_KINDS["$key"]="$kind"
}
reject_authority_role_collision() {
  record_install_lock rejected 2 || true
  LOCK_TERMINAL_RECORDED=true
  die 'install-authority-role-collision'
}
CURRENT_RELEASE_KEY=''
CURRENT_PERSISTENT_KEY=''
for target_kind in release persistent systemd; do
  case "$target_kind" in
    release) target_authority="$RELEASE_ROOT" ;;
    persistent) target_authority="$PERSISTENT_AGENT_DATA_ROOT" ;;
    systemd) target_authority="$SYSTEMD_UNIT_DESTINATION" ;;
  esac
  target_spec="$(lock_spec "$target_kind" "$target_authority" "$LOCAL_REHEARSAL")"
  IFS='|' read -r _ _ target_key _ <<< "$target_spec"
  case "$target_kind" in
    release) CURRENT_RELEASE_KEY="$target_key" ;;
    persistent) CURRENT_PERSISTENT_KEY="$target_key" ;;
  esac
  if add_target_lock_request "$target_kind" "$target_authority" "$target_key"; then
    :
  else
    target_request_status=$?
    [ "$target_request_status" -ne 12 ] || reject_authority_role_collision
    die 'install-lock-acquire-failed'
  fi
done
if [ "$PENDING_STALE_RECOVERY" = true ]; then
  for target_kind in release persistent; do
    case "$target_kind" in
      release)
        target_authority="$STALE_RELEASE_ROOT"
        target_key="$STALE_RELEASE_KEY"
        ;;
      persistent)
        target_authority="$STALE_PERSISTENT_ROOT"
        target_key="$STALE_PERSISTENT_KEY"
        ;;
    esac
    if add_target_lock_request "$target_kind" "$target_authority" "$target_key"; then
      :
    else
      target_request_status=$?
      [ "$target_request_status" -ne 12 ] || reject_authority_role_collision
      record_install_lock recovery-required 2 || true
      LOCK_TERMINAL_RECORDED=true
      die 'stale-install-recovery-required'
    fi
  done
fi
mapfile -t TARGET_LOCK_KEYS < <(printf '%s\n' "${TARGET_LOCK_KEYS[@]}" | sort)
for target_key in "${TARGET_LOCK_KEYS[@]}"; do
  target_kind="${TARGET_LOCK_KINDS[$target_key]}"
  target_authority="${TARGET_LOCK_AUTHORITIES[$target_key]}"
  if acquire_authority_lock "$target_kind" "$target_authority" "$LOCAL_REHEARSAL"; then
    :
  else
    target_lock_status=$?
    CONFLICT_LOCK_KEY="$target_key"
    if [ "$target_lock_status" -eq 10 ]; then
      record_install_lock rejected 2
      LOCK_TERMINAL_RECORDED=true
      die 'install-target-locked'
    fi
    record_install_lock acquire-failed 2 || true
    LOCK_TERMINAL_RECORDED=true
    die 'install-lock-acquire-failed'
  fi
done
if [ "$PENDING_STALE_RECOVERY" = true ]; then
  if ! reconcile_stale_install_attempt; then
    record_install_lock recovery-required 2 || true
    LOCK_TERMINAL_RECORDED=true
    die 'stale-install-recovery-required'
  fi
  reset_mutable_evidence "$EVIDENCE_DIR" || die 'evidence-dir-reset-failed'
  PENDING_STALE_RECOVERY=false
fi
record_install_lock acquired 0

case "${VL360_INSTALL_FAIL_AFTER:-}" in
  ''|detach-agent-data|swap-release-root|restore-bind-agent-data) ;;
  *) die 'invalid-local-failure-injection' ;;
esac
[ "$LOCAL_REHEARSAL" = true ] || [ -z "${VL360_INSTALL_FAIL_AFTER:-}" ] \
  || die 'live-failure-injection-forbidden'

PINNED_ARCHIVE_ROOT=''
STAGING_ROOT=''
OLD_ROOT=''
STAGING_OWNER_MARKER=''
STAGING_CLEANUP_ARMED=false
cleanup_pinned_archive() {
  [ -n "$PINNED_ARCHIVE_ROOT" ] || return 0
  rm -rf -- "$PINNED_ARCHIVE_ROOT" >/dev/null 2>&1 || true
  PINNED_ARCHIVE_ROOT=''
}
cleanup_private_staging() {
  [ "$STAGING_CLEANUP_ARMED" = true ] || return 0
  local expected="$RELEASE_PARENT/.${RELEASE_NAME}.closed-stage.$$"
  [ "$STAGING_ROOT" = "$expected" ] || return 1
  [ "$STAGING_OWNER_MARKER" = "$STAGING_ROOT.owner" ] || return 1
  [ -f "$STAGING_OWNER_MARKER" ] && [ ! -L "$STAGING_OWNER_MARKER" ] \
    && grep -Fxq "$ATTEMPT_ID" "$STAGING_OWNER_MARKER" || return 1
  if [ -e "$STAGING_ROOT" ] || [ -L "$STAGING_ROOT" ]; then
    [ -d "$STAGING_ROOT" ] && [ ! -L "$STAGING_ROOT" ] || return 1
    rm -rf -- "$STAGING_ROOT" >/dev/null 2>&1 || return 1
  fi
  rm -f -- "$STAGING_OWNER_MARKER" >/dev/null 2>&1 || return 1
  STAGING_CLEANUP_ARMED=false
}
cleanup_attempt_authorities() {
  cleanup_private_staging || true
  cleanup_pinned_archive
  release_all_install_locks || true
}
trap cleanup_attempt_authorities EXIT

# Snapshot the candidate into a private authority, then verify and extract only
# those pinned bytes so replacing the caller-owned archive cannot win a TOCTOU race.
PINNED_ARCHIVE_ROOT="$(mktemp -d "$EVIDENCE_DIR/.closed-archive-attempt.XXXXXXXX")"
PINNED_ARCHIVE="$PINNED_ARCHIVE_ROOT/$(basename -- "$ARCHIVE")"
PINNED_ARCHIVE_DIGEST_FILE="$PINNED_ARCHIVE_ROOT/$(basename -- "$ARCHIVE_DIGEST_FILE")"
cp -- "$ARCHIVE" "$PINNED_ARCHIVE"
cp -- "$ARCHIVE_DIGEST_FILE" "$PINNED_ARCHIVE_DIGEST_FILE"
chmod 0600 -- "$PINNED_ARCHIVE" "$PINNED_ARCHIVE_DIGEST_FILE"

# Integrity and manifest verification must complete before extraction or mutation.
python "$VERIFY_SCRIPT" \
  --archive "$PINNED_ARCHIVE" --archive-digest-file "$PINNED_ARCHIVE_DIGEST_FILE" \
  --require-closed --evidence-dir "$EVIDENCE_DIR/package"

STAGING_ROOT="$RELEASE_PARENT/.${RELEASE_NAME}.closed-stage.$$"
OLD_ROOT="$RELEASE_PARENT/.${RELEASE_NAME}.closed-old.$$"
STAGING_OWNER_MARKER="$STAGING_ROOT.owner"
UNIT_ATTEMPT_ROOT=''
UNIT_BACKUP_ROOT=''
UNIT_MUTATION_MARKER=''
rm -f -- "$EVIDENCE_DIR/systemd-unit-mutation-armed"
rm -rf -- "$EVIDENCE_DIR/systemd-unit-backup"
for stale_attempt in "$EVIDENCE_DIR"/.systemd-unit-attempt.*; do
  [ -d "$stale_attempt" ] || continue
  [ -e "$stale_attempt/armed" ] || rm -rf -- "$stale_attempt"
done
[ ! -e "$STAGING_ROOT" ] && [ ! -L "$STAGING_ROOT" ] \
  && [ ! -e "$STAGING_OWNER_MARKER" ] && [ ! -L "$STAGING_OWNER_MARKER" ] \
  && [ ! -e "$OLD_ROOT" ] && [ ! -L "$OLD_ROOT" ] || die 'staging-path-exists'
STAGING_CLEANUP_ARMED=true
printf '%s\n' "$ATTEMPT_ID" > "$STAGING_OWNER_MARKER"
mkdir -- "$STAGING_ROOT"
python "$VERIFY_SCRIPT" \
  --archive "$PINNED_ARCHIVE" --archive-digest-file "$PINNED_ARCHIVE_DIGEST_FILE" \
  --require-closed --evidence-dir "$EVIDENCE_DIR/package"
tar -xzf "$PINNED_ARCHIVE" -C "$STAGING_ROOT" --no-same-owner --no-same-permissions
cleanup_pinned_archive
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
  python - "$PINNED_ENVIRONMENT_AUTHORITY" "$RELEASE_ROOT/.env" \
    "$ENVIRONMENT_AUTHORITY_SHA256" <<'PY'
from hashlib import sha256
import os
from pathlib import Path
import sys
import tempfile

pinned = Path(sys.argv[1])
target = Path(sys.argv[2])
expected_sha256 = sys.argv[3]
if pinned.is_symlink() or not pinned.is_file():
    raise SystemExit("pinned environment authority is not a real file")
if target.exists() or target.is_symlink():
    raise SystemExit("closed release unexpectedly contains environment material")
raw = pinned.read_bytes()
if sha256(raw).hexdigest() != expected_sha256:
    raise SystemExit("pinned environment authority digest mismatch")
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
      clear_mutation_state || true
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
  cleanup_attempt_authorities
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
write_mutation_state detach-agent-data-armed
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
write_mutation_state persistent-detached
fail_after detach-agent-data

# swap-release-root
write_mutation_state swap-release-root-armed
INSTALL_FAILURE_POINT=swap-release-root
[ -d "$RELEASE_ROOT" ] || die 'existing-release-root-required'
mv -- "$RELEASE_ROOT" "$OLD_ROOT"
OLD_ROOT_READY=true
mv -- "$STAGING_ROOT" "$RELEASE_ROOT"
rm -f -- "$STAGING_OWNER_MARKER"
STAGING_CLEANUP_ARMED=false
mkdir -p -- "$RELEASE_ROOT/agent"
rm -rf -- "$RELEASE_ROOT/agent/data"
write_mutation_state root-swapped
fail_after swap-release-root

INSTALL_FAILURE_POINT=materialize-environment-authority
materialize_environment_authority

# restore-bind-agent-data
INSTALL_FAILURE_POINT=restore-bind-agent-data
if [ "$LOCAL_REHEARSAL" = true ]; then
  mv -- "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent/data"
  PERSISTENT_ATTACHED_TO_RELEASE=true
  PERSISTENT_DETACHED=false
  write_mutation_state persistent-restored
  fail_after restore-bind-agent-data
  mkdir -- "$PERSISTENT_AGENT_DATA_ROOT"
else
  mkdir -- "$RELEASE_ROOT/agent/data"
  "$MOUNT_AUTHORITY" mount --bind "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent/data"
  PERSISTENT_ATTACHED_TO_RELEASE=true
  PERSISTENT_DETACHED=false
  write_mutation_state persistent-restored
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
  --environment-authority "$PINNED_ENVIRONMENT_AUTHORITY" \
  --verify-environment-authority \
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

INSTALL_FAILURE_POINT=remove-old-root
rm -rf -- "$OLD_ROOT"
OLD_ROOT_READY=false
INSTALL_COMPLETE=true
clear_mutation_state
if disarm_systemd_unit_attempt; then
  record_systemd_unit_cleanup passed 0
else
  cleanup_status=$?
  record_systemd_unit_cleanup failed "$cleanup_status" || true
fi
exit 0
