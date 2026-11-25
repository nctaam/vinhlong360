#!/usr/bin/env bash
# Standardized multi-province VPS deployment script.
# Reads defaults from config/province.config.json (or --config <path>) so the same
# script deploys vinhlong360, dongthap360, cantho360, or any cloned province cleanly.
#
# Usage:
#   bash scripts/deploy_vps.sh --host root@66.42.57.202
#   bash scripts/deploy_vps.sh --dry-run --skip-build --config config/province.dongthap.example.json --host root@1.2.3.4

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)"
cd "$REPO_ROOT"

CONFIG_PATH="config/province.config.json"
HOST="${VPS_HOST:-}"
SSH_KEY="${VPS_SSH_KEY:-}"
APP_DIR_OVERRIDE=""
AGENT_SERVICE_OVERRIDE=""
WEB_SERVICE_OVERRIDE=""
BOT_SERVICE_OVERRIDE=""
SKIP_BUILD=0
SKIP_DB_SYNC=0
SKIP_MEDIA_SYNC=0
ALLOW_DIRTY=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: bash scripts/deploy_vps.sh [options]

Options:
  --host <user@host>        Target VPS SSH host (or env VPS_HOST)
  --key <path>              SSH private key path (or env VPS_SSH_KEY; defaults to config deploy.defaultSshKey)
  --config <path>           Province config JSON (default: config/province.config.json)
  --app-dir <path>          Override remote app directory (config deploy.appDir)
  --service-agent <name>    Override systemd agent service name
  --service-web <name>      Override systemd web service name
  --service-bot <name>      Override systemd bot service name
  --skip-build              Reuse existing web-nuxt/.output build
  --skip-db-sync            Skip SQLite DB upload and parity/invariant gate
  --skip-media-sync         Skip syncing web-nuxt/public/img/entities assets
  --allow-dirty             Allow deploying with uncommitted local git changes
  --dry-run                 Validate config, print deployment plan, and exit without mutating VPS
  -h, --help                Show this help
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --host)
      HOST="${2:?--host requires a value}"; shift 2 ;;
    --key)
      SSH_KEY="${2:?--key requires a value}"; shift 2 ;;
    --config)
      CONFIG_PATH="${2:?--config requires a value}"; shift 2 ;;
    --app-dir)
      APP_DIR_OVERRIDE="${2:?--app-dir requires a value}"; shift 2 ;;
    --service-agent)
      AGENT_SERVICE_OVERRIDE="${2:?--service-agent requires a value}"; shift 2 ;;
    --service-web)
      WEB_SERVICE_OVERRIDE="${2:?--service-web requires a value}"; shift 2 ;;
    --service-bot)
      BOT_SERVICE_OVERRIDE="${2:?--service-bot requires a value}"; shift 2 ;;
    --skip-build)
      SKIP_BUILD=1; shift ;;
    --skip-db-sync)
      SKIP_DB_SYNC=1; shift ;;
    --skip-media-sync)
      SKIP_MEDIA_SYNC=1; shift ;;
    --allow-dirty)
      ALLOW_DIRTY=1; shift ;;
    --dry-run)
      DRY_RUN=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2 ;;
  esac
done

PYTHON_LOCAL=""
for py_candidate in python3 python; do
  if command -v "$py_candidate" >/dev/null 2>&1 && "$py_candidate" --version >/dev/null 2>&1; then
    PYTHON_LOCAL="$py_candidate"
    break
  fi
done
[ -n "$PYTHON_LOCAL" ] || {
  echo "Error: working python3 or python is required locally to read $CONFIG_PATH" >&2
  exit 1
}

[ -f "$CONFIG_PATH" ] || {
  echo "Error: province config not found: $CONFIG_PATH" >&2
  exit 1
}

eval "$("$PYTHON_LOCAL" - "$CONFIG_PATH" <<'PY'
import json
import shlex
import sys
from pathlib import Path

cfg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
identity = cfg["identity"]
deploy = cfg["deploy"]
fields = {
    "CFG_SLUG": str(identity["slug"]),
    "CFG_DOMAIN": str(identity["domain"]),
    "CFG_SITE_URL": str(identity["siteUrl"]).rstrip("/"),
    "CFG_APP_DIR": str(deploy["appDir"]),
    "CFG_DB_FILENAME": str(deploy["dbFilename"]),
    "CFG_AGENT_SERVICE": str(deploy["agentService"]),
    "CFG_WEB_SERVICE": str(deploy["webService"]),
    "CFG_BOT_SERVICE": str(deploy.get("botService", "")),
    "CFG_AGENT_PORT": str(deploy["agentPort"]),
    "CFG_WEB_PORT": str(deploy["webPort"]),
    "CFG_SSH_KEY": str(deploy.get("defaultSshKey", "")),
}
for k, v in fields.items():
    print(f"{k}={shlex.quote(v)}")
PY
)"

APP_DIR="${APP_DIR_OVERRIDE:-$CFG_APP_DIR}"
AGENT_SERVICE="${AGENT_SERVICE_OVERRIDE:-$CFG_AGENT_SERVICE}"
WEB_SERVICE="${WEB_SERVICE_OVERRIDE:-$CFG_WEB_SERVICE}"
BOT_SERVICE="${BOT_SERVICE_OVERRIDE:-$CFG_BOT_SERVICE}"

if [ -z "$SSH_KEY" ] && [ -n "$CFG_SSH_KEY" ]; then
  case "$CFG_SSH_KEY" in
    "~"/*) SSH_KEY="$HOME/${CFG_SSH_KEY#\~/}" ;;
    *) SSH_KEY="$CFG_SSH_KEY" ;;
  esac
fi

[ -n "$HOST" ] || {
  echo "Error: pass --host <user@host> or set VPS_HOST" >&2
  exit 2
}

for val in "$HOST" "$APP_DIR" "$AGENT_SERVICE" "$WEB_SERVICE"; do
  case "$val" in
    *[!A-Za-z0-9._:/@-]*|"")
      echo "Error: unsupported characters in parameter: $val" >&2
      exit 2 ;;
  esac
done

case "$APP_DIR" in
  /*) ;;
  *) echo "Error: app-dir must be an absolute path: $APP_DIR" >&2; exit 2 ;;
esac

if [ "$ALLOW_DIRTY" = 0 ] && command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [ -n "$(git status --porcelain --untracked-files=all)" ]; then
    echo "Error: working tree is dirty. Commit changes or pass --allow-dirty." >&2
    exit 1
  fi
fi

TS="$(date +%Y%m%d-%H%M%S)"
LOCAL_DB_PATH="agent/data/${CFG_DB_FILENAME}"
REMOTE_TMP="/tmp/deploy_${CFG_SLUG}_${TS}"

echo "==> Deploy plan (${CFG_SLUG} -> ${HOST})"
echo "  config:        ${CONFIG_PATH}"
echo "  site_url:      ${CFG_SITE_URL}"
echo "  app_dir:       ${APP_DIR}"
echo "  db_file:       ${LOCAL_DB_PATH}"
echo "  services:      agent=${AGENT_SERVICE} (:${CFG_AGENT_PORT}), web=${WEB_SERVICE} (:${CFG_WEB_PORT}), bot=${BOT_SERVICE:-none}"
echo "  ssh_key:       ${SSH_KEY:-<default-agent>}"
echo "  flags:         skip_build=${SKIP_BUILD} skip_db_sync=${SKIP_DB_SYNC} skip_media_sync=${SKIP_MEDIA_SYNC}"

if [ "$DRY_RUN" = 1 ]; then
  echo "==> dry-run complete (no SSH/build/mutating actions executed)"
  exit 0
fi

SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=20)
SCP_OPTS=(-o BatchMode=yes -o ConnectTimeout=20)
if [ -n "$SSH_KEY" ]; then
  [ -f "$SSH_KEY" ] || { echo "Error: SSH key not found: $SSH_KEY" >&2; exit 1; }
  SSH_OPTS+=(-i "$SSH_KEY")
  SCP_OPTS+=(-i "$SSH_KEY")
fi
SSH=(ssh "${SSH_OPTS[@]}" -- "$HOST")
SCP=(scp "${SCP_OPTS[@]}" --)

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/deploy_${CFG_SLUG}.XXXXXX")"
cleanup() {
  local rc=$?
  rm -rf -- "$TMP_DIR" || true
  if [ "$rc" -ne 0 ]; then
    echo "Deploy aborted (exit=$rc). Remote staging preserved/cleaned best-effort." >&2
  fi
}
trap cleanup EXIT

echo "==> Pre-flight SSH check"
"${SSH[@]}" true

if [ "$SKIP_BUILD" = 0 ]; then
  echo "==> Building web-nuxt (API_BASE=http://127.0.0.1:${CFG_AGENT_PORT})"
  (
    cd "$REPO_ROOT/web-nuxt"
    API_BASE="http://127.0.0.1:${CFG_AGENT_PORT}" NODE_OPTIONS="--max-old-space-size=4096" npm run build
  )
fi

[ -f "web-nuxt/.output/server/index.mjs" ] || {
  echo "Error: missing web-nuxt/.output/server/index.mjs" >&2
  exit 1
}

echo "==> Packaging code, config, and Nuxt output"
CODE_TAR="$TMP_DIR/repo_sync.tar.gz"
OUTPUT_TAR="$TMP_DIR/nuxt_output.tar.gz"
MEDIA_TAR="$TMP_DIR/media_entities.tar.gz"
HAS_MEDIA_TAR=0
HAS_DB_FILE=0

tar -czf "$CODE_TAR" \
  --exclude=".env" \
  --exclude="agent/.env" \
  --exclude="agent/data/*.db*" \
  --exclude="**/__pycache__" \
  --exclude="*.pyc" \
  --exclude=".pytest_cache" \
  --exclude=".tmp" \
  agent config/province.config.json scripts web/data.json

tar -czf "$OUTPUT_TAR" -C web-nuxt .output

if [ "$SKIP_MEDIA_SYNC" = 0 ] && [ -d "web-nuxt/public/img/entities" ]; then
  tar -czf "$MEDIA_TAR" -C web-nuxt/public/img entities
  HAS_MEDIA_TAR=1
fi

if [ "$SKIP_DB_SYNC" = 0 ] && [ -f "$LOCAL_DB_PATH" ]; then
  HAS_DB_FILE=1
fi

echo "==> Staging artifacts on ${HOST}:${REMOTE_TMP}"
"${SSH[@]}" "mkdir -p '$REMOTE_TMP'"
"${SCP[@]}" "$CODE_TAR" "$HOST:$REMOTE_TMP/repo_sync.tar.gz"
"${SCP[@]}" "$OUTPUT_TAR" "$HOST:$REMOTE_TMP/nuxt_output.tar.gz"
if [ "$HAS_MEDIA_TAR" = 1 ]; then
  "${SCP[@]}" "$MEDIA_TAR" "$HOST:$REMOTE_TMP/media_entities.tar.gz"
fi
if [ "$HAS_DB_FILE" = 1 ]; then
  "${SCP[@]}" "$LOCAL_DB_PATH" "$HOST:$REMOTE_TMP/${CFG_DB_FILENAME}"
fi

echo "==> Backing up, verifying DB/CTI invariants, and swapping release atomically"
"${SSH[@]}" "APP_DIR='$APP_DIR' REMOTE_TMP='$REMOTE_TMP' TS='$TS' DB_FILENAME='$CFG_DB_FILENAME' AGENT_SERVICE='$AGENT_SERVICE' WEB_SERVICE='$WEB_SERVICE' BOT_SERVICE='$BOT_SERVICE' AGENT_PORT='$CFG_AGENT_PORT' WEB_PORT='$CFG_WEB_PORT' SKIP_DB_SYNC='$SKIP_DB_SYNC' HAS_DB_FILE='$HAS_DB_FILE' HAS_MEDIA_TAR='$HAS_MEDIA_TAR' bash -s" <<'REMOTE_EOF'
set -euo pipefail

VENV_PY="${APP_DIR}/venv/bin/python"
[ -x "$VENV_PY" ] || { echo "Error: missing remote venv python at $VENV_PY" >&2; exit 1; }

BACKUP_DIR="${APP_DIR}/backups/deploy-${TS}"
mkdir -p "$BACKUP_DIR"

if [ -f "${APP_DIR}/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  source "${APP_DIR}/.env"
  set +a
fi

if [ -n "${DATABASE_URL:-}" ] && command -v pg_dump >/dev/null 2>&1; then
  echo "  -> Backing up PostgreSQL database"
  pg_dump "$DATABASE_URL" > "${BACKUP_DIR}/postgres-${TS}.sql"
fi

if [ -f "${APP_DIR}/agent/data/${DB_FILENAME}" ]; then
  cp -a "${APP_DIR}/agent/data/${DB_FILENAME}" "${BACKUP_DIR}/${DB_FILENAME}"
fi

if [ -d "${APP_DIR}/web-nuxt/.output" ]; then
  tar -czf "${BACKUP_DIR}/nuxt-output-${TS}.tar.gz" -C "${APP_DIR}/web-nuxt" .output
fi

echo "  -> Extracting updated code and config (preserving .env)"
tar -xzf "${REMOTE_TMP}/repo_sync.tar.gz" -C "$APP_DIR"

if [ "$SKIP_DB_SYNC" = 0 ]; then
  if [ "$HAS_DB_FILE" = 1 ]; then
    mkdir -p "${APP_DIR}/agent/data"
    install -m 644 "${REMOTE_TMP}/${DB_FILENAME}" "${APP_DIR}/agent/data/${DB_FILENAME}"
  fi

  if [ -n "${DATABASE_URL:-}" ]; then
    echo "  -> Verifying Postgres CTI invariants and entity_details parity"
    "$VENV_PY" "${APP_DIR}/scripts/verify_entity_invariants.py" --json
    "$VENV_PY" "${APP_DIR}/scripts/verify_entity_details_parity.py"
  fi
fi

if [ "$HAS_MEDIA_TAR" = 1 ]; then
  echo "  -> Syncing entity .webp assets"
  mkdir -p "${APP_DIR}/web-nuxt/public/img"
  tar -xzf "${REMOTE_TMP}/media_entities.tar.gz" -C "${APP_DIR}/web-nuxt/public/img"
fi

echo "  -> Swapping web-nuxt/.output atomically"
mkdir -p "${APP_DIR}/web-nuxt"
rm -rf "${APP_DIR}/web-nuxt/.output.next" "${APP_DIR}/web-nuxt/.output.prev"
mkdir -p "${APP_DIR}/web-nuxt/.output.next"
tar -xzf "${REMOTE_TMP}/nuxt_output.tar.gz" -C "${APP_DIR}/web-nuxt/.output.next" --strip-components=1
if [ -d "${APP_DIR}/web-nuxt/.output" ]; then
  mv "${APP_DIR}/web-nuxt/.output" "${APP_DIR}/web-nuxt/.output.prev"
fi
mv "${APP_DIR}/web-nuxt/.output.next" "${APP_DIR}/web-nuxt/.output"
rm -rf "${APP_DIR}/web-nuxt/.output.prev"

echo "  -> Restarting systemd services"
systemctl restart "$AGENT_SERVICE"
systemctl restart "$WEB_SERVICE"
if [ -n "$BOT_SERVICE" ] && systemctl is-enabled "$BOT_SERVICE" >/dev/null 2>&1; then
  systemctl restart "$BOT_SERVICE"
fi

echo "  -> Waiting for local agent health on :${AGENT_PORT}"
ready=0
for _ in $(seq 1 30); do
  if curl -fsS --max-time 3 "http://127.0.0.1:${AGENT_PORT}/health" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
[ "$ready" = 1 ] || { echo "Error: ${AGENT_SERVICE} failed to respond on /health" >&2; exit 1; }

curl -fsS --max-time 5 --retry 5 --retry-delay 1 --retry-connrefused \
  "http://127.0.0.1:${WEB_PORT}/api/stats" >/dev/null

rm -rf "$REMOTE_TMP"
REMOTE_EOF

echo "==> Public smoke checks against ${CFG_SITE_URL}"
health_code="$(curl -s -o /dev/null -w "%{http_code}" --max-time 12 "${CFG_SITE_URL}/api/health" || echo 000)"
stats_code="$(curl -s -o /dev/null -w "%{http_code}" --max-time 12 "${CFG_SITE_URL}/api/stats" || echo 000)"
home_code="$(curl -s -o /dev/null -w "%{http_code}" --max-time 12 "${CFG_SITE_URL}/" || echo 000)"
echo "  health=${health_code} stats=${stats_code} home=${home_code}"
[ "$health_code" = "200" ] && [ "$stats_code" = "200" ] && [ "$home_code" = "200" ] || {
  echo "Error: public smoke check failed (health=$health_code stats=$stats_code home=$home_code)" >&2
  exit 1
}

echo "==> Deploy ${CFG_SLUG} DONE (${TS})"
