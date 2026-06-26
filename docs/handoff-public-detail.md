# Session 2: Public Detail — Entity Detail + Ward/Area + Directory

> Paste toàn bộ nội dung này làm message đầu tiên.

## Bối cảnh

Worktree `C:/Code/vinhlong360/vl360-public-detail`, nhánh `dev/public-detail`. Dự án vinhlong360 — MXH du lịch/OCOP cho 3 tỉnh sáp nhập. **Đọc `CLAUDE.md` + `docs/PARALLEL-BRANCHES.md`.**

## Phạm vi file SỞ HỮU

**Pages:**
- `web-nuxt/pages/dia-diem/[id].vue` — Entity detail (trang quan trọng nhất)
- `web-nuxt/pages/dia-diem/index.vue` — Entity listing
- `web-nuxt/pages/xa-phuong/[id].vue` — Ward page
- `web-nuxt/pages/khu-vuc/[area].vue` — Area page
- `web-nuxt/pages/danh-ba.vue` — Danh bạ hành chính
- `web-nuxt/pages/tuyen-duong.vue` — Tuyến đường
- `web-nuxt/pages/luu-tru.vue` — Lưu trú

**Components:**
- `NearbyEntities.vue`, `EntityFeed.vue`, `EntityReviews.vue`
- `ImageGallery.vue`, `ShareButton.vue`, `SaveButton.vue`
- `Breadcrumb.vue`

**Backend (additive only):**
- `agent/public_api.py` — chỉ thêm endpoint mới

**KHÔNG SỬA:** EntityCard.vue (thuộc public-front), base.css, layouts/, admin/**, user pages.

## Công việc — Audit 10 tầng

**Ưu tiên:**
1. **Entity detail** (`dia-diem/[id].vue`) — trang được visit nhiều nhất
   - JSON-LD: enrich theo entity type (FoodEstablishment, LodgingBusiness, TouristAttraction)
   - Lightbox/swipe/gallery UX
   - KBYG (Know Before You Go) data accuracy
   - CTA: liên hệ Zalo/điện thoại (§1.4 — KHÔNG booking)
2. **Ward page** — summary, sản phẩm, entity list
3. **Directory pages** — danh-ba, tuyen-duong, luu-tru

**Kiểm tra:**
- T1: Chức năng hoạt động đúng
- T2: Null-safety, empty states cho entity thiếu data
- T3: Phân cấp heading, breadcrumb, CTA rõ ràng
- T4: ARIA landmark, alt text ảnh, keyboard nav gallery
- T5: JSON-LD enrichment, canonical, og:image
- T8: Loading/error/empty states
- T9: Mobile layout, touch target

## Verify

```bash
python -m pytest -q
cd web-nuxt && npm run build
```

## Commit prefix: `[public-detail]`
