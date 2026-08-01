<template>
  <span
    class="source-mark"
    data-source-mark
    data-color-role="trust"
    :data-source-tier="tier"
    :class="{ 'source-mark--compact': compact }"
  >
    <IconLine :name="meta.icon" aria-hidden="true" />
    <span>{{ meta.label }}</span>
  </span>
</template>

<script setup lang="ts">
import type { SourceTier } from '../utils/regionalColor'

const props = withDefaults(defineProps<{
  tier: SourceTier
  compact?: boolean
}>(), {
  compact: false,
})

const SOURCE_META = Object.freeze({
  official: { label: 'Chính thức', icon: 'shield' },
  verified: { label: 'Đã xác minh', icon: 'check' },
  community: { label: 'Cộng đồng', icon: 'user' },
  unknown: { label: 'Chưa rõ nguồn', icon: 'info' },
} as const)

const meta = computed(() => SOURCE_META[props.tier])
</script>

<style scoped>
.source-mark {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  min-height: var(--space-8);
  padding: var(--space-1) var(--space-2);
  color: var(--color-source-community);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  line-height: var(--lh-xs);
  background: var(--color-source-community-surface);
  border: 1px solid color-mix(in srgb, var(--color-source-community) 48%, transparent);
  border-radius: var(--radius-full);
}

.source-mark[data-source-tier='official'] {
  color: var(--color-source-official);
  background: var(--color-source-official-surface);
  border-color: color-mix(in srgb, var(--color-source-official) 48%, transparent);
}

.source-mark[data-source-tier='verified'] {
  color: var(--color-source-verified);
  background: var(--color-source-verified-surface);
  border-color: color-mix(in srgb, var(--color-source-verified) 48%, transparent);
}

.source-mark--compact {
  min-height: auto;
  padding: var(--space-1);
}

.source-mark :deep(.line-icon) {
  font-size: var(--text-sm);
}
</style>
