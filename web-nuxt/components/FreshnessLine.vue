<template>
  <span
    class="freshness-line"
    data-freshness-line
    data-color-role="status"
    :data-freshness-status="status"
    :aria-label="meta.ariaLabel"
  >
    <IconLine :name="meta.icon" aria-hidden="true" />
    <span>{{ meta.label }}</span>
    <span v-if="normalizedUpdatedLabel" class="freshness-line__updated">· {{ normalizedUpdatedLabel }}</span>
  </span>
</template>

<script setup lang="ts">
import type { FreshnessStatus } from '../utils/regionalColor'

type PublicFreshnessStatus = FreshnessStatus | 'conflict'

const props = defineProps<{
  status: PublicFreshnessStatus
  updatedLabel: string
}>()

const FRESHNESS_META = Object.freeze({
  fresh: { label: 'Mới cập nhật', icon: 'clock', ariaLabel: 'Thông tin mới cập nhật' },
  aging: { label: 'Cần kiểm tra định kỳ', icon: 'clock', ariaLabel: 'Thông tin cần kiểm tra định kỳ' },
  stale: { label: 'Có thể đã cũ', icon: 'alert-triangle', ariaLabel: 'Thông tin có thể đã cũ' },
  unknown: { label: 'Chưa rõ thời điểm cập nhật', icon: 'info', ariaLabel: 'Chưa rõ thời điểm cập nhật' },
  conflict: { label: 'Thông tin có mâu thuẫn', icon: 'alert-triangle', ariaLabel: 'Thông tin có mâu thuẫn' },
} as const)

const meta = computed(() => FRESHNESS_META[props.status])
const normalizedUpdatedLabel = computed(() => props.updatedLabel.trim())
</script>

<style scoped>
.freshness-line {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-1);
  color: var(--color-material-neutral);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}

.freshness-line[data-freshness-status='fresh'] {
  color: var(--color-success);
}

.freshness-line[data-freshness-status='aging'] {
  color: var(--color-warning);
}

.freshness-line[data-freshness-status='stale'] {
  color: var(--color-error);
}

.freshness-line[data-freshness-status='conflict'] {
  color: var(--color-error);
}

.freshness-line__updated {
  color: currentColor;
}
</style>
