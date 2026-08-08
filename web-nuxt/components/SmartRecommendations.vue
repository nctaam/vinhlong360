<template>
  <section v-if="visible" class="smart-rec" :data-color-recipe="colorRecipe || undefined">
    <div class="section-head sediment-head">
      <div class="sh-text">
        <h2>{{ title }}</h2>
        <p v-if="subtitle" class="sh-sub">{{ subtitle }}</p>
      </div>
      <span class="ai-label"><IconLine name="sparkles" class="emoji-chip" /> AI gợi ý</span>
    </div>

    <div v-if="loading" class="grid smart-rec-grid" aria-hidden="true">
      <div v-for="i in skeletonCount" :key="i" class="smart-rec-skel"></div>
    </div>
    <div v-else class="grid smart-rec-grid">
      <div v-for="entity in items" :key="entity.id" class="smart-rec-item">
        <!-- `color-recipe` giữ từ main (hệ màu theo vùng); nhánh NP-1 rẽ trước khi có nó. -->
        <EntityCard :entity="entity" :color-recipe="colorRecipe" />
        <!--
          Hai bên cùng chiếm một chỗ "vì sao gợi ý": main hiện một dòng lý do TĨNH,
          NP-1 hiện NÚT mở drawer giải thích (sau cờ recommendation_explanations_v1).
          Dùng v-if/v-else-if chứ không xếp chồng: khi bật cờ thì nút thắng vì nó nói
          được nhiều hơn; khi tắt cờ thì rơi về dòng lý do tĩnh thay vì mất hẳn.
        -->
        <button
          v-if="ff('recommendation_explanations_v1') && explanationFor(entity)"
          type="button"
          class="smart-rec-reason"
          data-action="why-this"
          aria-haspopup="dialog"
          :aria-expanded="whyOpen && selectedEntityId === entity.id"
          @click="openExplanation(entity)"
        >
          <IconLine name="circle-help" aria-hidden="true" />
          Vì sao gợi ý này?
        </button>
        <p v-else-if="reasonFor(entity.id)" class="smart-rec-reason">{{ reasonFor(entity.id) }}</p>
      </div>
    </div>

    <p v-if="drawerStatus" class="smart-rec-status" role="status" aria-live="polite">{{ drawerStatus }}</p>

    <WhyThisDrawer
      v-if="ff('recommendation_explanations_v1')"
      :open="whyOpen"
      :explanation="selectedExplanation"
      preference-href="/cai-dat#khu-vuc-de-xuat"
      @close="closeExplanation"
      @open-preferences="closeExplanation"
      @reset="resetRecommendations"
      @disable-personalization="disablePersonalization"
    />
  </section>
</template>

<script setup lang="ts">
import type { RecommendationCard, RecommendationExplanation } from '~/types/api'
import WhyThisDrawer from './WhyThisDrawer.vue'

const props = withDefaults(defineProps<{
  context?: string
  entityId?: string
  query?: string
  title?: string
  limit?: number
  colorRecipe?: 'tri-region-v1'
}>(), {
  context: 'home',
  title: 'Dành cho bạn',
  limit: 6,
})

const { enabled: ff } = useFeature()
const { items, reasons, profile, loading, source, refresh } = useContextualRecommendations({
  context: computed(() => props.context),
  entityId: computed(() => props.entityId),
  query: computed(() => props.query),
  limit: computed(() => props.limit),
})
const preferences = usePersonalizationPreferences()
const whyOpen = ref(false)
const selectedEntityId = ref('')
const selectedExplanation = ref<Partial<RecommendationExplanation> | null>(null)
const drawerStatus = ref('')
const drawerActionPending = ref(false)

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

function explanationFor(entity: RecommendationCard): Partial<RecommendationExplanation> | null {
  const explanation = entity.explanation
  const primary = explanation?.primary_reason?.trim()
  if (explanation && primary) return explanation
  const legacyReason = reasonFor(entity.id).trim()
  return legacyReason ? { primary_reason: legacyReason, reasons: [legacyReason] } : null
}

function openExplanation(entity: RecommendationCard) {
  if (!ff('recommendation_explanations_v1')) return
  const explanation = explanationFor(entity)
  if (!explanation) return
  selectedEntityId.value = entity.id
  selectedExplanation.value = explanation
  drawerStatus.value = ''
  whyOpen.value = true
}

function closeExplanation() {
  whyOpen.value = false
}

async function resetRecommendations() {
  if (drawerActionPending.value) return
  drawerActionPending.value = true
  const result = await preferences.resetRecommendations()
  if (result.ok) {
    await refresh()
    drawerStatus.value = 'Đã làm mới đề xuất.'
  } else {
    drawerStatus.value = preferences.error.value || 'Không thể làm mới đề xuất lúc này.'
  }
  drawerActionPending.value = false
}

async function disablePersonalization() {
  if (drawerActionPending.value) return
  drawerActionPending.value = true
  const result = await preferences.patch({ personalization_enabled: false })
  if (result.ok) {
    await refresh()
    drawerStatus.value = 'Đã tắt cá nhân hóa. Gợi ý chung vẫn được giữ lại.'
    closeExplanation()
  } else {
    drawerStatus.value = preferences.error.value || 'Không thể tắt cá nhân hóa lúc này.'
  }
  drawerActionPending.value = false
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
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 44px;
  margin: .35rem 0 0;
  padding: 0 var(--space-2);
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--ink-700);
  background: transparent;
  cursor: pointer;
  font: inherit;
  font-size: .82rem;
  font-weight: var(--weight-semibold);
  line-height: 1.4;
}
.smart-rec-reason:hover { color: var(--primary-fg); background: var(--bg-warm); }
.smart-rec-reason:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.smart-rec-reason .line-icon { color: var(--primary-fg); }
.smart-rec-status { margin: var(--space-3) 0 0; color: var(--muted); font-size: var(--text-sm); }
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
