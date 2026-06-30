<template>
  <section class="page saved-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Đã lưu' }]" />

    <div v-if="!isLoggedIn" class="saved-guest card">
      <h1>Đã lưu</h1>
      <p>Đăng nhập để xem nội dung đã lưu.</p>
      <button type="button" class="btn btn-primary" @click="openAuth">Đăng nhập</button>
    </div>

    <template v-else>
      <h1 class="saved-title">Đã lưu</h1>

      <!-- Tabs -->
      <div class="saved-tabs" role="tablist">
        <button v-for="t in tabs" :key="t.key" type="button" role="tab"
                :class="['saved-tab', { active: tab === t.key }]"
                :aria-selected="tab === t.key"
                @click="tab = t.key">
          {{ t.label }}
          <span v-if="t.count != null" class="saved-tab-count">{{ t.count }}</span>
        </button>
      </div>

      <!-- Saved entities -->
      <div v-if="tab === 'entities'" class="saved-panel" role="tabpanel">
        <div v-if="entitiesLoading" class="saved-skeletons">
          <div v-for="i in 4" :key="i" class="skeleton-box saved-card-skel"></div>
        </div>
        <div v-else-if="savedEntities.length" class="saved-grid">
          <div v-for="item in savedEntities" :key="item.id" class="saved-entity card">
            <NuxtLink :to="`/${item.id}`" class="saved-entity-link">
              <img v-if="item.image" :src="item.image" :alt="item.name" class="saved-entity-img" width="120" height="80" loading="lazy" decoding="async" />
              <div class="saved-entity-info">
                <span class="saved-entity-name">{{ item.name }}</span>
                <span v-if="item.type" class="saved-entity-type">{{ item.type }}</span>
                <span v-if="item.place_name" class="saved-entity-place">{{ item.place_name }}</span>
              </div>
            </NuxtLink>
            <button type="button" class="saved-remove" aria-label="Bỏ lưu" @click="removeEntity(item.id)">✕</button>
          </div>
        </div>
        <p v-else class="saved-empty">Chưa lưu địa điểm nào. Khi duyệt các trang địa điểm, nhấn nút lưu để thêm vào đây.</p>
      </div>

      <!-- Bookmarked posts -->
      <div v-if="tab === 'posts'" class="saved-panel" role="tabpanel">
        <div v-if="postsLoading" class="saved-skeletons">
          <div v-for="i in 4" :key="i" class="skeleton-box saved-card-skel"></div>
        </div>
        <div v-else-if="bookmarkedPosts.length" class="saved-posts-list">
          <div v-for="post in bookmarkedPosts" :key="post.id" class="saved-post card">
            <NuxtLink :to="`/bai-viet/${post.id}`" class="saved-post-link">
              <span class="saved-post-title">{{ post.content?.slice(0, 100) || 'Bài viết' }}{{ post.content?.length > 100 ? '…' : '' }}</span>
              <span class="saved-post-meta">
                {{ post.author_name || 'Người dùng' }} · {{ timeAgo(post.bookmarked_at || post.created_at) }}
              </span>
            </NuxtLink>
            <button type="button" class="saved-remove" aria-label="Bỏ lưu" @click="removeBookmark(post.id)">✕</button>
          </div>
        </div>
        <p v-else class="saved-empty">Chưa bookmark bài viết nào.</p>
        <button v-if="postsHasMore && bookmarkedPosts.length" type="button" class="btn btn-secondary saved-load-more" @click="loadMorePosts">
          Xem thêm
        </button>
      </div>

      <!-- Itineraries -->
      <div v-if="tab === 'itineraries'" class="saved-panel" role="tabpanel">
        <div v-if="itinerariesLoading" class="saved-skeletons">
          <div v-for="i in 3" :key="i" class="skeleton-box saved-card-skel"></div>
        </div>
        <div v-else-if="itineraries.length" class="saved-posts-list">
          <div v-for="plan in itineraries" :key="plan.id" class="saved-post card">
            <NuxtLink :to="`/lich-trinh/${plan.id}`" class="saved-post-link">
              <span class="saved-post-title">{{ plan.title || `Lịch trình ${plan.days || ''}` }}</span>
              <span class="saved-post-meta">{{ timeAgo(plan.savedAt || plan.created_at) }}</span>
            </NuxtLink>
            <button type="button" class="saved-remove" aria-label="Xóa lịch trình" @click="removeItinerary(plan.id)">✕</button>
          </div>
        </div>
        <p v-else class="saved-empty">Chưa có lịch trình nào.</p>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
const { isLoggedIn, authHeaders } = useAuth()
const { openAuth } = useAuthModal()
const { timeAgo } = useTimeAgo()
const { favorites, remove: removeFavoriteLocal } = useFavorites()

useHead({
  title: 'Đã lưu',
  meta: [{ name: 'robots', content: 'noindex,nofollow' }],
  link: [{ rel: 'canonical', href: canonicalUrl('/da-luu') }],
})

const tab = ref<'entities' | 'posts' | 'itineraries'>('entities')
const entitiesLoading = ref(true)
const savedEntities = ref<any[]>([])
const postsLoading = ref(false)
const bookmarkedPosts = ref<any[]>([])
const postsPage = ref(1)
const postsHasMore = ref(false)
const itinerariesLoading = ref(false)
const itineraries = ref<any[]>([])

const tabs = computed(() => [
  { key: 'entities' as const, label: 'Địa điểm', count: savedEntities.value.length || favorites.value.length },
  { key: 'posts' as const, label: 'Bài viết', count: bookmarkedPosts.value.length || null },
  { key: 'itineraries' as const, label: 'Lịch trình', count: itineraries.value.length || null },
])

onMounted(async () => {
  if (!isLoggedIn.value) return
  await loadEntities()
})

watch(tab, (t) => {
  if (t === 'posts' && !bookmarkedPosts.value.length && !postsLoading.value) loadPosts()
  if (t === 'itineraries' && !itineraries.value.length && !itinerariesLoading.value) loadItineraries()
})

async function loadEntities() {
  entitiesLoading.value = true
  try {
    const res = await $fetch<{ items: any[] }>('/api/saved', { headers: authHeaders() })
    savedEntities.value = res.items || []
  } catch { /* use local favorites as fallback */ }
  if (!savedEntities.value.length && favorites.value.length) {
    savedEntities.value = favorites.value
  }
  entitiesLoading.value = false
}

async function loadPosts() {
  postsLoading.value = true
  try {
    const res = await $fetch<{ items: any[]; total: number }>('/api/me/bookmarks?page=1&limit=20', { headers: authHeaders() })
    bookmarkedPosts.value = res.items || []
    postsHasMore.value = (res.total || 0) > bookmarkedPosts.value.length
    postsPage.value = 1
  } catch { /* empty state */ }
  postsLoading.value = false
}

async function loadMorePosts() {
  postsPage.value++
  try {
    const res = await $fetch<{ items: any[]; total: number }>(`/api/me/bookmarks?page=${postsPage.value}&limit=20`, { headers: authHeaders() })
    bookmarkedPosts.value.push(...(res.items || []))
    postsHasMore.value = (res.total || 0) > bookmarkedPosts.value.length
  } catch { /* ignore */ }
}

async function loadItineraries() {
  itinerariesLoading.value = true
  try {
    const res = await $fetch<{ plans: any[] }>('/api/my-plans', { headers: authHeaders() })
    itineraries.value = res.plans || []
  } catch { /* empty state */ }
  itinerariesLoading.value = false
}

function removeEntity(id: string) {
  savedEntities.value = savedEntities.value.filter(e => e.id !== id)
  removeFavoriteLocal(id)
}

async function removeBookmark(postId: string) {
  bookmarkedPosts.value = bookmarkedPosts.value.filter(p => p.id !== postId)
  try { await $fetch(`/api/posts/${postId}/bookmark`, { method: 'DELETE', headers: authHeaders() }) } catch { /* ignore */ }
}

async function removeItinerary(planId: string) {
  itineraries.value = itineraries.value.filter(p => p.id !== planId)
  try { await $fetch(`/api/my-plans/${planId}`, { method: 'DELETE', headers: authHeaders() }) } catch { /* ignore */ }
}
</script>

<style scoped>
.saved-page { max-width: 720px; margin: 0 auto; }
.saved-guest { padding: 2rem; text-align: center; }
.saved-guest h1 { margin: 0 0 1rem; font-size: 1.5rem; }
.saved-guest p { color: var(--ink-700); margin-bottom: 1rem; }
.saved-title { font-size: 1.4rem; margin: 0 0 1rem; }

/* Tabs */
.saved-tabs {
  display: flex; gap: .25rem; margin-bottom: 1.25rem;
  border-bottom: 2px solid var(--line); padding-bottom: 0;
}
.saved-tab {
  padding: .5rem 1rem; background: none; border: none; cursor: pointer;
  font-weight: 500; font-size: .9rem; color: var(--ink-700);
  border-bottom: 2px solid transparent; margin-bottom: -2px;
  transition: color .15s, border-color .15s;
}
.saved-tab:hover { color: var(--ink); }
.saved-tab.active { color: var(--primary); border-bottom-color: var(--primary); font-weight: 600; }
.saved-tab-count {
  display: inline-block; margin-left: .35rem;
  background: var(--bg-alt); padding: 0 5px; border-radius: var(--radius-full);
  font-size: .75rem; font-weight: 600; color: var(--ink-700);
}
.saved-tab.active .saved-tab-count { background: var(--primary-light, #f0e6df); color: var(--primary); }

/* Entity grid */
.saved-grid { display: flex; flex-direction: column; gap: .5rem; }
.saved-entity { display: flex; align-items: center; padding: .5rem; gap: 0; }
.saved-entity-link {
  display: flex; align-items: center; gap: .75rem; flex: 1; min-width: 0;
  text-decoration: none; color: var(--ink);
}
.saved-entity-img { width: 80px; height: 56px; border-radius: var(--radius-md); object-fit: cover; flex-shrink: 0; }
.saved-entity-info { flex: 1; min-width: 0; }
.saved-entity-name { display: block; font-weight: 600; font-size: .92rem; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.saved-entity-type { display: block; font-size: .78rem; color: var(--ink-700); }
.saved-entity-place { display: block; font-size: .78rem; color: var(--ink-700); }
.saved-remove {
  flex-shrink: 0; width: 28px; height: 28px; border: none; background: none;
  color: var(--ink-700); cursor: pointer; font-size: .85rem;
  border-radius: var(--radius-full); transition: background .15s;
}
.saved-remove:hover { background: var(--bg-alt); color: var(--error, #e53e3e); }

/* Posts list */
.saved-posts-list { display: flex; flex-direction: column; gap: .5rem; }
.saved-post { padding: .75rem 1rem; display: flex; align-items: center; gap: .5rem; }
.saved-post-link { text-decoration: none; color: var(--ink); display: block; flex: 1; min-width: 0; }
.saved-post-title { display: block; font-weight: 500; font-size: .92rem; line-height: 1.4; }
.saved-post-meta { display: block; font-size: .78rem; color: var(--ink-700); margin-top: .2rem; }
.saved-load-more { margin-top: .75rem; width: 100%; }

/* Skeletons & empty */
.saved-skeletons { display: flex; flex-direction: column; gap: .5rem; }
.saved-card-skel { height: 64px; border-radius: var(--radius-md); }
.saved-empty { color: var(--ink-700); font-size: .9rem; text-align: center; padding: 2rem 1rem; }

/* Dark */
.dark .saved-entity { background: var(--bg-alt); }
.dark .saved-post { background: var(--bg-alt); }

/* Mobile */
@media (max-width: 600px) {
  .saved-tab { padding: .5rem .6rem; font-size: .82rem; }
  .saved-entity-img { width: 60px; height: 42px; }
}
</style>
