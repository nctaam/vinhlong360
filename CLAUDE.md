# SESSION SCOPE: Frontend UI/UX — branch `session-fe`

> **Session song song 1/3.** CHỈ sửa file trong `web-nuxt/`. KHÔNG sửa `agent/`, `scripts/`, `docs/`, `tests/`, `web/`, config gốc.
> Sau khi xong, session gốc sẽ merge + deploy. KHÔNG tự push/merge.

---

## 0. Bối cảnh

MXH du lịch/OCOP/cộng đồng cho Vĩnh Long mới (VL+Bến Tre+Trà Vinh). Solo dev, budget <1tr/th, web-first.
Backend FastAPI (`agent/`) + Nuxt 4 SSR (`web-nuxt/`). Kiến trúc: `docs/architecture-decisions.md`.

## 1. Giới hạn file (TUYỆT ĐỐI — vi phạm = hỏng merge)

**ĐƯỢC sửa:**
- `web-nuxt/pages/**`
- `web-nuxt/components/**`
- `web-nuxt/composables/**`
- `web-nuxt/layouts/**`
- `web-nuxt/assets/**`
- `web-nuxt/plugins/**`
- `web-nuxt/middleware/**`
- `web-nuxt/public/**`
- `web-nuxt/app.vue`
- `web-nuxt/error.vue`

**KHÔNG ĐƯỢC sửa:**
- `web-nuxt/nuxt.config.ts` — chung, dễ conflict
- `web-nuxt/package.json` — KHÔNG thêm dependency (dùng cái đã có)
- `agent/**` — session backend phụ trách
- `scripts/**`, `docs/**`, `tests/**` — session khác
- `web/data.json` — DỮ LIỆU GỐC, TUYỆT ĐỐI KHÔNG SỬA
- File root: `CLAUDE.md` gốc, `docker-compose.yml`, `.env.example`

## 2. Bất biến

- **B5.** Mỗi commit để lại build pass (`cd web-nuxt && npm run build`)
- **B8.** Không thêm dependency trả phí, không thêm package mới
- KHÔNG thêm Tailwind/UI library — giữ CSS thuần + tokens hiện tại
- KHÔNG gợi ý AR, audio guide, native app
- CTA chỉ liên hệ Zalo/điện thoại — KHÔNG form đặt hàng/booking (§1.4)
- Vue auto-escape `{{ }}` → không cần escape UGC thủ công

## 3. Commit

- Branch: `session-fe` (đã checkout)
- Format: `[FE] <mô tả ngắn>`
- Commit nhỏ, 1 feature/fix = 1 commit
- **KHÔNG push, KHÔNG merge vào main**

## 4. Verify mỗi commit

```powershell
cd C:\Code\vinhlong360\vl360-session-fe\web-nuxt
npm run build
```

## 5. Danh sách task (làm theo thứ tự, tick [x] khi xong)

### Nhóm 1: Accessibility (ưu tiên cao nhất)
- [ ] **FE-1** Clickable `<div @click>` → `<button>` hoặc `<NuxtLink>` toàn bộ pages + components. Đảm bảo keyboard accessible.
- [ ] **FE-2** Focus visible — mọi interactive element có `:focus-visible` outline rõ ràng.
- [ ] **FE-3** Alt text cho `<img>` — rà toàn bộ, thêm alt mô tả (dùng entity name/title).
- [ ] **FE-4** Skip navigation link — "Chuyển đến nội dung chính" ẩn ở layout, hiện khi Tab.
- [ ] **FE-5** ARIA landmarks — `<header>`, `<main>`, `<nav>`, `<footer>` semantic đúng.

### Nhóm 2: UI/UX trải nghiệm
- [ ] **FE-6** Empty states — `/cong-dong`, `/lich-trinh`, `/theo-mua`, `/danh-ba` khi không có data: thêm illustration/icon + message hướng dẫn.
- [ ] **FE-7** Loading states — mọi trang dùng `useAsyncData`/`useFetch` có skeleton/spinner thống nhất (component `LoadingSkeleton.vue`).
- [ ] **FE-8** Error states — API fail hiện message thân thiện + nút thử lại, không raw error.
- [ ] **FE-9** Mobile responsive — kiểm `/du-lich`, `/san-pham`, `/cong-dong`, trang chi tiết trên 375px. Fix overflow, font, spacing.
- [ ] **FE-10** Dark mode consistency — mọi component dùng CSS variable, không hardcode màu. Fix chỗ bị trắng/đen lạc.

### Nhóm 3: Component cải thiện
- [ ] **FE-11** PostCard — image preview (nếu post có images), truncate long content, time relative ("2 giờ trước").
- [ ] **FE-12** EntityCard — subtle hover effect + focus ring. Card là semantic link.
- [ ] **FE-13** SearchBar — debounce input, dropdown suggestions, keyboard nav (arrow keys + Enter).
- [ ] **FE-14** Toast/notification — component nhẹ cho feedback (đã lưu, đã báo cáo...) thay `alert()`.
- [ ] **FE-15** Pagination — thống nhất: visual feedback loading more, scroll behavior.

### Nhóm 4: Admin pages polish (FE only)
- [ ] **FE-16** Admin entity editor — character counter cho summary, better form layout.
- [ ] **FE-17** Admin moderation — content preview modal lớn (full post + images + author context).
- [ ] **FE-18** Admin responsive — sidebar collapse mobile, table horizontal scroll.
- [ ] **FE-19** Command palette (Ctrl+K) — quick nav + entity search, mount ở admin layout.

### Nhóm 5: Performance
- [ ] **FE-20** Lazy images — `loading="lazy"` cho images below fold.
- [ ] **FE-21** Code splitting — lazy import heavy components (Map modal, editor).
- [ ] **FE-22** CSS cleanup — remove unused rules, consolidate duplicates (KHÔNG xóa token variables).

### Nhóm 6: Cross-cutting FE (consume endpoints BE session tạo)
> Ghi chú: Các task này dùng endpoint mà session BE sẽ tạo. Nếu endpoint chưa có, code FE PHẢI
> degrade gracefully (check response, fallback UI). Không bị block — FE hoạt động dù BE chưa merge.

- [ ] **FE-23** Avatar display — sửa `PostCard.vue`, `nguoi-dung/[id].vue`, comment list: nếu user có `avatar_url` thì hiện ảnh, không thì dùng `AvatarPlaceholder.vue` hiện tại. Nhất quán toàn site.
- [ ] **FE-24** Avatar upload form — thêm vào `/cai-dat` tab Hồ sơ: file input + preview + gọi `POST /auth/avatar`. Fallback: ẩn nếu endpoint trả 404.
- [ ] **FE-25** Notification bell — component `NotificationBell.vue` ở nav (layout chính): badge đỏ + dropdown 5 item gần nhất. Dùng `useNotifications.ts` polling đã có.
- [ ] **FE-26** Notification preferences — toggle switches per type (like/comment/mention/follow) trong `/cai-dat` tab Thông báo. Gọi `GET/PUT /api/notification-preferences`. Fallback: ẩn tab nếu 404.
- [ ] **FE-27** Image responsive — entity có `images` array: hiển thị ảnh chính + gallery nhỏ ở trang chi tiết. `srcset`/`sizes` cho responsive. `loading="lazy"` cho ảnh phụ.
- [ ] **FE-28** og:image per entity — sửa `useSeo.ts`: nếu entity có image, dùng làm `og:image` thay default. Fallback: giữ default site image.

## 6. Lưu ý kỹ thuật

- Đọc `agent/public_api.py` hoặc `agent/admin.py` để hiểu API response shape, nhưng KHÔNG sửa.
- Design tokens: `assets/css/tokens.css` hoặc `base.css`.
- Hệ màu: `--color-vinh-long`, `--color-ben-tre`, `--color-tra-vinh`.
- Khi tạo component mới, đặt trong `components/` với tên PascalCase.
- Admin pages ở `pages/admin/`.
