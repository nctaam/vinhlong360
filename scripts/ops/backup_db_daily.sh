#!/bin/bash
# Backup Postgres hằng ngày (systemd timer vl-backup-db.timer) — audit 2026-07-02 risk #4.
# Dump → gzip → backups/daily/, giữ 7 bản mới nhất. Chạy as root (sudo -u postgres).
# LƯU Ý: vẫn CÙNG đĩa VPS — offsite (R2) chờ chủ quyết (bucket riêng vs mã hoá).
set -euo pipefail

DIR=/opt/vinhlong360/backups/daily
mkdir -p "$DIR"
TS=$(date +%Y%m%d-%H%M%S)
OUT="$DIR/db-daily-$TS.sql.gz"
MANIFEST="$OUT.manifest.json"

sudo -u postgres pg_dump vinhlong360 | gzip > "$OUT"
SIZE=$(du -h "$OUT" | cut -f1)

# Sanity TRƯỚC, xoay vòng SAU. Thứ tự này là load-bearing: xoay vòng trước nghĩa
# là bản mới CHƯA kiểm chiếm slot 1 và đẩy bản TỐT cũ nhất ra khỏi vòng giữ —
# mất một bản dùng được để đổi lấy một bản có thể hỏng.
# Sanity: (a) gzip nguyên vẹn; (b) dump KẾT THÚC đầy đủ ("dump complete" ở cuối
# — bắt được dump cụt). Dùng tail (đọc trọn stream) thay head: head đóng pipe
# sớm → zcat SIGPIPE → pipefail fail oan (bug bắt được khi cài 2026-07-02).
if ! gzip -t "$OUT" || ! zcat "$OUT" | tail -5 | grep -q "database dump complete"; then
  echo "$(date -Is) BACKUP BẤT THƯỜNG: $OUT hỏng hoặc thiếu footer 'dump complete' (dump cụt?) — đã xoá, KHÔNG xoay vòng" >> /var/log/vl-backup.log
  rm -f "$OUT"
  exit 1
fi

# Publish the same checksum/source envelope consumed by offsite and restore.
python3 - "$OUT" "$MANIFEST" <<'PY'
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

artifact, manifest_path = sys.argv[1:]
digest = hashlib.sha256()
with open(artifact, "rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
checksum = digest.hexdigest()
payload = {
    "schema": "vinhlong360-backup-manifest-v2",
    "artifact_id": os.path.basename(artifact),
    "format": "postgres.sql.gz",
    "source_identity": {"target": "pg", "database": "vinhlong360"},
    "row_counts": {},
    "checksum": checksum,
    "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    "artifact": {"path": os.path.basename(artifact), "sha256": checksum},
}
with open(manifest_path, "x", encoding="utf-8") as stream:
    json.dump(payload, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
PY

# Xoay vòng: giữ 7 bản daily mới nhất (KHÔNG đụng backups/ cấp trên — milestone/pre-deploy)
ls -t "$DIR"/db-daily-*.sql.gz 2>/dev/null | tail -n +8 | while read -r old; do rm -f "$old" "$old.manifest.json"; done
echo "$(date -Is) OK $OUT ($SIZE), giữ $(ls "$DIR"/db-daily-*.sql.gz | wc -l) bản" >> /var/log/vl-backup.log
