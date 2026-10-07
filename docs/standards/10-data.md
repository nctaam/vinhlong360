# Data — Tiêu chuẩn vinhlong360
> STATUS: active (2026-09-15) — Tiêu chuẩn toàn vẹn dữ liệu.

## Mốc tham chiếu
Schema.org (type mapping đã dùng trong seo.py) · nguyên tắc anti-hallucination (CLAUDE.md §1.7, B7) · entity-content-model.md (17 type STI-with-registry) · chính sách tên tỉnh CLAUDE.md §1.6.

## Quy tắc
| Rule | Phát biểu | Tầng | Cách đo |
|---|---|---|---|
| R10.1 | `id` entity duy nhất toàn kho | hard | check_data_schema (`R10.schema`) |
| R10.2 | `type` thuộc đúng 17 enum TYPE_META (nguồn sự thật: useConstants.ts) | hard | check_data_schema |
| R10.3 | Trường bắt buộc: id, type, name, summary — không rỗng | hard | check_data_schema |
| R10.3b | Trường bắt buộc PER-TYPE theo registry `agent/entity_schemas.py` (person.role, accommodation.accommodation_type, facility.office_kind, craft_village.specialty) | hard-ratchet (baseline 49 lúc bật, SP2) | check_data_schema (data_typed_required) |
| R10.4 | `coordinates` trong bbox tỉnh [lat 9.0–10.6, lng 105.6–107.1] hoặc null | hard | check_data_schema |
| R10.hash | `web/data.json` thuộc Git phải khớp hash chuẩn khi quét staged/toàn kho. `agent/data/vinhlong360.db` là runtime local bị ignore và được ghi liên tục, nên chỉ hash trong kiểm tra tường minh có truyền đúng đường dẫn DB | hard | check_data_schema (`data_store_hash`) |
| R10.5 | KHÔNG bịa fact thực địa (SĐT/giờ/giá/mùa) — chỉ nhập từ nguồn; thiếu thì để trống | checklist-ký* | ngoại lệ ký bên dưới |
| R10.6 | Ảnh AI phải ghi nhãn và không giả ảnh thật; ảnh báo chí/tư liệu/chính thức chỉ hợp lệ khi có `image_author`, `image_source`, `image_license` và URL nguồn truy vết. Cấm Wikimedia/Pexels/Unsplash/UGC và cào/hotlink ảnh chưa có quyền. Nợ URL lịch sử được khóa theo ID tại `r10.6-image-url-debt.txt`: không được tăng và phải xóa ID khi bổ sung nguồn | hard-ratchet (baseline 40 theo batch-21) | check_banned_claims (`image_source_policy`) |
| R45.1 | Tệp WebP tương ứng phải tồn tại; caption/alt phải đủ dài và không chứa địa danh cũ, filler hoặc công thức mở bài | hard | check_image_hygiene |
| R10.7 | "tỉnh Bến Tre/Trà Vinh" chỉ hợp lệ trong ngữ cảnh lịch sử ĐÃ whitelist (per-occurrence, chống swap) | hard-ratchet | check_tinh_cu + whitelist-tinh-cu.txt |
| R10.8 | Entity được `agent/index_policy.py` quyết định indexable phải có ≥1 URL nguồn HTTP(S) bên ngoài; lỗi tải policy artifact/evidence là lỗi hard | hard-ratchet (baseline 0, SP2); artifact-load failure: hard | check_data_schema (`data_rich_source`, tái dùng `index_policy.decide_entity`) |
| R10.9 | Xuất xứ đặc sản/địa danh phải TRONG tỉnh (cấm gán Cái Bè/Lai Vung/Định Yên...) — nợ về 0 sau SP2 (quyết định chủ 2026-07-07: bỏ hẳn điểm ngoài tỉnh) | soft-ratchet (baseline 0) | check_content_voice (out_of_province) |

## Authority trong Phase A

- Backend runtime writes make the configured database the primary runtime store.
- `web/data.json` is a tracked export/fallback snapshot, not an automatic replacement for the configured database.
- Neither current local store may overwrite the other while parity drift remains unexplained.
- `scripts/checks/audit_data_parity.py` is diagnostic in Phase A: its normal mode reports drift without creating a hard or CI gate.
- Strict parity becomes a hard gate only after reviewed reconciliation establishes the intended relationship and field state.

## Ngoại lệ đã duyệt
- **R10.5** không máy-đo-được trọn vẹn — *chủ dự án duyệt dạng checklist khi nhập liệu (2026-07-07); mọi phát hiện bịa-fact = sự cố P0.*
