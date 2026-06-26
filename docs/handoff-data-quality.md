# Handoff: Session Data Quality (`dev/data-quality`)

> Paste toàn bộ nội dung này làm message đầu tiên trong session Claude Code mới.

---

## Bối cảnh

Bạn đang làm trên nhánh `dev/data-quality` của dự án vinhlong360 — MXH du lịch/OCOP cho Vĩnh Long (3 tỉnh sáp nhập). Solo dev, Nuxt 4 SSR + FastAPI. **Đọc `CLAUDE.md` và `docs/PARALLEL-BRANCHES.md` trước khi bắt đầu.**

## Nhánh hiện tại

```bash
git checkout dev/data-quality
```

## Phạm vi file bạn SỞ HỮU (chỉ sửa các file này)

- `scripts/*.py` (trừ `backup_data.py` — chạy nhưng KHÔNG sửa code)
- `agent/tests/test_database.py`, `agent/tests/test_knowledge.py` (thêm test mới)
- `web/data.json` (chỉ qua script có dry-run, KHÔNG sửa tay)

**KHÔNG SỬA:** agent/*.py (trừ test), web-nuxt/**, nuxt.config.ts, server.py, bất kỳ file production nào.

## ⚠️ BẤT BIẾN QUAN TRỌNG

- **§B1** Chạy `python scripts/backup_data.py` **TRƯỚC MỌI** thao tác dữ liệu
- **§B7** KHÔNG chạy lệnh phá dữ liệu — viết script **dry-run** trước, in ra thay đổi, xác nhận rồi mới apply
- **§1.4** KHÔNG bịa dữ liệu — chỉ sửa lỗi có bằng chứng (type sai, duplicate rõ ràng, cấu trúc hỏng)
- KHÔNG ghi thêm data vào entity nếu không có nguồn thật (địa chỉ, SĐT, mùa vụ = cần nguồn ngoài)

## Công việc

### 1. Nâng cấp validate_data.py (P1-16)
Thêm check mới vào `scripts/validate_data.py`:
- Self-loop relationship (entity trỏ về chính nó)
- Dangling itinerary-stop (stop tham chiếu entity không tồn tại)
- `produced_in` target-type validation (target phải là place/ward)
- `place` entity thiếu `level` attribute
- Chạy: `python scripts/validate_data.py` — phải exit 0

### 2. Audit & fix entity mis-type (~38 entity)
Từ audit (ke-hoach-hoan-thien-10-tang.md §3.6): ~38 entity có type sai.
- Viết script `scripts/fix_entity_types.py` với `--dry-run` flag
- Script phải in rõ: entity nào, type hiện tại → type đề xuất, lý do
- Chỉ fix khi có bằng chứng rõ ràng (tên chứa "quán/nhà hàng" nhưng type=place → restaurant)

### 3. Audit & fix entity duplicate (~9 entity)
- Viết script `scripts/find_duplicates.py` — Levenshtein/substring match trên name
- Hiện rõ các cặp nghi ngờ kèm evidence (name, type, placeId, summary)
- Script merge: giữ entity giàu data hơn, redirect relationships

### 4. Mở rộng test coverage
- Thêm test cho edge case database.py (empty result, invalid input, boundary values)
- Thêm test cho knowledge.py search (Vietnamese diacritics, partial match)

## Verify

```bash
python scripts/backup_data.py           # backup trước
python scripts/validate_data.py         # validation pass
python -m pytest -q                     # tests xanh
```

## Commit convention

```
[data] mô tả ngắn

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
