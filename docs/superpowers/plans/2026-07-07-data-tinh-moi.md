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

---

## KẾT QUẢ THỰC THI (2026-07-07)

| Kho | Trước | Sau | Ghi chú |
|---|---|---|---|
| **Prod PG** | 498 occ / 314 entity | **87 occ — TOÀN chủ-đích** | 427 patch, dry-run trước, restart vl-agent, health 200 |
| web/data.json | 493 occ | **87 occ (khớp prod)** | 427 patch + 3 vá phân-kỳ address |
| Local SQLite | 121 occ | 109 occ | Kho phân kỳ — áp 12 match; còn lại chờ reconcile local↔prod (backlog) |

**87 occurrence còn lại là ĐÚNG (giữ chủ đích):** 65 ngữ-cảnh = lịch sử có mốc thời gian (quyết định/công nhận của UBND tỉnh cũ) + chứng nhận gắn " (cũ)" + 9 uncertain giữ-nguyên-không-đoán; 22 tên riêng cơ quan.

**Phương pháp:** workflow 78 agent phân loại chính sách a/b/c/d (270 rewrite / 29 keep / 9 uncertain); 67 mẫu verify đối kháng — 0 lỗi; diff-guard lập trình (difflib opcodes giao match-spans) chặn mọi sửa-ngoài-cụm; apply match-old-value-mới-ghi.

**Chất lượng phân loại đáng ghi:** "chùa cổ nhất tỉnh Bến Tre" KHÔNG thay thành tỉnh Vĩnh Long (sai fact — chùa Khmer Trà Vinh cổ hơn) → "vùng Bến Tre"; stat "90% toàn tỉnh Trà Vinh" giữ phạm vi "vùng"; tổng đài 115 phạm vi phục vụ "vùng Bến Tre".

**T1/T5 export:** scripts/export_data.py hồi sinh (5 test, atomic, dry-run diff, fix datetime PG). Export prod chạy OK — NHƯNG shape DB-export ≠ data.json (8 cột phẳng-hoá thừa: address/phone/website/hours/price_range/sub_category/best_time/highlight + thiếu createdAt) → KHÔNG thay-nguyên-file; data.json sửa bằng patch. Chuẩn hoá shape export ↔ data.json = backlog.

**T6 sweep miền-Tây:** 38 chỗ/12 file template FE = 0 "miền Tây"; eyebrow mới "TỈNH VĨNH LONG · MIỆT VƯỜN — XỨ DỪA — ĐẤT CHÙA KHMER"; bắt thêm lỗi xuất xứ "chiếu lác Định Yên" (Đồng Tháp) → hoa kiểng Cái Mơn. Data còn 253 "miền Tây" trong summary/desc (nhiều chỗ là văn nói hợp lệ) → campaign content riêng.

### 22 tên riêng chờ nguồn chính thống (Track-H — KHÔNG tự đổi)
- bao-tang-tinh-ben-tre :: Bảo tàng tỉnh Bến Tre
- bao-tang-tong-hop-tinh-tra-vinh :: Bảo tàng Tổng hợp tỉnh Trà Vinh
- cua-hang-ocop-tinh-ben-tre-trung-tam-xuc-tien-dau-tu-ho-tro-doanh-nghiep-ben-tre :: Cửa hàng OCOP tỉnh Bến Tre (Trung tâm Xúc tiến Đầu tư & Hỗ trợ Doanh nghiệp)
- giai-dua-ghe-ngo-truyen-thong-tinh-ben-tre-ben-tre :: Giải Đua Ghe Ngo truyền thống tỉnh Bến Tre
- giai-marathon-tra-vinh-tra-vinh-marathon-tra-vinh :: Giải Marathon Trà Vinh (Tra Vinh Marathon)
- giai-the-thao-dan-toc-quoc-phong-tinh-tra-vinh-tra-vinh :: Giải Thể thao Dân tộc - Quốc phòng tỉnh Trà Vinh
- hoi-cho-thuong-mai-du-lich-tinh-tra-vinh-tra-vinh :: Hội chợ Thương mại - Du lịch tỉnh Trà Vinh
- hoi-thi-ghe-ngo-mo-rong-tinh-tra-vinh-dua-ghe-ngo-truyen-thong-tra-vinh :: Hội thi Ghe Ngo mở rộng tỉnh Trà Vinh (Đua Ghe Ngo truyền thống)
- le-hoi-van-hoa-the-thao-du-lich-dong-bao-khmer-nam-bo-tinh-tra-vinh-tra-vinh :: Lễ hội Văn hóa - Thể thao - Du lịch đồng bào Khmer Nam Bộ tỉnh Trà Vinh
- lien-hoan-don-ca-tai-tu-nam-bo-tinh-ben-tre-ben-tre :: Liên hoan Đờn ca Tài tử Nam Bộ tỉnh Bến Tre
- lien-hoan-van-nghe-quan-chung-tinh-tra-vinh-tra-vinh :: Liên hoan Văn nghệ Quần chúng tỉnh Trà Vinh
- tuyen-xe-buyt-noi-tinh-tra-vinh-cac-tuyen-tp-tra-vinh-di-huyen-tra-vinh :: Tuyến xe buýt nội tỉnh Trà Vinh (các tuyến TP. Trà Vinh đi huyện)

### 9 uncertain đã giữ nguyên (rà tay khi có thời gian)
- chua-luong-xuyen :: description — d — 'hiện là trụ sở Ban Trị sự GHPGVN tỉnh Trà Vinh': sau sáp nhập BTS 3 tỉnh hợp nhất thành BTS tỉnh Vĩnh Long, chưa xác minh được trụ sở m
- chua-luong-xuyen :: attr:highlight — d — cùng vấn đề 'hiện là trụ sở GHPGVN tỉnh Trà Vinh'; chưa rõ trụ sở BTS tỉnh mới → giữ, cần kiểm chứng
- san-chim-chua-phat-lon-tra-vinh :: description — d — record lẫn dữ liệu: entity là Chùa Phật Lớn (Trà Vinh) nhưng text nói Sân chim Vàm Hồ (vốn ở Ba Tri, Bến Tre); claim 'lớn nhất của tỉnh 
- san-chim-chua-phat-lon-tra-vinh :: summary — d — cùng lỗi lẫn Vàm Hồ/Chùa Phật Lớn như description
- tuyen-xe-buyt-noi-tinh-tra-vinh-cac-tuyen-tp-tra-vinh-di-huyen-tra-vinh :: description — d — cụm 'Tuyến xe buýt nội tỉnh Trà Vinh...' là echo nguyên văn tên entity; sửa riêng description sẽ lệch field name — cần xử đồng bộ với na
- xa-cho-lach :: description — d — 'thuộc huyện Chợ Lách, tỉnh Bến Tre' nói vị trí hiện tại (loại a) nhưng huyện đã bãi bỏ; thay tỉnh sẽ tạo cặp sai 'huyện Chợ Lách, tỉnh 
- xa-cho-lach :: summary — d — như description: cần bỏ 'huyện Chợ Lách' mới thay tỉnh được, ngoài phạm vi cho phép
- xa-hung-khanh-trung :: description — d — text hỏng sẵn ('huyện Chợ Lách + H', câu đứt 'Mỏ Cày Bắc.' cuối); cụm 'tỉnh Bến Tre' gắn huyện đã bãi bỏ, thay riêng tỉnh tạo cặp sai; c
- xa-hung-khanh-trung :: summary — d — summary cụt giữa chừng + 'huyện Chợ Lách + H' hỏng; như description, cần viết lại ngoài phạm vi

