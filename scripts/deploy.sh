#!/usr/bin/env bash
# scripts/deploy.sh — deploy vinhlong360 to the VPS via the proven tarball flow.
#
# Usage (run from repo root, in Git Bash):
#   scripts/deploy.sh --all                 # frontend + backend + data (data needs --replace to take effect)
#   scripts/deploy.sh --frontend            # only Nuxt .output
#   scripts/deploy.sh --backend             # only agent/*.py + requirements.txt (+ pip install)
#   scripts/deploy.sh --backend --data --replace   # backend + re-import data.json into prod Postgres
#   scripts/deploy.sh --frontend --no-backup       # skip prod backup (NOT recommended)
#
# Flags:
#   --frontend   build + ship web-nuxt/.output, npm install --omit=dev, restart vl-nuxt
#   --backend    ship agent/*.py + requirements.txt + web/data.json(+.js), pip install, restart vl-agent
#   --data       ship web/data.json (alias kept for clarity; backend already ships it)
#   --replace    DESTRUCTIVE: re-import data.json into prod Postgres (entities/rels/itineraries).
#                Requires a fresh prod DB dump first (done automatically unless --no-backup).
#   --no-backup  skip the prod DB + code rollback snapshot (dangerous)
#   --skip-build assume web-nuxt/.output is already built (don't run npm run build)
#
# Hard-won gotchas encoded here (see memory ref-vps-deploy):
#   * LIVE Nuxt output = $REMOTE/web-nuxt/.output (the top-level $REMOTE/.output is STALE/unused).
#   * MUST `rm -rf .output` before extracting (tar over existing symlinks => "File exists").
#   * .output/server needs `npm install --omit=dev` (Linux-native deps).
#   * data sync into Postgres needs ALLOW_DESTRUCTIVE_DB_REPLACE=1 (B7 lock) + restart to reload RAM cache.
#   * pg_dump to /tmp then move (peer-auth postgres user can't write root-owned backups/).
#   * NEVER touch prod .env (a parse error there crash-loops vl-agent: server.py hard-reads os.environ["LLM_API_KEY"]).

set -euo pipefail

VPS="root@66.42.57.202"
KEY="$HOME/.ssh/vinhlong_vps"
REMOTE="/opt/vinhlong360"
SSH="ssh -i $KEY -o ConnectTimeout=20"
SCP="scp -i $KEY"

DO_FRONTEND=0; DO_BACKEND=0; DO_DATA=0; DO_REPLACE=0; DO_BACKUP=1; DO_BUILD=1
for arg in "$@"; do
  case "$arg" in
    --frontend) DO_FRONTEND=1 ;;
    --backend)  DO_BACKEND=1 ;;
    --data)     DO_DATA=1; DO_BACKEND=1 ;;   # data ships with the backend tarball
    --all)      DO_FRONTEND=1; DO_BACKEND=1; DO_DATA=1 ;;
    --replace)  DO_REPLACE=1; DO_BACKEND=1; DO_DATA=1 ;;
    --no-backup) DO_BACKUP=0 ;;
    --skip-build) DO_BUILD=0 ;;
    *) echo "Unknown flag: $arg" >&2; exit 2 ;;
  esac
done

if [ "$DO_FRONTEND" = 0 ] && [ "$DO_BACKEND" = 0 ]; then
  echo "Nothing to do. Pass --frontend / --backend / --data / --all (see header)." >&2
  exit 2
fi

TS="$(date +%Y%m%d-%H%M%S)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "==> deploy $TS  (frontend=$DO_FRONTEND backend=$DO_BACKEND data=$DO_DATA replace=$DO_REPLACE backup=$DO_BACKUP)"

# 0. Pre-flight: connectivity + current health -------------------------------
echo "==> pre-flight health"
$SSH "$VPS" 'systemctl is-active vl-agent vl-nuxt >/dev/null && echo "services up" || echo "WARN: a service is down"'

# 1. Build frontend (local) --------------------------------------------------
if [ "$DO_FRONTEND" = 1 ] && [ "$DO_BUILD" = 1 ]; then
  echo "==> building web-nuxt (npm run build)"
  ( cd web-nuxt && npm run build )
fi

# 2. Pack tarballs (local) ---------------------------------------------------
if [ "$DO_BACKEND" = 1 ]; then
  echo "==> packing agent + data"
  DATAJS=""; [ -f web/data.js ] && DATAJS="web/data.js"
  tar -czf "$TMP/vl-deploy.tar.gz" agent/*.py requirements.txt web/data.json $DATAJS
fi
if [ "$DO_FRONTEND" = 1 ]; then
  echo "==> packing nuxt .output"
  tar -czf "$TMP/vl-nuxt-output.tar.gz" -C web-nuxt .output
fi

# 3. Backup prod (DB + rollback tarball) -------------------------------------
if [ "$DO_BACKUP" = 1 ]; then
  echo "==> backing up prod (db + code)"
  $SSH "$VPS" "bash -s" <<EOF
set -e
cd $REMOTE
set -a; . ./.env; set +a
pg_dump "\$DATABASE_URL" -f /tmp/db-pre-deploy-$TS.sql && mv /tmp/db-pre-deploy-$TS.sql backups/ && echo "  db dump -> backups/db-pre-deploy-$TS.sql"
tar -czf backups/pre-deploy-$TS.tar.gz agent web/data.json web-nuxt/.output 2>/dev/null && echo "  code snapshot -> backups/pre-deploy-$TS.tar.gz"
EOF
fi

# 4. Ship tarballs -----------------------------------------------------------
echo "==> uploading"
[ "$DO_BACKEND" = 1 ]  && $SCP "$TMP/vl-deploy.tar.gz" "$VPS:/tmp/"
[ "$DO_FRONTEND" = 1 ] && $SCP "$TMP/vl-nuxt-output.tar.gz" "$VPS:/tmp/"

# 5. Extract + install + (optional) data replace + restart -------------------
$SSH "$VPS" "DO_FRONTEND=$DO_FRONTEND DO_BACKEND=$DO_BACKEND DO_REPLACE=$DO_REPLACE bash -s" <<EOF
set -e
cd $REMOTE

if [ "\$DO_BACKEND" = 1 ]; then
  echo "  extract agent + data"
  tar -xzf /tmp/vl-deploy.tar.gz -C $REMOTE/
  echo "  pip install"
  ./venv/bin/pip install -q -r requirements.txt 2>&1 | tail -2 || true
fi

if [ "\$DO_FRONTEND" = 1 ]; then
  echo "  extract .output (rm -rf first — symlink gotcha)"
  rm -rf $REMOTE/web-nuxt/.output
  tar -xzf /tmp/vl-nuxt-output.tar.gz -C $REMOTE/web-nuxt/
  echo "  npm install --omit=dev"
  ( cd $REMOTE/web-nuxt/.output/server && npm install --omit=dev 2>&1 | tail -2 )
fi

if [ "\$DO_REPLACE" = 1 ]; then
  echo "  data --replace (destructive, guarded)"
  set -a; . ./.env; set +a
  ALLOW_DESTRUCTIVE_DB_REPLACE=1 ./venv/bin/python agent/database.py --replace 2>&1 | tail -8
fi

echo "  restart services"
[ "\$DO_BACKEND" = 1 ] && systemctl restart vl-agent
[ "\$DO_FRONTEND" = 1 ] && systemctl restart vl-nuxt
[ "\$DO_REPLACE" = 1 ] && systemctl restart vl-agent   # reload RAM cache after import
sleep 4
systemctl is-active vl-agent vl-nuxt

echo "  cleanup /tmp"
rm -f /tmp/vl-deploy.tar.gz /tmp/vl-nuxt-output.tar.gz
EOF

# 6. Verify ------------------------------------------------------------------
echo "==> verify"
$SSH "$VPS" 'curl -s -o /dev/null -w "  home=%{http_code}\n" https://vinhlong360.vn/; journalctl -u vl-agent --since "2 min ago" -p err --no-pager | tail -5 || true'
echo "==> deploy $TS DONE. Rollback: backups/pre-deploy-$TS.tar.gz + backups/db-pre-deploy-$TS.sql"
