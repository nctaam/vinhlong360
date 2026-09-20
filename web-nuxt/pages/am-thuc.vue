<template>
  <section class="page" data-color-system="tri-region-v1" data-page-recipe="culinary" data-material-accent="amber">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Ẩm thực' }]" :json-ld="true" />

    <!-- Hero — Mekong Culinary Editorial -->
    <section class="wake-hero cat-dish" aria-label="Ẩm thực Mekong Vĩnh Long">
      <div class="wake-hero-inner">
        <p class="wake-hero-eyebrow">TỈNH VĨNH LONG · ẨM THỰC BẢN ĐỊA &amp; ĐẶC SẢN MIỆT VƯỜN</p>
        <h1 class="wake-hero-title">Ẩm thực sông nước Cửu Long</h1>
        <p class="wake-hero-sub">Cẩm nang 120 món ngon và địa chỉ ẩm thực chọn lọc — từ bún nước lèo, bánh xèo vịt xiêm đến lẩu cá linh bông điên điển mùa nước nổi.</p>
      </div>
      <div v-if="allEntities.length" class="wake-hero-stats">
        <div class="stat-item">
          <CountUp :value="allEntities.length" class="stat-num" />
          <span class="stat-label">món ẩm thực</span>
        </div>
        <div v-for="a in areaCounts" :key="a.key" class="stat-item">
          <CountUp :value="a.count" class="stat-num" />
          <span class="stat-label">{{ a.name }}</span>
        </div>
      </div>
    </section>

    <!-- AEO Plaque — Culinary Guidance -->
    <CatalogAeoPlaque
      title="Chỉ dẫn Ẩm thực Bản địa Vĩnh Long — Hương vị sông Cửu Long"
      kicker="Góc nhìn bản địa · Giải đáp nhanh AEO"
      accent="amber"
      icon="cup"
      :entries="culinaryAeoEntries"
      cta-to="/ocop"
      cta-label="Khám phá sản vật OCOP ẩm thực"
    />

    <!-- Signature Dishes Triad -->
    <section class="block band reveal">
      <div class="sediment-head">
        <h2>Ba phong vị ẩm thực sông nước</h2>
      </div>
      <p class="section-desc">Hương vị hình thành từ sự hòa quyện giữa văn hóa ẩm thực ba dân tộc Kinh - Khmer - Hoa và chu kỳ con nước Cửu Long.</p>
      <div class="cuisine-triad">
        <article class="cuisine-tile">
          <div class="cuisine-tile-icon" aria-hidden="true"><IconLine name="bowl" /></div>
          <p class="cuisine-tile-kicker">Món nước đậm vị</p>
          <h3 class="cuisine-tile-title">Bún nước lèo & Bún suông</h3>
          <p class="cuisine-tile-body">Hương vị giao thoa Kinh - Khmer độc đáo: nước lèo nấu từ mắm bò hóc cùng củ ngải bún thanh mát, ăn kèm chả cá thát lát, heo quay da giòn và rau chuối bào non.</p>
          <p class="cuisine-tile-tag">Đặc sản Trà Vinh & Vĩnh Long</p>
        </article>
        <article class="cuisine-tile">
          <div class="cuisine-tile-icon" aria-hidden="true"><IconLine name="sun" /></div>
          <p class="cuisine-tile-kicker">Mùa nước nổi</p>
          <h3 class="cuisine-tile-title">Canh chua cá linh & Bông điên điển</h3>
          <p class="cuisine-tile-body">Tháng 8 đến tháng 11 âm lịch, cá linh non đầu mùa xương mềm béo ngậy nấu chua me dốt cùng bông điên điển vàng rực ven sông, gợi trọn hồn cốt đồng bằng.</p>
          <p class="cuisine-tile-tag">Theo con nước tháng 8 - 11</p>
        </article>
        <article class="cuisine-tile">
          <div class="cuisine-tile-icon" aria-hidden="true"><IconLine name="gift" /></div>
          <p class="cuisine-tile-kicker">Miệt vườn cù lao</p>
          <h3 class="cuisine-tile-title">Bánh xèo vịt xiêm củ hũ dừa</h3>
          <p class="cuisine-tile-body">Vỏ bánh giòn tan đúc từ bột gạo ngâm cối đá hòa nước cốt dừa béo bùi, nhân vịt xiêm bằm xào củ hũ dừa ngọt thanh, cuộn cùng hơn 20 loại rau rừng vườn nhà.</p>
          <p class="cuisine-tile-tag">Trải nghiệm nhà vườn Cù lao</p>
        </article>
      </div>
    </section>

    <!-- Editorial Prose -->
    <section v-once class="page-article reveal">
      <div class="sediment-head"><h2>Hồn cốt ẩm thực miệt vườn sông nước</h2></div>
      <div class="editorial-body drop-cap">
        <p>Ẩm thực châu thổ Cửu Long tại vùng đất Vĩnh Long hợp nhất (3 vùng trước 7-2025) là khúc biến tấu hài hòa giữa sản vật thiên nhiên hào sảng và bàn tay cần lao của cư dân ba dân tộc Kinh, Khmer, Hoa. Mỗi món ăn gắn liền với mùa vụ con nước: mùa nước nổi rộn ràng với mớ cá linh non, bông điên điển nở vàng bờ kinh; mùa gặt thơm lừng cá lóc nướng trui rơm rạ; và mùa nắng êm đềm với những chảo bánh xèo vịt xiêm củ hũ dừa giòn tan bên rặng dừa xanh mát.</p>
      </div>
      <CatalogInterstitial
        fact="Ẩm thực Mekong Vĩnh Long hội tụ hơn 300 món ngon và đặc sản truyền thống, kết hợp gia vị tự nhiên độc bản như ngải bún, mắm đồng và củ hũ dừa, được ban biên tập tổng hợp và cập nhật liên tục."
        icon-name="award"
        variant="warm"
        :links="[{ to: '/san-pham', label: 'Xem sản vật OCOP' }, { to: '/theo-mua', label: 'Ẩm thực theo mùa' }]"
      />
    </section>

    <!-- Catalog Results Block -->
    <section ref="gridSection" class="catalog-results block reveal" data-catalog-section="results" aria-label="Duyệt danh bạ ẩm thực">
      <div class="controls">
        <!-- Search row -->
        <div class="search-row">
          <IconLine name="search" class="search-icon" aria-hidden="true" />
          <input
            v-model="q"
            type="search"
            class="search-input"
            placeholder="Tìm bún nước lèo, bánh xèo, cá linh, đặc sản..."
            aria-label="Tìm kiếm món ăn"
          />
          <button
            v-if="q"
            type="button"
            class="btn-clear tactile-pill"
            aria-label="Xóa từ khóa"
            @click="q = ''"
          >
            <IconLine name="x" aria-hidden="true" />
          </button>
        </div>

        <!-- Area filter pills (tactile pills >= 44x44px) -->
        <div class="chip-row wrap-mobile" role="group" aria-label="Lọc theo vùng">
          <button
            type="button"
            :class="['chip tactile-pill', { active: areaFilter === 'all' }]"
            :aria-pressed="areaFilter === 'all'"
            @click="areaFilter = 'all'"
          >
            Tất cả vùng
          </button>
          <button
            v-for="(meta, key) in AREA_META"
            :key="key"
            type="button"
            :class="['chip tactile-pill', { active: areaFilter === key }]"
            :aria-pressed="areaFilter === key"
            @click="areaFilter = key as string"
          >
            <IconLine :name="meta.icon || 'pin'" /> {{ meta.name }}
          </button>
        </div>

        <!-- Type filter pills (tactile pills >= 44x44px) -->
        <div class="chip-row wrap-mobile" role="group" aria-label="Lọc theo phân loại">
          <button
            type="button"
            :class="['chip tactile-pill', { active: typeFilter === 'all' }]"
            :aria-pressed="typeFilter === 'all'"
            @click="typeFilter = 'all'"
          >
            Tất cả món
          </button>
          <button
            type="button"
            :class="['chip tactile-pill', { active: typeFilter === 'dish' }]"
            :aria-pressed="typeFilter === 'dish'"
            @click="typeFilter = 'dish'"
          >
            <IconLine name="bowl" /> Món ăn bản địa
          </button>
          <button
            type="button"
            :class="['chip tactile-pill', { active: typeFilter === 'product' }]"
            :aria-pressed="typeFilter === 'product'"
            @click="typeFilter = 'product'"
          >
            <IconLine name="gift" /> Đặc sản làm quà
          </button>
        </div>

        <!-- Active filter ledger -->
        <div v-if="activeFilterCount > 0" class="active-filter-ledger" role="region" aria-label="Bộ lọc đang áp dụng">
          <span class="afl-heading">Đang lọc:</span>
          <div class="afl-chips">
            <span v-if="q.trim()" class="afl-chip">
              <span class="afl-text">Tìm: “{{ q.trim() }}”</span>
              <button type="button" class="afl-remove" aria-label="Xóa từ khóa" @click="q = ''"><IconLine name="x" aria-hidden="true" /></button>
            </span>
            <span v-if="areaFilter !== 'all'" class="afl-chip">
              <span class="afl-text">{{ AREA_META[areaFilter]?.name || areaFilter }}</span>
              <button type="button" class="afl-remove" aria-label="Bỏ lọc vùng" @click="areaFilter = 'all'"><IconLine name="x" aria-hidden="true" /></button>
            </span>
            <span v-if="typeFilter !== 'all'" class="afl-chip">
              <span class="afl-text">{{ typeFilter === 'dish' ? 'Món ăn bản địa' : 'Đặc sản làm quà' }}</span>
              <button type="button" class="afl-remove" aria-label="Bỏ lọc loại" @click="typeFilter = 'all'"><IconLine name="x" aria-hidden="true" /></button>
            </span>
            <button type="button" class="afl-clear-all" @click="clearFilters">Xóa tất cả</button>
          </div>
        </div>
      </div>

      <!-- Result meta and view mode toggle -->
      <div class="result-bar">
        <p class="result-meta" aria-live="polite">{{ filtered.length }} món ngon & đặc sản</p>
        <div class="view-toggle" role="group" aria-label="Chế độ hiển thị">
          <button type="button" :class="['vt-btn tactile-pill', { active: viewMode === 'grid' }]" :aria-pressed="viewMode === 'grid'" @click="viewMode = 'grid'" title="Dạng lưới" aria-label="Dạng lưới"><IconLine name="layout-dashboard" aria-hidden="true" /></button>
          <button type="button" :class="['vt-btn tactile-pill', { active: viewMode === 'list' }]" :aria-pressed="viewMode === 'list'" @click="viewMode = 'list'" title="Dạng danh sách" aria-label="Dạng danh sách"><IconLine name="list" aria-hidden="true" /></button>
        </div>
      </div>

      <!-- Result States -->
      <EmptyState v-if="fetchError" tone="error" icon-name="alert-triangle" title="Không thể tải dữ liệu ẩm thực" message="Kết nối mạng đang chập chờn. Bạn thử tải lại một lần nữa nhé.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="refreshNuxtData('catalog-cuisine')">Thử lại</button>
        </template>
      </EmptyState>
      <SkeletonGrid v-else-if="!data" :count="6" />
      <div
        v-else-if="filtered.length"
        :class="viewMode === 'list' ? 'list-view' : 'grid grid--asymmetric cuisine-grid'"
        role="list"
        aria-label="Danh sách món ẩm thực"
      >
        <template v-for="(e, i) in visible" :key="e.id">
          <div v-if="i > 0 && i % 9 === 0" class="cuisine-divider reveal" role="presentation" aria-hidden="true">
            <span class="cuisine-divider-label">Hương vị tiếp nối · {{ dividerFact(i) }}</span>
          </div>
          <EntityCard :entity="e" />
        </template>
      </div>
      <EmptyState v-else icon-name="search" title="Không tìm thấy món ăn phù hợp" message="Thử thay đổi từ khóa hoặc bộ lọc vùng xem sao nhé.">
        <template #actions>
          <button type="button" class="btn btn-outline" @click="clearFilters"><IconLine name="x" aria-hidden="true" /> Xóa bộ lọc</button>
          <NuxtLink to="/san-pham" class="btn btn-outline"><IconLine name="gift" /> Đặc sản & OCOP</NuxtLink>
          <NuxtLink to="/theo-mua" class="btn btn-outline"><IconLine name="calendar" /> Xem theo mùa</NuxtLink>
        </template>
      </EmptyState>

      <!-- Load more button -->
      <button
        v-if="filtered.length && visibleCount < filtered.length"
        type="button"
        class="btn btn-ghost catalog-more tactile-pill"
        @click="visibleCount += PAGE_SIZE"
      >
        {{ loadMoreLabel }}
        <IconLine name="arrow-down" class="cuisine-more-icon" />
      </button>
    </section>

    <!-- Cross-links -->
    <CatalogCrossLinks
      title="Khám phá tiếp theo"
      subtitle="Trải nghiệm trọn vẹn văn hóa sông nước"
      :links="cuisineCrossLinks"
    />
  </section>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { AREA_META } from '~/composables/useConstants'

useReveal()

useHead({
  title: 'Ẩm thực Vĩnh Long — Tinh hoa món ngon sông nước Cửu Long',
})

useSeoMeta({
  title: 'Ẩm thực Vĩnh Long — Tinh hoa món ngon sông nước Cửu Long',
  description: 'Khám phá ẩm thực bản địa Vĩnh Long: Bún nước lèo, bánh xèo vịt xiêm, canh chua cá linh bông điên điển, cá lóc nướng trui và đặc sản OCOP.',
})

const culinaryAeoEntries = [
  {
    heading: 'Bún nước lèo Trà Vinh',
    text: 'Giao thoa văn hóa Kinh - Khmer - Hoa với nước dùng nấu từ mắm bò hóc thanh ngọt, củ ngải bún dậy mùi, cá lóc đồng ngọt thịt ăn kèm thịt heo quay da giòn rụm và rau muống bào, bắp chuối thái mỏng.',
  },
  {
    heading: 'Bánh xèo vịt xiêm miệt vườn cù lao',
    text: 'Vỏ bánh giòn xốp tráng từ bột gạo lúa mùa ngâm xay cối đá hòa nước cốt dừa, nhân thịt vịt xiêm bằm nhuyễn xào củ hũ dừa ngọt thanh bùi ngậy, cuộn rổ rau rừng hơn 20 loại hái quanh vườn nhà.',
  },
  {
    heading: 'Canh chua cá linh & Lẩu mắm bông điên điển',
    text: 'Đặc sản trứ danh mùa nước nổi (tháng 8 đến tháng 11 âm lịch). Cá linh non xương mềm béo ngậy nấu chua me dốt cùng bông súng, bông điên điển vàng rực ven sông.',
  },
  {
    heading: 'Khoai lang tím Bình Tân & Bánh tét Trà Cuôn',
    text: 'Củ khoai lang tím dẻo bùi chấm mắm sống cá lóc đồng đậm đà, cùng đòn bánh tét Trà Cuôn nếp dẻo thơm hạt ngọc trời quyện nhân đậu xanh, thịt mỡ và trứng muối béo ngậy nức tiếng gần xa.',
  },
]

const cuisineCrossLinks = computed(() => [
  {
    to: '/san-pham',
    label: 'Đặc sản & OCOP',
    desc: 'Sản vật nông nghiệp, bánh mứt làm quà',
    icon: 'gift',
  },
  {
    to: '/du-lich',
    label: 'Du lịch miệt vườn',
    desc: 'Khám phá cù lao xanh và vườn cây ăn trái',
    icon: 'leaf',
  },
  {
    to: '/theo-mua',
    label: 'Mùa nước nổi',
    desc: 'Đặc sản và con nước mùa lũ sông Cửu Long',
    icon: 'calendar',
  },
  {
    to: '/ban-do',
    label: 'Bản đồ ẩm thực',
    desc: 'Tìm quán ngon và địa điểm ẩm thực gần bạn',
    icon: 'compass',
    noPrefetch: true,
  },
])

const areaFilter = ref('all')
const typeFilter = ref('all')
const q = ref('')
const viewMode = ref<'grid' | 'list'>('grid')

const activeFilterCount = computed(() => (areaFilter.value !== 'all' ? 1 : 0) + (typeFilter.value !== 'all' ? 1 : 0) + (q.value.trim() ? 1 : 0))

function clearFilters() {
  areaFilter.value = 'all'
  typeFilter.value = 'all'
  q.value = ''
}

const { data, error: fetchError } = await useAsyncData('catalog-cuisine', () =>
  apiFetch<{ entities: Entity[]; total?: number }>('/api/entities?type=dish,product&limit=500')
)

const allEntities = computed<Entity[]>(() => {
  if (Array.isArray(data.value)) return data.value
  return data.value?.entities || []
})

const areaCounts = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of allEntities.value) {
    const area = getEntityArea(e)
    if (area) counts[area] = (counts[area] || 0) + 1
  }
  return Object.entries(AREA_META).map(([key, meta]) => ({
    key,
    name: meta.name,
    count: counts[key] || 0,
  }))
})

const filtered = computed(() => {
  let list = allEntities.value
  if (typeFilter.value !== 'all') {
    list = list.filter((e: Entity) => e.type === typeFilter.value)
  }
  if (areaFilter.value !== 'all') {
    list = list.filter((e: Entity) => getEntityArea(e) === areaFilter.value)
  }
  if (q.value.trim()) {
    const keyword = q.value.trim().toLowerCase()
    list = list.filter((e: Entity) => {
      const name = (e.name || '').toLowerCase()
      const summary = (e.summary || '').toLowerCase()
      const description = (e.description || '').toLowerCase()
      return name.includes(keyword) || summary.includes(keyword) || description.includes(keyword)
    })
  }
  return list
})

const PAGE_SIZE = 24
const visibleCount = ref(PAGE_SIZE)
const visible = computed(() => filtered.value.slice(0, visibleCount.value))

const loadMoreLabel = computed(() => {
  const remaining = filtered.value.length - visibleCount.value
  if (remaining <= 0) return ''
  return `Xem thêm (${remaining} món còn lại)`
})

function dividerFact(index: number): string {
  const seen = visible.value.slice(0, index)
  const areasSeen = new Set(seen.map((e: any) => e.placeName || e.place_name).filter(Boolean))
  const pool = Array.from(areasSeen)
  const nth = Math.floor(index / 9)
  if (pool.length) return pool[nth % pool.length] as string
  return `${index} món đã lật qua`
}

const gridSection = ref<HTMLElement | null>(null)
watch([areaFilter, typeFilter, q], () => {
  visibleCount.value = PAGE_SIZE
})
</script>

<style scoped>
.wake-hero {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-surface);
  padding: clamp(var(--space-8), 4vw + var(--space-6), 3.5rem) var(--space-6) var(--space-6);
  margin-bottom: var(--space-6);
  border: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
}

.wake-hero-inner {
  position: relative;
  z-index: 1;
  max-width: 65ch;
}

.wake-hero-eyebrow {
  margin: 0 0 var(--space-3);
  font-family: var(--font-sans);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--color-brand);
}

.wake-hero-title {
  margin: 0 0 var(--space-3);
  font-family: var(--font-editorial-display);
  font-size: clamp(var(--text-3xl), 4.5vw, var(--text-5xl));
  font-weight: var(--weight-semibold);
  line-height: 1.15;
  letter-spacing: var(--tracking-tight);
  color: var(--color-text);
  text-wrap: balance;
}

.wake-hero-sub {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  max-width: 60ch;
}

.wake-hero-stats {
  position: relative;
  z-index: 1;
  display: flex;
  gap: var(--space-6);
  margin-top: var(--space-6);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
  flex-wrap: wrap;
}

.wake-hero-stats .stat-item {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-control);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
}

.wake-hero-stats .stat-num {
  font-family: var(--font-mono);
  font-weight: var(--weight-bold);
  color: var(--color-text);
  margin-right: var(--space-1);
}

.wake-hero-stats .stat-label {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.tactile-pill {
  min-height: 44px;
  min-width: 44px;
}

.cuisine-triad {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-4);
  margin-top: var(--space-4);
}

.cuisine-tile {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-surface);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  transition: transform .2s var(--ease-out), box-shadow .2s var(--ease-out);
}

.cuisine-tile:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
  border-color: var(--color-border-strong);
}

.cuisine-tile-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-full);
  background: var(--color-action-surface);
  color: var(--color-action);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-1);
}

.cuisine-tile-kicker {
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--color-action);
  margin: 0;
}

.cuisine-tile-title {
  font-family: var(--font-editorial);
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.cuisine-tile-body {
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text-muted);
  margin: 0;
  flex: 1;
}

.cuisine-tile-tag {
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  color: var(--muted);
  margin-top: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px dashed var(--color-border);
}

.cuisine-divider {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin: var(--space-3) 0;
  padding: var(--space-2) 0;
}

.cuisine-divider::before,
.cuisine-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

.cuisine-divider-label {
  font-family: var(--font-editorial);
  font-style: italic;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  white-space: nowrap;
  padding: 0 var(--space-2);
}

.cuisine-more-icon {
  display: inline-block;
  margin-left: var(--space-1);
  transition: transform var(--duration-fast) var(--ease-out-expo);
}

.catalog-more:hover .cuisine-more-icon {
  transform: translateY(2px);
}
</style>
