# Nền tảng UI và shell vinhlong360 — Kế hoạch triển khai

> STATUS: implementation and verification complete - đã triển khai và kiểm chứng local ngày 2026-07-28; chờ tích hợp.
>
> **Kết quả kiểm chứng:** contract `14/14`, full frontend `926/926`, Nuxt typecheck và production build đều pass. Browser QA trên production artifact đã kiểm tra 375/768/1024/1440px, năm route public, light/dark, region persistence, catalog/drawer, focus return và console health. Hai route Admin redirect về `/?login=admin` đúng middleware; drawer/command palette Admin được kiểm chứng bằng integration test.
>
> **Sai khác quy trình đã duyệt:** do agent service không khả dụng, người dùng cho phép controller-side implementation. Các task được gom vào một commit P0 có allowlist thay vì một commit riêng cho từng task; phạm vi homepage Adaptive Feed P1 và ba file user-owned vẫn được loại khỏi stage.
>
> **Kỹ năng bắt buộc khi thực thi:** `superpowers:executing-plans`, `superpowers:test-driven-development`, `frontend-design:frontend-design`, `designing-ui-foundations`, `design-system`, `build-web-apps:frontend-app-builder`, `build-web-apps:frontend-testing-debugging` và `superpowers:verification-before-completion`.

**Mục tiêu:** Xây nền tảng giao diện Mekong Signal Atlas và nâng cấp hai shell public/AdminCP trước khi thiết kế lại từng trang, đồng thời giữ nguyên route, API, SEO, auth, RBAC và hành vi nghiệp vụ hiện tại.

**Kiến trúc:** Thực hiện chuyển đổi tương thích thay vì thay toàn bộ CSS một lần. Token mới được thêm theo chuỗi primitive → semantic → component và tiếp tục cấp alias cũ để các trang chưa di trú vẫn hoạt động. Public shell thêm thanh ngữ cảnh địa bàn, điều hướng tác vụ và bottom navigation mobile. Admin shell chuyển sang điều hướng theo workstream, cấu hình bằng dữ liệu, icon SVG thống nhất và mật độ cao. CSS shell mới được cô lập trong `assets/css/shell.css`; style page cũ chưa bị sửa trong giai đoạn P0.

**Tech stack:** Nuxt 4, Vue 3, TypeScript, CSS thuần, `@nuxt/fonts`, Vitest + happy-dom.

## Ràng buộc toàn cục

- Nguồn thiết kế: `design-system/vinhlong360/MASTER.md`; public shell kế thừa `design-system/vinhlong360/pages/home.md`; Admin shell kế thừa `design-system/vinhlong360/pages/admin-dashboard.md`.
- Không thêm React, shadcn, marketplace, booking hoặc thanh toán.
- Không đổi URL, middleware, API call, session handling, polling badge hoặc command palette.
- Không dùng emoji/HTML numeric entity làm icon cấu trúc trong hai shell.
- Glass chỉ dùng cho chrome; content surface opaque, border-first, shadow tối thiểu.
- Be Vietnam Pro là font UI/body/Admin; Fraunces chỉ còn vai trò editorial.
- Mọi action tương tác có hit area tối thiểu 44px, focus-visible rõ, reduced-motion và forced-colors hợp lệ.
- Giữ nguyên các file chưa theo dõi `agent/knowledge.db-shm`, `agent/knowledge.db-wal`, `docs/page-inventory-design-scope-2026-07-27.md`.
- Mỗi task là một commit nhỏ; không gộp trang chủ, `/du-lich`, entity detail hoặc Admin dashboard vào P0.

---

### Task 1: Khóa contract UI bằng test hồi quy

**Files:**
- Create: `web-nuxt/tests/ui-foundation-shell.test.ts`

**Interfaces cần bảo vệ:**
- `IconLine` render SVG thật cho icon shell/Admin và có fallback an toàn.
- Public context selector thay đổi `useRegionPref` và persistence thật.
- Bottom navigation đánh dấu đúng route hiện tại bằng `aria-current`.
- Bộ phân giải navigation Admin xử lý exact route, prefix route và query `kind`.
- Token/font/CSS được kiểm chứng qua computed style và browser QA, không dùng source-grep test chỉ phát hiện thay đổi văn bản.

- [ ] **Step 1: Viết test fail** — tạo test hành vi bằng `mountSuspended` và pure-function test:
  - Mount `IconLine` với `menu`, `layout-dashboard`, `panel-left-open`; mỗi trường hợp phải có SVG; tên lạ phải render fallback `circle-help`.
  - Mount `PublicContextBar`, đổi select sang `ben-tre`; label đổi thành `Bến Tre` và `localStorage['vl360-region-pref'] === 'ben-tre'`.
  - Mount `PublicBottomNav` ở route `/ban-do`; có đúng 5 link và link `/ban-do` mang `aria-current="page"`.
  - `isAdminNavItemActive` đúng với `/admin`, prefix `/admin/cai-dat/seo` và query `kind=product`; `resolveAdminPageLabel` trả nhãn không chứa emoji.
- [ ] **Step 2: Chạy để thấy fail** — `cd web-nuxt; npm test -- --run tests/ui-foundation-shell.test.ts` → FAIL đúng vì icon/hành vi/module mới chưa tồn tại.
- [ ] **Step 3: Commit test đỏ** — `git add web-nuxt/tests/ui-foundation-shell.test.ts && git commit -m "<UI-P0.1> test: khóa contract nền tảng và shell"`.

### Task 2: Nâng token và typography theo Mekong Signal Atlas

**Files:**
- Modify: `web-nuxt/assets/css/variables.css`
- Modify: `web-nuxt/nuxt.config.ts`
- Test: `web-nuxt/tests/ui-foundation-shell.test.ts`

**Interfaces tạo ra:**

```css
/* Primitive */
--alluvial-paper; --surface-white; --mekong-ink; --mekong-muted;
--river-600; --river-700; --mangthit-600; --mangthit-700;
--orchard-600; --harvest-600; --coral-error; --alluvial-line;

/* Semantic */
--color-canvas; --color-surface; --color-surface-subtle; --color-surface-raised;
--color-text; --color-text-muted; --color-border; --color-action;
--color-action-hover; --color-brand; --color-focus;
--color-success; --color-warning; --color-error;
--color-source-official; --color-source-verified; --color-source-community;

/* Component */
--radius-control: 8px;
--radius-surface: 12px;
--radius-sheet: 20px;
--shell-public-header-height;
--shell-admin-sidebar-width;
--shell-admin-sidebar-collapsed-width;
```

- [ ] **Step 1: Implement sRGB fallback** — thêm primitive/semantic/component token mới ở đầu `:root`, sau đó ánh xạ alias cũ (`--bg`, `--card`, `--ink`, `--muted`, `--line`, `--primary`, `--secondary`, `--error`) sang semantic mới. Không xóa token legacy vì các page chưa di trú vẫn dùng.
- [ ] **Step 2: Implement OKLCH override** — thêm `@supports (color: oklch(0% 0 0)) { :root { ... } }`; màu dark mode có override riêng, không đảo màu máy móc.
- [ ] **Step 3: Font UI** — trong `nuxt.config.ts`, thay family Inter bằng `Be Vietnam Pro`, weights `[400, 500, 600, 700]`, subsets `vietnamese/latin/latin-ext`; đổi `--font-sans` sang `'Be Vietnam Pro'` với fallback hệ thống. Giữ các preload Fraunces hiện tại cho editorial.
- [ ] **Step 4: Test pass phần token/font** — `cd web-nuxt; npm test -- --run tests/ui-foundation-shell.test.ts` → chỉ còn fail ở icon và shell.
- [ ] **Step 5: Typecheck** — `cd web-nuxt; npm run typecheck` → không có lỗi mới.
- [ ] **Step 6: Commit** — `git add web-nuxt/assets/css/variables.css web-nuxt/nuxt.config.ts && git commit -m "<UI-P0.2> feat: token và typography Mekong Signal Atlas"`.

### Task 3: Mở rộng family icon SVG dùng chung

**Files:**
- Modify: `web-nuxt/components/IconLine.vue`
- Modify: `web-nuxt/utils/adminKinds.ts`
- Test: `web-nuxt/tests/ui-foundation-shell.test.ts`

**Interfaces tạo ra:**
- `IconLine` tiếp tục nhận prop `name: string`, render SVG nội bộ `stroke-width="1.75"`, round cap/join và `currentColor`.
- `KindDef` thêm `icon: string`; giữ `emoji` tạm thời cho các page legacy, nhưng hai shell mới chỉ dùng `icon`.
- Icon shell/Admin bắt buộc: `menu`, `chevron-down`, `search`, `locate`, `alert-triangle`, `layout-dashboard`, `chart`, `clipboard-list`, `shield-check`, `images`, `users`, `flag`, `flask`, `bot`, `file-text`, `settings`, `arrow-left`, `panel-left-close`, `panel-left-open`, `route`, `database`, `wand`, `briefcase`.

- [ ] **Step 1: Bổ sung icon** — thêm SVG path vào `ICONS`; không thêm package icon ngoài và không dùng emoji fallback.
- [ ] **Step 2: Bổ sung icon kind** — ánh xạ 9 `ADMIN_KINDS` sang icon có sẵn: `landmark`, `sprout`, `fruit`, `bowl`, `home`, `calendar`, `building`, `user`, `pin`.
- [ ] **Step 3: Empty fallback an toàn** — icon không tồn tại trả SVG `circle-help` hoặc không render với `aria-hidden`, không hiện ký tự lạ.
- [ ] **Step 4: Test** — chạy test contract; phần icon phải xanh.
- [ ] **Step 5: Commit** — `git add web-nuxt/components/IconLine.vue web-nuxt/utils/adminKinds.ts && git commit -m "<UI-P0.3> feat: mở rộng family icon SVG thống nhất"`.

### Task 4: Public shell — ngữ cảnh địa bàn, task navigation và mobile bottom nav

**Files:**
- Create: `web-nuxt/components/shell/PublicContextBar.vue`
- Create: `web-nuxt/components/shell/PublicBottomNav.vue`
- Create: `web-nuxt/assets/css/shell.css`
- Modify: `web-nuxt/layouts/default.vue`
- Modify: `web-nuxt/nuxt.config.ts`
- Test: `web-nuxt/tests/ui-foundation-shell.test.ts`

**Interfaces và hành vi:**
- `PublicContextBar` dùng `useRegionPref()` và `AREA_META`; label mặc định `Vĩnh Long · Bến Tre · Trà Vinh`, cho phép chọn `Tất cả khu vực`, `Vĩnh Long`, `Bến Tre`, `Trà Vinh`; không tự xin quyền vị trí ở P0.
- Desktop primary nav: `Trang chủ`, `Khám phá`, `Gần bạn`, `Cộng đồng`, `Lịch trình`; nhóm danh mục sâu tiếp tục dùng `navigation.nav_groups` từ CMS trong mega panel.
- Mobile bottom nav tối đa 5 mục: `/`, `/du-lich`, `/ban-do`, `/cong-dong`, `/tai-khoan`; active state có icon + chữ và `aria-current="page"`.
- Search/autocomplete, auth modal, notification, user menu, theme toggle, focus trap mobile nav và route-focus giữ nguyên.

- [ ] **Step 1: Context bar** — tạo component với nút chọn khu vực, popover native-accessible, click-outside/Escape, label `Khu vực đang ưu tiên`; ghi lựa chọn qua `setRegion`.
- [ ] **Step 2: Bottom nav** — tạo component data-driven dùng `IconLine`, ẩn desktop, chừa safe-area và không che content/footer.
- [ ] **Step 3: Refactor layout** — chia header thành context row + command row + task row; thay caret Unicode bằng `IconLine name="chevron-down"`; dùng `IconLine name="menu"` cho mobile toggle; giữ toàn bộ state/function hiện hữu.
- [ ] **Step 4: Footer** — bỏ gradient “phù sa” trang trí và serif ở mọi heading; chuyển thành colophon border-first, Be Vietnam Pro, chỉ giữ Fraunces cho một tagline editorial nếu cần.
- [ ] **Step 5: Shell CSS** — thêm `shell.css` sau `base.css` trong `nuxt.config.ts`; dùng class prefix `.public-shell-*`/`.public-bottom-nav`; desktop, 1024px, 768px, 375px; `prefers-reduced-motion`, `prefers-contrast: more`, forced-colors.
- [ ] **Step 6: Test và smoke** — test contract xanh phần public; mount `/` ở dev server, xác nhận không horizontal overflow và keyboard dùng được.
- [ ] **Step 7: Commit** — `git add web-nuxt/components/shell web-nuxt/assets/css/shell.css web-nuxt/layouts/default.vue web-nuxt/nuxt.config.ts && git commit -m "<UI-P0.4> feat: public shell theo ngữ cảnh địa bàn"`.

### Task 5: Admin shell — bàn điều phối theo workstream

**Files:**
- Create: `web-nuxt/utils/adminNavigation.ts`
- Modify: `web-nuxt/layouts/admin.vue`
- Modify: `web-nuxt/assets/css/shell.css`
- Test: `web-nuxt/tests/ui-foundation-shell.test.ts`

**Interfaces tạo ra:**

```ts
export interface AdminNavItem {
  id: string
  label: string
  to: string | { path: string; query?: Record<string, string> }
  icon: string
  badge?: 'moderation' | 'images' | 'unclassified' | 'provisional' | 'reports'
  children?: AdminNavItem[]
}

export interface AdminNavGroup {
  id: 'overview' | 'content' | 'community' | 'system'
  label: string
  items: AdminNavItem[]
}

export const ADMIN_NAV_GROUPS: AdminNavGroup[]
export const ADMIN_PAGE_LABELS: Record<string, string>
```

- [ ] **Step 1: Navigation config** — chuyển toàn bộ nhóm/link hiện có sang `adminNavigation.ts`; entity subnav lấy `ADMIN_KINDS` và `kind.icon`; route và badge key giữ nguyên.
- [ ] **Step 2: Template data-driven** — render groups/items bằng vòng lặp; icon bằng `IconLine`; active matcher hỗ trợ route exact, route prefix và query `kind`; breadcrumb dùng `ADMIN_PAGE_LABELS` và không chèn emoji.
- [ ] **Step 3: Workstream context** — topbar hiển thị breadcrumb, label scope hiện tại, nút command palette hint; sidebar footer hiển thị người dùng, role, về trang chủ và theme toggle bằng icon.
- [ ] **Step 4: Responsive** — desktop sidebar 272px/collapse 76px; mobile chuyển thành off-canvas task drawer có nút mở rõ ràng, không biến toàn bộ navigation thành dải chip ngang. Main content giữ `min-width: 0`; bảng hiện tại tiếp tục tự scroll.
- [ ] **Step 5: CSS cleanup** — bỏ style hover `translate/scale` cho mọi nav row, bỏ gradient/shadow card mặc định trong shell, dùng border/status rail và chỉ shadow cho drawer/popover/sticky chrome.
- [ ] **Step 6: Giữ hành vi** — `loadBadges`, polling 60 giây, visibility refresh, `fetchMe`, theme state, error boundary, command palette, toast và confirm không đổi.
- [ ] **Step 7: Test** — contract test toàn bộ phải xanh; thêm assert không có `&#` và không có `k.emoji` trong `layouts/admin.vue`.
- [ ] **Step 8: Commit** — `git add web-nuxt/utils/adminNavigation.ts web-nuxt/layouts/admin.vue web-nuxt/assets/css/shell.css && git commit -m "<UI-P0.5> feat: admin shell theo workstream vận hành"`.

### Task 6: Kiểm chứng tích hợp và cổng nghiệm thu P0

**Files:**
- Modify khi cần: các file P0 ở Task 2–5, chỉ để sửa lỗi kiểm thử.

- [ ] **Step 1: Test mục tiêu** — `cd web-nuxt; npm test -- --run tests/ui-foundation-shell.test.ts` → pass.
- [ ] **Step 2: Regression test** — `cd web-nuxt; npm test` → pass hoặc ghi rõ lỗi baseline không liên quan; P0 không làm tăng lỗi.
- [ ] **Step 3: Typecheck** — `cd web-nuxt; npm run typecheck` → pass.
- [ ] **Step 4: Production build** — `cd web-nuxt; npm run build` → pass và manifest launch readiness được sinh thành công.
- [ ] **Step 5: Kiểm tra trình duyệt** — `/`, `/du-lich`, `/dia-diem`, `/cong-dong`, `/tai-khoan`, `/admin`, `/admin/entities?kind=product` tại 375, 768, 1024, 1440px; light/dark; keyboard; 200% zoom; reduced motion.
- [ ] **Step 6: Audit định lượng** — hai layout không còn emoji structural/numeric entity; font/UI token đúng; bottom nav không che nội dung; Admin mobile drawer không làm mất route nào.
- [ ] **Step 7: Commit sửa tích hợp nếu có** — `git add <chỉ file P0> && git commit -m "<UI-P0.6> fix: hoàn thiện kiểm chứng shell responsive"`.

## Ngoài phạm vi P0

- Thiết kế lại nội dung trang chủ `/` thành bảng tin địa phương thích ứng.
- Thiết kế lại `/du-lich`, `/dia-diem/[id]` và `/admin` dashboard.
- Xin quyền geolocation, suy luận IP, cá nhân hóa feed hoặc API “Vì sao bạn thấy nội dung này”. P0 chỉ tạo chỗ hiển thị/ngữ cảnh và tái dùng `useRegionPref` hiện có.
- Di trú toàn bộ 54 file còn emoji structural và toàn bộ CSS legacy. Các phần này được xử lý theo từng layout family sau pilot.

## Trình tự tiếp theo sau P0

1. `docs/superpowers/plans/2026-07-28-vinhlong360-home-adaptive-feed.md`
2. `docs/superpowers/plans/2026-07-28-vinhlong360-du-lich-ui.md`
3. `docs/superpowers/plans/2026-07-28-vinhlong360-entity-detail-ui.md`
4. `docs/superpowers/plans/2026-07-28-vinhlong360-admin-operations-dashboard.md`
