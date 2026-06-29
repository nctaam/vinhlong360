<template>
  <div>
    <div class="admin-head-row">
      <div>
        <NuxtLink to="/admin/cai-dat" class="cs-back">← Cài đặt</NuxtLink>
        <h1>Tính năng</h1>
        <p class="cs-subtitle">Bật/tắt các khối nội dung trên website</p>
      </div>
    </div>

    <p class="cs-hint">Tắt một mục sẽ ẩn khối đó khỏi website. Mặc định tất cả đều bật.</p>

    <div v-if="loading" class="cs-skeleton">
      <div class="cs-skel-item" v-for="n in 6" :key="n"></div>
    </div>

    <Transition name="cs-fade">
      <div v-if="!loading" class="ff-wrap">
        <div v-for="group in groups" :key="group.name" class="ff-group">
          <h3 class="ff-group-title">{{ group.name }}</h3>
          <label v-for="flag in group.items" :key="flag.key" class="ff-row">
            <div class="ff-info">
              <span class="ff-label">{{ flag.label }}</span>
              <span v-if="flag.description" class="ff-desc">{{ flag.description }}</span>
            </div>
            <span class="ff-toggle">
              <input type="checkbox" :checked="isOn(flag.key)" @change="setFlag(flag.key, ($event.target as HTMLInputElement).checked)" />
              <span class="ff-track"><span class="ff-thumb"></span></span>
            </span>
          </label>
        </div>

        <div class="cs-save-row">
          <button type="button" class="sf-save" :disabled="saving" @click="onSave">
            {{ saving ? 'Đang lưu...' : 'Lưu thay đổi' }}
          </button>
          <button type="button" class="sf-reset" :disabled="saving" @click="onReset">
            Bật lại tất cả
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { FEATURE_FLAGS, featureFlagDefault } from '~/utils/featureFlags'
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Tính năng — Admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()

const loading = ref(true)
const saving = ref(false)
const flags = ref<Record<string, boolean>>({})

const groups = computed(() => {
  const map = new Map<string, typeof FEATURE_FLAGS>()
  for (const f of FEATURE_FLAGS) {
    const g = f.group || 'Khác'
    if (!map.has(g)) map.set(g, [])
    map.get(g)!.push(f)
  }
  return [...map.entries()].map(([name, items]) => ({ name, items }))
})

function isOn(key: string): boolean {
  const v = flags.value[key]
  return typeof v === 'boolean' ? v : featureFlagDefault(key)
}
function setFlag(key: string, val: boolean) { flags.value = { ...flags.value, [key]: val } }

async function reload() {
  loading.value = true
  try {
    const r = await $fetch<any>('/admin-api/site-settings/features', { headers: authHeaders() })
    const row = (r.settings || []).find((s: any) => s.key === 'features.flags')
    flags.value = (row?.value && typeof row.value === 'object') ? row.value : {}
  } catch { showToast('Không thể tải cài đặt', 'error') }
  loading.value = false
}

function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); if (!saving.value) onSave() }
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

async function onSave() {
  if (saving.value) return
  saving.value = true
  try {
    // Persist an explicit boolean for every known flag (so defaults are captured).
    const full: Record<string, boolean> = {}
    for (const f of FEATURE_FLAGS) full[f.key] = isOn(f.key)
    await $fetch('/admin-api/site-settings/features.flags', {
      method: 'PUT', headers: authHeaders(), body: { value: full },
    })
    showToast('Đã lưu tính năng', 'success')
  } catch (e: unknown) { showToast(extractErrorMessage(e, 'Lỗi khi lưu'), 'error') }
  saving.value = false
}

async function onReset() {
  if (saving.value) return
  if (!await confirmDialog('Bật lại tất cả tính năng?', { danger: true })) return
  saving.value = true
  try {
    await $fetch('/admin-api/site-settings/features.flags', {
      method: 'PUT', headers: authHeaders(), body: { value: {} },
    })
    showToast('Đã bật lại tất cả', 'success')
    await reload()
  } catch (e: unknown) { showToast(extractErrorMessage(e, 'Lỗi'), 'error') }
  saving.value = false
}

onMounted(reload)
</script>

<style scoped>
.cs-back { font-size: .82rem; color: var(--muted); text-decoration: none; transition: color .15s; }
.cs-back:hover { color: var(--primary, #219653); }
.cs-subtitle { font-size: .82rem; color: var(--muted); margin-top: 4px; }
.cs-hint { font-size: .82rem; color: var(--muted); margin-bottom: var(--space-4); max-width: 640px; }
.ff-wrap { max-width: 640px; }

.ff-group { margin-bottom: var(--space-6); }
.ff-group-title { font-size: .8rem; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); margin-bottom: var(--space-3); }

.ff-row {
  display: flex; align-items: center; justify-content: space-between; gap: var(--space-4);
  padding: 14px 16px; border: .5px solid var(--line); border-radius: 12px;
  background: var(--bg); margin-bottom: 2px; cursor: pointer; min-height: 44px;
  transition: box-shadow .3s cubic-bezier(.2,1,.4,1);
}
.ff-row:hover { box-shadow: 0 2px 12px rgba(0,0,0,.05); }
.ff-info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ff-label { font-size: .9rem; font-weight: 500; }
.ff-desc { font-size: .76rem; color: var(--muted); line-height: 1.4; }

.ff-toggle { flex-shrink: 0; }
.ff-toggle input { display: none; }
.ff-track {
  display: block; width: 51px; height: 31px; border-radius: 16px;
  background: rgba(142,142,147,.3); position: relative;
  transition: background .25s cubic-bezier(.2,1,.4,1);
}
.ff-toggle input:checked + .ff-track { background: var(--primary, #219653); }
.ff-thumb {
  position: absolute; top: 2px; left: 2px; width: 27px; height: 27px; border-radius: 50%;
  background: var(--bg); box-shadow: 0 1px 4px rgba(0,0,0,.18);
  transition: transform .3s cubic-bezier(.2,1,.4,1);
}
.ff-toggle input:checked + .ff-track .ff-thumb { transform: translateX(20px); }

.cs-save-row { display: flex; gap: var(--space-3); padding-top: var(--space-5); margin-top: var(--space-4); border-top: .5px solid var(--line); }
.sf-save {
  padding: 12px 28px; border-radius: 12px; font-weight: 600; font-size: .88rem;
  background: var(--primary, #219653); color: var(--text-on-dark, #fff); border: none; cursor: pointer; min-height: 44px;
  transition: transform .2s cubic-bezier(.2,1,.4,1), box-shadow .2s;
}
.sf-save:hover:not(:disabled) { transform: scale(1.02); box-shadow: 0 4px 12px rgba(var(--primary-rgb),.2); }
.sf-save:active:not(:disabled) { transform: scale(.97); }
.sf-save:disabled { opacity: var(--opacity-disabled); cursor: not-allowed; }
.sf-reset {
  padding: 12px 20px; border-radius: 12px; font-size: .85rem; font-weight: 500;
  background: transparent; border: .5px solid var(--line); color: var(--muted); cursor: pointer; min-height: 44px;
  transition: border-color .2s, color .2s, transform .15s cubic-bezier(.2,1,.4,1);
}
.sf-reset:hover:not(:disabled) { border-color: var(--primary, #219653); color: var(--primary, #219653); }
.sf-reset:active:not(:disabled) { transform: scale(.97); }

.cs-skeleton { max-width: 640px; display: flex; flex-direction: column; gap: 2px; }
.cs-skel-item { height: 60px; border-radius: 12px; background: var(--line); opacity: .4; animation: cs-pulse 1.5s ease-in-out infinite; }
.cs-skel-item:nth-child(even) { animation-delay: .2s; }
@keyframes cs-pulse { 0%, 100% { opacity: .3; } 50% { opacity: .6; } }
.cs-fade-enter-active { transition: opacity .3s cubic-bezier(.2,1,.4,1), transform .3s cubic-bezier(.2,1,.4,1); }
.cs-fade-enter-from { opacity: 0; transform: translateY(6px); }

.dark .ff-row { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .ff-track { background: rgba(255,255,255,.15); }

@media (prefers-reduced-motion: reduce) {
  .ff-row, .ff-track, .ff-thumb, .sf-save, .sf-reset { transition: none; }
  .cs-skel-item { animation: none; }
  .cs-fade-enter-active { transition: none; }
}
</style>
