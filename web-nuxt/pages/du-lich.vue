<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Du lịch' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-experience" aria-label="Giới thiệu du lịch">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">🌿</span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
      <div v-if="allEntities.length" class="catalog-stats">
        <div class="stat-item" v-for="s in stats" :key="s.label">
          <span class="stat-num">{{ s.count }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>
    </section>

    <!-- Spotlight nổi bật (magazine, dùng-chung) -->
    <CatalogSpotlight :items="allEntities" />

    <!-- Featured -->
    <section v-if="featured.length" class="block reveal">
      <div class="section-head">
        <h2>Nổi bật</h2>
      </div>
      <div class="scroll-row" role="region" aria-label="Trải nghiệm nổi bật" tabindex="0">
        <EntityCard v-for="e in featured" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Category sections -->
    <section v-for="cat in categories" :key="cat.type" class="block reveal">
      <div class="section-head">
        <h2>{{ cat.emoji }} {{ cat.label }}</h2>
        <button type="button" class="see-all" @click="typeFilter = cat.type; scrollToGrid()">{{ cat.items.length }} kết quả →</button>
      </div>
      <p class="section-desc">{{ cat.desc }}</p>
      <div class="scroll-row" role="region" :aria-label="cat.label" tabindex="0">
        <EntityCard v-for="e in cat.items.slice(0, 8)" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Editorial -->
    <section v-once class="page-article reveal">
      <h2>Vì sao chọn Vĩnh Long, Bến Tre, Trà Vinh?</h2>
      <p>Ba tỉnh nằm ở trung tâm đồng bằng sông Cửu Long, nơi hệ thống sông Tiền và sông Hậu chia thành hàng chục nhánh nhỏ tạo nên mạng lưới kênh rạch chằng chịt. Đây là vùng đất của những cù lao xanh mát quanh năm — An Bình, Bình Hoà Phước, Minh, Ông Hổ — nơi cuộc sống vẫn giữ nhịp chậm rãi của miệt vườn Nam Bộ.</p>
      <p>Khác với các điểm du lịch đông đúc, khu vực này mang đến trải nghiệm gần gũi: chèo xuồng qua rạch dừa nước, đạp xe trên đường làng, tát mương bắt cá cùng nông dân, hoặc đơn giản là ngồi võng nghe chim hót trong vườn trái cây. Du khách không chỉ ngắm cảnh mà thực sự sống cùng nhịp sinh hoạt bản địa.</p>

      <h2>Trải nghiệm theo mùa</h2>
      <p>Mỗi thời điểm trong năm mang đến một trải nghiệm khác biệt. <strong>Tháng 8–11</strong> là mùa nước nổi — nước từ thượng nguồn Mekong tràn về, biến đồng ruộng thành biển nước mênh mông, mở ra mùa bông điên điển vàng rực và cá linh non béo ngậy. <strong>Tháng 12–3</strong> là mùa khô, thời tiết mát mẻ lý tưởng cho đạp xe và tham quan làng nghề. <strong>Tháng 4–7</strong> là mùa trái cây rộ — chôm chôm, sầu riêng, măng cụt chín đỏ khắp vườn.</p>

      <h2>Làng nghề trăm năm</h2>
      <p>Vùng đất này nổi tiếng với những làng nghề tồn tại hàng trăm năm: gốm đỏ Mang Thít với hàng ngàn lò gạch dọc sông Cổ Chiên, kẹo dừa Bến Tre được làm thủ công từ nước cốt dừa tươi, chiếu lác Định Yên dệt từ cây lác mọc ven kênh, hay bánh tráng Mỹ Lồng nướng trên than hồng. Mỗi sản phẩm kể một câu chuyện về đời sống và tri thức của người miền Tây qua nhiều thế hệ.</p>

      <h2>Di chuyển và lưu ý</h2>
      <p>Từ TP.HCM, bạn có thể đến Vĩnh Long trong khoảng 2 giờ bằng xe khách hoặc ô tô riêng theo cao tốc Trung Lương – Mỹ Thuận. Phà Mỹ Thuận nay đã được thay bằng cầu, rút ngắn thời gian di chuyển đáng kể. Trong vùng, xe máy hoặc xe đạp là phương tiện lý tưởng để khám phá các cù lao và đường làng nhỏ hẹp. Nhiều homestay cung cấp xe đạp miễn phí cho khách lưu trú.</p>
    </section>

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Duyệt tất cả</span>
    </div>

    <!-- Full filterable grid -->
    <section ref="gridSection" class="block" aria-label="Duyệt tất cả du lịch">
      <div class="controls">
        <div class="search-row">
          <input v-model="q" type="search" enterkeyhint="search" placeholder="Tìm trong du lịch…" aria-label="Tìm kiếm" />
          <select v-model="sortBy" aria-label="Sắp xếp">
            <option value="relevant">Phù hợp nhất</option>
            <option value="popular">Phổ biến</option>
            <option value="newest">Mới nhất</option>
            <option value="name">Tên A-Z</option>
          </select>
        </div>
        <p class="control-label">Loại</p>
        <div class="chip-row" role="group" aria-label="Lọc theo loại">
          <button type="button" :class="['chip', { active: typeFilter === 'all' }]" :aria-pressed="typeFilter === 'all'" @click="typeFilter = 'all'">Tất cả</button>
          <button type="button" v-for="t in typeChips" :key="t.value" :class="['chip', { active: typeFilter === t.value }]" :aria-pressed="typeFilter === t.value" @click="typeFilter = t.value">
            {{ t.label }}
          </button>
        </div>
        <p class="control-label">Theo tháng</p>
        <div class="chip-row" role="group" aria-label="Lọc theo tháng">
          <button type="button" :class="['chip', 'season', { active: seasonFilter === 'all' }]" :aria-pressed="seasonFilter === 'all'" @click="seasonFilter = 'all'">Tất cả</button>
          <button type="button" v-for="m in 12" :key="m" :class="['chip', 'season', { active: seasonFilter === String(m) }]" :aria-pressed="seasonFilter === String(m)" :title="MONTH_NAMES[m - 1]" :aria-label="MONTH_NAMES[m - 1]" @click="seasonFilter = String(m)">
            {{ MONTH_ABBR[m - 1] }}
          </button>
          <button type="button" :class="['chip', 'season', { active: seasonFilter === 'flood' }]" :aria-pressed="seasonFilter === 'flood'" @click="seasonFilter = 'flood'">🌊 Mùa nước nổi</button>
        </div>
        <div v-if="activeFilterCount > 0" class="filter-status">
          <span class="filter-count">{{ activeFilterCount }} bộ lọc</span>
          <button type="button" class="filter-clear" @click="clearFilters">Xóa tất cả</button>
        </div>
      </div>
      <div class="result-bar">
        <p class="result-meta" aria-live="polite">{{ filtered.length }} kết quả{{ sortBy !== 'relevant' ? ` · ${sortLabels[sortBy]}` : '' }}</p>
        <div class="view-toggle" role="group" aria-label="Chế độ hiển thị">
          <button type="button" :class="['vt-btn', { active: viewMode === 'grid' }]" :aria-pressed="viewMode === 'grid'" @click="viewMode = 'grid'" title="Dạng lưới">⊞</button>
          <button type="button" :class="['vt-btn', { active: viewMode === 'list' }]" :aria-pressed="viewMode === 'list'" @click="viewMode = 'list'" title="Dạng danh sách">☰</button>
        </div>
      </div>
      <EmptyState v-if="fetchError" icon="⚠️" title="Không thể tải dữ liệu" message="Mạng có thể đang chập chờn. Thử tải lại nhé.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="refreshNuxtData('catalog-tourism')">Thử lại</button>
        </template>
      </EmptyState>
      <SkeletonGrid v-else-if="!data" :count="6" />
      <div v-else-if="filtered.length" :class="viewMode === 'list' ? 'list-view' : 'grid'">
        <EntityCard v-for="e in filtered" :key="e.id" :entity="e" :season-filter="seasonFilter" />
      </div>
      <EmptyState v-else icon="🌿" title="Không tìm thấy kết quả" message="Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="clearFilters">Xóa bộ lọc</button>
          <NuxtLink to="/theo-mua" class="btn btn-outline">🗓️ Xem theo mùa</NuxtLink>
          <NuxtLink to="/san-pham" class="btn btn-outline">🍊 Đặc sản</NuxtLink>
          <NuxtLink to="/le-hoi" class="btn btn-outline">🎋 Lễ hội</NuxtLink>
        </template>
      </EmptyState>
    </section>

    <!-- Cross-links -->
    <section class="block catalog-cross" aria-label="Khám phá thêm">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink to="/san-pham" class="cross-card">
          <span class="cross-icon">🍊</span>
          <div><strong>Đặc sản</strong><p>Sản phẩm theo mùa</p></div>
        </NuxtLink>
        <NuxtLink to="/lich-trinh" class="cross-card">
          <span class="cross-icon">🗓️</span>
          <div><strong>Lịch trình</strong><p>Tuyến đi sẵn</p></div>
        </NuxtLink>
        <NuxtLink to="/ban-do" class="cross-card" no-prefetch>
          <span class="cross-icon">🗺️</span>
          <div><strong>Bản đồ</strong><p>Xem trên bản đồ</p></div>
        </NuxtLink>
        <NuxtLink to="/luu-tru" class="cross-card">
          <span class="cross-icon">🏡</span>
          <div><strong>Lưu trú</strong><p>Homestay, nhà vườn</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script lang="ts">
const MONTH_NAMES = [
  'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6',
  'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12',
]
const MONTH_ABBR = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12']
</script>

<script setup lang="ts">
import type { Entity } from '~/types'
import { TYPE_META, TOURISM_TYPES } from '~/composables/useConstants'
import { inSeason, relevanceScore } from '~/composables/useSeason'

useReveal()
const { f: pc } = usePageContent('du_lich')
const TYPES = TOURISM_TYPES as readonly string[]

const typeChips = TYPES.map(t => ({
  value: t,
  label: `${TYPE_META[t].emoji} ${TYPE_META[t].label}`,
}))

const q = ref('')
const typeFilter = ref('all')
const seasonFilter = ref('all')
const sortBy = ref('relevant')
const sortLabels: Record<string, string> = { popular: 'Phổ biến', newest: 'Mới nhất', name: 'Tên A-Z' }
const viewMode = ref('grid')
const gridSection = ref<HTMLElement | null>(null)

useFilterUrl({ type: typeFilter, mua: seasonFilter, sort: sortBy }, { type: 'all', mua: 'all', sort: 'relevant' })
const { sortByRegion } = useRegionPref()

const { data, error: fetchError } = await useAsyncData('catalog-tourism', () =>
  apiFetch<{ entities: Entity[]; total: number }>(`/api/entities?type=${TYPES.join(',')}&limit=500`)
)

const allEntities = computed(() => {
  const raw = data.value
  if (!raw) return []
  return raw.entities || []
})

const stats = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of allEntities.value) counts[e.type] = (counts[e.type] || 0) + 1
  return TYPES
    .filter(t => counts[t])
    .map(t => ({ label: TYPE_META[t].label, count: counts[t] }))
})

const featured = computed(() => {
  return allEntities.value
    .filter((e: Entity) => e.images?.length)
    .slice(0, 6)
})

const CATEGORY_DESC: Record<string, string> = {
  experience: 'Chèo xuồng, đạp xe miệt vườn, tát mương bắt cá — trải nghiệm đời sống sông nước Nam Bộ.',
  attraction: 'Chùa cổ, di tích lịch sử, cù lao, vườn trái cây — những điểm đến đáng ghé nhất.',
  craft_village: 'Gốm Mang Thít, kẹo dừa, chiếu lác, bánh tráng — nghề truyền thống hàng trăm năm.',
  dish: 'Bún nước lèo, bánh xèo, hủ tiếu, chả lụi — hương vị chỉ có ở miền Tây.',
  accommodation: 'Homestay nhà vườn, resort sông nước, nhà nghỉ dân dã — nơi lưu lại qua đêm.',
}

const categories = computed(() => {
  return TYPES
    .map(t => ({
      type: t,
      emoji: TYPE_META[t].emoji,
      label: TYPE_META[t].label,
      desc: CATEGORY_DESC[t] || '',
      items: allEntities.value.filter((e: Entity) => e.type === t),
    }))
    .filter(c => c.items.length > 0)
})

function scrollToGrid() {
  nextTick(() => gridSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

const activeFilterCount = computed(() => {
  let n = 0
  if (typeFilter.value !== 'all') n++
  if (seasonFilter.value !== 'all') n++
  if (q.value.trim()) n++
  return n
})

function clearFilters() {
  typeFilter.value = 'all'
  seasonFilter.value = 'all'
  q.value = ''
  sortBy.value = 'relevant'
}

const filtered = computed(() => {
  let list = allEntities.value

  if (typeFilter.value !== 'all') {
    list = list.filter((e: Entity) => e.type === typeFilter.value)
  }

  if (seasonFilter.value !== 'all') {
    list = list.filter((e: Entity) => inSeason(e, seasonFilter.value))
  }

  if (q.value.trim()) {
    const query = q.value.toLowerCase()
    list = list.filter((e: Entity) =>
      (e.name || '').toLowerCase().includes(query) ||
      (e.summary || '').toLowerCase().includes(query)
    )
  }

  list = [...list]
  switch (sortBy.value) {
    case 'popular':
      list.sort((a: Entity, b: Entity) => (b.relationship_total || 0) - (a.relationship_total || 0))
      break
    case 'newest':
      list.sort((a: Entity, b: Entity) => (b.updatedAt || '').localeCompare(a.updatedAt || ''))
      break
    case 'name':
      list.sort((a: Entity, b: Entity) => (a.name || '').localeCompare(b.name || '', 'vi'))
      break
    default:
      if (seasonFilter.value !== 'all') {
        list.sort((a: Entity, b: Entity) => (relevanceScore(b, seasonFilter.value) || 0) - (relevanceScore(a, seasonFilter.value) || 0))
      }
      break
  }
  return sortByRegion(list)
})

useSeoMeta({
  title: () => pc('seo_title'),
  description: () => pc('seo_description'),
  ogTitle: () => pc('og_title'),
  ogDescription: () => pc('og_description'),
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/du-lich') }],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'Du lịch Vĩnh Long',
        description: 'Trải nghiệm bản địa, điểm tham quan, lưu trú, làng nghề và ẩm thực khắp Vĩnh Long.',
        url: 'https://vinhlong360.vn/du-lich',
        numberOfItems: allEntities.value.length,
      }),
    },
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
          { '@type': 'ListItem', position: 2, name: 'Du lịch' },
        ],
      }),
    },
  ],
})

useHead(() => ({
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify(itemListJsonLd(
      'Du lịch Vĩnh Long, Bến Tre, Trà Vinh',
      'Trải nghiệm bản địa, điểm tham quan, lưu trú, làng nghề và ẩm thực miền Tây.',
      '/du-lich',
      filtered.value,
    )),
  }],
}))
</script>

<style scoped>
.controls {
  position: sticky;
  top: 0;
  z-index: 10;
}
.filter-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: .5px solid var(--line);
}
.filter-count {
  font-size: var(--text-xs);
  color: var(--muted);
  font-weight: var(--weight-medium);
}
.filter-clear {
  font-size: var(--text-xs);
  color: var(--primary-fg);
  background: none;
  border: none;
  cursor: pointer;
  font-weight: var(--weight-semibold);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  transition: background .2s;
}
.filter-clear:hover {
  background: rgba(var(--primary-rgb), .08);
}
.result-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}
.view-toggle {
  display: flex;
  gap: 2px;
  background: var(--surface);
  border-radius: var(--radius-sm);
  padding: 2px;
}
.vt-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-xs);
  font-size: var(--text-sm);
  color: var(--muted);
  transition: background .15s, color .15s;
  line-height: 1;
}
.vt-btn.active {
  background: var(--card);
  color: var(--fg);
  box-shadow: var(--shadow-xs);
}
.list-view {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.list-view :deep(.card) {
  flex-direction: row;
  align-items: stretch;
}
.list-view :deep(.cover) {
  width: 180px;
  min-height: 120px;
  flex-shrink: 0;
  aspect-ratio: auto;
}
.list-view :deep(.card-b) {
  flex: 1;
  min-width: 0;
}
.list-view :deep(.card-b h3) {
  -webkit-line-clamp: 1;
}
.list-view :deep(.summary) {
  -webkit-line-clamp: 2;
}
@media (max-width: 600px) {
  .list-view :deep(.card) { flex-direction: column; }
  .list-view :deep(.cover) { width: 100%; min-height: 140px; aspect-ratio: 16/9; }
}
</style>
