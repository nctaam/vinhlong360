# UI/Design — Tiêu chuẩn vinhlong360
> **STATUS (2026-07-07): active — bản 1.0 (SP0).** design-rulebook.md là NGUỒN đầy đủ; file này chỉ liệt phần GATE ĐƯỢC + ngoại lệ chính danh.

## Mốc tham chiếu
Apple HIG + Material 3 (values đã trích trong design-guidelines) · design-rulebook.md (đã truth-sync) · motif phù-sa (sediment-head/divider/tick).

## Quy tắc
| Rule | Phát biểu | Tầng | Cách đo |
|---|---|---|---|
| R40.1 | Palette = tokens (đồng nhất R30.3) | hard-ratchet | check_fe_tokens |
| R40.2 | Motif phù-sa là bản sắc — không thay/không nhại bằng motif khác khi thêm section | checklist-ký* | review design |
| R40.3 | Microcopy honesty: CẤM claim "đã xác minh"/con số kiểm-chứng khống | hard | check_banned_claims |
| R40.4 | Animation dài/parallax: chỉ signature đã duyệt, bắt buộc prefers-reduced-motion | ngoại lệ dưới | review + rulebook R4.4 |
| R40.5 | Điều hướng chuẩn đã chọn: top-nav + hamburger (không bottom-nav) | ghi nhận | — |

## Ngoại lệ đã duyệt
- **R40.4 hero Ken Burns + parallax homepage**: signature đã duyệt deploy (có reduced-motion). *Chủ dự án duyệt (deploy 07/2026).*
- **R40.2** checklist — *chủ dự án duyệt (2026-07-07).*
