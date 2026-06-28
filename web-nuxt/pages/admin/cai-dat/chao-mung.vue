<template>
  <div>
    <div class="admin-head-row">
      <div>
        <NuxtLink to="/admin/cai-dat" class="cs-back">← Cài đặt</NuxtLink>
        <h1>Bảng chào mừng</h1>
        <p class="cs-subtitle">Nội dung hiện cho khách lần đầu truy cập (onboarding)</p>
      </div>
    </div>

    <p class="cs-hint">Bật/tắt bảng này ở mục <NuxtLink to="/admin/cai-dat/tinh-nang" class="cs-link">Tính năng</NuxtLink> (cờ "Hướng dẫn lần đầu").</p>

    <div v-if="loading" class="cs-skeleton">
      <div class="cs-skel-row" v-for="n in 4" :key="n"><div class="cs-skel-label"></div><div class="cs-skel-input"></div></div>
    </div>
    <Transition name="cs-fade">
      <div v-if="!loading" class="cs-form-wrap">
        <AdminSettingsForm :category="'onboarding'" :object-key="'onboarding'" :object-value="value" :fields="fields" @saved="reload" />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { DEFAULT_ONBOARDING } from '~/utils/onboardingContent'
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Chào mừng — Admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const loading = ref(true)
const value = ref<Record<string, any>>({})

const fields = [
  { key: 'emoji', label: 'Emoji', input_type: 'text' },
  { key: 'title', label: 'Tiêu đề', input_type: 'text' },
  { key: 'intro', label: 'Mô tả ngắn', input_type: 'textarea' },
  {
    key: 'features', label: 'Điểm nổi bật', input_type: 'repeater', addLabel: 'Thêm điểm',
    itemSchema: [
      { field: 'icon', label: 'Emoji', input_type: 'text' },
      { field: 'title', label: 'Tiêu đề', input_type: 'text' },
      { field: 'desc', label: 'Mô tả', input_type: 'textarea' },
    ],
  },
  { key: 'cta_primary_label', label: 'Nút chính — nhãn', input_type: 'text' },
  { key: 'cta_primary_to', label: 'Nút chính — liên kết', input_type: 'text' },
  { key: 'cta_secondary_label', label: 'Nút phụ — nhãn', input_type: 'text' },
]

async function reload() {
  loading.value = true
  try {
    const r = await $fetch<any>('/admin-api/site-settings/onboarding', { headers: authHeaders() })
    const v = (r.settings || []).find((s: any) => s.key === 'onboarding')?.value
    value.value = (v && typeof v === 'object' && Object.keys(v).length) ? v : JSON.parse(JSON.stringify(DEFAULT_ONBOARDING))
  } catch { showToast('Không thể tải cài đặt', 'error') }
  loading.value = false
}

onMounted(reload)
</script>

<style scoped>
.cs-back { font-size: .82rem; color: var(--muted); text-decoration: none; transition: color .15s; }
.cs-back:hover { color: var(--primary, #219653); }
.cs-subtitle { font-size: .82rem; color: var(--muted); margin-top: 4px; }
.cs-hint { font-size: .82rem; color: var(--muted); margin-bottom: var(--space-4); max-width: 640px; }
.cs-link { color: var(--primary, #219653); }
.cs-form-wrap { max-width: 640px; }
.cs-skeleton { max-width: 640px; display: flex; flex-direction: column; gap: var(--space-5); }
.cs-skel-row { display: flex; flex-direction: column; gap: var(--space-2); }
.cs-skel-label { width: 120px; height: 14px; border-radius: 6px; background: var(--line); animation: cs-pulse 1.5s ease-in-out infinite; }
.cs-skel-input { width: 100%; height: 44px; border-radius: 10px; background: var(--line); opacity: .5; animation: cs-pulse 1.5s ease-in-out .15s infinite; }
@keyframes cs-pulse { 0%, 100% { opacity: .4; } 50% { opacity: .7; } }
.cs-fade-enter-active { transition: opacity .3s cubic-bezier(.2,1,.4,1), transform .3s cubic-bezier(.2,1,.4,1); }
.cs-fade-enter-from { opacity: 0; transform: translateY(6px); }
@media (prefers-reduced-motion: reduce) {
  .cs-skel-label, .cs-skel-input { animation: none; }
  .cs-fade-enter-active { transition: none; }
}
</style>
