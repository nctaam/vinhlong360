<template>
  <slot v-if="!error" />
  <div v-else class="error-boundary">
    <div class="error-boundary-inner">
      <span class="error-boundary-icon" aria-hidden="true">⚠️</span>
      <p class="error-boundary-msg">{{ message }}</p>
      <button v-if="retryable" class="error-boundary-retry" @click="retry">Thử lại</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { captureClientError } from '~/composables/useClientError'

const props = withDefaults(defineProps<{
  fallbackMessage?: string
  retryable?: boolean
}>(), {
  fallbackMessage: 'Không thể tải nội dung này.',
  retryable: true,
})

const emit = defineEmits<{ retry: [] }>()

const error = ref<Error | null>(null)
const message = computed(() => props.fallbackMessage)

onErrorCaptured((err: Error) => {
  error.value = err
  // P3: báo lỗi component về backend (best-effort, fire-and-forget, không chặn UI).
  try {
    captureClientError(`ErrorBoundary: ${props.fallbackMessage}`, err)
  } catch {
    /* noop */
  }
  return false
})

function retry() {
  error.value = null
  emit('retry')
}

defineExpose({ error, retry })
</script>

<style scoped>
.error-boundary {
  padding: var(--space-8, 2rem);
  text-align: center;
}
.error-boundary-inner {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2, 0.5rem);
  padding: var(--space-8, 2rem);
  border-radius: var(--radius-lg, 1rem);
  background: var(--bg-alt, #f5f5f5);
}
.error-boundary-icon { font-size: 2rem; }
.error-boundary-msg {
  color: var(--muted, #666);
  font-size: var(--text-sm, 0.875rem);
  margin: 0;
}
.error-boundary-retry {
  margin-top: var(--space-2, 0.5rem);
  padding: var(--space-2, 0.5rem) var(--space-4, 1rem);
  min-height: 44px;
  border: 1px solid var(--border, #ddd);
  border-radius: var(--radius-md, 0.5rem);
  background: var(--card, #fff);
  color: var(--text, #333);
  cursor: pointer;
  font-size: var(--text-sm, 0.875rem);
  transition: background .2s var(--ease-out, ease), transform .08s;
}
.error-boundary-retry:hover {
  background: var(--bg-warm, #eee);
}
.error-boundary-retry:active { transform: scale(.96); transition-duration: .08s; }
</style>
