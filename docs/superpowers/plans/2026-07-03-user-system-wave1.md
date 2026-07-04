# User System Deep Upgrade — Wave 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close frontend gaps for existing backend features (collections, scheduled posts, muted users) + add password strength meter, content analytics, reaction animations, avatar consistency, and settings enrichment.

**Architecture:** All changes are additive FE-only (no migrations, no new backend endpoints). Backend CRUD for collections (`/me/collections`), scheduled posts (`/scheduled`), muted users (`/muted-users`), and user stats (`/me/stats`) already exists. We wire up FE to these endpoints and polish UX.

**Tech Stack:** Nuxt 4 (SSR), Vue 3 Composition API, TypeScript, CSS custom properties (no Tailwind), existing design system tokens.

## Global Constraints

- Solo dev, free-tier, web-only, <10k users, <1M VND/month budget
- No new npm dependencies — CSS-only animations, inline scoring
- `prefers-reduced-motion` guard on all animations
- Test: `python -m pytest -q` baseline must stay green; `cd web-nuxt && npm run build` must pass
- Commit per task, message format: `feat(user): <mô tả>`
- Branch: `feat/entity-content-model` (current working branch)
- Windows environment, PowerShell primary

## Already Done (audit results — do NOT re-implement)

- **Dark mode public pages**: `@nuxtjs/color-mode` module configured (`nuxt.config.ts:8,11`), toggle button in public header (`default.vue:30`), settings "Giao diện" tab with light/dark/system toggle, `dark-overrides.css` applied globally
- **Login history UI**: `cai-dat.vue:218-231` — table with method/success/IP/timestamp
- **Blocked users list**: `cai-dat.vue:316-329` — tab "Người bị chặn" with unblock buttons
- **Save pop animation**: `components.css:404` — `@keyframes savePop` exists
- **Like pop animation**: `PostCard.vue:75` — `like-pop` class binding exists

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `web-nuxt/pages/cai-dat.vue` | User settings page | Modify: add password strength meter, muted users tab, overview enrichment |
| `web-nuxt/pages/cong-dong.vue` | Community page + post creation | Modify: add scheduling UI, "save to collection" flow |
| `web-nuxt/pages/nguoi-dung/[id].vue` | User profile page | Modify: add analytics card, collections tab |
| `web-nuxt/components/PostCard.vue` | Post card component | Modify: add "save to collection" dropdown |
| `web-nuxt/components/AvatarPlaceholder.vue` | Shared avatar component | Read (no change needed — already handles src+initial+error) |
| `web-nuxt/components/ReviewCard.vue` | Review card component | Modify: replace inline avatar with AvatarPlaceholder |
| `web-nuxt/assets/css/components.css` | Component styles | Modify: add reaction animation keyframes |
| `web-nuxt/composables/useCollections.ts` | Collection management (new) | Create: CRUD composable wrapping /me/collections |

---

### Task 1: Password Strength Meter

**Files:**
- Modify: `web-nuxt/pages/cai-dat.vue:182-189` (password fields in security tab)

**Interfaces:**
- Consumes: existing `newPw` ref in cai-dat.vue
- Produces: inline `passwordScore()` function + visual bar below password input

- [ ] **Step 1: Add password scoring function in cai-dat.vue script**

Add after the existing password-related refs (find `const newPw` or `const confirmPw`):

```typescript
const COMMON_PASSWORDS = new Set([
  '123456', 'password', '12345678', 'qwerty', 'abc123', 'monkey', 'master',
  '111111', '123123', 'letmein', 'dragon', 'baseball', 'iloveyou', 'trustno1',
  'sunshine', 'princess', 'football', 'shadow', 'superman', 'michael',
])

const pwStrength = computed(() => {
  const pw = newPw.value
  if (!pw) return { score: 0, label: '', color: '' }
  if (COMMON_PASSWORDS.has(pw.toLowerCase())) return { score: 1, label: 'Rất yếu', color: 'var(--danger)' }
  let score = 0
  if (pw.length >= 8) score++
  if (pw.length >= 12) score++
  if (pw.length >= 16) score++
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++
  if (/\d/.test(pw)) score++
  if (/[^a-zA-Z0-9]/.test(pw)) score++
  const level = score <= 2 ? 1 : score <= 3 ? 2 : score <= 4 ? 3 : 4
  const labels = ['', 'Yếu', 'Trung bình', 'Mạnh', 'Rất mạnh']
  const colors = ['', 'var(--danger)', 'var(--warning)', 'var(--success)', 'var(--primary)']
  return { score: level, label: labels[level], color: colors[level] }
})
```

- [ ] **Step 2: Add strength bar UI below the new password input**

Find the new password `<label class="sf-field">` block (line ~182-185). After the `<input>` for new password, add:

```html
<div v-if="newPw" class="pw-strength" aria-live="polite">
  <div class="pw-bar">
    <span v-for="i in 4" :key="i" :class="['pw-segment', { filled: i <= pwStrength.score }]" :style="i <= pwStrength.score ? { background: pwStrength.color } : {}"></span>
  </div>
  <span class="pw-label" :style="{ color: pwStrength.color }">{{ pwStrength.label }}</span>
</div>
```

- [ ] **Step 3: Add strength bar CSS**

Add to the `<style scoped>` section of cai-dat.vue:

```css
.pw-strength { display: flex; align-items: center; gap: var(--space-2); margin-top: var(--space-1); }
.pw-bar { display: flex; gap: 3px; flex: 1; max-width: 160px; }
.pw-segment { height: 4px; flex: 1; border-radius: 2px; background: var(--line); transition: background .2s; }
.pw-label { font-size: .75rem; font-weight: 500; min-width: 80px; }
```

- [ ] **Step 4: Build and verify**

Run: `cd web-nuxt && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/pages/cai-dat.vue
git commit -m "feat(user): password strength meter in security tab"
```

---

### Task 2: Muted Users Tab in Settings

**Files:**
- Modify: `web-nuxt/pages/cai-dat.vue`

**Interfaces:**
- Consumes: `GET /api/muted-users` endpoint (already exists at `notifications.py:722`)
- Produces: new "Tắt tiếng" tab in settings with unmute buttons

- [ ] **Step 1: Add the muted users tab to TABS array**

Find the `TABS` constant (around line 395-405). Add after the `chan` (blocked) tab entry:

```typescript
{ key: 'tat-tieng', label: 'Tắt tiếng', icon: '\u{1F507}' },
```

- [ ] **Step 2: Add muted users data + fetch function**

Add near the `blockedUsers` refs (around line 688):

```typescript
const mutedUsers = ref<any[]>([])
const mutedLoading = ref(true)

async function loadMutedUsers() {
  mutedLoading.value = true
  try {
    const res = await $fetch<{ users: any[] }>('/api/muted-users', { headers: authHeaders() })
    mutedUsers.value = res.users || []
  } catch { /* ignore */ }
  mutedLoading.value = false
}

async function unmuteUser(id: string, name: string) {
  try {
    await $fetch(`/api/mute/${id}`, { method: 'POST', headers: { ...authHeaders(), 'x-csrf-token': csrf.value } })
    mutedUsers.value = mutedUsers.value.filter(u => u.id !== id)
    showToast(`Đã bỏ tắt tiếng ${name || 'người dùng'}`, 'success')
  } catch (e: unknown) {
    if (getStatusCode(e) === 401) { handleSessionExpired(); return }
    showToast('Không thể bỏ tắt tiếng', 'error')
  }
}
```

- [ ] **Step 3: Trigger load when tab activates**

Find the tab loading logic (around line 446, the `if (key === 'bao-mat')` block). Add:

```typescript
if (key === 'tat-tieng' && !tabLoaded.has('tat-tieng')) { loadMutedUsers(); tabLoaded.add('tat-tieng') }
```

- [ ] **Step 4: Add muted users tab panel template**

Add after the blocked users panel (after line ~329):

```html
<!-- Tab: Người tắt tiếng -->
<div v-if="activeTab === 'tat-tieng'" id="panel-tat-tieng" class="settings-card card" role="tabpanel" aria-labelledby="tab-tat-tieng">
  <h2>Người bị tắt tiếng</h2>
  <p class="sf-hint sf-hint-spaced">Bài viết và bình luận của người bị tắt tiếng sẽ ẩn khỏi bảng tin của bạn, nhưng họ vẫn có thể xem nội dung của bạn.</p>
  <div v-if="mutedLoading" class="sf-loading" role="status"><div class="spinner spinner-sm"></div> Đang tải...</div>
  <div v-else-if="mutedUsers.length" class="sessions-list">
    <div v-for="m in mutedUsers" :key="m.id" class="session-item">
      <div class="session-info">
        <NuxtLink :to="userPath(m.username || m.id)" class="session-ua">{{ m.display_name || 'Người dùng' }}</NuxtLink>
      </div>
      <button type="button" class="btn btn-ghost btn-sm" @click="unmuteUser(m.id, m.display_name)">Bỏ tắt tiếng</button>
    </div>
  </div>
  <p v-else class="sf-hint">Bạn chưa tắt tiếng ai.</p>
</div>
```

- [ ] **Step 5: Build and verify**

Run: `cd web-nuxt && npm run build`
Expected: Build succeeds.

- [ ] **Step 6: Commit**

```bash
git add web-nuxt/pages/cai-dat.vue
git commit -m "feat(user): muted users tab in settings with unmute"
```

---

### Task 3: Collection Management FE

**Files:**
- Create: `web-nuxt/composables/useCollections.ts`
- Modify: `web-nuxt/pages/nguoi-dung/[id].vue` (add Collections tab)
- Modify: `web-nuxt/components/PostCard.vue` (add "save to collection" option)

**Interfaces:**
- Consumes: `GET /me/collections`, `POST /me/collections`, `DELETE /me/collections/{id}`, `POST /me/collections/{id}/items`, `DELETE /me/collections/{id}/items/{post_id}`, `GET /collections/{id}` (all exist in `social.py:2791+`)
- Produces: `useCollections()` composable + collection tab on profile + collection dropdown on PostCard

- [ ] **Step 1: Create useCollections composable**

```typescript
// web-nuxt/composables/useCollections.ts
export function useCollections() {
  const collections = useState<any[]>('user-collections', () => [])
  const loading = ref(false)

  async function fetchCollections() {
    loading.value = true
    try {
      const { authHeaders } = useAuth()
      const res = await $fetch<{ collections: any[] }>('/me/collections', { headers: authHeaders() })
      collections.value = res.collections || []
    } catch { /* ignore */ }
    loading.value = false
  }

  async function createCollection(name: string, description = '', isPublic = true) {
    const { authHeaders, csrf } = useAuth()
    const res = await $fetch<{ collection: any }>('/me/collections', {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json', 'x-csrf-token': csrf.value, 'idempotency-key': crypto.randomUUID() },
      body: { name, description, is_public: isPublic },
    })
    if (res.collection) collections.value.unshift({ ...res.collection, item_count: 0 })
    return res.collection
  }

  async function deleteCollection(id: string) {
    const { authHeaders, csrf } = useAuth()
    await $fetch(`/me/collections/${id}`, {
      method: 'DELETE',
      headers: { ...authHeaders(), 'x-csrf-token': csrf.value },
    })
    collections.value = collections.value.filter(c => c.id !== id)
  }

  async function addToCollection(collectionId: string, postId: string) {
    const { authHeaders, csrf } = useAuth()
    await $fetch(`/me/collections/${collectionId}/items`, {
      method: 'POST',
      headers: { ...authHeaders(), 'Content-Type': 'application/json', 'x-csrf-token': csrf.value },
      body: { post_id: postId },
    })
    const c = collections.value.find(c => c.id === collectionId)
    if (c) c.item_count = (c.item_count || 0) + 1
  }

  async function removeFromCollection(collectionId: string, postId: string) {
    const { authHeaders, csrf } = useAuth()
    await $fetch(`/me/collections/${collectionId}/items/${postId}`, {
      method: 'DELETE',
      headers: { ...authHeaders(), 'x-csrf-token': csrf.value },
    })
    const c = collections.value.find(c => c.id === collectionId)
    if (c && c.item_count > 0) c.item_count--
  }

  return { collections, loading, fetchCollections, createCollection, deleteCollection, addToCollection, removeFromCollection }
}
```

- [ ] **Step 2: Add collections tab on user profile**

In `nguoi-dung/[id].vue`, find the profile tabs section (around line 117-123). Add a new tab button for collections:

```html
<button type="button" id="profile-tab-collections" role="tab" v-if="isSelf" :class="['chip', { active: tab === 'collections' }]" :aria-selected="tab === 'collections'" aria-controls="profile-panel-collections" :tabindex="tab === 'collections' ? 0 : -1" @click="setProfileTab('collections')">
  Danh sách<ClientOnly><span v-if="collectionsCount > 0" class="tab-count">{{ collectionsCount }}</span></ClientOnly>
</button>
```

Then in the feed-main section (around line 125+), add the collections panel:

```html
<ClientOnly v-if="tab === 'collections' && isSelf">
  <div v-if="collectionsLoading" class="sf-loading"><div class="spinner spinner-sm"></div> Đang tải...</div>
  <div v-else>
    <div class="collections-header">
      <button type="button" class="btn btn-primary btn-sm" @click="showCreateCollection = true">+ Tạo danh sách</button>
    </div>
    <div v-if="userCollections.length" class="saved-grid">
      <div v-for="c in userCollections" :key="c.id" class="card saved-card">
        <div class="card-b">
          <span class="card-type">{{ c.is_public ? 'Công khai' : 'Riêng tư' }}</span>
          <h3>{{ c.name }}</h3>
          <p v-if="c.description" class="place">{{ c.description }}</p>
          <p class="place">{{ c.item_count || 0 }} bài viết</p>
        </div>
        <button type="button" class="btn btn-ghost btn-sm btn-danger-text" @click="handleDeleteCollection(c.id, c.name)">Xóa</button>
      </div>
    </div>
    <p v-else class="empty-state">Bạn chưa tạo danh sách nào. Tạo danh sách để sắp xếp bài viết yêu thích!</p>
  </div>

  <!-- Create collection modal -->
  <div v-if="showCreateCollection" class="modal-overlay" @click.self="showCreateCollection = false">
    <div class="modal-content card" role="dialog" aria-label="Tạo danh sách">
      <h3>Tạo danh sách mới</h3>
      <form @submit.prevent="handleCreateCollection">
        <label class="sf-field">
          <span class="sf-label">Tên</span>
          <input v-model="newCollectionName" type="text" class="sf-input" maxlength="100" required placeholder="VD: Quán ngon Vĩnh Long" />
        </label>
        <label class="sf-field">
          <span class="sf-label">Mô tả (không bắt buộc)</span>
          <textarea v-model="newCollectionDesc" class="sf-input" maxlength="300" rows="2"></textarea>
        </label>
        <div class="sf-actions">
          <button type="button" class="btn btn-ghost" @click="showCreateCollection = false">Hủy</button>
          <button type="submit" class="btn btn-primary" :disabled="creatingCollection">{{ creatingCollection ? 'Đang tạo...' : 'Tạo' }}</button>
        </div>
      </form>
    </div>
  </div>
</ClientOnly>
```

- [ ] **Step 3: Add collections script logic in nguoi-dung/[id].vue**

Add in the `<script setup>` section:

```typescript
const { collections: userCollections, loading: collectionsLoading, fetchCollections, createCollection, deleteCollection } = useCollections()
const collectionsCount = computed(() => userCollections.value.length)
const showCreateCollection = ref(false)
const newCollectionName = ref('')
const newCollectionDesc = ref('')
const creatingCollection = ref(false)

async function handleCreateCollection() {
  if (!newCollectionName.value.trim()) return
  creatingCollection.value = true
  try {
    await createCollection(newCollectionName.value.trim(), newCollectionDesc.value.trim())
    showCreateCollection.value = false
    newCollectionName.value = ''
    newCollectionDesc.value = ''
  } catch { /* toast error */ }
  creatingCollection.value = false
}

async function handleDeleteCollection(id: string, name: string) {
  if (!confirm(`Xóa danh sách "${name}"?`)) return
  try { await deleteCollection(id) } catch { /* toast error */ }
}

// Load collections when tab selected
watch(() => tab.value, (t) => {
  if (t === 'collections' && !userCollections.value.length) fetchCollections()
})
```

- [ ] **Step 4: Build and verify**

Run: `cd web-nuxt && npm run build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/composables/useCollections.ts web-nuxt/pages/nguoi-dung/[id].vue
git commit -m "feat(user): collection management — composable + profile tab"
```

---

### Task 4: Scheduled Posts UI

**Files:**
- Modify: `web-nuxt/pages/cong-dong.vue` (add schedule option to post creation + scheduled posts section)

**Interfaces:**
- Consumes: `POST /draft/{id}/schedule?scheduled_at=ISO` (social.py:622), `GET /scheduled` (social.py:660), `DELETE /scheduled/{post_id}` (social.py:698)
- Produces: date/time picker in post form + "Bài đã lên lịch" section

- [ ] **Step 1: Audit cong-dong.vue for post creation form**

Read the post creation form section in `cong-dong.vue`. Find the form's submit handler and the area where post_type / content fields are. The scheduling UI will be added as an option below the submit button.

- [ ] **Step 2: Add schedule toggle + datetime input**

In the post creation form, add after the existing form fields (before the submit button):

```html
<div class="schedule-option">
  <label class="schedule-toggle">
    <input type="checkbox" v-model="schedulePost" class="toggle" />
    <span>Lên lịch đăng bài</span>
  </label>
  <div v-if="schedulePost" class="schedule-picker">
    <input type="datetime-local" v-model="scheduledAt" class="sf-input" :min="minScheduleDate" required />
    <span class="sf-hint">Bài sẽ tự động đăng vào thời gian này.</span>
  </div>
</div>
```

Add in script:

```typescript
const schedulePost = ref(false)
const scheduledAt = ref('')
const minScheduleDate = computed(() => {
  const d = new Date()
  d.setMinutes(d.getMinutes() + 10)
  return d.toISOString().slice(0, 16)
})
```

- [ ] **Step 3: Wire scheduling into post submit flow**

In the post submit handler, after the draft is created (POST to create draft), add scheduling logic:

```typescript
if (schedulePost.value && scheduledAt.value) {
  await $fetch(`/draft/${draftId}/schedule?scheduled_at=${new Date(scheduledAt.value).toISOString()}`, {
    method: 'POST',
    headers: { ...authHeaders(), 'x-csrf-token': csrf.value },
  })
  showToast('Đã lên lịch đăng bài', 'success')
  schedulePost.value = false
  scheduledAt.value = ''
  return
}
```

- [ ] **Step 4: Add scheduled posts section**

Add a "Bài đã lên lịch" section visible to the authenticated user. This goes near the top of the community page content area:

```html
<details v-if="isLoggedIn && scheduledPosts.length" class="scheduled-section">
  <summary class="scheduled-summary">📅 Bài đã lên lịch ({{ scheduledPosts.length }})</summary>
  <div class="scheduled-list">
    <div v-for="sp in scheduledPosts" :key="sp.id" class="scheduled-item card">
      <p>{{ sp.content?.slice(0, 100) }}{{ sp.content?.length > 100 ? '...' : '' }}</p>
      <div class="scheduled-meta">
        <time>{{ new Date(sp.scheduled_at).toLocaleString('vi-VN') }}</time>
        <button type="button" class="btn btn-ghost btn-sm btn-danger-text" @click="cancelScheduled(sp.id)">Hủy</button>
      </div>
    </div>
  </div>
</details>
```

Add in script:

```typescript
const scheduledPosts = ref<any[]>([])

async function loadScheduledPosts() {
  if (!isLoggedIn.value) return
  try {
    const res = await $fetch<{ scheduled: any[] }>('/scheduled', { headers: authHeaders() })
    scheduledPosts.value = res.scheduled || []
  } catch { /* ignore */ }
}

async function cancelScheduled(id: string) {
  try {
    await $fetch(`/scheduled/${id}`, { method: 'DELETE', headers: { ...authHeaders(), 'x-csrf-token': csrf.value } })
    scheduledPosts.value = scheduledPosts.value.filter(s => s.id !== id)
    showToast('Đã hủy lịch đăng', 'success')
  } catch { showToast('Không thể hủy', 'error') }
}

// Load on mount if logged in
onMounted(() => { loadScheduledPosts() })
```

- [ ] **Step 5: Add scheduled posts CSS**

```css
.schedule-option { margin-top: var(--space-3); }
.schedule-toggle { display: flex; align-items: center; gap: var(--space-2); cursor: pointer; }
.schedule-picker { margin-top: var(--space-2); }
.scheduled-section { margin-bottom: var(--space-4); }
.scheduled-summary { cursor: pointer; font-weight: 600; color: var(--primary); padding: var(--space-2) 0; }
.scheduled-item { padding: var(--space-3); margin-bottom: var(--space-2); }
.scheduled-meta { display: flex; justify-content: space-between; align-items: center; margin-top: var(--space-2); font-size: .85rem; color: var(--muted); }
```

- [ ] **Step 6: Build and verify**

Run: `cd web-nuxt && npm run build`
Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add web-nuxt/pages/cong-dong.vue
git commit -m "feat(user): scheduled posts UI — schedule toggle, list, cancel"
```

---

### Task 5: Content Analytics Card on Self-Profile

**Files:**
- Modify: `web-nuxt/pages/nguoi-dung/[id].vue`

**Interfaces:**
- Consumes: `GET /me/stats` endpoint (social.py:1347) — returns reactions_received, collections, reviews, ratings, followers, following, likes_received, entities_reviewed
- Produces: analytics summary card visible on self-profile

- [ ] **Step 1: Add stats fetch logic**

Add in script section of `nguoi-dung/[id].vue`:

```typescript
const userStats = ref<Record<string, number>>({})
const statsLoading = ref(false)

async function loadUserStats() {
  if (!isSelf.value) return
  statsLoading.value = true
  try {
    const { authHeaders } = useAuth()
    const res = await $fetch<Record<string, any>>('/me/stats', { headers: authHeaders() })
    userStats.value = res
  } catch { /* ignore */ }
  statsLoading.value = false
}

onMounted(() => { if (isSelf.value) loadUserStats() })
```

- [ ] **Step 2: Add analytics card template**

Insert after the `profile-completion` section (after line ~111), guarded by `isSelf`:

```html
<div v-if="isSelf && Object.keys(userStats).length" class="profile-analytics card reveal">
  <h3 class="pa-title">Tổng quan hoạt động</h3>
  <div class="pa-grid">
    <div class="pa-stat">
      <strong>{{ userStats.likes_received || 0 }}</strong>
      <span>lượt thích nhận</span>
    </div>
    <div class="pa-stat">
      <strong>{{ userStats.reactions_received || 0 }}</strong>
      <span>reactions nhận</span>
    </div>
    <div class="pa-stat">
      <strong>{{ userStats.entities_reviewed || 0 }}</strong>
      <span>nơi đã đánh giá</span>
    </div>
    <div class="pa-stat">
      <strong>{{ userStats.collections || 0 }}</strong>
      <span>danh sách</span>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Add analytics card CSS**

```css
.profile-analytics { padding: var(--space-4); margin-bottom: var(--space-4); }
.pa-title { font-size: .85rem; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; color: var(--muted); margin-bottom: var(--space-3); }
.pa-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--space-3); text-align: center; }
.pa-stat strong { display: block; font-size: 1.25rem; color: var(--text); }
.pa-stat span { font-size: .75rem; color: var(--muted); }
@media (max-width: 520px) { .pa-grid { grid-template-columns: repeat(2, 1fr); } }
```

- [ ] **Step 4: Build and verify**

Run: `cd web-nuxt && npm run build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/pages/nguoi-dung/[id].vue
git commit -m "feat(user): content analytics card on self-profile"
```

---

### Task 6: Reaction Micro-animations

**Files:**
- Modify: `web-nuxt/assets/css/components.css`

**Interfaces:**
- Consumes: existing `.save-btn` and reaction button classes
- Produces: CSS keyframe animations for reactions

- [ ] **Step 1: Add reaction pop animation**

Find the existing `@keyframes savePop` in `components.css:404`. Add after it:

```css
@keyframes reactionPop { 0% { transform: scale(0); opacity: 0; } 50% { transform: scale(1.3); opacity: 1; } 100% { transform: scale(1); opacity: 1; } }
@keyframes heartBeat { 0% { transform: scale(1); } 15% { transform: scale(1.25); } 30% { transform: scale(1); } 45% { transform: scale(1.15); } 60% { transform: scale(1); } }

.reaction-btn.just-reacted { animation: reactionPop .3s ease-out; }
.save-btn.just-saved { animation: heartBeat .5s ease-out; }

@media (prefers-reduced-motion: reduce) {
  .reaction-btn.just-reacted, .save-btn.just-saved { animation: none; }
}
```

- [ ] **Step 2: Build and verify**

Run: `cd web-nuxt && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add web-nuxt/assets/css/components.css
git commit -m "feat(user): reaction + save micro-animations with reduced-motion guard"
```

---

### Task 7: AvatarPlaceholder Consistency

**Files:**
- Modify: `web-nuxt/components/PostCard.vue`
- Modify: `web-nuxt/components/ReviewCard.vue`

**Interfaces:**
- Consumes: existing `AvatarPlaceholder.vue` component (auto-imported by Nuxt)
- Produces: consistent avatar rendering across all card components

- [ ] **Step 1: Audit PostCard.vue avatar rendering**

Read `PostCard.vue` and find the inline avatar pattern (typically lines 5-10). It will look something like:

```html
<img v-if="post.author_avatar" :src="post.author_avatar" ... />
<span v-else class="avatar">{{ post.author_name?.[0] }}</span>
```

Replace with:

```html
<AvatarPlaceholder :src="post.author_avatar" :initial="post.author_name?.[0]?.toUpperCase()" />
```

- [ ] **Step 2: Audit ReviewCard.vue avatar rendering**

Read `ReviewCard.vue` and find the same inline avatar pattern. Replace with the same `<AvatarPlaceholder>` usage:

```html
<AvatarPlaceholder :src="review.author_avatar" :initial="review.author_name?.[0]?.toUpperCase()" />
```

- [ ] **Step 3: Verify AvatarPlaceholder handles img error**

Read `AvatarPlaceholder.vue` to confirm it has `@error` handling on the `<img>`. If not, add:

```html
<img v-if="src && !broken" :src="src" ... @error="broken = true" />
```

- [ ] **Step 4: Build and verify**

Run: `cd web-nuxt && npm run build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/components/PostCard.vue web-nuxt/components/ReviewCard.vue
git commit -m "feat(user): consistent AvatarPlaceholder across PostCard + ReviewCard"
```

---

### Task 8: Settings Overview Enrichment

**Files:**
- Modify: `web-nuxt/pages/cai-dat.vue`

**Interfaces:**
- Consumes: existing `notifPrefs`, `privacy`, `blockedUsers`, `mutedUsers` refs (all already loaded on tab switch)
- Produces: enriched overview cards at top of settings page

- [ ] **Step 1: Add new overview cards**

Find the settings overview section (around lines 14-29). After the existing 3 items, add:

```html
<div class="settings-overview-item">
  <span class="so-label">Thông báo</span>
  <strong>{{ notifSummary }}</strong>
  <NuxtLink to="#thong-bao" class="so-link" @click.prevent="setTab('thong-bao')">Tùy chỉnh</NuxtLink>
</div>
<div class="settings-overview-item">
  <span class="so-label">Quyền riêng tư</span>
  <strong>{{ privacySummary }}</strong>
  <NuxtLink to="#rieng-tu" class="so-link" @click.prevent="setTab('rieng-tu')">Xem</NuxtLink>
</div>
```

- [ ] **Step 2: Add computed summaries**

Add in the script section:

```typescript
const notifSummary = computed(() => {
  if (!tabLoaded.has('thong-bao')) return 'Chưa kiểm tra'
  const on = Object.values(notifPrefs.value).filter(v => v === true).length
  const total = Object.keys(notifPrefs.value).length || 5
  return `${on}/${total} loại bật`
})

const privacySummary = computed(() => {
  if (!tabLoaded.has('rieng-tu')) return 'Chưa kiểm tra'
  const labels: Record<string, string> = { public: 'Công khai', followers: 'Người theo dõi', private: 'Riêng tư' }
  return labels[privacy.value.profile_visibility] || 'Công khai'
})
```

- [ ] **Step 3: Pre-fetch notification prefs + privacy on mount**

So the overview cards show data immediately, trigger loading on mount (not just on tab switch). Find the `onMounted` or tab-loading logic and add:

```typescript
onMounted(() => {
  loadNotifPrefs()
  loadPrivacy()
})
```

(Ensure `loadNotifPrefs` and `loadPrivacy` exist — they should be the existing tab-load functions. Mark them as loaded in `tabLoaded` after fetch.)

- [ ] **Step 4: Build and verify**

Run: `cd web-nuxt && npm run build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add web-nuxt/pages/cai-dat.vue
git commit -m "feat(user): enriched settings overview — notif + privacy summary cards"
```

---

### Task 9: Final Verification

**Files:** None (verification only)

- [ ] **Step 1: Run Python tests**

Run: `python -m pytest -q`
Expected: Same baseline as before (no new failures).

- [ ] **Step 2: Run Nuxt build**

Run: `cd web-nuxt && npm run build`
Expected: Build succeeds (check bundle size is reasonable — should be ~6MB).

- [ ] **Step 3: Verify with dev server (if possible)**

Start the Nuxt dev server and spot-check:
- Settings page: password strength meter appears when typing
- Settings page: "Tắt tiếng" tab shows
- Settings page: overview cards show notif/privacy summaries
- Profile page: analytics card visible on own profile
- Profile page: collections tab visible

---

## Waves 2-4: Subsequent Plans

These waves will be planned in separate sessions after Wave 1 is deployed:

- **Wave 2** (Activity Timeline + Profile Depth): 6 items, needs migration `063_profile_views.sql`, new endpoint `/api/users/{id}/timeline`, badge progress endpoint
- **Wave 3** (Achievement System + Engagement): 6 items, needs migrations `063_achievements.sql` + `064_login_streak.sql`, achievement checking logic, heatmap endpoint
- **Wave 4** (2FA + Security Hardening): 5 items, needs `pyotp` dependency, migrations `065_user_2fa.sql` + `066_trusted_devices.sql`, 2FA login flow changes

Each wave gets its own plan document with full step-by-step code when ready.
