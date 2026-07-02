# Entity content-model — nghiên cứu & lộ trình (2026-07)

> Nguồn: deep-research đa-agent (9 agent: map codebase + taxonomy thực nghiệm +
> nghiên cứu pattern STI/TPT/CTI + headless-CMS + JSONB migration). Grounding:
> 1730 entities / 17 type thật, backup `scratch/backups/20260702-111701`.

## Bối cảnh & yêu cầu

Chủ dự án muốn: tách các loại entity (địa điểm, sản phẩm, lưu trú, sự kiện, lễ hội,
trải nghiệm, lịch trình) để **quản lý thuận tiện**, mỗi danh mục có **cấu trúc khác
nhau cho phù hợp**, nâng cấp AdminCP quản lý toàn diện, phát triển lâu dài.

## Hiện trạng (đo thực tế)

- **1 bảng `entities` đa hình** (init.sql:21): `type` TEXT discriminator + `attributes`
  JSONB catch-all. `itineraries` + `relationships` là bảng riêng. `images` JSONB rỗng
  0/1730 (ảnh AI-gen theo yêu cầu).
- **17 type thật** (nhiều hơn 7 danh mục chủ nêu):
  - Địa điểm (du lịch): `attraction` (202), `history` (181), `nature` (124)
  - Sản phẩm/OCOP: `product` (218), `craft_village` (85)
  - Ẩm thực/Ăn uống: `dish` (118), `restaurant` (**188**), `cafe` (56), `drink` (1)
  - Lưu trú: `accommodation` (164)
  - Trải nghiệm: `experience` (92)
  - Sự kiện & Lễ hội: `event` (67) — *lễ hội gộp trong event qua `lunar_date`*
  - Lịch trình: `itinerary` (16) + bảng `itineraries`
  - Chưa nằm trong 7 danh mục: `facility` (58, cơ quan HC), `person` (34), `place`
    (125, **xã/phường hành chính** — KHÁC với "địa điểm du lịch**)
- **Nỗi đau quản lý thật nằm ở AdminCP, KHÔNG phải storage:** form sửa entity là 1
  form 6-field generic (id/name/type/placeId/summary/images) + panel KBYG, **giống hệt
  cho mọi loại**. `attributes` không có editor (chỉ ~6 key KBYG). 2 bug: type dropdown
  (17) lệch `VALID_TYPES` (13) → restaurant/cafe/drink/place/itinerary 422 khi lưu; id
  regex client cho `_` nhưng server chặn.

## Quyết định kiến trúc: STI-with-registry (KHÔNG tách bảng vật lý)

Chủ dự án ban đầu chọn "tách bảng vật lý theo loại". Nhưng **hai nguồn độc lập cùng
bác bỏ** phương án đó:

1. **Kiến trúc đã chốt của dự án** (`kien-truc-va-lo-trinh.md` §2.2 + design principle
   #2): *"Đặc sản, trải nghiệm, sự kiện, homestay… không phải bảng riêng… Tránh nở
   bảng. Chỉ tách bảng phụ khi một loại có truy vấn nặng đặc thù."*
2. **Nghiên cứu best-practice** (Fowler PoEAA + Postgres, ở đúng quy mô 1730 dòng/17
   type nạp RAM): tách bảng *"buys almost nothing and costs a great deal"* — phá vỡ
   không-gian id thống nhất mà đồ thị quan hệ + RAM-loader phụ thuộc, biến mọi truy
   vấn cross-type thành UNION fan-out, ép migration big-bang vi phạm §B2/§B5, và làm
   DoD-7 ("thêm type không phải sửa nhiều nơi") **khó hơn**.

**Chốt:** giữ 1 bảng `entities`; thêm **lớp content-model registry ở tầng ứng dụng**
(giống headless CMS Strapi/Directus) — mỗi type có schema field riêng lái form AdminCP
+ validation + hiển thị. Đây chính là "mỗi danh mục có cấu trúc khác nhau" nhưng
additive & reversible, không DDL. Đạt đúng mục tiêu quản lý mà không gánh rủi ro.

Mục tiêu xa (nếu cần): **CTI** — bảng lõi `entities` giữ nguyên + bảng mở rộng
`entity_<kind>(id REFERENCES entities(id) 1:1)` cho cột promote + `extra JSONB`. KHÔNG
phải pure TPT. Chỉ làm khi có trigger (xem Backlog).

## Lộ trình theo pha (additive, expand-contract)

| Pha | Mục tiêu | Additive | Trạng thái |
|----|----------|----------|-----------|
| **1** | Registry field-schema/type + form AdminCP typed + validation + fix 2 bug | ✅ (no DDL) | **XONG + DEPLOYED** (2026-07-02) |
| **2** | Lớp `kind` (7 danh mục) derived trên 17 type, group catalog/report | ✅ | **XONG + DEPLOYED** (2026-07-02) |
| 3 | Bảng mở rộng `entity_<kind>` + generated columns (expand) | ✅ | chưa |
| 4 | Backfill + parity test (idempotent, batched) | ✅ | chưa |
| 5 | Read-switch sau config flag (soak 1-2 tuần, rollback = tắt flag) | ✅ | chưa |
| 6 | Contract (chỉ sau soak; generated cột thường NO-OP) | ❌ destructive | chưa |

### Pha 1 — đã triển khai (backend)
- `agent/entity_schemas.py`: registry 18 type, `validate_attributes()` (coerce
  number/bool/tags, cảnh báo required/enum, **giữ nguyên bespoke tail**), `valid_types()`,
  `kind_of()`, `all_schemas()`.
- `admin.py`: `VALID_TYPES` lấy từ registry (fix mismatch); validate attributes khi
  create/update (trả `warnings`); endpoint `GET /admin/entity-schema`; id regex cho `_`.
- Frontend: `components/admin/SchemaField.vue` dispatcher + `entities.vue` render field
  group theo `form.type`, merge vào attributes (giữ tail, xoá field trống).
- Test: `agent/tests/test_entity_schemas.py` (13 test).

## Câu hỏi mở (cần chủ dự án)
- `restaurant`/`cafe` (ăn uống, 244 entity) nên là danh mục "Ẩm thực" riêng hay gộp
  "sản phẩm"? (hiện map kind=`food`).
- `place` hành chính (xã/phường) có nên tách hẳn khỏi mô hình du lịch không?
- `festival` giữ là sub-type của `event` (qua `lunar_date`) hay tách type riêng?
- Long-tail key đặc thù (sac_phong, deity_worshipped…) — giữ JSONB linh hoạt (đang vậy)
  hay chuẩn hoá dần?
