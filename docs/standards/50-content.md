# Content — Tiêu chuẩn vinhlong360
> **STATUS (2026-07-07): active — bản 1.0 (SP0).**

## Mốc tham chiếu
E-E-A-T · docs/toi-uu-chong-ai-va-google-spam-playbook.md (giọng đặc-thù-Vĩnh-Long) · cổng index P0-1 (agent/seo.py: INDEX_RICH_WORDS = 130 từ).

## Quy tắc
| Rule | Phát biểu | Tầng | Cách đo |
|---|---|---|---|
| R50.1 | CẤM claim "đã xác minh" trong content (đồng nhất R40.3) | hard | check_banned_claims |
| R50.2 | Filler cấm: "miền Tây" (positioning), "sông nước hữu tình", "thiên đường", "hidden gem", "must-see", "không thể bỏ lỡ", "đắm chìm", "hòa mình vào", "điểm đến lý tưởng" | soft-ratchet | check_content_voice |
| R50.3 | Công thức mở bài cấm ("Tọa lạc/Nằm ở/…/là một") + kết sáo ("Hãy đến/Đừng bỏ lỡ") — câu đầu/cuối | soft-ratchet | check_content_gates |
| R50.4 | Entity summary+description ≥200 ký tự (sàn); đích index-worthy = 130 TỪ (seo.py) | soft | check_thin_content |
| R50.6 | Giọng đặc-thù-VL khi viết mới: tên riêng + số liệu + mùa vụ + chi tiết first-hand, nhịp câu đa dạng | checklist-ký* | checklist playbook |
| R50.7 | Superlative-trơ cấm: "nổi tiếng/nhất vùng/đậm đà bản sắc" trong câu KHÔNG có số/năm/nguồn | soft-ratchet | check_content_gates |
| R10.10 | Đơn-vị-HC-cũ (huyện/thị xã X) trong giọng biên tập — freeze-forward, sweep sau | soft-ratchet | check_content_gates |

(R50.5 = tên tỉnh §1.6 đã hợp nhất vào R10.7/check_tinh_cu — không dùng số riêng.)

## Ngoại lệ đã duyệt
- **R50.6** checklist khi viết content mới — *chủ dự án duyệt (2026-07-07).*
- **R50.2**: "miền Tây" trong DATA là văn-nói hợp lệ ở một số ngữ cảnh (vd "dân miền Tây gọi...") — xử CÓ NGỮ CẢNH ở SP6, ratchet chặn TĂNG từ hôm nay.
