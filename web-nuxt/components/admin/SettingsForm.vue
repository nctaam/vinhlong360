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
            placeholder="#000000" @input="localValues[field.key] = ($event.target as HTMLInputElement).value" />
          <button v-if="localValues[field.key]" type="button" class="sf-color-clear" @click="localValues[field.key] = ''" title="Xoá (dùng mặc định)">✕</button>
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
            <span class="sf-rep-label">{{ item[field.itemSchema[0].field] || '(chưa đặt tên)' }}</span>
            <span v-if="field.itemSchema[1]" class="sf-rep-sub">{{ item[field.itemSchema[1].field] }}</span>
          </template>
          <template #edit-fields="{ item, update }">
            <div v-for="s in field.itemSchema" :key="s.field" class="sf-rep-field">
              <label class="sf-rep-flabel">{{ s.label }}</label>
              <textarea v-if="s.input_type === 'textarea'" :value="item[s.field]" rows="2" class="sf-rep-input"
                @input="update(s.field, ($event.target as HTMLTextAreaElement).value)"></textarea>
              <input v-else :value="item[s.field]" :placeholder="s.label" class="sf-rep-input"
                @input="update(s.field, ($event.target as HTMLInputElement).value)" />
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
        <img v-if="localValues[field.key] && isImageUrl(localValues[field.key])" :src="localValues[field.key]" class="sf-url-preview" alt="Preview" loading="lazy" />
      </template>

      <template v-else>
        <input :id="`sf-${field.key}`" :type="field.input_type === 'number' ? 'number' : 'text'" v-model="localValues[field.key]" class="sf-input" :placeholder="field.placeholder" />
      </template>
    </div>

    <div class="sf-actions">
      <button type="submit" class="btn-primary sf-save" :disabled="saving">
        {{ saving ? 'Đang lưu...' : 'Lưu thay đổi' }}
      </button>
      <button type="button" v-if="!hideReset" class="btn-outline sf-reset" :disabled="saving" @click="onReset">
        Đặt lại mặc định
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
interface RepeaterItemField {
  field: string
  label: string
  input_type?: 'text' | 'textarea'
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
const saving = ref(false)

const localValues = ref<Record<string, any>>({})
const jsonTexts = ref<Record<string, string>>({})
const jsonErrors = ref<Record<string, string>>({})

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
}

watch(() => [props.fields, props.objectValue], initValues, { immediate: true, deep: true })

function validateJson(key: string): boolean {
  try {
    const parsed = JSON.parse(jsonTexts.value[key])
    localValues.value[key] = parsed
    jsonErrors.value[key] = ''
    return true
  } catch (e: any) {
    jsonErrors.value[key] = `JSON không hợp lệ: ${e.message}`
    return false
  }
}

function isImageUrl(url: string): boolean {
  try {
    return /\.(jpg|jpeg|png|gif|webp|svg)(\?.*)?$/i.test(new URL(url).pathname)
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
      const obj: Record<string, any> = { ...(props.objectValue || {}) }
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
    showToast('Đã lưu cài đặt', 'success')
    emit('saved')
  } catch (e: any) {
    showToast(e?.data?.detail || 'Lỗi khi lưu', 'error')
  }
  saving.value = false
}

async function onReset() {
  if (props.objectKey) {
    if (!confirm('Đặt lại nội dung trang này về mặc định? (xoá mọi tuỳ chỉnh)')) return
    saving.value = true
    try {
      await $fetch(`/admin-api/site-settings/${props.objectKey}`, {
        method: 'PUT',
        headers: authHeaders(),
        body: { value: {} },
      })
      showToast('Đã đặt lại về mặc định', 'success')
      emit('saved')
    } catch (e: any) {
      showToast(e?.data?.detail || 'Lỗi', 'error')
    }
    saving.value = false
    return
  }
  if (!confirm(`Đặt lại tất cả cài đặt "${props.category}" về mặc định?`)) return
  saving.value = true
  try {
    await $fetch(`/admin-api/site-settings/reset/${props.category}`, {
      method: 'POST',
      headers: authHeaders(),
    })
    showToast('Đã đặt lại về mặc định', 'success')
    emit('saved')
  } catch (e: any) {
    showToast(e?.data?.detail || 'Lỗi', 'error')
  }
  saving.value = false
}
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
  transition: border-color .2s cubic-bezier(.2,1,.4,1), box-shadow .2s cubic-bezier(.2,1,.4,1);
}
.sf-input:focus, .sf-textarea:focus {
  outline: none; border-color: var(--primary, #219653);
  box-shadow: 0 0 0 3px rgba(33,150,83,.1);
}
.sf-input::placeholder, .sf-textarea::placeholder { color: var(--muted); opacity: .6; }
.sf-textarea { resize: vertical; min-height: 88px; font-family: inherit; line-height: 1.5; }
.sf-json { font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', monospace; font-size: .8rem; min-height: 160px; line-height: 1.6; tab-size: 2; }
.sf-json-invalid { border-color: #D94F3D !important; box-shadow: 0 0 0 3px rgba(217,79,61,.08) !important; }
.sf-json-error { color: #D94F3D; font-size: .75rem; margin-top: 4px; }

/* ── Repeater (A3) ── */
.sf-rep-label { font-size: .88rem; font-weight: 500; }
.sf-rep-sub { display: block; font-size: .75rem; color: var(--muted); margin-top: 2px; }
.sf-rep-field { display: flex; flex-direction: column; gap: 4px; }
.sf-rep-flabel { font-size: .72rem; font-weight: 500; color: var(--muted); }
.sf-rep-input {
  padding: 8px 12px; border: .5px solid var(--line); border-radius: 10px;
  font-size: .85rem; background: var(--bg); color: var(--ink); min-height: 38px;
  font-family: inherit; resize: vertical;
  transition: border-color .2s, box-shadow .2s;
}
.sf-rep-input:focus { outline: none; border-color: var(--primary, #219653); box-shadow: 0 0 0 3px rgba(33,150,83,.1); }
.dark .sf-rep-input { background: rgba(255,255,255,.04); border-color: rgba(255,255,255,.08); }

/* ── Color ── */
.sf-color-row { display: flex; align-items: center; gap: var(--space-3); }
.sf-color-picker {
  width: 44px; height: 44px; border: .5px solid var(--line); border-radius: 10px;
  padding: 2px; cursor: pointer; background: var(--bg);
  transition: box-shadow .2s;
}
.sf-color-picker:focus { outline: none; box-shadow: 0 0 0 3px rgba(33,150,83,.15); }
.sf-color-hex {
  width: 110px; padding: 10px 12px; border: .5px solid var(--line); border-radius: 10px;
  font-size: .85rem; font-family: 'SF Mono', 'Cascadia Code', monospace;
  min-height: 44px; box-sizing: border-box; background: var(--bg); color: var(--ink);
  transition: border-color .2s, box-shadow .2s;
}
.sf-color-hex:focus { outline: none; border-color: var(--primary, #219653); box-shadow: 0 0 0 3px rgba(33,150,83,.1); }
.sf-color-clear {
  padding: 8px 14px; border: .5px solid var(--line); border-radius: 10px; background: var(--bg);
  cursor: pointer; font-size: .78rem; color: var(--muted);
  min-height: 36px; display: flex; align-items: center;
  transition: background .2s, color .2s, border-color .2s, transform .15s cubic-bezier(.2,1,.4,1);
}
.sf-color-clear:hover { background: rgba(217,79,61,.06); color: #D94F3D; border-color: rgba(217,79,61,.2); }
.sf-color-clear:active { transform: scale(.95); }

/* ── Toggle ── */
.sf-toggle { display: flex; align-items: center; gap: var(--space-3); cursor: pointer; min-height: 44px; }
.sf-toggle input { display: none; }
.sf-toggle-track {
  width: 51px; height: 31px; border-radius: 16px;
  background: rgba(142,142,147,.3); position: relative; flex-shrink: 0;
  transition: background .25s cubic-bezier(.2,1,.4,1);
}
.sf-toggle input:checked + .sf-toggle-track { background: var(--primary, #219653); }
.sf-toggle-thumb {
  position: absolute; top: 2px; left: 2px;
  width: 27px; height: 27px; border-radius: 50%;
  background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.18), 0 0 1px rgba(0,0,0,.04);
  transition: transform .3s cubic-bezier(.2,1,.4,1);
}
.sf-toggle input:checked + .sf-toggle-track .sf-toggle-thumb { transform: translateX(20px); }
.sf-toggle:active .sf-toggle-thumb { width: 31px; }
.sf-toggle input:checked + .sf-toggle-track .sf-toggle:active .sf-toggle-thumb { transform: translateX(16px); }
.sf-toggle-label { font-size: .85rem; color: var(--muted); font-weight: 500; }

/* ── URL preview ── */
.sf-url-preview {
  max-width: 220px; max-height: 130px; border-radius: 10px; margin-top: var(--space-3);
  border: .5px solid var(--line); object-fit: cover;
  transition: opacity .3s cubic-bezier(.2,1,.4,1);
}

/* ── Actions ── */
.sf-actions {
  display: flex; gap: var(--space-3); padding-top: var(--space-5);
  margin-top: var(--space-2); border-top: .5px solid var(--line);
}
.sf-save {
  padding: 12px 28px; border-radius: 12px; font-weight: 600; font-size: .88rem;
  background: var(--primary, #219653); color: #fff; border: none; cursor: pointer;
  min-height: 44px;
  transition: transform .2s cubic-bezier(.2,1,.4,1), opacity .2s, box-shadow .2s;
}
.sf-save:hover:not(:disabled) { transform: scale(1.02); box-shadow: 0 4px 12px rgba(33,150,83,.2); }
.sf-save:active:not(:disabled) { transform: scale(.97); }
.sf-save:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.sf-save:disabled { opacity: .45; cursor: not-allowed; }
.sf-reset {
  padding: 12px 20px; border-radius: 12px; font-size: .85rem; font-weight: 500;
  background: transparent; border: .5px solid var(--line); color: var(--muted); cursor: pointer;
  min-height: 44px;
  transition: border-color .2s, color .2s, transform .15s cubic-bezier(.2,1,.4,1);
}
.sf-reset:hover:not(:disabled) { border-color: #D94F3D; color: #D94F3D; }
.sf-reset:active:not(:disabled) { transform: scale(.97); }
.sf-reset:focus-visible { outline: 2px solid #D94F3D; outline-offset: 2px; }

/* ── Dark ── */
.dark .sf-input, .dark .sf-textarea { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.08); }
.dark .sf-color-picker { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.08); }
.dark .sf-color-hex { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.08); color: var(--ink); }
.dark .sf-color-clear { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.08); }
.dark .sf-toggle-track { background: rgba(255,255,255,.15); }
.dark .sf-toggle-thumb { box-shadow: 0 1px 4px rgba(0,0,0,.35); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .sf-input, .sf-textarea, .sf-color-picker, .sf-color-hex,
  .sf-save, .sf-reset, .sf-color-clear, .sf-toggle-track, .sf-toggle-thumb { transition: none; }
  .sf-save:hover:not(:disabled), .sf-save:active:not(:disabled),
  .sf-reset:active:not(:disabled), .sf-color-clear:active { transform: none; }
}
</style>
