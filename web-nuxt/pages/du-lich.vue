<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Du lịch' }]" />

    <!-- Hero — "living atlas" thesis: mode dial swaps scene before any scroll -->
    <section class="atlas-hero" :class="`mode-${activeMode.key}`" aria-label="Giới thiệu du lịch">
      <span class="atlas-hero-grain" aria-hidden="true"></span>
      <span class="atlas-hero-motif" aria-hidden="true" v-html="activeMode.motif"></span>
      <div class="atlas-hero-inner">
        <p class="atlas-hero-eyebrow">ĐỒNG BẰNG SÔNG CỬU LONG · VĨNH LONG — BẾN TRE — TRÀ VINH</p>
        <h1 class="atlas-hero-title">
          <span class="atlas-hero-line1">{{ pc('hero_title', 'Ba tỉnh, một nhịp sông.') }}</span>
          <Transition name="mode-fade" mode="out-in">
            <span class="atlas-hero-line2" :key="activeModeKey">{{ activeMode.line }}</span>
          </Transition>
        </h1>
        <Transition name="mode-fade" mode="out-in">
          <p class="atlas-hero-sub" :key="activeModeKey">{{ pc('hero_subtitle', activeMode.sub) }}</p>
        </Transition>
        <div class="mode-dial" role="group" aria-label="Chọn cách khám phá">
          <button type="button"
            v-for="m in heroModes"
            :key="m.key"
            :class="['mode-pill', { active: activeModeKey === m.key }]"
            :aria-pressed="activeModeKey === m.key"
            @click="activeModeKey = m.key"
          >{{ m.emoji }} {{ m.label }}</button>
        </div>
      </div>
      <div v-if="allEntities.length" class="atlas-hero-stats">
        <div class="stat-item" v-for="s in stats" :key="s.label">
          <CountUp :value="s.count" class="stat-num" />
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>
    </section>

    <!-- Bốn cách sống trong ngày — the information-scent layer: one click to a
         pre-filtered grid view, replacing the flat "browse or search only" gap -->
    <section class="block reveal">
      <div class="sediment-head">
        <h2>Bốn cách sống trong ngày</h2>
      </div>
      <div class="life-quad">
        <button v-for="l in lifeRegisters" :key="l.key" type="button" class="life-tile" :class="`life-${l.key}`" @click="typeFilter = l.filterType; scrollToGrid()">
          <span class="life-tile-motif" aria-hidden="true" v-html="l.motif"></span>
          <p class="life-tile-kicker">{{ l.kicker }}</p>
          <p class="life-tile-line">{{ l.line }}</p>
        </button>
      </div>
    </section>

    <!-- Spotlight nổi bật (magazine, dùng-chung) -->
    <CatalogSpotlight :items="allEntities" />

    <!-- Featured -->
    <section v-if="featured.length" class="block band reveal">
      <div class="sediment-head section-head">
        <h2>Nổi bật</h2>
      </div>
      <div class="scroll-row" role="region" aria-label="Trải nghiệm nổi bật" tabindex="0">
        <EntityCard v-for="e in featured" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Category sections — season is the connective tissue: "here's what's
         good to do, and here's why now" -->
    <section v-for="(cat, ci) in categories" :key="cat.type" :class="['block', 'reveal', { band: ci % 2 === 0 }]">
      <div class="sediment-head section-head">
        <h2>{{ cat.emoji }} {{ cat.label }}</h2>
        <button type="button" class="see-all" @click="typeFilter = cat.type; scrollToGrid()">{{ cat.items.length }} kết quả →</button>
      </div>
      <p class="section-desc">{{ cat.desc }}</p>
      <p v-if="cat.seasonNote" class="season-note">{{ cat.seasonNote }}</p>
      <div class="scroll-row" role="region" :aria-label="cat.label" tabindex="0">
        <EntityCard v-for="e in cat.items.slice(0, 8)" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Interstitial -->
    <!-- Editorial (declutter-2 A2: interstitial inline vào mạch bài, hết section rời) -->
    <section v-once class="page-article reveal">
      <div class="sediment-head"><h2>Vì sao chọn Vĩnh Long, Bến Tre, Trà Vinh?</h2></div>
      <div class="editorial-body drop-cap">
        <p>Ba tỉnh nằm ở trung tâm đồng bằng sông Cửu Long, nơi hệ thống sông Tiền và sông Hậu chia thành hàng chục nhánh nhỏ tạo nên mạng lưới kênh rạch chằng chịt. Đây là vùng đất của những cù lao xanh mát quanh năm — An Bình, Bình Hoà Phước, Minh, Ông Hổ — nơi cuộc sống vẫn giữ nhịp chậm rãi của miệt vườn Nam Bộ.</p>
        <p>Khác với các điểm du lịch đông đúc, khu vực này mang đến trải nghiệm gần gũi: chèo xuồng qua rạch dừa nước, đạp xe trên đường làng, tát mương bắt cá cùng nông dân, hoặc đơn giản là ngồi võng nghe chim hót trong vườn trái cây. Du khách không chỉ ngắm cảnh mà thực sự sống cùng nhịp sinh hoạt bản địa. Ở Trà Vinh, nhịp sống ấy còn mang thêm màu sắc Khmer — mái chùa vàng-đỏ giữa vườn dừa, tiếng chuông chùa hoà vào tiếng ghe máy trên sông.</p>
      </div>

      <CatalogInterstitial
        fact="Vĩnh Long, Bến Tre và Trà Vinh có hơn 200 điểm du lịch sinh thái — phần lớn nằm trên các cù lao giữa sông Tiền và sông Hậu."
        icon="🌊"
        variant="warm"
        :links="[{ to: '/ban-do', label: 'Xem bản đồ' }, { to: '/lich-trinh', label: 'Lịch trình gợi ý' }]"
      />

      <div class="sediment-head"><h2>Trải nghiệm theo mùa</h2></div>
      <div class="editorial-body">
        <p>Mỗi thời điểm trong năm mang đến một trải nghiệm khác biệt. <strong>Tháng 8–11</strong> là mùa nước nổi — nước từ thượng nguồn Mekong tràn về, biến đồng ruộng thành biển nước mênh mông, mở ra mùa bông điên điển vàng rực và cá linh non béo ngậy. <strong>Tháng 12–3</strong> là mùa khô, thời tiết mát mẻ lý tưởng cho đạp xe và tham quan làng nghề. <strong>Tháng 4–7</strong> là mùa trái cây rộ — chôm chôm, sầu riêng, măng cụt chín đỏ khắp vườn.</p>
      </div>

      <div class="sediment-head"><h2>Làng nghề trăm năm</h2></div>
      <div class="editorial-body">
        <p>Vùng đất này nổi tiếng với những làng nghề tồn tại hàng trăm năm: gốm đỏ Mang Thít với hàng ngàn lò gạch dọc sông Cổ Chiên, kẹo dừa Bến Tre được làm thủ công từ nước cốt dừa tươi, chiếu lác Định Yên dệt từ cây lác mọc ven kênh, hay bánh tráng Mỹ Lồng nướng trên than hồng. Mỗi sản phẩm kể một câu chuyện về đời sống và tri thức của người miền Tây qua nhiều thế hệ.</p>
      </div>

      <div class="sediment-head"><h2>Di chuyển và lưu ý</h2></div>
      <div class="editorial-body">
        <p>Từ TP.HCM, bạn có thể đến Vĩnh Long trong khoảng 2 giờ bằng xe khách hoặc ô tô riêng theo cao tốc Trung Lương – Mỹ Thuận. Phà Mỹ Thuận nay đã được thay bằng cầu, rút ngắn thời gian di chuyển đáng kể. Trong vùng, xe máy hoặc xe đạp là phương tiện lý tưởng để khám phá các cù lao và đường làng nhỏ hẹp. Nhiều homestay cung cấp xe đạp miễn phí cho khách lưu trú.</p>
      </div>
    </section>

    <!-- Divider -->
    <div class="catalog-divider">
      <span class="catalog-divider-text">Duyệt tất cả</span>
    </div>

    <!-- Full filterable grid -->
    <section ref="gridSection" class="block reveal" aria-label="Duyệt tất cả du lịch">
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
        <FilterChips
          :filters="typeFilterOptions"
          :model-value="[typeFilter]"
          single-select
          aria-label="Lọc theo loại"
          @update:model-value="v => typeFilter = v[0] || 'all'"
        />
        <p class="control-label">Theo tháng</p>
        <FilterChips
          :filters="seasonFilterOptions"
          :model-value="[seasonFilter]"
          single-select
          aria-label="Lọc theo tháng"
          @update:model-value="v => seasonFilter = v[0] || 'all'"
        />
        <div v-if="activeFilterCount > 0" class="filter-status">
          <span class="filter-count">{{ activeFilterCount }} bộ lọc</span>
          <button type="button" class="filter-clear" @click="clearFilters">Xóa tất cả</button>
        </div>
      </div>
      <div class="result-bar">
        <p class="result-meta" aria-live="polite">{{ filtered.length }} kết quả{{ sortBy !== 'relevant' ? ` · ${sortLabels[sortBy]}` : '' }}</p>
        <div class="view-toggle" role="group" aria-label="Chế độ hiển thị">
          <button type="button" :class="['vt-btn', { active: viewMode === 'grid' }]" :aria-pressed="viewMode === 'grid'" @click="viewMode = 'grid'" title="Dạng lưới" aria-label="Dạng lưới">⊞</button>
          <button type="button" :class="['vt-btn', { active: viewMode === 'list' }]" :aria-pressed="viewMode === 'list'" @click="viewMode = 'list'" title="Dạng danh sách" aria-label="Dạng danh sách">☰</button>
        </div>
      </div>
      <EmptyState v-if="fetchError" icon="⚠️" title="Không thể tải dữ liệu" message="Mạng có thể đang chập chờn. Thử tải lại nhé.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="refreshNuxtData('catalog-tourism')">Thử lại</button>
        </template>
      </EmptyState>
      <SkeletonGrid v-else-if="!data" :count="6" />
      <div v-else-if="filtered.length" :class="viewMode === 'list' ? 'list-view' : 'grid'">
        <EntityCard v-for="e in visible" :key="e.id" :entity="e" :season-filter="seasonFilter" />
      </div>
      <EmptyState v-else icon="🌿" title="Không tìm thấy kết quả" message="Thử thay đổi bộ lọc hoặc từ khóa tìm kiếm.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="clearFilters">Xóa bộ lọc</button>
          <NuxtLink to="/theo-mua" class="btn btn-outline">🗓️ Xem theo mùa</NuxtLink>
          <NuxtLink to="/san-pham" class="btn btn-outline">🍊 Đặc sản</NuxtLink>
          <NuxtLink to="/le-hoi" class="btn btn-outline">🎋 Lễ hội</NuxtLink>
        </template>
      </EmptyState>
      <button
        v-if="filtered.length && visibleCount < filtered.length"
        type="button"
        class="btn btn-ghost catalog-more"
        @click="visibleCount += PAGE_SIZE"
      >
        Xem thêm ({{ filtered.length - visibleCount }} còn lại)
      </button>
    </section>

    <!-- Cross-links (declutter-2 A1: 4 hardcode → 3 từ mảng script; bỏ Bản-đồ — đã có
         ở interstitial links + nav) -->
    <section class="block band catalog-cross reveal" aria-label="Khám phá thêm">
      <h2>Khám phá thêm</h2>
      <div class="cross-links">
        <NuxtLink v-for="c in relatedCatalogs" :key="c.to" :to="c.to" class="cross-card">
          <span class="cross-icon" aria-hidden="true">{{ c.icon }}</span>
          <div><strong>{{ c.label }}</strong><p>{{ c.desc }}</p></div>
        </NuxtLink>
      </div>
    </section>
    <!-- declutter-3 T14 (A3c): JourneyBar page-level — trang thuộc luồng lập-kế-hoạch -->
    <ClientOnly><LazyJourneyBar /></ClientOnly>
  </div>
</template>

<script lang="ts">
const MONTH_ABBR = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12']
</script>

<script setup lang="ts">
import type { Entity } from '~/types'
import { TYPE_META, TOURISM_TYPES } from '~/composables/useConstants'
import { inSeason, relevanceScore } from '~/composables/useSeason'
import { generateCategoryIcon } from '~/composables/useCategoryPlaceholder'

useReveal()
const { f: pc } = usePageContent('du_lich')
const TYPES = TOURISM_TYPES as readonly string[]
function typeMeta(type: string) {
  return TYPE_META[type] || { emoji: '📍', label: type, cat: type }
}

const typeChips = TYPES.map(t => ({
  value: t,
  label: `${typeMeta(t).emoji} ${typeMeta(t).label}`,
}))

const q = ref('')
const typeFilter = ref('all')
const seasonFilter = ref('all')

// Hero mode-dial — the signature moment: clicking a mode cross-fades the
// hero's own background/copy (CSS transition on the section's mode-* class),
// no grid interaction, zero extra data cost (concept §2/§10).
const heroModes = [
  { key: 'trai-nghiem', emoji: '🌾', label: 'Trải nghiệm', line: 'Khám phá theo mùa nước, theo mùa trái, theo mùa lễ.', sub: 'Miệt vườn, cù lao, làng nghề trăm năm — khám phá theo mùa nước, mùa trái, mùa lễ hội.', motif: generateCategoryIcon('experience') },
  { key: 'am-thuc', emoji: '🍲', label: 'Ẩm thực', line: 'Một tô bún nước lèo, một mẻ bánh xèo mới đổ.', sub: 'Hương vị sông nước — món ăn nào cũng có một câu chuyện đứng sau nó.', motif: generateCategoryIcon('dish') },
  { key: 'lang-nghe', emoji: '🏺', label: 'Làng nghề', line: 'Tiếng lò gạch Mang Thít, mùi kẹo dừa mới sên.', sub: 'Gốm đỏ, kẹo dừa, chiếu lác, bánh tráng — nghề trăm năm vẫn còn đỏ lửa mỗi sáng.', motif: generateCategoryIcon('craft') },
  { key: 'luu-tru', emoji: '🏡', label: 'Lưu trú', line: 'Một buổi sáng thức dậy giữa vườn trái cây.', sub: 'Homestay nhà vườn, resort ven sông — nơi bạn muốn mở mắt vào buổi sáng ở miền Tây.', motif: generateCategoryIcon('accommodation') },
]
const activeModeKey = ref(heroModes[0]!.key)
const activeMode = computed(() => heroModes.find(m => m.key === activeModeKey.value) || heroModes[0]!)

// declutter-2 A1: cross-links cuối trang — 3 card, script-driven (bỏ Bản-đồ: đã có
// ở interstitial links + nav chính).
const relatedCatalogs = [
  { to: '/san-pham', icon: '🍊', label: 'Đặc sản', desc: 'Sản phẩm theo mùa' },
  { to: '/lich-trinh', icon: '🗓️', label: 'Lịch trình', desc: 'Tuyến đi sẵn' },
  { to: '/luu-tru', icon: '🏡', label: 'Lưu trú', desc: 'Homestay, nhà vườn' },
]

// Bốn cách sống trong ngày — information-scent quad: one click to a
// pre-filtered grid view (concept §3/§6). Maps to real cultural registers
// already present in the taxonomy (sông nước / miệt vườn / làng nghề / tâm linh).
const lifeRegisters = [
  { key: 'song-nuoc', kicker: 'SÔNG NƯỚC', line: 'Chèo xuồng qua rạch dừa nước lúc sáng sớm, khi sương còn chưa tan trên mặt kênh.', filterType: 'experience', motif: generateCategoryIcon('experience') },
  { key: 'miet-vuon', kicker: 'MIỆT VƯỜN', line: 'Ngồi võng nghe chim hót trong vườn trái cây, tự tay hái chôm chôm chín đỏ.', filterType: 'nature', motif: generateCategoryIcon('nature') },
  { key: 'lang-nghe', kicker: 'LÀNG NGHỀ', line: 'Nghe tiếng khung dệt chiếu Định Yên, ngửi mùi kẹo dừa sên trên bếp than.', filterType: 'craft_village', motif: generateCategoryIcon('craft') },
  { key: 'tam-linh', kicker: 'TÂM LINH · DI TÍCH', line: 'Mái chùa Khmer vàng-đỏ giữa vườn dừa, chuông chùa hoà vào tiếng ghe máy trên sông.', filterType: 'attraction', motif: generateCategoryIcon('attraction') },
]

const typeFilterOptions = computed(() => [
  { key: 'all', label: 'Tất cả' },
  ...typeChips.map(t => ({ key: t.value, label: t.label })),
])
const seasonFilterOptions = computed(() => [
  { key: 'all', label: 'Tất cả' },
  ...Array.from({ length: 12 }, (_, i) => ({ key: String(i + 1), label: MONTH_ABBR[i] || String(i + 1) })),
  { key: 'flood', label: 'Mùa nước nổi', icon: '🌊' },
])
const sortBy = ref('relevant')
const sortLabels: Record<string, string> = { popular: 'Phổ biến', newest: 'Mới nhất', name: 'Tên A-Z' }
const viewMode = ref('grid')
const gridSection = ref<HTMLElement | null>(null)

useFilterUrl({ q, type: typeFilter, mua: seasonFilter, sort: sortBy }, { q: '', type: 'all', mua: 'all', sort: 'relevant' })
const { sortByRegion } = useRegionPref()

onMounted(() => {
  const h = (e: KeyboardEvent) => {
    if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes((e.target as Element)?.tagName)) {
      e.preventDefault()
      document.querySelector<HTMLInputElement>('.search-row input[type="search"]')?.focus()
    }
  }
  document.addEventListener('keydown', h)
  onUnmounted(() => document.removeEventListener('keydown', h))
})

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
    .map(t => ({ label: typeMeta(t).label, count: counts[t] || 0 }))
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

// "đang đúng mùa" contextual note per category — data already computed via
// inSeason/relevanceScore (useSeason.ts), no new fetch/logic (concept §3/§11):
// gives a reason to check back ("what's in season now?") instead of a static list.
const currentMonthKey = String(new Date().getMonth() + 1)
function categorySeasonNote(items: Entity[]): string {
  const peak = items.filter(e => relevanceScore(e, currentMonthKey) === 4)
  if (!peak.length) return ''
  const name = peak[0]!.name
  return peak.length > 1
    ? `Đang đúng mùa — ${name} và ${peak.length - 1} nơi khác đang vào lúc đẹp nhất.`
    : `Đang đúng mùa — ${name} đang vào lúc đẹp nhất.`
}

const categories = computed(() => {
  return TYPES
    .map(t => {
      const items = allEntities.value.filter((e: Entity) => e.type === t)
      return {
        type: t,
        emoji: typeMeta(t).emoji,
        label: typeMeta(t).label,
        desc: CATEGORY_DESC[t] || '',
        items,
        seasonNote: categorySeasonNote(items),
      }
    })
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

// Client-side pagination: bound hydration cost on the full filtered grid
// (perf audit P2). First PAGE_SIZE render on the server for SEO/first-paint;
// "Xem thêm" reveals more without a refetch. Resets whenever a filter/search/
// sort input changes so the visible window always starts from the top.
const PAGE_SIZE = 24
const visibleCount = ref(PAGE_SIZE)
const visible = computed(() => filtered.value.slice(0, visibleCount.value))
watch([q, typeFilter, seasonFilter, sortBy], () => { visibleCount.value = PAGE_SIZE })

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
/* .filter-status/.result-bar/.view-toggle/.vt-btn/.list-view moved to
   assets/css/catalog.css (was identical across du-lich/ocop/san-pham). */

/* ══════════════════════════════════════════════════════════════════════
   ATLAS HERO — "living atlas" thesis. Warm clay/amber register (contrast
   with luu-tru's cool dawn-blue). Signature moment: the mode-dial cross-fade
   — clicking a mode swaps headline/sub/motif in one smooth motion before any
   scrolling (concept §2/§10), zero extra data cost (all copy pre-computed).
   ══════════════════════════════════════════════════════════════════════ */
.atlas-hero {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  border-radius: var(--radius-xl);
  padding: clamp(var(--space-8), 4vw + var(--space-6), 4.5rem) var(--space-6) var(--space-6);
  margin-bottom: var(--space-6);
  border: .5px solid var(--line);
  background: linear-gradient(135deg, rgba(var(--primary-rgb), .14) 0%, var(--bg-warm) 70%);
  transition: background 1.1s var(--ease-cinematic);
}
.dark .atlas-hero { background: linear-gradient(135deg, rgba(255,255,255,.04) 0%, rgba(255,255,255,.01) 100%); border-color: var(--line); }
/* each mode gets its own warm tint (still clay/amber family — same publication) */
.atlas-hero.mode-am-thuc { background: linear-gradient(135deg, rgba(var(--accent-rgb), .16) 0%, var(--bg-warm) 70%); }
.atlas-hero.mode-lang-nghe { background: linear-gradient(135deg, rgba(var(--secondary-rgb), .14) 0%, var(--bg-warm) 70%); }
.atlas-hero.mode-luu-tru { background: linear-gradient(135deg, rgba(var(--river-rgb, var(--primary-rgb)), .14) 0%, var(--bg-warm) 70%); }
.dark .atlas-hero.mode-am-thuc,
.dark .atlas-hero.mode-lang-nghe,
.dark .atlas-hero.mode-luu-tru { background: linear-gradient(135deg, rgba(255,255,255,.04) 0%, rgba(255,255,255,.01) 100%); }

.atlas-hero-grain {
  position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-image: var(--grain); background-size: 140px 140px; opacity: .04;
}
.dark .atlas-hero-grain { opacity: .07; }

/* Oversized off-centre category motif — bleeds off the edge, changes per mode */
.atlas-hero-motif {
  position: absolute; right: -4%; bottom: -10%; z-index: 0; pointer-events: none;
  width: clamp(140px, 22vw, 260px); color: var(--primary);
  opacity: .1;
  transition: color .8s var(--ease-cinematic);
}
.atlas-hero-motif :deep(svg) { width: 100%; height: auto; display: block; }
.atlas-hero.mode-am-thuc .atlas-hero-motif { color: var(--accent); }
.atlas-hero.mode-lang-nghe .atlas-hero-motif { color: var(--secondary); }
.atlas-hero.mode-luu-tru .atlas-hero-motif { color: var(--tertiary); }

.atlas-hero-inner { position: relative; z-index: 1; max-width: 64ch; }
.atlas-hero-eyebrow {
  margin: 0 0 var(--space-4);
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  text-transform: uppercase; letter-spacing: var(--tracking-caps);
  color: var(--primary-fg-strong, var(--primary-fg));
}
.atlas-hero-title {
  margin: 0 0 var(--space-4); font-family: var(--font-editorial); font-weight: 600;
  letter-spacing: var(--tracking-tighter); text-wrap: balance;
}
.atlas-hero-line1 {
  display: block; font-size: clamp(2rem, 1.6rem + 2.6vw, var(--text-5xl));
  line-height: var(--leading-tight); color: var(--clay-600, var(--primary));
}
.dark .atlas-hero-line1 { color: var(--clay-400, var(--primary)); }
.atlas-hero-line2 {
  display: block; margin-top: var(--space-2);
  font-family: var(--font-sans); font-weight: var(--weight-medium);
  font-size: clamp(1rem, .9rem + .6vw, var(--text-lg));
  color: var(--muted); letter-spacing: normal;
}
.atlas-hero-sub {
  margin: 0 0 var(--space-5); color: var(--ink);
  font-size: var(--text-base); line-height: var(--leading-relaxed); max-width: 56ch;
}
/* Mode-dial cross-fade — deliberately slower than a UI toggle (600ms,
   cinematic ease) so swapping modes reads as "the scene changes" (§10). */
.mode-fade-enter-active,
.mode-fade-leave-active { transition: opacity .6s var(--ease-cinematic); }
.mode-fade-enter-from,
.mode-fade-leave-to { opacity: 0; }
@media (prefers-reduced-motion: reduce) {
  .mode-fade-enter-active,
  .mode-fade-leave-active { transition: none; }
}

/* Mode dial — the signature interaction */
.mode-dial { display: flex; gap: var(--space-2); flex-wrap: wrap; }
.mode-pill {
  min-height: 44px; padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-full); border: .5px solid var(--line);
  background: var(--card); color: var(--ink);
  font-size: var(--text-sm); font-weight: var(--weight-medium); cursor: pointer;
  transition: background .3s var(--ease-out), color .3s var(--ease-out), border-color .3s var(--ease-out), transform .2s var(--ease-spring-gentle), box-shadow .3s var(--ease-out);
}
.mode-pill:hover { border-color: var(--primary-fg); transform: translateY(-1px); }
.mode-pill:active { transform: scale(.96); transition-duration: .08s; }
.mode-pill:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
.mode-pill.active {
  background: var(--primary); color: var(--text-on-dark, #fff); border-color: var(--primary);
  box-shadow: 0 2px 10px -2px rgba(var(--primary-rgb), .4);
}
.dark .mode-pill { background: var(--card); border-color: var(--line); }

.atlas-hero-stats {
  position: relative; z-index: 1;
  display: flex; gap: var(--space-6); margin-top: var(--space-6); padding-top: var(--space-4);
  border-top: .5px solid var(--line); flex-wrap: wrap;
}

@media (max-width: 640px) {
  .atlas-hero { padding: var(--space-6) var(--space-4); }
  .atlas-hero-line1 { font-size: var(--text-2xl); }
}
@media (prefers-reduced-motion: reduce) {
  .atlas-hero { transition: none; }
  .mode-pill:hover, .mode-pill:active { transform: none; }
  .atlas-hero-motif { transition: none; }
}

/* ══════════════════════════════════════════════════════════════════════
   BỐN CÁCH SỐNG TRONG NGÀY — information-scent quad. Each tile: kicker +
   one sensory sentence, reads as story not category chip (anti-slop §7).
   ══════════════════════════════════════════════════════════════════════ */
.life-quad {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}
.life-tile {
  position: relative;
  overflow: hidden;
  isolation: isolate;
  display: block;
  text-align: left;
  padding: var(--space-6) var(--space-5);
  border-radius: var(--radius-lg);
  background: var(--card); border: .5px solid var(--line);
  cursor: pointer; min-height: 44px;
  transition: transform .35s var(--ease-spring-gentle), box-shadow .3s var(--ease-out-expo), border-color .2s var(--ease-out);
}
.life-tile:hover { transform: translateY(-4px); box-shadow: var(--shadow-md); border-color: var(--border); }
.life-tile:active { transform: scale(.98); transition-duration: .08s; }
.life-tile:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }
/* asymmetric bleed motif per tile — editorial, not icon-in-a-box */
.life-tile-motif {
  position: absolute; right: -8%; bottom: -14%; z-index: 0;
  width: 110px; height: 110px; opacity: .09; color: var(--primary);
  pointer-events: none;
}
.life-tile.life-miet-vuon .life-tile-motif { color: var(--secondary); }
.life-tile.life-lang-nghe .life-tile-motif { color: var(--accent-dark, var(--accent)); }
.life-tile.life-tam-linh .life-tile-motif { color: var(--tertiary); }
.life-tile-motif :deep(svg) { width: 100%; height: 100%; display: block; }
.life-tile-kicker {
  position: relative; z-index: 1; margin: 0 0 var(--space-3);
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase; color: var(--muted);
}
.life-tile-line {
  position: relative; z-index: 1; margin: 0;
  font-family: var(--font-editorial); font-size: var(--text-lg);
  line-height: var(--leading-snug); color: var(--ink);
}
.dark .life-tile { background: var(--card); border-color: var(--line); }
.dark .life-tile:hover { border-color: rgba(255,255,255,.1); }

@media (max-width: 760px) {
  .life-quad { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  .life-tile:hover, .life-tile:active { transform: none; }
}

/* ══════════════════════════════════════════════════════════════════════
   SEASON NOTE — "đang đúng mùa" contextual note per category row: the
   connective tissue that turns a static list into "here's what's good
   to do, and why now" (concept §3/§6, data-driven, no fabrication).
   ══════════════════════════════════════════════════════════════════════ */
.season-note {
  display: inline-flex; align-items: center; gap: var(--space-2);
  margin: 0 0 var(--space-4); padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  background: rgba(var(--accent-rgb), .1);
  color: var(--accent-dark, var(--accent));
  font-size: var(--text-xs); font-weight: var(--weight-semibold);
}
/* Static dot, deliberately NOT breathing — the page can render several
   season-notes at once (one per category row); an ambient pulse on each
   would stack into exactly the "everything breathing" anti-slop tell the
   narrative system forbids (§3 "one ambient element per viewport"). The
   sweep/mode-dial already claims this page's one moving signature. */
.season-note::before {
  content: ""; width: 6px; height: 6px; border-radius: 50%;
  background: currentColor; flex-shrink: 0;
}
.dark .season-note { background: rgba(var(--accent-rgb), .16); color: var(--accent); }
</style>
