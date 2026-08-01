<template>
  <span
    class="freshness-line"
    data-freshness-line
    data-color-role="status"
    :data-freshness-status="status"
  >
    <IconLine name="clock" aria-hidden="true" />
    <span>{{ meta.label }}</span>
    <span v-if="normalizedUpdatedLabel" class="freshness-line__updated">· {{ normalizedUpdatedLabel }}</span>
  </span>
</template>

<script setup lang="ts">
import type { FreshnessStatus } from '../utils/regionalColor'

const props = defineProps<{
  status: FreshnessStatus
  updatedLabel: string
}>()

const FRESHNESS_META = Object.freeze({
  fresh: { label: 'Mới cập nhật' },
  aging: { label: 'Cần kiểm tra định kỳ' },
  stale: { label: 'Có thể đã cũ' },
  unknown: { label: 'Chưa rõ thời điểm cập nhật' },
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

.freshness-line__updated {
  color: currentColor;
}
</style>
