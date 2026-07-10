# Re-audit đa-chiều toàn bộ trang — Design / Rubric
> STATUS (2026-07-10): done — design/audit đã hiện thực & ship.


**Ngày:** 2026-07-04. **Nhánh:** main. **Kiểu:** dimension-led sweep (Approach B).

**Goal:** Đánh giá lại **toàn bộ ~67 trang** Nuxt của vinhlong360, mỗi chiều một agent quét hết trang, cho điểm + findings ưu tiên; rồi **sửa ngay P0/P1** (đã verify), P2/P3 vào backlog.

**Bối cảnh:** Đã qua 3 vòng audit (UI ~8/10, nút thắt = nội dung). Phiên gần nhất ship nhiều FE mới (User System: hồ sơ timeline/achievement/heatmap/XP, ví 2FA, cộng đồng discovery, notifications; AdminCP: media, nhật-ký, entities kind-aware) — nhiều trang chưa qua audit cũ. Ràng buộc dự án: CLAUDE.md (CTA chỉ liên hệ/không booking; chỉ ảnh AI-gen; free-tier; solo dev).

## Phạm vi: 67 trang (`web-nuxt/pages/`)

- **Công khai (~37):** index; catalog (du-lich, san-pham, ocop, luu-tru, le-hoi, su-kien, theo-mua, ban-do, danh-ba, bang-xep-hang, tim-kiem, dia-diem/index, lich-trinh/index); detail (dia-diem/[id], bai-viet/[id], nguoi-dung/[id], lich-trinh/[id], lich-trinh-chia-se/[id], khu-vuc/[area], xa-phuong/[id], kham-pha/[interest]); cong-dong; user (tai-khoan, cai-dat, da-luu, thong-bao); tao-lich-trinh; static/legal (gioi-thieu, huong-dan, huong-dan-thanh-vien, lien-he, chinh-sach-bao-mat, dieu-khoan-su-dung, tuyen-duong); [...slug] (CMS).
- **Admin (~30):** index, ai, bao-cao, chua-phan-loai, danh-ba, data-quality, duyet-anh, duyet-tu-hoc, entities, kiem-duyet, lich-trinh, media, nhat-ky, thong-ke, users; cai-dat/* (14 CMS settings).

## 10 chiều (mỗi chiều = 1 agent sweep)

- **D1 Visual & hierarchy:** typography scale, spacing rhythm, color discipline, contrast visual, above-the-fold, image treatment.
- **D2 Interaction & micro-interaction:** hover/active/focus states, transition, feedback tức thời, optimistic UI, affordance, reduced-motion.
- **D3 Accessibility (WCAG 2.2 AA):** semantic HTML, ARIA đúng, keyboard nav + focus visible, contrast ≥4.5:1, alt text, form label, skip-link, aria-live cho toast/loading.
- **D4 Responsive & mobile:** breakpoint hợp lý, touch target ≥44px, mobile nav/hamburger, KHÔNG horizontal-scroll, thumb-reach, layout mobile riêng khi cần.
- **D5 Performance & CWV:** route-level CSS, lazy + responsive image (srcset/sizes/width-height chống CLS), LCP/CLS/INP risk, hydration, **apiFetch cho SSR-fetch** (không `$fetch` nội bộ — bài học silent-empty), over-fetch/N+1.
- **D6 Design-system consistency:** dùng CSS token (KHÔNG hardcode màu/spacing), reuse component (EntityCard/Badge/Button…), nhất quán button/card/badge/chip, **dark-mode parity**, spacing scale.
- **D7 Content & copy:** tiếng Việt tự nhiên, empty/placeholder có ý nghĩa, microcopy, **CTA = liên hệ Zalo/điện thoại/hỏi-giá (KHÔNG form chốt đơn/booking)**, tone, cờ thin-content.
- **D8 SEO & metadata:** title/meta description/OG/Twitter per trang, JSON-LD/Schema.org đúng loại, canonical, cấu trúc heading (1 h1), internal link, og:image.
- **D9 States (empty/loading/error):** skeleton khi load, empty state hữu ích, error recovery (retry), 404/edge, **SSR-fallback không kẹt** (bài học "Đang cập nhật nội dung").
- **D10 IA & navigation:** nav rõ, breadcrumb, findability, cross-link giữa trang liên quan, orphan page, mạch user-flow, mobile nav.

## Cách mỗi sweep chạy (agent brief)

1. Đọc **nền tảng chung 1 lần** cho lăng kính của mình: `web-nuxt/assets/css/base.css` (tokens), `web-nuxt/layouts/*`, `web-nuxt/app.vue`, và 3-6 component cốt lõi liên quan chiều (vd D6/D1 đọc `components/EntityCard.vue`, `Badge`, nav).
2. **Pattern-scan toàn bộ 67 trang** cho anti-pattern của chiều (grep, vd D6: `#[0-9a-fA-F]{3,6}` hardcode màu; D5: `\$fetch\(['\"]/api`; D3: `<img` thiếu `alt`, `@click` trên `<div>`; D8: thiếu `useSeoMeta`/`useHead`).
3. **Deep-read điểm nóng** + 1 mẫu đại diện mỗi cụm trang (không cần đọc kỹ cả 67).
4. Chấm **mỗi trang 1-10** cho chiều (hoặc "n/a") + liệt findings.

## Định dạng finding (bắt buộc, structured)

Mỗi finding: `{trang (path), chiều, mức (P0|P1|P2|P3), tóm tắt 1 câu, bằng chứng (file:line hoặc pattern), cách sửa gợi ý}`. Mỗi agent trả về: `{dimension, avg_score, per_page_scores, findings[], cross_page_themes[]}`.

**Thang mức:** P0 = hỏng/không dùng được/vi phạm ràng buộc (vd CTA booking, trang kẹt fallback, a11y chặn hoàn toàn keyboard). P1 = lỗi rõ ảnh hưởng nhiều user/nhiều trang. P2 = cải thiện đáng kể. P3 = nice-to-have.

## Xác minh (chống false-positive)

Mọi finding **P0/P1 phải được orchestrator adversarial-verify** (tái hiện trên code sống / render) mới vào danh sách sửa. Phiên này đã chứng minh "findings" từ agent có thể brittle/sai — KHÔNG sửa mù theo report.

## Tổng hợp → báo cáo

`docs/audit/2026-07-04-page-reaudit.md`: scorecard 10 chiều (X/10) + heat-map per-trang + chủ đề xuyên suốt + danh sách P0/P1/P2/P3 (đã verify). 

## Sửa

- **P0/P1** (đã verify) → **SDD** (implementer + reviewer tươi mỗi fix) hoặc sửa trực tiếp nếu nhỏ; §B1 backup nếu đụng data; `npm run build` + `pytest -q -p no:randomly` sau mỗi nhóm; không phá 6-đỏ PG-env baseline.
- **P2/P3** → backlog trong `docs/ROADMAP.md`.
- **Deploy = quyết định riêng của chủ** (không tự deploy sau audit).

## Render (do orchestrator, ở bước verify)

Agent audit **theo source**. Orchestrator dựng dev server (`preview_start`) + screenshot/inspect để **xác minh các claim visual** (D1-D5, D9) trên trang đại diện — không để 10 agent tranh 1 dev server.

## Nghiệm thu

Báo cáo master có scorecard + findings verified; P0/P1 đã sửa + build/test xanh; P2/P3 vào backlog; không regression (baseline 6-đỏ PG-env giữ nguyên).
