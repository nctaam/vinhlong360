<template>
  <div>
    <div class="admin-head-row">
      <div>
        <NuxtLink to="/admin/cai-dat" class="cs-back">← Cài đặt</NuxtLink>
        <h1>Danh mục</h1>
        <p class="cs-subtitle">Ghi đè emoji & nhãn cho loại địa điểm và khu vực</p>
      </div>
    </div>

    <div class="cs-help">
      <p>Chỉ điền những mục muốn đổi. Bỏ trống = giữ mặc định. Ví dụ ghi đè emoji món ăn:</p>
      <pre>{ "dish": { "emoji": "🍜" } }</pre>
      <p class="cs-help-keys"><strong>Loại entity:</strong> experience, product, dish, craft_village, attraction, accommodation, nature, history, event, drink — mỗi loại có <code>emoji</code>, <code>label</code>.</p>
      <p class="cs-help-keys"><strong>Khu vực:</strong> vinh-long, ben-tre, tra-vinh — mỗi vùng có <code>name</code>, <code>emoji</code>, <code>blurb</code>.</p>
      <p class="cs-help-keys"><strong>Loại cơ quan (danh bạ):</strong> ubnd, cong_an, y_te, truong_hoc, buu_dien, tu_phap, khac — mỗi loại có <code>emoji</code>, <code>label</code>.</p>
      <p class="cs-help-keys"><strong>Chủ đề khám phá:</strong> am-thuc, thien-nhien, van-hoa, lang-nghe, mua-sam — mỗi chủ đề có <code>emoji</code>, <code>label</code>, <code>description</code>, <code>types[]</code>.</p>
    </div>

    <div v-if="loading" class="cs-skeleton">
      <div class="cs-skel-row" v-for="n in 2" :key="n"><div class="cs-skel-label"></div><div class="cs-skel-input cs-skel-tall"></div></div>
    </div>
    <Transition name="cs-fade">
      <div v-if="!loading" class="cs-form-wrap">
        <AdminSettingsForm :category="'categories'" :fields="fields" @saved="reload" />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Danh mục — Admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const fields = ref<any[]>([])
const loading = ref(true)

async function reload() {
  loading.value = true
  try {
    const r = await $fetch<any>('/admin-api/site-settings/categories', { headers: authHeaders() })
    fields.value = r.settings || []
  } catch { showToast('Không thể tải cài đặt', 'error') }
  loading.value = false
}
onMounted(reload)
</script>

<style scoped>
.cs-back { font-size: .82rem; color: var(--muted); text-decoration: none; transition: color .15s; }
.cs-back:hover { color: var(--primary, #219653); }
.cs-subtitle { font-size: .82rem; color: var(--muted); margin-top: var(--space-1); }
.cs-form-wrap { max-width: 640px; }

.cs-help {
  max-width: 640px; margin-bottom: var(--space-5); padding: var(--space-4);
  background: rgba(var(--primary-rgb),.04); border: .5px solid var(--line); border-radius: 12px;
  font-size: .82rem; color: var(--muted); line-height: 1.5;
}
.cs-help p { margin: 0 0 var(--space-2); }
.cs-help p:last-child { margin-bottom: 0; }
.cs-help pre {
  margin: 0 0 var(--space-2); padding: var(--space-2) var(--space-3); border-radius: 8px;
  background: var(--bg); border: .5px solid var(--line);
  font-family: 'SF Mono', 'Cascadia Code', monospace; font-size: .78rem; color: var(--ink);
  overflow-x: auto;
}
.cs-help-keys code { font-family: 'SF Mono', monospace; font-size: .75rem; color: var(--primary, #219653); }

.cs-skeleton { max-width: 640px; display: flex; flex-direction: column; gap: var(--space-5); }
.cs-skel-row { display: flex; flex-direction: column; gap: var(--space-2); }
.cs-skel-label { width: 120px; height: 14px; border-radius: 6px; background: var(--line); animation: cs-pulse 1.5s var(--ease-in-out) infinite; }
.cs-skel-input { width: 100%; height: 44px; border-radius: 10px; background: var(--line); opacity: .5; animation: cs-pulse 1.5s var(--ease-in-out) .15s infinite; }
.cs-skel-tall { height: 120px; }
@keyframes cs-pulse { 0%, 100% { opacity: .4; } 50% { opacity: .7; } }
.cs-fade-enter-active { transition: opacity .3s var(--ease-soft), transform .3s var(--ease-soft); }
.cs-fade-enter-from { opacity: 0; transform: translateY(6px); }
@media (prefers-reduced-motion: reduce) {
  .cs-skel-label, .cs-skel-input { animation: none; }
  .cs-fade-enter-active { transition: none; }
}
.dark .cs-help { background: rgba(var(--primary-rgb),.08); }
.dark .cs-help pre { background: var(--card, #2c2c2e); }
</style>
