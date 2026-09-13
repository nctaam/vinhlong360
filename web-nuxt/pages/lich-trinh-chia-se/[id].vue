<script setup lang="ts">
import MekongWaterBadge from '~/components/MekongWaterBadge.vue'
import PlannerRiverTransitWarning from '~/components/planner/PlannerRiverTransitWarning.vue'
import PlannerMobilePassModal from '~/components/planner/PlannerMobilePassModal.vue'

const route = useRoute()
const planId = normalizeRouteParam(route.params.id)
const encodedPlanId = encodePathId(planId)

const goBack = () => goBackOr('/lich-trinh')

const copied = ref(false)
const showPassModal = ref(false)
let copyTimer: ReturnType<typeof setTimeout> | null = null

onUnmounted(() => {
  if (copyTimer) clearTimeout(copyTimer)
})

const modalStops = computed(() => {
  return (plan.value?.stops || []).map((s: any, i: number) => ({
    id: String(s.id || s.entityId || s.entity_id || `stop-${i}`),
    name: s.name || `Điểm dừng ${i + 1}`,
    place_name: s.place_name || s.place || '',
  }))
})

function isMangThitStop(stop: any) {
  const text = `${stop?.name || ''} ${stop?.notes || ''} ${stop?.place_name || ''}`.toLowerCase()
  return text.includes('mang thít') || text.includes('gốm') || text.includes('thầy cai')
}

const { data: plan, status } = await useAsyncData(`shared-plan-${planId}`, async () => {
  try {
    const res = await apiFetch<{ plan: any }>(`/api/shared-plans/${encodedPlanId}`)
    return res?.plan ?? null
  } catch {
    return null
  }
})
if (import.meta.server && !plan.value) {
  throw createError({ statusCode: 404, statusMessage: 'Không tìm thấy lịch trình' })
}

async function copyShareLink() {
  if (import.meta.server) return
  try {
    const url = window.location.href
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(url)
    } else {
      const input = document.createElement('textarea')
      input.value = url
      input.style.position = 'fixed'
      input.style.opacity = '0'
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
    }
    copied.value = true
    if (copyTimer) clearTimeout(copyTimer)
    copyTimer = setTimeout(() => {
      copied.value = false
    }, 2400)
  } catch {
    /* copy best-effort */
  }
}

const planSchema = computed(() => {
  if (!plan.value) return null
  return {
    '@context': 'https://schema.org',
    '@type': 'ItemPage',
    name: plan.value.title,
    description: `Lịch trình trải nghiệm ${plan.value.stops?.length || 0} điểm dừng tại Vĩnh Long`,
    url: canonicalUrl(`/lich-trinh-chia-se/${encodedPlanId}`),
    speakable: buildSpeakableSpecification(['.sp-title', '.sp-meta', '.sp-stops']),
    mainEntity: {
      '@type': 'TouristTrip',
      name: plan.value.title,
      description: `Lịch trình du lịch Vĩnh Long khám phá qua ${plan.value.stops?.length || 0} điểm dừng`,
      touristType: 'Leisure',
      itinerary: {
        '@type': 'ItemList',
        numberOfItems: plan.value.stops?.length || 0,
        itemListElement: (plan.value.stops || []).map((s: any, i: number) => ({
          '@type': 'ListItem',
          position: i + 1,
          name: s.name || `Điểm dừng ${i + 1}`,
          description: s.notes || s.place_name || undefined,
        })),
      },
    },
  }
})

useSeoMeta({
  title: () => plan.value ? `${plan.value.title} — Lịch trình chia sẻ | vinhlong360` : 'Lịch trình chia sẻ | vinhlong360',
  description: () => plan.value ? `Khám phá lịch trình "${plan.value.title}" gồm ${plan.value.stops?.length || 0} điểm dừng trải nghiệm tại Vĩnh Long.` : 'Lịch trình cộng đồng chia sẻ trên Vĩnh Long 360',
  ogTitle: () => plan.value ? `${plan.value.title} — Lịch trình chia sẻ | vinhlong360` : 'Lịch trình chia sẻ | vinhlong360',
  ogDescription: () => plan.value ? `Lịch trình khám phá ${plan.value.stops?.length || 0} điểm dừng trải nghiệm tại Vĩnh Long.` : 'Lịch trình cộng đồng chia sẻ',
  ogUrl: () => canonicalUrl(`/lich-trinh-chia-se/${encodedPlanId}`),
  twitterCard: 'summary_large_image',
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl(`/lich-trinh-chia-se/${encodedPlanId}`) }],
  script: computed(() => {
    const s = planSchema.value
    return s ? [{ type: 'application/ld+json', innerHTML: safeJsonLd(s) }] : []
  }),
})
</script>

<template>
  <section class="page shared-plan-page" data-color-system="tri-region-v1">
    <Breadcrumb
      :items="[
        { label: 'Trang chủ', to: '/' },
        { label: 'Lịch trình', to: '/lich-trinh' },
        { label: plan?.title || 'Lịch trình chia sẻ' }
      ]"
      :json-ld="true"
    >
      <template #before>
        <button type="button" class="bc-back" aria-label="Quay lại" @click="goBack">
          <IconLine name="arrow-left" aria-hidden="true" />
        </button>
      </template>
    </Breadcrumb>

    <div v-if="plan" class="shared-plan card">
      <header class="sp-header">
        <span class="sp-eyebrow">Sổ Hành Trình Du Ký Cửu Long · Bản Chia Sẻ Thực Địa</span>
        <h1 class="sp-title">{{ plan.title }}</h1>
        <div class="sp-meta">
          <span v-if="plan.author" class="sp-meta-item"><IconLine name="user" /> {{ plan.author }}</span>
          <span class="sp-meta-item">· {{ plan.stops?.length || 0 }} điểm dừng</span>
          <div class="sp-water-badge">
            <MekongWaterBadge :interactive="false" show-description />
          </div>
        </div>
      </header>

      <PlannerRiverTransitWarning v-if="plan.stops?.length" :stops="plan.stops" />

      <ol class="sp-stops">
        <li v-for="(s, i) in plan.stops" :key="i" class="sp-stop">
          <span class="sp-num" aria-hidden="true">{{ Number(i) + 1 }}</span>
          <div class="sp-stop-body">
            <div class="sp-stop-head">
              <NuxtLink v-if="s.id" :to="entityPath(s.id)" class="sp-stop-name">{{ s.name }}</NuxtLink>
              <strong v-else class="sp-stop-name">{{ s.name }}</strong>
              <span v-if="isMangThitStop(s)" class="sp-mangthit-badge">
                <IconLine name="award" aria-hidden="true" /> Di sản Mang Thít
              </span>
            </div>
            <div class="sp-stop-meta">
              <small v-if="s.place_name" class="sp-stop-place"><IconLine name="pin" /> {{ s.place_name }}</small>
              <small v-if="s.time" class="sp-stop-time"><IconLine name="clock" /> {{ s.time }}</small>
            </div>
            <p v-if="s.notes" class="sp-stop-notes">{{ s.notes }}</p>
          </div>
        </li>
      </ol>

      <div class="sp-actions">
        <button
          type="button"
          class="btn btn-outline sp-btn-pass btn-export-pass"
          aria-label="Xuất thẻ hành trình bỏ túi"
          @click="showPassModal = true"
        >
          <IconLine name="ticket" class="sp-btn-icon" aria-hidden="true" />
          <span>Thẻ bỏ túi</span>
        </button>
        <button
          type="button"
          class="btn btn-outline sp-btn-share"
          :class="{ 'is-copied': copied }"
          @click="copyShareLink"
        >
          <IconLine :name="copied ? 'check' : 'share'" class="sp-btn-icon" />
          <span>{{ copied ? 'Đã sao chép liên kết!' : 'Chia sẻ lịch trình' }}</span>
        </button>
        <NuxtLink :to="{ path: '/tao-lich-trinh', query: { title: plan?.title } }" class="btn btn-primary sp-btn-create">
          <IconLine name="plus" class="sp-btn-icon" />
          <span>Tạo lịch trình từ gợi ý này</span>
        </NuxtLink>
      </div>

      <PlannerMobilePassModal
        v-model:open="showPassModal"
        :title="plan.title"
        :stops="modalStops"
      />
    </div>

    <SkeletonList v-else-if="status === 'pending'" :count="4" />
    <EmptyState v-else icon-name="map" title="Không tìm thấy lịch trình" message="Lịch trình này không tồn tại hoặc chưa được công khai.">
      <template #actions>
        <NuxtLink to="/lich-trinh" class="btn btn-outline">Xem lịch trình gợi ý</NuxtLink>
      </template>
    </EmptyState>
  </section>
</template>

<style scoped>
.shared-plan-page {
  max-width: 680px;
  margin: 0 auto;
  padding-bottom: var(--space-8);
}
.shared-plan {
  padding: var(--space-6);
  border-radius: var(--radius-surface, 12px);
  border: 1px solid var(--line);
  border-top: 4px solid var(--mangthit-500, var(--color-material-clay));
  background: var(--card);
  box-shadow: var(--shadow-sm);
}
.sp-header {
  margin-bottom: var(--space-6);
}
.sp-eyebrow {
  display: block;
  font-family: var(--font-sans);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--mangthit-500, var(--muted));
  margin-bottom: var(--space-2);
}
.sp-title {
  margin: 0 0 var(--space-2);
  font-family: var(--font-serif, var(--font-editorial));
  font-size: clamp(1.4rem, 4vw, 1.85rem);
  font-weight: var(--weight-bold);
  color: var(--ink);
  line-height: var(--leading-tight);
}
.sp-meta {
  color: var(--muted);
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  font-size: var(--text-sm);
}
.sp-meta-item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}
.sp-water-badge {
  display: inline-flex;
  align-items: center;
  margin-left: auto;
}
.sp-stops {
  list-style: none;
  margin: 0 0 var(--space-6);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.sp-stop {
  display: flex;
  gap: var(--space-3);
  position: relative;
  align-items: flex-start;
}
.sp-stop:not(:last-child)::before {
  content: '';
  position: absolute;
  top: 44px;
  bottom: -16px;
  left: 21px;
  width: 2px;
  background: var(--mangthit-500, var(--line));
  opacity: .35;
}
.sp-num {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  min-width: 44px;
  min-height: 44px;
  border-radius: var(--radius-pill, 999px);
  background: var(--mangthit-600);
  color: var(--white);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--weight-bold);
  font-size: var(--text-sm);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--mangthit-600) 25%, transparent), var(--shadow-sm);
  position: relative;
  z-index: 1;
}
.sp-stop-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  flex: 1;
}
.sp-stop-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.sp-stop-name {
  font-family: var(--font-serif, var(--font-editorial));
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--ink);
  text-decoration: none;
  transition: color .2s var(--ease-out);
}
.sp-stop-name:hover {
  color: var(--color-action);
}
.sp-mangthit-badge,
.stop-mangthit-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  color: var(--mangthit-600);
  background: color-mix(in srgb, var(--mangthit-600) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--mangthit-600) 25%, transparent);
  border-radius: var(--radius-pill, 999px);
  padding: 1px var(--space-2);
}
.dark .sp-mangthit-badge,
.dark .stop-mangthit-badge {
  background: color-mix(in srgb, var(--mangthit-600) 16%, transparent);
  border-color: color-mix(in srgb, var(--mangthit-600) 35%, transparent);
}
.sp-stop-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.sp-stop-place,
.sp-stop-time {
  color: var(--muted);
  font-size: var(--text-xs);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}
.sp-stop-notes {
  margin: var(--space-1) 0 0;
  font-size: var(--text-sm);
  color: var(--ink);
  line-height: var(--leading-relaxed);
  background: var(--bg-warm);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-control);
}
.sp-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  padding-top: var(--space-5);
  border-top: 1px solid var(--line);
}
.sp-btn-pass,
.sp-btn-share,
.sp-btn-create {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 44px;
  min-width: 44px;
  border-radius: var(--radius-control, 8px);
  transition: transform .2s var(--ease-out-expo), box-shadow .2s var(--ease-out);
}
.sp-btn-pass:hover,
.sp-btn-share:hover,
.sp-btn-create:hover {
  transform: translateY(-1px);
}
.sp-btn-pass:active,
.sp-btn-share:active,
.sp-btn-create:active {
  transform: scale(.97);
}
.sp-btn-pass:focus-visible,
.sp-btn-share:focus-visible,
.sp-btn-create:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
@media (prefers-reduced-motion: reduce) {
  .sp-btn-share,
  .sp-btn-create {
    transition: none;
    transform: none;
  }
}
.sp-btn-icon {
  font-size: 1.1em;
}
.sp-btn-share.is-copied {
  border-color: var(--success);
  color: var(--success);
}
@media (max-width: 520px) {
  .sp-actions {
    flex-direction: column;
  }
  .sp-actions .btn {
    width: 100%;
    justify-content: center;
  }
}
</style>
