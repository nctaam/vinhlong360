#!/usr/bin/env bash
# Deploy one canonical, verified closed release to the VPS.
#
# Partial frontend/backend flags remain accepted as compatibility aliases, but
# every invocation installs the same combined release. Data replacement and
# migrations require a separate, explicitly authorized workflow.

set -euo pipefail

source "$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/ops" && pwd -P)/deploy_launch_admission.sh"

VPS="${VL360_DEPLOY_HOST:?Set VL360_DEPLOY_HOST, for example deploy@example.com}"
KEY="${VL360_DEPLOY_KEY:-$HOME/.ssh/vinhlong_vps}"
REMOTE="${VL360_DEPLOY_RELEASE_ROOT:-/opt/vinhlong360}"
PERSISTENT_AGENT_DATA_ROOT="${VL360_DEPLOY_PERSISTENT_AGENT_DATA_ROOT:?Set the external persistent agent data root}"
ENVIRONMENT_AUTHORITY="${VL360_DEPLOY_ENVIRONMENT_AUTHORITY:?Set the external environment authority file}"
RUNTIME_AUTHORITY="${VL360_DEPLOY_RUNTIME_AUTHORITY:?Set the external runtime authority directory}"
MOUNT_AUTHORITY="${VL360_DEPLOY_MOUNT_AUTHORITY:?Set the persistent mount authority executable}"
DEPLOY_EVIDENCE_ROOT="${VL360_DEPLOY_EVIDENCE_ROOT:-/var/lib/vinhlong360/launch-evidence}"

validate_remote_value() {
  local label="$1"
  local value="$2"
  case "$value" in
    /*) ;;
    *) echo "$label must be an absolute remote path" >&2; exit 2 ;;
  esac
  case "$value" in
    *[!A-Za-z0-9_./-]*) echo "$label contains unsupported characters" >&2; exit 2 ;;
  esac
}

case "$VPS" in
  *[!A-Za-z0-9._:@-]*|"")
    echo "Set VL360_DEPLOY_HOST to a simple user@host value" >&2
    exit 2
    ;;
esac
for remote_binding in \
  "release root:$REMOTE" \
  "persistent agent data root:$PERSISTENT_AGENT_DATA_ROOT" \
  "environment authority:$ENVIRONMENT_AUTHORITY" \
  "runtime authority:$RUNTIME_AUTHORITY" \
  "mount authority:$MOUNT_AUTHORITY" \
  "deploy evidence root:$DEPLOY_EVIDENCE_ROOT"; do
  validate_remote_value "${remote_binding%%:*}" "${remote_binding#*:}"
done

OPERATOR_CIDR="${VL360_OPERATOR_CIDR:?Set VL360_OPERATOR_CIDR, for example 203.0.113.10/32}"
case "$OPERATOR_CIDR" in
  *[!0-9A-Fa-f:./]*|"")
    echo "VL360_OPERATOR_CIDR contains unsupported characters" >&2
    exit 2
    ;;
esac

SSH=(ssh -i "$KEY" -o ConnectTimeout=20 -- "$VPS")
SCP=(scp -i "$KEY" --)

DEPLOY_REQUESTED=0
DO_BUILD=1
ALLOW_DIRTY=0
for arg in "$@"; do
  case "$arg" in
    --all|--frontend|--backend) DEPLOY_REQUESTED=1 ;;
    --skip-build) DO_BUILD=0 ;;
    --allow-dirty) ALLOW_DIRTY=1 ;;
    --data|--replace|--migrate)
      echo "destructive data and migration operations are not supported by the closed-release deploy path" >&2
      exit 2
      ;;
    --no-backup)
      echo "--no-backup is obsolete for the atomic closed-release installer" >&2
      exit 2
      ;;
    *) echo "Unknown flag: $arg" >&2; exit 2 ;;
  esac
done
[ "$DEPLOY_REQUESTED" = 1 ] || {
  echo "Nothing to do. Pass --all, --frontend, or --backend." >&2
  exit 2
}

if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if [ "$ALLOW_DIRTY" = 0 ] && [ -n "$(git status --porcelain)" ]; then
    echo "Working tree is dirty. Commit/stash changes or pass --allow-dirty intentionally." >&2
    exit 2
  fi
fi

TS="$(date +%Y%m%d-%H%M%S)"
TMP="$(mktemp -d "$PWD/.vl360-deploy.XXXXXXXX")"
RELEASE_ARCHIVE="$TMP/vl360-launch-release.tar.gz"
COMPOSE_AUDIT="$TMP/compose-network-audit.json"
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
  rm -rf -- "$TMP"
  exit "$status"
}

trap cleanup_deploy EXIT
echo "==> canonical closed deploy $TS"

# 0. Verify that the remote command path is reachable before doing local work.
echo "==> pre-flight connectivity"
"${SSH[@]}" true

# 1. Build the revision-bound Nuxt output for the canonical systemd topology.
export BUILD_REVISION="$(git rev-parse --verify HEAD)"
if [ "$DO_BUILD" = 1 ]; then
  echo "==> building web-nuxt"
  ( cd web-nuxt && API_BASE=http://127.0.0.1:8360 NODE_OPTIONS="--max-old-space-size=4096" npm run build )
fi
[ -f web-nuxt/.output/server/index.mjs ] || {
  echo "Nuxt output is missing server/index.mjs" >&2
  exit 1
}
[ -f web-nuxt/.output/server/launch-readiness-manifest.json ] || {
  echo "Nuxt output is missing launch-readiness-manifest.json" >&2
  exit 1
}

# 2. Produce the source-bound Compose audit and the one combined release.
echo "==> auditing Compose and packaging the combined launch release"
python scripts/ops/compose_network_audit.py \
  --root . \
  --compose docker-compose.yml \
  --production docker-compose.prod.yml \
  --developer docker-compose.dev.yml \
  --systemd-deps docker-compose.systemd-deps.yml \
  --output "$COMPOSE_AUDIT"
python scripts/package_launch_release.py launch-release \
  --root . \
  --destination "$RELEASE_ARCHIVE" \
  --compose-network-audit "$COMPOSE_AUDIT" \
  --source-revision "$BUILD_REVISION"
[ -f "$RELEASE_ARCHIVE" ] && [ -f "$RELEASE_ARCHIVE.sha256" ] || {
  echo "combined release package or sidecar is missing" >&2
  exit 1
}

# 3. Create a unique remote staging authority.
LAUNCH_STAGE="$("${SSH[@]}" 'umask 077; mktemp -d /tmp/vl360-launch-admission.XXXXXXXXXX')"
case "$LAUNCH_STAGE" in
  /tmp/vl360-launch-admission.*) ;;
  *) echo "remote mktemp returned an unexpected launch stage" >&2; exit 1 ;;
esac
LAUNCH_ID="${LAUNCH_STAGE##*/}"
"${SSH[@]}" "install -d -m 700 -- '$LAUNCH_STAGE/archives' '$LAUNCH_STAGE/evidence' '$LAUNCH_STAGE/maintenance'"

# 4. Stage only operational helpers and reviewed maintenance sources.
LAUNCH_FILES=(
  scripts/ops/deploy_launch_admission.sh
  scripts/ops/probe_launch_boundary.py
  scripts/ops/socket_boundary_probe.py
  scripts/ops/maintenance_mode.sh
  scripts/ops/verify_closed_release.py
  scripts/ops/install_closed_release.sh
)
MAINTENANCE_FILES=(
  ops/nginx/maintenance/http-context.conf.template
  ops/nginx/maintenance/server-enabled.conf
  ops/nginx/maintenance/server-disabled.conf
)
for launch_file in "${LAUNCH_FILES[@]}"; do
  [ -f "$launch_file" ] || { echo "Missing launch helper: $launch_file" >&2; exit 1; }
done
for maintenance_file in "${MAINTENANCE_FILES[@]}"; do
  [ -f "$maintenance_file" ] || { echo "Missing maintenance source: $maintenance_file" >&2; exit 1; }
done
"${SCP[@]}" "${LAUNCH_FILES[@]}" "$VPS:$LAUNCH_STAGE/"
"${SCP[@]}" "${MAINTENANCE_FILES[@]}" "$VPS:$LAUNCH_STAGE/maintenance/"

# 5. Ship tarballs: the canonical archive and its adjacent integrity sidecar.
echo "==> uploading combined release"
"${SCP[@]}" "$RELEASE_ARCHIVE" "$VPS:$LAUNCH_STAGE/archives/vl360-launch-release.tar.gz"
"${SCP[@]}" "$RELEASE_ARCHIVE.sha256" "$VPS:$LAUNCH_STAGE/archives/vl360-launch-release.tar.gz.sha256"

# 5a. Remote verification must pass before maintenance or service mutation.
"${SSH[@]}" "LAUNCH_STAGE=$LAUNCH_STAGE bash -s" <<EOF
set -euo pipefail
python3 "\$LAUNCH_STAGE/verify_closed_release.py" \
  --archive "\$LAUNCH_STAGE/archives/vl360-launch-release.tar.gz" \
  --archive-digest-file "\$LAUNCH_STAGE/archives/vl360-launch-release.tar.gz.sha256" \
  --require-closed \
  --evidence-dir "\$LAUNCH_STAGE/evidence/package-preflight"
EOF

# 6a. Close traffic, then prove maintenance from the operator source.
REMOTE_STAGE_PRESERVE=1
"${SSH[@]}" "OPERATOR_CIDR=$OPERATOR_CIDR LAUNCH_STAGE=$LAUNCH_STAGE bash -s" <<EOF
set -euo pipefail
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

# 6b. The verified closed installer is the only release mutation authority.
"${SSH[@]}" "OPERATOR_CIDR=$OPERATOR_CIDR LAUNCH_STAGE=$LAUNCH_STAGE LAUNCH_ID=$LAUNCH_ID bash -s" <<EOF
set -euo pipefail
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

"\$LAUNCH_STAGE/install_closed_release.sh" \
  --archive "\$LAUNCH_STAGE/archives/vl360-launch-release.tar.gz" \
  --archive-digest-file "\$LAUNCH_STAGE/archives/vl360-launch-release.tar.gz.sha256" \
  --release-root "$REMOTE" \
  --persistent-agent-data-root "$PERSISTENT_AGENT_DATA_ROOT" \
  --environment-authority "$ENVIRONMENT_AUTHORITY" \
  --runtime-authority "$RUNTIME_AUTHORITY" \
  --mount-authority "$MOUNT_AUTHORITY" \
  --evidence-dir "\$LAUNCH_STAGE/evidence/install" \
  --require-closed

systemctl daemon-reload
systemctl restart vl-agent
systemctl restart vl-bot
systemctl restart vl-nuxt
curl --fail --silent --show-error \
  --connect-timeout 5 \
  --max-time 45 \
  --retry 5 --retry-delay 1 --retry-connrefused \
  --output "\$LAUNCH_STAGE/evidence/nuxt-api-proxy.json" \
  http://127.0.0.1:3000/api/homepage
reopen_launch_admission

echo "  persist launch evidence atomically"
evidence_root="$DEPLOY_EVIDENCE_ROOT"
evidence_final="\$evidence_root/\$LAUNCH_ID"
install -d -m 700 "\$evidence_root"
evidence_tmp="\$(mktemp -d "\$evidence_root/.\$LAUNCH_ID.XXXXXXXXXX")"
cleanup_evidence() {
  if [ -n "\${evidence_tmp:-}" ]; then
    rm -rf -- "\$evidence_tmp"
  fi
}
trap cleanup_evidence EXIT
cp -a -- "\$LAUNCH_STAGE/evidence/." "\$evidence_tmp/"
mv -T -- "\$evidence_tmp" "\$evidence_final"
evidence_tmp=""
rm -rf -- "\$LAUNCH_STAGE"
EOF

# 7. Post-admission diagnostics report backend state without reopening authority.
echo "==> diagnostics"
"${SSH[@]}" 'set +e
home=$(curl -s -o /dev/null -w "%{http_code}" --max-time 12 https://vinhlong360.vn/ || echo 000)
agent=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:8360/health || echo 000)
ready=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:8360/health/ready || echo 000)
search=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://127.0.0.1:8360/api/search?q=deploy-check" || echo 000)
pub_api=$(curl -s -o /dev/null -w "%{http_code}" --max-time 12 https://vinhlong360.vn/api/homepage || echo 000)
printf "  home=%s\n  agent_health=%s\n  agent_ready=%s\n  search=%s\n  public_api_homepage=%s\n" "$home" "$agent" "$ready" "$search" "$pub_api"
exit 0'
echo "==> canonical closed deploy $TS DONE"
