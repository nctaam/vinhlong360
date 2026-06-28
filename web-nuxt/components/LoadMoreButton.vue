<template>
  <button
    type="button"
    class="lm-btn"
    :class="{ 'lm-loading': loading }"
    :disabled="loading"
    @click="$emit('load')"
  >
    <span v-if="loading" class="spinner lm-spin" aria-hidden="true"></span>
    {{ loading ? loadingText : label }}
    <span v-if="remaining && !loading" class="lm-count">({{ remaining }})</span>
  </button>
</template>

<script setup lang="ts">
defineProps<{
  loading?: boolean
  label?: string
  loadingText?: string
  remaining?: number
}>()

defineEmits<{ load: [] }>()
</script>

<style scoped>
.lm-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-5);
  border: 1px solid var(--border);
  border-radius: var(--radius-md, 8px);
  background: var(--bg-card);
  color: var(--text);
  font-size: .875rem;
  font-weight: 500;
  cursor: pointer;
  transition: border-color .2s, background .2s;
}
.lm-btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
.lm-btn:active:not(:disabled) { transform: scale(.97); }
.lm-btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.lm-btn:disabled { opacity: .6; cursor: not-allowed; }
.lm-count { color: var(--muted); font-weight: 400; }
.lm-spin { width: 1em; height: 1em; }
.dark .lm-btn { background: rgba(255,255,255,.04); }
@media (prefers-reduced-motion: reduce) {
  .lm-btn, .lm-btn:active { transition: none; transform: none; }
}
</style>
