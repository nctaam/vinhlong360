# Re-audit đa-chiều toàn bộ trang — Báo cáo (2026-07-04)

**Cách chạy:** 10 agent, mỗi agent 1 chiều quét toàn bộ 67 trang (`web-nuxt/pages/`), findings có bằng chứng file:line, P0/P1 orchestrator adversarial-verify. Rubric: `docs/superpowers/specs/2026-07-04-page-reevaluation-design.md`.

## Scorecard (trung bình ≈ **8.6/10**)

| Chiều | Điểm | Tóm tắt |
|-------|------|---------|
| D3 Accessibility (WCAG 2.2) | **9.4** | Xuất sắc: skip-link/landmark, focus-trap tập trung, combobox ARIA-1.2, 0 img thiếu alt. Agent tự loại 3 false-positive. |
| D2 Interaction | 9.1 | focus-visible phổ quát, `prefers-reduced-motion` 80+ file, optimistic-UI có rollback. |
| D7 Content & copy | 8.9 | **CTA chỉ liên hệ — 0 booking/thanh toán** (ràng buộc §1.4 OK); copy VN chất lượng cao. |
| D9 States | 8.9 (public) | SSR silent-empty **kiến trúc đã loại bỏ** (apiFetch); state-trio nhất quán. Admin: 2 gap error-banner. |
| D4 Responsive & mobile | 8.7 | touch-target 44px global, chống iOS-zoom, mobile nav đủ, bảng admin overflow-scroll. |
| D8 SEO & metadata | 8.7 | 62/68 trang có useSeoMeta+canonical, JSON-LD giàu đúng @type, admin noindex. |
| D10 IA & navigation | 8.7 | breadcrumb 32/37, cross-link giàu, nav parity mobile, 0 orphan thật. |
| D5 Performance & CWV | 8.4 | SSR-fetch discipline, image CWV gần hoàn hảo, CSS route-split, maplibre lazy. |
| D1 Visual & hierarchy | 7.9 | Token foundation mạnh; drift type-scale + token `--danger`. |
| **D6 Consistency** | **7.4** | Thấp nhất: token ma `--danger`, 116 fallback token cũ ở admin, dark-parity 1 chỗ. |

**Kết luận:** xác nhận kết luận audit cũ — UI beyond-world-class (~8.6). Không có P0. Findings hầu hết P2/P3 polish; **P1 thật rất ít**.

## Findings đã verify

### P1 (sửa ngay)
- **P1-a `--danger` token không tồn tại** [D1+D6, CONFIRMED]. Grep `--danger:` trong `assets/css/` = rỗng (chỉ có `--error` + `--danger-rgb`). Bare `var(--danger)` ở `admin/ai.vue:80,94,149,379` render màu inherit (mis-render); `var(--danger, #c0392b)` ở `cai-dat`/`tai-khoan`/`dia-diem/index` luôn rơi fallback lệch brand + không dark-variant. **Fix:** thêm `--danger: var(--error)` vào block light + dark → sửa mọi use cùng lúc.
- **P1-b `dia-diem/[id].vue:1169` `.trust-status.aging` mất dark-parity** [D6, CONFIRMED]. Hardcode amber `#8a5b00`/`rgba(245,158,11,…)`, KHÔNG có `.dark` override (siblings `.fresh`/`.stale` dùng token auto-adapt). Dark mode = chữ nâu trên nền gần vô hình. **Fix:** dùng `var(--warning)`/`--warning-bg`/`--warning-border` (đã có light+dark).

### P2 (backlog — nhiều cái đáng làm)
- **Catalog un-paginated** [D5]: `du-lich`/`theo-mua`/`kham-pha/[interest]` fetch `limit=500` render ~600 EntityCard 1 lần; `san-pham`/`ocop` limit=200. Hydration/INP nặng. Fix: `visibleCount`+"Xem thêm" hoặc load-more (pattern có sẵn ở `dia-diem/index.vue`).
- **Admin nuốt lỗi** [D9]: `admin/nhat-ky.vue:98` + `admin/media.vue:134` `catch{ showToast }` không set `loadError`/retry banner → load fail trông như "no data". Admin-only. Fix: thêm loadError + banner retry (pattern `kiem-duyet.vue`).
- **Security-tab double-submit** [D2]: `cai-dat.vue` nút begin/confirm/disable2FA, revokeSession, unblock/unmute, removeTrustedDevice + `cong-dong` cancelScheduled thiếu `:disabled` khi await.
- **116 fallback token cũ ở admin** [D6]: `var(--primary,#219653/#0071e3)`, `var(--accent,#f5c518)` — dormant nhưng latent brand-break. Fix: bỏ fallback (bulk find/replace).
- **`/huong-dan` không có trong main nav** [D10]: chỉ 1 link footer; beta lấy giáo dục làm nút thắt. Fix: thêm vào nav group/UserMenu.
- **UGC noindex** [D8, CẦN CHỦ QUYẾT]: `bai-viet/[id]`/`nguoi-dung/[id]`/`lich-trinh-chia-se/[id]` `noindex` — bỏ organic reach. Đánh đổi privacy/thin-content; cân nhắc index có điều kiện.
- **Hardcoded status color** [D6]: `admin/entities` category badge, `index` decision-icon bg, `admin/nhat-ky` method badge — dùng rgb thô thay `--*-rgb` token.
- **data-quality không skeleton loading**, **ai.vue thiếu subsection empty-state** [D9-admin].

### P3 (backlog polish)
- Type-scale drift (~510 rem off-scale, tập trung user-system+admin) [D1]; kicker/eyebrow reimplement; off-grid rem spacing [D6].
- Catalog dùng chung `og-default.jpg`; thiếu `og:image:alt` [D8].
- admin dark-toggle thiếu `aria-label`; PhotoGallery dot `aria-hidden-focus`; entities `<th>` thiếu `aria-sort` [D3].
- `dia-diem/[id]`+`lich-trinh/[id]` ném mọi lỗi SSR thành 404 (mislabel); cong-dong thiếu skeleton lần-đầu [D9].
- ItineraryCard raw `<img>` thay `<NuxtImg>` [D5]; luu-tru "Lời khuyên đặt phòng" heading [D7].
- admin cai-dat breadcrumb gộp nhãn cha [D10].

## Fix log
(cập nhật khi sửa)
