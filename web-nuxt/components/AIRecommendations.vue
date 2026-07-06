<template>
  <div v-if="ff('ai_recommendations') && (loading || items.length)" class="ai-recommend">
    <div class="section-head sediment-head ai-rec-head">
      <h2>{{ title }}</h2>
      <span class="ai-label"><IconLine name="sparkles" class="emoji-chip" /> AI gợi ý</span>
    </div>
    <div v-if="loading" class="grid" aria-hidden="true">
      <div v-for="i in skelCount" :key="i" class="ai-rec-skel"></div>
    </div>
    <div v-else class="grid">
      <EntityCard v-for="e in items" :key="e.id" :entity="e" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
const props = defineProps<{
  entityId?: string
  month?: number
  limit?: number
  title?: string
}>()

const items = ref<Entity[]>([])
const loading = ref(true)
const { enabled: ff } = useFeature()
const skelCount = computed(() => Math.min(props.limit || 4, 4))

onMounted(async () => {
  if (!ff('ai_recommendations')) { loading.value = false; return }
  const month = props.month || new Date().getMonth() + 1
  const cacheKey = `airec:${props.entityId || 'home'}:${month}:${props.limit || 6}`

  // Session cache: AI recommendations are stable within a visit — avoid a fresh
  // LLM call on every mount/navigation (cost control, B8).
  try {
    const cached = sessionStorage.getItem(cacheKey)
    if (cached) {
      const list = JSON.parse(cached)
      if (Array.isArray(list)) { items.value = list; loading.value = false; return }
    }
  } catch { /* ignore cache read errors */ }

  try {
    const { aiRecommend } = useAI()
    const res: any = await aiRecommend({ entityId: props.entityId, month, limit: props.limit || 6 })
    const list = res?.recommendations || res?.entities || (Array.isArray(res) ? res : [])
    items.value = Array.isArray(list) ? list : []
    try { sessionStorage.setItem(cacheKey, JSON.stringify(items.value)) } catch { /* quota — skip */ }
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
/* h2 already gets the sediment tick from the shared .sediment-head rule
   (components.css targets h2 globally) — only the quiet AI label needs
   scoping here. */
.ai-rec-head { align-items: baseline; }
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
}
.ai-rec-skel {
  height: 260px; border-radius: var(--radius); background: var(--bg-warm);
  animation: aiRecPulse 1.5s var(--ease-in-out) infinite;
}
@keyframes aiRecPulse { 0%, 100% { opacity: .5; } 50% { opacity: .85; } }
@media (prefers-reduced-motion: reduce) { .ai-rec-skel { animation: none; } }
</style>
