# Ops — Tiêu chuẩn vinhlong360
> **STATUS (2026-07-07): active — bản 1.0 (SP0).**

## Mốc tham chiếu
CLAUDE.md §2 (B1/B7/B8) · HANDOFF.md runbook · hạ tầng thật: VPS 1GB, systemd vl-agent/vl-nuxt/vl-bot, SSH root@ (key vinhlong_vps), PG prod + SQLite dev.

## Quy tắc
| Rule | Phát biểu | Tầng | Cách đo |
|---|---|---|---|
| R70.1 | CẤM secrets hardcode; CẤM stage .env | hard | check_secrets |
| R70.2 | B1: backup TRƯỚC mọi thao tác dữ liệu (backup_data.py + pg_dump prod) | quy-trình-ký* | checklist trong plan data-ops |
| R70.3 | Tên service chuẩn: vl-agent / vl-nuxt / vl-bot; SSH hiện hành root@ | ghi nhận | doc_status (từ-khoá sai) |
| R70.4 | Rotate ADMIN_API_KEY khi 2FA bật: đặt TOTP_ENC_KEY trước (bẫy khoá vĩnh viễn) | ghi nhận | incident-runbook |
| R70.5 | Script apply/sửa-hàng-loạt BẮT BUỘC có --dry-run và chạy dry-run trước | quy-trình-ký* | review khi thêm script |

## Ngoại lệ đã duyệt
- **R70.2/R70.5** quy trình — *chủ dự án duyệt (2026-07-07); vi phạm = dừng theo §4 CLAUDE.md.*
