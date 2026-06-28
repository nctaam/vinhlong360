#!/usr/bin/env bash
# scripts/deploy.sh — deploy vinhlong360 to the VPS via the proven tarball flow.
#
# Usage (run from repo root, in Git Bash):
#   scripts/deploy.sh --all                 # frontend + backend + data (data needs --replace to take effect)
#   scripts/deploy.sh --frontend            # only Nuxt .output
#   scripts/deploy.sh --backend             # only agent/*.py + requirements.txt (+ pip install)
#   scripts/deploy.sh --backend --data --replace   # backend + re-import data.json into prod Postgres
#   scripts/deploy.sh --frontend --no-backup       # skip prod backup (NOT recommended)
#   scripts/deploy.sh --dry-run --all              # show what would be done without doing it
#
# Flags:
#   --frontend   build + ship web-nuxt/.output, npm install --omit=dev, restart vl-nuxt
#   --backend    ship agent/*.py + requirements.txt + web/data.json(+.js), pip install, restart vl-agent
#   --data       ship web/data.json (alias kept for clarity; backend already ships it)
#   --replace    DESTRUCTIVE: re-import data.json into prod Postgres (entities/rels/itineraries).
#                Requires a fresh prod DB dump first (done automatically unless --no-backup).
#   --no-backup  skip the prod DB + code rollback snapshot (dangerous)
#   --skip-build assume web-nuxt/.output is already built (don't run npm run build)
#   --dry-run    show what would be done without executing remote commands
#
# Hard-won gotchas encoded here (see memory ref-vps-deploy):
#   * LIVE Nuxt output = $REMOTE/web-nuxt/.output (the top-level $REMOTE/.output is STALE/unused).
#   * MUST `rm -rf .output` before extracting (tar over existing symlinks => "File exists").
#   * .output/server needs `npm install --omit=dev` (Linux-native deps).
#   * data sync into Postgres needs ALLOW_DESTRUCTIVE_DB_REPLACE=1 (B7 lock) + restart to reload RAM cache.
#   * pg_dump to /tmp then move (peer-auth postgres user can't write root-owned backups/).
#   * NEVER touch prod .env (a parse error there crash-loops vl-agent: server.py hard-reads os.environ["LLM_API_KEY"]).
#
# ROLLBACK:
#   Every deploy creates two rollback artifacts in /opt/vinhlong360/backups/:
#     1. pre-deploy-<TS>.tar.gz  — code snapshot (agent/, web/data.json, web-nuxt/.output)
#     2. db-pre-deploy-<TS>.sql  — full Postgres dump
#
#   Automated rollback triggers if post-deploy health polling fails (5 checks over 60s).
#   Manual rollback: scripts/deploy.sh does NOT provide a --rollback flag — use the
#   rollback() function on the VPS directly (see below).
#
#   To rollback on VPS:
#     cd /opt/vinhlong360
#     tar -xzf backups/pre-deploy-<TS>.tar.gz        # restore code
#     psql "$DATABASE_URL" < backups/db-pre-deploy-<TS>.sql  # restore DB
#     systemctl restart vl-agent vl-nuxt              # restart services
#     curl -s http://127.0.0.1:8360/health            # verify
#
#   If only the frontend broke:
#     tar -xzf backups/pre-deploy-<TS>.tar.gz web-nuxt/.output
#     cd web-nuxt/.output/server && npm install --omit=dev
#     systemctl restart vl-nuxt

set -euo pipefail

# ── Color output helpers ──────────────────────────────────────────────────────
# Detect whether the terminal supports color.
if [ -t 1 ] && command -v tput >/dev/null 2>&1 && [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
  _RED="\033[0;31m"
  _GREEN="\033[0;32m"
  _YELLOW="\033[0;33m"
  _CYAN="\033[0;36m"
  _BOLD="\033[1m"
  _RESET="\033[0m"
else
  _RED="" _GREEN="" _YELLOW="" _CYAN="" _BOLD="" _RESET=""
fi

info()  { echo -e "${_CYAN}==> $*${_RESET}"; }
ok()    { echo -e "${_GREEN}  [OK] $*${_RESET}"; }
warn()  { echo -e "${_YELLOW}  [WARN] $*${_RESET}"; }
fail()  { echo -e "${_RED}  [FAIL] $*${_RESET}" >&2; }
step()  { echo -e "${_BOLD}  $*${_RESET}"; }
dry()   { echo -e "${_YELLOW}  [DRY-RUN] $*${_RESET}"; }

# ── Configuration ─────────────────────────────────────────────────────────────
VPS="root@66.42.57.202"
KEY="$HOME/.ssh/vinhlong_vps"
REMOTE="/opt/vinhlong360"
SSH="ssh -i $KEY -o ConnectTimeout=20"
SCP="scp -i $KEY"

# Post-deploy health polling settings
HEALTH_CHECKS=5
HEALTH_INTERVAL=12          # seconds between checks (5 * 12 = 60s total)
HEALTH_URL="http://127.0.0.1:8360/health"

# ── Parse flags ───────────────────────────────────────────────────────────────
DO_FRONTEND=0; DO_BACKEND=0; DO_DATA=0; DO_REPLACE=0; DO_BACKUP=1; DO_BUILD=1; DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --frontend) DO_FRONTEND=1 ;;
    --backend)  DO_BACKEND=1 ;;
    --data)     DO_DATA=1; DO_BACKEND=1 ;;   # data ships with the backend tarball
    --all)      DO_FRONTEND=1; DO_BACKEND=1; DO_DATA=1 ;;
    --replace)  DO_REPLACE=1; DO_BACKEND=1; DO_DATA=1 ;;
    --no-backup) DO_BACKUP=0 ;;
    --skip-build) DO_BUILD=0 ;;
    --dry-run)  DRY_RUN=1 ;;
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

if [ "$DRY_RUN" = 1 ]; then
  info "DRY-RUN deploy $TS  (frontend=$DO_FRONTEND backend=$DO_BACKEND data=$DO_DATA replace=$DO_REPLACE backup=$DO_BACKUP)"
else
  info "deploy $TS  (frontend=$DO_FRONTEND backend=$DO_BACKEND data=$DO_DATA replace=$DO_REPLACE backup=$DO_BACKUP)"
fi

# ── 0a. Pre-deploy local checks ──────────────────────────────────────────────
info "pre-deploy checks (local)"
if ! python -m pytest -q 2>&1 | tail -3; then
  fail "Tests failed — aborting deploy. Fix tests first."
  exit 1
fi
ok "tests passed"

if [ "$DO_BACKEND" = 1 ]; then
  if python scripts/validate_data.py --json > /dev/null 2>&1; then
    ok "validate_data.py passed"
  else
    warn "validate_data.py exited non-zero (warnings only, continuing)"
  fi
fi

if [ "$DO_FRONTEND" = 1 ] && [ "$DO_BUILD" = 0 ]; then
  if [ ! -f web-nuxt/.output/server/index.mjs ]; then
    fail "--skip-build but web-nuxt/.output/server/index.mjs missing — build first or drop --skip-build."
    exit 1
  fi
  ok "pre-built .output found"
fi

# ── Dry-run: show plan and exit ──────────────────────────────────────────────
if [ "$DRY_RUN" = 1 ]; then
  echo ""
  info "DRY-RUN plan — the following steps would execute:"
  echo ""

  if [ "$DO_FRONTEND" = 1 ] && [ "$DO_BUILD" = 1 ]; then
    dry "build web-nuxt (npm run build with NODE_OPTIONS=--max-old-space-size=4096)"
  fi

  if [ "$DO_BACKEND" = 1 ]; then
    dry "pack agent/*.py + requirements.txt + web/data.json into tarball"
  fi

  if [ "$DO_FRONTEND" = 1 ]; then
    dry "pack web-nuxt/.output into tarball"
  fi

  if [ "$DO_BACKUP" = 1 ]; then
    dry "SSH to VPS: pg_dump + code snapshot -> backups/"
  fi

  if [ "$DO_BACKEND" = 1 ]; then
    dry "SCP vl-deploy.tar.gz to VPS:/tmp/"
  fi
  if [ "$DO_FRONTEND" = 1 ]; then
    dry "SCP vl-nuxt-output.tar.gz to VPS:/tmp/"
  fi

  if [ "$DO_BACKEND" = 1 ]; then
    dry "SSH to VPS: extract agent + data, pip install"
  fi
  if [ "$DO_FRONTEND" = 1 ]; then
    dry "SSH to VPS: rm -rf .output, extract, npm install --omit=dev"
  fi
  if [ "$DO_REPLACE" = 1 ]; then
    dry "SSH to VPS: ALLOW_DESTRUCTIVE_DB_REPLACE=1 python agent/database.py --replace"
  fi

  echo ""
  dry "rolling restart: postgres -> vl-agent -> vl-nuxt -> nginx (wait for health between each)"
  dry "post-deploy health polling: $HEALTH_CHECKS checks over $((HEALTH_CHECKS * HEALTH_INTERVAL))s"
  dry "if health fails: automated rollback from backups/pre-deploy-$TS.tar.gz"

  echo ""
  info "DRY-RUN complete — no remote changes were made."
  exit 0
fi

# ── 0b. Pre-flight: connectivity + current health ────────────────────────────
info "pre-flight health"
$SSH "$VPS" 'systemctl is-active vl-agent vl-nuxt >/dev/null && echo "  services up" || echo "  WARN: a service is down"'

# ── 1. Build frontend (local) ────────────────────────────────────────────────
if [ "$DO_FRONTEND" = 1 ] && [ "$DO_BUILD" = 1 ]; then
  info "building web-nuxt (npm run build)"
  # ARCH-006: cấp thêm heap V8 cho build (maplibre + tooling nặng) tránh OOM.
  # KHÔNG đặt quá cao (8192) — sẽ bỏ đói esbuild/WASM native; 4096 cân bằng.
  ( cd web-nuxt && NODE_OPTIONS="--max-old-space-size=4096" npm run build )
  ok "frontend build complete"
fi

# ── 2. Pack tarballs (local) ─────────────────────────────────────────────────
if [ "$DO_BACKEND" = 1 ]; then
  info "packing agent + data"
  DATAJS=""; [ -f web/data.js ] && DATAJS="web/data.js"
  tar -czf "$TMP/vl-deploy.tar.gz" agent/*.py requirements.txt web/data.json $DATAJS
  ok "backend tarball ready"
fi
if [ "$DO_FRONTEND" = 1 ]; then
  # Fail-fast: build dở/ngắt (vd Bash timeout 120s) để .output/server RỖNG → ship sẽ làm
  # vl-nuxt 502 (npm install walk-up chạy `nuxt prepare`). Chặn ship .output hỏng.
  if [ ! -f web-nuxt/.output/server/index.mjs ] || [ ! -f web-nuxt/.output/server/package.json ]; then
    fail ".output/server missing index.mjs/package.json (build incomplete?) — abort, NOT shipping broken .output"
    exit 1
  fi
  info "packing nuxt .output"
  tar -czf "$TMP/vl-nuxt-output.tar.gz" -C web-nuxt .output
  ok "frontend tarball ready"
fi

# ── 3. Backup prod (DB + rollback tarball) ───────────────────────────────────
if [ "$DO_BACKUP" = 1 ]; then
  info "backing up prod (db + code)"
  $SSH "$VPS" "bash -s" <<EOF
set -e
cd $REMOTE
set -a; . ./.env; set +a
pg_dump "\$DATABASE_URL" -f /tmp/db-pre-deploy-$TS.sql && mv /tmp/db-pre-deploy-$TS.sql backups/ && echo "  db dump -> backups/db-pre-deploy-$TS.sql"
tar -czf backups/pre-deploy-$TS.tar.gz agent web/data.json web-nuxt/.output 2>/dev/null && echo "  code snapshot -> backups/pre-deploy-$TS.tar.gz"
# Xoay-vòng: giữ 6 bản auto-backup mới nhất mỗi loại (chặn đầy đĩa — sự-cố 2026-06-24).
# Chỉ đụng pre-deploy-*/db-pre-deploy-* tự-sinh; KHÔNG đụng milestone-backup có-tên.
ls -t backups/pre-deploy-*.tar.gz 2>/dev/null | tail -n +7 | xargs -r rm -f
ls -t backups/db-pre-deploy-*.sql 2>/dev/null | tail -n +7 | xargs -r rm -f
echo "  rotated auto-backups (kept newest 6)"
EOF
  ok "prod backup complete"
fi

# ── 4. Ship tarballs ─────────────────────────────────────────────────────────
info "uploading"
[ "$DO_BACKEND" = 1 ]  && $SCP "$TMP/vl-deploy.tar.gz" "$VPS:/tmp/"
[ "$DO_FRONTEND" = 1 ] && $SCP "$TMP/vl-nuxt-output.tar.gz" "$VPS:/tmp/"
ok "tarballs uploaded"

# ── 5. Extract + install + (optional) data replace ───────────────────────────
info "extract + install on VPS"
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
  # PG_USE_POOL=false: pool treo replace lúc startup (incident 2026-06-22); timeout: fail-fast
  ALLOW_DESTRUCTIVE_DB_REPLACE=1 PG_USE_POOL=false timeout 240 ./venv/bin/python agent/database.py --replace 2>&1 | tail -8
  [ \${PIPESTATUS[0]:-0} -eq 124 ] && { echo "  FAIL: replace TIMEOUT 240s — abort (data cu giu nguyen, transaction rollback)"; exit 1; }
fi
echo "  extract + install done"
EOF
ok "extract + install complete"

# ── 6. Rolling restart ───────────────────────────────────────────────────────
#
# Restart services one by one in dependency order:
#   postgres (if needed) -> vl-agent -> vl-nuxt -> nginx (reload)
# Wait for each service to be healthy before proceeding to the next.
# This minimizes downtime compared to restarting everything at once.
#
info "rolling restart"
$SSH "$VPS" "DO_FRONTEND=$DO_FRONTEND DO_BACKEND=$DO_BACKEND DO_REPLACE=$DO_REPLACE bash -s" <<'ROLLING_EOF'
set -e
cd /opt/vinhlong360

wait_for_service() {
  local svc="$1"
  local max_wait="${2:-30}"
  local elapsed=0
  while [ "$elapsed" -lt "$max_wait" ]; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
      echo "    $svc is active (${elapsed}s)"
      return 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
  done
  echo "    WARN: $svc not active after ${max_wait}s"
  return 1
}

wait_for_health() {
  local url="$1"
  local max_wait="${2:-30}"
  local elapsed=0
  while [ "$elapsed" -lt "$max_wait" ]; do
    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "$url" 2>/dev/null || echo 000)
    if [ "$code" = "200" ]; then
      echo "    health OK (${elapsed}s)"
      return 0
    fi
    sleep 3
    elapsed=$((elapsed + 3))
  done
  echo "    WARN: health not 200 after ${max_wait}s"
  return 1
}

# Step 1: Ensure postgres is healthy (dependency for everything)
echo "  [1/4] checking postgres"
if systemctl is-active --quiet postgresql 2>/dev/null; then
  echo "    postgresql already active"
else
  echo "    restarting postgresql"
  systemctl restart postgresql
  wait_for_service postgresql 30
fi

# Step 2: Restart vl-agent (backend)
if [ "$DO_BACKEND" = 1 ] || [ "$DO_REPLACE" = 1 ]; then
  echo "  [2/4] restarting vl-agent"
  systemctl restart vl-agent
  sleep 4
  wait_for_service vl-agent 30
  wait_for_health "http://127.0.0.1:8360/health" 30 || echo "    (continuing despite health warning)"
else
  echo "  [2/4] vl-agent: no changes, skipping restart"
fi

# Step 3: Restart vl-nuxt (frontend)
if [ "$DO_FRONTEND" = 1 ]; then
  echo "  [3/4] restarting vl-nuxt"
  systemctl restart vl-nuxt
  sleep 3
  wait_for_service vl-nuxt 30
else
  echo "  [3/4] vl-nuxt: no changes, skipping restart"
fi

# Step 4: Reload nginx (picks up any config changes, near-zero downtime)
echo "  [4/4] reloading nginx"
if systemctl is-active --quiet nginx 2>/dev/null; then
  nginx -t 2>/dev/null && systemctl reload nginx && echo "    nginx reloaded" || echo "    WARN: nginx config test failed, skipping reload"
else
  echo "    nginx not running, skipping"
fi

echo "  rolling restart complete"
ROLLING_EOF
ok "rolling restart complete"

# ── 7. Post-deploy health polling ────────────────────────────────────────────
#
# Poll /health N times over ~60 seconds. If any check fails, trigger
# automated rollback from the pre-deploy backup.
#
info "post-deploy health polling ($HEALTH_CHECKS checks over $((HEALTH_CHECKS * HEALTH_INTERVAL))s)"
HEALTH_PASS=0
HEALTH_FAIL=0

for i in $(seq 1 $HEALTH_CHECKS); do
  HCODE=$($SSH "$VPS" "curl -s -o /dev/null -w '%{http_code}' --max-time 8 $HEALTH_URL 2>/dev/null || echo 000")
  if [ "$HCODE" = "200" ]; then
    ok "health check $i/$HEALTH_CHECKS: HTTP $HCODE"
    HEALTH_PASS=$((HEALTH_PASS + 1))
  else
    fail "health check $i/$HEALTH_CHECKS: HTTP $HCODE"
    HEALTH_FAIL=$((HEALTH_FAIL + 1))
  fi
  if [ "$i" -lt "$HEALTH_CHECKS" ]; then
    sleep "$HEALTH_INTERVAL"
  fi
done

step "health results: $HEALTH_PASS passed, $HEALTH_FAIL failed"

# ── 8. Automated rollback (if health polling failed) ─────────────────────────
#
# rollback() restores from the pre-deploy backup created in step 3.
# It restores code (tarball) and DB (pg_dump), then restarts services.
#
rollback() {
  fail "HEALTH CHECK FAILED — initiating automated rollback"
  echo ""
  warn "Rolling back to pre-deploy-$TS snapshot..."

  $SSH "$VPS" "bash -s" <<ROLLBACK_EOF
set -e
cd $REMOTE
echo "  rollback: restoring code from backups/pre-deploy-$TS.tar.gz"
if [ -f backups/pre-deploy-$TS.tar.gz ]; then
  tar -xzf backups/pre-deploy-$TS.tar.gz
  echo "  rollback: code restored"
else
  echo "  rollback: ERROR — backup tarball not found!"
  exit 1
fi

echo "  rollback: restoring DB from backups/db-pre-deploy-$TS.sql"
if [ -f backups/db-pre-deploy-$TS.sql ]; then
  set -a; . ./.env; set +a
  psql "\$DATABASE_URL" < backups/db-pre-deploy-$TS.sql 2>&1 | tail -3
  echo "  rollback: DB restored"
else
  echo "  rollback: WARNING — DB backup not found, skipping DB restore"
fi

echo "  rollback: restarting services"
systemctl restart vl-agent
sleep 4
systemctl restart vl-nuxt
sleep 3

echo "  rollback: verifying health"
rcode=\$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1:8360/health 2>/dev/null || echo 000)
echo "  rollback: agent_health=\$rcode"
if [ "\$rcode" = "200" ]; then
  echo "  rollback: SUCCESS — services restored to pre-deploy state"
else
  echo "  rollback: WARNING — health still not 200 after rollback. Manual intervention needed."
  echo "  rollback: check: journalctl -u vl-agent --since '5 min ago' -p err"
fi
ROLLBACK_EOF
}

if [ "$HEALTH_FAIL" -gt 0 ]; then
  if [ "$DO_BACKUP" = 1 ]; then
    rollback
    fail "deploy $TS ROLLED BACK due to health failures."
    fail "Investigate: ssh $VPS 'journalctl -u vl-agent --since \"10 min ago\" -p err --no-pager | head -30'"
    exit 1
  else
    fail "health checks failed but --no-backup was used — cannot auto-rollback!"
    fail "Manual investigation needed on VPS."
    exit 1
  fi
fi

# ── 9. Final verification ───────────────────────────────────────────────────
info "final verify"
$SSH "$VPS" 'curl -s -o /dev/null -w "  home=%{http_code}\n" https://vinhlong360.vn/; curl -s -o /dev/null -w "  agent_health=%{http_code}\n" --max-time 10 http://127.0.0.1:8360/health; journalctl -u vl-agent --since "2 min ago" -p err --no-pager | tail -5 || true'

# ── 10. Cleanup VPS /tmp ─────────────────────────────────────────────────────
step "cleanup /tmp on VPS"
$SSH "$VPS" 'rm -f /tmp/vl-deploy.tar.gz /tmp/vl-nuxt-output.tar.gz'

echo ""
info "deploy $TS DONE"
ok "rollback artifacts: backups/pre-deploy-$TS.tar.gz + backups/db-pre-deploy-$TS.sql"
