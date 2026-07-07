# Docs & Workflow — Tiêu chuẩn vinhlong360
> **STATUS (2026-07-07): active — bản 1.0 (SP0).**

## Mốc tham chiếu
Bài học truth-sync 2026-07-07 (89 finding, 25 file archive vì chuẩn không có răng) · CLAUDE.md §3.6.

## Quy tắc
| Rule | Phát biểu | Tầng | Cách đo |
|---|---|---|---|
| R60.1 | Mọi docs-active .md có `> STATUS (...)` trong 10 dòng đầu | hard-ratchet | check_doc_status |
| R60.2 | Lifecycle: active → done/obsolete/superseded-by → docs/archive/ (không xoá, có header lý-do) | quy-trình | review + archive/README |
| R60.3 | Spec/plan mới theo template superpowers (Goal/Architecture/Task/verify) | quy-trình | review |
| R60.4 | Internal link trong docs-active phải sống | hard-ratchet | check_links |
| R60.5 | Kết đợt bắt buộc có plan-result ("KẾT QUẢ") trước merge | hard (pre-merge) | pre_merge_check bước 8 |

## Ngoại lệ đã duyệt
— (chưa có)
