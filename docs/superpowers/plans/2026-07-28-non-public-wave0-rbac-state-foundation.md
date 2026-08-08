> STATUS: done — plan cho `codex/non-public-wave0`, đã hợp vào `main` ngày 2026-08-08
> (merge `8593e89a`). Giữ lại làm hồ sơ; các bước trong đây đã thực hiện xong.

# Non-public Wave NP-0 RBAC and State Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép đúng actor truy cập đúng AdminCP surface bằng scope backend và cung cấp state component dùng chung cho các wave non-public tiếp theo.

**Architecture:** Backend sở hữu mapping role/scope trong module độc lập và xuất scope đã chuẩn hóa qua `/auth/me`. Frontend dùng utility thuần để kiểm tra route, lọc navigation và chọn landing route; middleware, layout và trang 403 cùng tiêu thụ utility đó. State UI là component trình bày không chứa fetch/navigation để tái sử dụng an toàn.

**Tech Stack:** FastAPI, Python 3, Pytest, Nuxt 4, Vue 3, TypeScript, Vitest, `@nuxt/test-utils`.

## Global Constraints

- Không sửa homepage, public catalog, entity detail hoặc file concept của session song song.
- Không thay database schema, không chạy migration, ETL, reload hoặc thao tác dữ liệu.
- Backend là nguồn sự thật RBAC; frontend chỉ tiêu thụ contract và fallback role để rollout tương thích.
- Không claim `Đã xác minh` khi thiếu `attributes.verifiedAt`.
- Không structural emoji; icon dùng `IconLine`.
- Mỗi task phải chạy test đỏ -> xanh trước khi chuyển task.
- Copy UI dùng tiếng Việt có dấu.

---

### Task 1: Tách contract scope backend

**Files:**
- Create: `agent/admin_permissions.py`
- Modify: `agent/admin.py`
- Test: `agent/tests/test_admin_permissions.py`

**Interfaces:**
- Produces: `ADMIN_ROLE_SCOPES`, `ADMIN_ENTRY_SCOPES`, `coerce_scope_list(value) -> set[str]`, `admin_scopes_for_user(user) -> list[str]`, `has_admin_entry_scope(user) -> bool`.
- Preserves: các symbol `ADMIN_ROLE_SCOPES` và `admin_scopes_for_user` vẫn import được từ `admin`.

- [ ] **Step 1: Viết test fail cho role và custom scope**

```python
from admin_permissions import admin_scopes_for_user, has_admin_entry_scope

def test_moderator_receives_only_moderation_scope():
    assert admin_scopes_for_user({"role": "moderator"}) == ["moderation.manager"]

def test_superadmin_receives_wildcard():
    assert admin_scopes_for_user({"role": "superadmin"}) == ["*"]

def test_custom_scopes_are_normalized_and_deduplicated():
    user = {"role": "user", "admin_scopes": "content.editor, moderation.manager"}
    assert admin_scopes_for_user(user) == ["content.editor", "moderation.manager"]
    assert has_admin_entry_scope(user) is True
```

- [ ] **Step 2: Chạy test để xác nhận đỏ**

Run: `python -m pytest agent/tests/test_admin_permissions.py -q`

Expected: FAIL vì `admin_permissions` chưa tồn tại.

- [ ] **Step 3: Tạo module permission tối thiểu và đổi import trong `admin.py`**

```python
ADMIN_ROLE_SCOPES = {
    "moderator": {"moderation.manager"},
    "admin": {"content.editor", "moderation.manager", "ops.deploy", "settings.admin", "security.admin"},
    "superadmin": {"*"},
}
ADMIN_ENTRY_SCOPES = frozenset({"content.editor", "moderation.manager", "ops.deploy", "settings.admin", "security.admin"})
```

`admin.py` import/re-export các tên cũ và dùng `has_admin_entry_scope` cho `_has_admin_entry_scope`.

- [ ] **Step 4: Chạy focused backend test**

Run: `python -m pytest agent/tests/test_admin_permissions.py agent/tests/test_wave3_security.py -q`

Expected: PASS.

### Task 2: Thêm scope vào `/auth/me`

**Files:**
- Modify: `agent/auth.py`
- Modify: `agent/tests/test_admin_permissions.py`

**Interfaces:**
- Consumes: `admin_permissions.admin_scopes_for_user`.
- Produces: `_safe_user(user)["admin_scopes"]: list[str]`.

- [ ] **Step 1: Viết test fail cho safe-user contract**

```python
from auth import _safe_user

def test_safe_user_exposes_normalized_admin_scopes():
    payload = _safe_user({"id": "u1", "phone": "0900000000", "role": "moderator"})
    assert payload["admin_scopes"] == ["moderation.manager"]

def test_safe_user_keeps_regular_user_scope_empty():
    payload = _safe_user({"id": "u2", "phone": "0900000001", "role": "user"})
    assert payload["admin_scopes"] == []
```

- [ ] **Step 2: Xác nhận test đỏ**

Run: `python -m pytest agent/tests/test_admin_permissions.py -q`

Expected: FAIL vì thiếu key `admin_scopes`.

- [ ] **Step 3: Thêm field vào `_safe_user`**

```python
"admin_scopes": admin_scopes_for_user(user),
```

- [ ] **Step 4: Chạy auth/admin regression liên quan**

Run: `python -m pytest agent/tests/test_admin_permissions.py agent/tests/test_account_control_plane_security.py agent/tests/test_wave3_security.py -q`

Expected: PASS.

### Task 3: Tạo frontend access resolver

**Files:**
- Create: `web-nuxt/utils/adminAccess.ts`
- Modify: `web-nuxt/types/index.ts`
- Test: `web-nuxt/tests/admin-access.test.ts`

**Interfaces:**
- Produces: `AdminScope`, `AdminActor`, `resolveAdminScopes(user)`, `hasAdminEntry(scopes)`, `requiredAdminScope(path)`, `canAccessAdminPath(path, scopes)`, `firstAdminRoute(scopes)`.

- [ ] **Step 1: Viết Vitest fail cho moderator/admin/superadmin**

```ts
expect(resolveAdminScopes({ id: 'm1', role: 'moderator' })).toEqual(['moderation.manager'])
expect(canAccessAdminPath('/admin/kiem-duyet', ['moderation.manager'])).toBe(true)
expect(canAccessAdminPath('/admin/users', ['moderation.manager'])).toBe(false)
expect(firstAdminRoute(['moderation.manager'])).toBe('/admin/kiem-duyet')
expect(canAccessAdminPath('/admin/cai-dat/seo', ['*'])).toBe(true)
```

- [ ] **Step 2: Xác nhận test đỏ**

Run: `npm test -- admin-access.test.ts`

Workdir: `web-nuxt`

Expected: FAIL vì utility chưa tồn tại.

- [ ] **Step 3: Viết resolver fail-closed**

Route map phải dùng longest-prefix match; `/admin` là entry route, route `/admin/**` chưa biết trả `false`.

- [ ] **Step 4: Chạy test resolver**

Run: `npm test -- admin-access.test.ts`

Expected: PASS.

### Task 4: Gắn scope vào navigation và middleware

**Files:**
- Modify: `web-nuxt/utils/adminNavigation.ts`
- Modify: `web-nuxt/middleware/admin.ts`
- Modify: `web-nuxt/tests/admin-access.test.ts`
- Modify: `web-nuxt/tests/ui-foundation-shell.test.ts`

**Interfaces:**
- `AdminNavItem.scope?: AdminScope`.
- Produces: `filterAdminNavGroups(groups, scopes) -> AdminNavGroup[]`.

- [ ] **Step 1: Viết test fail cho nav filtering**

```ts
const groups = filterAdminNavGroups(ADMIN_NAV_GROUPS, ['moderation.manager'])
const ids = groups.flatMap(group => group.items.map(item => item.id))
expect(ids).toContain('moderation')
expect(ids).toContain('reports')
expect(ids).not.toContain('users')
expect(ids).not.toContain('entities-all')
```

- [ ] **Step 2: Viết source contract test cho middleware**

Test đọc `middleware/admin.ts` và xác nhận nó dùng `resolveAdminScopes`, `canAccessAdminPath`, `firstAdminRoute`, không còn `['admin', 'superadmin']`.

- [ ] **Step 3: Xác nhận test đỏ**

Run: `npm test -- admin-access.test.ts ui-foundation-shell.test.ts`

Expected: FAIL ở filter/middleware contract.

- [ ] **Step 4: Sửa navigation và middleware**

Middleware logic:

```ts
const scopes = resolveAdminScopes(user.value)
if (!hasAdminEntry(scopes)) return navigateTo('/?login=admin')
if (to.path === '/admin' && firstAdminRoute(scopes) !== '/admin') return navigateTo(firstAdminRoute(scopes))
const required = requiredAdminScope(to.path)
if (!canAccessAdminPath(to.path, scopes)) {
  return navigateTo({ path: '/403', query: { from: to.path, required: required || '' } })
}
```

- [ ] **Step 5: Chạy focused frontend test**

Run: `npm test -- admin-access.test.ts ui-foundation-shell.test.ts`

Expected: PASS.

### Task 5: Tạo `SystemStatePanel` và trang `/403`

**Files:**
- Create: `web-nuxt/components/system/SystemStatePanel.vue`
- Create: `web-nuxt/pages/403.vue`
- Test: `web-nuxt/tests/system-state-panel.test.ts`

**Interfaces:**
- Props: `kind`, `title`, `description`, `primaryLabel?`, `secondaryLabel?`, `details?`, `retryAfter?`.
- Emits: `primary`, `secondary`.

- [ ] **Step 1: Viết component test fail**

```ts
const wrapper = await mountSuspended(SystemStatePanel, {
  props: {
    kind: 'permission-denied',
    title: 'Bạn chưa có quyền truy cập',
    description: 'Tài khoản hiện tại không có phạm vi cần thiết.',
    primaryLabel: 'Mở khu vực được phép',
  },
})
expect(wrapper.get('[role="alert"]').text()).toContain('Bạn chưa có quyền truy cập')
await wrapper.get('button').trigger('click')
expect(wrapper.emitted('primary')).toHaveLength(1)
expect(wrapper.find('.line-icon').exists()).toBe(true)
```

- [ ] **Step 2: Xác nhận test đỏ**

Run: `npm test -- system-state-panel.test.ts`

Expected: FAIL vì component chưa tồn tại.

- [ ] **Step 3: Viết component và trang 403**

`403.vue` resolve scope từ `useAuth`, chọn `firstAdminRoute`, chỉ nhận `from` bắt đầu bằng `/`, và dùng `SystemStatePanel` cho action quay lại.

- [ ] **Step 4: Chạy component test**

Run: `npm test -- system-state-panel.test.ts`

Expected: PASS.

### Task 6: Lọc Admin layout theo scope

**Files:**
- Modify: `web-nuxt/layouts/admin.vue`
- Modify: `web-nuxt/tests/ui-foundation-shell.test.ts`

**Interfaces:**
- Consumes: `resolveAdminScopes`, `filterAdminNavGroups`.
- Produces: `visibleAdminNavGroups` computed và workstream label chỉ dựa trên nhóm visible.

- [ ] **Step 1: Viết layout test fail với moderator**

Mock `useAuth().user.value = { id: 'm1', role: 'moderator', admin_scopes: ['moderation.manager'] }`; mount layout; assert có `Kiểm duyệt`, `Báo cáo`, không có `Thành viên`, `Chất lượng dữ liệu`, `Knowledge Agent`.

- [ ] **Step 2: Xác nhận test đỏ**

Run: `npm test -- ui-foundation-shell.test.ts`

Expected: FAIL vì layout vẫn render `ADMIN_NAV_GROUPS` tĩnh.

- [ ] **Step 3: Dùng visible groups và tránh tải badge ngoài scope**

`v-for` đổi sang `visibleAdminNavGroups`; `loadBadges` bỏ qua khi không có queue visible hoặc lọc badge theo item visible.

- [ ] **Step 4: Chạy shell/access/state tests**

Run: `npm test -- admin-access.test.ts system-state-panel.test.ts ui-foundation-shell.test.ts`

Expected: PASS.

### Task 7: Verification và handoff Wave NP-1

**Files:**
- Modify: `docs/page-inventory-design-scope-2026-07-27.md`
- Modify: `docs/superpowers/plans/2026-07-28-non-public-wave0-rbac-state-foundation.md`

- [ ] **Step 1: Chạy backend focused suite**

Run: `python -m pytest agent/tests/test_admin_permissions.py agent/tests/test_admin.py agent/tests/test_wave3_security.py agent/tests/test_account_control_plane_security.py -q`

- [ ] **Step 2: Chạy frontend tests**

Run: `npm test -- admin-access.test.ts system-state-panel.test.ts ui-foundation-shell.test.ts smoke.test.ts`

Workdir: `web-nuxt`

- [ ] **Step 3: Chạy typecheck và build**

Run: `npm run typecheck`

Run: `npm run build`

Workdir: `web-nuxt`

- [ ] **Step 4: Kiểm tra diff và tiêu chí**

Run: `git diff --check`

Xác nhận không có thay đổi homepage/public catalog/database schema và moderator chỉ thấy moderation surface.

- [ ] **Step 5: Cập nhật trạng thái plan**

Đánh dấu checkbox đã hoàn tất bằng evidence thật; ghi các test đã chạy và phần còn lại của Wave NP-1. Không đánh dấu `done` nếu typecheck/build hoặc focused suite còn fail mới.
