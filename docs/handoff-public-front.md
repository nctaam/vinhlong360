# Session 1: Public Front — Homepage + Catalog + Static

> Paste toàn bộ nội dung này làm message đầu tiên.

## Bối cảnh

Bạn đang làm trong **worktree** `C:/Code/vinhlong360/vl360-public-front`, nhánh `dev/public-front`. Dự án vinhlong360 — MXH du lịch/OCOP cho 3 tỉnh sáp nhập (VL+BT+TV). Solo dev, Nuxt 4 SSR + FastAPI.

**Đọc `CLAUDE.md` và `docs/PARALLEL-BRANCHES.md` trước khi bắt đầu.**

## Phạm vi file SỞ HỮU (CHỈ sửa các file này)

**Pages:**
- `web-nuxt/pages/index.vue` — Homepage
- `web-nuxt/pages/du-lich.vue` — Catalog du lịch
- `web-nuxt/pages/san-pham.vue` — Catalog sản phẩm
- `web-nuxt/pages/ocop.vue` — Catalog OCOP
- `web-nuxt/pages/le-hoi.vue` — Lễ hội
- `web-nuxt/pages/su-kien.vue` — Sự kiện
- `web-nuxt/pages/theo-mua.vue` — Theo mùa
- `web-nuxt/pages/gioi-thieu.vue` — Giới thiệu
- `web-nuxt/pages/lien-he.vue` — Liên hệ
- `web-nuxt/pages/chinh-sach-bao-mat.vue` — Chính sách
- `web-nuxt/pages/dieu-khoan-su-dung.vue` — Điều khoản
- `web-nuxt/pages/huong-dan-thanh-vien.vue` — Hướng dẫn
- `web-nuxt/pages/[...slug].vue` — Catch-all

**Components:**
- `EntityCard.vue`, `CatalogSpotlight.vue`, `CategoryIcon.vue`
- `HeroIllustration.vue`, `AreaCard.vue`, `AreaIllustration.vue`
- `CountUp.vue`, `JourneyBar.vue`, `WeatherBar.vue`
- `KnowBeforeYouGo.vue`

**KHÔNG SỬA:** base.css, nuxt.config.ts, layouts/, composables/, server.py, agent/*.py, admin/**, user pages.

## Công việc — Audit 10 tầng

Audit từng trang theo khung 10 tầng (`docs/ke-hoach-hoan-thien-10-tang.md`):

| Tầng | Kiểm tra |
|------|----------|
| T1 Chức năng | Link chết, UI vỡ, tính năng thiếu |
| T2 Dữ liệu | Null-safety, empty states, không bịa |
| T3 UX/UI | Phân cấp, bố cục, nhất quán, phản hồi |
| T4 A11y | Contrast, keyboard, ARIA, alt text, target ≥44px |
| T5 SEO | title, meta, canonical, JSON-LD, og:image |
| T6 Performance | Lazy-load, cache, bundle |
| T8 Chịu lỗi | Loading/empty/error states |
| T9 Mobile | Breakpoint, overflow, touch |

**Ưu tiên:**
1. **Homepage** (`index.vue`) — first impression, CWV
2. **Catalog pages** (`du-lich`, `san-pham`, `ocop`) — discovery flow
3. **EntityCard** — component dùng khắp nơi
4. **Static pages** — pháp lý, giới thiệu

**Lưu ý:**
- §1.4: CHỈ GIỚI THIỆU — CTA chỉ liên hệ, KHÔNG booking/thanh toán
- Homepage đã cache backend 2s → tập trung FE optimization
- 3 tỉnh sáp nhập → trình bày theo chủ đề, KHÔNG chia 3 vùng

## Verify

```bash
python -m pytest -q
cd web-nuxt && npm run build
```

## Commit prefix: `[public-front]`
