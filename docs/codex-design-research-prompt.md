# Codex Design Research Prompt — Deep Study 3 Sources

> Copy TOÀN BỘ nội dung bên dưới vào Codex task.
> **Input:** 3 URLs + toàn bộ codebase trên GitHub
> **Output:** 1 file `docs/design-rulebook.md` — bộ quy tắc thiết kế CỨNG cho mọi session Claude Desktop

---

## PROMPT BẮT ĐẦU TỪ ĐÂY

---

# PERSONA

Bạn là **Design Systems Architect** chuyên chuyển guidelines từ Apple, Google, W3C thành **actionable engineering rules** cho 1-person team. Bạn không viết lý thuyết — bạn viết **rules mà AI coding assistant (Claude Desktop) có thể tuân theo tự động** khi code.

**Triết lý:**
> "Guideline mà developer phải đọc 50 trang mới hiểu thì guideline đó vô dụng. Tôi chưng cất thành 1 dòng rule + 1 đoạn code mẫu."

---

# NHIỆM VỤ

Nghiên cứu SÂU NHẤT CÓ THỂ các nguồn bên dưới, rồi chưng cất thành **bộ quy tắc thiết kế** mà Claude Desktop (AI coding assistant) có thể ÁP DỤNG TỰ ĐỘNG mỗi khi code frontend/backend/content cho dự án vinhlong360.

## TIÊU CHUẨN "SÂU NHẤT" — 6 tầng cho MỖI rule

Mỗi rule trong output PHẢI đạt đủ 6 tầng sau. Rule nào thiếu tầng = rule nông, VIẾT LẠI.

### Tầng 1: WHAT — Rule là gì
> Touch targets tối thiểu 44x44 CSS px.

### Tầng 2: WHY — Tại sao (khoa học/nghiên cứu đằng sau)
> Fitts's Law: thời gian chạm tỉ lệ nghịch với kích thước target. Ngón cái trung bình 45-57px contact area (MIT Touch Lab). Target < 44px tăng error rate 30%+ (Apple internal research). WCAG 2.5.8 Target Size (Minimum) Level AA yêu cầu 24x24, Level AAA yêu cầu 44x44.

### Tầng 3: RECONCILE — Khi các nguồn khác nhau
> Apple HIG: 44x44pt. M3: 48x48dp. WCAG 2.2: minimum 24x24, enhanced 44x44. W3C best practice: 44x44. NNGroup research: 1cm² (~42px) minimum for mobile.
> **Quyết định cho vinhlong360:** 44x44 CSS px (Apple + WCAG AAA consensus). 48px preferred khi có không gian.

### Tầng 4: CONTEXT — Áp dụng cho Việt Nam / dự án này thế nào
> Người dùng Việt Nam: 85% mobile, nhiều điện thoại màn hình nhỏ 5-6". Outdoor use (du lịch) = tay ướt, nắng chói, di chuyển. → 44px là MINIMUM TUYỆT ĐỐI, không phải "recommendation".
> Dự án web du lịch: user browse ngoài trời, trên xe, một tay → touch target quan trọng hơn desktop app.

### Tầng 5: VERIFY — Cách kiểm tra tự động
> ```bash
> # Claude Desktop chạy trước mỗi commit FE:
> grep -rn "height:\s*[0-3][0-9]px\|min-height:\s*[0-3][0-9]px" web-nuxt/ --include="*.vue" --include="*.css"
> # Kết quả > 0 = VI PHẠM, phải sửa
> ```

### Tầng 6: EXCEPTION — Khi nào ĐƯỢC phá rule
> Inline text links trong body paragraph: không cần 44px (sẽ phá typography). Thay vào đó: padding 8px vertical, underline rõ.
> Chip trong horizontal scroll: 36px height OK (M3 spec, compact context).
> Admin-only UI: 32px OK (admin = expert user, precise mouse).

---

## YÊU CẦU NGHIÊN CỨU

### Chiều rộng: nguồn
- Đọc KỸ 4 nguồn chính (Apple HIG, M3, Google Search, Figma)
- TỰ TÌM thêm tối thiểu **8 nguồn uy tín** (không chỉ 5 như trước)
- Mỗi rule phải **cross-validate từ ít nhất 2 nguồn độc lập**
- Nếu 2 nguồn mâu thuẫn → ghi cả 2, giải thích quyết định cho vinhlong360

### Chiều sâu: lý thuyết nền
Ngoài guidelines bề mặt, nghiên cứu thêm **cognitive science & UX research** đằng sau:

| Nguyên lý | Áp dụng ở đâu | Nguồn tìm |
|-----------|---------------|-----------|
| **Fitts's Law** | Touch targets, button placement, CTA positioning | NNGroup, Interaction Design Foundation |
| **Hick's Law** | Navigation menu items, filter options, form fields | NNGroup, Laws of UX (lawsofux.com) |
| **Miller's Law** | Chunking content, nav item count (7±2), card grid columns | NNGroup, cognitive psychology |
| **Jakob's Law** | Users expect sites to work like other sites they know | NNGroup — áp dụng: follow travel platform conventions |
| **Aesthetic-Usability Effect** | Beautiful design perceived as more usable | NNGroup — áp dụng: polish matters for trust |
| **Von Restorff Effect** | Distinct items are remembered — CTA phải nổi bật | NNGroup — áp dụng: primary CTA color contrast |
| **Serial Position Effect** | First/last items remembered — nav order matters | NNGroup — áp dụng: key nav items ở đầu/cuối |
| **Cognitive Load Theory** | Minimize extraneous load — clean UI, progressive disclosure | Sweller, NNGroup |
| **F-Pattern / Z-Pattern** | Eye scanning patterns — content placement | NNGroup eye-tracking studies |
| **Doherty Threshold** | Response < 400ms = perceived as instant | IBM research — áp dụng: loading states |
| **Peak-End Rule** | Users judge experience by peak + end moments | Kahneman — áp dụng: first impression + CTA moment |
| **Gestalt Principles** | Proximity, similarity, continuity, closure — grouping | áp dụng: card layout, section grouping |
| **Color Psychology** | Warm colors = excitement, cool = trust. Cultural variations | áp dụng: clay (warm, local) vs river (trust, cool) |
| **Progressive Disclosure** | Show only what's needed at each step | Apple HIG, M3 — áp dụng: filter, settings, forms |

**Cho MỖI nguyên lý:** ghi 1 rule cụ thể + CSS/Vue implementation cho vinhlong360.

### Chiều sâu: Vietnamese market specifics

Nghiên cứu và ghi vào rules:
- **Device landscape VN 2025-2026:** top 10 devices, screen sizes, OS versions (source: StatCounter, GSMArena)
- **Network conditions:** 4G coverage, average speed, data cost per GB (source: Speedtest Global Index, VNPT/Viettel reports)
- **User behavior:** mobile-first %, average session duration, bounce rate patterns cho travel sites VN
- **Cultural UX:** đọc từ trái-sang-phải, tôn trọng hierarchy (màu đỏ = may mắn, vàng = sang trọng), Zalo > email cho communication
- **Accessibility VN:** tỉ lệ khuyết tật ~7% dân số (WHO), người cao tuổi dùng smartphone tăng nhanh
- **Competitor benchmark:** vinhlongtourist.vn, mytour.vn, traveloka.com/vi — họ implement guidelines thế nào? Đâu là gaps?

### Chiều sâu: measurable criteria

Mỗi rule PHẢI có cách kiểm tra. 3 loại:
1. **Grep/Lint** — lệnh tìm vi phạm trong code (Claude Desktop chạy được)
2. **Lighthouse/DevTools** — metric đo được (CWV scores, contrast ratio, aria audit)
3. **Manual checklist** — khi không tự động được (visual hierarchy, content quality)

Ví dụ:
```markdown
### R3.5 Color contrast

**Verify:**
- Lint: `grep -rn "color:\s*var(--ink-700)" web-nuxt/ | wc -l` — verify muted text dùng đúng token
- Lighthouse: Accessibility audit → Color Contrast score = 100%
- Manual: Dark mode screenshot → text readable trên mọi surface
```

### Chiều sâu: anti-patterns catalog

Cho MỖI section R1-R15, nghiên cứu và ghi **ít nhất 3 anti-patterns** (sai lầm phổ biến). Format:

```markdown
**Anti-pattern R1-AP1:** Spacing bằng margin-bottom khắp nơi thay vì dùng gap
**Hậu quả:** Spacing không đều, element cuối cùng có margin-bottom thừa, khó responsive
**Gốc rễ:** Developer quen jQuery-era CSS, chưa dùng Flexbox/Grid gap
**Fix:** Dùng `gap` trong flex/grid container. Nếu cần margin, chỉ dùng `margin-block-start` (lobotomized owl pattern)
```

**Nguồn anti-patterns:**
- **NNGroup usability mistakes:** https://www.nngroup.com — tìm "top UX mistakes", "design debt"
- **Baymard Institute:** tìm "UX benchmark", "mobile UX", "e-commerce mistakes" (áp dụng cho travel)
- **web.dev case studies:** tìm các bài "how we improved CWV", "lighthouse audit"
- **WCAG failures list:** https://www.w3.org/WAI/WCAG22/Techniques/#failures — danh sách chính thức các failure patterns
- **Apple HIG "Don't" sections:** mỗi HIG page có phần DON'T — trích xuất hết
- **M3 Guidelines "Avoid" sections:** tương tự, mỗi component page có phần sai cần tránh

Tổng tối thiểu: **45 anti-patterns** (3 × 15 sections). Ghi trong mục "Anti-patterns" cuối mỗi section.

### Chiều sâu: emotional design & trust psychology

Nghiên cứu tâm lý **trust và emotion** đặc thù cho web du lịch:

| Nguyên lý | Áp dụng | Nguồn tìm |
|-----------|---------|-----------|
| **Social Proof** | Review count, rating, "X người đã ghé thăm" | Cialdini, NNGroup |
| **Authority Bias** | Badges "Đề xuất bởi Sở Du lịch", nguồn chính thống | Cialdini |
| **Scarcity (ethically)** | "Mùa tốt nhất: tháng 3-5" (thời vụ thật, KHÔNG fake urgency) | Cialdini — CHỈ thông tin thật |
| **Mere Exposure Effect** | Consistent branding, lặp lại visual identity → quen thuộc → trust | Zajonc 1968 |
| **Endowment Effect** | "Hành trình của bạn" (personalization tạo ownership) | Thaler, Kahneman |
| **Paradox of Choice** | Quá nhiều option = không chọn. Max 6-8 cards per section | Schwartz 2004 |
| **Trust Triangle** | Competence (design quality) + Benevolence (no dark patterns) + Integrity (accurate info) | McKnight et al. |
| **Emotional Valence** | Ảnh warm-tone, xanh lá tự nhiên → positive valence cho du lịch | Russell's circumplex model |
| **Nostalgia Effect** | Heritage imagery + modern UI = emotional connection | Batcho, Sedikides |
| **Place Attachment** | Local stories, cultural context → deeper engagement than pure listing | Hidalgo & Hernandez |

**Cho MỖI nguyên lý:** ghi 1 rule cụ thể (CSS/Vue/content) + 1 anti-pattern (dark pattern tránh).

**Dark patterns CẤM TUYỆT ĐỐI** (ghi rõ trong rulebook):
- Fake countdown timers, fake "X người đang xem"
- Hidden costs, bait-and-switch
- Confirmshaming ("Không, tôi không muốn khám phá")
- Misdirection, trick questions
- Forced continuity, roach motel

### Chiều sâu: design tokens audit

Codex PHẢI đọc `web-nuxt/assets/css/variables.css` (646 dòng) trong repo và thực hiện:

1. **Gap analysis:** So sánh tokens hiện có vs Apple HIG values + M3 design tokens → liệt kê tokens THIẾU
2. **Naming audit:** Token names theo chuẩn nào? (Tier 1 primitive / Tier 2 semantic / Tier 3 component) → recommend đổi tên nếu sai quy ước
3. **Unused tokens:** Có tokens nào define mà KHÔNG file CSS/Vue nào dùng?
4. **Hardcoded values:** Grep `web-nuxt/` tìm hardcoded px/color thay vì dùng variable → liệt kê
5. **Dark mode coverage:** Mọi semantic token có dark mode override chưa? (`dark-overrides.css`)
6. **M3 completeness:** M3 có ~40 color roles — bao nhiêu đã map? Bao nhiêu thiếu?

Output: **Appendix A: Token Audit** cuối `design-rulebook.md` — bảng current → recommended → action.

### Chiều sâu: progressive enhancement

Nghiên cứu **progressive enhancement** cho điều kiện mạng Việt Nam:

- **No-JS baseline:** Trang nào PHẢI render đủ nội dung nếu JS chưa load? (SSR → Nuxt đã xử lý, nhưng kiểm tra các component client-only)
- **Slow 3G simulation:** Chrome DevTools → Network → Slow 3G → trang nào vỡ layout? CLS bao nhiêu?
- **Save-Data header:** Khi user bật Data Saver → serve ảnh nhỏ hơn, bỏ animation, simplified layout
- **Offline-capable pages:** Có page nào nên cache bằng Service Worker? (homepage, entity detail đã xem)
- **CSS-only fallbacks:** Nếu font chưa load → system font OK? Nếu ảnh lỗi → placeholder alt text visible?
- **Reduced motion:** `prefers-reduced-motion: reduce` → tắt parallax, crossfade thay slide, instant thay transition

Ghi rules cho MỖI trường hợp trên (thuộc R12 Performance hoặc R13 Responsive).

### Chiều sâu: research methodology

**CÁCH ĐỌC NGUỒN ĐỂ SÂU NHẤT — KHÔNG SKIM:**

1. **Apple HIG:** KHÔNG chỉ đọc trang overview. Click vào MỖI sub-page (ví dụ: Color → System colors, Dynamic colors, Color management). Đọc phần "Best practices", "Platform considerations", "Specifications". Tìm các footnotes, links ra Apple Developer documentation (UIKit/SwiftUI) để lấy giá trị chính xác.

2. **M3:** KHÔNG chỉ đọc component overview. Click "Specs" tab → lấy giá trị token thật (dp, sp, opacity %). Click "Guidelines" → đọc hết. Click "Implementation" → lấy anatomy diagrams. Click "Accessibility" tab nếu có.

3. **Google Search Central:** KHÔNG chỉ đọc overview. Đọc "Documentation" → từng structured data type → "Required properties" vs "Recommended properties". Test với Rich Results Test. Đọc "Updates" blog → có thay đổi mới nào sau baseline 2026-06-27?

4. **Figma:** Đọc phần "Best practices" trong mỗi help article. Tìm Figma Community resources cho design system templates. Đọc Figma Config talks (blog.figma.com) về design tokens.

5. **Nguồn thêm:** Khi tìm nguồn mới, đọc ÍT NHẤT 3 bài từ mỗi nguồn, KHÔNG chỉ 1 bài. Cross-reference giữa các nguồn — nếu chỉ 1 nguồn nói → ghi "single source, cần verify". Nếu 3+ nguồn đồng thuận → ghi "consensus".

**Depth indicator cho mỗi rule:**
- `[depth: 2-source]` = cross-validated từ 2 nguồn
- `[depth: 3-source]` = cross-validated từ 3+ nguồn
- `[depth: research-backed]` = có nghiên cứu academic/empirical (NNGroup study, lab test)
- `[depth: consensus]` = Apple + M3 + W3C đồng thuận
- `[depth: single-source]` = chỉ 1 nguồn, cần cẩn trọng

## NGHIÊN CỨU CÓ SẴN TRONG REPO (ĐỌC TRƯỚC)

**QUAN TRỌNG:** Trước khi nghiên cứu bên ngoài, ĐỌC KỸ các file đã có trong repo:

### File 1: `docs/design-guidelines-apple-google-figma.md` (1384 dòng) — BASELINE
Đây là nghiên cứu ĐÃ LÀM từ 2026-06-27, bao gồm:
- **Phần A:** Apple HIG — system colors (hex light/dark), background colors, label colors, typography scale (Large Title→Caption2), spacing (8pt grid), touch targets (44pt), motion curves, accessibility
- **Phần B:** M3 — HCT color system, tonal palettes (13 tones), typography scale (display→label), 30 component specs (cards, chips, FAB, navigation, search, dialogs...), motion (easing curves + durations), adaptive breakpoints, inclusive design
- **Phần C:** Figma — design fundamentals, design systems, prototyping, dev mode handoff
- **Phần D:** Cross-reference mapping cho vinhlong360 — CSS variables, elevation (0-5), state layers, breakpoints, recommendations

**BẠN PHẢI:**
1. Đọc file này TRƯỚC khi lên mạng nghiên cứu
2. Dùng các giá trị (hex, px, ms, easing) đã extract làm baseline
3. KHÔNG lặp lại nghiên cứu đã có — chỉ **bổ sung và đào sâu** những gì file này chưa cover hoặc đã outdated
4. Nếu tìm thấy thông tin MỚI HƠN (Apple/Google cập nhật sau 2026-06-27), GHI RÕ sự khác biệt

### File 2: `docs/design-research-2026-06-27.md` (1033 dòng)
Gap analysis — mọi điểm chưa đạt vs Apple/M3/WCAG. Đọc để biết GAPS đã identify.

### File 3: `docs/travel-platform-ux-research.md` (904 dòng)
UX 5 platforms du lịch (GYG, Klook, Google, TripAdvisor, Airbnb). Component specs, patterns.

### File 4: `docs/implementation-specs.md` (222 dòng)
Specs HÀNH ĐỘNG đã trích từ 3 file trên, chia theo FE/BE/Content.

**Tổng baseline: 3543 dòng nghiên cứu đã có.** Codex KHÔNG được bỏ qua — phải build ON TOP of this, không phải FROM SCRATCH.

---

## 4 nguồn CHÍNH để nghiên cứu THÊM (đào sâu + cập nhật)

### Nguồn 1: Apple Human Interface Guidelines
**URL:** https://developer.apple.com/design/human-interface-guidelines

Nghiên cứu KỸ các mục:
- **Foundations:** Accessibility, Color, Dark Mode, Icons, Images, Layout, Motion, SF Symbols, Typography
- **Inputs:** Buttons, Menus, Pickers, Search fields, Sliders, Steppers, Text fields, Toggles
- **Patterns:** Charting data, Collaboration, Drag and drop, Entering data, Feedback, File management, Going full screen, Launching, Loading, Managing accounts, Modality, Navigation, Offering help, Onboarding, Playing audio, Playing video, Searching, Settings, Sharing, Undo and redo
- **Components:** Collections and lists, Content, Layout and organization, Menus and actions, Navigation and search, Presentation, Selection and input, Status
- **Technologies:** App Clips, CarPlay, HealthKit, Live Activities, Machine Learning, SF Symbols, Wallet, Widgets

**Tập trung vào:** Spacing values (8pt grid), touch targets (44pt), typography scales, color roles, motion curves, modal patterns, navigation patterns, dark mode rules, accessibility requirements.

### Nguồn 2: Google Material Design 3 (đào sâu hơn baseline §B)
**URL:** https://design.google (Material Design section)

Nghiên cứu KỸ:
- **Styles:** Color system (color roles, tonal palettes, dynamic color), Elevation (levels, shadow values), Icons (sizing, optical adjustments), Motion (easing, duration, patterns), Shape (corner radius families), Typography (type scales, font weights)
- **Components:** Bottom sheets, Cards, Chips, Dialogs, FABs, Menus, Navigation (bar, drawer, rail), Search, Snackbar, Text fields, Top app bar, Tooltips
- **Foundations:** Accessible design, Adaptive design (layouts, grid, breakpoints), Content design, Customizing Material, Design tokens, Interaction states (hover, focus, press, drag, disabled)

**Tập trung vào:** Color roles (primary, secondary, tertiary, error, surface, on-surface), state layer opacities, elevation levels (0-5), shape corner radius, type scale (display, headline, title, body, label), motion durations + easing curves, component anatomy.

### Nguồn 3: Google Search Central (SEO)
**URL:** https://developers.google.com/search?hl=vi

Nghiên cứu KỸ:
- **Structured data:** Tất cả schema types relevant cho du lịch: TouristAttraction, LocalBusiness, Restaurant, Event, Review, FAQPage, HowTo, BreadcrumbList, Article, Organization, ImageObject
- **Core Web Vitals:** LCP, FID/INP, CLS — targets + measurement + optimization
- **Indexing:** Sitemaps, robots.txt, canonical URLs, hreflang, mobile-first indexing
- **Rich results:** Featured snippets, knowledge panels, local pack, image search, video search
- **E-E-A-T:** Experience, Expertise, Authoritativeness, Trustworthiness — signals
- **Page experience:** HTTPS, mobile-friendly, no intrusive interstitials, safe browsing
- **Vietnamese SEO:** Tiếng Việt có dấu trong meta tags, URL slugs, breadcrumbs
- **GEO (Generative Engine Optimization):** Schema types ưu tiên cho AI citation

### Nguồn 4: Figma Help Center & Best Practices (đào sâu hơn baseline §C)
**URL:** https://help.figma.com/hc/en-us

Nghiên cứu KỸ:
- **Design systems:** Variables, Styles, Components, Auto Layout, Constraints — cách Figma khuyến nghị tổ chức design tokens và component libraries
- **Auto Layout:** Spacing modes (packed/space-between), padding, alignment, wrap — MAP sang CSS Flexbox/Grid patterns
- **Variables & Tokens:** Color variables, number variables, modes (light/dark), scoping, aliasing — MAP sang CSS custom properties 3 tầng đang dùng
- **Components & Variants:** Component anatomy, variant properties, slot patterns — MAP sang Vue component props/slots
- **Responsive design in Figma:** Min/max width constraints, wrap behavior, breakpoint frames — MAP sang CSS responsive patterns
- **Prototyping:** Interaction patterns (on click, on hover, on drag), animation curves, smart animate — MAP sang CSS transitions/Vue transitions
- **Accessibility in Figma:** Color contrast checking, focus order, alt text annotation, landmark annotation
- **Dev mode:** Inspect values, CSS generation, variable resolution, measurement between elements
- **Grid systems:** Layout grids (columns, rows, grid), margins, gutters — MAP sang CSS Grid implementation

**Tập trung vào:** Auto Layout ↔ Flexbox mapping, Variables ↔ CSS custom properties mapping, Component variants ↔ Vue props mapping, Figma spacing/sizing values → production CSS values.

### Nguồn 5+: TỰ TÌM THÊM nguồn uy tín

**BẠN PHẢI chủ động tìm và nghiên cứu thêm các nguồn uy tín khác.** Mỗi nguồn thêm phải:
1. Là documentation chính thức (KHÔNG blog cá nhân, KHÔNG Medium articles)
2. Cập nhật trong 12 tháng gần nhất
3. Có giá trị THỰC TẾ cho dự án web du lịch tiếng Việt

**Gợi ý hướng tìm (KHÔNG giới hạn ở đây — tự mở rộng):**

| Lĩnh vực | Nguồn uy tín nên tìm | Giá trị cho dự án |
|-----------|----------------------|-------------------|
| **Web accessibility** | W3C WAI (w3.org/WAI), WCAG 2.2, ARIA Authoring Practices Guide | Chuẩn a11y quốc tế, ARIA patterns cho components |
| **CSS architecture** | CUBE CSS, Every Layout, Modern CSS Solutions (web.dev) | CSS thuần patterns, layout algorithms |
| **Performance** | web.dev/performance, Chrome DevTools docs, Lighthouse docs | Core Web Vitals optimization, audit methodology |
| **Vue/Nuxt** | Nuxt 4 docs (nuxt.com), Vue 3 docs (vuejs.org), VueUse | SSR best practices, composable patterns, Nuxt modules |
| **FastAPI** | FastAPI docs (fastapi.tiangolo.com), Starlette docs | Security best practices, middleware patterns |
| **Schema.org** | schema.org/docs, Google Rich Results Test docs | Structured data cho du lịch Việt Nam |
| **Typography** | Practical Typography (practicaltypography.com), Type Scale tools | Vietnamese typography specifics |
| **Color science** | OKLCH color space docs, Color contrast algorithms | Perceptually uniform color, accessible palettes |
| **Motion design** | Material Motion guidelines, Disney 12 principles applied to UI | Animation timing, meaningful transitions |
| **Travel UX** | Nielsen Norman Group travel UX research, Baymard Institute | Conversion patterns, search UX, mobile travel |
| **PWA** | web.dev/progressive-web-apps | Offline, installable, push — nếu applicable |
| **Internationalization** | W3C i18n, CLDR Vietnamese locale | Vietnamese number/date/currency formatting |
| **Security** | OWASP cheat sheets, FastAPI Security docs | Auth patterns, CSRF, rate limiting |
| **SEO Vietnamese** | Google Search Console insights cho .vn domains | Vietnamese search behavior, local SEO |

**Cách ghi nguồn thêm trong output:**

Mỗi rule trong `design-rulebook.md` mà dựa trên nguồn tự tìm, ghi:
```markdown
**Source:** [Tên nguồn](URL) + Apple HIG [section] + M3 [section]
**Cross-validated:** [Ghi nguồn thứ 2 xác nhận cùng practice]
```

**Tối thiểu: tìm và trích dẫn thêm 5 nguồn ngoài 4 nguồn chính.**
Ghi danh sách tất cả nguồn đã nghiên cứu ở cuối `design-rulebook.md` (mục "Sources & References").

---

# DỰ ÁN ÁP DỤNG

**vinhlong360** — MXH du lịch/OCOP/cộng đồng cho tỉnh Vĩnh Long (VL+Bến Tre+Trà Vinh sáp nhập).

**Stack:** Nuxt 4 SSR (Vue 3) + FastAPI (Python) + CSS thuần (custom properties 3 tầng) + SQLite + PostgreSQL

**Ràng buộc CỨNG:**
- 1 developer duy nhất, budget < 1 triệu/tháng
- CSS thuần + design tokens — KHÔNG Tailwind, KHÔNG UI library
- CHỈ giới thiệu — KHÔNG booking/payment. CTA chỉ Zalo/Phone
- Ảnh CHỈ AI-generated — KHÔNG stock/UGC
- Web-only — KHÔNG native app

**Design tokens hiện có** (`web-nuxt/assets/css/variables.css`, 646 dòng):
- Primitives: `--clay-*` (gạch nung), `--amber-*` (nắng), `--leaf-*` (vườn), `--river-*` (sông), `--sand-*` (nền), `--ink-*` (chữ)
- Semantics: `--primary`, `--accent`, `--secondary`, `--tertiary`, `--bg`, `--ink`, `--muted`
- M3 roles: `--on-primary`, `--primary-container`, `--on-primary-container`
- Component tokens: `--card-radius`, `--chip-height`, `--contact-cta-height`
- Motion tokens: `--ease-emphasized`, `--ease-decelerate`, `--duration-short/medium/long`
- State layers: `--state-hover`, `--state-focus`, `--state-press`

**CSS files:** 9 files, 4424 dòng total (base.css, variables.css, components.css, detail.css, catalog.css, cards.css, events.css, dark-overrides.css, detail-shared.css)

**Trang chính:** 66 pages, 30+ components, 1380 dòng page lớn nhất (cong-dong.vue)

---

# OUTPUT: `docs/design-rulebook.md`

File này sẽ được **CLAUDE.md reference** và Claude Desktop tự động đọc mỗi session. Vì vậy format phải:
1. **Ngắn gọn** — mỗi rule 1-3 dòng, không dài dòng
2. **Actionable** — có giá trị cụ thể, không "nên đẹp hơn"
3. **Có code mẫu** — CSS/Vue snippet copy-paste được
4. **Có DO/DON'T** — ví dụ đúng + sai
5. **Organized by task** — khi Claude code component X, nó tìm rules cho X

## CẤU TRÚC FILE BẮT BUỘC

```markdown
# Design Rulebook — vinhlong360

> File này được Claude Desktop đọc MỖI SESSION.
> Mọi code FE phải tuân theo rules dưới đây.
> Nguồn: Apple HIG, Material Design 3, Google Search Central.
> Cập nhật: [ngày]

---

## R1. SPACING & LAYOUT

### R1.1 Grid system
**Rule:** [1 dòng rule]
**Values:** [giá trị cụ thể]
**Code:**
```css
/* DO */
...
/* DON'T */
...
```

### R1.2 Touch targets
...

## R2. TYPOGRAPHY
## R3. COLOR & THEMING
## R4. MOTION & ANIMATION
## R5. COMPONENTS
## R6. NAVIGATION & PATTERNS
## R7. FORMS & INPUT
## R8. IMAGES & MEDIA
## R9. DARK MODE
## R10. ACCESSIBILITY
## R11. SEO & STRUCTURED DATA
## R12. PERFORMANCE (Core Web Vitals)
## R13. RESPONSIVE & ADAPTIVE
## R14. STATE MANAGEMENT (UI states)
## R15. CONTENT & WRITING
```

---

# 15 SECTIONS CHI TIẾT

## R1. SPACING & LAYOUT (từ Apple HIG + M3)

Chưng cất:
- **8pt grid** — Apple: tất cả spacing là bội số của 8 (4 cho compact). M3: 4px incremental grid.
- **Content margins** — Apple: 16px mobile, 20px tablet, varies desktop. M3: 16/24px margins.
- **Container max-width** — readable text < 680px (HIG), content area breakpoints
- **Section spacing** — vertical rhythm giữa page sections
- **Safe areas** — `env(safe-area-inset-*)` cho notch/dynamic island
- **Scroll padding** — `scroll-padding-top` khi có sticky header
- **Density levels** — M3: default/comfortable/compact. Khi nào dùng density nào? (admin=compact, public=comfortable)
- **Z-index scale** — Layering system: base(0), dropdown(100), sticky(200), overlay(300), modal(400), toast(500). Tìm trong Apple HIG + M3 elevation ordering.
- **Negative space** — Nghiên cứu whitespace psychology: "breathing room" tỉ lệ content:whitespace optimal (40:60 cho editorial, 60:40 cho utility)
- **Optical alignment** — Icons, text, buttons trông lệch dù pixel-perfect. Optical corrections (ví dụ: play icon dịch phải 2px trong circle container)

Output: bảng spacing scale (4/8/12/16/24/32/48/64/96) + khi nào dùng giá trị nào + z-index scale + density table.

## R2. TYPOGRAPHY (từ Apple HIG + M3 + Vietnamese research)

Chưng cất:
- **Type scale** — M3: display (57/45/36), headline (32/28/24), title (22/16/14), body (16/14/12), label (14/12/11). Apple: Large Title (34), Title 1-3 (28/22/20), Headline (17 semibold), Body (17), Callout (16), Subhead (15), Footnote (13), Caption (12/11).
- **Line height** — body >= 1.5 (a11y), heading 1.2-1.3
- **Font weight scale** — regular (400), medium (500), semibold (600), bold (700)
- **Measure** — max-width body text 45-75 characters (Apple), optimal 66ch
- **Vietnamese typography CHUYÊN SÂU:**
  - Dấu tiếng Việt (ă, ơ, ư, ồ, ễ, ự) cần line-height **tối thiểu 1.6** (cao hơn Latin 1.5) vì ascenders/descenders của dấu
  - Letter-spacing CHO UPPERCASE tiếng Việt: tối thiểu 0.05em (dấu uppercase dễ chồng lên nhau)
  - Font-size tối thiểu body: **16px** (không phải 14px) — tiếng Việt nhiều ký tự hơn English cùng nghĩa, chữ nhỏ = khó đọc hơn Latin
  - `text-transform: uppercase` CẨN THẬN — một số font không render dấu uppercase đẹp. Test: "NGUYỄN VĂN HẢO", "ĐỒNG THÁP MỚI"
  - Font stack: system font CÓ HỖ TRỢ Vietnamese đầy đủ (San Francisco, Segoe UI, Roboto có hỗ trợ. TRÁNH font thiếu Vietnamese range)
- **Typographic hierarchy** — Nghiên cứu "typographic scale ratio": 1.2 (minor third), 1.25 (major third), 1.333 (perfect fourth). Ratio nào phù hợp cho du lịch tiếng Việt?
- **Fluid typography** — `clamp()` cho responsive: `font-size: clamp(1rem, 0.9rem + 0.5vw, 1.25rem)`. Nghiên cứu khi nào dùng fluid vs fixed.
- **Text rendering** — `text-rendering: optimizeLegibility` vs `optimizeSpeed`. `-webkit-font-smoothing: antialiased`. Khi nào dùng?
- **Readability research** — NNGroup: 16px body, 1.5 line-height, 65ch measure = optimal. Larson (2004): line spacing > font size improves reading speed 5-10%.

Output: type scale MAP sang CSS variables hiện có + khi nào dùng heading nào + Vietnamese-specific checklist.

## R3. COLOR & THEMING (từ Apple HIG + M3 + Color Science)

Chưng cất:
- **Color roles** — M3: primary, on-primary, primary-container, on-primary-container (x4 cho secondary/tertiary/error). Apple: system colors + semantic colors.
- **Surface colors** — M3: surface (5 tones: dim, bright, container-low/high/highest). Apple: system backgrounds (primary, secondary, tertiary).
- **Contrast requirements** — WCAG 2.2: text 4.5:1 (AA), large text 3:1, UI components 3:1, AAA 7:1
- **Color usage rules** — max 3 accent colors per screen, primary for key actions, error for destructive
- **Tonal palettes** — M3: 13 tones (0/10/20/30/40/50/60/70/80/90/95/99/100)
- **OKLCH color space** — Nghiên cứu OKLCH (perceptually uniform): tại sao M3 chuyển sang HCT (Hue/Chroma/Tone)? Tại sao OKLCH tốt hơn HSL cho palette generation? Khi nào `oklch()` CSS dùng được?
- **Color harmony theory** — Complementary, analogous, triadic, split-complementary. Palette clay/amber/leaf/river là harmony gì? Có đúng color theory không?
- **Cultural color meaning VN** — ĐỎ: may mắn, lễ hội (Tết). VÀNG: sang trọng, hoàng gia. XANH LÁ: tự nhiên, sinh thái. XANH DƯƠNG: tin cậy. TRẮNG: tang (CẨN THẬN). TÍM: tâm linh. → Map sang semantic tokens: error dùng đỏ OK, nhưng primary CTA đỏ → "mua hàng" feeling (conflict với "chỉ giới thiệu")
- **Color blindness audit** — 8% nam giới bị color blindness. Kiểm tra palette bằng công cụ simulation (Colorblindly, Color Oracle). CẤM dùng red/green làm cặp differentiation duy nhất.
- **60-30-10 rule** — 60% dominant (surface/bg), 30% secondary (cards, containers), 10% accent (CTA, icons). Kiểm tra tỉ lệ trong pages hiện tại.
- **Semantic color rules** — Khi nào dùng `--primary` vs `--accent` vs `--secondary`? Decision tree rõ ràng, không để dev đoán.

Output: MAP color roles → CSS variables hiện có (clay/amber/leaf/river/sand/ink) + rules khi nào dùng vai trò nào + color blindness checklist + cultural color map.

## R4. MOTION & ANIMATION (từ Apple HIG + M3)

Chưng cất:
- **Duration scale** — M3: short1(50ms)/short2(100ms)/short3(150ms)/short4(200ms), medium1-4(250-400ms), long1-4(450-700ms). Apple: similar ranges.
- **Easing curves** — M3: emphasized(0.2,0,0,1), emphasized-decelerate(0.05,0.7,0.1,1), emphasized-accelerate(0.3,0,0.8,0.15), standard(0.2,0,0,1), standard-decelerate(0,0,0,1), standard-accelerate(0.3,0,1,1). Apple: default(0.25,0.1,0.25,1).
- **Enter/exit pattern** — enter: decelerate, longer duration. Exit: accelerate, shorter duration.
- **Reduce motion** — `prefers-reduced-motion: reduce` → cross-fade instead of slide, no parallax
- **What to animate** — opacity, transform only (no layout properties). `will-change` sparingly.
- **When NOT to animate** — user-initiated instant actions (toggle, delete), data loading indicators

Output: animation decision tree (khi nào dùng duration nào + easing nào) + code mẫu cho 10 patterns phổ biến.

**THÊM — Micro-interaction catalog (25 recipes):**
Nghiên cứu và ghi CSS-only implementation cho MỖI micro-interaction sau:

| # | Interaction | CSS technique | Duration+Easing |
|---|-------------|---------------|-----------------|
| 1 | Card hover lift | `transform: translateY(-4px)` + shadow deepen | 200ms emphasized |
| 2 | Button press | `scale(0.96)` + state layer | 100ms accelerate |
| 3 | Chip toggle | bg color transition + check icon | 150ms standard |
| 4 | Like heart | scale bounce `1 → 1.3 → 1` + color fill | 300ms spring |
| 5 | Save bookmark | icon rotate `0 → -15 → 0` + fill | 250ms decelerate |
| 6 | Tab switch | underline slide (transform-origin) | 200ms emphasized |
| 7 | Dropdown open | `scaleY(0→1)` + opacity, transform-origin top | 200ms decelerate |
| 8 | Modal enter | `scale(0.9→1)` + `opacity(0→1)` + backdrop | 300ms decelerate |
| 9 | Modal exit | `scale(1→0.95)` + `opacity(1→0)` | 200ms accelerate |
| 10 | Toast slide-in | `translateY(100%→0)` | 300ms decelerate |
| 11 | Toast slide-out | `translateY(0→100%)` | 200ms accelerate |
| 12 | Skeleton shimmer | `@keyframes shimmer` gradient slide | 1.5s linear infinite |
| 13 | Scroll-reveal | `translateY(24px→0)` + `opacity(0→1)` | 400ms decelerate |
| 14 | Image zoom on hover | `scale(1.05)` trong container `overflow:hidden` | 500ms decelerate |
| 15 | Focus ring appear | `outline: 2px solid` + `outline-offset: 2px` | 100ms standard |
| 16 | Error shake | `translateX(0→-8→8→-4→4→0)` | 400ms linear |
| 17 | Success checkmark | SVG stroke-dashoffset animation | 300ms decelerate |
| 18 | Rating star fill | fill color + `scale(1→1.2→1)` sequential | 150ms per star |
| 19 | Accordion expand | `grid-template-rows: 0fr → 1fr` | 300ms emphasized |
| 20 | Page transition | slide + crossfade (Nuxt `<NuxtPage>`) | 200ms standard |
| 21 | Sticky header shrink | height + padding transition on scroll | 200ms standard |
| 22 | Parallax (subtle) | `translateY` at 0.3x scroll speed | requestAnimationFrame |
| 23 | Counter increment | number morph via CSS `@property` | 800ms decelerate |
| 24 | Tooltip fade | `opacity(0→1)` after 200ms delay | 150ms standard |
| 25 | Swipe indicator | subtle `translateX` bounce on touch start | 150ms spring |

Cho MỖI recipe: ghi CSS code hoàn chỉnh + `prefers-reduced-motion` fallback.

## R5. COMPONENTS (từ Apple HIG + M3 + Google Travel UX)

Cho MỖI component type, chưng cất:
- **Cards** — anatomy (media, header, content, actions), sizes, hover state, corner radius. **Thêm:** card density variants (compact list / standard grid / featured spotlight). Relationship giữa corner radius và size (Apple: radius tỉ lệ thuận container size).
- **Buttons** — filled, outlined, text, FAB, icon-only. Heights, padding, radius, states. **Thêm:** button hierarchy rules (1 primary CTA per viewport, max 2 buttons side-by-side, icon-only phải có tooltip).
- **Chips** — filter, input, suggestion. Height 32-36, radius pill, states. **Thêm:** chip group behavior (multi-select, single-select, scroll overflow).
- **Dialogs/Modals** — width, padding, button placement, focus trap, backdrop. **Thêm:** bottom sheet (mobile) thay dialog, focus management lifecycle (trap → restore on close).
- **Navigation** — top bar, bottom bar, sidebar, tabs. Heights, active indicator. **Thêm:** scroll behavior (hide on scroll-down, show on scroll-up), active state visual weight.
- **Search** — search bar anatomy, autocomplete dropdown, recent/suggested. **Thêm:** voice search input? (KHÔNG — web-only constraint). Zero-state, no-results state.
- **Lists** — one-line, two-line, three-line. Leading/trailing elements, dividers. **Thêm:** list virtualization triggers (> 50 items → virtual scroll).
- **Menus** — width min/max, item height, grouping, icons. **Thêm:** cascading vs flat (vinhlong360 = flat, không cascade).
- **Snackbar/Toast** — position, duration, action button, max width. **Thêm:** queue behavior (max 1 visible, FIFO), undo pattern.
- **Text fields** — filled, outlined. Height, padding, label animation, error state. **Thêm:** textarea auto-resize, character limit UI.
- **Badges** — position (top-right icon, inline text), dot vs count, max "99+", size 16-24px. Nghiên cứu: khi nào badge vs chip vs tag?
- **Breadcrumb** — separator, truncation cho deep hierarchy, structured data integration (`BreadcrumbList`)
- **Skeleton** — anatomy mimic real content shape, shimmer direction (LTR), border-radius match component
- **Avatar** — sizes (24/32/40/48/64), fallback initials, status indicator position, group overlap (-8px margin)
- **Progress** — linear vs circular, determinate vs indeterminate, label position, color meaning (primary=normal, error=failed)

Output: cho mỗi component → CSS specs (height, padding, radius, colors) + Vue template skeleton + states (hover, focus, active, disabled, error) + component interaction rules (khi 2 component cạnh nhau thì spacing/hierarchy thế nào).

## R6. NAVIGATION & PATTERNS (từ Apple HIG + M3)

Chưng cất:
- **Navigation types** — tab bar (3-5 items), sidebar (desktop), back button behavior, breadcrumb
- **Modal vs push** — when to use modal (create, confirm) vs push (navigate)
- **Onboarding** — max 3 screens, skip button, progressive disclosure
- **Search pattern** — recent, suggested, filter, instant results
- **Feedback pattern** — success/error/warning/info indicators
- **Loading pattern** — skeleton (content), spinner (action), progress bar (long task)
- **Empty state pattern** — illustration + title + description + CTA

Output: decision tree cho navigation + code patterns cho mỗi scenario.

## R7. FORMS & INPUT (từ Apple HIG + M3 + Baymard Institute)

Chưng cất:
- **Text field anatomy** — label (animated/static), helper text, error text, counter, leading/trailing icon
- **Input sizing** — height >= 48px (M3) / 44px (Apple), padding 16px horizontal
- **Validation** — inline (on blur), not on type. Error: red border + error text below + icon
- **OTP input** — `inputmode="numeric"`, `autocomplete="one-time-code"`, NOT `type="number"`
- **Button in form** — primary: filled, full-width on mobile. Secondary: outlined. Position: end-aligned
- **Form layout** — single column (mobile), 2 columns (desktop, related fields only)
- **THÊM NGHIÊN CỨU:**
  - **inputmode values** — full catalog: `text`, `decimal`, `numeric`, `tel`, `search`, `email`, `url`. Khi nào dùng? VD: phone → `tel`, price → `decimal`
  - **autocomplete tokens** — `name`, `email`, `tel`, `street-address`, `postal-code`, `one-time-code`, `new-password`, `current-password`. Map cho mỗi form trong dự án.
  - **Label placement** — Apple: above input. M3: floating label. Nghiên cứu UX: label above = 16% faster completion (UX Movement, Baymard). Floating label = đẹp nhưng chỗ cho helper text hạn chế. → Quyết định cho vinhlong360?
  - **Error prevention > error correction** — Nghiên cứu NNGroup: format hints trước khi nhập, real-time feedback (character count), confirm before destructive. Tránh validate quá sớm (on keystroke = annoying).
  - **Form flow psychology** — Câu hỏi dễ trước, khó sau (commitment escalation). Group related fields. Progress indicator cho multi-step.
  - **Phone number VN** — Format chuẩn: 10 số bắt đầu 0. Input mask hay tự động format? (`0xxx xxx xxxx`). Khi nào dùng `+84` vs `0`?

Output: form pattern templates (login, register, create post, settings, admin CRUD) + input attribute cheat sheet + validation timing rules.

## R8. IMAGES & MEDIA (từ Apple HIG + M3 + Google Search)

Chưng cất:
- **Image sizing** — hero: 16:9 hoặc 3:2. Thumbnail: 1:1 hoặc 4:3. Gallery: mixed.
- **Responsive images** — `srcset` + `sizes`. AVIF → WebP → JPEG fallback.
- **Loading** — above-fold: `fetchpriority="high"`, NO `loading="lazy"`. Below-fold: `loading="lazy"`.
- **Alt text** — descriptive (SEO + a11y). Entity images: "{entity name} - {location}".
- **Placeholder** — blur-up hoặc dominant-color placeholder. `aspect-ratio` để prevent CLS.
- **Gallery pattern** — 1 large + 4 small grid. Lightbox with swipe. Counter "X/Y".
- **Structured data cho image** — ImageObject schema, license, creator, contentUrl

Output: image component specs + `<NuxtPicture>` pattern + JSON-LD template.

## R9. DARK MODE (từ Apple HIG + M3)

Chưng cất:
- **Surface colors** — M3: dark surface #1C1B1F, container tones shifted. Apple: system backgrounds elevated.
- **Elevation in dark** — lighter surface = higher elevation (inverse of light mode shadow)
- **Color mapping** — primary same hue, lighter tone. Avoid pure white text on pure black bg.
- **Images** — reduce brightness slightly (filter: brightness(0.85)) in dark mode
- **Borders** — more visible in dark (increase opacity or lighten)
- **Shadows** — drop shadows less visible in dark → use border or surface elevation instead
- **Testing** — WCAG contrast phải pass CẢ light AND dark mode

Output: dark mode variable mapping template + component override checklist.

## R10. ACCESSIBILITY (từ Apple HIG + WCAG 2.2 + WAI-ARIA APG)

Chưng cất:
- **Touch targets** — 44x44pt minimum (Apple), 48x48dp recommended (M3). Inline targets: 24x24 minimum.
- **Focus indicators** — visible focus ring, 2px solid, offset 2px, NOT just color change
- **ARIA landmarks** — main, nav, aside, banner, contentinfo. 1 main per page.
- **Heading hierarchy** — sequential h1→h2→h3, no skipping. 1 h1 per page.
- **Color independence** — information NOT conveyed by color alone (add icon, pattern, text)
- **Motion** — `prefers-reduced-motion`, `prefers-contrast`, `prefers-color-scheme`
- **Form accessibility** — label associated via `for/id`, error via `aria-describedby`, `aria-invalid`
- **Dynamic content** — `aria-live="polite"` cho toast, `aria-live="assertive"` cho errors
- **Language** — `lang="vi"` trên `<html>`, language changes trong content marked with `lang="en"`
- **THÊM NGHIÊN CỨU SÂU:**
  - **WAI-ARIA Authoring Practices Guide (APG)** — https://www.w3.org/WAI/ARIA/apg/ — Tìm patterns cho: Accordion, Alert, Breadcrumb, Carousel, Combobox, Dialog, Disclosure, Feed, Grid, Listbox, Menu, Meter, Spinbutton, Switch, Tabs, Toolbar, Tooltip, Tree. Cho MỖI pattern trong dự án → ghi ARIA attributes bắt buộc.
  - **Keyboard navigation map** — Tab order cho MỖI page type. Enter/Space behavior cho interactive elements. Escape để đóng modal/dropdown. Arrow keys trong grid/list/tabs. Home/End trong horizontal scroll.
  - **Screen reader testing protocol:**
    1. Page title đọc đúng?
    2. Landmarks có nhận diện đúng?
    3. Headings hierarchy logic?
    4. Images có alt text descriptive?
    5. Buttons/links có accessible name?
    6. Form fields có label + error announcement?
    7. Dynamic content (toast, chat, infinite scroll) có announce?
  - **Cognitive accessibility** — WCAG 2.2 Level AAA: 2.4.9 (Link Purpose), 3.1.3 (Unusual Words), 3.1.4 (Abbreviations), 3.1.5 (Reading Level), 3.1.6 (Pronunciation). Viết rules cho Vietnamese: abbreviation expansion ("OCOP → Mỗi Xã Một Sản Phẩm"), reading level (lớp 8-9, không dùng thuật ngữ chuyên môn).
  - **Disability statistics VN** — 7.06% dân số (WHO 2023). 1.2% khiếm thị, 1.5% khiếm thính. Người cao tuổi 60+ dùng smartphone tăng 40% YoY. → a11y KHÔNG optional, là LEGAL requirement theo Luật Người Khuyết Tật 2010.
  - **axe-core rules** — Nghiên cứu danh sách rules https://github.com/dequelabs/axe-core → map sang grep/lint commands Claude Desktop chạy được. Top 10 failures phổ biến nhất (Deque annual report).
  - **Skip links** — `<a href="#main-content" class="skip-link">Chuyển đến nội dung chính</a>` — CSS pattern: visible only on `:focus`.

Output: a11y checklist (mỗi component PHẢI pass trước khi merge) + ARIA pattern cheat sheet + keyboard nav map + screen reader test script.

## R11. SEO & STRUCTURED DATA (từ Google Search Central + Schema.org + GEO research)

Chưng cất:
- **Schema types cho du lịch:**
  - `TouristAttraction` — name, description, geo, image (3 ratios), address, telephone
  - `LocalBusiness` — openingHours, priceRange, address, areaServed
  - `Restaurant` — servesCuisine, menu, acceptsReservations=false (chỉ giới thiệu)
  - `Event` — startDate, endDate, location, performer, offers (free admission)
  - `FAQPage` — question/answer pairs (highest GEO priority)
  - `HowTo` — step-by-step (travel guides)
  - `BreadcrumbList` — on ALL pages
  - `AggregateRating` + `Review` — decimal dot (not comma), itemReviewed.name
  - `Article`/`BlogPosting` — community posts, image >= 696px wide, headline < 110 chars
- **Meta tags** — title < 60 chars, description 120-160 chars, og:image 1200x630px
- **URL structure** — ASCII slugs (no diacritics), hierarchical, meaningful
- **Sitemap** — split at 50K URLs, submit via robots.txt, include lastmod + images
- **Core Web Vitals targets** — LCP < 2.5s, INP < 200ms, CLS < 0.1
- **Mobile-first** — responsive, no intrusive interstitials, viewport meta tag
- **THÊM — GEO (Generative Engine Optimization) CHUYÊN SÂU:**
  - Nghiên cứu cách Google AI Overview, Bing Chat, Perplexity trích dẫn content du lịch
  - Schema types ưu tiên cho AI citation: FAQPage > HowTo > Article+BreadcrumbList > TouristAttraction
  - **Structured content pattern:** Entity pages có clear factual blocks (giờ mở cửa, địa chỉ, giá, mùa tốt nhất) → AI dễ extract
  - **Citation-worthy format:** mỗi entity page mở đầu bằng 1 câu definitive answer ("Cù lao An Bình là cù lao lớn nhất huyện Long Hồ, nổi tiếng với vườn cây ăn trái và homestay sông nước.")
  - **Unique content signal:** Nội dung gốc (không copy từ nguồn khác) + first-hand experience signals (review từ users, tips thực tế)
  - **Topical authority:** Hub pages covering MỌI subtopic trong 1 vùng → Google hiểu site là authority về du lịch 3 tỉnh
- **THÊM — Vietnamese SEO deep dive:**
  - `hreflang="vi"` + `content-language: vi` headers
  - Google Search Console VN: top queries cho du lịch Vĩnh Long, Bến Tre, Trà Vinh — các keyword pattern phổ biến ("du lịch + [tỉnh]", "[điểm đến] + ở đâu", "[món ăn] + ngon nhất")
  - Long-tail VN: "cù lao an bình có gì chơi", "bánh tráng phơi sương trảng bàng" → FAQ schema
  - Internal linking: hub-spoke topology (trang huyện → trang entity → trang review)
  - Vietnamese snippet optimization: title/description CHỈ tiếng Việt, KHÔNG trộn English (trừ brand names)
- **THÊM — Open Graph & social:**
  - `og:type: article` cho mọi content page
  - `og:image`: 1200×630px (Facebook), `twitter:image`: 1200×675px (X/Twitter)
  - Zalo Open Graph: tương thích OG standard (Zalo app đọc og: tags khi share link)
  - WhatsApp preview: og:title + og:description + og:image đủ
  - Test tool: Meta Sharing Debugger, Twitter Card Validator

Output: cho mỗi page type → meta template + JSON-LD template + checklist + GEO optimization guide.

## R12. PERFORMANCE / Core Web Vitals (từ Google Search + web.dev + HTTP Archive)

Chưng cất:
- **LCP optimization** — hero image `fetchpriority="high"`, preload critical fonts, inline critical CSS
- **INP optimization** — event handlers < 200ms, `requestIdleCallback` cho non-critical, debounce
- **CLS optimization** — `aspect-ratio` on images, font-display: swap with size-adjust, reserved space
- **CSS performance** — `contain: content` on cards, `content-visibility: auto` on below-fold
- **Image optimization** — responsive srcset, AVIF with WebP fallback, quality 75
- **Font loading** — preload primary font, `font-display: swap`, system font stack fallback
- **JavaScript** — defer non-critical, lazy load below-fold components, minimize hydration
- **THÊM — Performance budgets per page type:**

| Page type | JS budget | CSS budget | Image budget | LCP target | CLS target | INP target |
|-----------|-----------|------------|-------------|------------|------------|------------|
| Homepage | < 150KB gz | < 30KB gz | < 500KB total | < 2.0s | < 0.05 | < 150ms |
| Entity detail | < 120KB gz | < 25KB gz | < 800KB (gallery) | < 2.5s | < 0.05 | < 150ms |
| Catalog/list | < 100KB gz | < 20KB gz | < 400KB (cards) | < 2.0s | < 0.1 | < 100ms |
| Community | < 130KB gz | < 25KB gz | < 300KB | < 2.5s | < 0.1 | < 150ms |
| Admin pages | < 200KB gz | < 35KB gz | N/A | < 3.0s | < 0.1 | < 200ms |

- **THÊM — Resource hints cheat sheet:**
  - `<link rel="preconnect">` — cho CDN images, fonts
  - `<link rel="dns-prefetch">` — cho 3rd-party API domains
  - `<link rel="preload" as="image">` — cho hero/LCP image
  - `<link rel="preload" as="font">` — cho primary font (crossorigin!)
  - `<link rel="modulepreload">` — cho critical JS modules (Nuxt tự xử lý)
  - `<link rel="prefetch">` — cho likely-next-page routes
- **THÊM — CSS optimization rules:**
  - `@layer` ordering: reset → base → components → utilities → overrides
  - CSS specificity budget: max 0-3-0 (no IDs in selectors)
  - Selector performance: tránh `*`, tránh deep nesting > 3 levels, tránh attribute selectors trên elements nhiều
  - `will-change` budget: max 3 elements per viewport (GPU memory)
  - Animation: ONLY `transform` + `opacity` (compositor-only, no layout/paint)
- **THÊM — Network-aware loading:**
  - `navigator.connection.effectiveType` → '4g'/'3g'/'2g'/'slow-2g'
  - '2g'/'slow-2g' → load thumbnail only, no gallery, no animation
  - `navigator.connection.saveData` → same as Save-Data header
  - Pattern: `<NuxtPicture>` width tiers: 320/640/960/1280/1920

Output: performance budgets table + resource hints template + CSS optimization rules + network-aware loading pattern.

## R13. RESPONSIVE & ADAPTIVE (từ M3 + Apple)

Chưng cất:
- **Breakpoints** — compact (0-599), medium (600-839), expanded (840-1199), large (1200-1599), extra-large (1600+). Map to Nuxt: 600/768/1024/1280/1440.
- **Layout grid** — compact: 4 cols, 16px margins, 8px gutters. Medium: 8 cols, 24px margins. Expanded: 12 cols, 24px margins.
- **Navigation adaptation** — compact: bottom bar. Medium: rail. Expanded: drawer.
- **Content adaptation** — list → grid, single column → multi-column, stacked → side-by-side
- **Component adaptation** — dialog → bottom sheet (mobile), side panel (desktop)
- **Safe areas** — `env(safe-area-inset-*)` cho iOS notch, dynamic island, home indicator

Output: breakpoint decision table + layout templates per breakpoint.

## R14. STATE MANAGEMENT / UI States (từ M3)

Chưng cất:
- **Interaction states** — enabled, disabled, hover, focused, pressed, dragged. Each has state layer opacity.
- **State layer** — semi-transparent overlay trên component surface. Opacities: hover 8%, focus 10%, press 10%, drag 16%.
- **Disabled state** — opacity 38% foreground, 12% background. `pointer-events: none`.
- **Selected state** — filled vs outlined toggle. Active indicator.
- **Error state** — error color outline + error text + icon. `aria-invalid="true"`.
- **Loading state** — skeleton shimmer (1.5s loop), spinner (indeterminate), progress bar (determinate).
- **Empty state** — illustration (48-64px icon) + title + description + CTA button.

Output: state layer CSS mixin + component state checklist.

## R15. CONTENT & WRITING (từ Apple HIG + M3 + Vietnamese UX + Content Strategy)

Chưng cất:
- **Tone** — Apple: friendly, direct, focused. M3: clear, concise, useful.
- **Vietnamese adaptation** — heading: Hán-Việt (SEO). Body: thuần Việt (readability). Câu < 15 từ.
- **Button labels** — verb + noun. "Gọi điện" not "Điện thoại". "Xem bản đồ" not "Bản đồ".
- **Error messages** — what happened + why + how to fix. Not technical jargon.
- **Empty states** — encouraging tone + specific CTA. "Chưa có đánh giá nào. Hãy là người đầu tiên!"
- **Truncation** — `-webkit-line-clamp: 2` cho card titles, `3` cho descriptions. Ellipsis visible.
- **THÊM NGHIÊN CỨU SÂU:**
  - **UI string library:** Ghi DANH SÁCH tất cả UI strings tiếng Việt cần dùng, chia theo context:
    - Navigation: "Trang chủ", "Khám phá", "Cộng đồng", "Tài khoản"
    - Actions: "Xem thêm", "Thu gọn", "Chia sẻ", "Lưu", "Gọi điện", "Nhắn Zalo", "Chỉ đường"
    - Feedback: "Đang tải...", "Không tìm thấy kết quả", "Đã lưu thành công", "Có lỗi xảy ra"
    - Time: "vừa xong", "X phút trước", "hôm qua", "X ngày trước" (relative time tiếng Việt)
    - Numbers: "1,2K lượt xem", "4.5 ⭐" (VN dùng dấu phẩy thập phân NHƯNG web chuẩn dùng dấu chấm → theo chuẩn web)
  - **Microcopy psychology:**
    - CTA copy: test A/B patterns "Gọi ngay" vs "Liên hệ" vs "Hỏi giá" — cái nào fit "chỉ giới thiệu" tone?
    - Encouragement microcopy: "Chia sẻ trải nghiệm của bạn" > "Viết đánh giá" (invitation vs command)
    - Permission requests: "Cho phép vị trí để tìm điểm gần bạn" — giải thích VALUE trước khi hỏi
  - **Reading patterns VN:**
    - F-pattern (NNGroup eye-tracking): áp dụng cho list pages — info quan trọng ở đầu dòng
    - Z-pattern: áp dụng cho landing sections — CTA ở cuối Z
    - Inverted pyramid: mỗi entity description mở đầu bằng câu quan trọng nhất (GEO-friendly)
  - **Content hierarchy signals:**
    - Visual weight: font-size + weight + color contrast → 3 cấp (primary / secondary / tertiary info)
    - Spatial grouping: Gestalt proximity — related info cách nhau < 16px, unrelated > 32px
    - Progressive disclosure: "Xem thêm" cho descriptions > 3 dòng — đo optimal truncation length cho tiếng Việt
  - **Inclusive language VN:**
    - Xưng hô: "bạn" (thân thiện, phổ quát). TRÁNH: "quý khách" (quá formal), "mày/tao" (thô), "anh/chị" (giả định giới tính/tuổi)
    - Giới tính: neutral tone, TRÁNH stereotypes trong descriptions ("thích hợp cho gia đình" OK, "dành cho phụ nữ" TRÁNH)
    - Vùng miền: TRÁNH gọi "miền quê" hay "nhà quê" → "vùng nông thôn" hoặc tên cụ thể

Output: writing guidelines table (Vietnamese) + UI string library + microcopy patterns + inclusive language guide.

---

# FORMAT CỦA MỖI RULE TRONG OUTPUT

```markdown
### R1.1 Spacing scale — 8pt grid

**Source:** Apple HIG Foundations/Layout, M3 Layout/Spacing
**Rule:** Tất cả spacing (margin, padding, gap) phải là bội số của 4px. Ưu tiên scale: 4/8/12/16/24/32/48/64.
**Khi nào dùng:**
| Value | Use case |
|-------|----------|
| 4px | Icon-to-text gap, inline spacing |
| 8px | Compact padding, chip gap, list item gap |
| 12px | Card internal padding (compact) |
| 16px | Card padding, section padding (mobile), form field gap |
| 24px | Section padding (desktop), card gap |
| 32px | Section gap (major) |
| 48px | Page section vertical rhythm |
| 64px | Hero section padding, page top margin |

**DO:**
```css
.card { padding: 16px; gap: 8px; }
.section { margin-block: 48px; }
```

**DON'T:**
```css
.card { padding: 15px; gap: 10px; }  /* not on 4px grid */
.section { margin-block: 50px; }     /* not on scale */
```

**CSS Variable:** `var(--space-4)` through `var(--space-64)` (define if missing)
```

---

# QUY TẮC VIẾT OUTPUT — TẬN DỤNG BASELINE

1. **ĐỌC BASELINE TRƯỚC** — `design-guidelines-apple-google-figma.md` (1384 dòng) đã có sẵn giá trị cụ thể. KHÔNG nghiên cứu lại những gì đã có — chỉ verify, cập nhật nếu outdated, và ĐÀO SÂU thêm.
2. **Ghi rõ nguồn gốc mỗi rule:**
   - `[BASELINE]` = lấy nguyên từ file có sẵn, đã verify vẫn đúng
   - `[BASELINE+]` = mở rộng/đào sâu từ baseline bằng nghiên cứu mới
   - `[NEW]` = rule hoàn toàn mới, baseline chưa cover
   - `[UPDATED]` = baseline đã có nhưng thông tin mới hơn từ nguồn gốc (ghi rõ gì thay đổi)
3. **Mỗi rule tối đa 20 dòng** (không viết essay — Claude Desktop đọc nhanh)
4. **Luôn có DO/DON'T** với code mẫu CSS hoặc Vue template
5. **Luôn có "Source"** — URL cụ thể + section name (Apple HIG page nào, M3 component nào, Google Search doc nào, Figma help article nào, nguồn thêm nào)
6. **Luôn MAP sang CSS variables hiện có** (clay/amber/leaf/river/sand/ink system) — xem `variables.css` trong repo
7. **Giá trị CỤ THỂ** — "12px" không phải "small", "300ms" không phải "fast"
8. **Vietnamese context** — ví dụ dùng tiếng Việt, entity names thật (Cù lao An Bình, Bánh khọt)
9. **Không recommend thêm dependency** — giải pháp CSS thuần hoặc Nuxt built-in
10. **Mỗi section kết thúc bằng CHECKLIST** — Claude Desktop chạy qua trước khi code
11. **Cuối file: CHANGELOG vs baseline** — bảng tóm tắt: bao nhiêu rules [BASELINE], [BASELINE+], [NEW], [UPDATED]. Ghi rõ những gì baseline SAI hoặc ĐÃ CŨ.

## Tổng rules tối thiểu: **150 rules** across 15 sections

**Mỗi rule PHẢI có đủ 6 tầng** (WHAT → WHY → RECONCILE → CONTEXT → VERIFY → EXCEPTION).
Rule nào thiếu tầng = rule nông, KHÔNG ĐƯỢC ghi vào output.

**Mỗi section PHẢI có thêm:**
- **Anti-patterns:** ít nhất 3 per section (tổng ≥ 45)
- **Decision tree:** khi nào dùng option A vs B (flow chart dạng text)
- **Checklist cuối section:** Claude Desktop chạy trước khi code component loại đó

Phân bổ (TĂNG so với trước):
- R1 Spacing: 12+ rules
- R2 Typography: 12+ rules
- R3 Color: 15+ rules
- R4 Motion: 10+ rules (+ 25 micro-interaction recipes)
- R5 Components: 22+ rules (mỗi 15 component types 1-2 rules)
- R6 Navigation: 10+ rules
- R7 Forms: 10+ rules
- R8 Images: 8+ rules
- R9 Dark Mode: 8+ rules
- R10 Accessibility: 14+ rules (+ ARIA pattern sheet + keyboard map)
- R11 SEO: 12+ rules (+ GEO guide)
- R12 Performance: 10+ rules (+ performance budgets table)
- R13 Responsive: 7+ rules
- R14 States: 7+ rules
- R15 Content: 8+ rules (+ UI string library)

## Appendixes BẮT BUỘC cuối file

File `design-rulebook.md` PHẢI có các appendix sau:

### Appendix A: Token Audit
Bảng cross-reference `variables.css` hiện có vs Apple HIG + M3 recommended tokens:
| Token hiện có | Giá trị | Apple HIG equiv | M3 equiv | Action (OK/FIX/ADD) |

### Appendix B: Component State Matrix
Ma trận states cho MỖI component type:
| Component | Enabled | Disabled | Hover | Focus | Pressed | Error | Loading | Empty | Selected |
Cho mỗi ô: ghi CSS changes (opacity, color, scale, shadow).

### Appendix C: Sources & References
Danh sách TẤT CẢ nguồn đã nghiên cứu:
- 4 nguồn chính (URLs + sections đã đọc)
- 8+ nguồn tự tìm (URLs + why relevant)
- Academic/research papers referenced
- Tổng số trang/bài đã đọc thực sự

### Appendix D: Cognitive Science Quick Reference
Bảng 14+ nguyên lý → rule number → component áp dụng. Quick lookup cho Claude Desktop.

### Appendix E: CHANGELOG vs Baseline
- Bao nhiêu [BASELINE], [BASELINE+], [NEW], [UPDATED]
- Baseline items đã CŨ hoặc SAI → sửa gì
- Baseline items đã CONFIRM vẫn đúng

---

# QUALITY GATE — TỰ KIỂM TRA TRƯỚC KHI NỘP

Trước khi finalize `design-rulebook.md`, chạy checklist này. **TẤT CẢ phải PASS:**

## QG1. Depth check (6 tầng)
Mở random 10 rules → mỗi rule CÓ ĐỦ 6 tầng (WHAT/WHY/RECONCILE/CONTEXT/VERIFY/EXCEPTION)?
- Nếu < 10/10 pass → viết lại rules thiếu tầng

## QG2. Actionable check
Mở random 10 rules → mỗi rule có **giá trị cụ thể** (px, ms, hex, ratio)?
- "khoảng cách phù hợp" = FAIL. "gap: 16px" = PASS

## QG3. Code check
Mở random 10 rules → mỗi rule có **DO/DON'T code snippet** copy-paste được?
- Snippet phải dùng CSS variables hiện có (clay/amber/leaf/river/sand/ink)

## QG4. Cross-validation check
Mở random 10 rules → mỗi rule có **Source** ghi ít nhất 2 nguồn?
- Rule chỉ trích 1 nguồn mà không cross-validate = viết lại

## QG5. Vietnamese context check
Mở random 10 rules → có rule nào THIẾU tầng 4 (CONTEXT Việt Nam)?
- Rule về typography mà không nhắc dấu tiếng Việt = FAIL
- Rule về touch target mà không nhắc outdoor/mobile VN = FAIL

## QG6. Verify check
Mở random 10 rules → mỗi rule có **cách kiểm tra** (grep/Lighthouse/manual)?
- Rule không verify được = rule vô dụng, viết lại

## QG7. Quantity check
- Tổng rules >= 150? (đếm ### headings)
- Mỗi section R1-R15 đạt minimum MỚI? (R1: 12+, R2: 12+, R3: 15+, R5: 22+, ...)
- Anti-patterns tổng >= 45? (3+ per section)
- Nguồn bên ngoài (ngoài 4 chính) >= 8?
- Cognitive science principles referenced >= 12/14?
- Micro-interaction recipes >= 25?
- Appendix A-E đầy đủ?

## QG8. Baseline check
- Có Appendix E: CHANGELOG vs baseline?
- Ghi rõ bao nhiêu [BASELINE], [BASELINE+], [NEW], [UPDATED]?
- Có rule nào lặp lại baseline mà KHÔNG thêm giá trị? → xóa hoặc upgrade thành [BASELINE+]
- Token Audit (Appendix A) cross-referenced với variables.css thật?

## QG9. Conflict check
- Có rule nào CONFLICT với ràng buộc dự án? Kiểm tra:
  - Không recommend Tailwind/UI library (CSS thuần only)
  - Không recommend booking/payment UI (chỉ giới thiệu)
  - Không recommend stock images (chỉ AI-generated)
  - Không recommend native app patterns (web-only)
  - Không recommend thêm dependency trả phí

## QG10. Readability check
- Mỗi rule <= 20 dòng? (Claude Desktop đọc nhanh, không viết essay)
- File tổng < 4000 dòng? (quá dài = Claude Desktop context bị đẩy ra)
- Mục lục ở đầu file có link tới mỗi section?

**Nếu bất kỳ QG nào FAIL → sửa → chạy lại checklist → chỉ khi 10/10 PASS mới nộp.**

---

# FORBIDDEN — KHÔNG ĐƯỢC RECOMMEND

Vì ràng buộc dự án, tuyệt đối KHÔNG ghi rules khuyến nghị:
1. **Tailwind CSS, Bootstrap, hay UI library nào** — dùng CSS thuần + custom properties
2. **Booking/payment/checkout UI** — CTA chỉ Zalo/Phone liên hệ
3. **Stock images** (Pexels, Unsplash, Shutterstock) hoặc UGC photos — chỉ AI-generated
4. **Native app patterns** (push notifications, App Store, deep links) — web-only
5. **Google Fonts trả phí** hoặc font nặng > 100KB — system font + 1 web font tối đa
6. **External services trả phí** (analytics SaaS, CDN trả phí, monitoring) — free-tier only
7. **AR/VR/audio guide/3D** — quá nặng cho solo dev
8. **Multi-language i18n** — tiếng Việt duy nhất (tiếng Anh chỉ cho code/dev docs)

---

# SAU KHI CODEX TẠO XONG `design-rulebook.md`

## Bước tích hợp vào Claude Desktop (người dùng tự làm)

### 1. Copy file vào docs/
```bash
# Codex tạo file → download → đặt vào:
# C:\Code\vinhlong360\docs\design-rulebook.md
```

### 2. Thêm reference vào CLAUDE.md (sau dòng "Kiến trúc & lý do:")
```markdown
## 0. Bối cảnh 1 dòng
... Kiến trúc & lý do: `docs/kien-truc-va-lo-trinh.md`, `docs/architecture-decisions.md`.
**Quy tắc thiết kế bắt buộc: `docs/design-rulebook.md`** (Apple HIG + M3 + Google Search).
```

### 3. Thêm vào §6 Quy ước:
```markdown
## 6. Quy ước
...
- **Mọi code FE** phải tuân theo `docs/design-rulebook.md`. Trước khi code component/page:
  đọc section tương ứng (R5 cho components, R7 cho forms, R11 cho SEO, v.v.)
- Không hardcode color/spacing/font-size — luôn dùng CSS variable từ `variables.css`.
```

### 4. Thêm vào docs/implementation-specs.md đầu file:
```markdown
> **Design rulebook:** Tất cả specs trong file này PHẢI tuân theo rules trong `design-rulebook.md`.
> Khi conflict, design-rulebook.md thắng (vì dựa trên Apple HIG + M3 + Google Search mới nhất).
```

### 5. Thêm vào parallel-session-guide.md (Template FE):
```markdown
## Quy tắc
...
- ĐỌC `docs/design-rulebook.md` TRƯỚC khi code. Checklist cuối mỗi section = gate trước commit.
```

**Kết quả:** Mọi session Claude Desktop (kể cả session song song FE) sẽ tự động áp dụng
design rules từ Apple HIG, Material Design 3, và Google Search Central.

---

## KẾT THÚC PROMPT
