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

# Load the same admission primitive that is staged to the target. The local
# source is definition-only; remote close/reopen calls use the staged copy.
source "$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/ops" && pwd -P)/deploy_launch_admission.sh"

VPS="${VL360_DEPLOY_HOST:?Set VL360_DEPLOY_HOST, for example deploy@example.com}"
KEY="${VL360_DEPLOY_KEY:-$HOME/.ssh/vinhlong_vps}"
REMOTE="/opt/vinhlong360"
case "$VPS" in
  *[!A-Za-z0-9._:@-]*|"")
    echo "Set VL360_DEPLOY_HOST to a simple user@host value" >&2
    exit 2
    ;;
esac
SSH=(ssh -i "$KEY" -o ConnectTimeout=20 -- "$VPS")
SCP=(scp -i "$KEY" --)
OPERATOR_CIDR="${VL360_OPERATOR_CIDR:?Set VL360_OPERATOR_CIDR, for example 203.0.113.10/32}"
case "$OPERATOR_CIDR" in
  *[!0-9A-Fa-f:./]*|"")
    echo "VL360_OPERATOR_CIDR contains unsupported characters" >&2
    exit 2
    ;;
esac

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
LAUNCH_STAGE=""
REMOTE_STAGE_PRESERVE=0

cleanup_remote_stage() {
  if [ "$REMOTE_STAGE_PRESERVE" = 0 ] && [ -n "$LAUNCH_STAGE" ]; then
    "${SSH[@]}" "rm -rf -- '$LAUNCH_STAGE'" || {
      echo "warning: failed to clean pre-close remote stage $LAUNCH_STAGE" >&2
    }
  fi
}

cleanup_deploy() {
  local status=$?
  cleanup_remote_stage
  rm -rf "$TMP"
  exit "$status"
}

trap cleanup_deploy EXIT
echo "==> deploy $TS  (frontend=$DO_FRONTEND backend=$DO_BACKEND data=$DO_DATA replace=$DO_REPLACE migrate=$DO_MIGRATE backup=$DO_BACKUP)"

# 0. Pre-flight: verify that the remote command path is reachable. Service
# health is checked after the launch boundary; it must not block safe-closed
# Nuxt admission or force a public reopen.
echo "==> pre-flight connectivity"
"${SSH[@]}" true

# 1. Build frontend (local)
if [ "$DO_FRONTEND" = 1 ] && [ "$DO_BUILD" = 1 ]; then
  echo "==> building web-nuxt (npm run build)"
  export BUILD_REVISION="$(git rev-parse --verify HEAD)"
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
  [ -f scripts/ops/deploy_launch_admission.sh ] && GATE_SCRIPTS="$GATE_SCRIPTS scripts/ops/deploy_launch_admission.sh"
  [ -f scripts/ops/probe_launch_boundary.py ] && GATE_SCRIPTS="$GATE_SCRIPTS scripts/ops/probe_launch_boundary.py"
  [ -f scripts/ops/socket_boundary_probe.py ] && GATE_SCRIPTS="$GATE_SCRIPTS scripts/ops/socket_boundary_probe.py"
  [ -f scripts/ops/maintenance_mode.sh ] && GATE_SCRIPTS="$GATE_SCRIPTS scripts/ops/maintenance_mode.sh"
  tar -czf "$TMP/vl-deploy.tar.gz" agent/*.py requirements.txt init.sql config web/data.json $DATAJS $MIGRATIONS $GATE_SCRIPTS
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
  "${SSH[@]}" bash -s <<EOF
set -e
cd $REMOTE
set -a; . ./.env; set +a
pg_dump -Fc "\$DATABASE_URL" -f /tmp/db-pre-deploy-$TS.dump && mv /tmp/db-pre-deploy-$TS.dump backups/ && echo "  db dump -> backups/db-pre-deploy-$TS.dump"
snapshot_members=(agent web/data.json web/media web-nuxt/.output)
[ -d config ] && snapshot_members+=(config)
snapshot_archive="backups/pre-deploy-$TS.tar.gz"
snapshot_tmp="\$snapshot_archive.tmp.\$\$"
rm -f "\$snapshot_tmp"
if ! tar -czf "\$snapshot_tmp" "\${snapshot_members[@]}" 2>/dev/null; then
  rm -f "\$snapshot_tmp"
  exit 1
fi
if ! mv -f "\$snapshot_tmp" "\$snapshot_archive"; then
  rm -f "\$snapshot_tmp"
  exit 1
fi
echo "  code snapshot -> \$snapshot_archive"
ls -t backups/pre-deploy-*.tar.gz 2>/dev/null | tail -n +7 | xargs -r rm -f
ls -t backups/db-pre-deploy-*.dump 2>/dev/null | tail -n +7 | xargs -r rm -f
echo "  rotated auto-backups (kept newest 6)"
EOF
fi

# 4. Stage the launch-admission primitive before closing traffic. This is an
# operational helper upload only; release extraction/install happens after the
# remote close/probe has passed.
LAUNCH_STAGE="$("${SSH[@]}" 'umask 077; mktemp -d /tmp/vl360-launch-admission.XXXXXXXXXX')"
case "$LAUNCH_STAGE" in
  /tmp/vl360-launch-admission.*) ;;
  *) echo "remote mktemp returned an unexpected launch stage" >&2; exit 1 ;;
esac
LAUNCH_ID="${LAUNCH_STAGE##*/}"
"${SSH[@]}" "install -d -m 700 -- '$LAUNCH_STAGE/archives' '$LAUNCH_STAGE/evidence' '$LAUNCH_STAGE/maintenance'"
LAUNCH_FILES=(
  scripts/ops/deploy_launch_admission.sh
  scripts/ops/probe_launch_boundary.py
  scripts/ops/socket_boundary_probe.py
  scripts/ops/maintenance_mode.sh
)
MAINTENANCE_FILES=(
  ops/nginx/maintenance/http-context.conf.template
  ops/nginx/maintenance/server-enabled.conf
  ops/nginx/maintenance/server-disabled.conf
)
for launch_file in "${LAUNCH_FILES[@]}"; do
  [ -f "$launch_file" ] || { echo "Missing launch admission helper: $launch_file" >&2; exit 1; }
done
for maintenance_file in "${MAINTENANCE_FILES[@]}"; do
  [ -f "$maintenance_file" ] || { echo "Missing maintenance source: $maintenance_file" >&2; exit 1; }
done
"${SCP[@]}" "${LAUNCH_FILES[@]}" "$VPS:$LAUNCH_STAGE/"
"${SCP[@]}" "${MAINTENANCE_FILES[@]}" "$VPS:$LAUNCH_STAGE/maintenance/"

# 5. Ship tarballs
echo "==> uploading"
[ "$DO_BACKEND" = 1 ]  && "${SCP[@]}" "$TMP/vl-deploy.tar.gz" "$VPS:$LAUNCH_STAGE/archives/vl-deploy.tar.gz"
[ "$DO_FRONTEND" = 1 ] && "${SCP[@]}" "$TMP/vl-nuxt-output.tar.gz" "$VPS:$LAUNCH_STAGE/archives/vl-nuxt-output.tar.gz"

# 6a. Close traffic remotely, then return to this operator machine to prove
# that the configured operator source reaches the reviewed maintenance surface.
REMOTE_STAGE_PRESERVE=1
"${SSH[@]}" "OPERATOR_CIDR=$OPERATOR_CIDR LAUNCH_STAGE=$LAUNCH_STAGE bash -s" <<EOF
set -euo pipefail
cd $REMOTE
export READINESS_EVIDENCE="\$LAUNCH_STAGE/evidence/readiness.json"
export SOCKET_BOUNDARY_EVIDENCE="\$LAUNCH_STAGE/evidence/socket-boundary.json"
export PUBLIC_BOUNDARY_EVIDENCE="\$LAUNCH_STAGE/evidence/public-closed.json"
export LAUNCH_ADMISSION_OPS_DIR="\$LAUNCH_STAGE"
export MAINTENANCE_MODE_SCRIPT="\$LAUNCH_STAGE/maintenance_mode.sh"
export MAINTENANCE_SOURCE_DIR="\$LAUNCH_STAGE/maintenance"
export LAUNCH_BOUNDARY_PROBE="\$LAUNCH_STAGE/probe_launch_boundary.py"
export SOCKET_BOUNDARY_PROBE="\$LAUNCH_STAGE/socket_boundary_probe.py"
export LAUNCH_READINESS_URL="http://127.0.0.1:3000/_internal/launch-readiness"
source "\$LAUNCH_STAGE/deploy_launch_admission.sh"

close_launch_admission
EOF

echo "==> probing maintenance from operator source"
OPERATOR_EVIDENCE="$TMP/operator-maintenance.json"
operator_probe_status=0
if python scripts/ops/probe_launch_boundary.py \
  --expect maintenance \
  --operator-source \
  --base-url https://vinhlong360.vn \
  --evidence "$OPERATOR_EVIDENCE"; then
  :
else
  operator_probe_status=$?
fi
if [ -f "$OPERATOR_EVIDENCE" ]; then
  "${SCP[@]}" "$OPERATOR_EVIDENCE" "$VPS:$LAUNCH_STAGE/evidence/operator-maintenance.json"
fi
[ "$operator_probe_status" -eq 0 ] || exit "$operator_probe_status"

# 6b. Only an operator-source pass admits archive verification, installation,
# restart, and eventual reopen. Any failure leaves remote maintenance active.
"${SSH[@]}" "DO_FRONTEND=$DO_FRONTEND DO_BACKEND=$DO_BACKEND DO_REPLACE=$DO_REPLACE DO_MIGRATE=$DO_MIGRATE OPERATOR_CIDR=$OPERATOR_CIDR LAUNCH_STAGE=$LAUNCH_STAGE LAUNCH_ID=$LAUNCH_ID bash -s" <<EOF
set -euo pipefail
cd $REMOTE
export READINESS_EVIDENCE="\$LAUNCH_STAGE/evidence/readiness.json"
export SOCKET_BOUNDARY_EVIDENCE="\$LAUNCH_STAGE/evidence/socket-boundary.json"
export PUBLIC_BOUNDARY_EVIDENCE="\$LAUNCH_STAGE/evidence/public-closed.json"
export LAUNCH_ADMISSION_OPS_DIR="\$LAUNCH_STAGE"
export MAINTENANCE_MODE_SCRIPT="\$LAUNCH_STAGE/maintenance_mode.sh"
export MAINTENANCE_SOURCE_DIR="\$LAUNCH_STAGE/maintenance"
export LAUNCH_BOUNDARY_PROBE="\$LAUNCH_STAGE/probe_launch_boundary.py"
export SOCKET_BOUNDARY_PROBE="\$LAUNCH_STAGE/socket_boundary_probe.py"
export LAUNCH_READINESS_URL="http://127.0.0.1:3000/_internal/launch-readiness"
source "\$LAUNCH_STAGE/deploy_launch_admission.sh"

if [ "\$DO_BACKEND" = 1 ]; then
  echo "  extract agent + data"
  tar -xzf "\$LAUNCH_STAGE/archives/vl-deploy.tar.gz" -C $REMOTE/
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
  tar -xzf "\$LAUNCH_STAGE/archives/vl-nuxt-output.tar.gz" -C $REMOTE/web-nuxt/
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

# Only Nuxt process-local readiness and listener isolation can admit traffic.
# Backend health remains an independent post-admission operational check.
reopen_launch_admission

echo "  persist launch evidence atomically"
evidence_root="$REMOTE/backups/launch-admission"
evidence_final="\$evidence_root/\$LAUNCH_ID"
install -d -m 700 "\$evidence_root"
evidence_tmp="\$(mktemp -d "\$evidence_root/.\$LAUNCH_ID.XXXXXXXXXX")"
cleanup_evidence() {
  if [ -n "\${evidence_tmp:-}" ]; then
    rm -rf -- "\$evidence_tmp"
  fi
}
trap cleanup_evidence EXIT
for evidence_file in \
  operator-maintenance.json readiness.json socket-boundary.json public-closed.json; do
  [ -f "\$LAUNCH_STAGE/evidence/\$evidence_file" ] || {
    echo "missing launch evidence: \$evidence_file" >&2
    exit 1
  }
  install -m 600 "\$LAUNCH_STAGE/evidence/\$evidence_file" "\$evidence_tmp/\$evidence_file"
done
mv -T -- "\$evidence_tmp" "\$evidence_final"
evidence_tmp=""
rm -rf -- "\$LAUNCH_STAGE"
EOF

# 7. Post-admission diagnostics. Launch admission already made the fail-closed
# decision; backend availability is reported here without turning it into a
# second gate after traffic has reopened.
echo "==> diagnostics"
"${SSH[@]}" 'set +e
home=$(curl -s -o /dev/null -w "%{http_code}" --max-time 12 https://vinhlong360.vn/ || echo 000)
agent=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:8360/health || echo 000)
ready=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:8360/health/ready || echo 000)
# Bài học incident 2026-07-02: search 500 nhiều ngày mà /health vẫn 200 —
# endpoint lõi PHẢI nằm trong cổng verify, deploy hỏng search không được pass.
search=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://127.0.0.1:8360/api/search?q=deploy-check" || echo 000)
# Bài học outage 2026-07-05: build với API_BASE=public làm nitro proxy /api/** loop → 500
# CHỈ trên endpoint đi qua public proxy (nginx→nitro); home/ vẫn 200 vì nitro serve trực tiếp.
# PHẢI check PUBLIC /api/homepage (qua proxy) để bắt vòng lặp proxy này, không chỉ localhost.
pub_api=$(curl -s -o /dev/null -w "%{http_code}" --max-time 12 https://vinhlong360.vn/api/homepage || echo 000)
printf "  home=%s\n  agent_health=%s\n  agent_ready=%s\n  search=%s\n  public_api_homepage=%s\n" "$home" "$agent" "$ready" "$search" "$pub_api"
journalctl -u vl-agent --since "2 min ago" -p err --no-pager | tail -5 || true
exit 0'
echo "==> deploy $TS DONE. Rollback: backups/pre-deploy-$TS.tar.gz + backups/db-pre-deploy-$TS.dump"
