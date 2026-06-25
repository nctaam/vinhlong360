<template>
  <div class="page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: areaMeta?.name || 'Khu vực' }]" />

    <!-- Hero -->
    <section v-if="areaMeta" class="catalog-hero area-hero" :class="'cat-area-' + areaKey" :style="areaTint">
      <span class="area-hero-bloom" aria-hidden="true"></span>
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true">{{ areaMeta.emoji }}</span>
        <div>
          <h1>{{ areaMeta.name }}</h1>
          <p>{{ areaMeta.blurb }}</p>
        </div>
      </div>
      <div v-if="entities.length" class="catalog-stats area-stats">
        <div class="stat-item">
          <span class="stat-num">{{ entities.length }}</span>
          <span class="stat-label">địa điểm</span>
        </div>
        <div v-for="s in typeStats" :key="s.type" class="stat-item">
          <span class="stat-num">{{ s.count }}</span>
          <span class="stat-label">{{ s.label }}</span>
        </div>
      </div>
    </section>

    <!-- Editorial -->
    <section v-if="areaEditorial" class="page-article reveal">
      <h2>{{ areaEditorial.title }}</h2>
      <p v-for="(p, i) in areaEditorial.paragraphs" :key="i">{{ p }}</p>
    </section>

    <!-- Error state -->
    <EmptyState v-if="fetchError && !entities.length" tone="error" icon="⚠️" title="Không thể tải dữ liệu" message="Lỗi kết nối. Vui lòng thử lại.">
      <template #actions>
        <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData(`area-${areaKey}`)">Thử lại</button>
      </template>
    </EmptyState>

    <!-- Loading skeleton (first paint, before data) -->
    <ClientOnly>
      <div v-if="!data && !fetchError" class="block">
        <div class="section-head"><h2 class="sk-heading">Đang tải…</h2></div>
        <SkeletonGrid :count="8" />
      </div>
    </ClientOnly>

    <!-- Featured -->
    <section v-if="featured.length" class="block reveal">
      <div class="section-head">
        <h2>Nổi bật {{ areaMeta?.name }}</h2>
      </div>
      <p class="section-desc">Những địa điểm nổi bật nhất vùng — chọn lọc theo hình ảnh và mức độ quan tâm.</p>
      <div class="scroll-row honor-roll" role="region" :aria-label="'Nổi bật ' + areaMeta?.name">
        <EntityCard v-for="e in featured" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Type sections -->
    <section v-for="cat in typeSections" :key="cat.type" class="block reveal area-type-block">
      <div class="section-head">
        <h2>{{ cat.emoji }} {{ cat.label }}</h2>
        <button
          v-if="cat.items.length > 8"
          type="button"
          class="see-all-toggle"
          :aria-expanded="expanded[cat.type] ? 'true' : 'false'"
          @click="toggleExpand(cat.type)"
        >
          {{ expanded[cat.type] ? 'Thu gọn' : `Xem tất cả (${cat.items.length})` }}
        </button>
        <span v-else class="see-all-count">{{ cat.items.length }} mục</span>
      </div>
      <div class="scroll-row" role="region" :aria-label="cat.label">
        <EntityCard v-for="e in (expanded[cat.type] ? cat.items : cat.items.slice(0, 8))" :key="e.id" :entity="e" />
      </div>
    </section>

    <!-- Wards -->
    <section v-if="wards.length" class="block reveal">
      <div class="section-head">
        <h2>Xã / phường ({{ wards.length }})</h2>
      </div>
      <p class="section-desc">Mỗi xã/phường có trang riêng: du lịch · lưu trú · đặc sản · danh bạ hành chính.</p>
      <div class="chip-row wrap-mobile area-wards">
        <NuxtLink v-for="w in wards" :key="w.id" :to="`/xa-phuong/${w.id}`" class="chip">{{ w.name }}</NuxtLink>
      </div>
    </section>

    <!-- Divider -->
    <div v-if="entities.length" class="catalog-divider">
      <span class="catalog-divider-text">Tất cả {{ entities.length }} mục</span>
    </div>

    <!-- Full grid -->
    <section v-if="entities.length" class="block reveal">
      <div class="grid">
        <EntityCard v-for="e in entities" :key="e.id" :entity="e" />
      </div>
    </section>
    <EmptyState v-else-if="data && !fetchError" icon="📍" title="Chưa có dữ liệu" message="Chưa có dữ liệu cho khu vực này. Dữ liệu đang được cập nhật.">
      <template #actions>
        <NuxtLink to="/du-lich" class="btn btn-outline">Khám phá du lịch</NuxtLink>
        <NuxtLink to="/" class="btn btn-outline">Về trang chủ</NuxtLink>
      </template>
    </EmptyState>

    <!-- Cross-links -->
    <section v-if="areaMeta" class="block catalog-cross">
      <h2>Khám phá thêm {{ areaMeta.name }}</h2>
      <div class="cross-links">
        <NuxtLink :to="`/du-lich?type=experience&mua=all`" class="cross-card">
          <span class="cross-icon">🌾</span>
          <div><strong>Trải nghiệm</strong><p>Miệt vườn sông nước</p></div>
        </NuxtLink>
        <NuxtLink to="/san-pham" class="cross-card">
          <span class="cross-icon">🍊</span>
          <div><strong>Sản phẩm</strong><p>Đặc sản địa phương</p></div>
        </NuxtLink>
        <NuxtLink to="/luu-tru" class="cross-card">
          <span class="cross-icon">🏡</span>
          <div><strong>Lưu trú</strong><p>Homestay, nhà vườn</p></div>
        </NuxtLink>
        <NuxtLink :to="`/danh-ba?area=${areaKey}`" class="cross-card">
          <span class="cross-icon">🏛️</span>
          <div><strong>Danh bạ</strong><p>Hành chính xã/phường</p></div>
        </NuxtLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import type { Place, Entity} from '~/types'
import { AREA_META, CARD_TYPES, TYPE_META } from '~/composables/useConstants'

useReveal()
const route = useRoute()
const areaKey = route.params.area as string
const areaMeta = AREA_META[areaKey]
if (!areaMeta) throw createError({ statusCode: 404, statusMessage: 'Không tìm thấy khu vực', fatal: true })

// Per-region accent binding — feeds the scoped hero bloom + stat tint so each
// area "owns" its colour. Falls back to brand primary for unknown areas.
const AREA_RGB: Record<string, string> = {
  'vinh-long': 'var(--primary-rgb)',
  'ben-tre': 'var(--secondary-rgb)',
  'tra-vinh': 'var(--river-rgb)',
}
const areaTint = computed(() => ({ '--AREA-rgb': AREA_RGB[areaKey] || 'var(--primary-rgb)' }))

const { data, error: fetchError } = await useAsyncData(`area-${areaKey}`, () =>
  apiFetch<any>(`/api/entities?area=${areaKey}&limit=200`)
)

const AREA_EDITORIAL: Record<string, { title: string; paragraphs: string[] }> = {
  'vinh-long': {
    title: 'Vĩnh Long — xứ dừa miệt vườn',
    paragraphs: [
      'Vĩnh Long nằm giữa sông Tiền và sông Hậu, nổi tiếng với các cù lao trái cây, vườn cây ăn trái xanh mướt quanh năm và hệ thống kênh rạch chằng chịt. Du khách đến đây thường trải nghiệm đi xuồng ba lá, thăm các làng nghề truyền thống như làm gạch gốm, dệt chiếu, và thưởng thức trái cây tại vườn.',
      'Ngoài du lịch sinh thái, Vĩnh Long còn giữ được nhiều di tích lịch sử và công trình kiến trúc độc đáo: Văn Thánh Miếu, nhà cổ Cai Cường, chùa Tiên Châu. Ẩm thực địa phương phong phú với cá tai tượng chiên xù, bánh tráng Cù Lao Mây, và các loại mứt trái cây đặc sản.',
    ],
  },
  'ben-tre': {
    title: 'Bến Tre — xứ dừa ngàn năm',
    paragraphs: [
      'Bến Tre được mệnh danh là "xứ dừa" với hơn 70.000 hecta dừa — lớn nhất cả nước. Toàn tỉnh là một hệ thống cù lao được bao bọc bởi sông Tiền và biển Đông, tạo nên cảnh quan sông nước đặc trưng nhất vùng Đồng bằng sông Cửu Long.',
      'Du lịch Bến Tre xoay quanh trải nghiệm sông nước: chèo thuyền trên rạch dừa, thăm lò kẹo dừa, uống nước dừa tươi trong vườn, và nghỉ tại các homestay ven sông. Sản phẩm OCOP nổi bật của Bến Tre gồm kẹo dừa Bến Tre, rượu dừa, tinh dầu dừa và các sản phẩm thủ công từ gáo dừa.',
    ],
  },
  'tra-vinh': {
    title: 'Trà Vinh — giao thoa Kinh–Khmer–Hoa',
    paragraphs: [
      'Trà Vinh là tỉnh có cộng đồng Khmer lớn nhất vùng đồng bằng, tạo nên bản sắc văn hoá đặc biệt với hệ thống hơn 140 ngôi chùa Khmer cổ, lễ hội Ok Om Bok, đua ghe Ngo và ẩm thực Khmer đặc trưng. Kiến trúc chùa Khmer Trà Vinh được đánh giá là đẹp nhất khu vực.',
      'Ngoài văn hoá Khmer, Trà Vinh còn có bờ biển Ba Động kéo dài, rừng ngập mặn Long Khánh, và hệ thống ao Bà Om — di tích quốc gia với hàng cổ thụ hàng trăm năm tuổi. Đặc sản nổi tiếng gồm bún nước lèo, bánh tét Trà Cuôn, và dừa sáp — giống dừa quý hiếm chỉ có ở Cầu Kè, Trà Vinh.',
    ],
  },
}
const areaEditorial = computed(() => AREA_EDITORIAL[areaKey])

const ADMIN_LEVELS = ['phuong', 'xa', 'tinh']
const { data: placesData } = await useAsyncData(`area-wards-${areaKey}`, () =>
  apiFetch<Place[]>('/api/places').catch(() => [])
)
const wards = computed(() =>
  (placesData.value || [])
    .filter((p: Entity) => p.area === areaKey && ADMIN_LEVELS.includes(p.level))
    .sort((a: Entity, b: Entity) => a.name.localeCompare(b.name, 'vi'))
)

const entities = computed(() => {
  const raw = data.value
  if (!raw) return []
  const types = CARD_TYPES as readonly string[]
  return (raw.entities || []).filter((e: Entity) => types.includes(e.type))
})

const typeStats = computed(() => {
  const counts: Record<string, number> = {}
  for (const e of entities.value) counts[e.type] = (counts[e.type] || 0) + 1
  return (CARD_TYPES as readonly string[])
    .filter(t => counts[t])
    .map(t => ({ type: t, label: TYPE_META[t]?.label || t, count: counts[t] }))
})

const featured = computed(() =>
  entities.value.filter((e: Entity) => e.images?.length).slice(0, 6)
)

const typeSections = computed(() =>
  (CARD_TYPES as readonly string[])
    .map(t => ({
      type: t,
      emoji: TYPE_META[t]?.emoji || '📍',
      label: TYPE_META[t]?.label || t,
      items: entities.value.filter((e: Entity) => e.type === t),
    }))
    .filter(c => c.items.length > 0)
)

// Per-type "see all" expansion (truncated scroll-rows expand in place).
const expanded = reactive<Record<string, boolean>>({})
function toggleExpand(type: string) {
  expanded[type] = !expanded[type]
}

if (areaMeta) {
  useSeoMeta({
    title: `Khu vực ${areaMeta.name} — vinhlong360`,
    description: areaMeta.blurb,
    ogTitle: `${areaMeta.emoji} ${areaMeta.name} — vinhlong360`,
    ogDescription: areaMeta.blurb,
    ogImage: '/icons/icon-512.png',
  })

  useHead({
    link: [{ rel: 'canonical', href: canonicalUrl(`/khu-vuc/${areaKey}`) }],
    script: [{
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: [
          { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
          { '@type': 'ListItem', position: 2, name: areaMeta.name },
        ],
      }),
    }],
  })

  useHead(() => ({
    script: [{
      type: 'application/ld+json',
      innerHTML: JSON.stringify(itemListJsonLd(
        `Khu vực ${areaMeta.name}`,
        areaMeta.blurb,
        `/khu-vuc/${areaKey}`,
        entities.value,
      )),
    }],
  }))
}
</script>

<style scoped>
.see-all-count { font-size: var(--text-sm); color: var(--muted); }

/* ── SIGNATURE: Regional identity hero bloom ──────────────────────────────
   A radial wash keyed to the region's own colour (--AREA-rgb, set inline per
   area) layered over the shared catalog-hero gradient/motif so each region
   feels "owned" by its colour without overwriting the global motif layer.
   Sits below the text/stats (catalog-hero-inner / catalog-stats are z-index 1
   per catalog.css). Decorative only. */
.area-hero { --AREA-rgb: var(--primary-rgb); }
.area-hero-bloom {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(120% 80% at 6% -10%, rgba(var(--AREA-rgb), .12), transparent 60%),
    linear-gradient(to bottom, transparent 55%, rgba(0, 0, 0, .05) 100%);
}
.dark .area-hero-bloom {
  background:
    radial-gradient(120% 80% at 6% -10%, rgba(var(--AREA-rgb), .18), transparent 60%),
    linear-gradient(to bottom, transparent 55%, rgba(0, 0, 0, .18) 100%);
}
/* a touch more breathing room around the regional emoji + text on phones */
@media (max-width: 640px) {
  .area-hero { padding-bottom: var(--space-6); }
}

/* ── SIGNATURE: Stat pills as "proof badges" ──────────────────────────────
   Region-tinted surface + hairline so each stat reads as a credential, not
   loose text. Hover lifts the number in the region colour. Scoped to this
   page only. */
.area-stats .stat-item {
  background: rgba(var(--AREA-rgb), .06);
  border: .5px solid var(--line);
  border-radius: var(--radius-md);
}
.area-stats .stat-item:hover {
  background: rgba(var(--AREA-rgb), .1);
}
.area-stats .stat-item:hover .stat-num {
  color: var(--primary-fg-strong, var(--primary-fg));
  transform: scale(1.08);
}
.area-stats .stat-num {
  display: inline-block;
  transition: color .3s var(--ease-out), transform .25s var(--ease-spring-gentle);
}
/* mobile: stats become a tidy 2-up grid so they never orphan on a line */
@media (max-width: 640px) {
  .area-stats {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-3);
  }
  .area-stats .stat-item {
    align-items: center;
    text-align: center;
    min-height: 44px;
    justify-content: center;
  }
}

/* ── SIGNATURE: Type-section "see all" toggle ─────────────────────────────
   Truncated scroll-rows (>8 items) get an inline expand control instead of a
   silent cut. Matches the muted count typography when collapsed. */
.see-all-toggle {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--primary-fg);
  background: transparent;
  border: .5px solid transparent;
  border-radius: var(--radius-full);
  padding: var(--space-2) var(--space-3);
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  transition: background .25s var(--ease-out), color .25s var(--ease-out), transform .15s var(--ease-spring);
}
.see-all-toggle:hover {
  background: rgba(var(--primary-rgb), .08);
  border-color: rgba(var(--primary-rgb), .2);
}
.see-all-toggle:active { transform: scale(.96); transition-duration: .08s; }
.see-all-toggle:focus-visible { outline: 2px solid var(--primary); outline-offset: 3px; }

/* ── POLISH: Ward chips wrap to a tap-friendly grid on mobile ─────────────
   On phones the shared .chip-row.wrap-mobile already wraps; here we lock the
   ward chips to a 2-column grid with comfortable 48px tap targets so no ward
   name gets cut and neighbours don't crowd. */
@media (max-width: 640px) {
  .area-wards {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-2);
  }
  .area-wards .chip {
    min-height: 48px;
    justify-content: center;
    text-align: center;
    font-size: var(--text-sm);
    min-width: 0;
    white-space: normal;
    line-height: 1.25;
  }
}

/* loading heading mirrors a section title without drawing attention */
.sk-heading { color: var(--muted); font-weight: var(--weight-semibold); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .area-stats .stat-item:hover .stat-num { transform: none; }
  .see-all-toggle:active { transform: none; }
}
</style>
