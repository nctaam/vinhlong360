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

