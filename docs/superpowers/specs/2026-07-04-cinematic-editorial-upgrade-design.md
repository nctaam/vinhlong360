# Nâng cấp cinematic-editorial — Design (batch 1: luồng khám phá)
> STATUS (2026-07-10): done — design/audit đã hiện thực & ship.


**Ngày:** 2026-07-04. **Nhánh:** main. **Kiểu:** bespoke per-page, thẩm mỹ cinematic-editorial (NatGeo/Condé Nast).

**Goal:** Nâng 4 trang lõi của luồng khám phá lên cảm giác **premium / điện ảnh / kể chuyện rõ** kiểu tạp chí du lịch cao cấp — mỗi trang bespoke nhưng cùng một ngôn ngữ editorial. Pha 1 = code-first (đẹp cả khi thiếu ảnh); pha 2 = ảnh AI-gen (chủ duyệt sau).

**Bối cảnh:** UI hiện ~8.6/10 (audit 10 chiều 2026-07-04, `docs/audit/2026-07-04-page-reaudit.md`). Nền token 3 tầng (`web-nuxt/assets/css/variables.css`), dark-parity, reduced-motion khắp nơi; homepage đã có Ken Burns/parallax/spotlight. Nút thắt: ảnh (chỉ AI-gen).

## Global Constraints (bất di — mọi task ngầm gồm phần này)
- **CSS thuần + token**, KHÔNG Tailwind. Màu/spacing qua `var(--...)`; thêm token mới vào `variables.css` (light+dark).
- **Font display self-host, hỗ trợ ĐẦY ĐỦ tiếng Việt** (dấu + đ/ă/â/ê/ô/ơ/ư). Subset Latin+Vietnamese, `woff2`, `font-display: swap`, preload chỉ weight hero. KHÔNG CDN font (bài học CWV). Ứng viên: Fraunces / Lora / Playfair Display (đều có Vietnamese) — chốt khi làm.
- **Reduced-motion:** mọi Ken-Burns/parallax/scroll-reveal/transition PHẢI gate `@media (prefers-reduced-motion: reduce)` → tắt hoặc còn fade tối giản.
- **CWV:** LCP hero `loading="eager" fetchpriority="high"` + `width/height` (0 CLS); ảnh khác lazy + kích thước rõ + `<NuxtImg>`/weserv khi remote; scroll-reveal bằng IntersectionObserver (không lib); KHÔNG thêm dependency nặng (§no-heavy-features). SSR-fetch qua `web-nuxt/utils/apiFetch.ts` (không `$fetch` nội bộ — bài học silent-empty).
- **CTA chỉ liên hệ** (Zalo/điện thoại/hỏi-giá), KHÔNG booking/giỏ/thanh toán (§1.4).
- **Đẹp-khi-thiếu-ảnh:** hero + story block phải premium bằng gradient/texture/typographic composition khi ảnh mỏng; ảnh chỉ nâng thêm.
- **Không phá:** giữ SEO/JSON-LD, a11y (landmark/focus/alt), empty/loading/error, dark-mode của mỗi trang. Build (`npm run build`) + `pytest -q -p no:randomly` (baseline 6-đỏ PG-env) phải giữ.

## Ngôn ngữ editorial dùng chung (bespoke vẫn rút từ đây)
Không bắt buộc component hoá cứng (đây là bespoke), nhưng chuẩn hoá **vocabulary CSS + pattern**:
- **Cinematic hero:** full-bleed media + dark scrim gradient + overlay editorial: `kicker` (eyebrow uppercase tracking) → `display title` (display serif, cỡ lớn fluid) → `dek/standfirst` (1-2 câu dẫn) → `meta line` (địa danh · mùa · loại). Ken Burns (scale rất chậm) + parallax nhẹ khi scroll.
- **Typography editorial:** display serif cho H1/H2 hero+section; body giữ font hiện tại; drop-cap câu mở (`::first-letter`); `pull-quote` (trích dẫn cỡ lớn, lề âm); measure ~68ch + leading rộng cho đoạn văn.
- **Scroll narrative:** `scroll-reveal` (fade+rise khi vào viewport, IO), `sticky-chapter` (tiêu đề chương dính khi cuộn qua section), `parallax layer` (media dịch chậm hơn text).
- **Story block:** section ảnh full-bleed xen chữ, `figure` + `figcaption`/credit, caption cảm giác.
- **Nhịp điện ảnh:** 1 tiêu điểm/viewport, section-break rõ (khoảng thở lớn, divider mảnh), tránh nhồi.
- Token mới đề xuất: `--font-display`, `--scrim-hero` (gradient), `--space-editorial` (rhythm dọc lớn), `--measure-read`, `--ease-cinematic`, `--dur-kenburns`.

## Mô hình kể chuyện lồng nhau (zoom in) — 4 trang = 1 vòng cung
- **Home** (`pages/index.vue`) = *cover story* 3 vùng: mở đầu gợi mở về miền Tây, mời khám phá.
- **khu-vuc/[area]** (`pages/khu-vuc/[area].vue`) = *cẩm nang vùng*: bản sắc vùng + phường/xã như các "chương" + highlight.
- **xa-phuong/[id]** (`pages/xa-phuong/[id].vue`) = *hồ sơ nơi chốn*: bản sắc xã, điểm/sản vật nổi bật.
- **dia-diem/[id]** (`pages/dia-diem/[id].vue`) = *bài feature*: câu chuyện đầy đủ nhất (lịch sử/văn hoá/trải nghiệm/thực dụng).
Bàn giao dẫn chuyện: mỗi trang có khối "đọc tiếp" trỏ trang zoom kế (region→area→ward→place) + ngược lên.

## Bespoke từng trang (batch 1)

### Home — cover story
Hero điện ảnh vùng (Ken Burns, dek mời gọi) → scroll editorial theo "chương" chủ đề (di sản · ẩm thực · mùa · cộng đồng), mỗi chương 1 section filmic có sticky-title + spotlight entity dạng card tạp chí + interstitial dẫn chuyện. Giữ dữ liệu `/api/homepage` hiện có; tái sắp xếp thành mạch tạp chí. (Home vốn đã có hero/spotlight — nâng, không đập bỏ.)

### khu-vuc/[area] — cẩm nang vùng
Hero vùng (tên + dek gợi cảm + stats dạng meta editorial) → intro bản sắc (drop-cap) → chip phường/xã như "mục lục chương" (link xuống) → highlight entity dạng feature card → story block theo mùa/chủ đề → "đọc tiếp: xã/phường".

### xa-phuong/[id] — hồ sơ nơi chốn
Hero xã → hồ sơ editorial (nổi tiếng vì gì) → điểm/sản vật dạng card tuyển → cross-link vùng cha + "đọc tiếp: điểm đến".

### dia-diem/[id] — flagship feature
Hero entity (Ken Burns) → lead có drop-cap (từ summary) → section ảnh-truyện immersive (PhotoGallery nâng thành photo-essay) → pull-quote trích summary → sidebar cảm giác/thực dụng (giờ/mùa/liên hệ) → "câu chuyện nơi chốn" → related/nearby dạng "đọc tiếp" → CTA liên hệ như *end-note* tạp chí. Xây trên trang detail đã giàu (giữ JSON-LD/SEO/contact-widget).

## Nền kỹ thuật
- Token editorial mới vào `variables.css` (light+dark). Display font self-host trong `web-nuxt/assets/fonts/` + `@font-face` (subset VN, swap), preload weight hero trong `nuxt.config.ts` head.
- CSS editorial dùng chung: file `web-nuxt/assets/css/editorial.css` (hero/scrim/kicker/dek/pull-quote/drop-cap/story-block/scroll-reveal utilities), import route-scoped ở 4 trang (giữ entry CSS gọn — bài học route-CSS split).
- Scroll-reveal + parallax: 1 composable nhẹ `web-nuxt/composables/useScrollReveal.ts` (IntersectionObserver, tôn trọng reduced-motion), không lib.
- Mỗi trang: giữ SSR `apiFetch`, LCP hero eager, phần dưới lazy.

## Phân rã & thứ tự (cho writing-plans)
1. **Nền editorial** — token + `@font-face` + `editorial.css` + `useScrollReveal` (tiên quyết, nhỏ, verify build).
2. **Home** bespoke (lớn nhất, đặt nhịp).
3. **khu-vuc/[area]** bespoke.
4. **xa-phuong/[id]** bespoke.
5. **dia-diem/[id]** bespoke (flagship).
Mỗi task: build xanh + reduced-motion + không CLS + SSR còn nội dung + a11y/SEO giữ. Deploy = chủ quyết.

## Pha 2 (chủ duyệt sau)
Sinh ảnh hero/editorial AI-gen (cx/gpt-5.5-image) cho 4 trang → thay gradient/texture bằng ảnh thật; cùng khung layout đã dựng ở pha 1.

## Nghiệm thu (batch 1)
4 trang mang thẩm mỹ cinematic-editorial (hero + typography display + scroll narrative + story block) đẹp cả khi thiếu ảnh; build+test xanh; CWV không xấu đi (LCP/CLS/INP); reduced-motion + a11y + SEO + dark giữ nguyên; mạch "đọc tiếp" nối 4 trang.
