#!/usr/bin/env bash
# Install one verified closed tree while preserving external agent/data bytes.
set -Eeuo pipefail
umask 077

EARLY_ARGUMENTS=("$@")
EARLY_ARGUMENTS_VALID=true
EARLY_LOCAL_REHEARSAL=false
EARLY_ARCHIVE_PRESENT=false
EARLY_ARCHIVE_DIGEST_PRESENT=false
EARLY_RELEASE_ROOT_PRESENT=false
EARLY_RELEASE_ROOT_VALUE=''
EARLY_PERSISTENT_ROOT_PRESENT=false
EARLY_ENVIRONMENT_AUTHORITY_PRESENT=false
EARLY_MIGRATION_GATE_EVIDENCE_PRESENT=false
EARLY_RUNTIME_AUTHORITY_PRESENT=false
EARLY_EVIDENCE_DIR_PRESENT=false
EARLY_REQUIRE_CLOSED=false
early_index=0
while ((early_index < ${#EARLY_ARGUMENTS[@]})); do
  early_argument="${EARLY_ARGUMENTS[$early_index]}"
  case "$early_argument" in
    --archive|--archive-digest-file|--release-root|--persistent-agent-data-root|\
    --environment-authority|--runtime-authority|--mount-authority|--evidence-dir|\
    --migration-gate-evidence)
      early_value_index=$((early_index + 1))
      if ((early_value_index >= ${#EARLY_ARGUMENTS[@]})); then
        EARLY_ARGUMENTS_VALID=false
        break
      fi
      early_value="${EARLY_ARGUMENTS[$early_value_index]}"
      case "$early_value" in
        ''|--*) EARLY_ARGUMENTS_VALID=false; break ;;
      esac
      case "$early_argument" in
        --archive) EARLY_ARCHIVE_PRESENT=true ;;
        --archive-digest-file) EARLY_ARCHIVE_DIGEST_PRESENT=true ;;
        --release-root)
          EARLY_RELEASE_ROOT_PRESENT=true
          EARLY_RELEASE_ROOT_VALUE="$early_value"
          ;;
        --persistent-agent-data-root) EARLY_PERSISTENT_ROOT_PRESENT=true ;;
        --environment-authority) EARLY_ENVIRONMENT_AUTHORITY_PRESENT=true ;;
        --migration-gate-evidence) EARLY_MIGRATION_GATE_EVIDENCE_PRESENT=true ;;
        --runtime-authority) EARLY_RUNTIME_AUTHORITY_PRESENT=true ;;
        --evidence-dir) EARLY_EVIDENCE_DIR_PRESENT=true ;;
      esac
      early_index=$((early_index + 2))
      ;;
    --require-closed)
      EARLY_REQUIRE_CLOSED=true
      early_index=$((early_index + 1))
      ;;
    --local-rehearsal)
      EARLY_LOCAL_REHEARSAL=true
      early_index=$((early_index + 1))
      ;;
    *)
      EARLY_ARGUMENTS_VALID=false
      break
      ;;
  esac
done
EARLY_REQUIRED_ARGUMENTS_VALID=false
if [ "$EARLY_ARGUMENTS_VALID" = true ] \
  && [ "$EARLY_ARCHIVE_PRESENT" = true ] \
  && [ "$EARLY_ARCHIVE_DIGEST_PRESENT" = true ] \
  && [ "$EARLY_RELEASE_ROOT_PRESENT" = true ] \
  && [ "$EARLY_PERSISTENT_ROOT_PRESENT" = true ] \
  && [ "$EARLY_ENVIRONMENT_AUTHORITY_PRESENT" = true ] \
  && [ "$EARLY_RUNTIME_AUTHORITY_PRESENT" = true ] \
  && [ "$EARLY_EVIDENCE_DIR_PRESENT" = true ] \
  && [ "$EARLY_REQUIRE_CLOSED" = true ]; then
  EARLY_REQUIRED_ARGUMENTS_VALID=true
fi

canonical_executable_path() {
  local candidate="$1"
  local canonical
  [ -n "$candidate" ] || return 1
  case "$candidate" in
    /*) ;;
    *) return 1 ;;
  esac
  canonical="$(/usr/bin/readlink -f -- "$candidate")" || return 1
  if [ -x /usr/bin/cygpath ]; then
    canonical="$(/usr/bin/cygpath -u \
      "$(/usr/bin/cygpath -w -- "$canonical")")" || return 1
  fi
  case "$canonical" in
    /*) ;;
    *) return 1 ;;
  esac
  [ -f "$canonical" ] && [ ! -L "$canonical" ] && [ -x "$canonical" ] \
    || return 1
  [ "$(/usr/bin/readlink -f -- "$canonical")" = "$canonical" ] || return 1
  printf '%s\n' "$canonical"
}

if [ "$EARLY_REQUIRED_ARGUMENTS_VALID" = true ] \
  && [ -n "${VL360_PYTHON_EXECUTOR:-}" ] \
  && [ -n "${VL360_LOCAL_PYTHON_EXECUTOR:-}" ]; then
  printf 'install_closed_release: python-executor-authority-conflict\n' >&2
  exit 2
fi

if [ -n "${VL360_PYTHON_EXECUTOR:-}" ] \
  && [ "$EARLY_REQUIRED_ARGUMENTS_VALID" = true ]; then
  PYTHON_EXECUTOR_CANDIDATE="$VL360_PYTHON_EXECUTOR"
elif [ -n "${VL360_LOCAL_PYTHON_EXECUTOR:-}" ] \
  && [ "$EARLY_REQUIRED_ARGUMENTS_VALID" = true ]; then
  [ "$EARLY_LOCAL_REHEARSAL" = true ] || {
    printf 'install_closed_release: local-python-executor-live-forbidden\n' >&2
    exit 2
  }
  PYTHON_EXECUTOR_CANDIDATE="$VL360_LOCAL_PYTHON_EXECUTOR"
  [ "$(/usr/bin/readlink -f -- "$PYTHON_EXECUTOR_CANDIDATE" 2>/dev/null)" \
    = "$PYTHON_EXECUTOR_CANDIDATE" ] || {
    printf 'install_closed_release: python-executor-authority-required\n' >&2
    exit 2
  }
else
  if [ "$EARLY_REQUIRED_ARGUMENTS_VALID" = true ] \
    && [ "$EARLY_LOCAL_REHEARSAL" != true ]; then
    PYTHON_EXECUTOR_CANDIDATE="$EARLY_RELEASE_ROOT_VALUE/venv/bin/python"
    if [ ! -x "$PYTHON_EXECUTOR_CANDIDATE" ]; then
      PYTHON_EXECUTOR_CANDIDATE=/usr/bin/python3
    fi
  else
    PYTHON_EXECUTOR_CANDIDATE="$(type -P python3 2>/dev/null \
      || type -P python 2>/dev/null)" || {
      printf 'install_closed_release: python-executor-unavailable\n' >&2
      exit 2
    }
  fi
fi
PYTHON_EXECUTOR_LOGICAL="$PYTHON_EXECUTOR_CANDIDATE"
PYTHON_EXECUTOR_AUTHORITY="$(canonical_executable_path "$PYTHON_EXECUTOR_CANDIDATE")" || {
  printf 'install_closed_release: python-executor-authority-required\n' >&2
  exit 2
}
PYTHON_EXECUTOR="$PYTHON_EXECUTOR_AUTHORITY"
PYTHON_EXECUTOR_FD=''
if [[ "$OSTYPE" = linux* ]]; then
  exec {PYTHON_EXECUTOR_FD}<"$PYTHON_EXECUTOR_AUTHORITY" || {
    printf 'install_closed_release: python-executor-pin-failed\n' >&2
    exit 2
  }
  [ "$PYTHON_EXECUTOR_AUTHORITY" -ef "/proc/$BASHPID/fd/$PYTHON_EXECUTOR_FD" ] || {
    printf 'install_closed_release: python-executor-pin-mismatch\n' >&2
    exit 2
  }
  PYTHON_EXECUTOR="/proc/$BASHPID/fd/$PYTHON_EXECUTOR_FD"
fi
invoke_python() {
  if [[ "$OSTYPE" = linux* ]]; then
    /usr/bin/env --argv0="$PYTHON_EXECUTOR_LOGICAL" "$PYTHON_EXECUTOR" "$@"
  else
    "$PYTHON_EXECUTOR" "$@"
  fi
}
executable_sha256() {
  invoke_python - "$1" <<'PY'
from hashlib import sha256
from pathlib import Path
import sys

path = Path(sys.argv[1])
if path.is_symlink() or not path.is_file():
    raise SystemExit(1)
print(sha256(path.read_bytes()).hexdigest())
PY
}
executable_identity() {
  invoke_python - "$1" <<'PY'
from pathlib import Path
import stat
import sys

path = Path(sys.argv[1])
observed = path.lstat()
if path.is_symlink() or not stat.S_ISREG(observed.st_mode):
    raise SystemExit(1)
print(f"{observed.st_dev}:{observed.st_ino}")
PY
}
if [ "$EARLY_REQUIRED_ARGUMENTS_VALID" = true ] \
  && ! invoke_python -c \
    'import ssl; from dotenv.parser import parse_stream' >/dev/null 2>&1; then
  printf 'install_closed_release: python-executor-runtime-incompatible\n' >&2
  exit 2
fi
BASH_EXECUTOR="$(canonical_executable_path "$BASH")" || {
  printf 'install_closed_release: bash-executor-authority-required\n' >&2
  exit 2
}
RM_EXECUTOR_CANDIDATE=/usr/bin/rm
if [ -n "${VL360_LOCAL_RM_EXECUTOR:-}" ] \
  && [ "$EARLY_REQUIRED_ARGUMENTS_VALID" = true ]; then
  [ "$EARLY_LOCAL_REHEARSAL" = true ] || {
    printf 'install_closed_release: local-rm-executor-live-forbidden\n' >&2
    exit 2
  }
  RM_EXECUTOR_CANDIDATE="$VL360_LOCAL_RM_EXECUTOR"
  [ "$(/usr/bin/readlink -f -- "$RM_EXECUTOR_CANDIDATE" 2>/dev/null)" \
    = "$RM_EXECUTOR_CANDIDATE" ] || {
    printf 'install_closed_release: rm-executor-authority-required\n' >&2
    exit 2
  }
fi
RM_EXECUTOR="$(canonical_executable_path "$RM_EXECUTOR_CANDIDATE")" || {
  printf 'install_closed_release: rm-executor-authority-required\n' >&2
  exit 2
}
RM_EXECUTOR_SHA256="$(executable_sha256 "$RM_EXECUTOR")" || {
  printf 'install_closed_release: rm-executor-authority-required\n' >&2
  exit 2
}
RM_EXECUTOR_IDENTITY="$(executable_identity "$RM_EXECUTOR")" || {
  printf 'install_closed_release: rm-executor-authority-required\n' >&2
  exit 2
}
unset VL360_LOCAL_RM_EXECUTOR
ENV_EXECUTOR="$(canonical_executable_path /usr/bin/env)" || {
  printf 'install_closed_release: env-executor-authority-required\n' >&2
  exit 2
}
invoke_rm() {
  [ "$(canonical_executable_path "$RM_EXECUTOR")" = "$RM_EXECUTOR" ] \
    && [ "$(executable_sha256 "$RM_EXECUTOR")" = "$RM_EXECUTOR_SHA256" ] \
    && [ "$(executable_identity "$RM_EXECUTOR")" = "$RM_EXECUTOR_IDENTITY" ] \
    || return 126
  "$RM_EXECUTOR" "$@"
}
if [[ "$OSTYPE" = linux* ]]; then
  [ "$BASH_EXECUTOR" -ef "/proc/$BASHPID/exe" ] || {
    printf 'install_closed_release: bash-executor-identity-mismatch\n' >&2
    exit 2
  }
fi
BASH_PIN_AUTHORITY="$BASH_EXECUTOR"
readonly PYTHON_EXECUTOR_LOGICAL PYTHON_EXECUTOR_AUTHORITY PYTHON_EXECUTOR \
  PYTHON_EXECUTOR_FD BASH_EXECUTOR BASH_PIN_AUTHORITY RM_EXECUTOR \
  RM_EXECUTOR_SHA256 RM_EXECUTOR_IDENTITY ENV_EXECUTOR

fsync_directories() {
  (($# > 0)) || return 0
  invoke_python - "$@" <<'PY'
import os
import sys

if os.name == "nt":
    raise SystemExit(0)

seen = set()
for raw in sys.argv[1:]:
    directory = os.path.realpath(raw)
    if directory in seen:
        continue
    seen.add(directory)
    descriptor = os.open(
        directory,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
PY
}

remove_private_directory() {
  local target="$1"
  local parent="$2"
  local cleanup_status=0
  if invoke_rm -rf -- "$target" >/dev/null 2>&1; then
    :
  else
    cleanup_status=$?
  fi
  if [ -e "$target" ] || [ -L "$target" ]; then
    [ "$cleanup_status" -ne 0 ] || cleanup_status=1
  elif fsync_directories "$parent"; then
    :
  else
    local fsync_status=$?
    [ "$cleanup_status" -ne 0 ] || cleanup_status="$fsync_status"
  fi
  return "$cleanup_status"
}

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
MIGRATION_GATE_EVIDENCE=''
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
    "$root/migration-gate-evidence.json" \
    "$root/install-recovery.json" \
    "$root/systemd-unit-cleanup.json" \
    "$root/install-lock.json" \
    "$root/findmnt-before.json" \
    "$root/findmnt-after-umount.json" \
    "$root/findmnt-after.json" \
    "$root/findmnt-recovery.json" \
    "$root/persistent-before.json" \
    "$root/persistent-after.json" \
    "$root/persistent-recovery.json" \
    "$root/install-mutation-state.json" || return 1
  rm -rf -- \
    "$root/package" \
    "$root/staged" \
    "$root/installed" \
    "$root/installed-recovery" || return 1
  fsync_directories "$root" "$(dirname -- "$root")" || return 1
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

preflight_authority_role_collisions() {
  invoke_python - "$@" <<'PY'
import os
import sys

seen = []
for index in range(1, len(sys.argv), 2):
    role = sys.argv[index]
    authority = os.path.normcase(os.path.realpath(sys.argv[index + 1]))
    for existing_role, existing_authority in seen:
        if existing_role == role and existing_authority == authority:
            continue
        try:
            common = os.path.commonpath((authority, existing_authority))
        except ValueError:
            continue
        if common in (authority, existing_authority):
            raise SystemExit(12)
    seen.append((role, authority))
PY
}

canonical_authority_path() {
  local authority="$1"
  local local_rehearsal="$2"
  local canonical
  canonical="$(invoke_python - "$authority" <<'PY'
import os
from pathlib import Path
import stat
import sys

path = Path(os.path.abspath(sys.argv[1]))
anchor = Path(path.anchor) if path.anchor else Path()
current = anchor
parts = path.parts[1:] if path.anchor else path.parts
for part in parts:
    current /= part
    try:
        observed = os.lstat(current)
    except FileNotFoundError:
        continue
    if stat.S_ISLNK(observed.st_mode) or os.path.islink(current):
        raise SystemExit(12)
print(os.path.realpath(path))
PY
  )" || return 1
  if [ -x /usr/bin/cygpath ]; then
    /usr/bin/cygpath -u "$canonical"
  else
    printf '%s\n' "$canonical"
  fi
}

validate_executable_authority_sources() {
  invoke_python - "$RELEASE_ROOT" "$PERSISTENT_AGENT_DATA_ROOT" "$EVIDENCE_DIR" \
    "$SYSTEMD_UNIT_DESTINATION" "$STALE_RELEASE_ROOT" "$STALE_PERSISTENT_ROOT" \
    "$STALE_SYSTEMD_UNIT_DESTINATION" "$MOUNT_AUTHORITY" \
    "$PYTHON_DEPENDENCY_HOOK" "$NUXT_DEPENDENCY_HOOK" "$UNIT_VERIFY_HOOK" <<'PY'
import os
from pathlib import Path
import stat
import sys


def absolute(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def has_symlink_component(raw):
    path = Path(os.path.abspath(raw))
    anchor = Path(path.anchor) if path.anchor else Path()
    current = anchor
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current /= part
        try:
            observed = os.lstat(current)
        except OSError:
            return True
        if stat.S_ISLNK(observed.st_mode) or os.path.islink(current):
            return True
    return False


def overlaps(left, right):
    try:
        common = os.path.commonpath((left, right))
    except ValueError:
        return False
    return common in (left, right)


def is_reserved(candidate, release):
    if not release:
        return False
    release = absolute(release)
    parent = os.path.dirname(release)
    name = os.path.basename(release)
    try:
        relative = os.path.relpath(candidate, parent)
    except ValueError:
        return False
    if relative == os.pardir or relative.startswith(os.pardir + os.sep):
        return False
    first = relative.split(os.sep, 1)[0]
    return any(
        first == f".{name}.closed-{kind}"
        or first.startswith(f".{name}.closed-{kind}.")
        for kind in ("stage", "old", "retired")
    )


release, persistent, evidence, systemd, stale_release, stale_persistent, stale_systemd = (
    sys.argv[1:8]
)
mount, python_hook, nuxt_hook, unit_hook = sys.argv[8:]
if not mount and os.environ.get("VL360_EXECUTABLE_LIVE_MODE") == "true":
    raise SystemExit(22)
sources = [
    ("mount", mount),
    ("hook", python_hook),
    ("hook", nuxt_hook),
    ("hook", unit_hook),
]
protected = [
    absolute(path)
    for path in (
        release,
        persistent,
        evidence,
        systemd,
        stale_release,
        stale_persistent,
        stale_systemd,
    )
    if path
]
for role, raw in sources:
    if not raw:
        continue
    if has_symlink_component(raw):
        raise SystemExit(22 if role == "mount" else 20)
    path = Path(os.path.abspath(raw))
    try:
        observed = path.stat()
    except OSError:
        raise SystemExit(22 if role == "mount" else 20)
    executable = os.access(path, os.X_OK) if os.name == "nt" else bool(observed.st_mode & 0o111)
    if not stat.S_ISREG(observed.st_mode) or not executable:
        raise SystemExit(22 if role == "mount" else 20)
    candidate = absolute(raw)
    if any(overlaps(candidate, namespace) for namespace in protected):
        raise SystemExit(21)
    if is_reserved(candidate, release) or is_reserved(candidate, stale_release):
        raise SystemExit(21)
PY
}

validate_executable_pin_root() {
  local candidate="$1"
  invoke_python - "$candidate" "$RELEASE_ROOT" "$PERSISTENT_AGENT_DATA_ROOT" \
    "$EVIDENCE_DIR" "$SYSTEMD_UNIT_DESTINATION" "$STALE_RELEASE_ROOT" \
    "$STALE_PERSISTENT_ROOT" "$STALE_SYSTEMD_UNIT_DESTINATION" <<'PY'
import os
import sys


def absolute(path):
    return os.path.normcase(os.path.realpath(os.path.abspath(path)))


def overlaps(left, right):
    try:
        common = os.path.commonpath((left, right))
    except ValueError:
        return False
    return common in (left, right)


def is_reserved(candidate, release):
    if not release:
        return False
    release = absolute(release)
    parent = os.path.dirname(release)
    name = os.path.basename(release)
    try:
        relative = os.path.relpath(candidate, parent)
    except ValueError:
        return False
    if relative == os.pardir or relative.startswith(os.pardir + os.sep):
        return False
    first = relative.split(os.sep, 1)[0]
    return any(
        first == f".{name}.closed-{kind}"
        or first.startswith(f".{name}.closed-{kind}.")
        for kind in ("stage", "old", "retired")
    )


candidate = absolute(sys.argv[1])
release = sys.argv[2]
stale_release = sys.argv[6]
protected = [absolute(path) for path in sys.argv[2:] if path]
if any(overlaps(candidate, namespace) for namespace in protected):
    raise SystemExit(1)
if is_reserved(candidate, release) or is_reserved(candidate, stale_release):
    raise SystemExit(1)
PY
}

pin_executable_authorities() {
  invoke_python - "$EXECUTABLE_PIN_ROOT" "$MOUNT_AUTHORITY" \
    "$PYTHON_DEPENDENCY_HOOK" "$NUXT_DEPENDENCY_HOOK" "$UNIT_VERIFY_HOOK" \
    "$BASH_PIN_AUTHORITY" <<'PY'
from hashlib import sha256
import os
from pathlib import Path
import stat
import sys


def validate_components(raw):
    path = Path(os.path.abspath(raw))
    anchor = Path(path.anchor) if path.anchor else Path()
    current = anchor
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current /= part
        observed = os.lstat(current)
        if stat.S_ISLNK(observed.st_mode) or os.path.islink(current):
            raise OSError("symlink component")
    return path


def read_admitted_bytes(raw):
    path = validate_components(raw)
    if os.name != "nt" and hasattr(os, "O_NOFOLLOW") and os.open in os.supports_dir_fd:
        parts = path.parts
        descriptor = os.open(
            path.anchor,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            for component in parts[1:-1]:
                next_descriptor = os.open(
                    component,
                    os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_DIRECTORY", 0),
                    dir_fd=descriptor,
                )
                os.close(descriptor)
                descriptor = next_descriptor
            file_descriptor = os.open(
                parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=descriptor
            )
        finally:
            os.close(descriptor)
    else:
        file_descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    try:
        observed = os.fstat(file_descriptor)
        executable = (
            os.access(path, os.X_OK)
            if os.name == "nt"
            else bool(observed.st_mode & 0o111)
        )
        if not stat.S_ISREG(observed.st_mode) or not executable:
            raise OSError("not a regular executable")
        chunks = []
        while True:
            chunk = os.read(file_descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(file_descriptor)


root = Path(sys.argv[1])
if root.is_symlink() or not root.is_dir():
    raise SystemExit(1)
roles = (
    ("mount", sys.argv[2]),
    ("python-dependency", sys.argv[3]),
    ("nuxt-dependency", sys.argv[4]),
    ("unit-verify", sys.argv[5]),
    ("bash-interpreter", sys.argv[6]),
)
digests = []
for role, source in roles:
    if not source:
        digests.append("-")
        continue
    raw = read_admitted_bytes(source)
    target = root / role
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
        0o500,
    )
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fchmod(descriptor, 0o500)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if target.is_symlink() or not target.is_file() or target.read_bytes() != raw:
        raise SystemExit(1)
    if os.name != "nt" and stat.S_IMODE(target.stat().st_mode) != 0o500:
        raise SystemExit(1)
    digests.append(sha256(raw).hexdigest())
if os.name != "nt":
    descriptor = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
print("\t".join(digests))
PY
}

verify_pinned_executable() {
  local path="$1"
  local expected_sha256="$2"
  invoke_python - "$path" "$expected_sha256" <<'PY'
from hashlib import sha256
import os
from pathlib import Path
import stat
import sys

path = Path(sys.argv[1])
expected = sys.argv[2]
if path.is_symlink() or not path.is_file():
    raise SystemExit(1)
observed = path.stat()
if not stat.S_ISREG(observed.st_mode):
    raise SystemExit(1)
if os.name != "nt" and stat.S_IMODE(observed.st_mode) != 0o500:
    raise SystemExit(1)
if sha256(path.read_bytes()).hexdigest() != expected:
    raise SystemExit(1)
PY
}

ATTEMPT_ID="$(invoke_python - <<'PY'
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
  key="$(invoke_python - "$authority" <<'PY'
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
  owner="$(invoke_python - "$lock_dir/owner.json" <<'PY'
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

named_artifact_owner_is_live() {
  local artifact="$1"
  local name suffix owner_pid owner_start current_start
  name="$(basename -- "$artifact")"
  case "$name" in
    vl360-executable-pins.*)
      suffix="${name#vl360-executable-pins.}"
      ;;
    *.pending.*)
      suffix="${name##*.pending.}"
      ;;
    *.released.*)
      suffix="${name##*.released.}"
      ;;
    *.stale.*)
      suffix="${name##*.stale.}"
      ;;
    *) return 2 ;;
  esac
  owner_pid="${suffix%%.*}"
  [ "$owner_pid" != "$suffix" ] || return 2
  suffix="${suffix#*.}"
  owner_start="${suffix%%.*}"
  case "$owner_pid" in ''|*[!0-9]*) return 2 ;; esac
  [ -n "$owner_start" ] || return 2
  kill -0 "$owner_pid" 2>/dev/null || return 1
  current_start="$(process_start_identity "$owner_pid" 2>/dev/null)" || return 0
  [ "$current_start" = "$owner_start" ]
}

private_attempt_artifact_is_stale() {
  local artifact="$1"
  local owner_state
  if lock_owner_is_live "$artifact"; then
    return 1
  else
    owner_state=$?
  fi
  case "$owner_state" in
    1) return 0 ;;
    2)
      if named_artifact_owner_is_live "$artifact"; then
        return 1
      else
        owner_state=$?
      fi
      [ "$owner_state" -eq 1 ]
      ;;
    *) return 1 ;;
  esac
}

sweep_stale_lock_artifacts() {
  local lock_dir="$1"
  local lock_root="$2"
  local artifact
  for artifact in "$lock_dir".pending.* "$lock_dir".released.* \
    "$lock_dir".stale.*; do
    [ -e "$artifact" ] || [ -L "$artifact" ] || continue
    [ -d "$artifact" ] && [ ! -L "$artifact" ] || return 1
    if private_attempt_artifact_is_stale "$artifact"; then
      remove_private_directory "$artifact" "$lock_root" || return 1
    fi
  done
}

sweep_stale_archive_attempts() {
  local evidence_root="$1"
  local artifact
  for artifact in "$evidence_root"/.closed-archive-attempt.*; do
    [ -e "$artifact" ] || [ -L "$artifact" ] || continue
    [ -d "$artifact" ] && [ ! -L "$artifact" ] || return 1
    remove_private_directory "$artifact" "$evidence_root" || return 1
  done
}

remove_lock_dir() {
  local lock_dir="$1"
  remove_private_directory "$lock_dir" "$(dirname -- "$lock_dir")"
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
  local released="$lock_dir.released.$$.${PROCESS_START_IDENTITY}"
  local retry
  for retry in 1 2 3 4 5; do
    lock_is_owned_by_attempt "$lock_dir" || return 1
    if mv -- "$lock_dir" "$released" 2>/dev/null; then
      [ ! -e "$lock_dir" ] && [ ! -L "$lock_dir" ] \
        && lock_is_owned_by_attempt "$released" || return 1
      remove_lock_dir "$released"
      return $?
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
  local pending="$lock_dir.pending.$$.${PROCESS_START_IDENTITY}"
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
  sweep_stale_lock_artifacts "$lock_dir" "$lock_root" || return 11

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
    tombstone="$lock_dir.stale.$$.${PROCESS_START_IDENTITY}"
    if mv -- "$lock_dir" "$tombstone" 2>/dev/null; then
      if publish_owned_lock "$lock_dir"; then
        HELD_LOCK_DIRS+=("$lock_dir")
        HELD_LOCK_ROOTS+=("$lock_root")
        HELD_LOCK_KEYS+=("$lock_key")
        HELD_LOCK_KINDS+=("$lock_kind")
        remove_private_directory "$tombstone" "$lock_root" || return 11
        RECLAIMED_STALE_LOCKS=$((RECLAIMED_STALE_LOCKS + 1))
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
  sweep_stale_archive_attempts "$root" || die 'private-archive-cleanup-failed'
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
DISCOVERED_RELEASE_ROOT=''
DISCOVERED_PERSISTENT_ROOT=''
DISCOVERED_ENVIRONMENT_AUTHORITY=''
DISCOVERED_MIGRATION_GATE_EVIDENCE=''
DISCOVERED_RUNTIME_AUTHORITY=''
DISCOVERY_AUTHORITIES_VALID=false
for ((discovery_index = 0; discovery_index < ${#ORIGINAL_ARGS[@]}; discovery_index++)); do
  discovery_option="${ORIGINAL_ARGS[$discovery_index]}"
  case "$discovery_option" in
    --evidence-dir|--release-root|--persistent-agent-data-root|\
    --environment-authority|--runtime-authority) ;;
    --migration-gate-evidence) ;;
    *) continue ;;
  esac
  discovery_value_index=$((discovery_index + 1))
  ((discovery_value_index < ${#ORIGINAL_ARGS[@]})) || continue
  discovery_value="${ORIGINAL_ARGS[$discovery_value_index]}"
  case "$discovery_value" in
    ''|--*) continue ;;
  esac
  case "$discovery_option" in
    --evidence-dir) DISCOVERED_EVIDENCE_DIR="$discovery_value" ;;
    --release-root) DISCOVERED_RELEASE_ROOT="$discovery_value" ;;
    --persistent-agent-data-root) DISCOVERED_PERSISTENT_ROOT="$discovery_value" ;;
    --environment-authority) DISCOVERED_ENVIRONMENT_AUTHORITY="$discovery_value" ;;
    --migration-gate-evidence) DISCOVERED_MIGRATION_GATE_EVIDENCE="$discovery_value" ;;
    --runtime-authority) DISCOVERED_RUNTIME_AUTHORITY="$discovery_value" ;;
  esac
done
if [ -n "$DISCOVERED_EVIDENCE_DIR" ] \
  && [ -n "$DISCOVERED_RELEASE_ROOT" ] \
  && [ -n "$DISCOVERED_PERSISTENT_ROOT" ] \
  && [ -n "$DISCOVERED_ENVIRONMENT_AUTHORITY" ] \
  && { [ "$DISCOVERY_LOCAL_REHEARSAL" != true ] \
    || [ -n "$DISCOVERED_RUNTIME_AUTHORITY" ]; }; then
  if DISCOVERED_EVIDENCE_DIR="$(
      normalize_evidence_candidate "$DISCOVERED_EVIDENCE_DIR" \
        "$DISCOVERY_LOCAL_REHEARSAL" 2>/dev/null
    )" \
    && DISCOVERED_RELEASE_ROOT="$(
      normalize_evidence_candidate "$DISCOVERED_RELEASE_ROOT" \
        "$DISCOVERY_LOCAL_REHEARSAL" 2>/dev/null
    )" \
    && DISCOVERED_PERSISTENT_ROOT="$(
      normalize_evidence_candidate "$DISCOVERED_PERSISTENT_ROOT" \
        "$DISCOVERY_LOCAL_REHEARSAL" 2>/dev/null
    )" \
    && DISCOVERED_ENVIRONMENT_AUTHORITY="$(
      normalize_evidence_candidate "$DISCOVERED_ENVIRONMENT_AUTHORITY" \
        "$DISCOVERY_LOCAL_REHEARSAL" 2>/dev/null
    )"; then
    if DISCOVERED_EVIDENCE_DIR="$(
        canonical_authority_path "$DISCOVERED_EVIDENCE_DIR" \
          "$DISCOVERY_LOCAL_REHEARSAL" 2>/dev/null
      )" \
      && DISCOVERED_ENVIRONMENT_AUTHORITY="$(
        canonical_authority_path "$DISCOVERED_ENVIRONMENT_AUTHORITY" \
          "$DISCOVERY_LOCAL_REHEARSAL" 2>/dev/null
      )"; then
      if [ "$DISCOVERY_LOCAL_REHEARSAL" = true ]; then
        if DISCOVERED_RUNTIME_AUTHORITY="$(
          normalize_evidence_candidate "$DISCOVERED_RUNTIME_AUTHORITY" true \
            2>/dev/null
        )" \
          && DISCOVERED_RUNTIME_AUTHORITY="$(
            canonical_authority_path "$DISCOVERED_RUNTIME_AUTHORITY" true \
              2>/dev/null
          )"; then
          DISCOVERED_SYSTEMD_DESTINATION="$DISCOVERED_RUNTIME_AUTHORITY/systemd-units"
        else
          DISCOVERED_SYSTEMD_DESTINATION=''
        fi
      else
        DISCOVERED_SYSTEMD_DESTINATION=/etc/systemd/system
      fi
      if [ -n "$DISCOVERED_SYSTEMD_DESTINATION" ]; then
        if preflight_authority_role_collisions \
          evidence "$DISCOVERED_EVIDENCE_DIR" \
          release "$DISCOVERED_RELEASE_ROOT" \
          persistent "$DISCOVERED_PERSISTENT_ROOT" \
          systemd "$DISCOVERED_SYSTEMD_DESTINATION"; then
          :
        else
          discovery_collision_status=$?
          [ "$discovery_collision_status" -ne 12 ] \
            || die 'install-authority-role-collision'
        fi
        DISCOVERY_AUTHORITIES_VALID=true
      fi
    else
      DISCOVERED_SYSTEMD_DESTINATION=''
    fi
  fi
fi
if [ "$DISCOVERY_AUTHORITIES_VALID" = true ] \
  && [ -n "$DISCOVERED_EVIDENCE_DIR" ]; then
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
    --migration-gate-evidence)
      require_option_value "$1" "$#" "${2:-}"
      MIGRATION_GATE_EVIDENCE="$2"
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
if [ "$LOCAL_REHEARSAL" != true ] && [ -z "$MIGRATION_GATE_EVIDENCE" ]; then
  die 'migration-gate-evidence-required'
fi
if [ "$LOCAL_REHEARSAL" = true ] && command -v cygpath >/dev/null 2>&1; then
  ARCHIVE="$(cygpath -u "$ARCHIVE")"
  ARCHIVE_DIGEST_FILE="$(cygpath -u "$ARCHIVE_DIGEST_FILE")"
  RELEASE_ROOT="$(cygpath -u "$RELEASE_ROOT")"
  PERSISTENT_AGENT_DATA_ROOT="$(cygpath -u "$PERSISTENT_AGENT_DATA_ROOT")"
  ENVIRONMENT_AUTHORITY="$(cygpath -u "$ENVIRONMENT_AUTHORITY")"
  [ -z "$MIGRATION_GATE_EVIDENCE" ] || MIGRATION_GATE_EVIDENCE="$(cygpath -u "$MIGRATION_GATE_EVIDENCE")"
  RUNTIME_AUTHORITY="$(cygpath -u "$RUNTIME_AUTHORITY")"
  [ -z "$MOUNT_AUTHORITY" ] || MOUNT_AUTHORITY="$(cygpath -u "$MOUNT_AUTHORITY")"
  EVIDENCE_DIR="$(cygpath -u "$EVIDENCE_DIR")"
  [ -z "$LOCAL_REHEARSAL_SENTINEL" ] \
    || LOCAL_REHEARSAL_SENTINEL="$(cygpath -u "$LOCAL_REHEARSAL_SENTINEL")"
fi
if canonical_evidence_dir="$(
    canonical_authority_path "$EVIDENCE_DIR" "$LOCAL_REHEARSAL"
  )"; then
  EVIDENCE_DIR="$canonical_evidence_dir"
else
  die 'evidence-dir-symlink-forbidden'
fi
if canonical_environment_authority="$(
    canonical_authority_path "$ENVIRONMENT_AUTHORITY" "$LOCAL_REHEARSAL"
  )"; then
  ENVIRONMENT_AUTHORITY="$canonical_environment_authority"
else
  die 'external-environment-authority-required'
fi
if canonical_runtime_authority="$(
    canonical_authority_path "$RUNTIME_AUTHORITY" "$LOCAL_REHEARSAL"
  )"; then
  RUNTIME_AUTHORITY="$canonical_runtime_authority"
else
  die 'external-runtime-authority-required'
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
if ENVIRONMENT_AUTHORITY_SHA256="$(invoke_python - "$ENVIRONMENT_AUTHORITY" \
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
MIGRATION_GATE_EVIDENCE_SHA256=''
MIGRATION_GATE_MIGRATION_SET_SHA256=''
MIGRATION_GATE_LATEST_VERSION=''
MIGRATION_GATE_LATEST_MIGRATION=''
MIGRATION_GATE_OBSERVED_VERSION=''
MIGRATION_GATE_OBSERVED_MIGRATION=''
if [ -n "$MIGRATION_GATE_EVIDENCE" ]; then
  if canonical_migration_gate_evidence="$(
      canonical_authority_path "$MIGRATION_GATE_EVIDENCE" "$LOCAL_REHEARSAL"
    )"; then
    MIGRATION_GATE_EVIDENCE="$canonical_migration_gate_evidence"
  else
    die 'migration-gate-evidence-authority-required'
  fi
  [ -f "$MIGRATION_GATE_EVIDENCE" ] && [ ! -L "$MIGRATION_GATE_EVIDENCE" ] \
    || die 'migration-gate-evidence-regular-file-required'
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
CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT="$EVIDENCE_DIR/candidate-release-topology.json"
SOURCE_RELEASE_TOPOLOGY_SNAPSHOT="$EVIDENCE_DIR/source-release-topology.json"
MUTATION_STATE="$EVIDENCE_DIR/install-mutation-state.json"
CANDIDATE_MANIFEST_SHA256=''
CANDIDATE_RELEASE_TOPOLOGY_SHA256=''
CANDIDATE_RELEASE_ROOT_IDENTITY=''
PERSISTENT_SNAPSHOT_SHA256=''
SOURCE_RELEASE_TOPOLOGY_SHA256=''
SOURCE_RELEASE_ROOT_IDENTITY=''
STALE_RELEASE_ROOT=''
STALE_PERSISTENT_ROOT=''
STALE_RELEASE_KEY=''
STALE_PERSISTENT_KEY=''
STALE_STAGING_ROOT=''
STALE_OLD_ROOT=''
STALE_RETIRED_ROOT=''
STALE_SYSTEMD_UNIT_DESTINATION=''
STALE_SYSTEMD_KEY=''
STALE_SYSTEMD_UNIT_ATTEMPT_ROOT=''
STALE_STAGE=''
STALE_PID=''
STALE_ATTEMPT_ID=''
STALE_LOCAL_REHEARSAL=''
STALE_SCHEMA_VERSION=''
STALE_CANDIDATE_MANIFEST_SHA256=''
STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256=''
STALE_CANDIDATE_RELEASE_ROOT_IDENTITY=''
STALE_ENVIRONMENT_AUTHORITY_SHA256=''
STALE_PERSISTENT_SNAPSHOT_SHA256=''
STALE_SOURCE_RELEASE_TOPOLOGY_SHA256=''
STALE_SOURCE_RELEASE_ROOT_IDENTITY=''

regular_file_sha256() {
  invoke_python - "$1" <<'PY'
from hashlib import sha256
from pathlib import Path
import sys

path = Path(sys.argv[1])
if path.is_symlink() or not path.is_file():
    raise SystemExit(1)
print(sha256(path.read_bytes()).hexdigest())
PY
}

source_release_topology_payload() {
  invoke_python - "$1" <<'PY'
import json
import os
from hashlib import sha256
from pathlib import Path
import stat
import sys

raw_root = os.path.abspath(sys.argv[1])
if os.name == "nt" and not raw_root.startswith("\\\\?\\"):
    raw_root = "\\\\?\\" + raw_root
root = Path(raw_root)
if root.is_symlink() or not root.is_dir():
    raise SystemExit(1)
entries = []

def visit(path, relative):
    if relative == "agent/data" or relative.startswith("agent/data/"):
        return
    observed = path.lstat()
    mode = stat.S_IMODE(observed.st_mode)
    if stat.S_ISLNK(observed.st_mode):
        entries.append((relative, "symlink", mode, os.readlink(path)))
        return
    if stat.S_ISREG(observed.st_mode):
        raw = path.read_bytes()
        entries.append((relative, "file", mode, sha256(raw).hexdigest(), len(raw)))
        return
    if stat.S_ISDIR(observed.st_mode):
        entries.append((relative, "directory", mode))
        for child in sorted(path.iterdir(), key=lambda item: item.name):
            child_relative = child.name if relative == "." else f"{relative}/{child.name}"
            visit(child, child_relative)
        return
    raise SystemExit(1)

visit(root, ".")
print(json.dumps(entries, separators=(",", ":"), ensure_ascii=True))
PY
}

source_release_topology_sha256() {
  local root="$1"
  source_release_topology_payload "$root" | invoke_python -c '
from hashlib import sha256
import sys
print(sha256(sys.stdin.buffer.read()).hexdigest())
'
}

source_release_topology_snapshot() {
  local root="$1"
  local target="$2"
  source_release_topology_payload "$root" \
    | write_durable_text_file_from_stdin "$target"
}

source_release_topology_subset() {
  invoke_python - "$1" "$2" <<'PY'
import json
from hashlib import sha256
import os
from pathlib import Path
import stat
import sys

raw_root = os.path.abspath(sys.argv[1])
raw_snapshot = os.path.abspath(sys.argv[2])
if os.name == "nt":
    if not raw_root.startswith("\\\\?\\"):
        raw_root = "\\\\?\\" + raw_root
    if not raw_snapshot.startswith("\\\\?\\"):
        raw_snapshot = "\\\\?\\" + raw_snapshot
root = Path(raw_root)
snapshot = Path(raw_snapshot)
if root.is_symlink() or not root.is_dir() or snapshot.is_symlink() or not snapshot.is_file():
    raise SystemExit(1)
expected = {
    tuple(item)
    for item in json.loads(snapshot.read_text(encoding="utf-8"))
}
observed = []

def visit(path, relative):
    if relative == "agent/data" or relative.startswith("agent/data/"):
        return
    current = path.lstat()
    mode = stat.S_IMODE(current.st_mode)
    if stat.S_ISLNK(current.st_mode):
        observed.append((relative, "symlink", mode, os.readlink(path)))
        return
    if stat.S_ISREG(current.st_mode):
        raw = path.read_bytes()
        observed.append((relative, "file", mode, sha256(raw).hexdigest(), len(raw)))
        return
    if stat.S_ISDIR(current.st_mode):
        observed.append((relative, "directory", mode))
        for child in sorted(path.iterdir(), key=lambda item: item.name):
            child_relative = child.name if relative == "." else f"{relative}/{child.name}"
            visit(child, child_relative)
        return
    raise SystemExit(1)

visit(root, ".")
if not set(observed) <= expected:
    raise SystemExit(1)
PY
}

tree_root_identity() {
  invoke_python - "$1" <<'PY'
import os
from pathlib import Path
import stat
import sys

raw_root = os.path.abspath(sys.argv[1])
if os.name == "nt" and not raw_root.startswith("\\\\?\\"):
    raw_root = "\\\\?\\" + raw_root
root = Path(raw_root)
observed = root.lstat()
if root.is_symlink() or not stat.S_ISDIR(observed.st_mode):
    raise SystemExit(1)
print(f"{observed.st_dev}:{observed.st_ino}")
PY
}

tree_matches_bound_topology() {
  local root="$1"
  local expected_identity="$2"
  local snapshot="$3"
  local allow_subset="${4:-false}"
  [ "$(tree_root_identity "$root")" = "$expected_identity" ] || return 1
  if [ "$allow_subset" = true ]; then
    source_release_topology_subset "$root" "$snapshot"
  else
    [ "$(source_release_topology_sha256 "$root")" \
      = "$(regular_file_sha256 "$snapshot")" ]
  fi
}

write_cleanup_owner_marker() {
  local marker="$1"
  local role="$2"
  local attempt_id="$3"
  local root_identity="$4"
  local topology_sha256="$5"
  local payload
  payload="$(invoke_python - "$role" "$attempt_id" "$root_identity" \
    "$topology_sha256" <<'PY'
import json
import re
import sys

if sys.argv[1] not in ("candidate", "staging", "retired"):
    raise SystemExit(1)
if re.fullmatch(r"[0-9a-f]{32}", sys.argv[2]) is None:
    raise SystemExit(1)
if re.fullmatch(r"[0-9]+:[0-9]+", sys.argv[3]) is None:
    raise SystemExit(1)
if re.fullmatch(r"[0-9a-f]{64}", sys.argv[4]) is None:
    raise SystemExit(1)
print(json.dumps({
    "attempt_id": sys.argv[2],
    "role": sys.argv[1],
    "root_identity": sys.argv[3],
    "topology_sha256": sys.argv[4],
}, separators=(",", ":"), sort_keys=True))
PY
  )" || return 1
  write_durable_atomic_json "$marker" "$payload"
}

verify_cleanup_owner_marker() {
  invoke_python - "$1" "$2" "$3" "$4" "$5" <<'PY'
import json
from pathlib import Path
import sys

marker = Path(sys.argv[1])
if marker.is_symlink() or not marker.is_file():
    raise SystemExit(1)
expected = {
    "attempt_id": sys.argv[3],
    "role": sys.argv[2],
    "root_identity": sys.argv[4],
    "topology_sha256": sys.argv[5],
}
if json.loads(marker.read_text(encoding="utf-8")) != expected:
    raise SystemExit(1)
PY
}

new_private_staging_nonce() {
  invoke_python -c 'import secrets; print(secrets.token_hex(32))'
}

write_private_staging_owner_marker() {
  local marker="$1"
  local attempt_id="$2"
  local pid="$3"
  local root_identity="$4"
  local nonce="$5"
  local payload
  payload="$(invoke_python - "$attempt_id" "$pid" "$root_identity" \
    "$nonce" <<'PY'
import json
import re
import sys

if re.fullmatch(r"[0-9a-f]{32}", sys.argv[1]) is None:
    raise SystemExit(1)
if re.fullmatch(r"[1-9][0-9]*", sys.argv[2]) is None:
    raise SystemExit(1)
if re.fullmatch(r"[0-9]+:[0-9]+", sys.argv[3]) is None:
    raise SystemExit(1)
if re.fullmatch(r"[0-9a-f]{64}", sys.argv[4]) is None:
    raise SystemExit(1)
print(json.dumps({
    "attempt_id": sys.argv[1],
    "nonce": sys.argv[4],
    "pid": int(sys.argv[2]),
    "role": "private-staging",
    "root_identity": sys.argv[3],
}, separators=(",", ":"), sort_keys=True))
PY
  )" || return 1
  write_durable_atomic_json "$marker" "$payload"
}

verify_private_staging_owner_marker() {
  invoke_python - "$1" "$2" "$3" "$4" "$5" "$6" <<'PY'
import json
import os
from pathlib import Path
import re
import stat
import sys

marker = Path(sys.argv[1])
stage = Path(sys.argv[2])
if marker.is_symlink() or not marker.is_file():
    raise SystemExit(1)
expected = {
    "attempt_id": sys.argv[3],
    "nonce": sys.argv[6],
    "pid": int(sys.argv[4]),
    "role": "private-staging",
    "root_identity": sys.argv[5],
}
if json.loads(marker.read_text(encoding="utf-8")) != expected:
    raise SystemExit(1)
if os.path.lexists(stage):
    observed = stage.lstat()
    if stage.is_symlink() or not stat.S_ISDIR(observed.st_mode):
        raise SystemExit(1)
    if f"{observed.st_dev}:{observed.st_ino}" != sys.argv[5]:
        raise SystemExit(1)
PY
}

verify_observed_private_staging_owner_marker() {
  invoke_python - "$1" "$2" "$3" "$4" "$5" <<'PY'
import json
import os
from pathlib import Path
import re
import stat
import sys

marker = Path(sys.argv[1])
stage = Path(sys.argv[2])
if marker.is_symlink() or not marker.is_file():
    raise SystemExit(1)
payload = json.loads(marker.read_text(encoding="utf-8"))
if set(payload) != {"attempt_id", "nonce", "pid", "role", "root_identity"}:
    raise SystemExit(1)
if payload != {
    "attempt_id": sys.argv[3],
    "nonce": payload["nonce"],
    "pid": int(sys.argv[4]),
    "role": "private-staging",
    "root_identity": sys.argv[5],
}:
    raise SystemExit(1)
if not isinstance(payload["nonce"], str) or re.fullmatch(
    r"[0-9a-f]{64}", payload["nonce"]
) is None:
    raise SystemExit(1)
if os.path.lexists(stage):
    observed = stage.lstat()
    if stage.is_symlink() or not stat.S_ISDIR(observed.st_mode):
        raise SystemExit(1)
    if f"{observed.st_dev}:{observed.st_ino}" != sys.argv[5]:
        raise SystemExit(1)
PY
}

write_durable_atomic_json() {
  local path="$1"
  local payload="$2"
  VL360_DURABLE_JSON_PAYLOAD="$payload" invoke_python - "$path" <<'PY'
import json
import os
from pathlib import Path
import sys
import tempfile

def fsync_directory(directory):
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

path = Path(sys.argv[1])
payload = json.loads(os.environ["VL360_DURABLE_JSON_PAYLOAD"])
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
    fsync_directory(path.parent)
finally:
    if descriptor != -1:
        os.close(descriptor)
    temporary.unlink(missing_ok=True)
PY
}

write_mutation_state() {
  local stage="$1"
  local payload release_spec persistent_spec release_key persistent_key
  release_spec="$(lock_spec release "$RELEASE_ROOT" "$LOCAL_REHEARSAL")" || return 1
  persistent_spec="$(lock_spec persistent "$PERSISTENT_AGENT_DATA_ROOT" \
    "$LOCAL_REHEARSAL")" || return 1
  IFS='|' read -r _ _ release_key _ <<< "$release_spec"
  IFS='|' read -r _ _ persistent_key _ <<< "$persistent_spec"
  payload="$(MSYS2_ENV_CONV_EXCL='VL360_STATE_RELEASE_ROOT;VL360_STATE_PERSISTENT_ROOT;VL360_STATE_STAGING_ROOT;VL360_STATE_OLD_ROOT;VL360_STATE_RETIRED_ROOT;VL360_STATE_SYSTEMD_UNIT_DESTINATION;VL360_STATE_SYSTEMD_UNIT_ATTEMPT_ROOT' \
    VL360_STATE_RELEASE_ROOT="$RELEASE_ROOT" \
    VL360_STATE_PERSISTENT_ROOT="$PERSISTENT_AGENT_DATA_ROOT" \
    VL360_STATE_STAGING_ROOT="$STAGING_ROOT" \
    VL360_STATE_OLD_ROOT="$OLD_ROOT" \
    VL360_STATE_RETIRED_ROOT="$RETIRED_ROOT" \
    VL360_STATE_SYSTEMD_UNIT_DESTINATION="$SYSTEMD_UNIT_DESTINATION" \
    VL360_STATE_SYSTEMD_UNIT_ATTEMPT_ROOT="$UNIT_ATTEMPT_ROOT" \
    VL360_STATE_LOCAL_REHEARSAL="$LOCAL_REHEARSAL" \
    invoke_python - "$MUTATION_STATE" "$stage" "$ATTEMPT_ID" "$$" \
      "$release_key" "$persistent_key" "$CURRENT_SYSTEMD_KEY" \
      "$CANDIDATE_MANIFEST_SHA256" "$ENVIRONMENT_AUTHORITY_SHA256" \
      "$PERSISTENT_SNAPSHOT_SHA256" "$SOURCE_RELEASE_TOPOLOGY_SHA256" \
      "$CANDIDATE_RELEASE_TOPOLOGY_SHA256" \
      "$SOURCE_RELEASE_ROOT_IDENTITY" "$CANDIDATE_RELEASE_ROOT_IDENTITY" <<'PY'
import json
import os
import re
import sys
for value in sys.argv[8:13]:
    if re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise SystemExit(1)
for value in sys.argv[13:15]:
    if re.fullmatch(r"[0-9]+:[0-9]+", value) is None:
        raise SystemExit(1)
payload = {
    "attempt_id": sys.argv[3],
    "candidate_manifest_sha256": sys.argv[8],
    "candidate_release_root_identity": sys.argv[14],
    "candidate_release_topology_sha256": sys.argv[12],
    "environment_authority_sha256": sys.argv[9],
    "local_rehearsal": os.environ["VL360_STATE_LOCAL_REHEARSAL"] == "true",
    "old_root": os.environ["VL360_STATE_OLD_ROOT"],
    "persistent_key_sha256": sys.argv[6],
    "persistent_root": os.environ["VL360_STATE_PERSISTENT_ROOT"],
    "pid": int(sys.argv[4]),
    "release_key_sha256": sys.argv[5],
    "release_root": os.environ["VL360_STATE_RELEASE_ROOT"],
    "retired_root": os.environ["VL360_STATE_RETIRED_ROOT"],
    "persistent_snapshot_sha256": sys.argv[10],
    "schema_version": 4,
    "source_release_root_identity": sys.argv[13],
    "source_release_topology_sha256": sys.argv[11],
    "stage": sys.argv[2],
    "staging_root": os.environ["VL360_STATE_STAGING_ROOT"],
    "systemd_key_sha256": sys.argv[7],
    "systemd_unit_attempt_root": os.environ["VL360_STATE_SYSTEMD_UNIT_ATTEMPT_ROOT"],
    "systemd_unit_destination": os.environ["VL360_STATE_SYSTEMD_UNIT_DESTINATION"],
}
print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
PY
  )" || return 1
  write_durable_atomic_json "$MUTATION_STATE" "$payload"
}

clear_mutation_state() {
  local clear_status=0
  rm -f -- "$MUTATION_STATE" || clear_status=$?
  if [ -e "$MUTATION_STATE" ] || [ -L "$MUTATION_STATE" ]; then
    [ "$clear_status" -ne 0 ] || clear_status=1
  elif ! fsync_directories "$(dirname -- "$MUTATION_STATE")"; then
    [ "$clear_status" -ne 0 ] || clear_status=1
  fi
  return "$clear_status"
}

load_stale_install_state() {
  local state release_spec persistent_spec systemd_spec
  local observed_release_key observed_persistent_key observed_systemd_key
  state="$(invoke_python - "$MUTATION_STATE" <<'PY'
import json
import posixpath
from pathlib import Path
import re
import sys

attempt_id_re = re.compile(r"^[0-9a-f]{32}$")
sha256_re = re.compile(r"^[0-9a-f]{64}$")
v3_keys = {
    "attempt_id",
    "local_rehearsal",
    "old_root",
    "persistent_key_sha256",
    "persistent_root",
    "pid",
    "release_key_sha256",
    "release_root",
    "retired_root",
    "schema_version",
    "stage",
    "staging_root",
    "systemd_key_sha256",
    "systemd_unit_attempt_root",
    "systemd_unit_destination",
}
v4_keys = v3_keys | {
    "candidate_manifest_sha256",
    "candidate_release_root_identity",
    "candidate_release_topology_sha256",
    "environment_authority_sha256",
    "persistent_snapshot_sha256",
    "source_release_root_identity",
    "source_release_topology_sha256",
}
try:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if type(payload) is not dict:
        raise ValueError
    schema_version = payload.get("schema_version")
    if type(schema_version) is not int or schema_version not in (3, 4):
        raise ValueError
    if set(payload) != (v4_keys if schema_version == 4 else v3_keys):
        raise ValueError
    attempt_id = payload["attempt_id"]
    pid = payload["pid"]
    stage = payload["stage"]
    local_rehearsal = payload["local_rehearsal"]
    release_root = payload["release_root"]
    persistent_root = payload["persistent_root"]
    staging_root = payload["staging_root"]
    old_root = payload["old_root"]
    retired_root = payload["retired_root"]
    systemd_destination = payload["systemd_unit_destination"]
    systemd_attempt_root = payload["systemd_unit_attempt_root"]
    release_key = payload["release_key_sha256"]
    persistent_key = payload["persistent_key_sha256"]
    systemd_key = payload["systemd_key_sha256"]
    candidate_manifest_sha256 = payload.get("candidate_manifest_sha256", "")
    candidate_release_root_identity = payload.get(
        "candidate_release_root_identity", ""
    )
    candidate_release_topology_sha256 = payload.get(
        "candidate_release_topology_sha256", ""
    )
    environment_authority_sha256 = payload.get(
        "environment_authority_sha256", ""
    )
    persistent_snapshot_sha256 = payload.get("persistent_snapshot_sha256", "")
    source_release_root_identity = payload.get("source_release_root_identity", "")
    source_release_topology_sha256 = payload.get(
        "source_release_topology_sha256", ""
    )
    values = (
        release_root,
        persistent_root,
        staging_root,
        old_root,
        retired_root,
        systemd_destination,
    )
    if (
        type(attempt_id) is not str
        or attempt_id_re.fullmatch(attempt_id) is None
        or type(pid) is not int
        or pid <= 0
        or type(stage) is not str
        or any(c in stage for c in "\n|")
        or type(local_rehearsal) is not bool
        or any(type(value) is not str for value in values)
        or type(systemd_attempt_root) is not str
        or type(release_key) is not str
        or type(persistent_key) is not str
        or type(systemd_key) is not str
        or any(not value.startswith("/") or any(c in value for c in "\t\n|") for value in values)
        or not sha256_re.fullmatch(release_key)
        or not sha256_re.fullmatch(persistent_key)
        or not sha256_re.fullmatch(systemd_key)
        or (
            schema_version == 4
            and (
                any(
                    sha256_re.fullmatch(value) is None
                    for value in (
                        candidate_manifest_sha256,
                        candidate_release_topology_sha256,
                        environment_authority_sha256,
                        persistent_snapshot_sha256,
                        source_release_topology_sha256,
                    )
                )
                or re.fullmatch(
                    r"[0-9]+:[0-9]+", candidate_release_root_identity
                ) is None
                or re.fullmatch(
                    r"[0-9]+:[0-9]+", source_release_root_identity
                ) is None
            )
        )
    ):
        raise ValueError
    authority_paths = (
        release_root,
        persistent_root,
        systemd_destination,
    )
    if any(posixpath.normpath(path) != path for path in authority_paths):
        raise ValueError
    release_parent = posixpath.dirname(release_root)
    release_name = posixpath.basename(release_root)
    if release_name in ("", ".", ".."):
        raise ValueError
    expected_staging_name = f".{release_name}.closed-stage.{pid}"
    expected_old_name = f".{release_name}.closed-old.{pid}"
    expected_retired_name = f".{release_name}.closed-retired.{attempt_id}"
    for path, expected_name in (
        (staging_root, expected_staging_name),
        (old_root, expected_old_name),
        (retired_root, expected_retired_name),
    ):
        if (
            posixpath.normpath(path) != path
            or posixpath.dirname(path) != release_parent
            or posixpath.basename(path) != expected_name
        ):
            raise ValueError
    if staging_root != f"{release_parent}/{expected_staging_name}":
        raise ValueError
    if old_root != f"{release_parent}/{expected_old_name}":
        raise ValueError
    if retired_root != f"{release_parent}/{expected_retired_name}":
        raise ValueError
    if systemd_attempt_root:
        if (
            not systemd_attempt_root.startswith("/")
            or any(c in systemd_attempt_root for c in "\t\n|")
            or posixpath.normpath(systemd_attempt_root) != systemd_attempt_root
            or re.fullmatch(
                r"\.systemd-unit-attempt\.[A-Za-z0-9]+",
                posixpath.basename(systemd_attempt_root),
            )
            is None
        ):
            raise ValueError
except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
    raise SystemExit(1)
print(
    "|".join(
        (
            str(schema_version),
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
            retired_root,
            systemd_destination,
            systemd_key,
            systemd_attempt_root,
            candidate_manifest_sha256,
            candidate_release_topology_sha256,
            candidate_release_root_identity,
            environment_authority_sha256,
            persistent_snapshot_sha256,
            source_release_topology_sha256,
            source_release_root_identity,
        )
    )
)
PY
  )" || return 1
  IFS='|' read -r STALE_SCHEMA_VERSION STALE_STAGE STALE_PID STALE_ATTEMPT_ID \
    STALE_LOCAL_REHEARSAL STALE_RELEASE_ROOT STALE_PERSISTENT_ROOT \
    STALE_RELEASE_KEY STALE_PERSISTENT_KEY STALE_STAGING_ROOT STALE_OLD_ROOT \
    STALE_RETIRED_ROOT STALE_SYSTEMD_UNIT_DESTINATION STALE_SYSTEMD_KEY \
    STALE_SYSTEMD_UNIT_ATTEMPT_ROOT STALE_CANDIDATE_MANIFEST_SHA256 \
    STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256 \
    STALE_CANDIDATE_RELEASE_ROOT_IDENTITY \
    STALE_ENVIRONMENT_AUTHORITY_SHA256 STALE_PERSISTENT_SNAPSHOT_SHA256 \
    STALE_SOURCE_RELEASE_TOPOLOGY_SHA256 STALE_SOURCE_RELEASE_ROOT_IDENTITY \
    <<< "$state"
  local stale_authority canonical_authority
  for stale_authority in "$STALE_RELEASE_ROOT" "$STALE_PERSISTENT_ROOT" \
    "$STALE_SYSTEMD_UNIT_DESTINATION"; do
    canonical_authority="$(canonical_authority_path "$stale_authority" \
      "$STALE_LOCAL_REHEARSAL")" || return 1
    [ "$canonical_authority" = "$stale_authority" ] || return 1
  done
  if [ -n "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" ]; then
    canonical_authority="$(canonical_authority_path \
      "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" "$STALE_LOCAL_REHEARSAL")" \
      || return 1
    [ "$canonical_authority" = "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" ] \
      || return 1
    [ "$(dirname -- "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT")" = "$EVIDENCE_DIR" ] \
      || return 1
  fi
  release_spec="$(lock_spec release "$STALE_RELEASE_ROOT" \
    "$STALE_LOCAL_REHEARSAL")" || return 1
  persistent_spec="$(lock_spec persistent "$STALE_PERSISTENT_ROOT" \
    "$STALE_LOCAL_REHEARSAL")" || return 1
  systemd_spec="$(lock_spec systemd "$STALE_SYSTEMD_UNIT_DESTINATION" \
    "$STALE_LOCAL_REHEARSAL")" || return 1
  IFS='|' read -r _ _ observed_release_key _ <<< "$release_spec"
  IFS='|' read -r _ _ observed_persistent_key _ <<< "$persistent_spec"
  IFS='|' read -r _ _ observed_systemd_key _ <<< "$systemd_spec"
  [ "$observed_release_key" = "$STALE_RELEASE_KEY" ] \
    && [ "$observed_persistent_key" = "$STALE_PERSISTENT_KEY" ] \
    && [ "$observed_systemd_key" = "$STALE_SYSTEMD_KEY" ]
}

tree_matches_snapshot() {
  local root="$1"
  local snapshot="$2"
  invoke_python - "$root" "$snapshot" <<'PY'
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

restore_systemd_units_from() {
  local destination="$1"
  local attempt_root="$2"
  [ -d "$attempt_root" ] && [ ! -L "$attempt_root" ] \
    && [ -f "$attempt_root/armed" ] && [ ! -L "$attempt_root/armed" ] \
    || return 1
  invoke_python - "$destination" "$attempt_root/backup" <<'PY'
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

UNIT_NAMES = (
    "vl-agent.service",
    "vl-nuxt.service",
    "vl-bot.service",
    "vl-watchdog.service",
    "vl-watchdog.timer",
)

destination = Path(sys.argv[1])
backup = Path(sys.argv[2])
metadata_path = backup / "metadata.json"
if (
    destination.is_symlink()
    or not destination.is_dir()
    or backup.is_symlink()
    or not backup.is_dir()
    or metadata_path.is_symlink()
    or not metadata_path.is_file()
):
    raise SystemExit(1)
metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
if type(metadata) is not dict or set(metadata) != set(UNIT_NAMES):
    raise SystemExit(1)
validated = []
for name in UNIT_NAMES:
    entry = metadata[name]
    target = destination / name
    if (
        type(entry) is not dict
        or type(entry.get("existed")) is not bool
        or type(entry.get("mode")) is not int
        or isinstance(entry.get("mode"), bool)
        or not 0 <= entry["mode"] <= 0o777
        or target.parent != destination
        or target.is_symlink()
        or (target.exists() and not target.is_file())
    ):
        raise SystemExit(1)
    if entry["existed"]:
        if (
            set(entry) != {"existed", "mode", "sha256", "size"}
            or type(entry["sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is None
            or type(entry["size"]) is not int
            or isinstance(entry["size"], bool)
            or entry["size"] < 0
        ):
            raise SystemExit(1)
        backup_file = backup / name
        if backup_file.is_symlink() or not backup_file.is_file():
            raise SystemExit(1)
        raw = backup_file.read_bytes()
        if (
            hashlib.sha256(raw).hexdigest() != entry["sha256"]
            or len(raw) != entry["size"]
        ):
            raise SystemExit(1)
        validated.append((target, entry, raw))
    else:
        if set(entry) != {"existed", "mode"} or entry["mode"] != 0:
            raise SystemExit(1)
        validated.append((target, entry, None))

for target, entry, raw in validated:
    if entry["existed"]:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=destination
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, entry["mode"])
            os.replace(temporary, target)
        finally:
            if descriptor != -1:
                os.close(descriptor)
            temporary.unlink(missing_ok=True)
    else:
        if target.exists() or target.is_symlink():
            target.unlink()
if os.name != "nt":
    descriptor = os.open(destination, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
for target, entry, _raw in validated:
    if entry["existed"]:
        raw = target.read_bytes()
        if (
            target.is_symlink()
            or hashlib.sha256(raw).hexdigest() != entry["sha256"]
            or len(raw) != entry["size"]
            or target.stat().st_mode & 0o777 != entry["mode"]
        ):
            raise SystemExit(1)
    elif target.exists() or target.is_symlink():
        raise SystemExit(1)
PY
}

remove_systemd_unit_attempt_root() {
  local attempt_root="$1"
  local cleanup_status=0
  if rm -rf -- "$attempt_root"; then
    :
  else
    cleanup_status=$?
  fi
  if [ -e "$attempt_root" ] || [ -L "$attempt_root" ]; then
    [ "$cleanup_status" -ne 0 ] || cleanup_status=1
  elif ! fsync_directories "$(dirname -- "$attempt_root")"; then
    [ "$cleanup_status" -ne 0 ] || cleanup_status=1
  fi
  return "$cleanup_status"
}

write_stale_mutation_state() {
  local stage="$1"
  local payload
  payload="$(MSYS2_ENV_CONV_EXCL='VL360_STALE_RELEASE_ROOT;VL360_STALE_PERSISTENT_ROOT;VL360_STALE_STAGING_ROOT;VL360_STALE_OLD_ROOT;VL360_STALE_RETIRED_ROOT;VL360_STALE_SYSTEMD_UNIT_DESTINATION;VL360_STALE_SYSTEMD_UNIT_ATTEMPT_ROOT' \
    VL360_STALE_RELEASE_ROOT="$STALE_RELEASE_ROOT" \
    VL360_STALE_PERSISTENT_ROOT="$STALE_PERSISTENT_ROOT" \
    VL360_STALE_STAGING_ROOT="$STALE_STAGING_ROOT" \
    VL360_STALE_OLD_ROOT="$STALE_OLD_ROOT" \
    VL360_STALE_RETIRED_ROOT="$STALE_RETIRED_ROOT" \
    VL360_STALE_SYSTEMD_UNIT_DESTINATION="$STALE_SYSTEMD_UNIT_DESTINATION" \
    VL360_STALE_SYSTEMD_UNIT_ATTEMPT_ROOT="$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" \
    invoke_python - "$MUTATION_STATE" "$stage" "$STALE_STAGE" \
      "$STALE_ATTEMPT_ID" "$STALE_PID" "$STALE_LOCAL_REHEARSAL" \
      "$STALE_RELEASE_KEY" "$STALE_PERSISTENT_KEY" "$STALE_SYSTEMD_KEY" \
      "$STALE_SCHEMA_VERSION" "$STALE_CANDIDATE_MANIFEST_SHA256" \
      "$STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256" \
      "$STALE_CANDIDATE_RELEASE_ROOT_IDENTITY" \
      "$STALE_ENVIRONMENT_AUTHORITY_SHA256" \
      "$STALE_PERSISTENT_SNAPSHOT_SHA256" \
      "$STALE_SOURCE_RELEASE_TOPOLOGY_SHA256" \
      "$STALE_SOURCE_RELEASE_ROOT_IDENTITY" <<'PY'
import json
import os
from pathlib import Path
import sys

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
    "retired_root": os.environ["VL360_STALE_RETIRED_ROOT"],
    "schema_version": int(sys.argv[10]),
    "stage": sys.argv[3],
    "staging_root": os.environ["VL360_STALE_STAGING_ROOT"],
    "systemd_key_sha256": sys.argv[9],
    "systemd_unit_attempt_root": os.environ["VL360_STALE_SYSTEMD_UNIT_ATTEMPT_ROOT"],
    "systemd_unit_destination": os.environ["VL360_STALE_SYSTEMD_UNIT_DESTINATION"],
}
if expected["schema_version"] == 4:
    expected.update(
        {
            "candidate_manifest_sha256": sys.argv[11],
            "candidate_release_topology_sha256": sys.argv[12],
            "candidate_release_root_identity": sys.argv[13],
            "environment_authority_sha256": sys.argv[14],
            "persistent_snapshot_sha256": sys.argv[15],
            "source_release_topology_sha256": sys.argv[16],
            "source_release_root_identity": sys.argv[17],
        }
    )
if payload != expected:
    raise SystemExit(1)
payload["stage"] = sys.argv[2]
print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
PY
  )" || return 1
  write_durable_atomic_json "$MUTATION_STATE" "$payload" || return 1
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

remove_empty_directory_durably() {
  local directory="$1"
  local remove_status=0
  if rmdir -- "$directory"; then
    :
  else
    remove_status=$?
  fi
  if [ ! -e "$directory" ] && [ ! -L "$directory" ]; then
    fsync_directories "$(dirname -- "$directory")" || return $?
    return "$remove_status"
  fi
  [ "$remove_status" -ne 0 ] && return "$remove_status"
  return 1
}

remove_file_durably() {
  local path="$1"
  local remove_status=0 fsync_status=0
  if invoke_rm -f -- "$path"; then
    :
  else
    remove_status=$?
  fi
  if [ ! -e "$path" ] && [ ! -L "$path" ]; then
    if fsync_directories "$(dirname -- "$path")"; then
      :
    else
      fsync_status=$?
      [ "$remove_status" -ne 0 ] || remove_status="$fsync_status"
    fi
    return "$remove_status"
  fi
  [ "$remove_status" -ne 0 ] && return "$remove_status"
  return 1
}

write_durable_text_file() {
  local path="$1"
  local content="$2"
  invoke_python - "$path" "$content" <<'PY'
import os
import sys
import tempfile
from pathlib import Path

target = Path(sys.argv[1])
raw = sys.argv[2]
descriptor, name = tempfile.mkstemp(
    prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
)
temporary = Path(name)
try:
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
        descriptor = -1
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    if os.name != "nt":
        directory = os.open(
            target.parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
finally:
    if descriptor != -1:
        os.close(descriptor)
    temporary.unlink(missing_ok=True)
PY
}

write_durable_text_file_from_stdin() {
  local path="$1"
  invoke_python -c '
import os
import sys
import tempfile
from pathlib import Path

target = Path(sys.argv[1])
raw = sys.stdin.buffer.read()
descriptor, name = tempfile.mkstemp(
    prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
)
temporary = Path(name)
try:
    with os.fdopen(descriptor, "wb") as stream:
        descriptor = -1
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    if os.name != "nt":
        directory = os.open(
            target.parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
finally:
    if descriptor != -1:
        os.close(descriptor)
    temporary.unlink(missing_ok=True)
' "$path"
}

sweep_stale_staging_attempts() {
  [ ! -e "$MUTATION_STATE" ] && [ ! -L "$MUTATION_STATE" ] || return 1
  local inventory prefix="$RELEASE_PARENT/.${RELEASE_NAME}.closed-stage."
  inventory="$(invoke_python - "$RELEASE_PARENT" "$RELEASE_NAME" <<'PY'
import os
import json
import re
import sys
from pathlib import Path

parent = Path(sys.argv[1])
release_name = sys.argv[2]
if parent.is_symlink() or not parent.is_dir():
    raise SystemExit(1)
parent = Path(os.path.realpath(parent))
prefix = f".{release_name}.closed-stage."
stages = {}
owners = {}
with os.scandir(parent) as entries:
    for entry in entries:
        if not entry.name.startswith(prefix):
            continue
        if entry.is_symlink():
            raise SystemExit(1)
        suffix = entry.name[len(prefix):]
        kind = "owner" if suffix.endswith(".owner") else "stage"
        attempt = suffix[:-6] if kind == "owner" else suffix
        if (
            re.fullmatch(r"[0-9]+", attempt) is None
            or int(attempt) <= 0
            or str(int(attempt)) != attempt
        ):
            raise SystemExit(1)
        path = Path(entry.path)
        if kind == "stage":
            if not entry.is_dir(follow_symlinks=False):
                raise SystemExit(1)
            stages[attempt] = path
        else:
            if not entry.is_file(follow_symlinks=False):
                raise SystemExit(1)
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                raise SystemExit(1)
            if set(payload) != {
                "attempt_id", "nonce", "pid", "role", "root_identity"
            }:
                raise SystemExit(1)
            if (
                not isinstance(payload["attempt_id"], str)
                or re.fullmatch(r"[0-9a-f]{32}", payload["attempt_id"]) is None
                or not isinstance(payload["nonce"], str)
                or re.fullmatch(r"[0-9a-f]{64}", payload["nonce"]) is None
                or type(payload["pid"]) is not int
                or payload["pid"] != int(attempt)
                or payload["role"] != "private-staging"
                or not isinstance(payload["root_identity"], str)
                or re.fullmatch(r"[0-9]+:[0-9]+", payload["root_identity"]) is None
            ):
                raise SystemExit(1)
            owners[attempt] = payload
for attempt in stages:
    if attempt not in owners:
        raise SystemExit(1)
    observed = stages[attempt].stat()
    if f"{observed.st_dev}:{observed.st_ino}" != owners[attempt]["root_identity"]:
        raise SystemExit(1)
for attempt in sorted(set(stages) | set(owners), key=int):
    print(attempt)
PY
  )" || return $?
  local attempt stage owner
  while IFS= read -r attempt; do
    [ -n "$attempt" ] || continue
    stage="$prefix$attempt"
    owner="$stage.owner"
    if [ -e "$stage" ] || [ -L "$stage" ]; then
      verify_observed_private_staging_owner_marker "$owner" "$stage" \
        "$(invoke_python - "$owner" <<'PY'
import json
from pathlib import Path
import sys
print(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["attempt_id"])
PY
        )" "$attempt" "$(tree_root_identity "$stage")" || return 1
      remove_private_directory "$stage" "$RELEASE_PARENT" || return $?
    fi
    remove_file_durably "$owner" || return $?
  done <<< "$inventory"
}

verify_installed_release_authority() {
  local installed_root="$1"
  local persistent_root="$2"
  local systemd_root="$3"
  local evidence_root="$4"
  local mount_evidence="${5:-}"
  local rehearsal="$6"
  local -a mount_args=()
  if [ "$rehearsal" = true ]; then
    mount_args+=(--local-rehearsal)
  else
    [ -n "$mount_evidence" ] || return 1
    mount_args+=(--persistent-mount-evidence "$mount_evidence")
  fi
  invoke_python "$VERIFY_SCRIPT" \
    --installed-root "$installed_root" \
    --persistent-agent-data-root "$persistent_root" \
    --verify-config-ingress-unit-digests \
    --verify-persistent-agent-data-mount \
    --systemd-unit-root "$systemd_root" \
    --verify-systemd-unit-destination \
    --environment-authority "$PINNED_ENVIRONMENT_AUTHORITY" \
    --verify-environment-authority \
    "${mount_args[@]}" \
    --require-closed --evidence-dir "$evidence_root"
}

verify_stale_journal_bindings() {
  local committed="$1"
  local candidate_root="${2:-}"
  if [ "$STALE_SCHEMA_VERSION" = 3 ]; then
    return 1
  fi
  [ "$STALE_SCHEMA_VERSION" = 4 ] || return 1
  [ "$(regular_file_sha256 "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT")" \
    = "$STALE_SOURCE_RELEASE_TOPOLOGY_SHA256" ] || return 1
  [ "$(regular_file_sha256 "$CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT")" \
    = "$STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256" ] || return 1
  [ "$(regular_file_sha256 "$SNAPSHOT_BEFORE")" \
    = "$STALE_PERSISTENT_SNAPSHOT_SHA256" ] || return 1
  if [ -n "$candidate_root" ]; then
    [ "$(regular_file_sha256 \
      "$candidate_root/launch-release-manifest.json")" \
      = "$STALE_CANDIDATE_MANIFEST_SHA256" ] || return 1
  fi
  if [ "$committed" = true ]; then
    [ "$ENVIRONMENT_AUTHORITY_SHA256" \
      = "$STALE_ENVIRONMENT_AUTHORITY_SHA256" ] || return 1
    [ "$(regular_file_sha256 "$PINNED_ENVIRONMENT_AUTHORITY")" \
      = "$STALE_ENVIRONMENT_AUTHORITY_SHA256" ] || return 1
  fi
}

inspect_stale_mount() {
  local target="$1"
  if invoke_mount_authority findmnt --json --mountpoint "$target" \
    > "$EVIDENCE_DIR/findmnt-recovery.json"; then
    if invoke_python - "$VERIFY_SCRIPT" "$EVIDENCE_DIR/findmnt-recovery.json" \
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
    then
      return 0
    fi
    return 2
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
    && [ "$CURRENT_PERSISTENT_KEY" = "$STALE_PERSISTENT_KEY" ] \
    && [ "$CURRENT_SYSTEMD_KEY" = "$STALE_SYSTEMD_KEY" ] || return 1
  [ -f "$MUTATION_STATE" ] && [ ! -L "$MUTATION_STATE" ] || return 1
  local entry_stage="$STALE_STAGE"
  local stale_stage_owner="$STALE_STAGING_ROOT.owner"
  local current_data="$STALE_RELEASE_ROOT/agent/data"
  local current_state persistent_state mount_state rename_status
  local candidate_root source_root
  local candidate_cleanup_root staging_delete_root retired_cleanup_root
  local candidate_cleanup_owner staging_delete_owner retired_cleanup_owner
  local old_present=false retired_present=false release_present=false staging_present=false
  local candidate_cleanup_present=false staging_delete_present=false retired_cleanup_present=false
  local candidate_cleanup_owner_present=false staging_delete_owner_present=false
  local retired_cleanup_owner_present=false
  local mount_verified=false committed_recovery=false
  local observed_root_topology_requires_fsync=false
  case "$STALE_STAGE" in
    detach-agent-data-armed|persistent-detached|swap-release-root-armed|\
    root-swapped|restore-bind-agent-data-armed|persistent-restored|\
    systemd-backup-preparing|\
    systemd-units-armed|\
    retire-old-root-armed|committed-cleanup|\
    recovery-remove-empty-persistent-root-armed|\
    recovery-detach-persistent-armed|recovery-remove-release-root-armed|\
    recovery-restore-old-root-armed|recovery-restore-persistent-armed|\
    recovery-create-persistent-root-armed|recovery-remove-staging-armed|\
    recovery-remove-staging-owner-armed|\
    recovery-remove-systemd-attempt-armed|rollback-restored) ;;
    *) return 1 ;;
  esac

  for candidate in "$STALE_RELEASE_ROOT" "$STALE_PERSISTENT_ROOT" \
    "$STALE_STAGING_ROOT" "$STALE_OLD_ROOT" "$STALE_RETIRED_ROOT" \
    "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" "$stale_stage_owner"; do
    [ ! -L "$candidate" ] || return 1
  done
  candidate_cleanup_root="$(dirname -- "$STALE_RELEASE_ROOT")/.${RELEASE_NAME}.closed-candidate-cleanup.${STALE_ATTEMPT_ID}"
  staging_delete_root="$(dirname -- "$STALE_RELEASE_ROOT")/.${RELEASE_NAME}.closed-staging-cleanup.${STALE_ATTEMPT_ID}"
  retired_cleanup_root="$(dirname -- "$STALE_RELEASE_ROOT")/.${RELEASE_NAME}.closed-retired-cleanup.${STALE_ATTEMPT_ID}"
  candidate_cleanup_owner="$candidate_cleanup_root.owner"
  staging_delete_owner="$staging_delete_root.owner"
  retired_cleanup_owner="$retired_cleanup_root.owner"
  for cleanup_root in "$candidate_cleanup_root" "$staging_delete_root" \
    "$retired_cleanup_root" "$candidate_cleanup_owner" \
    "$staging_delete_owner" "$retired_cleanup_owner"; do
    [ ! -L "$cleanup_root" ] || return 1
  done
  if [ -e "$STALE_OLD_ROOT" ]; then
    [ -d "$STALE_OLD_ROOT" ] || return 1
    old_present=true
  fi
  if [ -e "$STALE_RELEASE_ROOT" ]; then
    [ -d "$STALE_RELEASE_ROOT" ] || return 1
    release_present=true
  fi
  if [ -e "$STALE_RETIRED_ROOT" ]; then
    [ -d "$STALE_RETIRED_ROOT" ] || return 1
    retired_present=true
  fi
  if [ -e "$STALE_STAGING_ROOT" ]; then
    [ -d "$STALE_STAGING_ROOT" ] || return 1
    staging_present=true
  fi
  if [ -e "$candidate_cleanup_root" ]; then
    [ -d "$candidate_cleanup_root" ] || return 1
    candidate_cleanup_present=true
  fi
  if [ -e "$candidate_cleanup_owner" ]; then
    [ -f "$candidate_cleanup_owner" ] || return 1
    candidate_cleanup_owner_present=true
  fi
  if [ -e "$staging_delete_root" ]; then
    [ -d "$staging_delete_root" ] || return 1
    staging_delete_present=true
  fi
  if [ -e "$staging_delete_owner" ]; then
    [ -f "$staging_delete_owner" ] || return 1
    staging_delete_owner_present=true
  fi
  if [ -e "$retired_cleanup_root" ]; then
    [ -d "$retired_cleanup_root" ] || return 1
    retired_cleanup_present=true
  fi
  if [ -e "$retired_cleanup_owner" ]; then
    [ -f "$retired_cleanup_owner" ] || return 1
    retired_cleanup_owner_present=true
  fi
  if [ "$candidate_cleanup_present" = true ] \
    || [ "$candidate_cleanup_owner_present" = true ]; then
    [ "$entry_stage" = recovery-remove-release-root-armed ] || return 1
  fi
  if [ "$release_present" = true ] \
    && [ "$candidate_cleanup_present" = true ]; then
    return 1
  fi
  if [ "$staging_delete_present" = true ] \
    || [ "$staging_delete_owner_present" = true ]; then
    [ "$entry_stage" = recovery-remove-staging-armed ] || return 1
  fi
  if [ "$staging_present" = true ] \
    && [ "$staging_delete_present" = true ]; then
    return 1
  fi
  if [ "$retired_cleanup_present" = true ] \
    || [ "$retired_cleanup_owner_present" = true ]; then
    [ "$entry_stage" = committed-cleanup ] || return 1
  fi
  if [ "$retired_present" = true ] \
    && [ "$retired_cleanup_present" = true ]; then
    return 1
  fi

  case "$entry_stage" in
    detach-agent-data-armed|persistent-detached)
      [ "$old_present" = false ] || return 1
      ;;
    root-swapped|restore-bind-agent-data-armed|persistent-restored|\
    systemd-backup-preparing|\
    systemd-units-armed|\
    recovery-remove-empty-persistent-root-armed|\
    recovery-detach-persistent-armed)
      [ "$old_present" = true ] || return 1
      ;;
    swap-release-root-armed)
      case "$old_present:$release_present:$staging_present" in
        false:true:true|true:false:true) ;;
        true:true:false) observed_root_topology_requires_fsync=true ;;
        *) return 1 ;;
      esac
      ;;
    recovery-remove-release-root-armed)
      [ "$old_present" = true ] || return 1
      if [ "$release_present" = false ]; then
        observed_root_topology_requires_fsync=true
      fi
      ;;
    retire-old-root-armed)
      if [ "$old_present" = true ] && [ "$retired_present" = false ]; then
        :
      elif [ "$old_present" = false ] && [ "$retired_present" = true ]; then
        committed_recovery=true
        observed_root_topology_requires_fsync=true
      else
        return 1
      fi
      ;;
    committed-cleanup)
      [ "$old_present" = false ] || return 1
      committed_recovery=true
      if [ "$retired_present" = false ]; then
        observed_root_topology_requires_fsync=true
      fi
      ;;
    recovery-create-persistent-root-armed|recovery-remove-staging-armed|\
    recovery-remove-staging-owner-armed|\
    recovery-remove-systemd-attempt-armed|rollback-restored)
      [ "$old_present" = false ] || return 1
      ;;
    recovery-restore-persistent-armed)
      [ "$release_present" = true ] || return 1
      ;;
    recovery-restore-old-root-armed)
      if [ "$old_present" = true ] && [ "$release_present" = false ]; then
        :
      elif [ "$old_present" = false ] && [ "$release_present" = true ]; then
        observed_root_topology_requires_fsync=true
      else
        return 1
      fi
      ;;
  esac

  candidate_root=''
  if [ "$staging_present" = true ]; then
    candidate_root="$STALE_STAGING_ROOT"
  elif [ "$old_present" = true ] && [ "$release_present" = true ]; then
    candidate_root="$STALE_RELEASE_ROOT"
  elif [ "$committed_recovery" = true ] && [ "$release_present" = true ]; then
    candidate_root="$STALE_RELEASE_ROOT"
  fi
  if [ "$committed_recovery" = true ]; then
    if [ "$retired_present" = true ]; then
      source_root="$STALE_RETIRED_ROOT"
    else
      source_root=''
    fi
  elif [ "$old_present" = true ]; then
    source_root="$STALE_OLD_ROOT"
  elif [ "$release_present" = true ]; then
    source_root="$STALE_RELEASE_ROOT"
  else
    return 1
  fi
  if [ -n "$source_root" ]; then
    tree_matches_bound_topology "$source_root" \
      "$STALE_SOURCE_RELEASE_ROOT_IDENTITY" \
      "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT" false || return 1
  fi
  verify_stale_journal_bindings "$committed_recovery" "$candidate_root" \
    || return 1

  if [ "$observed_root_topology_requires_fsync" = true ]; then
    fsync_directories "$(dirname -- "$STALE_RELEASE_ROOT")" || return 1
  fi

  if [ "$committed_recovery" = false ] && [ "$retired_present" = true ]; then
    return 1
  fi
  if [ "$entry_stage" = rollback-restored ] \
    && [ -n "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" ] \
    && { [ -e "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" ] \
      || [ -L "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" ]; }; then
    return 1
  fi
  if [ -n "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" ]; then
    if [ -e "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" ]; then
      [ -d "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" ] \
        && [ ! -L "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" ] || return 1
      if [ -e "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT/armed" ] \
        && [ "$committed_recovery" = false ] \
        && [ "$entry_stage" != rollback-restored ] \
        && [ "$entry_stage" != recovery-remove-systemd-attempt-armed ]; then
        restore_systemd_units_from "$STALE_SYSTEMD_UNIT_DESTINATION" \
          "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" || return 1
      fi
    else
      [ "$entry_stage" = recovery-remove-systemd-attempt-armed ] \
        || [ "$entry_stage" = committed-cleanup ] \
        || [ "$entry_stage" = rollback-restored ] || return 1
    fi
  fi

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
              remove_empty_directory_durably "$STALE_PERSISTENT_ROOT" \
                || return $?
            fi
            write_stale_mutation_state recovery-detach-persistent-armed \
              || return 1
            rename_status=0
            if mv -- "$current_data" "$STALE_PERSISTENT_ROOT"; then
              :
            else
              rename_status=$?
            fi
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
            if [ "$current_state:$persistent_state" = 1:0 ]; then
              fsync_directories "$(dirname -- "$current_data")" \
                "$(dirname -- "$STALE_PERSISTENT_ROOT")" || return 1
              [ "$rename_status" -eq 0 ] || return "$rename_status"
            else
              [ "$rename_status" -ne 0 ] && return "$rename_status"
              return 1
            fi
            ;;
          1:0|2:0)
            if [ "$entry_stage" = recovery-detach-persistent-armed ]; then
              fsync_directories "$(dirname -- "$current_data")" \
                "$(dirname -- "$STALE_PERSISTENT_ROOT")" || return 1
            fi
            ;;
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
          restore-bind-agent-data-armed:0|persistent-restored:0|\
          systemd-backup-preparing:0|systemd-units-armed:0|\
          retire-old-root-armed:0|recovery-detach-persistent-armed:0)
            write_stale_mutation_state recovery-detach-persistent-armed \
              || return 1
            invoke_mount_authority umount "$current_data" || true
            if inspect_stale_mount "$current_data"; then
              mount_state=0
            else
              mount_state=$?
            fi
            [ "$mount_state" -eq 1 ] || return 1
            fsync_directories "$current_data" "$(dirname -- "$current_data")" \
              || return 1
            ;;
          recovery-detach-persistent-armed:1|restore-bind-agent-data-armed:1|\
          persistent-restored:1|systemd-backup-preparing:1|\
          systemd-units-armed:1|retire-old-root-armed:1|root-swapped:1|\
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
      tree_matches_bound_topology "$STALE_OLD_ROOT" \
        "$STALE_SOURCE_RELEASE_ROOT_IDENTITY" \
        "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT" false || return 1
      tree_matches_bound_topology "$STALE_RELEASE_ROOT" \
        "$STALE_CANDIDATE_RELEASE_ROOT_IDENTITY" \
        "$CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT" false || return 1
      [ "$(regular_file_sha256 \
        "$STALE_RELEASE_ROOT/launch-release-manifest.json")" \
        = "$STALE_CANDIDATE_MANIFEST_SHA256" ] || return 1
      [ "$candidate_cleanup_present" = false ] || return 1
      if [ "$candidate_cleanup_owner_present" = true ]; then
        verify_cleanup_owner_marker "$candidate_cleanup_owner" candidate \
          "$STALE_ATTEMPT_ID" "$STALE_CANDIDATE_RELEASE_ROOT_IDENTITY" \
          "$STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256" || return 1
      else
        write_cleanup_owner_marker "$candidate_cleanup_owner" candidate \
          "$STALE_ATTEMPT_ID" "$STALE_CANDIDATE_RELEASE_ROOT_IDENTITY" \
          "$STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256" || return 1
        candidate_cleanup_owner_present=true
      fi
      mv -- "$STALE_RELEASE_ROOT" "$candidate_cleanup_root" || return 1
      fsync_directories "$(dirname -- "$STALE_RELEASE_ROOT")" || return 1
      [ ! -e "$STALE_RELEASE_ROOT" ] && [ ! -L "$STALE_RELEASE_ROOT" ] \
        || return 1
      release_present=false
      candidate_cleanup_present=true
    fi
    if [ "$candidate_cleanup_present" = true ]; then
      [ "$candidate_cleanup_owner_present" = true ] || return 1
      verify_cleanup_owner_marker "$candidate_cleanup_owner" candidate \
        "$STALE_ATTEMPT_ID" "$STALE_CANDIDATE_RELEASE_ROOT_IDENTITY" \
        "$STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256" || return 1
      tree_matches_bound_topology "$candidate_cleanup_root" \
        "$STALE_CANDIDATE_RELEASE_ROOT_IDENTITY" \
        "$CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT" true || return 1
      invoke_rm -rf -- "$candidate_cleanup_root" || return 1
      [ ! -e "$candidate_cleanup_root" ] && [ ! -L "$candidate_cleanup_root" ] \
        || return 1
      fsync_directories "$(dirname -- "$STALE_RELEASE_ROOT")" || return 1
      candidate_cleanup_present=false
    fi
    if [ "$candidate_cleanup_owner_present" = true ]; then
      fsync_directories "$(dirname -- "$STALE_RELEASE_ROOT")" || return 1
      remove_file_durably "$candidate_cleanup_owner" || return 1
      [ ! -e "$candidate_cleanup_owner" ] \
        && [ ! -L "$candidate_cleanup_owner" ] || return 1
      candidate_cleanup_owner_present=false
    fi
    [ "$release_present" = false ] || return 1
    tree_matches_bound_topology "$STALE_OLD_ROOT" \
      "$STALE_SOURCE_RELEASE_ROOT_IDENTITY" \
      "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT" false || return 1
    write_stale_mutation_state recovery-restore-old-root-armed || return 1
    mv -- "$STALE_OLD_ROOT" "$STALE_RELEASE_ROOT" || return 1
    fsync_directories "$(dirname -- "$STALE_RELEASE_ROOT")" || return 1
    tree_matches_bound_topology "$STALE_RELEASE_ROOT" \
      "$STALE_SOURCE_RELEASE_ROOT_IDENTITY" \
      "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT" false || return 1
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
        case "$entry_stage" in
          recovery-restore-persistent-armed|recovery-create-persistent-root-armed)
            fsync_directories "$(dirname -- "$STALE_PERSISTENT_ROOT")" \
              "$(dirname -- "$current_data")" || return 1
            ;;
        esac
        write_stale_mutation_state recovery-create-persistent-root-armed \
          || return 1
        mkdir -- "$STALE_PERSISTENT_ROOT" || return 1
        fsync_directories "$(dirname -- "$STALE_PERSISTENT_ROOT")" \
          "$STALE_PERSISTENT_ROOT" || return 1
        ;;
      0:2)
        if [ "$entry_stage" = recovery-create-persistent-root-armed ]; then
          fsync_directories "$(dirname -- "$STALE_PERSISTENT_ROOT")" \
            "$STALE_PERSISTENT_ROOT" "$(dirname -- "$current_data")" || return 1
        fi
        ;;
      1:0)
        [ -d "$(dirname -- "$current_data")" ] \
          && [ ! -L "$(dirname -- "$current_data")" ] || return 1
        write_stale_mutation_state recovery-restore-persistent-armed || return 1
        mv -- "$STALE_PERSISTENT_ROOT" "$current_data" || return 1
        fsync_directories "$(dirname -- "$STALE_PERSISTENT_ROOT")" \
          "$(dirname -- "$current_data")" || return 1
        write_stale_mutation_state recovery-create-persistent-root-armed \
          || return 1
        mkdir -- "$STALE_PERSISTENT_ROOT" || return 1
        fsync_directories "$(dirname -- "$STALE_PERSISTENT_ROOT")" \
          "$STALE_PERSISTENT_ROOT" || return 1
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
        invoke_mount_authority mount --bind "$STALE_PERSISTENT_ROOT" "$current_data" \
          || return 1
        fsync_directories "$current_data" "$(dirname -- "$current_data")" \
          || return 1
        inspect_stale_mount "$current_data" || return 1
        mount_verified=true
        ;;
      *) return 1 ;;
    esac
    [ "$mount_verified" = true ] || return 1
    tree_matches_snapshot "$current_data" "$SNAPSHOT_BEFORE" || return 1
  fi

  if [ "$committed_recovery" = true ]; then
    [ -f "$STALE_RELEASE_ROOT/launch-release-manifest.json" ] \
      && [ ! -L "$STALE_RELEASE_ROOT/launch-release-manifest.json" ] \
      || return 1
    verify_installed_release_authority \
      "$STALE_RELEASE_ROOT" "$STALE_PERSISTENT_ROOT" \
      "$STALE_SYSTEMD_UNIT_DESTINATION" "$EVIDENCE_DIR/installed-recovery" \
      "$EVIDENCE_DIR/findmnt-recovery.json" "$STALE_LOCAL_REHEARSAL" \
      || return 1
    invoke_pinned_executable unit-verify "$UNIT_VERIFY_HOOK_SHA256" -- \
      --unit-root "$STALE_SYSTEMD_UNIT_DESTINATION" \
      --manifest "$STALE_RELEASE_ROOT/launch-release-manifest.json" \
      || return 1
    write_stale_mutation_state committed-cleanup || return 1
  fi

  local stage_owner_valid=false
  if [ -e "$stale_stage_owner" ]; then
    verify_observed_private_staging_owner_marker "$stale_stage_owner" \
      "$STALE_STAGING_ROOT" "$STALE_ATTEMPT_ID" "$STALE_PID" \
      "$STALE_CANDIDATE_RELEASE_ROOT_IDENTITY" || return 1
    stage_owner_valid=true
  fi
  if [ -e "$STALE_STAGING_ROOT" ] || [ -L "$STALE_STAGING_ROOT" ]; then
    [ -d "$STALE_STAGING_ROOT" ] && [ ! -L "$STALE_STAGING_ROOT" ] || return 1
    [ "$stage_owner_valid" = true ] || return 1
    if [ "$committed_recovery" = false ]; then
      write_stale_mutation_state recovery-remove-staging-armed || return 1
    fi
    tree_matches_bound_topology "$STALE_STAGING_ROOT" \
      "$STALE_CANDIDATE_RELEASE_ROOT_IDENTITY" \
      "$CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT" false || return 1
    [ "$(regular_file_sha256 \
      "$STALE_STAGING_ROOT/launch-release-manifest.json")" \
      = "$STALE_CANDIDATE_MANIFEST_SHA256" ] || return 1
    [ "$staging_delete_present" = false ] || return 1
    if [ "$staging_delete_owner_present" = true ]; then
      verify_cleanup_owner_marker "$staging_delete_owner" staging \
        "$STALE_ATTEMPT_ID" "$STALE_CANDIDATE_RELEASE_ROOT_IDENTITY" \
        "$STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256" || return 1
    else
      write_cleanup_owner_marker "$staging_delete_owner" staging \
        "$STALE_ATTEMPT_ID" "$STALE_CANDIDATE_RELEASE_ROOT_IDENTITY" \
        "$STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256" || return 1
      staging_delete_owner_present=true
    fi
    mv -- "$STALE_STAGING_ROOT" "$staging_delete_root" || return 1
    fsync_directories "$(dirname -- "$STALE_STAGING_ROOT")" || return 1
    [ ! -e "$STALE_STAGING_ROOT" ] && [ ! -L "$STALE_STAGING_ROOT" ] \
      || return 1
    staging_delete_present=true
  fi
  if [ "$staging_delete_present" = true ]; then
    [ "$staging_delete_owner_present" = true ] || return 1
    verify_cleanup_owner_marker "$staging_delete_owner" staging \
      "$STALE_ATTEMPT_ID" "$STALE_CANDIDATE_RELEASE_ROOT_IDENTITY" \
      "$STALE_CANDIDATE_RELEASE_TOPOLOGY_SHA256" || return 1
    tree_matches_bound_topology "$staging_delete_root" \
      "$STALE_CANDIDATE_RELEASE_ROOT_IDENTITY" \
      "$CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT" true || return 1
    invoke_rm -rf -- "$staging_delete_root" || return 1
    [ ! -e "$staging_delete_root" ] && [ ! -L "$staging_delete_root" ] \
      || return 1
    fsync_directories "$(dirname -- "$STALE_STAGING_ROOT")" || return 1
    staging_delete_present=false
  fi
  if [ "$staging_delete_owner_present" = true ]; then
    [ "$staging_delete_present" = false ] || return 1
    remove_file_durably "$staging_delete_owner" || return 1
    [ ! -e "$staging_delete_owner" ] && [ ! -L "$staging_delete_owner" ] \
      || return 1
    staging_delete_owner_present=false
  fi
  if [ -e "$stale_stage_owner" ] || [ -L "$stale_stage_owner" ]; then
    [ "$stage_owner_valid" = true ] || return 1
    if [ "$committed_recovery" = false ]; then
      write_stale_mutation_state recovery-remove-staging-owner-armed || return 1
    fi
    remove_file_durably "$stale_stage_owner" || return 1
    [ ! -e "$stale_stage_owner" ] && [ ! -L "$stale_stage_owner" ] \
      || return 1
    fsync_directories "$(dirname -- "$stale_stage_owner")" || return 1
  elif [ "$entry_stage" = recovery-remove-staging-owner-armed ]; then
    fsync_directories "$(dirname -- "$stale_stage_owner")" || return 1
  fi
  if [ "$committed_recovery" = true ]; then
    if [ -e "$STALE_RETIRED_ROOT" ] || [ -L "$STALE_RETIRED_ROOT" ]; then
      [ -d "$STALE_RETIRED_ROOT" ] && [ ! -L "$STALE_RETIRED_ROOT" ] \
        || return 1
      tree_matches_bound_topology "$STALE_RETIRED_ROOT" \
        "$STALE_SOURCE_RELEASE_ROOT_IDENTITY" \
        "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT" false || return 1
      [ "$retired_cleanup_present" = false ] || return 1
      if [ "$retired_cleanup_owner_present" = true ]; then
        verify_cleanup_owner_marker "$retired_cleanup_owner" retired \
          "$STALE_ATTEMPT_ID" "$STALE_SOURCE_RELEASE_ROOT_IDENTITY" \
          "$STALE_SOURCE_RELEASE_TOPOLOGY_SHA256" || return 1
      else
        write_cleanup_owner_marker "$retired_cleanup_owner" retired \
          "$STALE_ATTEMPT_ID" "$STALE_SOURCE_RELEASE_ROOT_IDENTITY" \
          "$STALE_SOURCE_RELEASE_TOPOLOGY_SHA256" || return 1
        retired_cleanup_owner_present=true
      fi
      mv -- "$STALE_RETIRED_ROOT" "$retired_cleanup_root" || return 1
      fsync_directories "$(dirname -- "$STALE_RETIRED_ROOT")" || return 1
      [ ! -e "$STALE_RETIRED_ROOT" ] && [ ! -L "$STALE_RETIRED_ROOT" ] \
        || return 1
      retired_cleanup_present=true
      retired_present=false
    fi
    [ ! -e "$STALE_RETIRED_ROOT" ] && [ ! -L "$STALE_RETIRED_ROOT" ] \
      || return 1
    if [ "$retired_cleanup_present" = true ]; then
      [ "$retired_cleanup_owner_present" = true ] || return 1
      verify_cleanup_owner_marker "$retired_cleanup_owner" retired \
        "$STALE_ATTEMPT_ID" "$STALE_SOURCE_RELEASE_ROOT_IDENTITY" \
        "$STALE_SOURCE_RELEASE_TOPOLOGY_SHA256" || return 1
      tree_matches_bound_topology "$retired_cleanup_root" \
        "$STALE_SOURCE_RELEASE_ROOT_IDENTITY" \
        "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT" true || return 1
      invoke_rm -rf -- "$retired_cleanup_root" || return 1
      [ ! -e "$retired_cleanup_root" ] && [ ! -L "$retired_cleanup_root" ] \
        || return 1
      fsync_directories "$(dirname -- "$STALE_RETIRED_ROOT")" || return 1
      retired_cleanup_present=false
    fi
    if [ "$retired_cleanup_owner_present" = true ]; then
      [ "$retired_cleanup_present" = false ] || return 1
      remove_file_durably "$retired_cleanup_owner" || return 1
      [ ! -e "$retired_cleanup_owner" ] \
        && [ ! -L "$retired_cleanup_owner" ] || return 1
      retired_cleanup_owner_present=false
    fi
  fi
  if [ -n "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" ] \
    && [ "$entry_stage" != rollback-restored ]; then
    if [ "$committed_recovery" = false ]; then
      write_stale_mutation_state recovery-remove-systemd-attempt-armed || return 1
    fi
    remove_systemd_unit_attempt_root "$STALE_SYSTEMD_UNIT_ATTEMPT_ROOT" \
      || return 1
  fi
  clear_mutation_state
}

record_install_lock() {
  local status="$1"
  local code="$2"
  invoke_python - "$EVIDENCE_DIR/install-lock.json" "$status" "$code" \
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

EXECUTABLE_PIN_ROOT=''
EXECUTABLE_PIN_PARENT=''
PINNED_MOUNT_AUTHORITY=''
PINNED_PYTHON_DEPENDENCY_HOOK=''
PINNED_NUXT_DEPENDENCY_HOOK=''
PINNED_UNIT_VERIFY_HOOK=''
PINNED_BASH_EXECUTOR=''
MOUNT_AUTHORITY_SHA256=''
PYTHON_DEPENDENCY_HOOK_SHA256=''
NUXT_DEPENDENCY_HOOK_SHA256=''
UNIT_VERIFY_HOOK_SHA256=''
BASH_EXECUTOR_SHA256=''

sweep_stale_executable_pin_roots() {
  local artifact
  for artifact in "$EXECUTABLE_PIN_PARENT"/vl360-executable-pins.*; do
    [ -e "$artifact" ] || [ -L "$artifact" ] || continue
    [ -d "$artifact" ] && [ ! -L "$artifact" ] || return 1
    if private_attempt_artifact_is_stale "$artifact"; then
      remove_private_directory "$artifact" "$EXECUTABLE_PIN_PARENT" || return 1
    fi
  done
}

cleanup_executable_pin_root() {
  [ -n "$EXECUTABLE_PIN_ROOT" ] || return 0
  local parent name
  parent="$(dirname -- "$EXECUTABLE_PIN_ROOT")"
  name="$(basename -- "$EXECUTABLE_PIN_ROOT")"
  [ "$parent" = "$EXECUTABLE_PIN_PARENT" ] || return 1
  case "$name" in vl360-executable-pins.*) ;; *) return 1 ;; esac
  lock_is_owned_by_attempt "$EXECUTABLE_PIN_ROOT" || return 1
  remove_private_directory "$EXECUTABLE_PIN_ROOT" "$EXECUTABLE_PIN_PARENT" \
    || return $?
  EXECUTABLE_PIN_ROOT=''
}

cleanup_preinstall_authorities() {
  local primary_status=$?
  local cleanup_status=0
  local current_status
  trap - EXIT
  set +e
  cleanup_executable_pin_root || cleanup_status=$?
  release_all_install_locks
  current_status=$?
  if [ "$current_status" -ne 0 ] && [ "$cleanup_status" -eq 0 ]; then
    cleanup_status="$current_status"
  fi
  [ "$primary_status" -ne 0 ] || primary_status="$cleanup_status"
  exit "$primary_status"
}

LOCK_EVIDENCE_ENABLED=true
trap cleanup_preinstall_authorities EXIT
if [ "$PENDING_STALE_RECOVERY" = true ] && ! load_stale_install_state; then
  record_install_lock recovery-required 2 || true
  LOCK_TERMINAL_RECORDED=true
  die 'stale-install-recovery-required'
fi
AUTHORITY_ROLE_ARGS=(
  evidence "$EVIDENCE_DIR"
  release "$RELEASE_ROOT"
  persistent "$PERSISTENT_AGENT_DATA_ROOT"
  systemd "$SYSTEMD_UNIT_DESTINATION"
)
if [ "$PENDING_STALE_RECOVERY" = true ]; then
  AUTHORITY_ROLE_ARGS+=(
    release "$STALE_RELEASE_ROOT"
    persistent "$STALE_PERSISTENT_ROOT"
    systemd "$STALE_SYSTEMD_UNIT_DESTINATION"
  )
fi
if preflight_authority_role_collisions "${AUTHORITY_ROLE_ARGS[@]}"; then
  :
else
  authority_role_status=$?
  if [ "$authority_role_status" -eq 12 ]; then
    record_install_lock rejected 2 || true
    LOCK_TERMINAL_RECORDED=true
    die 'install-authority-role-collision'
  fi
  record_install_lock acquire-failed 2 || true
  LOCK_TERMINAL_RECORDED=true
  die 'install-lock-acquire-failed'
fi

executable_authority_has_symlink_component() {
  local candidate="$1"
  local parent
  while [ "$candidate" != / ] && [ "$candidate" != . ]; do
    [ ! -L "$candidate" ] || return 0
    parent="$(dirname -- "$candidate")"
    [ "$parent" != "$candidate" ] || break
    candidate="$parent"
  done
  return 1
}

for executable_authority in "$PYTHON_DEPENDENCY_HOOK" \
  "$NUXT_DEPENDENCY_HOOK" "$UNIT_VERIFY_HOOK"; do
  if executable_authority_has_symlink_component "$executable_authority"; then
    die 'runtime-hook-authority-required: executable-authority-required'
  fi
done
if [ -n "$MOUNT_AUTHORITY" ] \
  && executable_authority_has_symlink_component "$MOUNT_AUTHORITY"; then
  die 'live-mount-authority-required: executable-authority-required'
fi

if VL360_EXECUTABLE_LIVE_MODE="$([ "$LOCAL_REHEARSAL" = true ] \
  && printf false || printf true)" validate_executable_authority_sources; then
  :
else
  executable_status=$?
  case "$executable_status" in
    20) die 'runtime-hook-authority-required: executable-authority-required' ;;
    21) die 'executable-authority-namespace-overlap' ;;
    22) die 'live-mount-authority-required: executable-authority-required' ;;
    *) die 'executable-authority-admission-failed' ;;
  esac
fi

EXECUTABLE_PIN_PARENT="$(CDPATH= cd -- "${TMPDIR:-/tmp}" && pwd -P)" \
  || die 'executable-authority-pin-failed'
sweep_stale_executable_pin_roots || die 'executable-authority-pin-cleanup-failed'
EXECUTABLE_PIN_ROOT="$(mktemp -d \
  "$EXECUTABLE_PIN_PARENT/vl360-executable-pins.$$.${PROCESS_START_IDENTITY}.XXXXXXXX")" \
  || die 'executable-authority-pin-failed'
chmod 0700 -- "$EXECUTABLE_PIN_ROOT" || die 'executable-authority-pin-failed'
write_lock_owner "$EXECUTABLE_PIN_ROOT" || die 'executable-authority-pin-failed'
fsync_directories "$EXECUTABLE_PIN_ROOT" || die 'executable-authority-pin-failed'
validate_executable_pin_root "$EXECUTABLE_PIN_ROOT" \
  || die 'executable-authority-pin-namespace-overlap'
if executable_pin_digests="$(pin_executable_authorities)"; then
  IFS=$'\t' read -r MOUNT_AUTHORITY_SHA256 PYTHON_DEPENDENCY_HOOK_SHA256 \
    NUXT_DEPENDENCY_HOOK_SHA256 UNIT_VERIFY_HOOK_SHA256 BASH_EXECUTOR_SHA256 \
    <<< "$executable_pin_digests"
else
  die 'executable-authority-pin-failed'
fi
[ "$MOUNT_AUTHORITY_SHA256" != - ] || MOUNT_AUTHORITY_SHA256=''
[ "$BASH_EXECUTOR_SHA256" != - ] || BASH_EXECUTOR_SHA256=''
[ -n "$PYTHON_DEPENDENCY_HOOK_SHA256" ] \
  && [ -n "$NUXT_DEPENDENCY_HOOK_SHA256" ] \
  && [ -n "$UNIT_VERIFY_HOOK_SHA256" ] \
  || die 'executable-authority-pin-failed'
if [[ "$OSTYPE" = linux* ]]; then
  [ -n "$BASH_EXECUTOR_SHA256" ] || die 'executable-authority-pin-failed'
fi
PINNED_PYTHON_DEPENDENCY_HOOK="$EXECUTABLE_PIN_ROOT/python-dependency"
PINNED_NUXT_DEPENDENCY_HOOK="$EXECUTABLE_PIN_ROOT/nuxt-dependency"
PINNED_UNIT_VERIFY_HOOK="$EXECUTABLE_PIN_ROOT/unit-verify"
if [ -n "$BASH_EXECUTOR_SHA256" ]; then
  PINNED_BASH_EXECUTOR="$EXECUTABLE_PIN_ROOT/bash-interpreter"
fi
PYTHON_DEPENDENCY_HOOK="$PINNED_PYTHON_DEPENDENCY_HOOK"
NUXT_DEPENDENCY_HOOK="$PINNED_NUXT_DEPENDENCY_HOOK"
UNIT_VERIFY_HOOK="$PINNED_UNIT_VERIFY_HOOK"
if [ "$LOCAL_REHEARSAL" != true ]; then
  [ -n "$MOUNT_AUTHORITY_SHA256" ] || die 'executable-authority-pin-failed'
  PINNED_MOUNT_AUTHORITY="$EXECUTABLE_PIN_ROOT/mount"
  MOUNT_AUTHORITY="$PINNED_MOUNT_AUTHORITY"
fi

run_with_sanitized_executable_environment() {
  local -a command=(
    "$ENV_EXECUTOR"
    -u BASH_ENV
    -u ENV
    -u BASHOPTS
    -u SHELLOPTS
    -u BASH_COMPAT
    -u POSIXLY_CORRECT
  )
  local entry name
  while IFS= read -r -d '' entry; do
    name="${entry%%=*}"
    case "$name" in
      BASH_FUNC_*%%) command+=(-u "$name") ;;
    esac
  done < <("$ENV_EXECUTOR" -0)
  "${command[@]}" "$@"
}

invoke_pinned_executable() {
  local role="$1"
  local expected_sha256="$2"
  local path platform_name executor_source launch_kind
  shift 2
  [ "${1:-}" = -- ] || {
    printf 'install_closed_release: executable-authority-arguments-invalid\n' >&2
    return 126
  }
  shift
  case "$role" in
    mount) path="$PINNED_MOUNT_AUTHORITY" ;;
    python-dependency) path="$PINNED_PYTHON_DEPENDENCY_HOOK" ;;
    nuxt-dependency) path="$PINNED_NUXT_DEPENDENCY_HOOK" ;;
    unit-verify) path="$PINNED_UNIT_VERIFY_HOOK" ;;
    *)
      printf 'install_closed_release: executable-authority-role-invalid\n' >&2
      return 126
      ;;
  esac
  [ -n "$path" ] || {
    printf 'install_closed_release: executable-authority-role-unavailable\n' >&2
    return 126
  }
  platform_name="$(invoke_python -c 'import os; print(os.name)')" || {
    printf 'install_closed_release: executable-authority-platform-unavailable\n' >&2
    return 126
  }
  if [ "$platform_name" = nt ]; then
    if [ "$LOCAL_REHEARSAL" != true ]; then
      printf 'install_closed_release: executable-authority-windows-fallback-forbidden\n' >&2
      return 126
    fi
    if ! verify_pinned_executable "$path" "$expected_sha256"; then
      printf 'install_closed_release: executable-authority-digest-mismatch\n' >&2
      return 126
    fi
    launch_kind="$(invoke_python - "$path" <<'PY'
from pathlib import Path
import sys

prefix = Path(sys.argv[1]).read_bytes()[:4096]
if not prefix.startswith(b"#!"):
    print("native")
    raise SystemExit(0)
line_end = prefix.find(b"\n")
if line_end < 0:
    raise SystemExit(1)
shebang = prefix[:line_end].rstrip(b"\r")
if shebang in (b"#!/usr/bin/env bash", b"#!/bin/bash", b"#!/usr/bin/bash"):
    print("bash")
elif shebang in (b"#!/bin/sh", b"#!/usr/bin/python3", b"#!/usr/local/bin/python3"):
    print("native")
else:
    raise SystemExit(1)
PY
    )" || {
      printf 'install_closed_release: executable-authority-shebang-forbidden\n' >&2
      return 126
    }
    if [ "$launch_kind" = bash ]; then
      if ! verify_pinned_executable "$BASH_EXECUTOR" "$BASH_EXECUTOR_SHA256"; then
        printf 'install_closed_release: executable-authority-digest-mismatch\n' >&2
        return 126
      fi
      run_with_sanitized_executable_environment \
        "$BASH_EXECUTOR" -- "$path" "$@"
    else
      run_with_sanitized_executable_environment "$path" "$@"
    fi
    return $?
  fi
  if [ "$platform_name" != posix ]; then
    printf 'install_closed_release: executable-authority-fd-exec-unavailable\n' >&2
    return 126
  fi
  IFS= read -r -d '' executor_source <<'VL360_PINNED_EXECUTOR_PY' || true
from hashlib import sha256
import fcntl
import os
import stat
import sys


ROLE_FILENAMES = {
    "mount": "mount",
    "python-dependency": "python-dependency",
    "nuxt-dependency": "nuxt-dependency",
    "unit-verify": "unit-verify",
    "bash-interpreter": "bash-interpreter",
}
BASH_SHEBANGS = {
    b"#!/bin/bash",
    b"#!/usr/bin/bash",
}
ENV_BASH_SHEBANG = b"#!/usr/bin/env bash"
APPROVED_SHEBANGS = {
    b"#!/bin/sh",
    b"#!/usr/bin/python3",
    b"#!/usr/local/bin/python3",
}
UNSAFE_ENVIRONMENT_KEYS = {
    "BASH_ENV",
    "ENV",
    "BASHOPTS",
    "SHELLOPTS",
    "BASH_COMPAT",
    "POSIXLY_CORRECT",
}


def fail(reason):
    print(f"install_closed_release: {reason}", file=sys.stderr)
    raise SystemExit(126)


def require_linux_fd_exec():
    seals = (
        "F_ADD_SEALS",
        "F_GET_SEALS",
        "F_SEAL_WRITE",
        "F_SEAL_GROW",
        "F_SEAL_SHRINK",
        "F_SEAL_SEAL",
    )
    if os.name != "posix" or not sys.platform.startswith("linux"):
        fail("executable-authority-fd-exec-unavailable")
    if not hasattr(os, "memfd_create") or not hasattr(os, "MFD_ALLOW_SEALING"):
        fail("executable-authority-fd-exec-unavailable")
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        fail("executable-authority-fd-exec-unavailable")
    if os.open not in os.supports_dir_fd or os.execve not in os.supports_fd:
        fail("executable-authority-fd-exec-unavailable")
    if any(not hasattr(fcntl, name) for name in seals):
        fail("executable-authority-fd-exec-unavailable")


def write_all(descriptor, raw):
    offset = 0
    while offset < len(raw):
        written = os.write(descriptor, raw[offset:])
        if written <= 0:
            fail("executable-authority-memfd-copy-failed")
        offset += written


def validate_script_shebang(prefix):
    if not prefix.startswith(b"#!"):
        return "native"
    line_end = prefix.find(b"\n")
    if line_end < 0:
        fail("executable-authority-shebang-forbidden")
    shebang = prefix[:line_end].rstrip(b"\r")
    if shebang == ENV_BASH_SHEBANG or shebang in BASH_SHEBANGS:
        return "bash"
    if shebang not in APPROVED_SHEBANGS:
        fail("executable-authority-shebang-forbidden")
    return "native"


def sanitized_environment():
    return {
        key: value
        for key, value in os.environ.items()
        if key not in UNSAFE_ENVIRONMENT_KEYS
        and not (key.startswith("BASH_FUNC_") and key.endswith("%%"))
    }


def open_canonical_executor(pin_root, role_filename):
    root_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    pin_root_fd = None
    pin_fd = None
    try:
        pin_root_fd = os.open(pin_root, root_flags)
        root_observed = os.fstat(pin_root_fd)
        if not stat.S_ISDIR(root_observed.st_mode):
            fail("executable-authority-pin-root-invalid")
        if stat.S_IMODE(root_observed.st_mode) != 0o700:
            fail("executable-authority-pin-root-invalid")
        pin_fd = os.open(role_filename, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=pin_root_fd)
    except OSError:
        fail("executable-authority-pin-invalid")
    finally:
        if pin_root_fd is not None:
            os.close(pin_root_fd)
    observed = os.fstat(pin_fd)
    if not stat.S_ISREG(observed.st_mode) or stat.S_IMODE(observed.st_mode) != 0o500:
        os.close(pin_fd)
        fail("executable-authority-pin-invalid")
    return pin_fd


def seal_memfd(memfd_fd):
    seals = (
        fcntl.F_SEAL_WRITE
        | fcntl.F_SEAL_GROW
        | fcntl.F_SEAL_SHRINK
        | fcntl.F_SEAL_SEAL
    )
    fcntl.fcntl(memfd_fd, fcntl.F_ADD_SEALS, seals)
    observed = fcntl.fcntl(memfd_fd, fcntl.F_GET_SEALS)
    if observed & seals != seals:
        fail("executable-authority-memfd-seal-failed")


def copy_verified_to_memfd(pin_fd, expected_sha256, role, *, inspect_shebang=True):
    memfd_fd = os.memfd_create(f"vl360-{role}", os.MFD_ALLOW_SEALING)
    digest = sha256()
    prefix = bytearray()
    while True:
        chunk = os.read(pin_fd, 1024 * 1024)
        if not chunk:
            break
        if len(prefix) < 4096:
            prefix.extend(chunk[: 4096 - len(prefix)])
        digest.update(chunk)
        write_all(memfd_fd, chunk)
    if digest.hexdigest() != expected_sha256:
        os.close(memfd_fd)
        fail("executable-authority-digest-mismatch")
    launch_kind = validate_script_shebang(bytes(prefix)) if inspect_shebang else "native"
    os.lseek(memfd_fd, 0, os.SEEK_SET)
    seal_memfd(memfd_fd)
    return memfd_fd, launch_kind


def main():
    require_linux_fd_exec()
    if len(sys.argv) < 8 or sys.argv[7] != "--":
        fail("executable-authority-arguments-invalid")
    role, expected_sha256, pin_root, pin_path, bash_sha256, bash_path = sys.argv[1:7]
    role_filename = ROLE_FILENAMES.get(role)
    if role_filename is None or role_filename == "bash-interpreter":
        fail("executable-authority-role-invalid")
    pin_fd = open_canonical_executor(pin_root, role_filename)
    try:
        memfd_fd, launch_kind = copy_verified_to_memfd(pin_fd, expected_sha256, role)
    finally:
        os.close(pin_fd)
    argv = [pin_path, *sys.argv[8:]]
    env = sanitized_environment()
    os.set_inheritable(memfd_fd, True)
    if not os.get_inheritable(memfd_fd):
        os.close(memfd_fd)
        fail("executable-authority-fd-exec-unavailable")
    if launch_kind == "bash":
        bash_fd = open_canonical_executor(pin_root, ROLE_FILENAMES["bash-interpreter"])
        try:
            bash_memfd_fd, _ = copy_verified_to_memfd(
                bash_fd,
                bash_sha256,
                "bash-interpreter",
                inspect_shebang=False,
            )
        finally:
            os.close(bash_fd)
        bash_fd = bash_memfd_fd
        os.set_inheritable(bash_fd, True)
        if not os.get_inheritable(bash_fd):
            os.close(bash_fd)
            os.close(memfd_fd)
            fail("executable-authority-fd-exec-unavailable")
        argv = [
            bash_path,
            "--",
            f"/proc/self/fd/{memfd_fd}",
            *sys.argv[8:],
        ]
        try:
            os.execve(bash_fd, argv, env)
        except (OSError, TypeError, ValueError):
            os.close(bash_fd)
            os.close(memfd_fd)
            fail("executable-authority-fd-exec-failed")
    try:
        os.execve(memfd_fd, argv, env)
    except (OSError, TypeError, ValueError):
        os.close(memfd_fd)
        fail("executable-authority-fd-exec-failed")


if __name__ == "__main__":
    main()
VL360_PINNED_EXECUTOR_PY
  invoke_python -c "$executor_source" "$role" "$expected_sha256" \
    "$EXECUTABLE_PIN_ROOT" "$path" "$BASH_EXECUTOR_SHA256" \
    "$BASH_EXECUTOR" -- "$@"
}

invoke_mount_authority() {
  [ -n "$PINNED_MOUNT_AUTHORITY" ] && [ -n "$MOUNT_AUTHORITY_SHA256" ] \
    || return 126
  invoke_pinned_executable mount "$MOUNT_AUTHORITY_SHA256" -- "$@"
}

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
CURRENT_SYSTEMD_KEY=''
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
    systemd) CURRENT_SYSTEMD_KEY="$target_key" ;;
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
  for target_kind in release persistent systemd; do
    case "$target_kind" in
      release)
        target_authority="$STALE_RELEASE_ROOT"
        target_key="$STALE_RELEASE_KEY"
        ;;
      persistent)
        target_authority="$STALE_PERSISTENT_ROOT"
        target_key="$STALE_PERSISTENT_KEY"
        ;;
      systemd)
        target_authority="$STALE_SYSTEMD_UNIT_DESTINATION"
        target_key="$STALE_SYSTEMD_KEY"
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
sweep_stale_staging_attempts || die 'stale-staging-cleanup-required'
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
RETIRED_ROOT=''
CANDIDATE_CLEANUP_ROOT=''
STAGING_DELETE_ROOT=''
RETIRED_CLEANUP_ROOT=''
CANDIDATE_CLEANUP_OWNER=''
STAGING_DELETE_OWNER=''
RETIRED_CLEANUP_OWNER=''
STAGING_OWNER_MARKER=''
STAGING_ROOT_IDENTITY=''
STAGING_OWNER_NONCE=''
STAGING_CLEANUP_ARMED=false
cleanup_pinned_archive() {
  [ -n "$PINNED_ARCHIVE_ROOT" ] || return 0
  local parent name
  parent="$(dirname -- "$PINNED_ARCHIVE_ROOT")"
  name="$(basename -- "$PINNED_ARCHIVE_ROOT")"
  [ "$parent" = "$EVIDENCE_DIR" ] || return 1
  case "$name" in .closed-archive-attempt.*) ;; *) return 1 ;; esac
  remove_private_directory "$PINNED_ARCHIVE_ROOT" "$EVIDENCE_DIR" \
    || return $?
  PINNED_ARCHIVE_ROOT=''
}
cleanup_private_staging() {
  [ "$STAGING_CLEANUP_ARMED" = true ] || return 0
  local expected="$RELEASE_PARENT/.${RELEASE_NAME}.closed-stage.$$"
  [ "$STAGING_ROOT" = "$expected" ] || return 1
  [ "$STAGING_OWNER_MARKER" = "$STAGING_ROOT.owner" ] || return 1
  verify_private_staging_owner_marker "$STAGING_OWNER_MARKER" \
    "$STAGING_ROOT" "$ATTEMPT_ID" "$$" "$STAGING_ROOT_IDENTITY" \
    "$STAGING_OWNER_NONCE" || return 1
  if [ -e "$STAGING_ROOT" ] || [ -L "$STAGING_ROOT" ]; then
    [ -d "$STAGING_ROOT" ] && [ ! -L "$STAGING_ROOT" ] || return 1
    remove_private_directory "$STAGING_ROOT" "$RELEASE_PARENT" || return $?
  fi
  [ ! -e "$STAGING_ROOT" ] && [ ! -L "$STAGING_ROOT" ] || return 1
  remove_file_durably "$STAGING_OWNER_MARKER" >/dev/null 2>&1 || return $?
  [ ! -e "$STAGING_OWNER_MARKER" ] && [ ! -L "$STAGING_OWNER_MARKER" ] \
    || return 1
  STAGING_CLEANUP_ARMED=false
}
cleanup_attempt_authorities() {
  local cleanup_status=0
  local current_status
  cleanup_private_staging || cleanup_status=$?
  cleanup_pinned_archive
  current_status=$?
  if [ "$current_status" -ne 0 ]; then
    [ "$cleanup_status" -ne 0 ] || cleanup_status="$current_status"
  fi
  cleanup_executable_pin_root
  current_status=$?
  if [ "$current_status" -ne 0 ]; then
    [ "$cleanup_status" -ne 0 ] || cleanup_status="$current_status"
  fi
  release_all_install_locks
  current_status=$?
  if [ "$current_status" -ne 0 ]; then
    [ "$cleanup_status" -ne 0 ] || cleanup_status="$current_status"
  fi
  return "$cleanup_status"
}
cleanup_attempt_trap() {
  local primary_status=$?
  local cleanup_status=0
  trap - EXIT
  set +e
  cleanup_attempt_authorities || cleanup_status=$?
  [ "$primary_status" -ne 0 ] || primary_status="$cleanup_status"
  exit "$primary_status"
}
trap cleanup_attempt_trap EXIT

# Snapshot the candidate into a private authority, then verify and extract only
# those pinned bytes so replacing the caller-owned archive cannot win a TOCTOU race.
PINNED_ARCHIVE_ROOT="$(mktemp -d "$EVIDENCE_DIR/.closed-archive-attempt.XXXXXXXX")"
PINNED_ARCHIVE="$PINNED_ARCHIVE_ROOT/$(basename -- "$ARCHIVE")"
PINNED_ARCHIVE_DIGEST_FILE="$PINNED_ARCHIVE_ROOT/$(basename -- "$ARCHIVE_DIGEST_FILE")"
cp -- "$ARCHIVE" "$PINNED_ARCHIVE"
cp -- "$ARCHIVE_DIGEST_FILE" "$PINNED_ARCHIVE_DIGEST_FILE"
chmod 0600 -- "$PINNED_ARCHIVE" "$PINNED_ARCHIVE_DIGEST_FILE"

# Integrity and manifest verification must complete before extraction or mutation.
invoke_python "$VERIFY_SCRIPT" \
  --archive "$PINNED_ARCHIVE" --archive-digest-file "$PINNED_ARCHIVE_DIGEST_FILE" \
  --require-closed --evidence-dir "$EVIDENCE_DIR/package"
PINNED_ARCHIVE_SHA256="$(regular_file_sha256 "$PINNED_ARCHIVE")" \
  || die 'pinned-archive-digest-failed'
if [ -n "$MIGRATION_GATE_EVIDENCE" ]; then
  MIGRATION_GATE_EVIDENCE_PIN="$EVIDENCE_DIR/migration-gate-evidence.json"
  if migration_gate_values="$(invoke_python - \
      "$MIGRATION_GATE_EVIDENCE" "$MIGRATION_GATE_EVIDENCE_PIN" \
      "$EVIDENCE_DIR/package/closed-release.json" \
      "$PINNED_ARCHIVE_SHA256" "$ENVIRONMENT_AUTHORITY_SHA256" <<'PY'
import json
import os
import re
import stat
import sys
import tempfile
from hashlib import sha256
from pathlib import Path


class Reject(SystemExit):
    def __init__(self, code: int):
        super().__init__(code)
        self.code = code


def read_pinned_regular(
    path: Path, *, invalid_code: int = 20, io_code: int = 23
) -> bytes:
    absolute = Path(os.path.abspath(path))
    if absolute.is_symlink() or os.path.normcase(os.path.realpath(absolute)) != os.path.normcase(str(absolute)):
        raise Reject(invalid_code)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        descriptor = os.open(absolute, flags)
    except OSError:
        raise Reject(io_code)
    try:
        observed = os.fstat(descriptor)
        if not stat.S_ISREG(observed.st_mode) or observed.st_size > 4 * 1024 * 1024:
            raise Reject(invalid_code)
        raw = bytearray()
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            raw.extend(chunk)
        return bytes(raw)
    finally:
        os.close(descriptor)


def object_without_duplicate_keys(pairs, invalid_code):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Reject(invalid_code)
        result[key] = value
    return result


def load_object(raw, invalid_code):
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=lambda pairs: object_without_duplicate_keys(
                pairs, invalid_code
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise Reject(invalid_code)
    if not isinstance(payload, dict):
        raise Reject(invalid_code)
    return payload


def digest(payload, key, invalid_code=20):
    value = payload.get(key)
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise Reject(invalid_code)
    return value


def migration_tuple(payload, key, invalid_code=20):
    value = payload.get(key)
    if not isinstance(value, dict) or set(value) != {"version", "migration"}:
        raise Reject(invalid_code)
    version = value["version"]
    migration = value["migration"]
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version < 1
        or not isinstance(migration, str)
        or re.fullmatch(r"[0-9]{3}_[a-z0-9_]+\.sql", migration) is None
        or int(migration[:3]) != version
    ):
        raise Reject(invalid_code)
    return version, migration


source = Path(sys.argv[1])
destination = Path(sys.argv[2])
package_evidence_source = Path(sys.argv[3])
expected_archive = sys.argv[4]
expected_environment = sys.argv[5]
package_payload = load_object(
    read_pinned_regular(package_evidence_source, invalid_code=25, io_code=25),
    25,
)
if digest(package_payload, "archive_sha256", 25) != expected_archive:
    raise Reject(25)
package_migrations = package_payload.get("migration_prerequisites")
if not isinstance(package_migrations, dict):
    raise Reject(25)
if digest(package_migrations, "archive_sha256", 25) != expected_archive:
    raise Reject(25)
expected_migration_set = digest(package_migrations, "migration_set_sha256", 25)
expected_latest = migration_tuple(package_migrations, "migration_latest", 25)
expected_tools = tuple(
    digest(package_migrations, key, 25)
    for key in ("verifier_sha256", "checker_sha256", "installer_sha256")
)
raw = read_pinned_regular(source)
payload = load_object(raw, 20)
allowed_keys = {
    "schema_version",
    "status",
    "timestamp",
    "archive_sha256",
    "verifier_sha256",
    "checker_sha256",
    "installer_sha256",
    "migration_set_sha256",
    "migration_latest",
    "observed_database",
    "environment_pin_sha256",
}
if set(payload) - allowed_keys:
    raise Reject(20)
if payload.get("schema_version") != 1 or payload.get("status") != "passed":
    raise Reject(20)
if "timestamp" in payload and not isinstance(payload["timestamp"], str):
    raise Reject(20)
observed_tools = tuple(
    digest(payload, key)
    for key in ("verifier_sha256", "checker_sha256", "installer_sha256")
)
archive_sha = digest(payload, "archive_sha256")
environment_sha = digest(payload, "environment_pin_sha256")
migration_set_sha = digest(payload, "migration_set_sha256")
latest_version, latest_migration = migration_tuple(payload, "migration_latest")
observed_version, observed_migration = migration_tuple(payload, "observed_database")
if archive_sha != expected_archive:
    raise Reject(21)
if environment_sha != expected_environment:
    raise Reject(22)
if (latest_version, latest_migration) != (observed_version, observed_migration):
    raise Reject(24)
if migration_set_sha != expected_migration_set:
    raise Reject(26)
if (latest_version, latest_migration) != expected_latest:
    raise Reject(27)
if observed_tools != expected_tools:
    raise Reject(28)

parent = destination.parent
if parent.is_symlink() or not parent.is_dir():
    raise Reject(23)
temporary = None
try:
    descriptor, temporary = tempfile.mkstemp(
        prefix=".migration-gate-evidence.", dir=str(parent)
    )
    try:
        os.fchmod(descriptor, 0o600)
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, destination)
    temporary = None
except OSError:
    raise Reject(23)
finally:
    if temporary is not None:
        try:
            os.unlink(temporary)
        except OSError:
            pass
if destination.is_symlink() or not destination.is_file() or destination.read_bytes() != raw:
    raise Reject(23)
print(
    "\t".join(
        (
            sha256(raw).hexdigest(),
            migration_set_sha,
            str(latest_version),
            latest_migration,
            str(observed_version),
            observed_migration,
        )
    )
)
PY
    )"; then
    IFS=$'\t' read -r MIGRATION_GATE_EVIDENCE_SHA256 \
      MIGRATION_GATE_MIGRATION_SET_SHA256 \
      MIGRATION_GATE_LATEST_VERSION MIGRATION_GATE_LATEST_MIGRATION \
      MIGRATION_GATE_OBSERVED_VERSION MIGRATION_GATE_OBSERVED_MIGRATION \
      <<< "$migration_gate_values"
    fsync_directories "$EVIDENCE_DIR" || die 'migration-gate-evidence-pin-failed'
  else
    migration_gate_status=$?
    case "$migration_gate_status" in
      21) die 'migration-gate-archive-mismatch' ;;
      22) die 'migration-gate-environment-mismatch' ;;
      24) die 'migration-gate-observed-mismatch' ;;
      25) die 'migration-gate-package-evidence-invalid' ;;
      26) die 'migration-gate-migration-set-mismatch' ;;
      27) die 'migration-gate-latest-mismatch' ;;
      28) die 'migration-gate-tool-digest-mismatch' ;;
      23) die 'migration-gate-evidence-pin-failed' ;;
      *) die 'migration-gate-evidence-invalid' ;;
    esac
  fi
fi

STAGING_ROOT="$RELEASE_PARENT/.${RELEASE_NAME}.closed-stage.$$"
OLD_ROOT="$RELEASE_PARENT/.${RELEASE_NAME}.closed-old.$$"
RETIRED_ROOT="$RELEASE_PARENT/.${RELEASE_NAME}.closed-retired.$ATTEMPT_ID"
CANDIDATE_CLEANUP_ROOT="$RELEASE_PARENT/.${RELEASE_NAME}.closed-candidate-cleanup.$ATTEMPT_ID"
STAGING_DELETE_ROOT="$RELEASE_PARENT/.${RELEASE_NAME}.closed-staging-cleanup.$ATTEMPT_ID"
RETIRED_CLEANUP_ROOT="$RELEASE_PARENT/.${RELEASE_NAME}.closed-retired-cleanup.$ATTEMPT_ID"
CANDIDATE_CLEANUP_OWNER="$CANDIDATE_CLEANUP_ROOT.owner"
STAGING_DELETE_OWNER="$STAGING_DELETE_ROOT.owner"
RETIRED_CLEANUP_OWNER="$RETIRED_CLEANUP_ROOT.owner"
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
fsync_directories "$EVIDENCE_DIR"
[ ! -e "$STAGING_ROOT" ] && [ ! -L "$STAGING_ROOT" ] \
  && [ ! -e "$STAGING_OWNER_MARKER" ] && [ ! -L "$STAGING_OWNER_MARKER" ] \
  && [ ! -e "$OLD_ROOT" ] && [ ! -L "$OLD_ROOT" ] \
  && [ ! -e "$RETIRED_ROOT" ] && [ ! -L "$RETIRED_ROOT" ] \
  && [ ! -e "$CANDIDATE_CLEANUP_ROOT" ] && [ ! -L "$CANDIDATE_CLEANUP_ROOT" ] \
  && [ ! -e "$CANDIDATE_CLEANUP_OWNER" ] && [ ! -L "$CANDIDATE_CLEANUP_OWNER" ] \
  && [ ! -e "$STAGING_DELETE_ROOT" ] && [ ! -L "$STAGING_DELETE_ROOT" ] \
  && [ ! -e "$STAGING_DELETE_OWNER" ] && [ ! -L "$STAGING_DELETE_OWNER" ] \
  && [ ! -e "$RETIRED_CLEANUP_ROOT" ] && [ ! -L "$RETIRED_CLEANUP_ROOT" ] \
  && [ ! -e "$RETIRED_CLEANUP_OWNER" ] && [ ! -L "$RETIRED_CLEANUP_OWNER" ] \
  || die 'staging-path-exists'
STAGING_CLEANUP_ARMED=true
mkdir -- "$STAGING_ROOT"
STAGING_ROOT_IDENTITY="$(tree_root_identity "$STAGING_ROOT")" \
  || die 'staging-root-identity-failed'
STAGING_OWNER_NONCE="$(new_private_staging_nonce)" \
  || die 'staging-owner-nonce-failed'
write_private_staging_owner_marker "$STAGING_OWNER_MARKER" "$ATTEMPT_ID" \
  "$$" "$STAGING_ROOT_IDENTITY" "$STAGING_OWNER_NONCE" || {
    owner_write_status=$?
    printf 'install_closed_release: staging-owner-write-failed\n' >&2
    exit "$owner_write_status"
  }
fsync_directories "$RELEASE_PARENT" "$STAGING_ROOT"
invoke_python "$VERIFY_SCRIPT" \
  --archive "$PINNED_ARCHIVE" --archive-digest-file "$PINNED_ARCHIVE_DIGEST_FILE" \
  --require-closed --evidence-dir "$EVIDENCE_DIR/package"
tar -xzf "$PINNED_ARCHIVE" -C "$STAGING_ROOT" --no-same-owner --no-same-permissions
cleanup_pinned_archive
[ -f "$STAGING_ROOT/launch-release-manifest.json" ] || die 'extracted-manifest-missing'

# Re-verify extracted activation-critical bytes before any dependency hook or mutation.
invoke_python "$VERIFY_SCRIPT" \
  --installed-root "$STAGING_ROOT" --verify-config-ingress-unit-digests \
  --require-closed --evidence-dir "$EVIDENCE_DIR/staged"
CANDIDATE_MANIFEST_SHA256="$(regular_file_sha256 \
  "$STAGING_ROOT/launch-release-manifest.json")" \
  || die 'candidate-manifest-digest-failed'

record_authority_result() {
  local name="$1"
  local status="$2"
  local code="$3"
  invoke_python - "$EVIDENCE_DIR/dependency-unit-checks.json" "$name" "$status" "$code" <<'PY'
import json
import os
from pathlib import Path
import sys
import tempfile

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
descriptor, name = tempfile.mkstemp(
    prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
)
temporary = Path(name)
try:
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        descriptor = -1
        stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    if os.name != "nt":
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
finally:
    if descriptor != -1:
        os.close(descriptor)
    temporary.unlink(missing_ok=True)
PY
}

record_systemd_unit_cleanup() {
  local status="$1"
  local code="$2"
  local payload
  payload="$(invoke_python - "$status" "$code" <<'PY'
import json
import sys

payload = {
    "exit_code": int(sys.argv[2]),
    "live_sla_proven": False,
    "observed_local_elapsed_seconds": 0.0,
    "schema_version": 1,
    "stage3_claim": False,
    "status": sys.argv[1],
}
print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
PY
  )" || return 1
  write_durable_atomic_json "$EVIDENCE_DIR/systemd-unit-cleanup.json" "$payload"
}

finalize_systemd_unit_cleanup() {
  local cleanup_status=0 record_status=0 outcome=passed code=0
  if remove_systemd_unit_attempt; then
    :
  else
    cleanup_status=$?
    outcome=failed
    code="$cleanup_status"
  fi
  if record_systemd_unit_cleanup "$outcome" "$code"; then
    :
  else
    record_status=$?
    printf 'install_closed_release: systemd-unit-cleanup-record-failed:%s\n' \
      "$record_status" >&2
  fi
  [ "$cleanup_status" -eq 0 ] || return "$cleanup_status"
  return "$record_status"
}

run_authority_hook() {
  local name="$1"
  local expected_sha256 role hook_status=0 record_status=0 outcome
  shift 2
  case "$name" in
    python-dependencies)
      role=python-dependency
      expected_sha256="$PYTHON_DEPENDENCY_HOOK_SHA256"
      ;;
    nuxt-production-dependencies)
      role=nuxt-dependency
      expected_sha256="$NUXT_DEPENDENCY_HOOK_SHA256"
      ;;
    systemd-units)
      role=unit-verify
      expected_sha256="$UNIT_VERIFY_HOOK_SHA256"
      ;;
    *) return 126 ;;
  esac
  if invoke_pinned_executable "$role" "$expected_sha256" -- "$@"; then
    outcome=passed
  else
    hook_status=$?
    outcome=failed
  fi
  if record_authority_result "$name" "$outcome" "$hook_status"; then
    :
  else
    record_status=$?
    printf 'install_closed_release: authority-result-record-failed:%s:%s\n' \
      "$name" "$record_status" >&2
  fi
  [ "$hook_status" -eq 0 ] || return "$hook_status"
  return "$record_status"
}

run_authority_hook python-dependencies "$PYTHON_DEPENDENCY_HOOK" \
  --release-root "$STAGING_ROOT" --requirements "$STAGING_ROOT/requirements.txt"
run_authority_hook nuxt-production-dependencies "$NUXT_DEPENDENCY_HOOK" \
  --project-root "$STAGING_ROOT/web-nuxt" --production-only

# Dependency hooks may modify staging, so verify tracked bytes again before
# making the candidate durable or touching the live release.
invoke_python "$VERIFY_SCRIPT" \
  --installed-root "$STAGING_ROOT" --verify-config-ingress-unit-digests \
  --require-closed --evidence-dir "$EVIDENCE_DIR/staged"
[ "$(regular_file_sha256 "$STAGING_ROOT/launch-release-manifest.json")" \
  = "$CANDIDATE_MANIFEST_SHA256" ] \
  || die 'candidate-manifest-changed-after-hooks'

snapshot_tree() {
  invoke_python - "$1" "$2" <<'PY'
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile

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
target = Path(sys.argv[2])

def fsync_directory(directory):
    if os.name == "nt":
        return
    descriptor = os.open(
        directory,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

descriptor, name = tempfile.mkstemp(
    prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
)
temporary = Path(name)
try:
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        descriptor = -1
        stream.write(json.dumps(result, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)
    fsync_directory(target.parent)
finally:
    if descriptor != -1:
        os.close(descriptor)
    temporary.unlink(missing_ok=True)
PY
}

fsync_tree_durably() {
  invoke_python - "$1" <<'PY'
import os
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1])
if root.is_symlink() or not root.is_dir():
    raise SystemExit(1)

def fsync_file(path):
    if os.name == "nt":
        return
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

def fsync_directory(path):
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

def walk(directory):
    child_directories = []
    with os.scandir(directory) as entries:
        for entry in entries:
            mode = entry.stat(follow_symlinks=False).st_mode
            if stat.S_ISLNK(mode):
                raise SystemExit(1)
            if stat.S_ISREG(mode):
                fsync_file(entry.path)
            elif stat.S_ISDIR(mode):
                child_directories.append(Path(entry.path))
            else:
                raise SystemExit(1)
    for child in child_directories:
        walk(child)
    fsync_directory(directory)

walk(root)
PY
}

MUTATION_STARTED=false
PERSISTENT_DETACHED=false
PERSISTENT_ATTACHED_TO_RELEASE=true
PERSISTENT_MOUNT_STATE_UNKNOWN=false
OLD_ROOT_READY=false
INSTALL_COMMITTED=false
INSTALL_COMPLETE=false
INSTALL_FAILURE_POINT=pre-mutation

write_recovery_evidence() {
  local status="$1"
  local root_restored="$2"
  local persistent_restored="$3"
  local systemd_units_restored="$4"
  local payload
  payload="$(invoke_python - "$status" "$INSTALL_FAILURE_POINT" \
    "$root_restored" "$persistent_restored" \
    "$systemd_units_restored" <<'PY'
import json
import sys

payload = {
    "failure_point": sys.argv[2],
    "live_sla_proven": False,
    "observed_local_elapsed_seconds": 0.0,
    "persistent_restored": sys.argv[4] == "true",
    "root_restored": sys.argv[3] == "true",
    "schema_version": 1,
    "stage3_claim": False,
    "status": sys.argv[1],
    "systemd_units_restored": sys.argv[5] == "true",
}
print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
PY
  )" || return 1
  write_durable_atomic_json "$EVIDENCE_DIR/install-recovery.json" "$payload"
}

materialize_environment_authority() {
  local target_root="${1:-$RELEASE_ROOT}"
  invoke_python - "$PINNED_ENVIRONMENT_AUTHORITY" "$target_root/.env" \
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
  fsync_directories "$target_root"
}

materialize_environment_authority "$STAGING_ROOT"
source_release_topology_snapshot \
  "$STAGING_ROOT" "$CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT" \
  || die 'candidate-release-topology-snapshot-failed'
CANDIDATE_RELEASE_TOPOLOGY_SHA256="$(regular_file_sha256 \
  "$CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT")" \
  || die 'candidate-release-topology-digest-failed'
CANDIDATE_RELEASE_ROOT_IDENTITY="$(tree_root_identity "$STAGING_ROOT")" \
  || die 'candidate-release-root-identity-failed'
[ "$CANDIDATE_RELEASE_ROOT_IDENTITY" = "$STAGING_ROOT_IDENTITY" ] \
  || die 'candidate-release-root-identity-changed'

prepare_systemd_unit_attempt() {
  [ -z "$UNIT_ATTEMPT_ROOT" ] || return 1
  UNIT_ATTEMPT_ROOT="$(mktemp -d "$EVIDENCE_DIR/.systemd-unit-attempt.XXXXXXXX")"
  UNIT_BACKUP_ROOT="$UNIT_ATTEMPT_ROOT/backup"
  UNIT_MUTATION_MARKER="$UNIT_ATTEMPT_ROOT/armed"
  fsync_directories "$EVIDENCE_DIR" "$UNIT_ATTEMPT_ROOT"
}

remove_systemd_unit_attempt() {
  [ -n "$UNIT_ATTEMPT_ROOT" ] || return 0
  remove_systemd_unit_attempt_root "$UNIT_ATTEMPT_ROOT" || return $?
  UNIT_ATTEMPT_ROOT=''
  UNIT_BACKUP_ROOT=''
  UNIT_MUTATION_MARKER=''
}

prepare_systemd_unit_backup() {
  invoke_python - "$RELEASE_ROOT" "$SYSTEMD_UNIT_DESTINATION" "$UNIT_BACKUP_ROOT" "$UNIT_MUTATION_MARKER" <<'PY'
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

def write_durable_bytes(path, raw):
    with path.open("wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

def write_durable_text(path, text):
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())

def fsync_directory(directory):
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

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
        raw = target.read_bytes()
        write_durable_bytes(backup_file, raw)
        entry["sha256"] = hashlib.sha256(raw).hexdigest()
        entry["size"] = len(raw)
    metadata[target.name] = entry
metadata_path = backup / "metadata.json"
metadata_text = json.dumps(metadata, indent=2, sort_keys=True) + "\n"
write_durable_text(metadata_path, metadata_text)
write_durable_text(marker, "armed\n")
fsync_directory(backup)
fsync_directory(backup.parent)
fsync_directory(backup.parent.parent)
fsync_directory(destination)
fsync_directory(destination.parent)
PY
}

install_systemd_units() {
  invoke_python - "$RELEASE_ROOT" "$SYSTEMD_UNIT_DESTINATION" <<'PY'
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
manifest = json.loads((release / "launch-release-manifest.json").read_text(encoding="utf-8"))
declarations = manifest.get("members")
if not isinstance(declarations, dict) or destination.is_symlink() or not destination.is_dir():
    raise SystemExit("systemd unit destination is not a real directory")
for relative in UNIT_PATHS:
    source = release / relative
    target = destination / Path(relative).name
    raw = source.read_bytes()
    declaration = declarations.get(relative)
    if (
        not isinstance(declaration, dict)
        or source.is_symlink()
        or declaration.get("sha256") != hashlib.sha256(raw).hexdigest()
        or declaration.get("size") != len(raw)
        or target.is_symlink()
        or (target.exists() and not target.is_file())
    ):
        raise SystemExit(f"systemd unit source or destination is unsafe: {relative}")
    descriptor, name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=destination
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
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
  restore_systemd_units_from "$SYSTEMD_UNIT_DESTINATION" "$UNIT_ATTEMPT_ROOT"
}

inspect_current_mount() {
  local target="$RELEASE_ROOT/agent/data"
  if invoke_mount_authority findmnt --json --mountpoint "$target" \
    > "$EVIDENCE_DIR/findmnt-recovery.json"; then
    verify_findmnt_file "$EVIDENCE_DIR/findmnt-recovery.json" \
      "$PERSISTENT_AGENT_DATA_ROOT" "$target" || return 2
    return 0
  else
    local status=$?
    [ "$status" -eq 1 ] && return 1
    return 2
  fi
}

restore_old_root_for_recovery() {
  local rename_status=0
  tree_matches_bound_topology "$OLD_ROOT" "$SOURCE_RELEASE_ROOT_IDENTITY" \
    "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT" false || return 1
  write_mutation_state recovery-restore-old-root-armed || return $?
  if mv -- "$OLD_ROOT" "$RELEASE_ROOT"; then
    :
  else
    rename_status=$?
  fi
  if [ ! -e "$OLD_ROOT" ] && [ ! -L "$OLD_ROOT" ] \
    && [ -d "$RELEASE_ROOT" ] && [ ! -L "$RELEASE_ROOT" ]; then
    tree_matches_bound_topology "$RELEASE_ROOT" \
      "$SOURCE_RELEASE_ROOT_IDENTITY" "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT" \
      false || return 1
    OLD_ROOT_READY=false
    return 0
  fi
  [ "$rename_status" -ne 0 ] && return "$rename_status"
  return 1
}

detach_local_persistent_for_recovery() {
  local source="$RELEASE_ROOT/agent/data"
  local rename_status=0
  if mv -- "$source" "$PERSISTENT_AGENT_DATA_ROOT"; then
    :
  else
    rename_status=$?
  fi
  if [ ! -e "$source" ] && [ ! -L "$source" ] \
    && [ -d "$PERSISTENT_AGENT_DATA_ROOT" ] \
    && [ ! -L "$PERSISTENT_AGENT_DATA_ROOT" ]; then
    PERSISTENT_ATTACHED_TO_RELEASE=false
    PERSISTENT_DETACHED=true
    PERSISTENT_MOUNT_STATE_UNKNOWN=false
    fsync_directories "$(dirname -- "$source")" \
      "$(dirname -- "$PERSISTENT_AGENT_DATA_ROOT")" || return $?
    return "$rename_status"
  fi
  PERSISTENT_ATTACHED_TO_RELEASE=true
  PERSISTENT_DETACHED=false
  PERSISTENT_MOUNT_STATE_UNKNOWN=false
  [ "$rename_status" -ne 0 ] && return "$rename_status"
  return 1
}

detach_persistent_from_release_for_recovery() {
  if [ "$LOCAL_REHEARSAL" = true ]; then
    if [ -e "$PERSISTENT_AGENT_DATA_ROOT" ] || [ -L "$PERSISTENT_AGENT_DATA_ROOT" ]; then
      [ -d "$PERSISTENT_AGENT_DATA_ROOT" ] && [ ! -L "$PERSISTENT_AGENT_DATA_ROOT" ] \
        || return 1
      [ -z "$(find "$PERSISTENT_AGENT_DATA_ROOT" -mindepth 1 -print -quit)" ] \
        || return 1
      write_mutation_state recovery-remove-empty-persistent-root-armed \
        || return $?
      remove_empty_directory_durably "$PERSISTENT_AGENT_DATA_ROOT" \
        || return $?
    fi
    write_mutation_state recovery-detach-persistent-armed || return $?
    detach_local_persistent_for_recovery || return $?
  else
    local mount_state
    if inspect_current_mount; then
      mount_state=0
    else
      mount_state=$?
    fi
    case "$mount_state" in
      0)
        write_mutation_state recovery-detach-persistent-armed || return $?
        invoke_mount_authority umount "$RELEASE_ROOT/agent/data" || true
        PERSISTENT_MOUNT_STATE_UNKNOWN=true
        if inspect_current_mount; then
          mount_state=0
        else
          mount_state=$?
        fi
        case "$mount_state" in
          0)
            PERSISTENT_ATTACHED_TO_RELEASE=true
            PERSISTENT_DETACHED=false
            PERSISTENT_MOUNT_STATE_UNKNOWN=false
            return 1
            ;;
          1)
            PERSISTENT_ATTACHED_TO_RELEASE=false
            PERSISTENT_DETACHED=true
            PERSISTENT_MOUNT_STATE_UNKNOWN=false
            fsync_directories "$RELEASE_ROOT/agent/data" "$RELEASE_ROOT/agent" \
              || return $?
            ;;
          *)
            PERSISTENT_ATTACHED_TO_RELEASE=true
            PERSISTENT_DETACHED=false
            PERSISTENT_MOUNT_STATE_UNKNOWN=true
            return "$mount_state"
            ;;
        esac
        ;;
      1)
        PERSISTENT_ATTACHED_TO_RELEASE=false
        PERSISTENT_DETACHED=true
        PERSISTENT_MOUNT_STATE_UNKNOWN=false
        ;;
      *) return 1 ;;
    esac
  fi
}

restore_local_persistent_for_recovery() {
  local target="$RELEASE_ROOT/agent/data"
  local rename_status=0
  if mv -- "$PERSISTENT_AGENT_DATA_ROOT" "$target"; then
    :
  else
    rename_status=$?
  fi
  if [ ! -e "$PERSISTENT_AGENT_DATA_ROOT" ] \
    && [ ! -L "$PERSISTENT_AGENT_DATA_ROOT" ] \
    && [ -d "$target" ] && [ ! -L "$target" ]; then
    PERSISTENT_ATTACHED_TO_RELEASE=true
    PERSISTENT_DETACHED=false
    PERSISTENT_MOUNT_STATE_UNKNOWN=false
    fsync_directories "$(dirname -- "$PERSISTENT_AGENT_DATA_ROOT")" \
      "$(dirname -- "$target")" || return $?
    return "$rename_status"
  fi
  PERSISTENT_ATTACHED_TO_RELEASE=false
  PERSISTENT_DETACHED=true
  PERSISTENT_MOUNT_STATE_UNKNOWN=false
  [ "$rename_status" -ne 0 ] && return "$rename_status"
  return 1
}

attach_persistent_to_release_for_recovery() {
  local target="$RELEASE_ROOT/agent/data"
  mkdir -p -- "$RELEASE_ROOT/agent" || return $?
  write_mutation_state recovery-restore-persistent-armed || return $?
  if [ -e "$target" ] || [ -L "$target" ]; then
    [ -d "$target" ] && [ ! -L "$target" ] || return 1
    [ -z "$(find "$target" -mindepth 1 -print -quit)" ] || return 1
    rmdir -- "$target" || return $?
  fi
  if [ "$LOCAL_REHEARSAL" = true ]; then
    restore_local_persistent_for_recovery || return $?
    write_mutation_state recovery-create-persistent-root-armed || return $?
    mkdir -- "$PERSISTENT_AGENT_DATA_ROOT" || return $?
    fsync_directories "$(dirname -- "$PERSISTENT_AGENT_DATA_ROOT")" \
      "$PERSISTENT_AGENT_DATA_ROOT" "$(dirname -- "$target")" || return $?
  else
    mkdir -- "$target" || return $?
    PERSISTENT_MOUNT_STATE_UNKNOWN=true
    invoke_mount_authority mount --bind "$PERSISTENT_AGENT_DATA_ROOT" "$target" \
      || return $?
    PERSISTENT_ATTACHED_TO_RELEASE=true
    PERSISTENT_DETACHED=false
    PERSISTENT_MOUNT_STATE_UNKNOWN=false
    fsync_directories "$target" "$(dirname -- "$target")" || return $?
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
    invoke_mount_authority findmnt --json --mountpoint "$RELEASE_ROOT/agent/data" \
      > "$EVIDENCE_DIR/findmnt-recovery.json" || return $?
    verify_findmnt_file "$EVIDENCE_DIR/findmnt-recovery.json" \
      "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent/data" || return $?
  fi
  snapshot_tree "$RELEASE_ROOT/agent/data" "$SNAPSHOT_RECOVERY" || return $?
  cmp -s -- "$SNAPSHOT_BEFORE" "$SNAPSHOT_RECOVERY"
}

cleanup_recovery_staging() {
  local staging_present=false staging_delete_present=false
  local staging_delete_owner_present=false
  local stage_owner_present=false
  for authority in "$STAGING_ROOT" "$STAGING_DELETE_ROOT" \
    "$STAGING_DELETE_OWNER" "$STAGING_OWNER_MARKER"; do
    [ ! -L "$authority" ] || return 1
  done
  if [ -e "$STAGING_ROOT" ]; then
    [ -d "$STAGING_ROOT" ] || return 1
    staging_present=true
  fi
  if [ -e "$STAGING_DELETE_ROOT" ]; then
    [ -d "$STAGING_DELETE_ROOT" ] || return 1
    staging_delete_present=true
  fi
  if [ -e "$STAGING_DELETE_OWNER" ]; then
    [ -f "$STAGING_DELETE_OWNER" ] || return 1
    staging_delete_owner_present=true
  fi
  if [ -e "$STAGING_OWNER_MARKER" ]; then
    verify_private_staging_owner_marker "$STAGING_OWNER_MARKER" \
      "$STAGING_ROOT" "$ATTEMPT_ID" "$$" "$STAGING_ROOT_IDENTITY" \
      "$STAGING_OWNER_NONCE" || return 1
    stage_owner_present=true
  fi
  [ "$staging_present" = false ] || [ "$staging_delete_present" = false ] \
    || return 1

  if [ "$staging_present" = true ] \
    || [ "$staging_delete_present" = true ] \
    || [ "$staging_delete_owner_present" = true ]; then
    write_mutation_state recovery-remove-staging-armed || return 1
  fi
  if [ "$staging_present" = true ]; then
    [ "$stage_owner_present" = true ] || return 1
    tree_matches_bound_topology "$STAGING_ROOT" \
      "$CANDIDATE_RELEASE_ROOT_IDENTITY" \
      "$CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT" false || return 1
    [ "$(regular_file_sha256 \
      "$STAGING_ROOT/launch-release-manifest.json")" \
      = "$CANDIDATE_MANIFEST_SHA256" ] || return 1
    if [ "$staging_delete_owner_present" = true ]; then
      verify_cleanup_owner_marker "$STAGING_DELETE_OWNER" staging \
        "$ATTEMPT_ID" "$CANDIDATE_RELEASE_ROOT_IDENTITY" \
        "$CANDIDATE_RELEASE_TOPOLOGY_SHA256" || return 1
    else
      write_cleanup_owner_marker "$STAGING_DELETE_OWNER" staging \
        "$ATTEMPT_ID" "$CANDIDATE_RELEASE_ROOT_IDENTITY" \
        "$CANDIDATE_RELEASE_TOPOLOGY_SHA256" || return 1
      staging_delete_owner_present=true
    fi
    mv -- "$STAGING_ROOT" "$STAGING_DELETE_ROOT" || return 1
    fsync_directories "$RELEASE_PARENT" || return 1
    [ ! -e "$STAGING_ROOT" ] && [ ! -L "$STAGING_ROOT" ] || return 1
    staging_present=false
    staging_delete_present=true
  fi
  if [ "$staging_delete_present" = true ]; then
    [ "$staging_delete_owner_present" = true ] || return 1
    verify_cleanup_owner_marker "$STAGING_DELETE_OWNER" staging \
      "$ATTEMPT_ID" "$CANDIDATE_RELEASE_ROOT_IDENTITY" \
      "$CANDIDATE_RELEASE_TOPOLOGY_SHA256" || return 1
    tree_matches_bound_topology "$STAGING_DELETE_ROOT" \
      "$CANDIDATE_RELEASE_ROOT_IDENTITY" \
      "$CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT" true || return 1
    invoke_rm -rf -- "$STAGING_DELETE_ROOT" || return 1
    [ ! -e "$STAGING_DELETE_ROOT" ] && [ ! -L "$STAGING_DELETE_ROOT" ] \
      || return 1
    fsync_directories "$RELEASE_PARENT" || return 1
    staging_delete_present=false
  fi
  if [ "$staging_delete_owner_present" = true ]; then
    [ "$staging_delete_present" = false ] || return 1
    remove_file_durably "$STAGING_DELETE_OWNER" || return 1
    [ ! -e "$STAGING_DELETE_OWNER" ] && [ ! -L "$STAGING_DELETE_OWNER" ] \
      || return 1
    staging_delete_owner_present=false
  fi
  if [ "$stage_owner_present" = true ]; then
    write_mutation_state recovery-remove-staging-owner-armed || return 1
    remove_file_durably "$STAGING_OWNER_MARKER" || return 1
    [ ! -e "$STAGING_OWNER_MARKER" ] && [ ! -L "$STAGING_OWNER_MARKER" ] \
      || return 1
    stage_owner_present=false
  fi
  [ "$staging_present" = false ] \
    && [ "$staging_delete_present" = false ] \
    && [ "$staging_delete_owner_present" = false ] \
    && [ "$stage_owner_present" = false ] || return 1
  STAGING_CLEANUP_ARMED=false
}

install_recovery() {
  local status=$?
  trap - EXIT ERR
  set +e
  local root_restored=true
  local persistent_restored=true
  local systemd_units_restored=true
  local recovery_cleanup_status=0
  local recovery_record_status=0
  local evidence_status=0
  local candidate_recovery_root=''

  if [ "$INSTALL_COMPLETE" != true ] && [ "$INSTALL_COMMITTED" != true ] \
    && [ "$MUTATION_STARTED" = true ]; then
    restore_systemd_units >/dev/null 2>&1 || systemd_units_restored=false

    if [ "$systemd_units_restored" = true ]; then
      if [ "$OLD_ROOT_READY" = true ] \
        && { [ "$PERSISTENT_ATTACHED_TO_RELEASE" = true ] \
          || [ "$PERSISTENT_MOUNT_STATE_UNKNOWN" = true ]; }; then
        detach_persistent_from_release_for_recovery >/dev/null 2>&1 \
          || persistent_restored=false
      fi

      if [ "$OLD_ROOT_READY" = true ]; then
        if [ "$persistent_restored" != true ] \
          || [ "$PERSISTENT_ATTACHED_TO_RELEASE" = true ] \
          || [ "$PERSISTENT_MOUNT_STATE_UNKNOWN" = true ]; then
          root_restored=false
        else
          write_mutation_state recovery-remove-release-root-armed \
            >/dev/null 2>&1 || root_restored=false
        fi
        if [ "$root_restored" = true ]; then
          if [ -d "$RELEASE_ROOT" ] && [ ! -L "$RELEASE_ROOT" ]; then
            candidate_recovery_root="$RELEASE_ROOT"
          elif [ -d "$STAGING_ROOT" ] && [ ! -L "$STAGING_ROOT" ]; then
            candidate_recovery_root="$STAGING_ROOT"
          else
            root_restored=false
          fi
        fi
        if [ "$root_restored" = true ]; then
          if ! tree_matches_bound_topology "$OLD_ROOT" \
              "$SOURCE_RELEASE_ROOT_IDENTITY" \
              "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT" false \
            || ! tree_matches_bound_topology "$candidate_recovery_root" \
              "$CANDIDATE_RELEASE_ROOT_IDENTITY" \
              "$CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT" false \
            || [ "$(regular_file_sha256 \
              "$candidate_recovery_root/launch-release-manifest.json")" \
              != "$CANDIDATE_MANIFEST_SHA256" ]; then
            root_restored=false
          fi
        fi
        if [ "$root_restored" = true ] \
          && [ "$candidate_recovery_root" = "$RELEASE_ROOT" ]; then
          if [ -e "$CANDIDATE_CLEANUP_ROOT" ] \
            || [ -L "$CANDIDATE_CLEANUP_ROOT" ] \
            || [ -e "$CANDIDATE_CLEANUP_OWNER" ] \
            || [ -L "$CANDIDATE_CLEANUP_OWNER" ]; then
            root_restored=false
          elif write_cleanup_owner_marker "$CANDIDATE_CLEANUP_OWNER" \
              candidate "$ATTEMPT_ID" "$CANDIDATE_RELEASE_ROOT_IDENTITY" \
              "$CANDIDATE_RELEASE_TOPOLOGY_SHA256" >/dev/null 2>&1 \
            && mv -- "$RELEASE_ROOT" "$CANDIDATE_CLEANUP_ROOT" \
            && fsync_directories "$RELEASE_PARENT" >/dev/null 2>&1 \
            && [ ! -e "$RELEASE_ROOT" ] && [ ! -L "$RELEASE_ROOT" ] \
            && tree_matches_bound_topology "$CANDIDATE_CLEANUP_ROOT" \
              "$CANDIDATE_RELEASE_ROOT_IDENTITY" \
              "$CANDIDATE_RELEASE_TOPOLOGY_SNAPSHOT" true; then
            if verify_cleanup_owner_marker "$CANDIDATE_CLEANUP_OWNER" \
                candidate "$ATTEMPT_ID" "$CANDIDATE_RELEASE_ROOT_IDENTITY" \
                "$CANDIDATE_RELEASE_TOPOLOGY_SHA256" \
              && invoke_rm -rf -- "$CANDIDATE_CLEANUP_ROOT" >/dev/null 2>&1 \
              && [ ! -e "$CANDIDATE_CLEANUP_ROOT" ] \
              && [ ! -L "$CANDIDATE_CLEANUP_ROOT" ] \
              && fsync_directories "$RELEASE_PARENT" >/dev/null 2>&1 \
              && remove_file_durably "$CANDIDATE_CLEANUP_OWNER" \
                >/dev/null 2>&1 \
              && [ ! -e "$CANDIDATE_CLEANUP_OWNER" ] \
              && [ ! -L "$CANDIDATE_CLEANUP_OWNER" ]; then
              :
            else
              root_restored=false
            fi
          else
            root_restored=false
          fi
        fi
        if [ "$root_restored" = true ] \
          && { [ -e "$RELEASE_ROOT" ] || [ -L "$RELEASE_ROOT" ]; }; then
          root_restored=false
        fi
        if [ "$root_restored" = true ]; then
          fsync_directories "$RELEASE_PARENT" >/dev/null 2>&1 \
            || root_restored=false
        fi
        if [ "$root_restored" = true ] \
          && [ "$PERSISTENT_ATTACHED_TO_RELEASE" != true ]; then
          restore_old_root_for_recovery >/dev/null 2>&1 \
            || root_restored=false
        fi
        if [ "$root_restored" = true ]; then
          fsync_directories "$RELEASE_PARENT" >/dev/null 2>&1 \
            || root_restored=false
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
    else
      root_restored=false
      persistent_restored=false
    fi

    if [ "$root_restored" = true ] \
      && [ "$persistent_restored" = true ] \
      && [ "$systemd_units_restored" = true ]; then
      if [ -n "$UNIT_ATTEMPT_ROOT" ]; then
        write_mutation_state recovery-remove-systemd-attempt-armed \
          >/dev/null 2>&1 || systemd_units_restored=false
        if [ "$systemd_units_restored" = true ]; then
          remove_systemd_unit_attempt >/dev/null 2>&1 \
            || systemd_units_restored=false
        fi
      fi
    fi

    if [ "$root_restored" = true ] \
      && [ "$persistent_restored" = true ] \
      && [ "$systemd_units_restored" = true ]; then
      if cleanup_recovery_staging >/dev/null 2>&1; then
        if write_mutation_state rollback-restored >/dev/null 2>&1; then
          if write_recovery_evidence rolled-back true true true; then
            if clear_mutation_state; then
              :
            else
              recovery_cleanup_status=$?
              if write_recovery_evidence rollback-failed true true true; then
                :
              else
                evidence_status=$?
                recovery_record_status="$evidence_status"
                printf 'install_closed_release: recovery-evidence-record-failed:rollback-failed:%s\n' \
                  "$evidence_status" >&2
              fi
            fi
          else
            evidence_status=$?
            recovery_record_status="$evidence_status"
            printf 'install_closed_release: recovery-evidence-record-failed:rolled-back:%s\n' \
              "$evidence_status" >&2
          fi
        else
          recovery_cleanup_status=$?
          if write_recovery_evidence rollback-failed true true true; then
            :
          else
            evidence_status=$?
            recovery_record_status="$evidence_status"
            printf 'install_closed_release: recovery-evidence-record-failed:rollback-failed:%s\n' \
              "$evidence_status" >&2
          fi
        fi
      else
        recovery_cleanup_status=$?
        if write_recovery_evidence rollback-failed true true true; then
          :
        else
          evidence_status=$?
          recovery_record_status="$evidence_status"
          printf 'install_closed_release: recovery-evidence-record-failed:rollback-failed:%s\n' \
            "$evidence_status" >&2
        fi
      fi
    else
      if write_recovery_evidence rollback-failed "$root_restored" \
          "$persistent_restored" "$systemd_units_restored"; then
        :
      else
        evidence_status=$?
        recovery_record_status="$evidence_status"
        printf 'install_closed_release: recovery-evidence-record-failed:rollback-failed:%s\n' \
          "$evidence_status" >&2
      fi
    fi
  fi

  if [ "$INSTALL_COMPLETE" = true ]; then
    if [ -e "$OLD_ROOT" ] || [ -L "$OLD_ROOT" ]; then
      if tree_matches_bound_topology "$OLD_ROOT" \
          "$SOURCE_RELEASE_ROOT_IDENTITY" "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT" \
          false \
        && invoke_rm -rf -- "$OLD_ROOT" >/dev/null 2>&1 \
        && [ ! -e "$OLD_ROOT" ] && [ ! -L "$OLD_ROOT" ] \
        && fsync_directories "$RELEASE_PARENT" >/dev/null 2>&1; then
        :
      else
        recovery_cleanup_status=1
      fi
    fi
  fi
  local cleanup_status=0
  cleanup_attempt_authorities || cleanup_status=$?
  [ "$cleanup_status" -ne 0 ] || cleanup_status="$recovery_cleanup_status"
  [ "$cleanup_status" -ne 0 ] || cleanup_status="$recovery_record_status"
  [ "$status" -ne 0 ] || status="$cleanup_status"
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

fsync_tree_durably "$STAGING_ROOT"
fsync_directories "$RELEASE_PARENT"

verify_findmnt_file() {
  local evidence="$1"
  local source="$2"
  local target="$3"
  invoke_python - "$VERIFY_SCRIPT" "$evidence" "$source" "$target" <<'PY'
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
if [ -e "$RELEASE_ROOT/agent" ] || [ -L "$RELEASE_ROOT/agent" ]; then
  [ -d "$RELEASE_ROOT/agent" ] && [ ! -L "$RELEASE_ROOT/agent" ] \
    || die 'agent-data-symlink-forbidden'
fi
if [ -e "$CURRENT_DATA" ] || [ -L "$CURRENT_DATA" ]; then
  [ -d "$CURRENT_DATA" ] && [ ! -L "$CURRENT_DATA" ] || die 'agent-data-symlink-forbidden'
snapshot_tree "$CURRENT_DATA" "$SNAPSHOT_BEFORE"
PERSISTENT_SNAPSHOT_SHA256="$(regular_file_sha256 "$SNAPSHOT_BEFORE")" \
  || die 'persistent-snapshot-digest-failed'
source_release_topology_snapshot \
  "$RELEASE_ROOT" "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT" \
  || die 'source-release-topology-snapshot-failed'
SOURCE_RELEASE_TOPOLOGY_SHA256="$(regular_file_sha256 \
  "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT")" \
  || die 'source-release-topology-digest-failed'
SOURCE_RELEASE_ROOT_IDENTITY="$(tree_root_identity "$RELEASE_ROOT")" \
  || die 'source-release-root-identity-failed'
else
  die 'agent-data-required'
fi

# detach-agent-data
write_mutation_state detach-agent-data-armed
MUTATION_STARTED=true
INSTALL_FAILURE_POINT=detach-agent-data
if [ "$LOCAL_REHEARSAL" = true ]; then
  detach_local_persistent_for_install() {
    local rename_status=0
    if mv -- "$CURRENT_DATA" "$PERSISTENT_AGENT_DATA_ROOT"; then
      :
    else
      rename_status=$?
    fi
    if [ ! -e "$CURRENT_DATA" ] && [ ! -L "$CURRENT_DATA" ] \
      && [ -d "$PERSISTENT_AGENT_DATA_ROOT" ] \
      && [ ! -L "$PERSISTENT_AGENT_DATA_ROOT" ]; then
      PERSISTENT_DETACHED=true
      PERSISTENT_ATTACHED_TO_RELEASE=false
      PERSISTENT_MOUNT_STATE_UNKNOWN=false
      fsync_directories "$(dirname -- "$CURRENT_DATA")" \
        "$(dirname -- "$PERSISTENT_AGENT_DATA_ROOT")" || return $?
      return "$rename_status"
    elif [ -d "$CURRENT_DATA" ] && [ ! -L "$CURRENT_DATA" ] \
      && [ ! -e "$PERSISTENT_AGENT_DATA_ROOT" ] \
      && [ ! -L "$PERSISTENT_AGENT_DATA_ROOT" ]; then
      PERSISTENT_DETACHED=false
      PERSISTENT_ATTACHED_TO_RELEASE=true
      PERSISTENT_MOUNT_STATE_UNKNOWN=false
      write_mutation_state recovery-create-persistent-root-armed || return $?
      mkdir -- "$PERSISTENT_AGENT_DATA_ROOT" || return $?
      fsync_directories "$(dirname -- "$CURRENT_DATA")" \
        "$(dirname -- "$PERSISTENT_AGENT_DATA_ROOT")" \
        "$PERSISTENT_AGENT_DATA_ROOT" || return $?
      [ "$rename_status" -ne 0 ] && return "$rename_status"
      return 1
    fi
    PERSISTENT_DETACHED=false
    PERSISTENT_ATTACHED_TO_RELEASE=true
    PERSISTENT_MOUNT_STATE_UNKNOWN=false
    [ "$rename_status" -ne 0 ] && return "$rename_status"
    return 1
  }
  if [ -d "$PERSISTENT_AGENT_DATA_ROOT" ]; then
    [ -z "$(find "$PERSISTENT_AGENT_DATA_ROOT" -mindepth 1 -print -quit)" ] \
      || die 'local-persistent-authority-not-empty'
    remove_empty_directory_durably "$PERSISTENT_AGENT_DATA_ROOT"
  fi
  detach_local_persistent_for_install
else
  invoke_mount_authority findmnt --json --mountpoint "$CURRENT_DATA" > "$EVIDENCE_DIR/findmnt-before.json"
  verify_findmnt_file "$EVIDENCE_DIR/findmnt-before.json" \
    "$PERSISTENT_AGENT_DATA_ROOT" "$CURRENT_DATA"
  detach_live_persistent_mount() {
    local unmount_status=0 mount_state probe_status=0 fsync_status=0
    if invoke_mount_authority umount "$CURRENT_DATA"; then
      :
    else
      unmount_status=$?
    fi
    PERSISTENT_MOUNT_STATE_UNKNOWN=true
    if invoke_mount_authority findmnt --json --mountpoint "$CURRENT_DATA" \
      > "$EVIDENCE_DIR/findmnt-after-umount.json"; then
      if verify_findmnt_file "$EVIDENCE_DIR/findmnt-after-umount.json" \
        "$PERSISTENT_AGENT_DATA_ROOT" "$CURRENT_DATA"; then
        mount_state=0
      else
        probe_status=$?
        mount_state=2
      fi
    else
      probe_status=$?
      if [ "$probe_status" -eq 1 ]; then
        mount_state=1
      else
        mount_state=2
      fi
    fi
    case "$mount_state" in
      0)
        PERSISTENT_ATTACHED_TO_RELEASE=true
        PERSISTENT_DETACHED=false
        PERSISTENT_MOUNT_STATE_UNKNOWN=false
        [ "$unmount_status" -ne 0 ] && return "$unmount_status"
        return 1
        ;;
      1)
        PERSISTENT_ATTACHED_TO_RELEASE=false
        PERSISTENT_DETACHED=true
        PERSISTENT_MOUNT_STATE_UNKNOWN=false
        fsync_directories "$CURRENT_DATA" "$(dirname -- "$CURRENT_DATA")" \
          || fsync_status=$?
        [ "$unmount_status" -ne 0 ] && return "$unmount_status"
        return "$fsync_status"
        ;;
      *)
        PERSISTENT_ATTACHED_TO_RELEASE=true
        PERSISTENT_DETACHED=false
        PERSISTENT_MOUNT_STATE_UNKNOWN=true
        [ "$unmount_status" -ne 0 ] && return "$unmount_status"
        [ "$probe_status" -ne 0 ] && return "$probe_status"
        return 1
        ;;
    esac
  }
  detach_live_persistent_mount
fi
write_mutation_state persistent-detached
fail_after detach-agent-data

# swap-release-root
write_mutation_state swap-release-root-armed
INSTALL_FAILURE_POINT=swap-release-root
[ -d "$RELEASE_ROOT" ] || die 'existing-release-root-required'
rename_release_root_to_old() {
  local rename_status=0
  if mv -- "$RELEASE_ROOT" "$OLD_ROOT"; then
    :
  else
    rename_status=$?
  fi
  if [ ! -e "$RELEASE_ROOT" ] && [ ! -L "$RELEASE_ROOT" ] \
    && [ -d "$OLD_ROOT" ] && [ ! -L "$OLD_ROOT" ]; then
    OLD_ROOT_READY=true
    return "$rename_status"
  elif [ -d "$RELEASE_ROOT" ] && [ ! -L "$RELEASE_ROOT" ] \
    && [ ! -e "$OLD_ROOT" ] && [ ! -L "$OLD_ROOT" ]; then
    OLD_ROOT_READY=false
    [ "$rename_status" -ne 0 ] && return "$rename_status"
    return 1
  else
    [ "$rename_status" -ne 0 ] && return "$rename_status"
    return 1
  fi
}
rename_release_root_to_old
fsync_directories "$RELEASE_PARENT"
activate_staging_root() {
  local rename_status=0
  if mv -- "$STAGING_ROOT" "$RELEASE_ROOT"; then
    :
  else
    rename_status=$?
  fi
  if [ ! -e "$STAGING_ROOT" ] && [ ! -L "$STAGING_ROOT" ] \
    && [ -d "$RELEASE_ROOT" ] && [ ! -L "$RELEASE_ROOT" ] \
    && [ -d "$OLD_ROOT" ] && [ ! -L "$OLD_ROOT" ]; then
    return "$rename_status"
  elif [ -d "$STAGING_ROOT" ] && [ ! -L "$STAGING_ROOT" ] \
    && [ ! -e "$RELEASE_ROOT" ] && [ ! -L "$RELEASE_ROOT" ] \
    && [ -d "$OLD_ROOT" ] && [ ! -L "$OLD_ROOT" ]; then
    [ "$rename_status" -ne 0 ] && return "$rename_status"
    return 1
  else
    [ "$rename_status" -ne 0 ] && return "$rename_status"
    return 1
  fi
}
activate_staging_root
fsync_directories "$RELEASE_PARENT"
remove_file_durably "$STAGING_OWNER_MARKER"
STAGING_CLEANUP_ARMED=false
mkdir -p -- "$RELEASE_ROOT/agent"
rm -rf -- "$RELEASE_ROOT/agent/data"
fsync_directories "$RELEASE_PARENT" "$RELEASE_ROOT" "$RELEASE_ROOT/agent"
write_mutation_state root-swapped
fail_after swap-release-root

INSTALL_FAILURE_POINT=materialize-environment-authority
[ "$(regular_file_sha256 "$RELEASE_ROOT/.env")" \
  = "$ENVIRONMENT_AUTHORITY_SHA256" ] \
  || die 'materialized-environment-authority-changed'

# restore-bind-agent-data
INSTALL_FAILURE_POINT=restore-bind-agent-data
if [ "$LOCAL_REHEARSAL" = true ]; then
  write_mutation_state recovery-restore-persistent-armed
  restore_local_persistent_for_recovery
  mkdir -- "$PERSISTENT_AGENT_DATA_ROOT"
  fsync_directories "$(dirname -- "$PERSISTENT_AGENT_DATA_ROOT")" \
    "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent"
  write_mutation_state persistent-restored
  fail_after restore-bind-agent-data
else
  mkdir -- "$RELEASE_ROOT/agent/data"
  write_mutation_state restore-bind-agent-data-armed
  PERSISTENT_MOUNT_STATE_UNKNOWN=true
  invoke_mount_authority mount --bind "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent/data"
  PERSISTENT_ATTACHED_TO_RELEASE=true
  PERSISTENT_DETACHED=false
  PERSISTENT_MOUNT_STATE_UNKNOWN=false
  fsync_directories "$RELEASE_ROOT/agent/data" "$RELEASE_ROOT/agent"
  write_mutation_state persistent-restored
fi

# verify-agent-data-mount, including agent/data/sitemap-bundles byte evidence.
INSTALL_FAILURE_POINT=verify-agent-data-mount
if [ "$LOCAL_REHEARSAL" != true ]; then
  invoke_mount_authority findmnt --json --mountpoint "$RELEASE_ROOT/agent/data" > "$EVIDENCE_DIR/findmnt-after.json"
  verify_findmnt_file "$EVIDENCE_DIR/findmnt-after.json" \
    "$PERSISTENT_AGENT_DATA_ROOT" "$RELEASE_ROOT/agent/data"
fi
snapshot_tree "$RELEASE_ROOT/agent/data" "$SNAPSHOT_AFTER"
cmp -s -- "$SNAPSHOT_BEFORE" "$SNAPSHOT_AFTER" || die 'persistent-agent-data-bytes-changed'

INSTALL_FAILURE_POINT=install-systemd-units
prepare_systemd_unit_attempt
write_mutation_state systemd-backup-preparing
prepare_systemd_unit_backup
write_mutation_state systemd-units-armed
install_systemd_units
run_authority_hook systemd-units "$UNIT_VERIFY_HOOK" \
  --unit-root "$SYSTEMD_UNIT_DESTINATION" \
  --manifest "$RELEASE_ROOT/launch-release-manifest.json"

verify_installed_release_authority \
  "$RELEASE_ROOT" "$PERSISTENT_AGENT_DATA_ROOT" \
  "$SYSTEMD_UNIT_DESTINATION" "$EVIDENCE_DIR/installed" \
  "$EVIDENCE_DIR/findmnt-after.json" "$LOCAL_REHEARSAL"

invoke_python - "$EVIDENCE_DIR/install-summary.json" \
  "$PINNED_ARCHIVE_SHA256" "$ENVIRONMENT_AUTHORITY_SHA256" \
  "$MIGRATION_GATE_EVIDENCE_SHA256" "$MIGRATION_GATE_MIGRATION_SET_SHA256" \
  "$MIGRATION_GATE_LATEST_VERSION" "$MIGRATION_GATE_LATEST_MIGRATION" \
  "$MIGRATION_GATE_OBSERVED_VERSION" "$MIGRATION_GATE_OBSERVED_MIGRATION" <<'PY'
import json
from pathlib import Path
import sys

def optional(value):
    return value or None

(
    summary_path,
    archive_sha256,
    environment_pin_sha256,
    migration_gate_evidence_sha256,
    migration_set_sha256,
    latest_version,
    latest_migration,
    observed_version,
    observed_migration,
) = sys.argv[1:]
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
    "archive_sha256": archive_sha256,
    "environment_pin_sha256": environment_pin_sha256,
    "migration_gate_evidence_sha256": optional(migration_gate_evidence_sha256),
    "migration_set_sha256": optional(migration_set_sha256),
    "migration_latest": (
        {"version": int(latest_version), "migration": latest_migration}
        if latest_version and latest_migration
        else None
    ),
    "observed_database": (
        {"version": int(observed_version), "migration": observed_migration}
        if observed_version and observed_migration
        else None
    ),
}
Path(summary_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

INSTALL_FAILURE_POINT=retire-old-root
write_mutation_state retire-old-root-armed
retire_old_root() {
  local rename_status=0
  if mv -- "$OLD_ROOT" "$RETIRED_ROOT"; then
    :
  else
    rename_status=$?
  fi
  if [ ! -e "$OLD_ROOT" ] && [ ! -L "$OLD_ROOT" ] \
    && [ -d "$RETIRED_ROOT" ] && [ ! -L "$RETIRED_ROOT" ] \
    && [ -d "$RELEASE_ROOT" ] && [ ! -L "$RELEASE_ROOT" ]; then
    OLD_ROOT_READY=false
    INSTALL_COMMITTED=true
    return "$rename_status"
  elif [ -d "$OLD_ROOT" ] && [ ! -L "$OLD_ROOT" ] \
    && [ ! -e "$RETIRED_ROOT" ] && [ ! -L "$RETIRED_ROOT" ] \
    && [ -d "$RELEASE_ROOT" ] && [ ! -L "$RELEASE_ROOT" ]; then
    OLD_ROOT_READY=true
    INSTALL_COMMITTED=false
    [ "$rename_status" -ne 0 ] && return "$rename_status"
    return 1
  else
    [ "$rename_status" -ne 0 ] && return "$rename_status"
    return 1
  fi
}
retire_old_root
[ "$(source_release_topology_sha256 "$RETIRED_ROOT")" \
  = "$SOURCE_RELEASE_TOPOLOGY_SHA256" ] \
  || die 'retired-root-topology-mismatch'
fsync_directories "$RELEASE_PARENT"
write_mutation_state committed-cleanup
INSTALL_FAILURE_POINT=remove-retired-old-root
tree_matches_bound_topology "$RETIRED_ROOT" \
  "$SOURCE_RELEASE_ROOT_IDENTITY" "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT" false \
  || die 'retired-root-topology-mismatch'
[ ! -e "$RETIRED_CLEANUP_ROOT" ] && [ ! -L "$RETIRED_CLEANUP_ROOT" ] \
  && [ ! -e "$RETIRED_CLEANUP_OWNER" ] \
  && [ ! -L "$RETIRED_CLEANUP_OWNER" ] \
  || die 'retired-cleanup-path-exists'
write_cleanup_owner_marker "$RETIRED_CLEANUP_OWNER" retired "$ATTEMPT_ID" \
  "$SOURCE_RELEASE_ROOT_IDENTITY" "$SOURCE_RELEASE_TOPOLOGY_SHA256" \
  || die 'retired-cleanup-owner-write-failed'
mv -- "$RETIRED_ROOT" "$RETIRED_CLEANUP_ROOT" \
  || die 'retired-old-root-quarantine-failed'
fsync_directories "$RELEASE_PARENT"
[ ! -e "$RETIRED_ROOT" ] && [ ! -L "$RETIRED_ROOT" ] \
  || die 'retired-old-root-quarantine-incomplete'
verify_cleanup_owner_marker "$RETIRED_CLEANUP_OWNER" retired "$ATTEMPT_ID" \
  "$SOURCE_RELEASE_ROOT_IDENTITY" "$SOURCE_RELEASE_TOPOLOGY_SHA256" \
  || die 'retired-cleanup-owner-mismatch'
tree_matches_bound_topology "$RETIRED_CLEANUP_ROOT" \
  "$SOURCE_RELEASE_ROOT_IDENTITY" "$SOURCE_RELEASE_TOPOLOGY_SNAPSHOT" true \
  || die 'retired-cleanup-topology-mismatch'
invoke_rm -rf -- "$RETIRED_CLEANUP_ROOT" \
  || die 'retired-old-root-cleanup-failed'
[ ! -e "$RETIRED_CLEANUP_ROOT" ] && [ ! -L "$RETIRED_CLEANUP_ROOT" ] \
  || die 'retired-old-root-cleanup-incomplete'
fsync_directories "$RELEASE_PARENT"
remove_file_durably "$RETIRED_CLEANUP_OWNER" \
  || die 'retired-cleanup-owner-remove-failed'
[ ! -e "$RETIRED_CLEANUP_OWNER" ] && [ ! -L "$RETIRED_CLEANUP_OWNER" ] \
  || die 'retired-cleanup-owner-remove-incomplete'
finalize_systemd_unit_cleanup
INSTALL_COMPLETE=true
clear_mutation_state
exit 0
