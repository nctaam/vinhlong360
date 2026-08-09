<template>
  <span
    class="source-mark"
    data-source-mark
    data-color-role="trust"
    :data-source-tier="effectiveTier"
    :class="{ 'source-mark--compact': compact }"
    :aria-label="meta.ariaLabel"
  >
    <IconLine :name="meta.icon" aria-hidden="true" />
    <span>{{ meta.label }}</span>
  </span>
</template>

<script setup lang="ts">
import type { SourceTier } from '../utils/regionalColor'
import { safeUrl } from '~/utils/safe'

const props = withDefaults(defineProps<{
  tier: SourceTier
  compact?: boolean
  sourceTitle?: string | null
  sourceUrl?: string | null
  verifiedAt?: string | null
}>(), {
  compact: false,
  sourceTitle: '',
  sourceUrl: '',
  verifiedAt: '',
})

const SOURCE_META = Object.freeze({
  official: { label: 'Chính thức', icon: 'shield', ariaLabel: 'Nguồn chính thức' },
  verified: { label: 'Có nguồn đối tác', icon: 'check', ariaLabel: 'Nguồn đối tác' },
  community: { label: 'Cộng đồng', icon: 'user', ariaLabel: 'Nguồn cộng đồng' },
  unknown: { label: 'Chưa rõ nguồn', icon: 'info', ariaLabel: 'Nguồn chưa rõ' },
} as const)

function validDate(value?: string | null) {
  if (typeof value !== 'string' || !value.trim()) return ''
  const normalized = value.trim()
  const datePart = /^(\d{4})-(\d{2})-(\d{2})(?:T|$)/.exec(normalized)
  if (!datePart || !Number.isFinite(Date.parse(normalized))) return ''
  const year = Number(datePart[1])
  const month = Number(datePart[2])
  const day = Number(datePart[3])
  const calendarDate = new Date(Date.UTC(year, month - 1, day))
  return calendarDate.getUTCFullYear() === year
    && calendarDate.getUTCMonth() === month - 1
    && calendarDate.getUTCDate() === day
    ? normalized
    : ''
}

const hasVerifiedEvidence = computed(() => Boolean(
  validDate(props.verifiedAt)
  && props.sourceTitle?.trim()
  && safeUrl(props.sourceUrl) !== '#',
))
const effectiveTier = computed<SourceTier>(() => props.tier === 'verified' && !hasVerifiedEvidence.value ? 'unknown' : props.tier)
const meta = computed(() => SOURCE_META[effectiveTier.value])
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
