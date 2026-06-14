# Kế hoạch Hệ thống Thiết kế (Design System) — vinhlong360.vn

> Tài liệu nguồn-sự-thật cho việc thiết kế giao diện. Tổng hợp từ nghiên cứu (deep-research 2026-06-14 + nghiên cứu nền bổ sung) và áp dụng thực dụng cho stack **Nuxt 4 SSR + CSS thuần + ngân sách thấp + solo dev**.
> Triển khai theo §B2 (additive-first) và §3/§6 CLAUDE.md. Mỗi bước để hệ thống vẫn chạy được.

---

## 0. Nguyên tắc định hướng (4 ưu tiên ngang nhau)

1. **Hiệu năng & SEO/GEO** — CWV: LCP ≤2.5s · INP ≤200ms · CLS ≤0.1 (đạt khi 75% lượt truy cập tốt). SSR + self-host font + ảnh WebP/AVIF + JSON-LD.
2. **Khả năng tiếp cận (WCAG 2.2 AA)** — tương phản 4.5:1 (chữ) / 3:1 (chữ lớn & UI); vùng chạm ≥24px (khuyến nghị 44px); không dựa mỗi màu để truyền nghĩa.
3. **Bản sắc địa phương** — màu lấy từ cảnh quan Tây Nam Bộ (gạch nung, dừa, phù sa) + tôn trọng biểu tượng màu văn hóa Việt.
4. **Chi phí thấp & dễ bảo trì** — **giữ CSS thuần + tokens biến CSS** (KHÔNG migrate Tailwind — chi phí chuyển đổi > lợi ích ở quy mô này; Nuxt 4 hỗ trợ cả hai nhưng dự án đã có hệ CSS chạy tốt). Dự án nhỏ: cấu hình biến CSS thủ công là đủ, không cần Style Dictionary.

---

## 1. Nền lý thuyết (cơ sở để quyết định, có dẫn nguồn)

### Tri giác / Gestalt — não gom nhóm trước khi "đọc"
- **Proximity:** khoảng cách gom nhóm mạnh hơn đường kẻ → ưu tiên khoảng trắng.
- **Similarity:** cùng style = cùng loại (badge OCOP/mùa phải đồng bộ).
- **Closure / Continuity / Figure–ground:** ảnh entity là "figure" rõ trên nền cream.
- **Visual hierarchy** = tương phản: phần tử tương phản cao nhất được thấy trước.

### 10 Heuristic của Nielsen (NN/g) — checklist review mỗi trang
1. Visibility of system status — phản hồi loading/toast rõ.
2. Match real world — ngôn ngữ người dùng ("Đặc sản theo mùa").
3. User control & freedom — nút hủy/quay lại, thoát modal dễ.
4. **Consistency & standards** — trụ của design system.
5. Error prevention — chặn lỗi từ gốc.
6. Recognition not recall — hiện lựa chọn, đừng bắt nhớ.
7. Flexibility & efficiency — shortcut ẩn cho người rành.
8. Aesthetic & minimalist — bỏ thông tin thừa.
9. Recognize/recover errors — lỗi nói tiếng người + gợi ý sửa.
10. Help & documentation — tốt nhất không cần đọc vẫn dùng được.

### Luật UX định lượng (lawsofux.com)
- **Jakob's Law:** theo quy ước site quen → đừng sáng tạo lại menu/search/giỏ.
- **Hick's Law:** ít lựa chọn → quyết định nhanh (menu/filter ngắn, gom nhóm).
- **Fitts's Law:** nút lớn, gần ngón cái trên mobile.
- **Miller's Law (7±2):** chia nhỏ, gom thông tin.
- **Von Restorff:** chỉ 1 CTA nổi bật mỗi màn.
- **Serial Position:** mục quan trọng đặt đầu/cuối nav.
- **Aesthetic-Usability Effect:** đẹp → cảm nhận dễ dùng hơn (ROI niềm tin).
- **Tesler's Law:** hệ thống gánh phức tạp thay người dùng (tự suy vùng từ địa chỉ).
- **Doherty Threshold (<400ms):** gắn với mục tiêu INP ≤200ms.

### Màu sắc
- **60–30–10:** 60% nền chủ đạo · 30% màu phụ thương hiệu · 10% nhấn/CTA.
- **NN/g:** giới hạn ~3 màu; nhất quán ngữ nghĩa (1 màu CTA dùng khắp nơi); không dựa mỗi màu (mù màu); ý nghĩa màu thay đổi theo văn hóa.
- **Biểu tượng màu văn hóa Việt** (định hướng, nguồn secondary):
  - Đỏ = may mắn/lễ hội/Tết · Vàng-gold = thịnh vượng/cao quý · Xanh lá = sinh trưởng/thiên nhiên · Teal = bình yên/sông nước · Nâu/đất = mộc mạc/nền tảng.
  - ⚠️ **Trắng** vừa tinh khôi vừa **tang tóc** → tránh trắng-lạnh diện rộng (nền cream ấm an toàn hơn). ⚠️ **Tím** dùng hạn chế.
  - → Bảng màu hiện tại (terracotta–amber–green–teal / nền cream) **khớp** cả hài hòa lẫn văn hóa. Giữ nguyên hệ màu.

### Quy ước & con số chốt
- Lưới 8pt, spacing bội số 4/8px.
- Tương phản WCAG AA: 4.5:1 chữ / 3:1 chữ lớn & UI (✅ verified WebAIM).
- Vùng chạm ≥24×24px (WCAG 2.5.8), khuyến nghị 44×44px mobile.

**Nguồn:** NN/g (10 Heuristics, Color), lawsofux.com, Wikipedia (Gestalt, Miller), UX Planet (60-30-10), WebAIM (contrast — verified 3-0), Nuxt docs (styling — verified 3-0), nuxtseo.com (CWV), masteringnuxt.com (@nuxt/image, @nuxt/fonts), penpot.app (token tiers), VinWonders (màu văn hóa Việt).

---

## 2. Hiện trạng (điểm khởi đầu — additive, không đập đi)

**Đã có:** biến CSS có cấu trúc (`web-nuxt/assets/css/variables.css`), bảng màu 3 vùng, dark mode `prefers-color-scheme`, token radius/shadow/z/duration, gradient theo category, security headers, compress, cache `_nuxt`.

**Thiếu:** tokens phẳng 1 tầng (trộn primitive lẫn semantic); chưa có thang typography & spacing chính thức; font Inter qua Google CDN (chưa self-host); chưa kiểm tương phản WCAG; dark mode không có nút bật/tắt; chưa có JSON-LD (mất điểm GEO).

---

## 3. Kế hoạch 5 bước (additive, ~3.5 buổi)

### Bước 1 — Hệ thống hóa tokens (rủi ro thấp) ⬅️ ĐANG LÀM
Tách `variables.css` thành 3 tầng, **giữ alias cũ** (`--primary`...) để không vỡ component:
- Primitive: thang màu đặt tên theo vùng (`--clay-*`, `--amber-*`, `--leaf-*`, `--river-*`, `--sand-*`).
- Semantic: `--color-primary: var(--clay-600)`, `--surface`, `--text`, `--text-muted`...
- Bổ sung **typography scale** (`--text-xs…3xl` + line-height) và **spacing scale** (`--space-1…16`, thang 4px / lưới 8pt).
- Tiêu chí: build Nuxt pass, giao diện không đổi pixel (alias resolve ra đúng hex cũ).

### Bước 2 — Audit & sửa tương phản WCAG (0.5 buổi)
Kiểm `--muted`, `--border`, badge, focus-ring trên light/dark; nâng màu <4.5:1 (chữ) / <3:1 (UI). `:focus-visible` rõ. Min target 44px cho nav/nút.

### Bước 3 — Self-host font + tối ưu ảnh (lợi ích CWV lớn nhất)
- `@nuxt/fonts`: bỏ `<link>` Google Fonts, self-host Inter (subset `vietnamese`); cân nhắc 1 display font có dấu đẹp cho heading (Be Vietnam Pro), giữ Inter cho body.
- `@nuxt/image`: ảnh entity → `<NuxtImg>` WebP/AVIF, hero `priority`, dưới fold `lazy`.

### Bước 4 — Dark mode có nút bật/tắt (0.5 buổi)
`@nuxtjs/color-mode`; chuyển dark token sang selector `.dark` (giữ media query làm mặc định); nút toggle ở header; không đổi markup component.

### Bước 5 — JSON-LD cho GEO (đòn bẩy GEO=SEO)
Schema.org JSON-LD theo loại: `TouristAttraction`, `LocalBusiness`, `Product` (OCOP), `TouristTrip` (lịch trình), `BreadcrumbList`. Render SSR qua `useHead`.

---

## 4. Checklist review mỗi trang (áp dụng từ Bước 2)
- [ ] Tỉ lệ màu 60-30-10; **chỉ 1 CTA nổi** mỗi màn (Von Restorff).
- [ ] Spacing theo thang 4/8px; gom nhóm bằng khoảng trắng (proximity).
- [ ] Tương phản ≥4.5:1 (chữ), ≥3:1 (chữ lớn & UI); không dựa mỗi màu.
- [ ] Vùng chạm ≥44px; nút chính to & dễ với (Fitts).
- [ ] Menu/filter ≤7 nhóm (Hick/Miller).
- [ ] Theo quy ước quen (Jakob): logo→home, search header, liên hệ footer.
- [ ] `:focus-visible` rõ; thao tác có phản hồi <400ms (Doherty).

---

## 5. Quyết định đã chốt (để các phiên sau không đề xuất lại)
- **Giữ CSS thuần + tokens biến CSS.** KHÔNG Tailwind, KHÔNG Style Dictionary.
- **Giữ hệ màu hiện tại** (terracotta–amber–green–teal / cream). Chỉ hệ thống hóa, không đổi hue.
- **Tránh trắng-lạnh diện rộng** (ngữ nghĩa tang trong văn hóa Việt).
