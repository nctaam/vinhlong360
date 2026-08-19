# Runbook cutover legacy JSONL — Correction Case Pilot

> STATUS: active
> Kế hoạch này KHÔNG tự cho phép nhập thật/đóng băng trên production (Review Protocol mục 4). Mọi bước mutate cần lệnh trực tiếp của chủ dự án, backup trước (B1), và chạy trên đích được nêu tên tường minh.

## Nguyên tắc

- **Một quyền ghi cho mỗi báo cáo**: kernel HOẶC JSONL, không bao giờ cả hai.
- **Cutover một chiều**: đã đóng băng thì hạ cờ không mở lại làn JSONL cho corrections (503 trung thực thay vì tách đôi sổ ghi). Trường kernel không giữ (ảnh, nguồn, khác) vẫn đi làn cũ.
- Nguồn `reports.jsonl` là **bằng chứng chỉ-đọc** — không sửa, không xoá, digest từng dòng theo byte gốc.

## Trình tự (mỗi bước phải xanh mới sang bước sau)

```bash
python scripts/backup_data.py
```
```bash
python scripts/migrate_info_reports_to_cases.py scan --source agent/data/reports.jsonl
```
Đọc report: total = valid + rejected + duplicates; ghi lại `source_digest`.

```bash
python scripts/migrate_info_reports_to_cases.py shadow-import --source agent/data/reports.jsonl --confirm-target "<tên-DB-đích>" --input-digest "<sha256-từ-scan>" --backup-evidence "<đường-dẫn-backup-vừa-tạo>"
```
```bash
python scripts/migrate_info_reports_to_cases.py reconcile --source agent/data/reports.jsonl --confirm-target "<tên-DB-đích>" --input-digest "<sha256>" --backup-evidence "<backup>"
```
`passed: false` = DỪNG. Không sửa số cho khớp; tìm dòng không giải thích được trong `legacy_intake_records`.

```bash
python scripts/migrate_info_reports_to_cases.py freeze-correction-writes --confirm-target "<tên-DB-đích>" --input-digest none --backup-evidence "<backup>"
```
Freeze ghi **hai đầu**: hàng bền trong PostgreSQL (`__correction_write_freeze__`) và file marker cạnh `reports.jsonl` (adapter đọc mỗi request).

## Phân loại (khoá cứng, không bịa ngữ nghĩa)

| Legacy | Thành | Ghi chú |
|---|---|---|
| stale_field/entity/facility + field ánh xạ + có detail | correction | reported_value đọc từ entry sống |
| thiếu detail hoặc field không ánh xạ | manual_triage | KHÔNG bịa quyết định |
| post/comment | moderation_link | ở lại làn kiểm duyệt |
| `resolved` cũ | giữ nguyên legacy_status | KHÔNG bao giờ thành `corrected` |
| `contact` cũ | không nhập | KHÔNG bao giờ thành consent |
| dòng hỏng | rejected | giữ locator để truy vết |
| dòng trùng | 1 case + n locator | replay idempotent theo (file, line) |

## Rollback

- Hạ cờ UI/intake được; kernel **vẫn là quyền ghi** cho corrections đã cutover. Không có "un-freeze" — nếu chủ dự án muốn đảo, đó là một quyết định mới cần spec riêng, không phải thao tác runbook.
