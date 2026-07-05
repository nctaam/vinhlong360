# Nâng cấp toàn diện trang chủ vinhlong360 — Design Spec

> Ngày: 2026-07-05 · Nhánh: `feat/entity-content-model` · Surface: `web-nuxt/pages/index.vue` + vài component/composable mới.
> Mục tiêu: đưa trang chủ từ ~7.5/10 (live) lên **9+**, qua **ảnh hero-grade + biên tập cô đọng + 1 khoảnh khắc giác quan chữ ký** — KHÔNG phải thêm nhiều feature/chuyển động.

## 0. Bối cảnh & nguyên tắc

- Vừa xong: de-slop 2 section (mục lục 01–04 editorial, spotlight ảnh thật) + sinh **31 ảnh entity** (commit `30a3fae`, **chưa deploy**).
- **Đòn bẩy #1 = deploy 31 ảnh** (step 0). Tự nâng ~0.7–1.0đ vì lấp điểm yếu placeholder.
- Ràng buộc bất biến: solo-dev, web-only, **CSS-tokens (không Tailwind)**, **ảnh CHỈ AI-gen** (cx/gpt-5.5-image), **CTA chỉ liên hệ** (không đặt hàng), **CWV giữ tốt**, reduced-motion, dark-parity, §B5 (mỗi bước để trang chạy được).
- Kim chỉ nam: **"Ít mà tinh" (reduce, then perfect)** — cách Airbnb/NatGeo thành premium. Trang ngắn-mạnh > dài-đều.

## 1. Kiến trúc (components & ranh giới)

| Đơn vị | Trách nhiệm | Phụ thuộc |
|---|---|---|
| `composables/useParallax.ts` (mới) | 1 IntersectionObserver + rAF; gắn `translateY` nhẹ theo scroll cho phần tử opt-in; **no-op khi reduced-motion**; tự huỷ observer onUnmounted | không |
| `components/home/EntityFeature.vue` (mới) | Khối "feature" ảnh-dẫn tái dùng: ảnh lớn + kicker/headline/lede editorial + CTA + 2–3 thumbnail đỡ; prop `side: 'left'\|'right'`, `priority?: boolean` (LCP) | useParallax (dưới fold), EntityCard (thumb) |
| `components/home/StorySpread.vue` (mới) | Section full-bleed tràn viền: ảnh panorama + tiêu đề editorial đè + Ken Burns chậm; **1 lần duy nhất/trang** | useParallax |
| `pages/index.vue` (sửa) | Orchestrate: giữ module mạnh, chèn 2 EntityFeature + 1 StorySpread, cắt/gộp section yếu, thay Cộng đồng | các trên |
| Ảnh hero-grade (mới, ~5–6 file) | `public/img/features/*.webp` (16:9 @1536w) + `public/img/spread/*.webp` (panorama ~2400×1000) — sinh bằng `scripts/gen_image.py` | endpoint ảnh |

**Nguyên tắc isolation:** EntityFeature/StorySpread nhận data qua props (entity + copy), không tự fetch → test/di chuyển độc lập; index.vue chỉ chọn entity + truyền copy.

## 2. Bố cục section-by-section (Checkpoint 2)

Thứ tự dọc mới (giữ ↔ sửa ↔ cắt ↔ mới):

1. **Hero masthead** — GIỮ. **Sửa:** card feature (`hf-card`/heroFeature) đang dùng gradient+icon placeholder → wire `heroFeature.images[0]` (như spotlight đã làm). Gỡ "đảo slop" trong hero.
2. **Mục lục 01–04** — GIỮ nguyên (vừa de-slop).
3. **Lưới tile 6 category** — GIỮ nguyên.
4. **"Đang diễn ra"** (sự kiện feature + mini) — GIỮ; hàng "theo mùa" GIỮ nhưng gọn lại (ảnh thật sau deploy làm nó đẹp lên sẵn).
5. **FEATURE #1 "Trải nghiệm miệt vườn"** — MỚI (`EntityFeature`, ảnh trái): ảnh hero-grade + kicker serif + headline biên tập + lede (drop-cap) + CTA + 3 thumbnail trải nghiệm. Thay cách trình bày experiences kiểu hàng-card.
6. **Spotlight "Nổi bật"** — GIỮ (ảnh thật + quán ngon rating).
7. **STORY SPREAD (full-bleed) — MỚI, khoảnh khắc chữ ký**: 1 `StorySpread` tràn viền, ảnh panorama + tiêu đề chủ đề editorial (vd "Miền sông nước — nơi vườn chạm sông") + Ken Burns chậm + parallax. **Đây là moment duy nhất có chuyển động mạnh.**
8. **FEATURE #2 "Đặc sản OCOP"** — MỚI (`EntityFeature`, ảnh phải): đối xứng feature #1, chủ đề sản phẩm OCOP.
9. **"Đang được quan tâm" (trending)** — CẮT (trùng lặp spotlight/feature). Ghép 3–4 mục hay nhất vào thumbnail của feature.
10. **"Lịch trình gợi ý"** — GIỮ nhưng **slim** (1 dải gọn, giá trị điều hướng thật).
11. **"Từ cộng đồng"** — THAY: hiện đang trống (feed 0 bài). Thay bằng **"Câu chuyện vùng đất"** (module editorial luôn-có-nội-dung: 1 entity/vùng nổi bật + ảnh + narrative). Khi feed cộng đồng CÓ bài → hiện feed; rỗng → hiện câu chuyện. Lấp lỗ hổng bằng thứ on-brand, luôn hiện.
12. **Personalization (recently viewed/saved)** — GIỮ nhưng gọn (client-only, giá trị cá nhân).
13. **Chatbot CTA** — GIỮ gọn.

**Phép trừ ròng:** cắt trending-row + slim itineraries/personalization + thay community → **ít section hơn, nhiều khoảng thở hơn**, 2 feature + 1 spread làm điểm nhấn.

## 3. Hệ giác quan + chiều sâu (chữ ký)

- **Parallax:** `useParallax` gắn cho ảnh trong StorySpread (mạnh) + ảnh EntityFeature (rất nhẹ, ~−6%). Chỉ **dưới fold**. `prefers-reduced-motion` → tắt hẳn (no transform).
- **Ken Burns:** chỉ StorySpread (slow zoom, đã có pattern ở hero).
- **Layering/overlap:** ảnh EntityFeature luồn nhẹ dưới tiêu đề khối kế; caption đè mép ảnh; số/pull-quote đè.
- **Tương phản tỷ lệ:** ảnh feature rất lớn ↔ caption/meta rất nhỏ; headline serif cỡ đại.
- **Kỹ thuật:** transform GPU-cheap; 1 observer dùng chung; không layout-thrash.

## 4. Typography & copy editorial

- Drop-cap trên lede của mỗi EntityFeature (dùng token `--font-editorial` Fraunces sẵn có).
- Pull-quote (đã có vocab trong editorial.css) cho spread/feature khi hợp.
- Caption ảnh có gu (nhỏ, italic serif, muted).
- **Copy viết tay** per feature: kicker + headline + lede (KHÔNG chỉ `entity.name + summary`). Lưu như hằng trong index.vue (data-driven fallback về summary nếu thiếu).

## 5. Ảnh (hero-grade, AI-gen)

Sinh mới bằng `scripts/gen_image.py` (cx/gpt-5.5-image, key từ `.env`), copyright-safe, no text/watermark:
- **~4 ảnh feature 16:9 @1536w** → `public/img/features/{key}.webp` (Pillow→webp ~1200w, quality 82): trải-nghiệm-miệt-vườn, ocop, (dự phòng 2).
- **1–2 ảnh panorama ~2400×1000** → `public/img/spread/{key}.webp` cho StorySpread (srcset: 2400/1600/900).
- Không dùng lại thumbnail card 800w cho feature (sẽ vỡ).

## 6. CWV & hiệu năng

- Ảnh feature ĐẦU (feature #1, gần fold) → `fetchpriority="high"` + preload; còn lại `loading="lazy"`.
- StorySpread panorama: `srcset`/`sizes` responsive; `loading="lazy"` (dưới fold).
- Parallax chỉ dưới fold → không đụng LCP; transform không gây CLS (ảnh có aspect-ratio cố định).
- Ngân sách: tổng ảnh mới < ~600KB (webp). Build CSS route-scoped giữ nguyên.

## 7. Trình tự triển khai (shippable từng bước — §B5)

1. **Step 0 — Deploy 31 ảnh** (pre-check prod-sync → `deploy.sh --frontend --backend --data --replace`, auto pg_dump). Trang +1đ ngay, nền thật.
2. Fix hero placeholder card (wire entity image). Ship.
3. `useParallax.ts` + token. Ship (chưa dùng).
4. `EntityFeature.vue` + sinh ảnh feature + Feature #1. Ship.
5. `StorySpread.vue` + ảnh panorama + spread. Ship.
6. Feature #2 (OCOP). Ship.
7. Cắt trending + slim itineraries/personalization. Ship.
8. Thay Cộng đồng → "Câu chuyện vùng đất". Ship.
9. Typography/copy editorial + polish depth/overlap. Ship.
10. Verify live (chrome MCP): CWV, dark, mobile, reduced-motion, reveal.

## 8. Ngoài phạm vi (YAGNI)

- Scroll-jacking/pin nặng (rủi ro CWV/mobile) — chỉ Ken Burns + parallax nhẹ.
- Footer redesign, các trang khác (chỉ trang chủ đợt này).
- Seeding UGC cộng đồng thật (thay bằng module editorial).
- Bento toàn trang (giữ editorial ảnh-dẫn làm ngôn ngữ chính).

## 9. Tiêu chí nghiệm thu

- Trang chủ: 2 EntityFeature + 1 StorySpread + community-replacement render đúng, cả light/dark, mobile.
- Không còn placeholder gradient+icon ở hero card + các card hàng chính (sau deploy ảnh).
- CWV: LCP không xấu đi (đo lại), CLS ~0, reduced-motion tắt chuyển động.
- Build xanh, deploy gate xanh (home/search=200).
- Cảm quan: nhịp dọc có điểm nhấn (feature/spread) thay vì hàng-card đều; ít section hơn, thoáng hơn.
