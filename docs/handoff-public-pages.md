# Handoff: Session Public Pages (`dev/public-pages`)

> Paste toàn bộ nội dung này làm message đầu tiên trong session Claude Code mới.

---

## Bối cảnh

Bạn đang làm trên nhánh `dev/public-pages` của dự án vinhlong360 — MXH du lịch/OCOP cho Vĩnh Long (3 tỉnh sáp nhập). Solo dev, Nuxt 4 SSR + FastAPI. **Đọc `CLAUDE.md` và `docs/PARALLEL-BRANCHES.md` trước khi bắt đầu.**

## Nhánh hiện tại

```bash
git checkout dev/public-pages
```

## Phạm vi file bạn SỞ HỮU (chỉ sửa các file này)

- `web-nuxt/pages/index.vue`
- `web-nuxt/pages/dia-diem/[id].vue`
- `web-nuxt/pages/du-lich.vue`, `san-pham.vue`, `ocop.vue`
- `web-nuxt/pages/le-hoi.vue`, `su-kien.vue`
- `web-nuxt/pages/ban-do.vue`
- `web-nuxt/pages/lich-trinh/**`, `tao-lich-trinh.vue`
- `web-nuxt/pages/theo-mua.vue`
- `web-nuxt/pages/kham-pha/**`
- `web-nuxt/pages/xa-phuong/[id].vue`, `khu-vuc/[area].vue`
- `web-nuxt/pages/danh-ba.vue`, `tuyen-duong.vue`, `luu-tru.vue`
- `web-nuxt/pages/tim-kiem.vue`
- `web-nuxt/components/EntityCard.vue`
- `web-nuxt/components/KnowBeforeYouGo.vue`
- `agent/public_api.py`, `agent/seo.py` (additive — chỉ thêm, không sửa logic hiện tại)

**KHÔNG SỬA:** `base.css` (trừ thêm class mới), `nuxt.config.ts`, `database.py`, `server.py`, file admin/, file user/auth.

## Công việc

### Tự audit toàn bộ trang công khai (10 tầng):

Audit từng trang theo khung 10 tầng (xem `docs/ke-hoach-hoan-thien-10-tang.md`):
- **T1 Chức năng:** link chết, UI vỡ, tính năng thiếu
- **T2 Dữ liệu:** null-safety, empty states, không bịa
- **T3 UX/UI:** phân cấp, bố cục, tương tác, nhất quán
- **T4 A11y:** contrast, keyboard, ARIA, alt text, target size
- **T5 SEO:** title, meta, canonical, JSON-LD, og:image
- **T6 Performance:** lazy-load, cache, bundle
- **T8 Chịu lỗi:** loading/empty/error states
- **T9 Mobile:** breakpoint, overflow, touch

### Ưu tiên (trang quan trọng nhất):

1. **Homepage (`index.vue`)** — first impression, tối ưu CWV
2. **Entity detail (`dia-diem/[id].vue`)** — trang được visit nhiều nhất
3. **Catalog pages (`du-lich`, `san-pham`, `ocop`)** — discovery flow
4. **Search (`tim-kiem.vue`)** — core UX
5. **Itinerary pages** — differentiator feature

### Gợi ý cụ thể:
- EntityCard: kiểm tra visual consistency across screen sizes
- KnowBeforeYouGo: verify data hiển thị đúng
- Catalog pages: filter/sort UX, load-more feedback
- Map page: fallback khi không có API key
- Seasonal page: verify content rendering by month
- JSON-LD: enrich schema cho từng loại entity (FoodEstablishment, LodgingBusiness, TouristAttraction)

## Lưu ý kỹ thuật

- Entity detail đã rất giàu (KBYG, amenity badges, lightbox, swipe, CTA, JSON-LD) — focus vào polish, không thêm feature mới
- Catalog pages dùng pattern chung: `useAsyncData` + filter + sort + load-more — kiểm tra consistency
- Homepage đã cache backend 2s → tập trung FE optimization
- `§1.4` CHỈ GIỚI THIỆU — CTA chỉ là liên hệ, KHÔNG booking/thanh toán

## Verify

```bash
python -m pytest -q                    # backend xanh
cd web-nuxt && npm run build           # FE build OK
```

## Commit convention

```
[public] mô tả ngắn

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
