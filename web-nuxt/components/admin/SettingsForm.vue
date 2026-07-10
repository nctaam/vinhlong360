<template>
  <form class="sf" @submit.prevent="onSave">
    <div v-for="field in fields" :key="field.key" class="sf-field">
      <label :for="`sf-${field.key}`" class="sf-label">
        {{ field.label }}
        <small v-if="field.description" class="sf-desc">{{ field.description }}</small>
      </label>

      <template v-if="field.input_type === 'toggle'">
        <label class="sf-toggle">
          <input :id="`sf-${field.key}`" type="checkbox" :checked="!!localValues[field.key]"
            :aria-label="`${field.label}: ${localValues[field.key] ? 'Bật' : 'Tắt'}`"
            @change="localValues[field.key] = ($event.target as HTMLInputElement).checked" />
          <span class="sf-toggle-track"><span class="sf-toggle-thumb"></span></span>
          <span class="sf-toggle-label">{{ localValues[field.key] ? 'Bật' : 'Tắt' }}</span>
        </label>
      </template>

      <template v-else-if="field.input_type === 'color'">
        <div class="sf-color-row">
          <input :id="`sf-${field.key}`" type="color" :value="localValues[field.key] || '#000000'"
            @input="localValues[field.key] = ($event.target as HTMLInputElement).value" class="sf-color-picker" />
          <input type="text" :value="localValues[field.key]" class="sf-color-hex"
            placeholder="#000000" :aria-label="`${field.label} (mã hex)`" @input="localValues[field.key] = ($event.target as HTMLInputElement).value" />
          <button v-if="localValues[field.key]" type="button" class="sf-color-clear" @click="localValues[field.key] = ''" title="Xoá (dùng mặc định)" aria-label="Xoá màu (dùng mặc định)">✕</button>
        </div>
      </template>

      <template v-else-if="field.input_type === 'textarea'">
        <textarea :id="`sf-${field.key}`" v-model="localValues[field.key]" rows="3" class="sf-textarea" :placeholder="field.placeholder"></textarea>
      </template>

      <template v-else-if="field.input_type === 'repeater' && field.itemSchema">
        <AdminSortableList
          :items="Array.isArray(localValues[field.key]) ? localValues[field.key] : []"
          :label-field="field.itemSchema[0]?.field"
          :editable-fields="field.itemSchema.map(s => s.field)"
          :add-label="field.addLabel || 'Thêm mục'"
          :new-item-template="repeaterTemplate(field)"
          @update:items="localValues[field.key] = $event"
        >
          <template #display="{ item }">
            <span class="sf-rep-label">{{ item[repeaterField(field, 0)] || '(chưa đặt tên)' }}</span>
            <span v-if="repeaterField(field, 1, '')" class="sf-rep-sub">{{ item[repeaterField(field, 1, '')] }}</span>
          </template>
          <template #edit-fields="{ item, update }">
            <div v-for="s in field.itemSchema" :key="s.field" class="sf-rep-field">
              <label class="sf-rep-flabel">{{ s.label }}</label>
              <textarea v-if="s.input_type === 'textarea'" :value="item[s.field]" rows="2" class="sf-rep-input"
                :aria-label="s.label" @input="update(s.field, ($event.target as HTMLTextAreaElement).value)"></textarea>
              <input v-else :value="item[s.field]" :placeholder="s.label" class="sf-rep-input"
                :aria-label="s.label" @input="update(s.field, ($event.target as HTMLInputElement).value)" />
            </div>
          </template>
        </AdminSortableList>
      </template>

      <template v-else-if="field.input_type === 'json' || field.input_type === 'repeater'">
        <textarea :id="`sf-${field.key}`" v-model="jsonTexts[field.key]" rows="8" class="sf-textarea sf-json"
          :class="{ 'sf-json-invalid': jsonErrors[field.key] }" @blur="validateJson(field.key)"></textarea>
        <small v-if="jsonErrors[field.key]" class="sf-json-error">{{ jsonErrors[field.key] }}</small>
      </template>

      <template v-else-if="field.input_type === 'url'">
        <input :id="`sf-${field.key}`" type="url" v-model="localValues[field.key]" class="sf-input" placeholder="https://..." />
        <img v-if="asString(localValues[field.key]) && isImageUrl(asString(localValues[field.key]))" :src="asString(localValues[field.key])" class="sf-url-preview" alt="Preview" loading="lazy" decoding="async" @error="(e: Event) => ((e.target as HTMLImageElement).style.opacity = '.15')" />
      </template>

      <template v-else>
        <input :id="`sf-${field.key}`" :type="field.input_type === 'number' ? 'number' : 'text'" v-model="localValues[field.key]" class="sf-input" :placeholder="field.placeholder" />
      </template>
    </div>

    <div class="sf-actions" :class="{ 'sf-actions-dirty': isDirty && !saving }">
      <button type="submit" class="btn-primary sf-save" :disabled="saving">
        <span v-if="saving" class="sf-spinner" aria-hidden="true"></span>
        {{ saving ? 'Đang lưu...' : (changedCount > 0 ? `Lưu ${changedCount} thay đổi` : 'Lưu thay đổi') }}
      </button>
      <button type="button" v-if="!hideReset" class="btn-outline sf-reset" :disabled="saving" @click="onReset">
        Đặt lại mặc định
      </button>
      <span v-if="isDirty && !saving" class="sf-dirty-badge" role="status">Chưa lưu</span>
    </div>
    <div v-if="history.length" class="sf-history" aria-label="Lịch sử thay đổi">
      <div class="sf-history-head">
        <strong>Lịch sử gần đây</strong>
        <button type="button" class="btn-ghost-sm" :disabled="historyLoading" @click="loadHistory">Tải lại</button>
      </div>
      <div v-for="h in history" :key="h.id" class="sf-history-row">
        <span class="sf-history-main">{{ h.setting_key }} · {{ historyActionLabel(h.action) }}</span>
        <time class="sf-history-time" :datetime="h.created_at">{{ formatDate(h.created_at) }}</time>
        <button type="button" class="btn-outline sf-history-rollback" :disabled="saving" @click="rollbackHistory(h.id)">Rollback</button>
      </div>
    </div>
  </form>
</template>

<script setup lang="ts">
interface RepeaterItemField {
  field: string
  label: string
  input_type?: string
  default?: string
}
interface SettingField {
  key: string
  value?: unknown
  label: string
  description?: string
  placeholder?: string
  input_type: string
  category?: string
  // Repeater mode (A3): array-of-objects editor (falls back to JSON textarea
  // when itemSchema is absent).
  itemSchema?: RepeaterItemField[]
  addLabel?: string
}

function isJsonLike(f: SettingField): boolean {
  return f.input_type === 'json' || (f.input_type === 'repeater' && !f.itemSchema)
}
function repeaterTemplate(f: SettingField): Record<string, string> {
  const t: Record<string, string> = {}
  for (const s of f.itemSchema || []) t[s.field] = s.default ?? ''
  return t
}

function repeaterField(f: SettingField, index: number, fallback = 'label'): string {
  return f.itemSchema?.[index]?.field ?? fallback
}

function asString(value: unknown): string {
  return typeof value === 'string' ? value : ''
}

const props = defineProps<{
  category: string
  fields: SettingField[]
  // Nested mode (A2): when set, all `fields` are sub-fields of this single
  // JSON setting key; values come from `objectValue` and save as one object.
  objectKey?: string
  objectValue?: Record<string, any>
  // Hide the "reset" button (e.g. single-key editors where a category-wide
  // reset would be too broad).
  hideReset?: boolean
}>()

const emit = defineEmits<{
  saved: []
}>()

const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()
const saving = ref(false)

const localValues = ref<Record<string, any>>({})
const jsonTexts = ref<Record<string, string>>({})
const jsonErrors = ref<Record<string, string>>({})
const history = ref<any[]>([])
const historyLoading = ref(false)
// Snapshot of values at load/save time, used purely for dirty-state display.
// Does NOT participate in the save/data path.
const initialSnapshot = ref<string>('{}')

function initValues() {
  const vals: Record<string, any> = {}
  const jTexts: Record<string, string> = {}
  const nested = !!props.objectKey
  for (const f of props.fields) {
    const base = nested ? props.objectValue?.[f.key] : f.value
    if (isJsonLike(f)) {
      vals[f.key] = base
      jTexts[f.key] = JSON.stringify(base ?? null, null, 2)
    } else if (f.input_type === 'repeater') {
      vals[f.key] = Array.isArray(base) ? base : []
    } else {
      vals[f.key] = base ?? ''
    }
  }
  localValues.value = vals
  jsonTexts.value = jTexts
  jsonErrors.value = {}
  initialSnapshot.value = snapshotOf(vals, jTexts)
}

// Build a stable string snapshot of the editable state for dirty comparison.
function snapshotOf(vals: Record<string, any>, jTexts: Record<string, string>): string {
  try {
    const out: Record<string, any> = {}
    for (const f of props.fields) {
      out[f.key] = isJsonLike(f) ? (jTexts[f.key] ?? '') : vals[f.key]
    }
    return JSON.stringify(out)
  } catch { return '' }
}

const currentSnapshot = computed(() => snapshotOf(localValues.value, jsonTexts.value))
const isDirty = computed(() => currentSnapshot.value !== initialSnapshot.value)
const changedCount = computed(() => {
  try {
    const before = JSON.parse(initialSnapshot.value || '{}')
    const after = JSON.parse(currentSnapshot.value || '{}')
    let n = 0
    for (const f of props.fields) {
      if (JSON.stringify(before[f.key]) !== JSON.stringify(after[f.key])) n++
    }
    return n
  } catch { return 0 }
})

watch(() => [props.fields, props.objectValue], initValues, { immediate: true })
watch(() => [props.category, props.objectKey], () => loadHistory(), { immediate: true })

function validateJson(key: string): boolean {
  try {
    const parsed = JSON.parse(jsonTexts.value[key] ?? '')
    localValues.value[key] = parsed
    jsonErrors.value[key] = ''
    return true
  } catch (e: unknown) {
    jsonErrors.value[key] = `JSON không hợp lệ: ${extractErrorMessage(e, 'cú pháp sai')}`
    return false
  }
}

function isSafeUrl(url: string): boolean {
  try { return /^https?:$/i.test(new URL(url).protocol) } catch { return false }
}
function isImageUrl(url: string): boolean {
  try {
    const u = new URL(url)
    if (!/^https?:$/i.test(u.protocol)) return false
    return /\.(jpg|jpeg|png|gif|webp|svg)(\?.*)?$/i.test(u.pathname)
  } catch { return false }
}

async function onSave() {
  for (const f of props.fields) {
    if (isJsonLike(f) && !validateJson(f.key)) {
      showToast(`JSON không hợp lệ cho "${f.label}"`, 'error')
      return
    }
  }

  saving.value = true
  try {
    if (props.objectKey) {
      // Nested mode: merge fields into one object, save under the single key.
      const src = props.objectValue || {}
      const obj: Record<string, any> = {}
      for (const k of Object.keys(src)) {
        if (k !== '__proto__' && k !== 'constructor' && k !== 'prototype') obj[k] = (src as any)[k]
      }
      for (const f of props.fields) obj[f.key] = localValues.value[f.key]
      await $fetch(`/admin-api/site-settings/${props.objectKey}`, {
        method: 'PUT',
        headers: authHeaders(),
        body: { value: obj },
      })
    } else {
      const updates: Record<string, unknown> = {}
      for (const f of props.fields) {
        updates[f.key] = localValues.value[f.key]
      }
      await $fetch('/admin-api/site-settings/bulk', {
        method: 'POST',
        headers: authHeaders(),
        body: { updates },
      })
    }
    initialSnapshot.value = snapshotOf(localValues.value, jsonTexts.value)
    showToast('Đã lưu cài đặt', 'success')
    await loadHistory()
    emit('saved')
  } catch (e: unknown) {
    showToast(extractErrorMessage(e, 'Lỗi khi lưu'), 'error')
  }
  saving.value = false
}

function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    if (!saving.value) onSave()
  }
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

async function onReset() {
  if (props.objectKey) {
    if (!await confirmDialog('Đặt lại nội dung trang này về mặc định? (xoá mọi tuỳ chỉnh)')) return
    saving.value = true
    try {
      await $fetch(`/admin-api/site-settings/${props.objectKey}`, {
        method: 'PUT',
        headers: authHeaders(),
        body: { value: {} },
      })
      showToast('Đã đặt lại về mặc định', 'success')
      await loadHistory()
      emit('saved')
    } catch (e: unknown) {
      showToast(extractErrorMessage(e, 'Lỗi'), 'error')
    }
    saving.value = false
    return
  }
  if (!await confirmDialog(`Đặt lại tất cả cài đặt "${props.category}" về mặc định?`)) return
  saving.value = true
  try {
    await $fetch(`/admin-api/site-settings/reset/${props.category}`, {
      method: 'POST',
      headers: authHeaders(),
    })
    showToast('Đã đặt lại về mặc định', 'success')
    await loadHistory()
    emit('saved')
  } catch (e: unknown) {
    showToast(extractErrorMessage(e, 'Lỗi'), 'error')
  }
  saving.value = false
}

function historyActionLabel(action?: string) {
  if (action === 'rollback') return 'rollback'
  if (action === 'reset') return 'reset'
  if (action === 'bulk_update') return 'cập nhật'
  return action || 'cập nhật'
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const params = new URLSearchParams({ limit: '5' })
    if (props.objectKey) params.set('key', props.objectKey)
    else params.set('category', props.category)
    const res = await $fetch<{ history?: any[] }>(`/admin-api/site-settings-history?${params}`, { headers: authHeaders() })
    history.value = res.history || []
  } catch {
    history.value = []
  } finally {
    historyLoading.value = false
  }
}

async function rollbackHistory(id: string) {
  if (!await confirmDialog('Rollback cài đặt này về snapshot trước đó?', { danger: true })) return
  saving.value = true
  try {
    await $fetch(`/admin-api/site-settings-history/${id}/rollback`, { method: 'POST', headers: authHeaders() })
    showToast('Đã rollback cài đặt', 'success')
    await loadHistory()
    emit('saved')
  } catch (e: unknown) {
    showToast(extractErrorMessage(e, 'Không thể rollback'), 'error')
  } finally {
    saving.value = false
  }
}

const formatDate = formatDateVN
</script>

<style scoped>
.sf { display: flex; flex-direction: column; gap: var(--space-6); }
.sf-field { display: flex; flex-direction: column; gap: var(--space-2); }
.sf-label { font-weight: 600; font-size: .88rem; color: var(--ink); line-height: 1.3; }
.sf-desc { display: block; font-weight: 400; font-size: .75rem; color: var(--muted); margin-top: 3px; line-height: 1.4; }

.sf-input, .sf-textarea {
  padding: 11px 14px; border: .5px solid var(--line); border-radius: 10px;
  font-size: .88rem; background: var(--bg); color: var(--ink);
  min-height: 44px; box-sizing: border-box;
  transition: border-color .2s var(--ease-soft), box-shadow .2s var(--ease-soft);
}
.sf-input:focus, .sf-textarea:focus {
  outline: none; border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .1);
}
.sf-input::placeholder, .sf-textarea::placeholder { color: var(--muted); opacity: .6; }
.sf-textarea { resize: vertical; min-height: 88px; font-family: inherit; line-height: 1.5; }
.sf-json { font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace; font-size: .8rem; min-height: 160px; line-height: 1.5; tab-size: 2; }
.sf-json-invalid { border-color: var(--danger, #D94F3D) !important; box-shadow: 0 0 0 3px rgba(var(--danger-rgb, 217,79,61),.08) !important; }
.sf-json-error { color: var(--danger, #D94F3D); font-size: .75rem; margin-top: var(--space-1); }

/* ── Repeater (A3) ── */
.sf-rep-label { font-size: .88rem; font-weight: 500; }
.sf-rep-sub { display: block; font-size: .75rem; color: var(--muted); margin-top: 2px; }
.sf-rep-field { display: flex; flex-direction: column; gap: var(--space-1); }
.sf-rep-flabel { font-size: .72rem; font-weight: 500; color: var(--muted); }
.sf-rep-input {
  padding: var(--space-2) var(--space-3); border: .5px solid var(--line); border-radius: 10px;
  font-size: .85rem; background: var(--bg); color: var(--ink); min-height: 38px;
  font-family: inherit; resize: vertical;
  transition: border-color .2s, box-shadow .2s;
}
.sf-rep-input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .1); }
.dark .sf-rep-input { background: rgba(var(--white-rgb),.04); border-color: rgba(var(--white-rgb),.08); }

/* ── Color ── */
.sf-color-row { display: flex; align-items: center; gap: var(--space-3); }
.sf-color-picker {
  width: 44px; height: 44px; border: .5px solid var(--line); border-radius: 10px;
  padding: 2px; cursor: pointer; background: var(--bg);
  transition: box-shadow .2s;
}
.sf-color-picker:focus { outline: none; box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .15); }
.sf-color-hex {
  width: 110px; padding: 10px var(--space-3); border: .5px solid var(--line); border-radius: 10px;
  font-size: .85rem; font-family: 'SF Mono', 'Cascadia Code', monospace;
  min-height: 44px; box-sizing: border-box; background: var(--bg); color: var(--ink);
  transition: border-color .2s, box-shadow .2s;
}
.sf-color-hex:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .1); }
.sf-color-clear {
  padding: var(--space-2) 14px; border: .5px solid var(--line); border-radius: 10px; background: var(--bg);
  cursor: pointer; font-size: .78rem; color: var(--muted);
  min-height: 44px; display: flex; align-items: center;
  transition: background .2s, color .2s, border-color .2s, transform .15s var(--ease-soft);
}
.sf-color-clear:hover { background: rgba(var(--danger-rgb, 217,79,61),.06); color: var(--danger, #D94F3D); border-color: rgba(var(--danger-rgb, 217,79,61),.2); }
.sf-color-clear:active { transform: scale(.95); }

/* ── Toggle ── */
.sf-toggle { display: flex; align-items: center; gap: var(--space-3); cursor: pointer; min-height: 44px; }
.sf-toggle input { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
.sf-toggle input:focus-visible + .sf-toggle-track { outline: 2px solid var(--primary); outline-offset: 2px; }
.sf-toggle-track {
  width: 51px; height: 31px; border-radius: 16px;
  background: rgba(142,142,147,.3); position: relative; flex-shrink: 0;
  transition: background .25s var(--ease-soft);
}
.sf-toggle input:checked + .sf-toggle-track { background: var(--primary); }
.sf-toggle-thumb {
  position: absolute; top: 2px; left: 2px;
  width: 27px; height: 27px; border-radius: 50%;
  background: var(--white, var(--white)); box-shadow: 0 1px 4px rgba(var(--black-rgb),.18), 0 0 1px rgba(var(--black-rgb),.04);
  transition: transform .3s var(--ease-soft);
}
.sf-toggle input:checked + .sf-toggle-track .sf-toggle-thumb { transform: translateX(20px); }
.sf-toggle:active .sf-toggle-thumb { width: 31px; }
.sf-toggle input:checked + .sf-toggle-track .sf-toggle:active .sf-toggle-thumb { transform: translateX(16px); }
.sf-toggle-label { font-size: .85rem; color: var(--muted); font-weight: 500; }

/* ── URL preview ── */
.sf-url-preview {
  max-width: 220px; max-height: 130px; border-radius: 10px; margin-top: var(--space-3);
  border: .5px solid var(--line); object-fit: cover;
  transition: opacity .3s var(--ease-soft);
}

/* ── Actions ── */
.sf-actions {
  display: flex; gap: var(--space-3); padding-top: var(--space-5);
  margin-top: var(--space-2); border-top: .5px solid var(--line);
}
.sf-save {
  padding: var(--space-3) 28px; border-radius: 12px; font-weight: 600; font-size: .88rem;
  background: var(--primary); color: var(--text-on-dark, var(--white)); border: none; cursor: pointer;
  min-height: 44px;
  transition: transform .2s var(--ease-soft), opacity .2s, box-shadow .2s;
}
.sf-save:hover:not(:disabled) { transform: scale(1.02); box-shadow: 0 4px 12px rgba(var(--primary-rgb), .2); }
.sf-save:active:not(:disabled) { transform: scale(.97); }
.sf-save:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.sf-save:disabled { opacity: var(--opacity-disabled); cursor: not-allowed; }
.sf-reset {
  padding: var(--space-3) var(--space-5); border-radius: 12px; font-size: .85rem; font-weight: 500;
  background: transparent; border: .5px solid var(--line); color: var(--muted); cursor: pointer;
  min-height: 44px;
  transition: border-color .2s, color .2s, transform .15s var(--ease-soft);
}
.sf-reset:hover:not(:disabled) { border-color: var(--danger, #D94F3D); color: var(--danger, #D94F3D); }
.sf-reset:active:not(:disabled) { transform: scale(.97); }
.sf-reset:focus-visible { outline: 2px solid var(--danger, #D94F3D); outline-offset: 2px; }

/* ── Save spinner ── */
.sf-save { display: inline-flex; align-items: center; justify-content: center; gap: var(--space-2); }
.sf-spinner {
  width: 16px; height: 16px; flex-shrink: 0;
  border: 2px solid rgba(var(--white-rgb),.4); border-top-color: var(--text-on-dark, var(--white)); border-radius: 50%;
  animation: sf-spin .7s linear infinite;
}
@keyframes sf-spin { to { transform: rotate(360deg); } }

/* ── Dirty / unsaved indicator ── */
.sf-actions-dirty { border-top-color: var(--primary); }
.sf-dirty-badge {
  display: inline-flex; align-items: center; align-self: center;
  padding: var(--space-1) 10px; border-radius: 999px;
  font-size: .72rem; font-weight: 600; color: var(--primary);
  background: rgba(var(--primary-rgb), .1); border: .5px solid rgba(var(--primary-rgb), .25);
}
.sf-history {
  display: grid; gap: var(--space-2);
  padding: var(--space-3); border: .5px solid var(--line);
  border-radius: 10px; background: var(--bg-alt, #f8faf9);
}
.sf-history-head {
  display: flex; align-items: center; justify-content: space-between;
  gap: var(--space-3); color: var(--ink);
}
.sf-history-head strong { font-size: .84rem; }
.sf-history-row {
  display: grid; grid-template-columns: minmax(0, 1fr) auto auto;
  gap: var(--space-3); align-items: center;
  padding: var(--space-2) 0; border-top: .5px solid var(--line);
}
.sf-history-main { min-width: 0; font-size: .8rem; font-weight: 600; color: var(--ink); word-break: break-word; }
.sf-history-time { font-size: .74rem; color: var(--muted); white-space: nowrap; }
.sf-history-rollback { min-height: 34px; padding: 6px 10px; border-radius: 8px; font-size: .76rem; }

/* ── Dark ── */
.dark .sf-input, .dark .sf-textarea { background: var(--card, #2c2c2e); border-color: rgba(var(--white-rgb),.08); }
.dark .sf-color-picker { background: var(--card, #2c2c2e); border-color: rgba(var(--white-rgb),.08); }
.dark .sf-color-hex { background: var(--card, #2c2c2e); border-color: rgba(var(--white-rgb),.08); color: var(--ink); }
.dark .sf-color-clear { background: var(--card, #2c2c2e); border-color: rgba(var(--white-rgb),.08); }
.dark .sf-toggle-track { background: rgba(var(--white-rgb),.15); }
.dark .sf-toggle-thumb { box-shadow: 0 1px 4px rgba(var(--black-rgb),.35); }
.dark .sf-dirty-badge { color: rgb(var(--success-rgb)); background: rgba(var(--primary-rgb),.18); border-color: rgba(var(--success-rgb),.3); }
.dark .sf-history { background: rgba(var(--white-rgb),.03); border-color: rgba(var(--white-rgb),.08); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .sf-input, .sf-textarea, .sf-color-picker, .sf-color-hex,
  .sf-save, .sf-reset, .sf-color-clear, .sf-toggle-track, .sf-toggle-thumb { transition: none; }
  .sf-save:hover:not(:disabled), .sf-save:active:not(:disabled),
  .sf-reset:active:not(:disabled), .sf-color-clear:active { transform: none; }
  .sf-spinner { animation: none; }
}

@media (max-width: 640px) {
  .sf-actions { flex-direction: column; align-items: stretch; }
  .sf-history-row { grid-template-columns: 1fr; gap: var(--space-1); }
  .sf-history-time { white-space: normal; }
  .sf-history-rollback { justify-self: start; }
}
</style>
