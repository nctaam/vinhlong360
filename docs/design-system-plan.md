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

### Bước 2 — Audit & sửa tương phản WCAG ✅ XONG
Audit bằng script tính tỉ lệ WCAG mọi cặp màu. Đã sửa:
- `--muted` (qua primitive `--ink-700`) #6B7B73 → **#586860**: 4.07/4.46 → **5.38/5.89** (đạt 4.5).
- Chữ trắng trên amber-dark (2.16/3.07 — fail) → đổi sang `--ink` ở `.btn-accent:hover`, `.hero-search button:hover`, `.toast.warning` (ink/amber-dark = 4.88 ✓).
- Viền control: thêm token **`--border-input`** (#8F8676 light / #7e7e82 dark, đều ≥3:1 — WCAG 1.4.11) áp cho `.input/.textarea/.select`, `.search-row`, topbar-search, chat input (trước dùng `--line` ~1.2–1.5).
- `:focus-visible` đã có khắp nơi ✓; `.btn` & `.input` đã có `min-height/width: 44px` ✓.
- Build pass. (Divider trang trí `--line`/`--border` giữ nguyên — WCAG miễn non-text cho phần tử trang trí.)

⚠️ **Phát hiện hoãn sang Bước 4:** `--primary` dùng đa vai trò (chữ 46×, nền 15×, viền 18×). Ở dark mode `--primary` (#9C3D22) làm **chữ** trên nền tối chỉ đạt 2.06–2.57 (fail), nhưng lighten token sẽ phá nút nền-terracotta-chữ-trắng. → Cần **tách token foreground/background brand** khi tái cấu trúc dark mode (.dark) ở Bước 4.

### Bước 3 — Self-host font + tối ưu ảnh ✅ XONG
- `@nuxt/fonts`: self-host Inter (subset vietnamese/latin/latin-ext, weights 400/600/700/800); bỏ `<link>` Google Fonts CDN + preconnect. Build → 0 ref googleapis/gstatic, 6 woff2 trong `_fonts/`.
- `@nuxt/image`: provider **`weserv`** (miễn phí, transcode WebP OFF-VPS) thay vì IPX — **VPS 1GB/1CPU không kham transcode remote-image server-side** (cùng lý do đã tắt BUILD_SEARCH_INDEXES). EntityCard `<img>`→`<NuxtImg>` có guard (chỉ URL tuyệt đối; tương đối giữ `<img>`).
- *Không* thêm display font thứ 2 (Inter có dấu Việt tốt; 1 font = nhẹ hơn).

### Bước 4 — Dark mode toggle + tách brand fg/bg ✅ XONG
- `@nuxtjs/color-mode` (classSuffix '', preference system, fallback light); nút toggle 🌙/☀️ ở header (ClientOnly, 44px). Dark token: `@media`→ selector `.dark` (system vẫn auto).
- Tách brand fg: `--primary-fg/-fg-strong/--secondary-fg/--tertiary-fg`. Light = base (0 đổi pixel); dark lighten (≥4.5:1 trên card tối) — fix dark-mode brand-as-text từ Bước 2. Nút nền brand giữ `--primary` đậm + chữ trắng.
- Dark surfaces: 35 `#fff`→`var(--card)` (light bất biến); topbar/journey-bar/save-btn → `--surface-translucent`; overlay-trên-ảnh giữ nguyên.

### Bước 5 — JSON-LD Schema.org (GEO) ✅ XONG (đã có sẵn + bổ sung)
Codebase **đã có JSON-LD đầy đủ** (17 trang): WebSite+SearchAction, Organization+areaServed (3 tỉnh)+logo, entity theo type (TouristAttraction/Product/LodgingBusiness/LocalBusiness…)+address+geo+Offer+citation, TouristTrip (lịch trình), BreadcrumbList. Bổ sung lỗ hổng duy nhất: `inLanguage: 'vi-VN'` cho WebSite/Organization/entity.

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

## 4b. Pattern BỐ CỤC/IA học từ thế giới (deep-research 2026-06-14, 25/25 claim verify 3-0)

> Nguồn chính: NN/g (mega-menu, menu-design, illusion-of-completeness), Baymard (navigation, split-view, applied-filters, product-page, avoid-horizontal-tabs), Visit California, michi-no-eki.com. Caveat: phần lớn Baymard từ e-commerce → pattern *bố cục* chuyển sạch, khung *bán hàng* KHÔNG áp (showcase-only §1.4).

1. **IA theo intent + region-first.** Tổ chức nav theo *ý định/hoạt động* (Nơi đến / Trải nghiệm / Cảm hứng / Cung đường) + *vùng trước* (3 tỉnh → huyện/xã → điểm), KHÔNG list điểm phẳng. Desktop hiện nav trực tiếp (mega-menu cho phân cấp sâu), hamburger CHỈ mobile, submenu **click-not-hover**, mỗi cấp ≤~10 mục, nhóm quan trọng góc trên-trái, label mang thông tin.
2. **Trang chủ = hub xếp tầng** (Visit California): 3 card vùng tĩnh (VL chỉ 3 tỉnh nên KHÔNG cần carousel) + section theo chủ đề/mùa/bài viết. SSR tĩnh hợp Nuxt.
3. **Chống "illusion of completeness"** (NN/g): hero KHÔNG lấp kín viewport, cho section kế *peek* trên fold + scroll cue; tránh đường kẻ ngang full-width + khoảng trắng quá lớn (báo hiệu "hết trang"). Quan trọng cho trang chi tiết nơi giờ/giá/liên hệ/map hay nằm dưới fold.
4. **Listing**: hiện **chip "filter đang áp"** (72% site chuẩn có; thiếu → khó gỡ, mobile phải mở lại panel). Catalog mỏng của VL → **đi thẳng tới listing**, tránh intermediary page. Có toạ độ → cân nhắc split-view list+map (desktop), mobile = **tab/toggle list↔map** (đừng nhúng map cướp scroll).
5. **Trang chi tiết**: dùng **one-long-page + sticky TOC** hoặc **collapsed sections** — **TRÁNH horizontal tabs** (27% user bỏ sót nội dung). Surface khối **"Highlights" quét nhanh** (giờ/giá/liên hệ Zalo/địa chỉ/map) — 78% site KHÔNG có. Gallery ~7 loại ảnh + nav + zoom (tap/double-tap mobile).
6. **OCOP showcase = michi-no-eki**: trình bày tường thuật ("Đặc sản nổi bật"), KHÔNG cart/giá/nút mua; nhúng trong nội dung biên tập điểm; nhấn farm-to-table + đặc sản có tên. (Đúng §1.4.)
7. **Danh bạ/directory = taxonomy kép**: duyệt theo địa lý (vùng→tỉnh, map tỉnh clickable) SONG SONG lọc faceted theo thuộc tính/tiện ích (loại, hạng OCOP, dịch vụ). Route theo tỉnh + facet query params (Nuxt SSR).

**Câu hỏi mở (chưa đủ nguồn):** tích hợp UGC/cộng đồng vào trang chi tiết (Atlas Obscura/Culture Trip — claim không verify được); layout danh bạ *hành chính* (civic) khác directory sản phẩm thế nào.

## 5. Quyết định đã chốt (để các phiên sau không đề xuất lại)
- **Giữ CSS thuần + tokens biến CSS.** KHÔNG Tailwind, KHÔNG Style Dictionary.
- **Giữ hệ màu hiện tại** (terracotta–amber–green–teal / cream). Chỉ hệ thống hóa, không đổi hue.
- **Tránh trắng-lạnh diện rộng** (ngữ nghĩa tang trong văn hóa Việt).
