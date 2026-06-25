<template>
  <div>
    <div class="admin-head-row">
      <div>
        <h1>Thu vien anh</h1>
        <p class="media-subtitle">Tat ca hinh anh tu cac entity — loc trung lap, thieu credit</p>
      </div>
      <button type="button" class="admin-refresh" :disabled="loading" @click="fetchMedia">
        <span :class="{ 'refresh-spin': loading }">&#8635;</span> Lam moi
      </button>
    </div>

    <!-- Stats -->
    <div class="stat-grid" v-if="stats">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_images }}</div>
        <div class="stat-label">Tong anh</div>
      </div>
      <div class="stat-card" :class="{ 'status-warn': stats.duplicates > 0 }">
        <div class="stat-value">{{ stats.duplicates }}</div>
        <div class="stat-label">URL trung lap</div>
      </div>
      <div class="stat-card" :class="{ 'status-warn': stats.missing_credit > 0 }">
        <div class="stat-value">{{ stats.missing_credit }}</div>
        <div class="stat-label">Thieu credit</div>
      </div>
    </div>

    <!-- Filter tabs -->
    <div class="media-tabs">
      <button v-for="f in FILTERS" :key="f.key" type="button" class="media-tab" :class="{ active: filter === f.key }" @click="setFilter(f.key)">{{ f.label }}</button>
    </div>

    <div v-if="loading" class="admin-loading"><div class="spinner"></div></div>
    <template v-else>

    <div v-if="!items.length" class="admin-empty-state">
      <div class="admin-empty-state-icon">&#128247;</div>
      <div class="admin-empty-state-text">Khong co anh nao{{ filter !== 'all' ? ' voi bo loc nay' : '' }}</div>
    </div>

    <!-- Image grid -->
    <div class="media-grid">
      <div v-for="item in items" :key="item.url + item.entity_id" class="media-card" role="button" tabindex="0" @click="previewItem = item" @keydown.enter="previewItem = item">
        <div class="media-img-wrap">
          <img :src="item.url" :alt="item.entity_name" loading="lazy" decoding="async" @error="onImgError" />
          <span v-if="item.usage_count > 1" class="media-dup-badge" title="Dung boi nhieu entity">{{ item.usage_count }}x</span>
        </div>
        <div class="media-card-info">
          <span class="media-entity-name">{{ item.entity_name }}</span>
          <span class="media-entity-type">{{ item.entity_type }}</span>
          <span v-if="item.credit" class="media-credit">{{ item.credit }}</span>
          <span v-else class="media-no-credit">Thieu credit</span>
        </div>
      </div>
    </div>

    <!-- Load more -->
    <button v-if="hasMore" type="button" class="btn btn-outline media-load-more" :disabled="loading" @click="loadMore">Xem them ({{ total - items.length }} con lai)</button>

    </template>

    <!-- Preview modal -->
    <Transition name="modal-fade">
    <div v-if="previewItem" class="modal-overlay show" role="dialog" aria-modal="true" @click.self="previewItem = null" @keyup.escape="previewItem = null">
      <div class="modal admin-modal-lg">
        <div class="media-preview-header">
          <strong>{{ previewItem.entity_name }}</strong>
          <button type="button" class="btn btn-ghost btn-sm" @click="previewItem = null">Dong</button>
        </div>
        <img :src="previewItem.url" :alt="previewItem.entity_name" class="media-preview-img" />
        <div class="media-preview-meta">
          <div><strong>Entity:</strong> <NuxtLink :to="`/dia-diem/${previewItem.entity_id}`" target="_blank">{{ previewItem.entity_name }}</NuxtLink> ({{ previewItem.entity_type }})</div>
          <div><strong>Credit:</strong> {{ previewItem.credit || 'Khong co' }}</div>
          <div><strong>License:</strong> {{ previewItem.license || 'Khong ro' }}</div>
          <div v-if="previewItem.usage_count > 1"><strong>Dung boi:</strong> {{ previewItem.usage_count }} entities</div>
          <div class="media-preview-url"><strong>URL:</strong> <code>{{ previewItem.url }}</code></div>
        </div>
      </div>
    </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })

const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const FILTERS = [
  { key: 'all', label: 'Tat ca' },
  { key: 'missing_credit', label: 'Thieu credit' },
  { key: 'duplicate', label: 'Trung lap' },
] as const

const items = ref<any[]>([])
const stats = ref<any>(null)
const total = ref(0)
const page = ref(1)
const loading = ref(true)
const filter = ref('all')
const previewItem = ref<any>(null)

const hasMore = computed(() => items.value.length < total.value)

async function fetchMedia(append = false) {
  loading.value = true
  try {
    const res = await $fetch<any>(`/admin-api/media?page=${page.value}&limit=50&filter=${filter.value}`, { headers: authHeaders() })
    items.value = append ? [...items.value, ...(res.items || [])] : (res.items || [])
    total.value = res.total || 0
    stats.value = res.stats || null
  } catch { showToast('Khong the tai thu vien anh', 'error') }
  loading.value = false
}

function setFilter(f: string) {
  if (filter.value === f) return
  filter.value = f
  page.value = 1
  fetchMedia()
}

function loadMore() { page.value++; fetchMedia(true) }

function onImgError(e: Event) {
  const img = e.target as HTMLImageElement
  img.style.opacity = '0.3'
}

onMounted(fetchMedia)
</script>

<style scoped>
.media-subtitle { font-size: .82rem; color: var(--muted); margin-top: 2px; }
.media-tabs { display: flex; gap: var(--space-2); margin-bottom: var(--space-5); }
.media-tab {
  padding: 7px 14px; border-radius: 100px; border: .5px solid var(--line);
  background: var(--bg); color: var(--muted); font-size: .82rem; font-weight: 500; cursor: pointer;
  transition: background .2s, color .2s;
}
.media-tab:hover { border-color: var(--primary); color: var(--ink); }
.media-tab.active { background: var(--primary, #219653); color: #fff; border-color: var(--primary); }

.media-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--space-3);
}
.media-card {
  background: var(--card, var(--bg)); border: 1px solid var(--line); border-radius: 12px;
  overflow: hidden; cursor: pointer; transition: box-shadow .2s, transform .15s;
}
.media-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.media-img-wrap { position: relative; aspect-ratio: 4/3; background: var(--bg-alt); overflow: hidden; }
.media-img-wrap img { width: 100%; height: 100%; object-fit: cover; }
.media-dup-badge {
  position: absolute; top: 6px; right: 6px; padding: 2px 8px; border-radius: 100px;
  background: rgba(255,159,10,.9); color: #fff; font-size: .7rem; font-weight: 700;
}
.media-card-info { padding: 8px 10px; display: flex; flex-direction: column; gap: 2px; }
.media-entity-name { font-weight: 600; font-size: .82rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.media-entity-type { font-size: .72rem; color: var(--muted); text-transform: uppercase; }
.media-credit { font-size: .72rem; color: var(--primary-fg, #219653); }
.media-no-credit { font-size: .72rem; color: #FF9F0A; font-style: italic; }

.media-load-more { margin-top: var(--space-4); }

.media-preview-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-3); }
.media-preview-img { width: 100%; max-height: 60vh; object-fit: contain; border-radius: 8px; background: var(--bg-alt); margin-bottom: var(--space-3); }
.media-preview-meta { font-size: .85rem; line-height: 1.8; }
.media-preview-url { word-break: break-all; }
.media-preview-url code { font-size: .75rem; background: var(--bg-alt); padding: 2px 6px; border-radius: 4px; }

.stat-card.status-warn { border-left: 4px solid #FF9F0A; }
@media (max-width: 640px) { .media-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); } }
@media (prefers-reduced-motion: reduce) { .media-card:hover { transform: none; } }
</style>
