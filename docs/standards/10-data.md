# Data — Tiêu chuẩn vinhlong360
> **STATUS (2026-07-07): active — bản 1.0 (SP0).**

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
| R10.5 | KHÔNG bịa fact thực địa (SĐT/giờ/giá/mùa) — chỉ nhập từ nguồn; thiếu thì để trống | checklist-ký* | ngoại lệ ký bên dưới |
| R10.6 | Ảnh CHỈ AI-gen — cấm Wikimedia/Pexels/Unsplash/UGC/cào báo | hard | check_banned_claims |
| R10.7 | "tỉnh Bến Tre/Trà Vinh" chỉ hợp lệ trong ngữ cảnh lịch sử ĐÃ whitelist (per-occurrence, chống swap) | hard-ratchet | check_tinh_cu + whitelist-tinh-cu.txt |
| R10.8 | Entity index-worthy (RICH) phải có ≥1 `source` — giữ thành quả 0 thiếu | hard-ratchet (baseline 0, SP2) | check_data_schema (data_rich_source, tái dùng seo.is_index_worthy) |
| R10.9 | Xuất xứ đặc sản/địa danh phải TRONG tỉnh (cấm gán Cái Bè/Lai Vung/Định Yên...) — nợ về 0 sau SP2 (quyết định chủ 2026-07-07: bỏ hẳn điểm ngoài tỉnh) | soft-ratchet (baseline 0) | check_content_voice (out_of_province) |

## Ngoại lệ đã duyệt
- **R10.5** không máy-đo-được trọn vẹn — *chủ dự án duyệt dạng checklist khi nhập liệu (2026-07-07); mọi phát hiện bịa-fact = sự cố P0.*
