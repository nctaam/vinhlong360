<template>
  <div>
    <div class="admin-head-row">
      <div>
        <NuxtLink to="/admin/cai-dat" class="cs-back">← Cài đặt</NuxtLink>
        <h1>Nội dung trang</h1>
        <p class="cs-subtitle">Sửa tiêu đề, mô tả & SEO của từng trang</p>
      </div>
    </div>

    <div class="cs-grid">
      <NuxtLink v-for="(p, i) in pages" :key="p.slug" :to="`/admin/cai-dat/trang/${p.slug}`" class="cs-card" :style="{ '--stagger': `${i * 40}ms` }">
        <span class="cs-icon">{{ p.icon }}</span>
        <div>
          <h3>{{ p.title }}</h3>
          <p>{{ p.route }}</p>
        </div>
        <span class="cs-arrow" aria-hidden="true">›</span>
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { PAGE_MANIFEST_LIST } from '~/utils/pageManifest'
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Quản lý trang — Admin' })
const pages = PAGE_MANIFEST_LIST
</script>

<style scoped>
.cs-back { font-size: .82rem; color: var(--muted); text-decoration: none; transition: color .15s; }
.cs-back:hover { color: var(--primary, #219653); }
.cs-subtitle { font-size: .82rem; color: var(--muted); margin-top: 4px; }
.cs-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: var(--space-4); }
.cs-card {
  display: flex; align-items: center; gap: var(--space-4);
  padding: var(--space-5); border-radius: 14px;
  background: var(--bg); border: .5px solid var(--line);
  text-decoration: none; color: inherit; min-height: 80px;
  animation: cs-fade-in .4s cubic-bezier(.2,1,.4,1) both; animation-delay: var(--stagger, 0ms);
  transition: transform .3s cubic-bezier(.2,1,.4,1), box-shadow .3s, border-color .3s;
}
.cs-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,.06); border-color: var(--primary, #219653); }
.cs-card:active { transform: scale(.98); }
.cs-card:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.cs-icon { font-size: 1.8rem; flex-shrink: 0; width: 40px; text-align: center; }
.cs-card div { flex: 1; min-width: 0; }
.cs-card h3 { margin: 0; font-size: .95rem; font-weight: 600; }
.cs-card p { margin: var(--space-1) 0 0; font-size: .78rem; color: var(--muted); font-family: 'SF Mono', monospace; }
.cs-arrow { font-size: 1.4rem; font-weight: 300; color: var(--muted); flex-shrink: 0; opacity: .4; transition: opacity .2s, transform .2s cubic-bezier(.2,1,.4,1); }
.cs-card:hover .cs-arrow { opacity: .8; transform: translateX(3px); }
@keyframes cs-fade-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
.dark .cs-card { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .cs-card:hover { box-shadow: 0 6px 20px rgba(0,0,0,.3); }
@media (prefers-reduced-motion: reduce) {
  .cs-card { animation: none; }
  .cs-card:hover, .cs-card:active { transform: none; }
  .cs-card:hover .cs-arrow { transform: none; }
}
</style>
