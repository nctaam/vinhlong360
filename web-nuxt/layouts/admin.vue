<template>
  <div class="admin-shell">
    <aside class="admin-sidebar">
      <NuxtLink class="admin-brand" to="/admin">
        <span class="logo">vinhlong<span class="dot">360</span></span>
        <small>AdminCP</small>
      </NuxtLink>
      <nav class="admin-nav" aria-label="Menu quản trị">
        <NuxtLink to="/admin/data-quality" :class="{ active: route.path === '/admin/data-quality' }">Dữ liệu</NuxtLink>
        <NuxtLink to="/admin" :class="{ active: route.path === '/admin' }">📊 Dashboard</NuxtLink>
        <NuxtLink to="/admin/entities" :class="{ active: route.path === '/admin/entities' }">📋 Entities</NuxtLink>
        <NuxtLink to="/admin/chua-phan-loai" :class="{ active: route.path === '/admin/chua-phan-loai' }">📍 Chưa phân loại</NuxtLink>
        <NuxtLink to="/admin/danh-ba" :class="{ active: route.path === '/admin/danh-ba' }">🏛️ Danh bạ</NuxtLink>
        <NuxtLink to="/admin/lich-trinh" :class="{ active: route.path === '/admin/lich-trinh' }">🗺️ Lịch trình</NuxtLink>
        <NuxtLink to="/admin/kiem-duyet" :class="{ active: route.path === '/admin/kiem-duyet' }">🛡️ Kiểm duyệt</NuxtLink>
        <NuxtLink to="/admin/users" :class="{ active: route.path === '/admin/users' }">👥 Users</NuxtLink>
        <NuxtLink to="/admin/bao-cao" :class="{ active: route.path === '/admin/bao-cao' }">🚩 Báo cáo</NuxtLink>
        <NuxtLink to="/admin/thong-ke" :class="{ active: route.path === '/admin/thong-ke' }">📈 Thống kê</NuxtLink>
        <NuxtLink to="/admin/duyet-tu-hoc" :class="{ active: route.path === '/admin/duyet-tu-hoc' }">🧪 Duyệt & Tiện ích</NuxtLink>
        <NuxtLink to="/admin/ai" :class="{ active: route.path === '/admin/ai' }">🤖 Knowledge Agent</NuxtLink>
      </nav>
      <div class="admin-sidebar-footer">
        <NuxtLink to="/">← Về trang chủ</NuxtLink>
      </div>
    </aside>
    <main class="admin-main">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const { user, fetchMe, token } = useAuth()

useHead({
  meta: [{ name: 'robots', content: 'noindex,nofollow' }],
})

onMounted(async () => {
  if (!user.value && token.value) await fetchMe()
})
</script>

<style>
.admin-shell { display: flex; min-height: 100vh; }
.admin-sidebar {
  width: 220px; background: var(--ink, #1a1a2e); color: var(--text-on-dark, #fff);
  display: flex; flex-direction: column; padding: var(--space-5) 0; flex-shrink: 0;
}
.admin-brand { display: block; text-align: center; padding: 0 var(--space-4) var(--space-5); text-decoration: none; color: var(--text-on-dark, #fff); }
.admin-brand .logo { font-size: 1.2rem; font-weight: 800; }
.admin-brand .dot { color: var(--accent, #f5c518); }
.admin-brand small { display: block; font-size: .72rem; opacity: .6; margin-top: 2px; letter-spacing: 2px; text-transform: uppercase; }
.admin-nav { flex: 1; display: flex; flex-direction: column; gap: 2px; padding: 0 var(--space-2); }
.admin-nav a {
  display: block; padding: var(--space-3) var(--space-4); border-radius: var(--radius-sm, 10px);
  color: rgba(255,255,255,.65); text-decoration: none; font-size: .88rem; font-weight: 500;
  transition: background .3s var(--ease-out), color .3s var(--ease-out), transform .35s var(--ease-spring-gentle);
}
.admin-nav a:active { transform: scale(.97); }
.admin-nav a:hover { background: rgba(255,255,255,.08); color: var(--text-on-dark, #fff); }
.admin-nav a.active { background: rgba(255,255,255,.14); color: var(--text-on-dark, #fff); font-weight: 700; }
.admin-sidebar-footer { padding: var(--space-4); border-top: .5px solid rgba(255,255,255,.1); }
.admin-sidebar-footer a { color: rgba(255,255,255,.5); text-decoration: none; font-size: .82rem; transition: color .3s var(--ease-out); }
.admin-sidebar-footer a:hover { color: var(--text-on-dark, #fff); }
.admin-main { flex: 1; padding: var(--space-8) var(--space-8); background: var(--bg-alt); overflow-y: auto; }
.admin-main h1 { margin: 0 0 var(--space-5); font-size: 1.5rem; }

.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: var(--space-4); margin-bottom: var(--space-8); }
.stat-card { background: var(--bg); border-radius: var(--radius-md, 14px); padding: var(--space-5); box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,.06)); transition: transform .35s var(--ease-spring-gentle), box-shadow .35s var(--ease-out-expo); border: .5px solid transparent; }
.stat-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md, 0 4px 12px rgba(0,0,0,.08)); }
.stat-card .stat-value { font-size: var(--text-2xl); font-weight: var(--weight-extrabold); color: var(--primary, #219653); }
.stat-card .stat-label { font-size: var(--text-xs); color: var(--muted); margin-top: var(--space-1); }

.admin-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; border-radius: var(--radius-md, 14px); box-shadow: var(--shadow-sm, 0 1px 3px rgba(0,0,0,.06)); }
.admin-table { width: 100%; border-collapse: collapse; background: var(--bg); min-width: 600px; }
.admin-table th { text-align: left; padding: var(--space-3) var(--space-4); background: var(--bg-alt); font-size: .82rem; font-weight: 700; color: var(--muted); border-bottom: .5px solid var(--line); }
.admin-table td { padding: var(--space-3) var(--space-4); border-bottom: .5px solid var(--line); font-size: .88rem; }
.admin-table tr:hover td { background: rgba(0,0,0,.015); }

.admin-toolbar { display: flex; gap: var(--space-3); align-items: center; margin-bottom: var(--space-4); flex-wrap: wrap; }
.admin-toolbar .input { flex: 1; min-width: 200px; }

.admin-actions { display: flex; gap: var(--space-2); }
.admin-actions button { padding: 5px var(--space-3); font-size: .8rem; border-radius: var(--radius-sm, 10px); border: .5px solid var(--line); background: var(--bg); cursor: pointer; transition: background .3s var(--ease-out), color .3s var(--ease-out), border-color .3s var(--ease-out), transform .35s var(--ease-spring-gentle); }
.admin-actions button:hover { background: var(--bg-alt, #f0f0f0); }
.admin-actions button:active { transform: scale(.95); }
.admin-actions .btn-danger { color: var(--error, #D94F3D); border-color: var(--error, #D94F3D); }
.admin-actions .btn-danger:hover { background: var(--error, #D94F3D); color: var(--text-on-dark, #fff); }
.admin-actions .btn-success { color: var(--primary, #219653); border-color: var(--primary); }
.admin-actions .btn-success:hover { background: var(--primary); color: var(--text-on-dark, #fff); }

.admin-pagination { display: flex; gap: var(--space-2); justify-content: center; margin-top: var(--space-4); }
.admin-pagination button { padding: var(--space-2) var(--space-4); border: .5px solid var(--line); border-radius: var(--radius-sm, 10px); background: var(--bg); cursor: pointer; font-size: .85rem; transition: background .3s var(--ease-out), border-color .3s var(--ease-out), color .3s var(--ease-out), transform .35s var(--ease-spring-gentle); }
.admin-pagination button:hover:not(:disabled) { border-color: var(--primary, #219653); color: var(--primary); }
.admin-pagination button:active:not(:disabled) { transform: scale(.95); }
.admin-pagination button:disabled { opacity: .4; cursor: default; }
.admin-pagination button.active { background: var(--primary); color: var(--text-on-dark, #fff); border-color: var(--primary); }

/* ── Shared admin utility classes ── */
.admin-loading { text-align: center; padding: var(--space-10); }
.admin-loading .spinner { width: 32px; height: 32px; border: 3px solid var(--line); border-top-color: var(--primary, #219653); border-radius: 50%; animation: admin-spin .7s linear infinite; margin: 0 auto var(--space-2); }
@keyframes admin-spin { to { transform: rotate(360deg); } }
.admin-refresh { background: none; border: .5px solid var(--line); border-radius: var(--radius-sm, 10px); padding: var(--space-2) var(--space-3); cursor: pointer; font-size: .85rem; color: var(--muted); transition: border-color .3s var(--ease-out), color .3s var(--ease-out); }
.admin-refresh:hover { border-color: var(--primary, #219653); color: var(--primary); }
.admin-refresh:disabled { opacity: .4; cursor: default; }
.admin-head-row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-5); }
.admin-head-row h1 { margin: 0; }
.admin-muted { color: var(--muted); }
.admin-td-muted { font-size: .82rem; color: var(--muted); }
.admin-td-id { font-size: .78rem; color: var(--muted); max-width: 120px; overflow: hidden; text-overflow: ellipsis; }
.admin-td-truncate { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.admin-empty-row { text-align: center; padding: var(--space-5); color: var(--muted); }
.admin-section-title { font-size: 1.1rem; margin-bottom: var(--space-3); }
.admin-section-block { margin-bottom: var(--space-6); }
.admin-btn-group { display: flex; gap: var(--space-3); flex-wrap: wrap; }
.admin-form-col { display: flex; flex-direction: column; gap: var(--space-3); margin-top: var(--space-4); }
.admin-modal-actions { display: flex; gap: var(--space-3); justify-content: flex-end; margin-top: var(--space-4); }
.admin-modal-md { max-width: 600px; }
.admin-select-inline { padding: var(--space-1) var(--space-2); min-height: auto; font-size: .82rem; }
.admin-select-filter { flex: 0 0 160px; }
.admin-page-info { padding: var(--space-2) var(--space-3); font-size: .85rem; }
.admin-textarea { resize: vertical; }
.admin-code { font-family: monospace; font-size: var(--text-xs); }
.admin-th-check { width: 28px; }
.admin-label { font-weight: 600; font-size: .88rem; }
.admin-inline-add { display: flex; gap: var(--space-2); margin-top: var(--space-2); }
.admin-type-stat .stat-value { font-size: 1.3rem; }
.admin-triage-box { margin-top: var(--space-3); padding: var(--space-3); border: .5px solid var(--line); border-radius: var(--radius-sm, 10px); white-space: pre-wrap; font-size: .9rem; }
.admin-trigger-result { margin-top: var(--space-3); font-size: .88rem; color: var(--muted); }
.admin-cost-note { font-size: .82rem; margin-top: var(--space-2); }
.admin-sub-value { font-size: 1rem; }
.admin-link-plain { text-decoration: none; color: inherit; }
.admin-simple-table { width: 100%; border-collapse: collapse; }
.admin-simple-table th, .admin-simple-table td { text-align: left; padding: var(--space-2); border-bottom: .5px solid rgba(0,0,0,.08); vertical-align: top; }
.status-active { color: var(--primary, #219653); }
.status-banned { color: var(--error, #D94F3D); }
.status-pending { color: var(--warning, #e67e22); }
.status-resolved { color: var(--primary, #219653); }
.status-dismissed { color: var(--muted); }
.status-warn .stat-value { color: var(--warning, #e67e22); }
.status-ok .stat-value { color: var(--primary, #219653); }
.status-error .stat-value { color: var(--error, #D94F3D); }

/* ── Dark mode ── */
.dark .admin-main { background: var(--bg, #1c1c1e); }
.dark .stat-card { background: var(--card, #2c2c2e); box-shadow: var(--shadow-sm); border-color: var(--line, rgba(255,255,255,.08)); }
.dark .stat-card:hover { box-shadow: var(--shadow-md); }
.dark .admin-table { background: var(--card, #2c2c2e); }
.dark .admin-table th { background: rgba(255,255,255,.04); }
.dark .admin-table tr:hover td { background: rgba(255,255,255,.03); }
.dark .admin-actions button { background: var(--card, #2c2c2e); border-color: var(--line, rgba(255,255,255,.1)); color: var(--ink, #e5e5e7); }
.dark .admin-actions button:hover { background: rgba(255,255,255,.06); }
.dark .admin-refresh { border-color: var(--line, rgba(255,255,255,.1)); color: var(--muted); }
.dark .admin-refresh:hover { border-color: var(--primary); color: var(--primary); }
.dark .admin-pagination button { background: var(--card, #2c2c2e); border-color: var(--line); color: var(--ink); }
.dark .admin-table-wrap { box-shadow: var(--shadow-sm); }
.dark .admin-triage-box { background: var(--card, #2c2c2e); border-color: var(--line); }
.dark .admin-simple-table th, .dark .admin-simple-table td { border-bottom-color: rgba(255,255,255,.08); }
.dark .admin-simple-table tr:hover td { background: rgba(255,255,255,.03); }

@media (max-width: 768px) {
  .admin-shell { flex-direction: column; }
  .admin-sidebar { width: 100%; flex-direction: row; padding: var(--space-3); align-items: center; flex-wrap: wrap; }
  .admin-brand { padding: 0 var(--space-3) 0 0; }
  .admin-brand small { display: none; }
  .admin-nav { flex-direction: row; flex-wrap: wrap; gap: var(--space-1); overflow-x: auto; }
  .admin-nav a { padding: var(--space-2) var(--space-3); font-size: .8rem; white-space: nowrap; }
  .admin-sidebar-footer { display: none; }
  .admin-main { padding: var(--space-4); }
  .admin-table { font-size: .82rem; }
  .admin-table th, .admin-table td { padding: var(--space-2) var(--space-3); }
  .admin-toolbar .input { min-width: 140px; }
}
</style>
