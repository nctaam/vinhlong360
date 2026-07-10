# Implementation Specs — Tổng hợp từ nghiên cứu
> STATUS (2026-07-10): active — tổng hợp spec từ nghiên cứu, tham chiếu.


> **File này tổng hợp các specs HÀNH ĐỘNG từ 3 tài liệu nghiên cứu gốc.**
> Sessions đọc file này để biết CẦN LÀM GÌ. Đọc file gốc chỉ khi cần hiểu sâu hơn.
>
> Nguồn gốc:
> - `design-guidelines-apple-google-figma.md` (1384 dòng) — Apple HIG + M3 + Figma specs
> - `design-research-2026-06-27.md` (1033 dòng) — Gap analysis vs Apple/M3/WCAG
> - `travel-platform-ux-research.md` (904 dòng) — UX 5 nền tảng du lịch

---

## A. FRONTEND SPECS

### A1. Component Specs (từ travel-platform-ux-research §9)

#### EntityCard
- Image `aspect-ratio: 3/2`, border-radius 12px
- Badge: absolute top 8px left 8px, font 11-12px weight 600
- Save button: absolute top 8px right 8px
- Title: weight 600, 2-line clamp (`-webkit-line-clamp: 2`)
- Hover: `scale(1.03)` transition 300ms
- CTA: Zalo + Phone inline (KHÔNG booking button)

#### PhotoGallery
- CSS Grid: `grid-template-columns: 3fr 2fr`, `grid-template-rows: 1fr 1fr`
- Main image spans 2 rows, gap 4px
- "Xem X ảnh" button: absolute bottom 12px right 12px
- Mobile < 768px: single carousel với dots + swipe

#### FilterChips
- Flex row, gap 8px, `overflow-x: auto`, `scroll-snap-type: x mandatory`
- Hide scrollbar (`::-webkit-scrollbar { display: none }`)
- Chip: height 36px, padding 0 16px, border-radius 18px, border 1px solid, weight 500
- Active: `var(--surface-inverse)` bg, transparent border
- Transition: 150ms trên bg/color/border

#### ContactWidget (thay BookingWidget)
- Desktop: sticky sidebar width 320px, border-radius 12px, shadow level 3, padding 24px
- CTA buttons: full-width, height 48px, pill radius (999px)
- Mobile: fixed bottom bar 56px height + safe-area padding (`env(safe-area-inset-bottom)`)

#### MapListView
- Desktop: grid `60% list / 40% map`
- Map: sticky, height `calc(100vh - var(--header-h))`
- Mobile < 768px: full-width list + "Bản đồ" toggle FAB
- Leaflet/OpenStreetMap (free). Category icon markers (không price pins)

#### ReviewSection
- 5-star màu gold (`var(--secondary)`)
- Distribution bar chart (5 → 1 star, horizontal bars)
- 4 category ratings grid: Không khí, Chất lượng, Giá trị, Phục vụ
- Mention chips: horizontal scroll
- Sort dropdown

### A2. CSS Variables cần thêm (từ travel-platform-ux-research §9.1)

```css
/* Card */
--card-image-ratio: 3/2;
--card-radius: 12px;
--card-gap: 16px;
--card-badge-font: 0.6875rem; /* 11px */

/* Chips */
--chip-height: 36px;
--chip-radius: 18px;
--chip-active-bg: var(--surface-inverse);

/* Gallery */
--gallery-gap: 4px;
--gallery-main-ratio: 3/2;
--gallery-main-width: 60%;

/* Contact Widget */
--contact-widget-width: 320px;
--contact-cta-height: 48px;
--contact-cta-radius: 999px;

/* Detail Page */
--detail-content-max: 680px;
--detail-sidebar-width: 320px;
--detail-section-gap: 32px;

/* Motion (từ design-guidelines D4) */
--ease-emphasized: cubic-bezier(0.2, 0, 0, 1);
--ease-decelerate: cubic-bezier(0.05, 0.7, 0.1, 1);
--ease-accelerate: cubic-bezier(0.3, 0, 0.8, 0.15);
--duration-short: 150ms;
--duration-medium: 300ms;
--duration-long: 500ms;

/* State layer opacity (M3) */
--state-hover: 0.08;
--state-focus: 0.10;
--state-press: 0.10;
--state-drag: 0.16;
--state-disabled-bg: 0.12;
--state-disabled-fg: 0.38;
```

### A3. Breakpoints (consensus từ 5 platforms)

```css
--bp-sm: 600px;
--bp-md: 768px;
--bp-lg: 1024px;
--bp-xl: 1280px;
--bp-2xl: 1440px;
```

### A4. Gap fixes — Accessibility & Polish (từ design-research §2.2, §12)

| ID | Fix | Chi tiết |
|----|-----|----------|
| DS-FE-13 | Skeleton loading | Thay spinner bằng shimmer 1.5s, `aria-busy="true"` |
| DS-FE-14 | Empty states | Icon 48-64px + title 20px + description + CTA cụ thể |
| DS-FE-15 | Scroll padding | `scroll-padding-top: var(--header-h)` — fix focus bị che sticky header |
| DS-FE-16 | Dark mode links | Re-specify màu link trong dark mode (blue mặc định chỉ 2.23:1 contrast) |
| DS-FE-17 | iOS zoom | Input `font-size: 16px` minimum — ngăn iOS auto-zoom |
| DS-FE-19 | Error messages | 3 tín hiệu: red outline + text + icon, `aria-invalid="true"` |
| DS-FE-20 | Touch targets | Tất cả targets >= 24x24 CSS px (WCAG 2.5.8) |
| DS-FE-1 | High contrast | `@media (prefers-contrast: more)` support |

### A5. Performance (từ design-research §15-16)

| ID | Fix | Chi tiết |
|----|-----|----------|
| R3-FE-1 | Contain | `contain: content` trên cards, `content-visibility: auto` trên list items |
| R3-FE-2 | Hero image | `fetchpriority="high"`, responsive `srcset/sizes`, KHÔNG `loading="lazy"` above fold |
| R3-FE-4 | Image format | `<NuxtPicture>` với AVIF→WebP→JPEG fallback. WebP q75 |
| R3-FE-9 | Animation | Enter 150ms decelerate, exit 100ms accelerate. Box-shadow qua `::after` opacity |

### A6. Pattern Library (từ travel-platform-ux-research §8)

**ADOPT (áp dụng nguyên):**
1. ~~Content-first homepage (không hero banner lớn)~~ **[OVERRIDE 2026-07-07: hero masthead cinematic là signature đã duyệt + deploy — không quay lại content-first/carousel]**
2. Asymmetric photo gallery (1 lớn + 4 nhỏ)
3. Horizontal filter chips (pill-shaped, sticky)
4. Detail page section order: media→title→facts→desc→amenities→map→reviews→similar→sticky CTA
5. Star rating 1-5 + count (quen thuộc nhất)
6. Responsive breakpoints 600/768/1024/1280/1440px
7. Scroll-reveal entrance animation
8. Card hover lift + shadow transition

**ADAPT (chỉnh cho vinhlong360):**
1. ContactWidget thay BookingWidget → CTA Zalo/Phone
2. Category icon map pins thay price pins
3. Community trust signals thay guest/host badges
4. 60:40 list:map split (ưu tiên list vì không có giá)
5. Leaflet/OpenStreetMap thay Google Maps (free)

**SKIP (không làm):**
- Split-panel filter sidebar, Dynamic pricing display, Verified badges, Instant booking flow
- Host/Superhost system, Experience categories, Wishlist sharing, Calendar availability
- Payment integration, Multi-currency, Trust & safety badges

---

## B. BACKEND SPECS

### B1. Structured Data / JSON-LD (từ design-research §21)

| Schema | Required fields |
|--------|----------------|
| `TouristAttraction` nested `LocalBusiness` | name, address (PostalAddress), telephone, url, geo, openingHoursSpecification, image (>=50000px, 3 ratios: 16:9/4:3/1:1) |
| `BreadcrumbList` | Trên tất cả trang |
| `Organization` | Homepage, `sameAs` [Zalo, Facebook], `logo` >=112x112px, `areaServed` |
| `AggregateRating` + `Review` | `author.name`, `itemReviewed.name`, `reviewRating.ratingValue` (decimal dot, không comma) |
| `Article`/`BlogPosting` | Community posts, `image` >=696px wide, `headline` <110 chars |

### B2. SEO Vietnamese (từ design-research §21.8)

- URL slugs: ASCII only (không dấu). Giữ dấu trong content/titles.
- Schema types ưu tiên cho AI citation (GEO): FAQPage > HowTo > Article+BreadcrumbList > TouristAttraction > LocalBusiness

### B3. Middleware (từ design-research §15)

- `Save-Data` middleware: detect `Save-Data: on` header → return smaller images / skip gallery. Phải set `Vary: Save-Data`

### B4. A11y Backend (từ design-research §2.2)

- OTP input: support paste + `autocomplete="one-time-code"`, `inputmode="numeric"`, KHÔNG `type="number"`
- Chat/Zalo CTA: consistent DOM order across pages (WCAG 3.2.6)
- Map pan/itinerary reorder: phải có click/button alternative cho drag (WCAG 2.5.7)

---

## C. CONTENT SPECS

### C1. Ngôn ngữ (từ design-research §19.7)

- Heading: dùng Hán-Việt (SEO value)
- Body text: dùng thuần Việt
- ~~Câu < 15 từ, đoạn 3-4 câu max~~ **[OVERRIDE 2026-07-07: nhịp câu ĐA DẠNG (ngắn xen dài) — trần cứng 15-từ công thức hoá văn, ngược mục tiêu chống đọc-như-AI]**
- Thay: tham quan→đi xem, ẩm thực→đồ ăn, lưu trú→nơi ở, giao thông→đi lại

### C2. Cognitive Accessibility (từ design-research §19.2-19.6)

- ADHD: chunked content < 1 ý/section
- Dyslexia: 16px+, line-height 1.5+, max-width 70ch, letter-spacing 0.05em, left-align only
- Autism: consistent layout, explicit labels, no idioms
- 60+: body 18-20px, contrast AAA 7:1, touch 20mm, persistent breadcrumbs, no infinite scroll

### C3. Content Quality Rules

- Tất cả entity phải có: name, summary (>50 chars), description (>100 chars), type, area
- Ảnh: CHỈ AI-generated (cx/gpt-5.5-image) — KHÔNG stock/UGC/Wikimedia
- Phone: format 0xxx.xxx.xxx hoặc +84
- Season: dùng month range "1-12" hoặc "all"
- Coordinates: phải trong bounding box 3 tỉnh (lat 9.6-10.5, lng 105.8-106.8)

---

## D. TÀI LIỆU GỐC (đọc thêm khi cần)

| File | Dòng | Nội dung | Khi nào đọc |
|------|------|----------|-------------|
| `design-guidelines-apple-google-figma.md` | 1384 | Apple HIG values, M3 component specs, Figma patterns | Cần giá trị cụ thể (spacing, color, typography) |
| `design-research-2026-06-27.md` | 1033 | Gap analysis — mọi điểm chưa đạt vs Apple/M3/WCAG | Cần hiểu WHY của một fix |
| `travel-platform-ux-research.md` | 904 | So sánh 5 platforms (GYG/Klook/Google/TA/Airbnb) | Cần context pattern nào platform nào dùng |
| `research/` (thư mục) | 1260 | Nghiên cứu văn hóa-du lịch 3 tỉnh (BVL corpus, 6 tầng, 12 chiều) | Cần enrichment content cho entities |
