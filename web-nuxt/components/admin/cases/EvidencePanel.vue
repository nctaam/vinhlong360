<script setup lang="ts">
// Evidence, behind the second door.
//
// The safe summary needs no clearance. What a person actually wrote does, and
// the panel says so plainly: step up to open it, watch the clearance expire,
// and lose it the moment it does. The clearance state is text, not a colour.
import { computed } from 'vue'

const props = defineProps<{
  caseId: string
  /** Empty string means no live clearance. */
  stepUpSecret: string
  stepUpExpiresAt?: string | null
  busy?: boolean
}>()

const emit = defineEmits<{
  (event: 'step-up'): void
  (event: 'drop-step-up'): void
  (event: 'add-evidence', body: Record<string, unknown>): void
}>()

const hasClearance = computed(() => Boolean(props.stepUpSecret))
const expiresLabel = computed(() => props.stepUpExpiresAt
  ? new Date(props.stepUpExpiresAt).toLocaleTimeString('vi-VN')
  : null)
</script>

<template>
  <section class="evidence-panel" aria-labelledby="evidence-heading">
    <h3 id="evidence-heading">Chứng cứ</h3>

    <div v-if="!hasClearance" class="evidence-locked" data-role="step-up-prompt">
      <p>
        Nội dung người dân gửi là dữ liệu riêng tư. Xác thực lại để mở trong
        <strong>15 phút</strong>; hết hạn phải xác thực lần nữa.
      </p>
      <button type="button" data-role="step-up" :disabled="busy" @click="emit('step-up')">
        Xác thực để mở chứng cứ
      </button>
    </div>

    <div v-else class="evidence-open">
      <p class="evidence-clearance" aria-live="polite" data-role="clearance-state">
        Đang mở<span v-if="expiresLabel"> — tự khoá lúc {{ expiresLabel }}</span>.
      </p>
      <slot />
      <button type="button" data-role="drop-step-up" @click="emit('drop-step-up')">
        Khoá lại ngay
      </button>
    </div>
  </section>
</template>

<style scoped>
.evidence-panel {
  display: grid;
  gap: 0.6rem;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.8rem 1rem;
}
.evidence-locked p,
.evidence-clearance {
  margin: 0;
}
</style>
