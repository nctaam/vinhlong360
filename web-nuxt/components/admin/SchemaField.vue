<template>
  <div class="ent-field sf-field">
    <label class="form-label" :for="fieldId">
      {{ field.label }}
      <span v-if="field.required" class="sf-req" aria-hidden="true">*</span>
    </label>

    <!-- textarea -->
    <textarea v-if="field.widget === 'textarea'" :id="fieldId" class="input admin-textarea"
      :value="(modelValue as string) || ''" rows="2" :placeholder="field.placeholder"
      @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"></textarea>

    <!-- select -->
    <select v-else-if="field.widget === 'select'" :id="fieldId" class="input"
      :value="(modelValue as string) ?? ''"
      @change="emit('update:modelValue', ($event.target as HTMLSelectElement).value)">
      <option value="">— Chưa chọn —</option>
      <option v-for="o in field.options || []" :key="String(o)" :value="String(o)">{{ o }}</option>
    </select>

    <!-- bool -->
    <label v-else-if="field.widget === 'bool'" class="sf-bool">
      <input type="checkbox" :checked="!!modelValue"
        @change="emit('update:modelValue', ($event.target as HTMLInputElement).checked)" />
      <span>{{ modelValue ? 'Có' : 'Không' }}</span>
    </label>

    <!-- number -->
    <input v-else-if="field.widget === 'number'" :id="fieldId" type="number" class="input"
      :value="modelValue as number" :min="field.min" :max="field.max" :step="field.step || 'any'"
      :placeholder="field.placeholder"
      @input="onNumber(($event.target as HTMLInputElement).value)" />

    <!-- tags / multiselect (comma-separated) -->
    <input v-else-if="field.widget === 'tags' || field.widget === 'multiselect'" :id="fieldId" class="input"
      :value="tagsText" :placeholder="field.placeholder || 'Cách nhau bằng dấu phẩy'"
      @input="onTags(($event.target as HTMLInputElement).value)" />

    <!-- text / tel / url -->
    <input v-else :id="fieldId" :type="inputType" class="input"
      :value="(modelValue as string) || ''" :placeholder="field.placeholder"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)" />

    <span v-if="field.help" class="sf-help">{{ field.help }}</span>
  </div>
</template>

<script setup lang="ts">
interface FieldDef {
  key: string
  label: string
  widget: string
  required?: boolean
  options?: (string | number)[]
  help?: string
  placeholder?: string
  min?: number
  max?: number
  step?: number
}

const props = defineProps<{ field: FieldDef; modelValue: unknown }>()
const emit = defineEmits<{ 'update:modelValue': [value: unknown] }>()

const fieldId = computed(() => `sf-${props.field.key}`)
const inputType = computed(() => (props.field.widget === 'tel' ? 'tel' : props.field.widget === 'url' ? 'url' : 'text'))

const tagsText = computed(() => (Array.isArray(props.modelValue) ? (props.modelValue as string[]).join(', ') : (props.modelValue as string) || ''))

function onNumber(raw: string) {
  if (raw === '') { emit('update:modelValue', undefined); return }
  const n = Number(raw)
  emit('update:modelValue', Number.isNaN(n) ? raw : n)
}
function onTags(raw: string) {
  const arr = raw.split(',').map(s => s.trim()).filter(Boolean)
  emit('update:modelValue', arr.length ? arr : undefined)
}
</script>

<style scoped>
.sf-field { display: flex; flex-direction: column; gap: .25rem; }
.sf-req { color: var(--error, #e53e3e); }
.sf-help { font-size: .75rem; color: var(--ink-700); }
.sf-bool { display: flex; align-items: center; gap: .5rem; font-size: .9rem; cursor: pointer; }
.sf-bool input { width: 18px; height: 18px; }
</style>
