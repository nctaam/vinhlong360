# Systemd units vận hành (cài trên VPS 2026-07-02 — audit risk #4 + #9)

Bản gốc script: `scripts/ops/backup_db_daily.sh`, `scripts/ops/watchdog.sh`
→ cài tại `/opt/vinhlong360/scripts/ops/` (chmod +x).

## /etc/systemd/system/vl-backup-db.service
```ini
[Unit]
Description=vinhlong360 daily Postgres backup

[Service]
Type=oneshot
ExecStart=/opt/vinhlong360/scripts/ops/backup_db_daily.sh
```

## /etc/systemd/system/vl-backup-db.timer
```ini
[Unit]
Description=Daily DB backup 20:30 UTC (03:30 VN)

[Timer]
OnCalendar=*-*-* 20:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

## /etc/systemd/system/vl-watchdog.service
```ini
[Unit]
Description=vinhlong360 watchdog (health + search + nuxt)

[Service]
Type=oneshot
ExecStart=/opt/vinhlong360/scripts/ops/watchdog.sh
```

## /etc/systemd/system/vl-watchdog.timer
```ini
[Unit]
Description=Watchdog moi 5 phut

[Timer]
OnCalendar=*:0/5
Persistent=false

[Install]
WantedBy=timers.target
```

Kích hoạt: `systemctl daemon-reload && systemctl enable --now vl-backup-db.timer vl-watchdog.timer`
Log: `/var/log/vl-backup.log`, `/var/log/vl-watchdog.log`. Guard restart-loop: `/run/vl-watchdog-last-restart` (30 phút).

**CÒN TREO (cần chủ quyết):** đẩy backup OFFSITE lên R2 — bucket hiện tại public qua
cdn.vinhlong360.vn nên dump (chứa PII/password hash) KHÔNG được upload thô; cần
(a) bucket R2 riêng private, hoặc (b) passphrase mã hoá (secret mới — §4 chủ đặt).
