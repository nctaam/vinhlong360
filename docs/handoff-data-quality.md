# Session 8: Data + SEO — Data Validation + SEO Optimization

> Paste toàn bộ nội dung này làm message đầu tiên.

## Bối cảnh

Worktree `C:/Code/vinhlong360/vl360-data-seo`, nhánh `dev/data-seo`. Dự án vinhlong360. **Đọc `CLAUDE.md` + `docs/PARALLEL-BRANCHES.md`.**

## Phạm vi file SỞ HỮU

**Scripts:**
- `scripts/*.py` (trừ `backup_data.py` — chạy nhưng KHÔNG sửa code)
- `tests/test_validate_data.py`

**Backend SEO:**
- `agent/seo.py` — SEO/JSON-LD/sitemap
- `agent/tests/test_seo_structured.py`

**Data:**
- `web/data.json` (chỉ qua script có dry-run, KHÔNG sửa tay)

**KHÔNG SỬA:** agent/*.py (trừ seo.py), web-nuxt/**, nuxt.config.ts, server.py.

## ⚠️ BẤT BIẾN

- **§B1** Chạy `python scripts/backup_data.py` **TRƯỚC MỌI** thao tác dữ liệu
- **§B7** KHÔNG chạy lệnh phá dữ liệu — viết script **dry-run** trước
- KHÔNG bịa dữ liệu — chỉ sửa lỗi có bằng chứng

## Công việc

### Đã xong (đợt trước):
- validate_data.py: thêm produced_in target type + place level checks
- seo.py: fix JSON-LD type mappings, 404 errors, media sitemap
- Tests cho cả hai

### Data quality tiếp:
- [ ] Self-loop relationship detection (entity trỏ về chính nó)
- [ ] Dangling itinerary-stop (stop tham chiếu entity không tồn tại)
- [ ] Audit ~38 entity mis-type → viết `scripts/fix_entity_types.py` (--dry-run)
- [ ] Audit ~9 entity duplicate → viết `scripts/find_duplicates.py` (Levenshtein)
- [ ] Test coverage cho database.py / knowledge.py edge cases

### SEO tiếp:
- [ ] JSON-LD enrichment cho FoodEstablishment, LodgingBusiness
- [ ] Sitemap: verify tất cả entity có trong sitemap
- [ ] og:image: verify mọi trang có og:image hợp lệ

## Verify

```bash
python scripts/backup_data.py
python scripts/validate_data.py
python -m pytest -q
```

## Commit prefix: `[data-seo]`
