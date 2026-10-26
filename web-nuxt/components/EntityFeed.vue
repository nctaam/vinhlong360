<template>
  <section
    v-if="loading || posts.length"
    class="entity-feed reveal"
    data-image-surface="entity-feed"
    data-source-class="user-uploaded"
    data-entity-image-policy="no-image-invariant"
  >
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

</script>

<style scoped>
.entity-feed { margin-top: var(--space-6); }
.ef-head { margin: 0 0 var(--space-2); }
.ef-title { font-family: var(--font-editorial); font-size: var(--text-lg); font-weight: 600; line-height: var(--leading-snug); text-wrap: balance; overflow-wrap: break-word; margin: 0; }

/* Tri-province sediment rule — same card-scale hairline idiom as
   NearbyEntities.vue's .nb-rule / PostCard.vue's .thread-rule — separates
   the section head from the list beneath it. */
.ef-rule {
  display: block;
  width: 48px;
  height: 2px;
  border-radius: var(--radius-pill, 999px);
  margin: 0 0 var(--space-3);
  background: linear-gradient(90deg, var(--color-material-river) 0%, var(--color-material-amber) 52%, var(--color-material-clay) 100%);
}
.ef-rating { letter-spacing: -2px; }
.ef-likes { font-variant-numeric: tabular-nums; }

.ef-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: var(--space-2); }
.ef-link {
  display: flex; gap: var(--space-3); padding: var(--space-3);
  background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-sheet);
  text-decoration: none; color: var(--ink);
  transition: border-color .25s var(--ease-out), transform .2s var(--ease-out-expo);
}
.ef-link:hover { border-color: var(--color-action); transform: translateY(-1px); }
.ef-avatar {
  width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--color-brand); color: var(--text-on-dark, var(--white)); font-weight: var(--weight-semibold); font-size: var(--text-sm);
}
.ef-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: .2rem; }
.ef-author { font-weight: var(--weight-semibold); font-size: var(--text-sm); line-height: 1.35; overflow-wrap: break-word; }
.ef-text { margin: 0; font-size: var(--text-sm); color: var(--ink-secondary, var(--ink)); line-height: var(--leading-relaxed); overflow-wrap: break-word; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.ef-meta { display: flex; align-items: center; gap: var(--space-2); font-size: var(--text-xs); color: var(--muted); flex-wrap: wrap; }
.ef-more { display: block; text-align: center; padding: var(--space-3); font-size: var(--text-sm); font-weight: var(--weight-medium); color: var(--color-action); text-decoration: none; border: .5px solid var(--line); border-radius: var(--radius-sheet); margin-top: var(--space-2); transition: background-color .2s ease; }
.ef-more:hover { background: rgba(var(--color-action-rgb), .06); }

.ef-skeleton { display: flex; flex-direction: column; gap: var(--space-2); }
.ef-sk-item { display: flex; gap: var(--space-3); padding: var(--space-3); background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-sheet); }
.ef-sk-avatar { width: 36px; height: 36px; border-radius: 50%; background: var(--bg-alt); flex-shrink: 0; animation: skPulse 1.2s var(--ease-in-out) infinite; }
.ef-sk-lines { flex: 1; display: flex; flex-direction: column; gap: 6px; padding-top: var(--space-1); }
.ef-sk-line { height: 10px; border-radius: 4px; background: var(--bg-alt); animation: skPulse 1.2s var(--ease-in-out) infinite; }
.ef-sk-line.w60 { width: 60%; }
.ef-sk-line.w90 { width: 90%; }
.ef-sk-line.w40 { width: 40%; }
@keyframes skPulse { 0%, 100% { opacity: .4; } 50% { opacity: .8; } }
@media (prefers-reduced-motion: reduce) { .ef-sk-avatar, .ef-sk-line { animation: none; } }
</style>
