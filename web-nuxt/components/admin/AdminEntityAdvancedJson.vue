<template>
  <details class="ent-kbyg-details">
    <summary class="admin-label ent-kbyg-summary"><IconLine name="sliders" /> Thuộc tính nâng cao (JSON)</summary>
    <div class="ent-kbyg-fields">
      <p class="sf-help">Các thuộc tính đặc thù không có ô riêng (vd sac_phong, deity_worshipped…). Sửa trực tiếp JSON — các trường đã có ô riêng ở trên sẽ được giữ tách biệt.</p>
      <textarea :value="modelValue" class="input admin-textarea ent-advanced-json" rows="6" spellcheck="false"
        placeholder='{\n  "sac_phong": "…",\n  "custom_key": "…"\n}'
        @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value); $emit('clear-error')"></textarea>
      <span v-if="error" class="form-error" role="alert">{{ error }}</span>
    </div>
  </details>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string
  error: string
}>()

defineEmits<{
  (e: 'update:modelValue', val: string): void
  (e: 'clear-error'): void
}>()
</script>
