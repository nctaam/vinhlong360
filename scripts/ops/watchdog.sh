#!/usr/bin/env bash
# Watch core endpoints, but never probe or restart through a rollback drain.
set -u

LOG="${VL360_WATCHDOG_LOG:-/var/log/vl-watchdog.log}"
STAMP="${VL360_WATCHDOG_STAMP:-/run/vl-watchdog-last-restart}"
MAINTENANCE_SELECTOR="${VL360_MAINTENANCE_SELECTOR:-/etc/nginx/vl360-maintenance/active-server.conf}"

log_line() {
  printf '%s %s\n' "$(date -Is)" "$1" >> "$LOG"
}

guard_against_maintenance() {
  local target
  if [ ! -L "$MAINTENANCE_SELECTOR" ]; then
    log_line "maintenance guard is unknown; probes and restarts are suppressed"
    exit 1
  fi
  target="$(readlink -- "$MAINTENANCE_SELECTOR" 2>/dev/null || true)"
  case "$target" in
    server-disabled.conf)
      return 0
      ;;
    server-enabled.conf)
      log_line "maintenance is active; probes and restarts are suppressed"
      exit 0
      ;;
    *)
      log_line "maintenance guard is unknown; probes and restarts are suppressed"
      exit 1
      ;;
  esac
}

guard_against_maintenance

h=$(curl -sm 10 -o /dev/null -w "%{http_code}" http://localhost:8360/health || echo 000)
s=$(curl -sm 10 -o /dev/null -w "%{http_code}" "http://localhost:8360/api/search?q=watchdog" || echo 000)
n=$(curl -sm 10 -o /dev/null -w "%{http_code}" http://localhost:3000/ || echo 000)

if [ "$h" = "200" ] && [ "$s" = "200" ] && [ "$n" = "200" ]; then
  exit 0
fi

log_line "FAIL health=$h search=$s nuxt=$n"

# Close the race where rollback starts after the probes but before a restart.
guard_against_maintenance

now=$(date +%s)
last=$(cat "$STAMP" 2>/dev/null || echo 0)
if [ "$((now - last))" -lt 1800 ]; then
  log_line "restart suppressed because a restart ran less than 30 minutes ago"
  exit 1
fi
echo "$now" > "$STAMP"

if [ "$h" != "200" ] || [ "$s" != "200" ]; then
  systemctl restart vl-agent
  log_line "restarted vl-agent"
fi
if [ "$n" != "200" ]; then
  systemctl restart vl-nuxt
  log_line "restarted vl-nuxt"
fi
