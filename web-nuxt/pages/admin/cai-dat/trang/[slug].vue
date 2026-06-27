<template>
  <div>
    <div class="admin-head-row">
      <div>
        <NuxtLink to="/admin/cai-dat/trang" class="cs-back">← Nội dung trang</NuxtLink>
        <h1>{{ manifest?.title || slug }}</h1>
        <p class="cs-subtitle" v-if="manifest">
          Sửa nội dung trang
          <a :href="manifest.route" target="_blank" rel="noopener" class="cs-view">{{ manifest.route }} ↗</a>
        </p>
      </div>
    </div>

    <div v-if="!manifest" class="cs-missing">
      <p>Không tìm thấy cấu hình cho trang <code>{{ slug }}</code>.</p>
      <NuxtLink to="/admin/cai-dat/trang" class="btn btn-outline">← Quay lại</NuxtLink>
    </div>

    <template v-else>
      <p class="cs-hint">Để trống một ô = dùng nội dung mặc định (hiển thị mờ bên trong ô).</p>

      <div v-if="loading" class="cs-skeleton">
        <div class="cs-skel-row" v-for="n in manifest.fields.length" :key="n"><div class="cs-skel-label"></div><div class="cs-skel-input"></div></div>
      </div>
      <Transition name="cs-fade">
        <div v-if="!loading" class="cs-form-wrap">
          <AdminSettingsForm
            :category="'page'"
            :object-key="`page.${slug}`"
            :object-value="current"
            :fields="formFields"
            @saved="reload"
          />
        </div>
      </Transition>
    </template>
  </div>
</template>

<script setup lang="ts">
import { getPageManifest } from '~/utils/pageManifest'
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Chỉnh sửa trang — Admin' })

const route = useRoute()
const slug = computed(() => String(route.params.slug || ''))
const manifest = computed(() => getPageManifest(slug.value))

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const current = ref<Record<string, any>>({})
const loading = ref(true)

// Map manifest fields → AdminSettingsForm field shape (default shown as placeholder).
const formFields = computed(() =>
  (manifest.value?.fields || []).map(f => ({
    key: f.field,
    label: f.label,
    description: f.description,
    placeholder: f.default,
    input_type: f.input_type,
  })),
)

async function reload() {
  if (!manifest.value) { loading.value = false; return }
  loading.value = true
  try {
    const r = await $fetch<any>('/admin-api/site-settings/page', { headers: authHeaders() })
    const row = (r.settings || []).find((s: any) => s.key === `page.${slug.value}`)
    current.value = (row?.value && typeof row.value === 'object') ? row.value : {}
  } catch {
    current.value = {}
    showToast('Không thể tải cài đặt', 'error')
  }
  loading.value = false
}

watch(slug, reload)
onMounted(reload)
</script>

<style scoped>
.cs-back { font-size: .82rem; color: var(--muted); text-decoration: none; transition: color .15s; }
.cs-back:hover { color: var(--primary, #219653); }
.cs-subtitle { font-size: .82rem; color: var(--muted); margin-top: 4px; }
.cs-view { color: var(--primary, #219653); text-decoration: none; margin-left: 6px; font-family: 'SF Mono', monospace; font-size: .78rem; }
.cs-view:hover { text-decoration: underline; }
.cs-hint { font-size: .82rem; color: var(--muted); margin-bottom: var(--space-4); max-width: 640px; }
.cs-form-wrap { max-width: 640px; }
.cs-missing { padding: var(--space-6); color: var(--muted); }
.cs-missing code { font-family: 'SF Mono', monospace; color: var(--primary, #219653); }

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
