# Campaign "Tỉnh mới" — sửa text tỉnh-cũ trong data + sweep miền-Tây + tái lập export

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline). 1 việc/commit.
> **STATUS (2026-07-07): active — đang thực thi.** Chủ dự án duyệt cả 3 phần (P0 data + P1 sweep + P1 export) trong phiên 2026-07-07.

**Goal:** (1) Sửa CÓ NGỮ CẢNH ~490 occurrence "tỉnh Bến Tre/Trà Vinh" đứng như tỉnh hiện hành trong data (hệ quả DF-02 06/2026 — quy tắc đã bị đảo chiều sau sáp nhập); (2) dẹp filler "miền Tây/ĐBSCL" trong copy hardcode FE; (3) tái lập cơ chế export DB→data.json.

**Bất biến áp dụng:** B1 (backup trước MỌI thao tác — cả 3 kho), B7 (không lệnh phá; mọi apply có --dry-run trước), B3/B4 (script mới có test), §1.6 CLAUDE.md (chính sách gọi tên tỉnh).

## Grounding đã chốt (2026-07-07)

| Kho | Entity | Occurrence "tỉnh Bến Tre\|Trà Vinh" | Vai trò |
|---|---|---|---|
| **Prod PG** (vl360@localhost/vinhlong360 trên VPS) | 1.730 | 314 entity dính (≈490 occ) | **SoT thật — nguồn sinh patch + đích áp chính** |
| web/data.json | 1.730 | 493 occ / 311 entity (desc 162, address 161, summary 136, name 11, attr khác ~23) | Export cũ của prod → thay bằng export MỚI sau khi sửa prod |
| Local SQLite (agent/data/vinhlong360.db) | 1.782 | 121 occ / 86 entity | Phân kỳ riêng — áp patch match-được-thì-áp; reconcile 1.782 vs 1.730 là việc KHÁC (không thuộc campaign này) |

Backend chọn theo `DATABASE_URL` (database.py:34); admin `POST /export` (admin.py:3143) stream từ `db.all_entities()` — tái dùng shape này cho script export.

## Chính sách rewrite theo loại (KHÔNG batch-replace mù)

1. **Địa chỉ hiện tại** (`attr:address` + mẫu "tọa lạc/nằm tại … tỉnh X"): thay `tỉnh Bến Tre|Trà Vinh` → `tỉnh Vĩnh Long`; GIỮ tên huyện cũ trong address (định vị dân gian hữu ích, không phải claim hành chính).
2. **Mô tả hiện tại** ("của tỉnh X", "thuộc tỉnh X" nói vị thế hôm nay): → `tỉnh Vĩnh Long`, hoặc bỏ chữ "tỉnh" giữ địa danh vùng ("đặc sản vùng Bến Tre") khi câu nói về văn hoá/đặc sản vùng — chọn theo ngữ cảnh từng câu (agent).
3. **Lịch sử** (năm <7/2025, "trước đây", quyết định/công nhận thời điểm cũ): **GIỮ NGUYÊN** (đúng lịch sử — "UBND tỉnh Trà Vinh công nhận năm 2016" là fact); chỉ thêm "(cũ)" khi câu dễ đọc nhầm thành hiện tại.
4. **Tên riêng** (`name`, `attr:name`, organizer — 18 chỗ): **KHÔNG đổi** (đổi tên cơ quan cần nguồn chính thống — Track-H); xuất danh sách chờ trong plan-result.

## Task

- [ ] **T1** `scripts/export_data.py` (TDD): xuất {entities, relationships, itineraries} từ DB qua database layer, khớp shape data.json; atomic write (.tmp+replace); `--out`, `--dry-run` in diff summary vs file hiện có. Test: tests/test_export_data.py trên SQLite temp. *KHÔNG auto-chạy định kỳ — công cụ thủ công.*
- [ ] **T2** `scripts/fix_tinh_moi.py`: `extract` (từ JSON dump prod) → occurrences.json (entity, field, value, matches+context); rule-engine gán loại 1-4; workflow agents sinh `new_value` cho loại 1-2 + rà loại 3 (giữ/thêm-cũ); adversarial verify mẫu ≥15%; output patches.json {entity_id, field, old_value, new_value}.
- [ ] **T3** Backup B1: `backup_data.py` + copy SQLite + **pg_dump prod** (giữ trên VPS + scp 1 bản về local).
- [ ] **T4** Áp: prod PG (script apply chạy trên VPS, `--dry-run` trước, match old_value mới ghi) → **restart vl-agent** (chat nạp RAM lúc boot); local SQLite (match-được-thì-áp); verify counts sau áp.
- [ ] **T5** Export prod → `web/data.json` mới (giải phân kỳ data.json↔prod); so diff sanity (±entity=0, chỉ text đổi).
- [ ] **T6** FE sweep "miền Tây/ĐBSCL" copy hardcode (du-lich/san-pham/theo-mua editorial, eyebrow atlas/wake-hero, interstitial...) — thay bằng đặc-thù-Vĩnh-Long theo playbook; SSR verify.
- [ ] **T7** Kết: pytest (đối chiếu fail-đã-biết) + build FE + verify 3 kho + plan-result + merge main + memory.

**Điều kiện dừng:** prod apply lỗi giữa chừng → dừng, restore pg_dump, báo người. Mơ hồ ngữ cảnh không phân loại được → để nguyên + ghi danh sách chờ (không đoán).
