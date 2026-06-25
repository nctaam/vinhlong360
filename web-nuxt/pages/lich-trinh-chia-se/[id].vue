<template>
  <section class="page shared-plan-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lịch trình', to: '/lich-trinh' }, { label: plan?.title || 'Lịch trình chia sẻ' }]" />

    <div v-if="plan" class="shared-plan card">
      <h1>{{ plan.title }}</h1>
      <p class="sp-meta">
        <span v-if="plan.author">👤 {{ plan.author }}</span>
        <span>· {{ plan.stops.length }} điểm</span>
      </p>
      <ol class="sp-stops">
        <li v-for="(s, i) in plan.stops" :key="i" class="sp-stop">
          <span class="sp-num">{{ i + 1 }}</span>
          <div class="sp-stop-body">
            <NuxtLink v-if="s.id" :to="`/dia-diem/${s.id}`" class="sp-stop-name">{{ s.name }}</NuxtLink>
            <strong v-else class="sp-stop-name">{{ s.name }}</strong>
            <small v-if="s.place_name" class="sp-stop-place">📍 {{ s.place_name }}</small>
            <small v-if="s.time" class="sp-stop-time">🕒 {{ s.time }}</small>
            <p v-if="s.notes" class="sp-stop-notes">{{ s.notes }}</p>
          </div>
        </li>
      </ol>
      <NuxtLink to="/tao-lich-trinh" class="btn btn-primary">Tạo lịch trình của bạn</NuxtLink>
    </div>

    <SkeletonList v-else-if="status === 'pending'" :count="4" />
    <EmptyState v-else icon="🗺️" title="Không tìm thấy lịch trình" message="Lịch trình này không tồn tại hoặc chưa được công khai.">
      <NuxtLink to="/lich-trinh" class="btn btn-outline">Xem lịch trình gợi ý</NuxtLink>
    </EmptyState>
  </section>
</template>

<script setup lang="ts">
const route = useRoute()
const planId = String(route.params.id || '')

const { data: plan, status } = await useAsyncData(`shared-plan-${planId}`, async () => {
  try {
    const res = await apiFetch<{ plan: any }>(`/api/shared-plans/${encodeURIComponent(planId)}`)
    return res?.plan ?? null
  } catch {
    return null
  }
})

useSeoMeta({
  title: () => plan.value ? `${plan.value.title} — Lịch trình chia sẻ` : 'Lịch trình chia sẻ',
  description: () => plan.value ? `Lịch trình ${plan.value.stops?.length || 0} điểm tại Vĩnh Long` : 'Lịch trình cộng đồng chia sẻ',
  robots: 'noindex,follow',
})
useHead({ link: [{ rel: 'canonical', href: canonicalUrl(`/lich-trinh-chia-se/${planId}`) }] })
</script>

<style scoped>
.shared-plan-page { max-width: 680px; margin: 0 auto; }
.shared-plan { padding: 1.5rem; }
.shared-plan h1 { margin: 0 0 .5rem; font-size: 1.5rem; }
.sp-meta { color: var(--ink-700); display: flex; gap: .4rem; margin-bottom: 1.25rem; font-size: var(--text-sm); }
.sp-stops { list-style: none; margin: 0 0 1.5rem; padding: 0; display: flex; flex-direction: column; gap: .9rem; }
.sp-stop { display: flex; gap: .75rem; }
.sp-num { flex-shrink: 0; width: 28px; height: 28px; border-radius: 999px; background: var(--primary); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: .85rem; }
.sp-stop-body { display: flex; flex-direction: column; gap: .15rem; }
.sp-stop-name { font-weight: var(--weight-medium); color: var(--ink-900); text-decoration: none; }
.sp-stop-place, .sp-stop-time { color: var(--ink-700); font-size: var(--text-sm); }
.sp-stop-notes { margin: .2rem 0 0; font-size: var(--text-sm); color: var(--ink); }
</style>
