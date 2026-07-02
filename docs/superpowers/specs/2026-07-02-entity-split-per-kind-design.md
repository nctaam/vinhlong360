# Spec — Tách quản lý entity theo nhóm + bảng CTI mở rộng

**Ngày:** 2026-07-02 · **Trạng thái:** chủ dự án đã duyệt hướng (brainstorming cùng ngày).
**Bối cảnh:** chủ yêu cầu "tách entity ra cho dễ quản lý, mỗi loại khác nhau; AdminCP quản lý
sâu hơn" và chốt **cả hai tầng**: tách giao diện quản lý VÀ tách bảng vật lý. Đây là chủ dự án
kích hoạt con đường CTI mà nghiên cứu 2026-07 đã chừa sẵn ("bảng mở rộng cho tương lai") —
KHÔNG phải lặp lại phương án table-per-type-thay-thế đã bác.

## Nguyên tắc bất di bất dịch

1. **`entities` vẫn là bảng xương sống** — id/type/name/summary/description/placeId/
   coordinates/season/source/images/confidence… GIỮ NGUYÊN. `relationships` tiếp tục trỏ
   `entities.id`. Graph không đổi, RAM loader không đổi shape.
2. **Additive từng bước (§B2/§B5):** mỗi giai đoạn ship được, hệ thống chạy được, rollback được.
3. **Hợp đồng bất biến:** public API (`/api/entities/**`), shape RAM loader cho chat,
   format `web/data.json` export — **không đổi 1 byte** trước/sau. Contract test khoá.
4. Registry `agent/entity_schemas.py` vẫn là nguồn sự thật về *trường nào thuộc type nào*
   (form + validation); bảng CTI là nơi *lưu vật lý* các trường đó.

## Kiến trúc đích

### Cột phổ quát thăng cấp lên `entities` (8 cột, mọi type đều dùng)
`address TEXT, phone TEXT, website TEXT, hours TEXT, price_range TEXT, sub_category TEXT,
best_time TEXT, highlight TEXT` — nullable, backfill từ JSONB.

### 9 bảng CTI mở rộng (1-1 với entities.id, PK=FK, per-KIND)
| Bảng | Types | Cột chính |
|---|---|---|
| `entity_place_details` | attraction, nature, history | admission, architecture_style*, founding_year, religion, dress_code, heritage_type, heritage_level, historical_period, waterway_type, scenic_rating, best_view_point |
| `entity_food_details` | dish, drink, restaurant, cafe | origin, ingredients(JSONB), specialty, where_to_eat, cooking_method, main_ingredient, signature_dish, rating, review_count, parking(bool), wifi(bool), view |
| `entity_product_details` | product, craft_village | ocop_star, ocop_certified(bool), gi_certification, producer, variety, shelf_life, specialty, households, raw_material, recognition_date, cooperative |
| `entity_lodging_details` | accommodation | accommodation_type, star_rating, rooms, check_in, check_out, amenities(JSONB), booking_note |
| `entity_event_details` | event | date_start, date_end, lunar_date, month, duration_days, organizer, venue, target_audience |
| `entity_experience_details` | experience | duration, operator |
| `entity_facility_details` | facility | office_kind, emergency_phone, note_for_tourists, category_tag, transport_type |
| `entity_person_details` | person | role, birth_year, death_year, hometown |
| `entity_adminplace_details` | place | former_district, merged_from(JSONB), population, effective_date, governance_model |

\* chuẩn hoá luôn drift `architecture_style` (attraction) vs `architectural_style` (history) → 1 cột.

- Kind `itinerary`: đã có bảng riêng — không đụng. Kind `other` (organization/economy):
  chỉ dùng bộ chung → không cần bảng mở rộng.
- `attributes` JSONB SAU GĐ-C chỉ còn: đuôi đặc thù (sac_phong, deity_worshipped,
  schema_type…) + cụm KBYG (kbyg_tips, golden_hours, peak_days, crowd_level,
  amenity_badges, checklist — cross-cutting, giữ JSONB).
- DDL cả 2 engine (init.sql + migration; SQLite parity cho dev).

## Giai đoạn

### GĐ-A — Tách giao diện AdminCP (không đụng DB, giá trị ngay) — ✅ XONG + DEPLOYED 2026-07-02

> Hoàn thành đủ 7 task (commits GĐA.1→GĐA.6+7), 6 test backend mới xanh, build FE pass,
> deploy prod verify: search 200, 2 endpoint mới 401 (auth-gate), bundle chứa đủ 3 tính năng.
> Lưu ý thực thi: test brittle `test_entity_list_pagination_uses_count` (cửa sổ soi source
> 2500 ký tự) nới lên 4000 vì `list_entities` dài ra hợp lệ — assertion giữ nguyên.
1. **Backend (additive):** `GET /admin/entities` thêm param `kind` (expand types qua
   `KIND_OF_TYPE`); endpoint mới `GET /admin/entity-completeness?kind=` — % điền từng trường
   (8 trường base + trường registry của kind + ảnh/mùa/tọa độ thật) + top-N entity thiếu
   nhiều nhất. Read-only, tính trên dữ liệu RAM/DB (~1.7k dòng, rẻ).
2. **Sidebar:** mục "Nội dung" → submenu 9 nhóm + đếm (nguồn `/admin/entity-kinds` có sẵn).
3. **Trang kind-aware:** `admin/entities.vue` đọc `?kind=` → tiêu đề nhóm, **cột đặc thù**
   (Sản phẩm: sao OCOP/nhà SX; Ẩm thực: giá/rating; Sự kiện: ngày/venue; Lưu trú: loại/số
   phòng…), **bộ lọc đặc thù** (OCOP ≥4⭐, di tích quốc gia, có wifi…), type-options khi tạo
   mới giới hạn theo kind.
4. **Dashboard đầy đủ:** panel completeness trong trang kind.
5. **Bulk edit:** chọn nhiều (cap 100) → gán 1 trường=giá trị → loop PUT client-side qua
   endpoint sẵn có (tái dùng toàn bộ validate + entity_changes log), progress + lỗi từng dòng.
6. **Inline edit:** ô typed quan trọng sửa tại chỗ (text/number/select/bool) qua PUT sẵn có
   (merge attributes phía client như modal đang làm).
7. Refactor nhẹ: phần nào của `entities.vue` (1.234 dòng) tách được thành component
   (`KindColumns`, `CompletenessPanel`, `BulkBar`) thì tách — không nhân bản trang.

### GĐ-B — Nền móng DB (additive, CHƯA đổi hành vi đọc/ghi)
0. **Tiền đề bắt buộc:** sửa chuỗi migration đứt 3 chỗ (audit 2026-07-02): init.sql
   (posts.deleted_at), migration 059 = reviewer_note bị 029 che + `entity_changes` +
   `site_settings_history` trên PG + vào `PG_REQUIRED_TABLES`; **replay-test init.sql +
   002→059 trên PG docker TRẮNG** phải pass.
1. Migration 060: 8 cột phổ quát trên `entities` (cả init.sql + SQLite).
2. Migration 061: 9 bảng CTI (PK = entity_id FK ON DELETE CASCADE; ALTER OWNER vl360).
3. **Backfill script** (scripts/backfill_entity_details.py): đọc JSONB → điền cột/bảng;
   idempotent; `python scripts/backup_data.py` TRƯỚC (§B1); KHÔNG xoá JSONB ở bước này.
4. **Script đối chiếu** (scripts/verify_entity_details_parity.py): từng dòng JSONB ↔ cột,
   exit≠0 nếu lệch; chạy cả local SQLite + prod PG.
5. Test §B4: schema test mỗi bảng + backfill round-trip test.

### GĐ-C — Flip nguồn sự thật (feature flag `ENTITY_DETAILS_TABLES=true`)
1. DAL: `get_entity`/`get_entities_batch`/search enrich đọc JOIN extension khi flag bật —
   dựng lại `attributes` dict ĐÚNG shape cũ (typed keys từ cột + tail từ JSONB).
2. Ghi: admin create/update ghi cột/bảng CTI (typed) + JSONB (tail); `_bulk_load`/
   `replace_from_json` tách attributes khi import; port luôn guard coords/alias vào
   `_bulk_load` (vá risk audit #6).
3. Export DB→data.json re-join → format y hệt (round-trip test byte-level trên entity mẫu).
4. Contract test khoá TRƯỚC khi flip: snapshot shape `/api/entities/{id}` + RAM loader +
   export của ≥1 entity mỗi kind; chạy lại sau flip — phải giống hệt.
5. Rollback = tắt flag (JSONB typed keys vẫn nguyên). Bước cuối cùng riêng biệt (sau ≥1 tuần
   ổn định): script dọn typed keys khỏi JSONB (backup §B1 + chủ duyệt riêng).

## Tiêu chí nghiệm thu
- **GĐ-A:** mỗi nhóm có mục menu riêng, cột+lọc đặc thù đúng, dashboard % đúng với dữ liệu
  thật, bulk 20 entity OK + lỗi hiển thị từng dòng, inline edit lưu đúng; build xanh; pytest
  admin subset xanh; deploy verify trên prod.
- **GĐ-B:** replay chuỗi migration trên PG trắng pass; backfill parity exit 0 trên cả 2 engine.
- **GĐ-C:** contract test byte-identical; flag bật trên prod ≥1 tuần không sự cố mới sang
  bước dọn JSONB.

## Rủi ro & ràng buộc
- `database.py`/`admin.py` đang dirty bởi session song song → khi làm GĐ-B/C: **chủ nên tạm
  dừng session khác sửa vùng entity**; mọi edit của dự án này additive + scoped.
- Chuỗi migration đứt là tiền đề — không skip bước 0.
- Test baseline đang đỏ (36 fail không liên quan) — mọi test mới phải xanh, không làm tăng đỏ.
- Solo dev: GĐ-C chỉ flip khi GĐ-B parity sạch; không gộp GĐ-B+C một đợt deploy.
