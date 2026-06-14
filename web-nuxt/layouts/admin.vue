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
        <NuxtLink to="/admin/lich-trinh" :class="{ active: route.path === '/admin/lich-trinh' }">🗺️ Lịch trình</NuxtLink>
        <NuxtLink to="/admin/kiem-duyet" :class="{ active: route.path === '/admin/kiem-duyet' }">🛡️ Kiểm duyệt</NuxtLink>
        <NuxtLink to="/admin/users" :class="{ active: route.path === '/admin/users' }">👥 Users</NuxtLink>
        <NuxtLink to="/admin/bao-cao" :class="{ active: route.path === '/admin/bao-cao' }">🚩 Báo cáo</NuxtLink>
        <NuxtLink to="/admin/thong-ke" :class="{ active: route.path === '/admin/thong-ke' }">📈 Thống kê</NuxtLink>
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
  transition: background .15s, color .15s;
}
.admin-nav a:hover { background: rgba(255,255,255,.08); color: #fff; }
.admin-nav a.active { background: rgba(255,255,255,.14); color: #fff; font-weight: 700; }
.admin-sidebar-footer { padding: 16px; border-top: 1px solid rgba(255,255,255,.1); }
.admin-sidebar-footer a { color: rgba(255,255,255,.5); text-decoration: none; font-size: .82rem; }
.admin-sidebar-footer a:hover { color: #fff; }
.admin-main { flex: 1; padding: 28px 32px; background: var(--bg-alt, #f6f7f9); overflow-y: auto; }
.admin-main h1 { margin: 0 0 20px; font-size: 1.5rem; }

.stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; margin-bottom: 28px; }
.stat-card { background: var(--bg, #fff); border-radius: 12px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
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
.admin-actions button { padding: 5px 10px; font-size: .8rem; border-radius: 6px; border: 1px solid var(--line, #ddd); background: var(--bg, #fff); cursor: pointer; }
.admin-actions button:hover { background: var(--bg-alt, #f0f0f0); }
.admin-actions .btn-danger { color: #D94F3D; border-color: #D94F3D; }
.admin-actions .btn-danger:hover { background: #D94F3D; color: #fff; }
.admin-actions .btn-success { color: var(--primary, #219653); border-color: var(--primary); }
.admin-actions .btn-success:hover { background: var(--primary); color: #fff; }

.admin-pagination { display: flex; gap: 8px; justify-content: center; margin-top: 16px; }
.admin-pagination button { padding: 6px 14px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); cursor: pointer; font-size: .85rem; }
.admin-pagination button:disabled { opacity: .4; cursor: default; }
.admin-pagination button.active { background: var(--primary); color: #fff; border-color: var(--primary); }

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
