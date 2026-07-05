<template>
  <button
    ref="btnRef"
    type="button"
    class="lm-btn"
    :class="{ 'lm-loading': loading }"
    :disabled="loading"
    @click="$emit('load')"
  >
    <span v-if="loading" class="spinner lm-spin" aria-hidden="true"></span>
    <span class="lm-label">{{ loading ? loadingText : label }}</span>
    <span v-if="remaining && !loading" class="lm-count">— còn {{ remaining }}</span>
    <span v-if="!loading" class="lm-arrow" aria-hidden="true">→</span>
  </button>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  loading?: boolean
  label?: string
  loadingText?: string
  remaining?: number
}>(), {
  label: 'Xem thêm',
  loadingText: 'Đang tải…',
})

defineEmits<{ load: [] }>()

const btnRef = ref<HTMLButtonElement>()

watch(() => props.loading, (now, prev) => {
  if (prev && !now && btnRef.value) {
    nextTick(() => {
      btnRef.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    })
  }
})
</script>

<style scoped>
/* Editorial "Xem thêm" affordance — reads as an invitation to keep reading the
   shelf, not a boxed pagination control. Hairline underline + quiet arrow
   carry the affordance instead of a heavy bordered button chrome. */
.lm-btn {
  display: inline-flex;
  align-items: baseline;
  gap: var(--space-2);
  min-height: 44px;
  padding: var(--space-2) var(--space-1);
  border: none;
  border-bottom: 1px solid var(--line);
  border-radius: 0;
  background: transparent;
  color: var(--ink);
  font-family: var(--font-editorial);
  font-size: var(--text-base);
  font-weight: 600;
  cursor: pointer;
  transition: border-color .3s var(--ease-out), color .3s var(--ease-out);
}
.lm-btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
.lm-btn:hover:not(:disabled) .lm-arrow { transform: translateX(3px); }
.lm-btn:active:not(:disabled) { transform: scale(.97); }
.lm-btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 4px; }
.lm-btn:disabled { opacity: .6; cursor: not-allowed; }
.lm-label { letter-spacing: -.01em; }
.lm-count {
  color: var(--muted);
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  font-weight: 400;
  font-variant-numeric: tabular-nums;
}
.lm-arrow { display: inline-block; transition: transform .3s var(--ease-out); }
.lm-spin { width: 1em; height: 1em; }
@media (prefers-reduced-motion: reduce) {
  .lm-btn, .lm-btn:active, .lm-arrow { transition: none; transform: none; }
  .lm-btn:hover:not(:disabled) .lm-arrow { transform: none; }
}
@media (forced-colors: active) {
  .lm-btn { border-bottom-color: ButtonText; color: ButtonText; }
}
</style>
