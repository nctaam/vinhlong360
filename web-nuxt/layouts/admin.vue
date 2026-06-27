<template>
  <div class="admin-shell">
    <a href="#admin-main" class="skip-link">Chuyển đến nội dung chính</a>
    <aside class="admin-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="admin-sidebar-head">
        <NuxtLink class="admin-brand" to="/admin">
          <span class="logo">vinhlong<span class="dot">360</span></span>
          <small v-if="!sidebarCollapsed">Admin</small>
        </NuxtLink>
        <button type="button" class="sidebar-toggle" aria-label="Thu gọn menu" @click="sidebarCollapsed = !sidebarCollapsed">
          <span class="toggle-icon" :class="{ rotated: sidebarCollapsed }">&#9776;</span>
        </button>
      </div>

      <nav class="admin-nav" aria-label="Menu quản trị">
        <div class="nav-group">
          <span class="nav-group-label" v-if="!sidebarCollapsed">Tổng quan</span>
          <NuxtLink to="/admin" :class="{ active: route.path === '/admin' }" :title="sidebarCollapsed ? 'Dashboard' : undefined">
            <span class="nav-icon">&#128202;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Dashboard</span>
          </NuxtLink>
          <NuxtLink to="/admin/thong-ke" :class="{ active: route.path === '/admin/thong-ke' }" :title="sidebarCollapsed ? 'Thống kê' : undefined">
            <span class="nav-icon">&#128200;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Thống kê</span>
          </NuxtLink>
        </div>

        <div class="nav-group">
          <span class="nav-group-label" v-if="!sidebarCollapsed">Nội dung</span>
          <NuxtLink to="/admin/entities" :class="{ active: route.path === '/admin/entities' }" :title="sidebarCollapsed ? 'Entities' : undefined">
            <span class="nav-icon">&#128203;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Entities</span>
          </NuxtLink>
          <NuxtLink to="/admin/chua-phan-loai" :class="{ active: route.path === '/admin/chua-phan-loai' }" :title="sidebarCollapsed ? 'Chưa phân loại' : undefined">
            <span class="nav-icon">&#128205;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Chưa phân loại</span>
            <span v-if="badges.unclassified" class="nav-badge">{{ badges.unclassified }}</span>
          </NuxtLink>
          <NuxtLink to="/admin/danh-ba" :class="{ active: route.path === '/admin/danh-ba' }" :title="sidebarCollapsed ? 'Danh bạ HC' : undefined">
            <span class="nav-icon">&#127963;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Danh bạ HC</span>
          </NuxtLink>
          <NuxtLink to="/admin/lich-trinh" :class="{ active: route.path === '/admin/lich-trinh' }" :title="sidebarCollapsed ? 'Lịch trình' : undefined">
            <span class="nav-icon">&#128506;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Lịch trình</span>
          </NuxtLink>
          <NuxtLink to="/admin/data-quality" :class="{ active: route.path === '/admin/data-quality' }" :title="sidebarCollapsed ? 'Chất lượng DL' : undefined">
            <span class="nav-icon">&#128269;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Chất lượng DL</span>
          </NuxtLink>
          <NuxtLink to="/admin/media" :class="{ active: route.path === '/admin/media' }" :title="sidebarCollapsed ? 'Thư viện ảnh' : undefined">
            <span class="nav-icon">&#128444;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Thư viện ảnh</span>
          </NuxtLink>
        </div>

        <div class="nav-group">
          <span class="nav-group-label" v-if="!sidebarCollapsed">Cộng đồng</span>
          <NuxtLink to="/admin/kiem-duyet" :class="{ active: route.path === '/admin/kiem-duyet' }" :title="sidebarCollapsed ? 'Kiểm duyệt' : undefined">
            <span class="nav-icon">&#128737;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Kiểm duyệt</span>
            <span v-if="badges.moderation" class="nav-badge">{{ badges.moderation }}</span>
          </NuxtLink>
          <NuxtLink to="/admin/duyet-anh" :class="{ active: route.path === '/admin/duyet-anh' }" :title="sidebarCollapsed ? 'Duyệt ảnh' : undefined">
            <span class="nav-icon">&#128247;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Duyệt ảnh</span>
            <span v-if="badges.images" class="nav-badge">{{ badges.images }}</span>
          </NuxtLink>
          <NuxtLink to="/admin/users" :class="{ active: route.path === '/admin/users' }" :title="sidebarCollapsed ? 'Users' : undefined">
            <span class="nav-icon">&#128101;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Users</span>
          </NuxtLink>
          <NuxtLink to="/admin/bao-cao" :class="{ active: route.path === '/admin/bao-cao' }" :title="sidebarCollapsed ? 'Báo cáo' : undefined">
            <span class="nav-icon">&#128681;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Báo cáo</span>
            <span v-if="badges.reports" class="nav-badge">{{ badges.reports }}</span>
          </NuxtLink>
        </div>

        <div class="nav-group">
          <span class="nav-group-label" v-if="!sidebarCollapsed">Hệ thống</span>
          <NuxtLink to="/admin/duyet-tu-hoc" :class="{ active: route.path === '/admin/duyet-tu-hoc' }" :title="sidebarCollapsed ? 'Duyệt & Tools' : undefined">
            <span class="nav-icon">&#129514;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Duyệt & Tools</span>
            <span v-if="badges.provisional" class="nav-badge">{{ badges.provisional }}</span>
          </NuxtLink>
          <NuxtLink to="/admin/ai" :class="{ active: route.path === '/admin/ai' }" :title="sidebarCollapsed ? 'Knowledge Agent' : undefined">
            <span class="nav-icon">&#129302;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Knowledge Agent</span>
          </NuxtLink>
          <NuxtLink to="/admin/nhat-ky" :class="{ active: route.path === '/admin/nhat-ky' }" :title="sidebarCollapsed ? 'Nhật ký' : undefined">
            <span class="nav-icon">&#128220;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Nhật ký</span>
          </NuxtLink>
          <NuxtLink to="/admin/cai-dat" :class="{ active: route.path.startsWith('/admin/cai-dat') }" :title="sidebarCollapsed ? 'Cài đặt trang' : undefined">
            <span class="nav-icon">&#9881;</span>
            <span class="nav-text" v-if="!sidebarCollapsed">Cài đặt trang</span>
          </NuxtLink>
        </div>
      </nav>

      <div class="admin-sidebar-footer" v-if="!sidebarCollapsed">
        <div v-if="user" class="admin-user-info">
          <div class="admin-user-avatar">{{ user.display_name?.[0] || 'A' }}</div>
          <div class="admin-user-meta">
            <span class="admin-user-name">{{ user.display_name || 'Admin' }}</span>
            <span class="admin-user-role">{{ user.role }}</span>
          </div>
        </div>
        <NuxtLink to="/" class="back-link">&#8592; Về trang chủ</NuxtLink>
      </div>
    </aside>
    <main id="admin-main" class="admin-main">
      <div class="admin-topbar">
        <nav class="admin-crumbs" aria-label="Đường dẫn">
          <NuxtLink to="/admin" class="admin-crumb-root">AdminCP</NuxtLink>
          <template v-if="currentPageLabel">
            <span class="admin-crumb-sep" aria-hidden="true">&rsaquo;</span>
            <span class="admin-crumb-current" aria-current="page">{{ currentPageLabel }}</span>
          </template>
        </nav>
      </div>
      <slot />
    </main>
    <ClientOnly><LazyCommandPalette /></ClientOnly>
    <ClientOnly><ToastContainer /></ClientOnly>
    <ClientOnly><ConfirmDialog /></ClientOnly>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const { user, fetchMe, token, authHeaders } = useAuth()
const { prefs, setPref } = useAdminPrefs()
const sidebarCollapsed = computed({
  get: () => prefs.value.sidebarCollapsed,
  set: (v: boolean) => setPref('sidebarCollapsed', v),
})
const badges = ref<Record<string, number>>({ moderation: 0, images: 0, unclassified: 0, provisional: 0, reports: 0 })

async function loadBadges() {
  try {
    const data = await $fetch<Record<string, number>>('/admin/badge-counts', { headers: authHeaders() })
    badges.value = data
  } catch { /* ignore */ }
}

const ADMIN_PAGE_LABELS: Record<string, string> = {
  '/admin/thong-ke': 'Thống kê',
  '/admin/entities': 'Entities',
  '/admin/chua-phan-loai': 'Chưa phân loại',
  '/admin/danh-ba': 'Danh bạ HC',
  '/admin/lich-trinh': 'Lịch trình',
  '/admin/data-quality': 'Chất lượng DL',
  '/admin/kiem-duyet': 'Kiểm duyệt',
  '/admin/duyet-anh': 'Duyệt ảnh',
  '/admin/users': 'Users',
  '/admin/bao-cao': 'Báo cáo',
  '/admin/duyet-tu-hoc': 'Duyệt & Tools',
  '/admin/ai': 'Knowledge Agent',
  '/admin/nhat-ky': 'Nhật ký',
  '/admin/media': 'Thư viện ảnh',
  '/admin/cai-dat': 'Cài đặt trang',
}
const currentPageLabel = computed(() => {
  const path = route.path
  if (path === '/admin' || path === '/admin/') return ''
  if (ADMIN_PAGE_LABELS[path]) return ADMIN_PAGE_LABELS[path]
  // Nested routes (e.g. /admin/cai-dat/branding): match by longest known prefix
  const match = Object.keys(ADMIN_PAGE_LABELS)
    .filter(k => path.startsWith(k + '/'))
    .sort((a, b) => b.length - a.length)[0]
  return match ? ADMIN_PAGE_LABELS[match] : ''
})

useHead({
  meta: [{ name: 'robots', content: 'noindex,nofollow' }],
})

let badgeInterval: ReturnType<typeof setInterval> | undefined
function _badgeTick() { if (!document.hidden) loadBadges() }
function _onVisChange() { if (!document.hidden) loadBadges() }
onMounted(async () => {
  if (!user.value && token.value) await fetchMe()
  if (window.innerWidth < 1024) sidebarCollapsed.value = true
  loadBadges()
  badgeInterval = setInterval(_badgeTick, 60_000)
  document.addEventListener('visibilitychange', _onVisChange)
})
onUnmounted(() => {
  if (badgeInterval) clearInterval(badgeInterval)
  document.removeEventListener('visibilitychange', _onVisChange)
})
</script>

<style>
.admin-shell { display: flex; min-height: 100vh; }

/* ── Sidebar ── */
.admin-sidebar {
  width: 240px; background: var(--ink, #1a1a2e); color: var(--text-on-dark, #fff);
  display: flex; flex-direction: column; flex-shrink: 0;
  transition: width .35s cubic-bezier(.2,1,.4,1);
  border-right: .5px solid rgba(255,255,255,.06);
  position: sticky; top: 0; height: 100vh;
  overflow: hidden;
}
.admin-sidebar.collapsed { width: 64px; }

.admin-sidebar-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--space-4) var(--space-4) var(--space-3);
  border-bottom: .5px solid rgba(255,255,255,.08);
}
.admin-brand {
  text-decoration: none; color: var(--text-on-dark, #fff);
  transition: opacity .3s;
}
.admin-brand:hover { opacity: .8; }
.admin-brand:active { opacity: .6; }
.admin-brand:focus-visible { outline: 2px solid var(--accent, #f5c518); outline-offset: 4px; border-radius: 4px; }
.admin-brand .logo { font-size: 1.15rem; font-weight: 800; letter-spacing: -.02em; }
.admin-brand .dot { color: var(--accent, #f5c518); }
.admin-brand small {
  display: block; font-size: .65rem; opacity: .45; margin-top: 1px;
  letter-spacing: 2.5px; text-transform: uppercase;
}
.collapsed .admin-brand .logo { font-size: .9rem; }
.collapsed .admin-brand { text-align: center; }

.sidebar-toggle {
  background: none; border: none; color: rgba(255,255,255,.5);
  cursor: pointer; padding: 4px; font-size: 1rem;
  min-width: 36px; min-height: 36px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 8px;
  transition: color .25s, background .25s, transform .35s cubic-bezier(.2,1,.4,1);
}
.sidebar-toggle:hover { color: rgba(255,255,255,.9); background: rgba(255,255,255,.08); }
.sidebar-toggle:active { transform: scale(.88); transition-duration: .08s; }
.sidebar-toggle:focus-visible { outline: 2px solid var(--accent, #f5c518); outline-offset: 2px; }
.toggle-icon { display: inline-block; transition: transform .35s cubic-bezier(.2,1,.4,1); }
.toggle-icon.rotated { transform: rotate(90deg); }

/* ── Nav groups ── */
.admin-nav {
  flex: 1; overflow-y: auto; padding: var(--space-3) var(--space-2);
  display: flex; flex-direction: column; gap: var(--space-1);
  scrollbar-width: thin; scrollbar-color: rgba(255,255,255,.08) transparent;
}
.admin-nav::-webkit-scrollbar { width: 4px; }
.admin-nav::-webkit-scrollbar-track { background: transparent; }
.admin-nav::-webkit-scrollbar-thumb { background: rgba(255,255,255,.08); border-radius: 2px; }
.nav-group { margin-bottom: var(--space-2); }
.nav-group-label {
  display: block; font-size: .65rem; font-weight: 600;
  text-transform: uppercase; letter-spacing: 1.5px;
  color: rgba(255,255,255,.3); padding: var(--space-2) var(--space-3) var(--space-1);
  transition: opacity .25s;
}
.admin-nav a {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) var(--space-3); border-radius: 8px;
  color: rgba(255,255,255,.6); text-decoration: none;
  font-size: .85rem; font-weight: 500;
  min-height: 40px; position: relative;
  transition: background .25s, color .25s, transform .35s cubic-bezier(.2,1,.4,1);
}
.admin-nav a:hover { background: rgba(255,255,255,.08); color: rgba(255,255,255,.95); }
.admin-nav a:active { transform: scale(.97); transition-duration: .08s; }
.admin-nav a:focus-visible { outline: 2px solid var(--accent, #f5c518); outline-offset: -2px; }
.admin-nav a.active {
  background: rgba(255,255,255,.14); color: #fff; font-weight: 600;
  box-shadow: inset 4px 0 0 var(--accent, #f5c518);
  transition: box-shadow .2s, background .2s, color .25s;
}
.nav-icon { font-size: 1.05rem; flex-shrink: 0; width: 24px; text-align: center; transition: transform .35s cubic-bezier(.2,1,.4,1); }
.admin-nav a:hover .nav-icon { transform: scale(1.1); }
.nav-text { white-space: nowrap; overflow: hidden; transition: opacity .2s; }
.nav-badge {
  margin-left: auto; min-width: 20px; height: 20px; padding: 0 6px;
  border-radius: 10px; background: var(--error, #D94F3D); color: #fff;
  font-size: .65rem; font-weight: 700; display: flex; align-items: center; justify-content: center;
  line-height: 1; flex-shrink: 0;
}
.collapsed .nav-badge {
  position: absolute; top: 4px; right: 4px; min-width: 16px; height: 16px;
  padding: 0 4px; font-size: .6rem;
}
.collapsed .nav-icon { font-size: 1.2rem; }
.collapsed .admin-nav a { justify-content: center; padding: var(--space-2); }
.collapsed .admin-nav a[title]:is(:hover, :focus-visible)::after {
  content: attr(title); position: absolute; left: calc(100% + 8px); top: 50%;
  transform: translateY(-50%); background: rgba(0,0,0,.85); color: #fff;
  padding: 4px 10px; border-radius: 6px; font-size: .75rem; font-weight: 600;
  white-space: nowrap; z-index: var(--z-overlay); pointer-events: none;
  animation: tooltipIn .15s ease-out;
}
@keyframes tooltipIn { from { opacity: 0; transform: translateY(-50%) translateX(-4px); } to { opacity: 1; transform: translateY(-50%) translateX(0); } }

/* ── Sidebar footer ── */
.admin-sidebar-footer {
  padding: var(--space-3) var(--space-4);
  border-top: .5px solid rgba(255,255,255,.08);
  display: flex; flex-direction: column; gap: var(--space-3);
}
.admin-user-info { display: flex; align-items: center; gap: var(--space-3); }
.admin-user-avatar {
  width: 32px; height: 32px; min-width: 32px; border-radius: 50%;
  background: var(--accent, #f5c518); color: var(--ink, #1a1a2e);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: .8rem; flex-shrink: 0;
  transition: transform .35s cubic-bezier(.2,1,.4,1);
}
.admin-user-info:hover .admin-user-avatar { transform: scale(1.08); }
.admin-user-meta { display: flex; flex-direction: column; overflow: hidden; }
.admin-user-name { font-size: .82rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.admin-user-role { font-size: .68rem; color: rgba(255,255,255,.4); text-transform: uppercase; letter-spacing: 1px; }
.back-link {
  color: rgba(255,255,255,.45); text-decoration: none; font-size: .78rem;
  transition: color .25s, transform .35s cubic-bezier(.2,1,.4,1);
  display: inline-flex; align-items: center; gap: var(--space-2);
  min-height: 36px; padding: var(--space-1) 0;
}
.back-link:hover { color: rgba(255,255,255,.85); transform: translateX(-2px); }
.back-link:active { transform: translateX(0) scale(.95); transition-duration: .08s; }
.back-link:focus-visible { outline: 2px solid var(--accent, #f5c518); outline-offset: 2px; border-radius: 4px; }

/* ── Topbar breadcrumb ── */
.admin-topbar {
  position: sticky; top: 0; z-index: var(--z-sticky, 100);
  margin: calc(var(--space-6) * -1) calc(var(--space-8) * -1) var(--space-5);
  padding: var(--space-3) var(--space-8);
  background: color-mix(in oklab, var(--bg-alt) 85%, transparent);
  -webkit-backdrop-filter: saturate(1.4) blur(8px);
  backdrop-filter: saturate(1.4) blur(8px);
  border-bottom: .5px solid var(--line);
}
.admin-crumbs { display: flex; align-items: center; gap: var(--space-2); flex-wrap: wrap; font-size: .82rem; }
.admin-crumb-root { color: var(--muted); text-decoration: none; font-weight: 600; transition: color .2s; }
.admin-crumb-root:hover { color: var(--primary, #219653); }
.admin-crumb-root:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; border-radius: 4px; }
.admin-crumb-sep { color: var(--muted); opacity: .5; }
.admin-crumb-current { color: var(--ink); font-weight: 600; }

/* ── Main area ── */
.admin-main {
  flex: 1; padding: var(--space-6) var(--space-8);
  background: var(--bg-alt); overflow-y: auto; min-width: 0;
}
.admin-main h1 { margin: 0 0 var(--space-5); font-size: 1.5rem; font-weight: 700; }

/* ── Stat cards ── */
.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: var(--space-4); margin-bottom: var(--space-8); }
.stat-card {
  background: var(--bg); border-radius: 14px; padding: var(--space-5);
  box-shadow: 0 1px 3px rgba(0,0,0,.04); border: .5px solid var(--line);
  transition: transform .35s cubic-bezier(.2,1,.4,1), box-shadow .35s cubic-bezier(.4,0,.2,1), border-color .25s;
}
.stat-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,.08); border-color: var(--border, rgba(0,0,0,.08)); }
.stat-card:active { transform: translateY(-1px) scale(.98); transition-duration: .08s; }
.stat-card .stat-value { font-size: var(--text-2xl); font-weight: 800; color: var(--primary, #219653); transition: color .3s; }
.stat-card .stat-label { font-size: .75rem; color: var(--muted); margin-top: var(--space-1); text-transform: uppercase; letter-spacing: .5px; }

/* ── Tables ── */
.admin-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; border-radius: 14px; border: .5px solid var(--line); }
.admin-table { width: 100%; border-collapse: collapse; background: var(--bg); min-width: 600px; }
.admin-table th {
  text-align: left; padding: var(--space-3) var(--space-4);
  background: var(--bg-alt); font-size: .75rem; font-weight: 600;
  color: var(--muted); border-bottom: .5px solid var(--line);
  text-transform: uppercase; letter-spacing: .5px;
  position: sticky; top: 0; z-index: 1;
  box-shadow: 0 2px 4px rgba(0,0,0,.02);
}
.admin-table td { padding: var(--space-3) var(--space-4); border-bottom: .5px solid var(--line); font-size: .88rem; }
.admin-table tbody tr { transition: background .25s cubic-bezier(.4,0,.2,1); }
.admin-table tbody tr:hover td { background: rgba(0,0,0,.02); }
.admin-table tbody tr:last-child td { border-bottom: none; }

/* ── Toolbar ── */
.admin-toolbar { display: flex; gap: var(--space-3); align-items: center; margin-bottom: var(--space-4); flex-wrap: wrap; }
.admin-toolbar .input { flex: 1; min-width: 200px; }

/* ── Actions ── */
.admin-actions { display: flex; gap: var(--space-2); }
.admin-actions button {
  padding: 6px var(--space-3); font-size: .8rem; border-radius: 8px;
  border: .5px solid var(--line); background: var(--bg); cursor: pointer;
  transition: background .25s, color .25s, border-color .25s, transform .35s cubic-bezier(.2,1,.4,1), box-shadow .25s;
  font-weight: 500; min-height: 36px;
}
.admin-actions button:hover { background: var(--bg-alt); }
.admin-actions button:active { transform: scale(.95); transition-duration: .08s; }
.admin-actions button:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.admin-actions .btn-danger { color: var(--error, #D94F3D); border-color: var(--error, #D94F3D); }
.admin-actions .btn-danger:hover { background: var(--error, #D94F3D); color: #fff; box-shadow: 0 2px 8px rgba(var(--danger-rgb),.2); }
.admin-actions .btn-success { color: var(--primary, #219653); border-color: var(--primary); }
.admin-actions .btn-success:hover { background: var(--primary); color: #fff; box-shadow: 0 2px 8px rgba(var(--primary-rgb),.2); }

/* ── Pagination ── */
.admin-pagination { display: flex; gap: var(--space-2); justify-content: center; margin-top: var(--space-4); }
.admin-pagination button {
  padding: var(--space-2) var(--space-4); border: .5px solid var(--line);
  border-radius: 8px; background: var(--bg); cursor: pointer;
  font-size: .85rem; font-weight: 500; min-height: 36px;
  transition: background .25s, color .25s, border-color .25s, transform .35s cubic-bezier(.2,1,.4,1), box-shadow .25s;
}
.admin-pagination button:hover:not(:disabled) { border-color: var(--primary, #219653); color: var(--primary); transform: translateY(-1px); }
.admin-pagination button:active:not(:disabled) { transform: scale(.95); transition-duration: .08s; }
.admin-pagination button:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.admin-pagination button:disabled { opacity: .35; cursor: default; }
.admin-pagination button.active { background: var(--primary); color: #fff; border-color: var(--primary); box-shadow: 0 2px 8px rgba(var(--primary-rgb),.2); }

/* ── Shared utilities ── */
.admin-loading { display: flex; align-items: center; justify-content: center; padding: var(--space-10); }
.admin-loading .spinner {
  width: 28px; height: 28px;
  border: 2.5px solid var(--line); border-top-color: var(--primary, #219653);
  border-radius: 50%; animation: admin-spin .6s linear infinite;
}
@keyframes admin-spin { to { transform: rotate(360deg); } }

.admin-refresh {
  background: none; border: .5px solid var(--line); border-radius: 8px;
  padding: var(--space-2) var(--space-3); cursor: pointer; font-size: .82rem;
  color: var(--muted); font-weight: 500; min-height: 36px;
  transition: border-color .25s, color .25s, background .25s, transform .35s cubic-bezier(.2,1,.4,1);
}
.admin-refresh:hover { border-color: var(--primary, #219653); color: var(--primary); background: rgba(var(--primary-rgb),.04); }
.admin-refresh:active { transform: scale(.95); transition-duration: .08s; }
.admin-refresh:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.admin-refresh:disabled { opacity: .35; cursor: default; }
.refresh-spin { display: inline-block; animation: admin-spin .6s linear infinite; }

.admin-head-row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-5); }
.admin-head-row h1 { margin: 0; }
.admin-muted { color: var(--muted); }
.admin-td-muted { font-size: .82rem; color: var(--muted); }
.admin-td-id { font-size: .75rem; color: var(--muted); max-width: 120px; overflow: hidden; text-overflow: ellipsis; font-family: var(--font-mono, monospace); }
.admin-td-truncate { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.admin-empty-row { text-align: center; padding: var(--space-8); color: var(--muted); font-size: .9rem; }
.admin-empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: var(--space-12); gap: var(--space-4); color: var(--muted); text-align: center; }
.admin-empty-state-icon { font-size: 3rem; opacity: .4; line-height: 1; }
.admin-empty-state-text { font-size: .9rem; }
.admin-empty-state-hint { font-size: .8rem; color: rgba(0,0,0,.3); }
.admin-section-title { font-size: 1.1rem; font-weight: 600; margin-bottom: var(--space-3); }
.admin-section-block { margin-bottom: var(--space-6); }
.admin-btn-group { display: flex; gap: var(--space-3); flex-wrap: wrap; }
.admin-form-col { display: flex; flex-direction: column; gap: var(--space-3); margin-top: var(--space-4); }
.admin-modal-actions { display: flex; gap: var(--space-3); justify-content: flex-end; margin-top: var(--space-4); }
.admin-modal-md { max-width: 600px; }
.admin-select-inline { padding: var(--space-1) var(--space-2); min-height: auto; font-size: .82rem; }
.admin-select-filter { flex: 0 0 160px; }
.admin-page-info { padding: var(--space-2) var(--space-3); font-size: .85rem; color: var(--muted); }
.admin-textarea { resize: vertical; }
.admin-code { font-family: var(--font-mono, monospace); font-size: var(--text-xs); }
.admin-th-check { width: 28px; }
.admin-label { font-weight: 600; font-size: .88rem; }
.admin-inline-add { display: flex; gap: var(--space-2); margin-top: var(--space-2); }
.admin-type-stat .stat-value { font-size: 1.3rem; }
.admin-triage-box {
  margin-top: var(--space-3); padding: var(--space-4); border: .5px solid var(--line);
  border-radius: 10px; white-space: pre-wrap; font-size: .88rem;
  background: var(--bg); line-height: 1.6;
}
.admin-trigger-result { margin-top: var(--space-3); font-size: .88rem; color: var(--muted); }
.admin-cost-note { font-size: .82rem; margin-top: var(--space-2); color: var(--muted); }
.admin-sub-value { font-size: 1rem; }
.admin-link-plain { text-decoration: none; color: inherit; }
.admin-simple-table { width: 100%; border-collapse: collapse; }
.admin-simple-table th, .admin-simple-table td { text-align: left; padding: var(--space-2) var(--space-3); border-bottom: .5px solid var(--line); vertical-align: top; }

/* ── Status badges ── */
.status-active { color: var(--primary, #219653); }
.status-banned { color: var(--error, #D94F3D); }
.status-pending { color: var(--warning, #e67e22); }
.status-resolved { color: var(--primary, #219653); }
.status-dismissed { color: var(--muted); }
.status-warn .stat-value { color: var(--warning, #e67e22); }
.status-ok .stat-value { color: var(--primary, #219653); }
.status-error .stat-value { color: var(--error, #D94F3D); }

/* ── Dark mode ── */
.dark .admin-sidebar { background: #0a0a0a; border-right-color: rgba(255,255,255,.08); }
.dark .nav-group-label { color: rgba(255,255,255,.35); }
.dark .admin-nav a { color: rgba(255,255,255,.65); }
.dark .admin-nav a:hover { color: #fff; background: rgba(255,255,255,.12); }
.dark .admin-nav a.active { background: rgba(255,255,255,.14); color: #fff; box-shadow: inset 4px 0 0 var(--primary-fg, #D98A6F); }
.dark .admin-table th { box-shadow: 0 2px 4px rgba(0,0,0,.03); }
.dark .admin-empty-state-hint { color: rgba(255,255,255,.3); }
.dark .admin-topbar { background: color-mix(in oklab, var(--bg, #1c1c1e) 85%, transparent); border-bottom-color: rgba(255,255,255,.08); }
.dark .admin-main { background: var(--bg, #1c1c1e); }
.dark .stat-card { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .stat-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.3); }
.dark .admin-table { background: var(--card, #2c2c2e); }
.dark .admin-table th { background: rgba(255,255,255,.03); }
.dark .admin-table tbody tr:hover td { background: rgba(255,255,255,.03); }
.dark .admin-table-wrap { border-color: rgba(255,255,255,.06); }
.dark .admin-actions button { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.08); color: var(--ink, #e5e5e7); }
.dark .admin-actions button:hover { background: rgba(255,255,255,.06); }
.dark .admin-refresh { border-color: rgba(255,255,255,.08); }
.dark .admin-refresh:hover { border-color: var(--primary); color: var(--primary); }
.dark .admin-pagination button { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.08); color: var(--ink); }
.dark .admin-triage-box { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .admin-simple-table th, .dark .admin-simple-table td { border-bottom-color: rgba(255,255,255,.06); }
.dark .admin-simple-table tr:hover td { background: rgba(255,255,255,.03); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .admin-sidebar { transition: none; }
  .admin-nav a:hover { transform: none; }
  .admin-nav a:active { transform: none; }
  .stat-card:hover { transform: none; }
  .stat-card:active { transform: none; }
  .admin-actions button:active { transform: none; }
  .admin-pagination button:hover:not(:disabled) { transform: none; }
  .admin-pagination button:active:not(:disabled) { transform: none; }
  .admin-refresh:active { transform: none; }
  .sidebar-toggle:active { transform: none; }
  .back-link:hover { transform: none; }
  .admin-nav a:hover .nav-icon { transform: none; }
  .toggle-icon { transition: none; }
  .admin-user-info:hover .admin-user-avatar { transform: none; }
}

/* ── Mobile ── */
@media (max-width: 768px) {
  .admin-shell { flex-direction: column; }
  .admin-sidebar {
    width: 100% !important; height: auto; flex-direction: row; padding: 0;
    align-items: center; flex-wrap: wrap; position: sticky; top: 0; z-index: var(--z-sticky);
  }
  .admin-sidebar-head { border-bottom: none; padding: var(--space-3) var(--space-4); }
  .admin-brand small { display: none; }
  .admin-nav {
    flex-direction: row; flex-wrap: nowrap; gap: var(--space-1);
    overflow-x: auto; padding: 0 var(--space-3) var(--space-2);
    -webkit-overflow-scrolling: touch;
    scroll-snap-type: x proximity;
    mask-image: linear-gradient(to right, #000 90%, transparent);
    -webkit-mask-image: linear-gradient(to right, #000 90%, transparent);
  }
  .admin-nav:hover, .admin-nav:focus-within { mask-image: none; -webkit-mask-image: none; }
  .nav-group { display: contents; }
  .nav-group-label { display: none; }
  .admin-nav a { padding: var(--space-2) var(--space-3); font-size: .78rem; white-space: nowrap; scroll-snap-align: start; min-height: 36px; }
  .nav-text { display: inline !important; }
  .admin-nav a.active { box-shadow: none; background: rgba(255,255,255,.15); }
  .admin-sidebar-footer { display: none; }
  .admin-main { padding: var(--space-4); }
  .admin-topbar { margin: calc(var(--space-4) * -1) calc(var(--space-4) * -1) var(--space-4); padding: var(--space-3) var(--space-4); }
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .admin-table { font-size: .82rem; }
  .admin-table th, .admin-table td { padding: var(--space-2) var(--space-3); }
  .admin-toolbar .input { min-width: 140px; }
  .sidebar-toggle { display: none; }
  .collapsed .admin-nav a[title]:hover::after { display: none; }
}

/* ── Toast / feedback (shared across admin pages) ── */
.admin-toast {
  position: fixed; bottom: var(--space-4); right: var(--space-4);
  z-index: var(--z-toast, 600); padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-sm, 10px); background: var(--bg, #fff);
  border: 1px solid var(--line); box-shadow: var(--shadow-lg);
  font-size: .88rem; color: var(--ink);
  animation: toastIn .25s var(--ease-out, ease-out);
}
.admin-toast.success { border-left: 4px solid var(--secondary, #219653); }
.admin-toast.error { border-left: 4px solid var(--error, #D94F3D); }
.admin-toast.warning { border-left: 4px solid var(--warning, #e67e22); }
@keyframes toastIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.dark .admin-toast { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.08); }
@media (prefers-reduced-motion: reduce) {
  .admin-toast { animation: none; }
}
/* ── Help tooltip ── */
.admin-help {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; border-radius: 50%;
  background: rgba(142,142,147,.12); color: var(--muted);
  font-size: .65rem; font-weight: 700; cursor: help;
  position: relative; vertical-align: middle; margin-left: 4px;
}
.admin-help::after {
  content: attr(data-tip); position: absolute; bottom: calc(100% + 6px); left: 50%;
  transform: translateX(-50%); padding: 6px 10px; border-radius: 8px;
  background: var(--ink, #1a1a2e); color: #fff; font-size: .72rem; font-weight: 400;
  white-space: nowrap; pointer-events: none; opacity: 0; transition: opacity .15s;
  z-index: var(--z-sticky); max-width: 260px; white-space: normal; line-height: 1.4;
}
.admin-help:hover::after, .admin-help:focus::after { opacity: 1; }
</style>
