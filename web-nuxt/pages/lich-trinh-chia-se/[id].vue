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
        <h1 class="sp-title">{{ plan.title }}</h1>
        <p class="sp-meta">
          <span v-if="plan.author" class="sp-meta-item"><IconLine name="user" /> {{ plan.author }}</span>
          <span class="sp-meta-item">· {{ plan.stops?.length || 0 }} điểm dừng</span>
        </p>
      </header>

      <ol class="sp-stops">
        <li v-for="(s, i) in plan.stops" :key="i" class="sp-stop">
          <span class="sp-num" aria-hidden="true">{{ Number(i) + 1 }}</span>
          <div class="sp-stop-body">
            <NuxtLink v-if="s.id" :to="entityPath(s.id)" class="sp-stop-name">{{ s.name }}</NuxtLink>
            <strong v-else class="sp-stop-name">{{ s.name }}</strong>
            <small v-if="s.place_name" class="sp-stop-place"><IconLine name="pin" /> {{ s.place_name }}</small>
            <small v-if="s.time" class="sp-stop-time"><IconLine name="clock" /> {{ s.time }}</small>
            <p v-if="s.notes" class="sp-stop-notes">{{ s.notes }}</p>
          </div>
        </li>
      </ol>

      <div class="sp-actions">
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
    </div>

    <SkeletonList v-else-if="status === 'pending'" :count="4" />
    <EmptyState v-else icon-name="map" title="Không tìm thấy lịch trình" message="Lịch trình này không tồn tại hoặc chưa được công khai.">
      <template #actions>
        <NuxtLink to="/lich-trinh" class="btn btn-outline">Xem lịch trình gợi ý</NuxtLink>
      </template>
    </EmptyState>
  </section>
</template>

<script setup lang="ts">
const route = useRoute()
const planId = normalizeRouteParam(route.params.id)
const encodedPlanId = encodePathId(planId)

const goBack = () => goBackOr('/lich-trinh')

const copied = ref(false)
let copyTimer: ReturnType<typeof setTimeout> | null = null

onUnmounted(() => {
  if (copyTimer) clearTimeout(copyTimer)
})

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

<style scoped>
.shared-plan-page {
  max-width: 680px;
  margin: 0 auto;
  padding-bottom: var(--space-8);
}
.shared-plan {
  padding: var(--space-6);
  border-radius: var(--radius-surface);
}
.sp-header {
  margin-bottom: var(--space-6);
}
.sp-title {
  margin: 0 0 var(--space-2);
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
}
.sp-stop:not(:last-child)::before {
  content: '';
  position: absolute;
  top: 36px;
  bottom: -16px;
  left: 15px;
  width: 2px;
  background: var(--line);
}
.sp-num {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--color-brand);
  color: var(--color-on-action, var(--white));
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--weight-bold);
  font-size: var(--text-sm);
  box-shadow: var(--shadow-sm);
  position: relative;
  z-index: 1;
}
.sp-stop-body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  flex: 1;
}
.sp-stop-name {
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  color: var(--ink);
  text-decoration: none;
  transition: color .2s var(--ease-out);
}
.sp-stop-name:hover {
  color: var(--color-action);
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
.sp-btn-share,
.sp-btn-create {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 44px;
  transition: transform .2s var(--ease-out-expo), box-shadow .2s var(--ease-out);
}
.sp-btn-share:hover,
.sp-btn-create:hover {
  transform: translateY(-1px);
}
.sp-btn-share:active,
.sp-btn-create:active {
  transform: scale(.97);
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
