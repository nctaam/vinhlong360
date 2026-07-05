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
#   --migrate    apply additive schema migrations shipped in this deploy
#   --allow-dirty deploy the current dirty working tree (otherwise blocked)

set -euo pipefail

VPS="${VL360_DEPLOY_HOST:?Set VL360_DEPLOY_HOST, for example deploy@example.com}"
KEY="${VL360_DEPLOY_KEY:-$HOME/.ssh/vinhlong_vps}"
REMOTE="/opt/vinhlong360"
SSH="ssh -i $KEY -o ConnectTimeout=20"
SCP="scp -i $KEY"

DO_FRONTEND=0; DO_BACKEND=0; DO_DATA=0; DO_REPLACE=0; DO_BACKUP=1; DO_BUILD=1; DO_MIGRATE=0; ALLOW_DIRTY=0
for arg in "$@"; do
  case "$arg" in
    --frontend) DO_FRONTEND=1 ;;
    --backend)  DO_BACKEND=1 ;;
    --data)     DO_DATA=1; DO_BACKEND=1 ;;
    --all)      DO_FRONTEND=1; DO_BACKEND=1; DO_DATA=1; DO_MIGRATE=1 ;;
    --replace)  DO_REPLACE=1; DO_BACKEND=1; DO_DATA=1 ;;
    --migrate)  DO_MIGRATE=1; DO_BACKEND=1 ;;
    --no-backup) DO_BACKUP=0 ;;
    --skip-build) DO_BUILD=0 ;;
    --allow-dirty) ALLOW_DIRTY=1 ;;
    *) echo "Unknown flag: $arg" >&2; exit 2 ;;
  esac
done

if [ "$DO_FRONTEND" = 0 ] && [ "$DO_BACKEND" = 0 ]; then
  echo "Nothing to do. Pass --frontend / --backend / --data / --all (see header)." >&2
  exit 2
fi

if [ "$DO_BACKUP" = 0 ] && { [ "$DO_MIGRATE" = 1 ] || [ "$DO_REPLACE" = 1 ]; }; then
  echo "--no-backup is not allowed with --migrate or --replace." >&2
  exit 2
fi

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [ "$ALLOW_DIRTY" = 0 ] && [ -n "$(git status --porcelain)" ]; then
    echo "Working tree is dirty. Commit/stash changes or pass --allow-dirty intentionally." >&2
    exit 2
  fi
fi

TS="$(date +%Y%m%d-%H%M%S)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
echo "==> deploy $TS  (frontend=$DO_FRONTEND backend=$DO_BACKEND data=$DO_DATA replace=$DO_REPLACE migrate=$DO_MIGRATE backup=$DO_BACKUP)"

# 0. Pre-flight: connectivity + current health
echo "==> pre-flight health"
$SSH "$VPS" 'systemctl is-active vl-agent vl-nuxt >/dev/null && echo "services up" || echo "WARN: a service is down"'

# 1. Build frontend (local)
if [ "$DO_FRONTEND" = 1 ] && [ "$DO_BUILD" = 1 ]; then
  echo "==> building web-nuxt (npm run build)"
  # NOTE: do NOT set API_BASE to the public URL here. `apiBase` (nuxt.config) bakes BOTH the
  # prerender fetch AND the runtime routeRule proxy targets — pointing it at the public URL
  # makes the runtime nitro proxy /api/** → nginx → nitro (infinite loop → 500 outage).
  # Keep the localhost:8360 default so the runtime proxy hits the real backend.
  ( cd web-nuxt && NODE_OPTIONS="--max-old-space-size=4096" npm run build )
fi

# 2. Pack tarballs (local)
if [ "$DO_BACKEND" = 1 ]; then
  echo "==> packing agent + data"
  DATAJS=""; [ -f web/data.js ] && DATAJS="web/data.js"
  MIGRATIONS=""
  [ -d agent/migrations ] && MIGRATIONS="agent/migrations"
  GATE_SCRIPTS=""
  [ -f scripts/check_migration_gate.py ] && GATE_SCRIPTS="$GATE_SCRIPTS scripts/check_migration_gate.py"
  [ -f scripts/apply_migrations.py ] && GATE_SCRIPTS="$GATE_SCRIPTS scripts/apply_migrations.py"
  [ -f scripts/validate_data.py ] && GATE_SCRIPTS="$GATE_SCRIPTS scripts/validate_data.py"
  [ -f scripts/quality_budget.py ] && GATE_SCRIPTS="$GATE_SCRIPTS scripts/quality_budget.py"
  [ -f scripts/restore_drill.py ] && GATE_SCRIPTS="$GATE_SCRIPTS scripts/restore_drill.py"
  tar -czf "$TMP/vl-deploy.tar.gz" agent/*.py requirements.txt init.sql web/data.json $DATAJS $MIGRATIONS $GATE_SCRIPTS
fi
if [ "$DO_FRONTEND" = 1 ]; then
  if [ ! -f web-nuxt/.output/server/index.mjs ] || [ ! -f web-nuxt/.output/server/package.json ]; then
    echo "❌ .output/server thiếu index.mjs/package.json (build dở?) — abort, KHÔNG ship .output hỏng"
    exit 1
  fi
  echo "==> packing nuxt .output"
  tar -czf "$TMP/vl-nuxt-output.tar.gz" -C web-nuxt .output
fi

# 3. Backup prod (DB + rollback tarball)
if [ "$DO_BACKUP" = 1 ]; then
  echo "==> backing up prod (db + code)"
  $SSH "$VPS" "bash -s" <<EOF
set -e
cd $REMOTE
set -a; . ./.env; set +a
pg_dump -Fc "\$DATABASE_URL" -f /tmp/db-pre-deploy-$TS.dump && mv /tmp/db-pre-deploy-$TS.dump backups/ && echo "  db dump -> backups/db-pre-deploy-$TS.dump"
tar -czf backups/pre-deploy-$TS.tar.gz agent web/data.json web/media web-nuxt/.output 2>/dev/null && echo "  code snapshot -> backups/pre-deploy-$TS.tar.gz"
ls -t backups/pre-deploy-*.tar.gz 2>/dev/null | tail -n +7 | xargs -r rm -f
ls -t backups/db-pre-deploy-*.dump 2>/dev/null | tail -n +7 | xargs -r rm -f
echo "  rotated auto-backups (kept newest 6)"
EOF
fi

# 4. Ship tarballs
echo "==> uploading"
[ "$DO_BACKEND" = 1 ]  && $SCP "$TMP/vl-deploy.tar.gz" "$VPS:/tmp/"
[ "$DO_FRONTEND" = 1 ] && $SCP "$TMP/vl-nuxt-output.tar.gz" "$VPS:/tmp/"

# 5. Extract + install + (optional) data replace + restart
$SSH "$VPS" "DO_FRONTEND=$DO_FRONTEND DO_BACKEND=$DO_BACKEND DO_REPLACE=$DO_REPLACE DO_MIGRATE=$DO_MIGRATE bash -s" <<EOF
set -euo pipefail
cd $REMOTE

if [ "\$DO_BACKEND" = 1 ]; then
  echo "  extract agent + data"
  tar -xzf /tmp/vl-deploy.tar.gz -C $REMOTE/
  echo "  pip install"
  ./venv/bin/pip install -q -r requirements.txt
fi

if [ "\$DO_MIGRATE" = 1 ]; then
  echo "  schema migrations"
  set -a; . ./.env; set +a
  ./venv/bin/python scripts/apply_migrations.py --database-url "\$DATABASE_URL" --baseline-version 52 --init-baseline --init-sql init.sql
  ./venv/bin/python scripts/check_migration_gate.py --db-check --database-url "\$DATABASE_URL"
  ./venv/bin/python scripts/quality_budget.py --data web/data.json --record-db --database-url "\$DATABASE_URL" --source "deploy:$TS"
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
  ALLOW_DESTRUCTIVE_DB_REPLACE=1 PG_USE_POOL=false timeout 240 ./venv/bin/python agent/database.py --replace 2>&1 | tail -8
  [ \${PIPESTATUS[0]:-0} -eq 124 ] && { echo "  ❌ replace TIMEOUT 240s — abort (data cũ giữ nguyên, transaction rollback)"; exit 1; }
fi

echo "  restart services"
[ "\$DO_BACKEND" = 1 ] && systemctl restart vl-agent
# Audit vòng 2 fix #6: --backend ship cả bot_gateway.py nhưng trước đây không
# restart vl-bot → prod chạy code bot cũ trong RAM vô thời hạn.
[ "\$DO_BACKEND" = 1 ] && systemctl restart vl-bot
[ "\$DO_FRONTEND" = 1 ] && systemctl restart vl-nuxt
[ "\$DO_REPLACE" = 1 ] && systemctl restart vl-agent
sleep 6
systemctl is-active vl-agent vl-nuxt vl-bot
acode=000
for i in 1 2 3 4 5 6 7 8 9 10; do
  acode=\$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://127.0.0.1:8360/health 2>/dev/null || echo 000)
  [ "\$acode" = 200 ] && break; sleep 3
done
echo "  agent_health=\$acode"
[ "\$acode" = 200 ] || { echo "  agent health failed"; exit 1; }

rcode=\$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 http://127.0.0.1:8360/health/ready 2>/dev/null || echo 000)
echo "  agent_ready=\$rcode"
[ "\$rcode" = 200 ] || { echo "  agent readiness failed"; exit 1; }

echo "  cleanup /tmp"
rm -f /tmp/vl-deploy.tar.gz /tmp/vl-nuxt-output.tar.gz
EOF

# 6. Verify
echo "==> verify"
$SSH "$VPS" 'set -e
home=$(curl -s -o /dev/null -w "%{http_code}" --max-time 12 https://vinhlong360.vn/ || echo 000)
agent=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:8360/health || echo 000)
ready=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:8360/health/ready || echo 000)
# Bài học incident 2026-07-02: search 500 nhiều ngày mà /health vẫn 200 —
# endpoint lõi PHẢI nằm trong cổng verify, deploy hỏng search không được pass.
search=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://127.0.0.1:8360/api/search?q=deploy-check" || echo 000)
printf "  home=%s\n  agent_health=%s\n  agent_ready=%s\n  search=%s\n" "$home" "$agent" "$ready" "$search"
journalctl -u vl-agent --since "2 min ago" -p err --no-pager | tail -5 || true
[ "$home" = 200 ] && [ "$agent" = 200 ] && [ "$ready" = 200 ] && [ "$search" = 200 ]'
echo "==> deploy $TS DONE. Rollback: backups/pre-deploy-$TS.tar.gz + backups/db-pre-deploy-$TS.dump"
