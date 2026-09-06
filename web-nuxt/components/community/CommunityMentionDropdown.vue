<template>
  <ul v-if="open && results.length" class="mention-menu" role="listbox" aria-label="Gợi ý @nhắc">
    <li
      v-for="(m, mi) in results"
      :key="m.type + m.id"
      :class="['mention-item', { active: mi === activeIndex }]"
      role="option"
      :aria-selected="mi === activeIndex"
      @mousedown.prevent="$emit('pick', m)"
    >
      <span class="mention-ic" aria-hidden="true"><IconLine :name="m.type === 'user' ? 'user' : 'pin'" /></span>
      <span class="mention-label">{{ m.label }}</span>
      <span class="mention-sub">{{ m.sub }}</span>
    </li>
  </ul>
</template>

<script setup lang="ts">
defineProps<{
  open: boolean
  results: Array<{ type: string; id: string; label: string; sub?: string }>
  activeIndex: number
}>()

defineEmits<{
  (e: 'pick', item: any): void
}>()
</script>
