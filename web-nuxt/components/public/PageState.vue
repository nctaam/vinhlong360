<template>
  <section
    class="page-state"
    :data-page-state="state.kind"
    :role="liveRole"
    :aria-live="livePoliteness"
  >
    <template v-if="state.kind === 'loading'">
      <p class="page-state__copy">Đang tải nội dung.</p>
    </template>

    <template v-else-if="state.kind === 'partial'">
      <div class="page-state__available" data-page-state-available><slot /></div>
      <div class="page-state__notice">
        <IconLine name="alert-triangle" aria-hidden="true" />
        <p class="page-state__copy">Một vài phần chưa tải được. Nội dung còn lại vẫn có thể sử dụng.</p>
      </div>
      <div v-if="retry && state.failedPanels.length" class="page-state__actions" aria-label="Khôi phục phần chưa tải">
        <button v-for="panel in state.failedPanels" :key="panel" type="button" class="page-state__action" data-page-state-retry :data-page-state-panel="panel" :disabled="retryInFlight" :aria-busy="retryInFlight || undefined" @click="retryPanel(panel)">
          {{ retryInFlight ? 'Đang tải lại' : `Tải lại ${panelLabel(panel)}` }}
        </button>
      </div>
    </template>

    <template v-else-if="state.kind === 'stale'">
      <div class="page-state__notice">
        <IconLine name="alert-triangle" aria-hidden="true" />
        <p class="page-state__copy">Có thể đã cũ <time :datetime="state.updatedAt">· {{ state.updatedAt }}</time></p>
      </div>
      <div class="page-state__available" data-page-state-available><slot /></div>
    </template>

    <template v-else-if="state.kind === 'empty'">
      <p class="page-state__title">{{ title }}</p>
      <p class="page-state__copy">Chưa có nội dung phù hợp.</p>
      <button type="button" class="page-state__action" data-page-state-recovery @click="recover">{{ state.recovery.label }}</button>
    </template>

    <template v-else-if="state.kind === 'error'">
      <p class="page-state__title">{{ title }}</p>
      <p class="page-state__copy">Không thể tải nội dung lúc này.</p>
      <button v-if="retry" type="button" class="page-state__action" data-page-state-retry :disabled="retryInFlight" :aria-busy="retryInFlight || undefined" @click="retryPanel()">{{ retryInFlight ? 'Đang tải lại' : state.retry.label || 'Thử lại' }}</button>
      <div v-if="state.fallback !== undefined" class="page-state__available" data-page-state-available><slot /></div>
    </template>

    <template v-else-if="state.kind === 'offline'">
      <div class="page-state__notice">
        <IconLine name="globe" aria-hidden="true" />
        <p class="page-state__copy">Bạn đang ngoại tuyến<span v-if="state.cachedAt"> · Bản lưu {{ state.cachedAt }}</span></p>
      </div>
      <div v-if="state.cached !== undefined" class="page-state__available" data-page-state-available><slot /></div>
    </template>

    <div v-else class="page-state__available" data-page-state-available><slot /></div>
  </section>
</template>

<script setup lang="ts">
import type { SurfaceState } from '~/types/publicExperience'

const props = withDefaults(defineProps<{
  state: SurfaceState<unknown>
  title?: string
  retry?: (panel?: string) => void | Promise<unknown>
  recovery?: () => void
}>(), {
  title: 'Chúng tôi cần thêm thời gian',
  retry: undefined,
  recovery: undefined,
})

const emit = defineEmits<{ recovery: [] }>()
const liveRole = computed(() => props.state.kind === 'error' ? 'alert' : props.state.kind === 'ready' ? undefined : 'status')
const livePoliteness = computed(() => liveRole.value === 'alert' ? 'assertive' : liveRole.value ? 'polite' : undefined)
const retryInFlight = ref(false)

async function retryPanel(panel?: string) {
  if (retryInFlight.value) return
  retryInFlight.value = true
  try {
    await props.retry?.(panel)
  } finally {
    retryInFlight.value = false
  }
}

function recover() {
  props.recovery?.()
  emit('recovery')
}

function panelLabel(panel: string) {
  return panel.trim() || 'phần này'
}
</script>
