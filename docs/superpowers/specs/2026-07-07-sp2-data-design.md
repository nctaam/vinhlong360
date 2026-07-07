# Spec SP2 — Data: hợp nhất 3 kho + schema-gate per-type + shape round-trip

> **STATUS (2026-07-07): active — spec SP2 theo điều lệ chương trình chuẩn-hoá (spec cha v2). Grounding số thật cùng ngày.**

## Grounding đã chốt (đo 2026-07-07)

| Fact | Số | Hệ quả thiết kế |
|---|---|---|
| Local-only entity | **54** (19 history, 15 attraction, 9 craft_village…) — **54/54 có source, 0 thiếu summary**, 11 thin, 2 dính tỉnh-cũ | Content THẬT chưa lên prod → **đẩy LÊN prod** sau khi vá 2 tỉnh-cũ + qua gate |
| Prod-only | 2 (xã Thạnh Phong, Hậu Lộc — place migration) | Kéo xuống local qua đồng bộ |
| Entity chung text khác | 1.728/1.728 (local là bản cũ) | Text: **prod thắng** (AdminCP + campaign) — local nhận toàn văn prod |
| RICH thiếu source | **0/405** | R10.8 bật gate = hard-ratchet baseline 0 (giữ thành quả) |
| Per-type schema | ĐÃ CÓ `agent/entity_schemas.py` (registry 18 type, deployed Pha 1) | Gate TÁI DÙNG registry — không chế chuẩn thứ hai |
| Shape export ≠ data.json | 8 cột phẳng thừa + thiếu createdAt | Chuẩn shape = data.json hiện tại (consumer giữ nguyên); export chuyển đổi + round-trip test |
| R10.9 (28 occ Cái Bè/Lai Vung/Định Yên) | Đa số HỢP LỆ (điểm lân cận có chú thích "(Tiền Giang)"; entity chợ nổi Cái Bè là sản phẩm thật) + 1 ca address tự-mâu-thuẫn | Cần **whitelist per-occurrence** như tinh_cu + **câu hỏi phạm vi cho chủ** (điểm lân cận ngoài tỉnh giữ/bỏ) — KHÔNG tự xoá entity |

## Thiết kế

1. **Reconcile một chiều có chọn lọc:** (a) vá 2 occ tỉnh-cũ trong 54 local-only (phân loại ngữ cảnh); (b) đẩy 54 entity local-only → prod (pg_dump trước; qua schema-gate); (c) export prod (1.784) làm bản chuẩn → thay data.json + **thay text local SQLite bằng bản prod** (backup local trước). Kết quả: 3 kho = 1.784 entity, text đồng nhất; cập nhật whitelist tinh-cu nếu 2 occ là lịch-sử-giữ.
2. **Shape:** `export_data.py` chuẩn hoá output = shape data.json (drop address/phone/website/hours/price_range/sub_category/best_time/highlight phẳng; giữ createdAt). Round-trip test: `replace_from_json(export(DB)) → export lại ≡ lần 1` trên SQLite temp.
3. **Schema-gate per-type:** `check_data_schema` gọi `entity_schemas.validate_attributes` — vi phạm **required** per-type = counter mới `R10.3b` (hard-ratchet, baseline đo lúc bật; đích SP2: không tăng, trả dần); giữ các gate cũ.
4. **R10.8 RICH-source:** thêm vào check_data_schema (hard-ratchet baseline 0).
5. **R10.9:** thêm cơ chế whitelist `whitelist-ngoai-tinh.txt` (per entity:field, chú-thích-ngoài-tỉnh rõ ràng = hợp lệ); ca mâu thuẫn (hu-tieu-cho-cai-be address "Vĩnh Long" + placeId VL nhưng chợ ở Tiền Giang) → rà tay; **quyết định giữ/bỏ điểm-lân-cận = chủ dự án** (treo tới khi trả lời — không chặn phần còn lại).

## DoD SP2 (số cứng)
3 kho cùng **1.784** entity, text đồng nhất (verify script) · round-trip test pass · R10.8 gate bật baseline 0 · R10.3b gate bật + baseline ghi nhận · scorecard data-dim KHÔNG TỤT và nợ R10.9 giảm về whitelist-hoá (còn lại chỉ ca chờ chủ) · pytest/build xanh · prod restart health 200.

## Ngoài phạm vi SP2
Làm giàu season/hours/tips theo nguồn (SP6/Track-H) · xoá/giữ entity lân-cận ngoài tỉnh (chờ chủ) · CTI Pha 3-6 của content-model.
