<template>
  <main class="page dd-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Địa điểm' }]" />

    <!-- Hero -->
    <section class="catalog-hero cat-directory" aria-label="Danh bạ địa điểm">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">📍</span>
        <div>
          <h1>Danh bạ địa điểm</h1>
          <p>Tất cả điểm đến, đặc sản, làng nghề, lưu trú và di tích của Vĩnh Long, Bến Tre, Trà Vinh — lọc theo loại và khu vực.</p>
        </div>
      </div>
      <div v-if="total" class="catalog-stats">
        <div class="stat-item">
          <CountUp :value="total" class="stat-num" />
          <span class="stat-label">địa điểm</span>
        </div>
        <div class="stat-item">
          <CountUp :value="CARD_TYPES.length" class="stat-num" />
          <span class="stat-label">loại hình</span>
        </div>
        <div class="stat-item">
          <CountUp :value="Object.keys(AREA_META).length" class="stat-num" />
          <span class="stat-label">khu vực</span>
        </div>
      </div>
    </section>

    <!-- Spotlight -->
    <CatalogSpotlight :items="firstPage" />

    <!-- Region discovery -->
    <section class="block band reveal">
      <div class="section-head">
        <h2>Khám phá theo khu vực</h2>
      </div>
      <div class="quick-picks region-quick-picks">
        <button type="button"
          v-for="(meta, key) in AREA_META" :key="key"
          :class="['quick-pick', 'region-pick', { active: areaFilter === key }]"
          :aria-pressed="areaFilter === key"
          @click="pickArea(key as string)"
        >
          <span class="quick-pick-icon">{{ meta.emoji }}</span>
          <span class="quick-pick-label">{{ meta.name }}</span>
          <span class="quick-pick-blurb">{{ meta.blurb }}</span>
        </button>
      </div>
    </section>

    <!-- Type discovery -->
    <section class="block reveal">
      <div class="section-head">
        <h2>Duyệt theo loại hình</h2>
      </div>
      <div class="scroll-row" role="region" aria-label="Loại hình" tabindex="0">
        <button type="button"
          v-for="t in typeChips" :key="t.value"
          :class="['dd-type-card', { active: typeFilter === t.value }]"
          :aria-pressed="typeFilter === t.value"
          @click="pickType(t.value)"
        >
          <span class="dd-type-icon">{{ t.emoji }}</span>
          <span class="dd-type-label">{{ t.label }}</span>
        </button>
      </div>
    </section>

    <!-- Interstitial -->
    <CatalogInterstitial
      fact="Vĩnh Long, Bến Tre và Trà Vinh có hơn 1.500 điểm đến, đặc sản và dịch vụ — từ cù lao xanh mát đến làng nghề trăm năm, tất cả được xác minh và cập nhật liên tục."
      icon="📊"
      variant="warm"
      :links="[{ to: '/ban-do', label: 'Xem bản đồ' }, { to: '/du-lich', label: 'Du lịch sinh thái' }]"
    />

    <!-- Editorial -->
    <section v-once class="page-article reveal">
      <h2>Khám phá toàn bộ điểm đến miền Tây</h2>
      <p>Danh bạ địa điểm tổng hợp mọi điểm đến, trải nghiệm, sản phẩm, lưu trú và di tích trên toàn vùng Vĩnh Long, Bến Tre và Trà Vinh. Mỗi mục đều có thông tin thực tế: địa chỉ, số điện thoại, giờ mở cửa, giá tham khảo và mùa vụ phù hợp.</p>
      <p>Dữ liệu được thu thập từ nhiều nguồn: trang thông tin chính quyền địa phương, khảo sát thực địa và đóng góp từ cộng đồng. Nếu bạn phát hiện thông tin sai hoặc thiếu, hãy báo cho chúng tôi qua nút "Báo sai dữ liệu" trên mỗi trang chi tiết.</p>
    </section>

    <!-- Tìm + lọc -->
    <div ref="gridAnchor" class="dd-search">
      <svg class="dd-search-ic" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
      <input v-model="qInput" type="search" enterkeyhint="search" class="dd-search-input" placeholder="Tìm địa điểm, đặc sản, làng nghề…" aria-label="Tìm địa điểm" @keyup.enter="applyQuery" />
      <button v-if="qApplied" type="button" class="dd-search-clear" aria-label="Xoá tìm" @click="clearQuery">&times;</button>
      <button type="button" class="btn btn-primary btn-sm" @click="applyQuery">Tìm</button>
    </div>

    <FilterChips
      :filters="typeFilterOptions"
      :model-value="[typeFilter]"
      single-select
      class="dd-filters"
      aria-label="Lọc theo loại"
      @update:model-value="v => setType(v.length ? v[0] : 'all')"
    />

    <FilterChips
      :filters="areaFilterOptions"
      :model-value="[areaFilter]"
      single-select
      class="dd-filters dd-areas"
      aria-label="Lọc theo khu vực"
      @update:model-value="v => setArea(v.length ? v[0] : 'all')"
    />

    <p v-if="!pending" class="dd-count" aria-live="polite">
      <strong>{{ total }}</strong> địa điểm<template v-if="qApplied"> cho “{{ qApplied }}”</template>
    </p>

    <SkeletonGrid v-if="pending && !items.length" :count="9" />

    <EmptyState
      v-else-if="listError && !items.length"
      icon="⚠️" title="Không thể tải danh sách"
      message="Đã có lỗi khi tải dữ liệu. Vui lòng thử lại."
      tone="error"
    >
      <template #actions>
        <button type="button" class="btn btn-primary btn-sm" @click="refresh">Thử lại</button>
      </template>
    </EmptyState>

    <EmptyState
      v-else-if="!items.length"
      icon="🔍" title="Không tìm thấy địa điểm"
      message="Thử bỏ bớt bộ lọc hoặc đổi từ khoá tìm kiếm."
    >
      <template #actions>
        <button type="button" class="btn btn-outline btn-sm" @click="resetAll">Xoá bộ lọc</button>
      </template>
    </EmptyState>

    <template v-else>
      <div class="grid dd-grid" role="list" aria-label="Danh sách địa điểm">
        <EntityCard v-for="e in items" :key="e.id" :entity="e" />
      </div>
      <p v-if="loadMoreError" class="dd-load-error" role="alert">Không tải thêm được. <button type="button" class="btn-text" @click="loadMore">Thử lại</button></p>
      <button v-if="hasMore" type="button" class="btn btn-ghost dd-more" :disabled="loadingMore" @click="loadMore">
        {{ loadingMore ? 'Đang tải…' : `Xem thêm (còn ${total - items.length})` }}
      </button>
    </template>
  </main>
</template>

<script setup lang="ts">
import { TYPE_META, CARD_TYPES, AREA_META } from '~/composables/useConstants'
useReveal()

const route = useRoute()
const router = useRouter()
const PAGE = 24
const gridAnchor = ref<HTMLElement | null>(null)

function scrollToGrid() {
  gridAnchor.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const typeFilter = ref<string>(typeof route.query.type === 'string' ? route.query.type : 'all')
const areaFilter = ref<string>(typeof route.query.area === 'string' ? route.query.area : 'all')
const qApplied = ref<string>(typeof route.query.q === 'string' ? route.query.q : '')
const qInput = ref<string>(qApplied.value)

const typeChips = CARD_TYPES.map(t => ({ value: t, emoji: TYPE_META[t]?.emoji || '📍', label: TYPE_META[t]?.label || t }))
const areaChips = Object.entries(AREA_META).map(([slug, m]) => ({ slug, name: m.name, emoji: m.emoji }))

const typeFilterOptions = computed(() => [
  { key: 'all', label: 'Tất cả' },
  ...typeChips.map(t => ({ key: t.value, label: t.label, icon: t.emoji })),
])
const areaFilterOptions = computed(() => [
  { key: 'all', label: 'Toàn vùng' },
  ...areaChips.map(a => ({ key: a.slug, label: a.name, icon: a.emoji })),
])

function buildUrl(offset: number) {
  const p = new URLSearchParams({ limit: String(PAGE), offset: String(offset) })
  if (typeFilter.value !== 'all') p.set('type', typeFilter.value)
  if (areaFilter.value !== 'all') p.set('area', areaFilter.value)
  if (qApplied.value) p.set('q', qApplied.value)
  return `/api/entities?${p}`
}

// Trang đầu (SSR-friendly cho SEO); load-more nối client-side.
const { data, pending, refresh, error: listError } = await useAsyncData(
  'dia-diem-list',
  () => apiFetch<{ total: number; entities: any[] }>(buildUrl(0)),
  { watch: [] },
)
const firstPage = computed(() => data.value?.entities || [])
const total = computed(() => data.value?.total || 0)

const extra = ref<any[]>([])
const items = computed(() => [...firstPage.value, ...extra.value])
const hasMore = computed(() => items.value.length < total.value)
const loadingMore = ref(false)
const loadMoreError = ref(false)

async function loadMore() {
  if (loadingMore.value) return
  loadingMore.value = true
  loadMoreError.value = false
  try {
    const res = await $fetch<{ entities: any[] }>(buildUrl(items.value.length))
    extra.value.push(...(res.entities || []))
  } catch {
    loadMoreError.value = true
  }
  loadingMore.value = false
}

// Đổi bộ lọc → reset trang nối + đồng bộ URL + refetch trang đầu
function syncUrlAndRefresh() {
  extra.value = []
  const query: Record<string, string> = {}
  if (typeFilter.value !== 'all') query.type = typeFilter.value
  if (areaFilter.value !== 'all') query.area = areaFilter.value
  if (qApplied.value) query.q = qApplied.value
  router.replace({ query })
  refresh()
}
function setType(t: string) { if (typeFilter.value !== t) { typeFilter.value = t; syncUrlAndRefresh() } }
function setArea(a: string) { if (areaFilter.value !== a) { areaFilter.value = a; syncUrlAndRefresh() } }
function pickArea(key: string) { areaFilter.value = areaFilter.value === key ? 'all' : key; syncUrlAndRefresh(); scrollToGrid() }
function pickType(value: string) { typeFilter.value = typeFilter.value === value ? 'all' : value; syncUrlAndRefresh(); scrollToGrid() }
function applyQuery() { qApplied.value = qInput.value.trim(); syncUrlAndRefresh() }
function clearQuery() { qInput.value = ''; qApplied.value = ''; syncUrlAndRefresh() }
function resetAll() { typeFilter.value = 'all'; areaFilter.value = 'all'; qInput.value = ''; qApplied.value = ''; syncUrlAndRefresh() }

const activeTypeLabel = computed(() => typeFilter.value === 'all' ? '' : (TYPE_META[typeFilter.value]?.label || ''))
useSeoMeta({
  title: () => activeTypeLabel.value
    ? `${activeTypeLabel.value} — Danh bạ địa điểm — vinhlong360`
    : 'Danh bạ địa điểm — Vĩnh Long, Bến Tre, Trà Vinh — vinhlong360',
  description: () => 'Khám phá toàn bộ điểm đến, đặc sản OCOP, làng nghề, lưu trú và di tích của Vĩnh Long, Bến Tre, Trà Vinh. Lọc theo loại hình và khu vực.',
  ogTitle: 'Danh bạ địa điểm — vinhlong360',
  ogDescription: 'Điểm đến, đặc sản, làng nghề, lưu trú và di tích miền Tây — tìm theo loại và khu vực.',
})

// JSON-LD: ItemList structured data for search engines
const listJsonLd = computed(() => {
  return itemListJsonLd(
    'Danh bạ địa điểm — vinhlong360',
    'Tất cả điểm đến, đặc sản, làng nghề, lưu trú và di tích của Vĩnh Long, Bến Tre, Trà Vinh.',
    '/dia-diem',
    firstPage.value,
  )
})
useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/dia-diem') }],
  script: [{ type: 'application/ld+json', innerHTML: () => JSON.stringify(listJsonLd.value) }],
})
</script>

<style scoped>
.dd-page { max-width: 1100px; margin: 0 auto; }

.dd-type-card {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  padding: var(--space-4) var(--space-5);
  background: var(--card); border: 1px solid var(--border); border-radius: var(--radius-lg);
  cursor: pointer; transition: border-color .2s, box-shadow .2s;
  min-width: 100px; flex-shrink: 0;
}
.dd-type-card:hover { border-color: var(--primary); box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.dd-type-card:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.dd-type-card.active { border-color: var(--primary); background: rgba(var(--primary-rgb), .06); }
.dd-type-icon { font-size: 1.6rem; }
.dd-type-label { font-size: var(--text-sm); font-weight: var(--weight-semibold); color: var(--ink); white-space: nowrap; }

.dd-search { display: flex; align-items: center; gap: var(--space-2); padding: .35rem .5rem .35rem .75rem; background: var(--card); border: 1px solid var(--border); border-radius: var(--radius-full); margin-bottom: var(--space-3); }
.dd-search:focus-within { border-color: var(--primary); }
.dd-search-ic { color: var(--muted); flex-shrink: 0; }
.dd-search-input { flex: 1; min-width: 0; border: none; background: none; outline: none; color: var(--ink); font-size: var(--text-sm); padding: .4rem 0; }
.dd-search-input::placeholder { color: var(--muted); }
.dd-search-clear { border: none; background: none; color: var(--muted); font-size: 1.3rem; line-height: 1; cursor: pointer; padding: 0 .25rem; }
.dd-search-clear:hover { color: var(--ink); }

.dd-filters { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-bottom: var(--space-3); }
.dd-areas { margin-bottom: var(--space-4); }
.dd-count { font-size: var(--text-sm); color: var(--muted); margin: 0 0 var(--space-4); }
.dd-count strong { color: var(--ink); }

.dd-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-4); }
.dd-more { display: block; margin: var(--space-5) auto 0; }
.dd-load-error { text-align: center; color: var(--danger, #dc2626); font-size: var(--text-sm); margin: var(--space-3) 0; }
.dd-load-error .btn-text { color: var(--primary-fg); font-weight: var(--weight-semibold); background: none; border: none; cursor: pointer; text-decoration: underline; }
</style>
