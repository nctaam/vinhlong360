# Frontend — Tiêu chuẩn vinhlong360
> **STATUS (2026-07-07): active — bản 1.0 (SP0).**

## Mốc tham chiếu
Vue Style Guide · WCAG 2.2 AA · design system đã chốt (CSS thuần + tokens, KHÔNG Tailwind) · IconLine.vue (~37 icon).

## Quy tắc
| Rule | Phát biểu | Tầng | Cách đo |
|---|---|---|---|
| R30.1 | CSS thuần + tokens — CẤM Tailwind (mọi dạng) | hard | check_banned_claims (no_tailwind) |
| R30.2 | Emoji chức năng mới → IconLine; emoji string-context (SEO/map/option) tồn kho qua baseline | soft-ratchet | check_fe_tokens (fe_emoji) |
| R30.3 | Màu hex/rgb trong .vue = nợ — dùng var(--*) từ tokens.css | hard-ratchet | check_fe_tokens (fe_colors) |
| R30.4 | Nội dung volatile (community/personalization) phải ClientOnly (chống hydration-mismatch) | checklist-ký* | review khi thêm section |
| R30.5 | Tap-target ≥44px | checklist-ký* + ngoại lệ dưới | preview_eval khi sửa control |
| R30.6 | axe-core 0 violation serious+ trên 14 trang sweep | hard-ratchet (SP4 XONG) | check_axe (đọc axe-report.json, graceful-skip nếu chưa scan; enforce CI) |
| R30.7 | Bundle budget: chunk-max ≤ baseline & đích entry ≤200kB gz | soft-ratchet (SP4 XONG) | check_bundle (parse .output/_nuxt, so bundle-budget.json) |

## Ngoại lệ đã duyệt
- **R30.5 season-ring theo-mua**: 12 notch 22px trên vòng 76px mobile — hình học không cho phép 44px không-chồng-lấn (đo thực nghiệm 2026-07-07: 11/12 tap sai khi nới); month-grid là fallback a11y. *Chủ dự án duyệt qua plan declutter đợt 3.*
- **R30.4/R30.5** dạng checklist — *chủ dự án duyệt (2026-07-07).*
