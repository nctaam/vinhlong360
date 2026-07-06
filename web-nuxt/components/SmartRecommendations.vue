<template>
  <section v-if="visible" class="smart-rec">
    <div class="section-head sediment-head">
      <div class="sh-text">
        <h2>{{ title }}</h2>
        <p v-if="subtitle" class="sh-sub">{{ subtitle }}</p>
      </div>
      <span class="ai-label"><span class="emoji-chip" aria-hidden="true">✨</span> AI gợi ý</span>
    </div>

    <div v-if="loading" class="grid smart-rec-grid" aria-hidden="true">
      <div v-for="i in skeletonCount" :key="i" class="smart-rec-skel"></div>
    </div>
    <div v-else class="grid smart-rec-grid">
      <div v-for="entity in items" :key="entity.id" class="smart-rec-item">
        <EntityCard :entity="entity" />
        <p v-if="reasonFor(entity.id)" class="smart-rec-reason">{{ reasonFor(entity.id) }}</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  context?: string
  entityId?: string
  query?: string
  title?: string
  limit?: number
}>(), {
  context: 'home',
  title: 'Dành cho bạn',
  limit: 6,
})

const { enabled: ff } = useFeature()
const { items, reasons, profile, loading, source } = useContextualRecommendations({
  context: computed(() => props.context),
  entityId: computed(() => props.entityId),
  query: computed(() => props.query),
  limit: computed(() => props.limit),
})

const visible = computed(() => ff('ai_recommendations') && (loading.value || items.value.length > 0))
const skeletonCount = computed(() => Math.min(Math.max(props.limit || 4, 1), 4))
const subtitle = computed(() => {
  if (source.value !== 'personalized') return ''
  const signalCount = Number(profile.value?.signal_count || 0)
  if (signalCount <= 0) return ''
  return signalCount >= 8 ? 'Ưu tiên theo những gì bạn hay xem, lưu và tìm kiếm.' : 'Đang tinh chỉnh theo hoạt động gần đây của bạn.'
})

function reasonFor(id: string) {
  return reasons.value[id]?.[0] || ''
}
</script>

<style scoped>
.smart-rec {
  max-width: var(--maxw);
  margin: var(--space-8) auto 0;
  padding: 0 var(--space-5);
}
:global(.detail-main) .smart-rec,
:global(.detail-aside) .smart-rec,
:global(.saved-page) .smart-rec,
:global(.cp-page) .smart-rec {
  max-width: none;
  padding: 0;
}
/* h2 already gets the sediment tick from the shared .sediment-head rule
   (components.css targets h2 globally) — only alignment + the quiet AI
   label need scoping here. */
.smart-rec .section-head { align-items: baseline; }
.ai-label {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  color: var(--muted);
  white-space: nowrap;
  flex-shrink: 0;
}
.smart-rec-grid {
  align-items: stretch;
}
.smart-rec-item {
  min-width: 0;
}
.smart-rec-reason {
  margin: .45rem 0 0;
  color: var(--ink-700);
  font-size: .82rem;
  line-height: 1.4;
}
.smart-rec-skel {
  min-height: 260px;
  border-radius: var(--radius);
  background: var(--bg-warm);
  animation: smartRecPulse 1.4s var(--ease-in-out) infinite;
}
@keyframes smartRecPulse {
  0%, 100% { opacity: .55; }
  50% { opacity: .85; }
}
@media (prefers-reduced-motion: reduce) {
  .smart-rec-skel { animation: none; }
}
@media (max-width: 640px) {
  .smart-rec { padding: 0 var(--space-3); }
}
</style>
