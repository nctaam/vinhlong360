<template>
  <div class="admin-shell">
    <aside class="admin-sidebar">
      <NuxtLink class="admin-brand" to="/admin">
        <span class="logo">vinhlong<span class="dot">360</span></span>
        <small>AdminCP</small>
      </NuxtLink>
      <nav class="admin-nav">
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
  width: 220px; background: var(--ink, #1a1a2e); color: #fff;
  display: flex; flex-direction: column; padding: 20px 0; flex-shrink: 0;
}
.admin-brand { display: block; text-align: center; padding: 0 16px 20px; text-decoration: none; color: #fff; }
.admin-brand .logo { font-size: 1.2rem; font-weight: 800; }
.admin-brand .dot { color: var(--accent, #f5c518); }
.admin-brand small { display: block; font-size: .72rem; opacity: .6; margin-top: 2px; letter-spacing: 2px; text-transform: uppercase; }
.admin-nav { flex: 1; display: flex; flex-direction: column; gap: 2px; padding: 0 8px; }
.admin-nav a {
  display: block; padding: 10px 14px; border-radius: 8px;
  color: rgba(255,255,255,.7); text-decoration: none; font-size: .88rem; font-weight: 500;
  transition: background .15s, color .15s, transform .1s;
}
.admin-nav a:active { transform: scale(.97); }
.admin-nav a:hover { background: rgba(255,255,255,.08); color: #fff; }
.admin-nav a.active { background: rgba(255,255,255,.14); color: #fff; font-weight: 700; }
.admin-sidebar-footer { padding: 16px; border-top: 1px solid rgba(255,255,255,.1); }
.admin-sidebar-footer a { color: rgba(255,255,255,.5); text-decoration: none; font-size: .82rem; }
.admin-sidebar-footer a:hover { color: #fff; }
.admin-main { flex: 1; padding: 28px 32px; background: var(--bg-alt, #f6f7f9); overflow-y: auto; }
.admin-main h1 { margin: 0 0 20px; font-size: 1.5rem; }

.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; margin-bottom: 28px; }
.stat-card { background: var(--bg, #fff); border-radius: 12px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,.06); transition: transform var(--duration-normal, .2s) var(--ease-spring, ease), box-shadow var(--duration-normal, .2s); border: 1px solid transparent; }
.stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.08); }
.stat-card .stat-value { font-size: 1.8rem; font-weight: 800; color: var(--primary, #219653); }
.stat-card .stat-label { font-size: .82rem; color: var(--muted, #888); margin-top: 4px; }

.admin-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
.admin-table { width: 100%; border-collapse: collapse; background: var(--bg, #fff); min-width: 600px; }
.admin-table th { text-align: left; padding: 12px 14px; background: var(--bg-alt, #f6f7f9); font-size: .82rem; font-weight: 700; color: var(--muted); border-bottom: 1px solid var(--line, #eee); }
.admin-table td { padding: 10px 14px; border-bottom: 1px solid var(--line, #eee); font-size: .88rem; }
.admin-table tr:hover td { background: rgba(0,0,0,.015); }

.admin-toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.admin-toolbar .input { flex: 1; min-width: 200px; }

.admin-actions { display: flex; gap: 6px; }
.admin-actions button { padding: 5px 10px; font-size: .8rem; border-radius: 6px; border: 1px solid var(--line, #ddd); background: var(--bg, #fff); cursor: pointer; transition: background .12s, color .12s, border-color .12s, transform .1s; }
.admin-actions button:hover { background: var(--bg-alt, #f0f0f0); }
.admin-actions button:active { transform: scale(.95); }
.admin-actions .btn-danger { color: var(--error, #D94F3D); border-color: var(--error, #D94F3D); }
.admin-actions .btn-danger:hover { background: var(--error, #D94F3D); color: #fff; }
.admin-actions .btn-success { color: var(--primary, #219653); border-color: var(--primary); }
.admin-actions .btn-success:hover { background: var(--primary); color: #fff; }

.admin-pagination { display: flex; gap: 8px; justify-content: center; margin-top: 16px; }
.admin-pagination button { padding: 6px 14px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); cursor: pointer; font-size: .85rem; transition: background .12s, border-color .12s, transform .1s; }
.admin-pagination button:hover:not(:disabled) { border-color: var(--primary, #219653); color: var(--primary); }
.admin-pagination button:active:not(:disabled) { transform: scale(.95); }
.admin-pagination button:disabled { opacity: .4; cursor: default; }
.admin-pagination button.active { background: var(--primary); color: #fff; border-color: var(--primary); }

/* ── Shared admin utility classes ── */
.admin-loading { text-align: center; padding: 40px; }
.admin-loading .spinner { width: 32px; height: 32px; border: 3px solid var(--line, #eee); border-top-color: var(--primary, #219653); border-radius: 50%; animation: admin-spin .7s linear infinite; margin: 0 auto 8px; }
@keyframes admin-spin { to { transform: rotate(360deg); } }
.admin-refresh { background: none; border: 1px solid var(--line, #ddd); border-radius: 8px; padding: 6px 12px; cursor: pointer; font-size: .85rem; color: var(--muted, #888); transition: all .15s; }
.admin-refresh:hover { border-color: var(--primary, #219653); color: var(--primary); }
.admin-refresh:disabled { opacity: .4; cursor: default; }
.admin-head-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 20px; }
.admin-head-row h1 { margin: 0; }
.admin-muted { color: var(--muted, #888); }
.admin-td-muted { font-size: .82rem; color: var(--muted, #888); }
.admin-td-id { font-size: .78rem; color: var(--muted, #888); max-width: 120px; overflow: hidden; text-overflow: ellipsis; }
.admin-td-truncate { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.admin-empty-row { text-align: center; padding: 20px; color: var(--muted, #888); }
.admin-section-title { font-size: 1.1rem; margin-bottom: 10px; }
.admin-section-block { margin-bottom: 24px; }
.admin-btn-group { display: flex; gap: 12px; flex-wrap: wrap; }
.admin-form-col { display: flex; flex-direction: column; gap: 12px; margin-top: 16px; }
.admin-modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 16px; }
.admin-modal-md { max-width: 600px; }
.admin-select-inline { padding: 4px 8px; min-height: auto; font-size: .82rem; }
.admin-select-filter { flex: 0 0 160px; }
.admin-page-info { padding: 6px 10px; font-size: .85rem; }
.admin-textarea { resize: vertical; }
.admin-label { font-weight: 600; font-size: .88rem; }
.admin-inline-add { display: flex; gap: 6px; margin-top: 6px; }
.admin-type-stat .stat-value { font-size: 1.3rem; }
.admin-triage-box { margin-top: 12px; padding: 12px; border: 1px solid var(--line, #eee); border-radius: 8px; white-space: pre-wrap; font-size: .9rem; }
.admin-trigger-result { margin-top: 10px; font-size: .88rem; color: var(--muted, #888); }
.admin-cost-note { font-size: .82rem; margin-top: 6px; }
.admin-sub-value { font-size: 1rem; }
.admin-link-plain { text-decoration: none; color: inherit; }
.admin-simple-table { width: 100%; border-collapse: collapse; }
.admin-simple-table th, .admin-simple-table td { text-align: left; padding: 8px; border-bottom: 1px solid rgba(0,0,0,.08); vertical-align: top; }
.status-active { color: var(--primary, #219653); }
.status-banned { color: var(--error, #D94F3D); }
.status-pending { color: var(--warning, #e67e22); }
.status-resolved { color: var(--primary, #219653); }
.status-dismissed { color: var(--muted, #888); }
.status-warn .stat-value { color: var(--warning, #e67e22); }
.status-ok .stat-value { color: var(--primary, #219653); }
.status-error .stat-value { color: var(--error, #D94F3D); }

/* ── Dark mode ── */
.dark .admin-main { background: var(--bg, #1c1c1e); }
.dark .stat-card { background: var(--card, #2c2c2e); box-shadow: 0 1px 3px rgba(0,0,0,.2); border-color: var(--line, rgba(255,255,255,.08)); }
.dark .stat-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.3); }
.dark .admin-table { background: var(--card, #2c2c2e); }
.dark .admin-table th { background: rgba(255,255,255,.04); }
.dark .admin-table tr:hover td { background: rgba(255,255,255,.03); }
.dark .admin-actions button { background: var(--card, #2c2c2e); border-color: var(--line, rgba(255,255,255,.1)); color: var(--ink, #e5e5e7); }
.dark .admin-actions button:hover { background: rgba(255,255,255,.06); }
.dark .admin-refresh { border-color: var(--line, rgba(255,255,255,.1)); color: var(--muted); }
.dark .admin-refresh:hover { border-color: var(--primary); color: var(--primary); }
.dark .admin-pagination button { background: var(--card, #2c2c2e); border-color: var(--line); color: var(--ink); }
.dark .admin-table-wrap { box-shadow: 0 1px 3px rgba(0,0,0,.2); }
.dark .admin-triage-box { background: var(--card, #2c2c2e); border-color: var(--line); }
.dark .admin-simple-table th, .dark .admin-simple-table td { border-bottom-color: rgba(255,255,255,.08); }
.dark .admin-simple-table tr:hover td { background: rgba(255,255,255,.03); }

@media (max-width: 768px) {
  .admin-shell { flex-direction: column; }
  .admin-sidebar { width: 100%; flex-direction: row; padding: 10px; align-items: center; flex-wrap: wrap; }
  .admin-brand { padding: 0 12px 0 0; }
  .admin-brand small { display: none; }
  .admin-nav { flex-direction: row; flex-wrap: wrap; gap: 4px; overflow-x: auto; }
  .admin-nav a { padding: 6px 10px; font-size: .8rem; white-space: nowrap; }
  .admin-sidebar-footer { display: none; }
  .admin-main { padding: 16px; }
  .admin-table { font-size: .82rem; }
  .admin-table th, .admin-table td { padding: 8px 10px; }
  .admin-toolbar .input { min-width: 140px; }
}
</style>
