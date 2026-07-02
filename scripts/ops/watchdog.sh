#!/bin/bash
# Watchdog 5 phút (systemd timer vl-watchdog.timer) — audit 2026-07-02 risk #9.
# Bài học incident: /api/search 500 nhiều ngày mà /health vẫn 200 → watchdog phải
# kiểm endpoint LÕI, không chỉ health. Fail → log + restart (guard 30' chống loop).
set -u

LOG=/var/log/vl-watchdog.log
STAMP=/run/vl-watchdog-last-restart

h=$(curl -sm 10 -o /dev/null -w "%{http_code}" http://localhost:8360/health || echo 000)
s=$(curl -sm 10 -o /dev/null -w "%{http_code}" "http://localhost:8360/api/search?q=watchdog" || echo 000)
n=$(curl -sm 10 -o /dev/null -w "%{http_code}" http://localhost:3000/ || echo 000)

if [ "$h" = "200" ] && [ "$s" = "200" ] && [ "$n" = "200" ]; then
  exit 0
fi

echo "$(date -Is) FAIL health=$h search=$s nuxt=$n" >> "$LOG"

now=$(date +%s)
last=$(cat "$STAMP" 2>/dev/null || echo 0)
if [ $((now - last)) -lt 1800 ]; then
  echo "$(date -Is) bỏ qua restart (đã restart <30 phút trước — tránh loop; cần người xem log)" >> "$LOG"
  exit 1
fi
echo "$now" > "$STAMP"

if [ "$h" != "200" ] || [ "$s" != "200" ]; then
  systemctl restart vl-agent
  echo "$(date -Is) đã restart vl-agent" >> "$LOG"
fi
if [ "$n" != "200" ]; then
  systemctl restart vl-nuxt
  echo "$(date -Is) đã restart vl-nuxt" >> "$LOG"
fi
