# Parallel Branch Strategy — vinhlong360

> Tạo 2026-06-26. 3 nhánh dev song song, mỗi nhánh = 1 session Claude Code riêng.
> **Merge flow:** branch → main (sau khi build+test xanh). KHÔNG merge chéo giữa dev branches.

---

## Quy tắc chung cho TẤT CẢ session

1. **Đọc `CLAUDE.md` trước** — mọi bất biến §2 vẫn áp dụng.
2. **Không sửa file chung** trừ khi được ghi rõ ở đây:
   - `base.css` — chỉ **thêm** class mới (không sửa/xoá class hiện tại)
   - `nuxt.config.ts` — KHÔNG sửa
   - `database.py` — chỉ nhánh cần migration mới sửa, additive-only
   - `server.py` — KHÔNG sửa (dùng router riêng)
3. **Build + test trước merge:** `python -m pytest -q` + `cd web-nuxt && npm run build`
4. **Commit message prefix:** `[admincp]`, `[usercp]`, `[public]`

---

## Branch 1: `dev/admincp` — AdminCP & CMS

**Phạm vi file SỞ HỮU (chỉ nhánh này được sửa):**
- `web-nuxt/pages/admin/**` (trừ `admin/index.vue` dashboard — shared)
- `web-nuxt/layouts/admin.vue`
- `web-nuxt/components/CommandPalette.vue`
- `agent/admin.py` (additive: thêm endpoint, không sửa endpoint hiện tại)

**Công việc từ deep upgrade plan:**
- [ ] **B2e** Rich summary editor — character counter + markdown preview toggle trong entity editor
- [ ] **B7b** Bulk relationship add — `POST /admin/relationships/bulk` + textarea UI
- [ ] **B8c** Contextual help tooltips — CSS-only `?` icons cạnh data quality, moderation status

**Polish thêm (tự audit):**
- Admin entity editor UX improvements
- Moderation workflow optimizations
- Media library filters/sort
- Dashboard widget improvements

---

## Branch 2: `dev/usercp` — User System & Cộng đồng

**Phạm vi file SỞ HỮU:**
- `web-nuxt/pages/cai-dat.vue`
- `web-nuxt/pages/cong-dong.vue`
- `web-nuxt/pages/nguoi-dung/[id].vue`
- `web-nuxt/pages/bai-viet/[id].vue`
- `web-nuxt/pages/thong-bao.vue`
- `web-nuxt/components/PostCard.vue`
- `web-nuxt/components/NotificationBell.vue`
- `web-nuxt/components/AuthModal.vue`
- `web-nuxt/composables/useNotifications.ts`
- `agent/social.py`, `agent/auth.py`, `agent/notifications.py` (additive)

**Công việc từ deep upgrade plan:**
- [ ] **A2d** Notification preferences — migration table + toggle switches per type (like/comment/mention/follow) + gate trong `create_notification`

**Polish thêm (tự audit):**
- Profile page UX improvements
- Community feed performance
- Settings page completeness
- Notification UX polish
- Comment/reply interaction improvements

---

## Branch 3: `dev/public-pages` — Trang công khai & SEO

**Phạm vi file SỞ HỮU:**
- `web-nuxt/pages/index.vue`
- `web-nuxt/pages/dia-diem/[id].vue`
- `web-nuxt/pages/du-lich.vue`
- `web-nuxt/pages/san-pham.vue`
- `web-nuxt/pages/ocop.vue`
- `web-nuxt/pages/le-hoi.vue`, `su-kien.vue`
- `web-nuxt/pages/ban-do.vue`
- `web-nuxt/pages/lich-trinh/**`
- `web-nuxt/pages/tao-lich-trinh.vue`
- `web-nuxt/pages/theo-mua.vue`
- `web-nuxt/pages/kham-pha/**`
- `web-nuxt/pages/xa-phuong/[id].vue`, `khu-vuc/[area].vue`
- `web-nuxt/pages/danh-ba.vue`, `tuyen-duong.vue`, `luu-tru.vue`
- `web-nuxt/pages/tim-kiem.vue`
- `web-nuxt/components/EntityCard.vue`
- `web-nuxt/components/KnowBeforeYouGo.vue`
- `agent/public_api.py`, `agent/seo.py` (additive)

**Công việc:**
- Catalog page UX polish (du-lich, san-pham, ocop)
- Entity detail page improvements
- Homepage optimization
- SEO: JSON-LD enrichment, og:image improvements
- Search page UX
- Map page improvements
- Itinerary pages polish

---

## Merge order (recommended)

1. `dev/public-pages` → main (ít conflict nhất, trang public ko chạm user/admin)
2. `dev/usercp` → main
3. `dev/admincp` → main

Nếu conflict: resolve bằng cách giữ CẢ HAI thay đổi (additive-first §B2).

---

## Cách mở session mới

```bash
# Session 1 (AdminCP)
git checkout dev/admincp

# Session 2 (UserCP)
git checkout dev/usercp

# Session 3 (Public pages)
git checkout dev/public-pages
```

Paste handoff prompt tương ứng (bên dưới) vào session mới.
