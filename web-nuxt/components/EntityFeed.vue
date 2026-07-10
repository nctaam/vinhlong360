<template>
  <section v-if="loading || posts.length" class="entity-feed reveal">
    <div class="sediment-head ef-head">
      <h2 class="ef-title">Cộng đồng chia sẻ về {{ entityName }}</h2>
    </div>
    <span class="ef-rule" aria-hidden="true"></span>
    <div v-if="loading" class="ef-skeleton">
      <div v-for="i in 2" :key="i" class="ef-sk-item"><div class="ef-sk-avatar"></div><div class="ef-sk-lines"><div class="ef-sk-line w60"></div><div class="ef-sk-line w90"></div><div class="ef-sk-line w40"></div></div></div>
    </div>
    <ul class="ef-list">
      <li v-for="p in posts" :key="p.id" class="ef-item">
        <NuxtLink :to="postPath(p.id)" class="ef-link">
          <span class="ef-avatar">{{ (p.display_name || '?')[0].toUpperCase() }}</span>
          <div class="ef-body">
            <span class="ef-author">{{ p.display_name }}</span>
            <p class="ef-text">{{ truncateText(p.content, 120) }}</p>
            <span class="ef-meta">
              <span v-if="p.rating" class="ef-rating" aria-hidden="true"><IconLine v-for="i in p.rating" :key="i" name="star" /></span>
              <span v-if="p.like_count" class="ef-likes">{{ p.like_count }} thích</span>
              <time :datetime="p.created_at">{{ timeAgo(p.created_at) }}</time>
            </span>
          </div>
          <NuxtImg v-if="firstImage(p) && isRemoteUrl(firstImage(p)!)" :src="firstImage(p)!" :alt="`Ảnh bài viết của ${p.display_name || 'người dùng'}`" class="ef-thumb" loading="lazy" decoding="async" width="80" height="80" sizes="80px" @error="hideImage" />
          <img v-else-if="firstImage(p)" :src="firstImage(p)!" :alt="`Ảnh bài viết của ${p.display_name || 'người dùng'}`" class="ef-thumb" loading="lazy" decoding="async" width="80" height="80" @error="hideImage" />
        </NuxtLink>
      </li>
    </ul>
    <NuxtLink v-if="total > posts.length" :to="communityEntityPath" class="ef-more">
      Xem tất cả {{ total }} bài viết
    </NuxtLink>
  </section>
</template>

<script setup lang="ts">
const props = defineProps<{ entityId: string; entityName: string }>()
const { timeAgo } = useTimeAgo()


const posts = ref<any[]>([])
const total = ref(0)
const loading = ref(true)
const communityEntityPath = computed(() => `/cong-dong?entity=${encodeURIComponent(props.entityId)}`)

onMounted(async () => {
  try {
    const params = new URLSearchParams({ limit: '5' })
    const res = await $fetch<any>(`/api/entities/${encodePathId(props.entityId)}/feed?${params}`)
    posts.value = res.posts || []
    total.value = res.total || 0
  } catch { /* non-critical */ } finally { loading.value = false }
})



function firstImage(p: any): string | null {
  if (Array.isArray(p.images) && p.images.length) return p.images[0]
  return null
}

function hideImage(payload: Event | string) {
  if (typeof payload === 'string') return
  const img = payload.target
  if (img instanceof HTMLImageElement) img.style.display = 'none'
}
</script>

<style scoped>
.entity-feed { margin-top: var(--space-6); }
.ef-head { margin: 0 0 var(--space-2); }
.ef-title { font-family: var(--font-editorial); font-size: var(--text-lg); font-weight: 600; margin: 0; }

/* Tri-province sediment rule — same card-scale hairline idiom as
   NearbyEntities.vue's .nb-rule / PostCard.vue's .thread-rule — separates
   the section head from the list beneath it. */
.ef-rule {
  display: block;
  width: 48px;
  height: 2px;
  border-radius: var(--radius-full);
  margin: 0 0 var(--space-3);
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .ef-rule {
  background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%);
}

/* Emoji-in-chip idiom (replicated locally; see PostCard.vue for the
   shared source pattern) — houses the rating stars and any bare emoji
   so they never float directly beside serif/body text. */
.emoji-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.4em;
  padding: 0 .3em;
  border-radius: var(--radius-sm);
  background: var(--bg-alt);
  font-size: .85em;
  line-height: 1.4;
}
.ef-rating { letter-spacing: -2px; }
.ef-likes { font-variant-numeric: tabular-nums; }

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
  background: var(--primary); color: var(--text-on-dark, var(--white)); font-weight: var(--weight-semibold); font-size: var(--text-sm);
}
.ef-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: .2rem; }
.ef-author { font-weight: var(--weight-semibold); font-size: var(--text-sm); }
.ef-text { margin: 0; font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); line-height: var(--leading-relaxed); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.ef-meta { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-xs); color: var(--muted); flex-wrap: wrap; }
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
.ef-sk-avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--bg-alt); flex-shrink: 0; animation: skPulse 1.2s var(--ease-in-out) infinite; }
.ef-sk-lines { flex: 1; display: flex; flex-direction: column; gap: 6px; padding-top: var(--space-1); }
.ef-sk-line { height: 10px; border-radius: 4px; background: var(--bg-alt); animation: skPulse 1.2s var(--ease-in-out) infinite; }
.ef-sk-line.w60 { width: 60%; }
.ef-sk-line.w90 { width: 90%; }
.ef-sk-line.w40 { width: 40%; }
@keyframes skPulse { 0%, 100% { opacity: .4; } 50% { opacity: .8; } }
@media (prefers-reduced-motion: reduce) { .ef-sk-avatar, .ef-sk-line { animation: none; } }
</style>
