<template>
  <section v-if="loading || posts.length" class="entity-feed">
    <h3 class="ef-title">Cộng đồng chia sẻ về {{ entityName }}</h3>
    <div v-if="loading" class="ef-skeleton">
      <div v-for="i in 2" :key="i" class="ef-sk-item"><div class="ef-sk-avatar"></div><div class="ef-sk-lines"><div class="ef-sk-line w60"></div><div class="ef-sk-line w90"></div><div class="ef-sk-line w40"></div></div></div>
    </div>
    <ul class="ef-list">
      <li v-for="p in posts" :key="p.id" class="ef-item">
        <NuxtLink :to="`/bai-viet/${p.id}`" class="ef-link">
          <span class="ef-avatar">{{ (p.display_name || '?')[0].toUpperCase() }}</span>
          <div class="ef-body">
            <span class="ef-author">{{ p.display_name }}</span>
            <p class="ef-text">{{ truncate(p.content, 120) }}</p>
            <span class="ef-meta">
              <span v-if="p.rating" class="ef-rating">{{ '⭐'.repeat(p.rating) }}</span>
              <span v-if="p.like_count">{{ p.like_count }} thích</span>
              <time :datetime="p.created_at">{{ timeAgo(p.created_at) }}</time>
            </span>
          </div>
          <NuxtImg v-if="firstImage(p) && isRemoteUrl(firstImage(p)!)" :src="firstImage(p)!" :alt="`Ảnh bài viết của ${p.display_name || 'người dùng'}`" class="ef-thumb" loading="lazy" decoding="async" width="80" height="80" />
          <img v-else-if="firstImage(p)" :src="firstImage(p)!" :alt="`Ảnh bài viết của ${p.display_name || 'người dùng'}`" class="ef-thumb" loading="lazy" decoding="async" width="80" height="80" />
        </NuxtLink>
      </li>
    </ul>
    <NuxtLink v-if="total > posts.length" :to="`/cong-dong?entity=${entityId}`" class="ef-more">
      Xem tất cả {{ total }} bài viết
    </NuxtLink>
  </section>
</template>

<script setup lang="ts">
const props = defineProps<{ entityId: string; entityName: string }>()
const { timeAgo } = useTimeAgo()
const isRemoteUrl = (url: string) => /^https?:\/\//.test(url)

const posts = ref<any[]>([])
const total = ref(0)
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await $fetch<any>(`/api/entities/${props.entityId}/feed?limit=5`)
    posts.value = res.posts || []
    total.value = res.total || 0
  } catch { /* non-critical */ } finally { loading.value = false }
})

function truncate(text: string, max: number): string {
  if (!text || text.length <= max) return text || ''
  return text.slice(0, max).replace(/\s+\S*$/, '') + '…'
}

function firstImage(p: any): string | null {
  if (Array.isArray(p.images) && p.images.length) return p.images[0]
  return null
}
</script>

<style scoped>
.entity-feed { margin-top: var(--space-6); }
.ef-title { font-size: var(--text-lg); font-weight: var(--weight-bold); margin: 0 0 var(--space-4); }
.ef-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.ef-link {
  display: flex; gap: var(--space-3); padding: var(--space-3);
  background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-lg);
  text-decoration: none; color: var(--ink);
  transition: border-color .25s var(--ease-out), transform .2s var(--ease-spring-gentle);
}
.ef-link:hover { border-color: var(--primary-fg); transform: translateY(-1px); }
.ef-avatar {
  width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--primary); color: #fff; font-weight: var(--weight-semibold); font-size: var(--text-sm);
}
.ef-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: .2rem; }
.ef-author { font-weight: var(--weight-semibold); font-size: var(--text-sm); }
.ef-text { margin: 0; font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); line-height: var(--leading-relaxed); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.ef-meta { display: flex; gap: var(--space-2); font-size: var(--text-xs); color: var(--muted); flex-wrap: wrap; }
.ef-rating { letter-spacing: -2px; }
.ef-thumb { width: 56px; height: 56px; border-radius: var(--radius-md); object-fit: cover; flex-shrink: 0; }
.ef-more { display: block; text-align: center; padding: var(--space-3); font-size: var(--text-sm); font-weight: var(--weight-medium); color: var(--primary-fg); text-decoration: none; border: .5px solid var(--line); border-radius: var(--radius-lg); margin-top: var(--space-2); transition: background .2s; }
.ef-more:hover { background: rgba(var(--primary-rgb), .04); }

.dark .ef-link { background: var(--bg-alt); }
.dark .ef-more:hover { background: rgba(255,255,255,.04); }

@media (max-width: 600px) {
  .ef-thumb { width: 48px; height: 48px; }
}

.ef-skeleton { display: flex; flex-direction: column; gap: var(--space-2); }
.ef-sk-item { display: flex; gap: var(--space-3); padding: var(--space-3); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-lg); }
.ef-sk-avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--bg-alt); flex-shrink: 0; animation: skPulse 1.2s ease-in-out infinite; }
.ef-sk-lines { flex: 1; display: flex; flex-direction: column; gap: 6px; padding-top: 4px; }
.ef-sk-line { height: 10px; border-radius: 4px; background: var(--bg-alt); animation: skPulse 1.2s ease-in-out infinite; }
.ef-sk-line.w60 { width: 60%; }
.ef-sk-line.w90 { width: 90%; }
.ef-sk-line.w40 { width: 40%; }
@keyframes skPulse { 0%, 100% { opacity: .4; } 50% { opacity: .8; } }
</style>
