#!/usr/bin/env bash
# Atomically switch the reviewed Nginx maintenance selector. This primitive
# validates and tests configuration only; callers own the later process handoff.
set -euo pipefail
umask 077

die() {
  printf 'maintenance_mode: %s\n' "$1" >&2
  exit 1
}

usage() {
  printf 'usage: maintenance_mode.sh enable|disable --operator-cidr CIDR\n' >&2
  exit 2
}

ACTION="${1:-}"
shift || usage
case "$ACTION" in
  enable|disable) ;;
  *) usage ;;
esac

OPERATOR_CIDR=''
while (($#)); do
  case "$1" in
    --operator-cidr)
      (($# >= 2)) || die 'missing-operator-cidr'
      [[ -z "$OPERATOR_CIDR" ]] || die 'duplicate-operator-cidr'
      OPERATOR_CIDR="$2"
      shift 2
      ;;
    *)
      die 'unknown-option'
      ;;
  esac
done
[[ -n "$OPERATOR_CIDR" ]] || die 'missing-operator-cidr'
[[ "$OPERATOR_CIDR" != *$'\n'* && "$OPERATOR_CIDR" != *$'\r'* ]] \
  || die 'invalid-cidr'
[[ "$OPERATOR_CIDR" != *'__OPERATOR_CIDR__'* ]] || die 'invalid-cidr'

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)" \
  || die 'unsafe-source-path'
PROJECT_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)" \
  || die 'unsafe-source-path'
SOURCE_DIR="${VL360_MAINTENANCE_SOURCE_DIR:-${MAINTENANCE_SOURCE_DIR:-$PROJECT_ROOT/ops/nginx/maintenance}}"
RUNTIME_DIR="${VL360_MAINTENANCE_DIR:-${MAINTENANCE_DIR:-${NGINX_MAINTENANCE_DIR:-/etc/nginx/vl360-maintenance}}}"
NGINX_BIN="${VL360_NGINX_BIN:-${MAINTENANCE_NGINX_BIN:-${NGINX_BIN:-nginx}}}"
PYTHON_BIN="${VL360_PYTHON_BIN:-python}"

is_absolute_path() {
  case "$1" in
    /*|[A-Za-z]:[\\/]*) return 0 ;;
    *) return 1 ;;
  esac
}

assert_safe_directory() {
  local directory="$1"
  is_absolute_path "$directory" || die 'unsafe-maintenance-path'
  [[ "$directory" != *'/../'* && "$directory" != */.. && "$directory" != ../* ]] \
    || die 'unsafe-maintenance-path'
  [[ "$directory" != '/' && -d "$directory" && ! -L "$directory" ]] \
    || die 'unsafe-maintenance-path'

  local current="$directory"
  while [[ "$current" != '/' && "$current" != '.' && -n "$current" ]]; do
    [[ ! -L "$current" ]] || die 'unsafe-maintenance-path'
    current="$(dirname -- "$current")"
  done
}

assert_regular_file() {
  local path="$1"
  [[ -f "$path" && ! -L "$path" ]] || die 'missing-maintenance-include'
}

assert_safe_directory "$SOURCE_DIR"
assert_safe_directory "$RUNTIME_DIR"
assert_regular_file "$SOURCE_DIR/http-context.conf.template"
assert_regular_file "$SOURCE_DIR/server-enabled.conf"
assert_regular_file "$SOURCE_DIR/server-disabled.conf"

HTTP_CONTEXT="$RUNTIME_DIR/http-context.conf"
SERVER_ENABLED="$RUNTIME_DIR/server-enabled.conf"
SERVER_DISABLED="$RUNTIME_DIR/server-disabled.conf"
SELECTOR="$RUNTIME_DIR/active-server.conf"
assert_regular_file "$HTTP_CONTEXT"
assert_regular_file "$SERVER_ENABLED"
assert_regular_file "$SERVER_DISABLED"
[[ -L "$SELECTOR" ]] || die 'missing-maintenance-selector'

SELECTOR_TARGET="$(readlink -- "$SELECTOR" 2>/dev/null)" \
  || die 'invalid-maintenance-selector'
case "$SELECTOR_TARGET" in
  server-enabled.conf|server-disabled.conf) ;;
  *) die 'invalid-maintenance-selector' ;;
esac
assert_regular_file "$RUNTIME_DIR/$SELECTOR_TARGET"

if ! CANONICAL_CIDR="$("$PYTHON_BIN" - "$OPERATOR_CIDR" 2>/dev/null <<'PY'
import ipaddress
import sys

try:
    print(ipaddress.ip_network(sys.argv[1], strict=False))
except (TypeError, ValueError):
    raise SystemExit(1)
PY
)"; then
  die 'invalid-cidr'
fi
[[ -n "$CANONICAL_CIDR" ]] || die 'invalid-cidr'
[[ "$CANONICAL_CIDR" != *$'\n'* && "$CANONICAL_CIDR" != *$'\r'* ]] \
  || die 'invalid-cidr'

DESIRED_TARGET='server-disabled.conf'
[[ "$ACTION" == enable ]] && DESIRED_TARGET='server-enabled.conf'

TMP_FILES=()
ROLLBACK_NEEDED=0

cleanup() {
  local path
  for path in "${TMP_FILES[@]:-}"; do
    [[ -n "$path" ]] && rm -f -- "$path" >/dev/null 2>&1 || true
  done
}

file_digest() {
  "$PYTHON_BIN" - "$1" 2>/dev/null <<'PY'
from hashlib import sha256
from pathlib import Path
import sys

print(sha256(Path(sys.argv[1]).read_bytes()).hexdigest())
PY
}

rollback() {
  local failed=0
  if ! mv -Tf -- "${ROLLBACK_HTTP:?}" "$HTTP_CONTEXT" >/dev/null 2>&1; then
    failed=1
  fi
  if ! mv -Tf -- "${ROLLBACK_ENABLED:?}" "$SERVER_ENABLED" >/dev/null 2>&1; then
    failed=1
  fi
  if ! mv -Tf -- "${ROLLBACK_DISABLED:?}" "$SERVER_DISABLED" >/dev/null 2>&1; then
    failed=1
  fi
  if ! mv -Tf -- "${ROLLBACK_SELECTOR:?}" "$SELECTOR" >/dev/null 2>&1; then
    failed=1
  fi

  [[ "$(file_digest "$HTTP_CONTEXT" || true)" == "$PRIOR_HTTP_DIGEST" ]] || failed=1
  [[ "$(file_digest "$SERVER_ENABLED" || true)" == "$PRIOR_ENABLED_DIGEST" ]] \
    || failed=1
  [[ "$(file_digest "$SERVER_DISABLED" || true)" == "$PRIOR_DISABLED_DIGEST" ]] \
    || failed=1
  [[ -L "$SELECTOR" ]] || failed=1
  [[ "$(readlink -- "$SELECTOR" 2>/dev/null || true)" == "$SELECTOR_TARGET" ]] \
    || failed=1
  return "$failed"
}

on_exit() {
  local status=$?
  if ((ROLLBACK_NEEDED)); then
    if ! rollback; then
      status=1
    fi
  fi
  cleanup
  exit "$status"
}
trap on_exit EXIT
trap 'exit 1' HUP INT TERM

make_temp_file() {
  local destination_variable="$1"
  local template="$2"
  local path
  path="$(mktemp "$RUNTIME_DIR/$template.XXXXXX.tmp" 2>/dev/null)" \
    || die 'temporary-file-failed'
  TMP_FILES+=("$path")
  chmod 600 "$path" >/dev/null 2>&1 || die 'temporary-file-failed'
  printf -v "$destination_variable" '%s' "$path"
}

make_temp_selector() {
  local destination_variable="$1"
  local target="$2"
  local path
  path="$(mktemp "$RUNTIME_DIR/.active-server.conf.XXXXXX.tmp" 2>/dev/null)" \
    || die 'temporary-selector-failed'
  TMP_FILES+=("$path")
  rm -f -- "$path" >/dev/null 2>&1 || die 'temporary-selector-failed'
  ln -s -- "$target" "$path" >/dev/null 2>&1 || die 'temporary-selector-failed'
  printf -v "$destination_variable" '%s' "$path"
}

make_temp_file RENDERED_HTTP '.http-context.conf'
make_temp_file RENDERED_ENABLED '.server-enabled.conf'
make_temp_file RENDERED_DISABLED '.server-disabled.conf'
make_temp_selector RENDERED_SELECTOR "$DESIRED_TARGET"

if ! "$PYTHON_BIN" - "$SOURCE_DIR/http-context.conf.template" \
  "$RENDERED_HTTP" "$CANONICAL_CIDR" >/dev/null 2>&1 <<'PY'
from pathlib import Path
import sys

template = Path(sys.argv[1]).read_text(encoding="utf-8")
if template.count("__OPERATOR_CIDR__") != 1:
    raise SystemExit(1)
Path(sys.argv[2]).write_text(
    template.replace("__OPERATOR_CIDR__", sys.argv[3]),
    encoding="utf-8",
)
PY
then
  die 'render-failed'
fi
if ! cp -- "$SOURCE_DIR/server-enabled.conf" "$RENDERED_ENABLED" >/dev/null 2>&1; then
  die 'copy-failed'
fi
if ! cp -- "$SOURCE_DIR/server-disabled.conf" "$RENDERED_DISABLED" >/dev/null 2>&1; then
  die 'copy-failed'
fi
cmp -s -- "$SOURCE_DIR/server-enabled.conf" "$RENDERED_ENABLED" \
  || die 'copy-failed'
cmp -s -- "$SOURCE_DIR/server-disabled.conf" "$RENDERED_DISABLED" \
  || die 'copy-failed'

make_temp_file ROLLBACK_HTTP '.rollback-http'
make_temp_file ROLLBACK_ENABLED '.rollback-enabled'
make_temp_file ROLLBACK_DISABLED '.rollback-disabled'
make_temp_selector ROLLBACK_SELECTOR "$SELECTOR_TARGET"
if ! cp -- "$HTTP_CONTEXT" "$ROLLBACK_HTTP" >/dev/null 2>&1 \
  || ! cp -- "$SERVER_ENABLED" "$ROLLBACK_ENABLED" >/dev/null 2>&1 \
  || ! cp -- "$SERVER_DISABLED" "$ROLLBACK_DISABLED" >/dev/null 2>&1; then
  die 'backup-failed'
fi

PRIOR_HTTP_DIGEST="$(file_digest "$HTTP_CONTEXT")" || die 'backup-failed'
PRIOR_ENABLED_DIGEST="$(file_digest "$SERVER_ENABLED")" || die 'backup-failed'
PRIOR_DISABLED_DIGEST="$(file_digest "$SERVER_DISABLED")" || die 'backup-failed'
ROLLBACK_NEEDED=1

if ! mv -Tf -- "$RENDERED_HTTP" "$HTTP_CONTEXT" >/dev/null 2>&1 \
  || ! mv -Tf -- "$RENDERED_ENABLED" "$SERVER_ENABLED" >/dev/null 2>&1 \
  || ! mv -Tf -- "$RENDERED_DISABLED" "$SERVER_DISABLED" >/dev/null 2>&1 \
  || ! mv -Tf -- "$RENDERED_SELECTOR" "$SELECTOR" >/dev/null 2>&1; then
  die 'atomic-replace-failed'
fi

if ! "$NGINX_BIN" -t >/dev/null 2>&1; then
  die 'nginx-config-test-failed'
fi

ROLLBACK_NEEDED=0
exit 0
