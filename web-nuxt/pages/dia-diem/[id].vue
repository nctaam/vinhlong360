<template>
  <div v-if="entity">
    <!-- Breadcrumb -->
    <nav class="breadcrumb" aria-label="Breadcrumb">
      <ol>
        <li><NuxtLink to="/">Trang chủ</NuxtLink></li>
        <li><NuxtLink :to="typeBreadcrumbUrl">{{ typeMeta.label }}</NuxtLink></li>
        <li v-if="entity.place_area"><NuxtLink :to="`/khu-vuc/${entity.place_area}`">{{ areaName }}</NuxtLink></li>
        <li aria-current="page">{{ entity.name }}</li>
      </ol>
    </nav>

    <!-- Cover + Hero Image -->
    <div :class="['detail-cover', `cat-${typeMeta.cat}`, { 'has-cover-img': coverImage }]">
      <img v-if="coverImage" :src="coverImage" :alt="entity.name" class="dc-bg" loading="eager" fetchpriority="high" sizes="100vw" @load="($event.target as HTMLElement)?.classList.add('loaded')" @click="openCoverLightbox" />
      <div v-if="coverImage" class="dc-overlay"></div>
      <div class="dc-inner">
        <span class="dc-emoji">{{ typeMeta.emoji }}</span>
        <span class="dc-type">{{ typeMeta.label }}</span>
        <h1>{{ entity.name }}</h1>
        <p v-if="entity.place_name" class="dc-place">📍 <NuxtLink v-if="entity.placeId" :to="`/xa-phuong/${entity.placeId}`" class="dc-place-link">{{ entity.place_name }}</NuxtLink><template v-else>{{ entity.place_name }}</template></p>
        <div class="dc-actions">
          <ClientOnly>
            <SaveButton :entity="entity" :show-label="true" />
          </ClientOnly>
          <ClientOnly>
            <ShareButton :title="entity.name" :text="entity.summary" />
          </ClientOnly>
        </div>
      </div>
      <button v-if="entity.images?.length" class="dc-photo-btn" :aria-label="entity.images.length === 1 ? 'Xem ảnh' : `Xem ${entity.images.length} ảnh`" @click="openCoverLightbox">
        <span class="dc-photo-icon" aria-hidden="true">&#128247;</span>
        {{ entity.images.length === 1 ? 'Xem ảnh' : `${entity.images.length} ảnh` }}
      </button>
      <div v-if="entity.images?.length > 1" class="dc-thumbs">
        <img
          v-for="(src, i) in entity.images.slice(0, 4)"
          :key="src"
          :src="src"
          :alt="`${entity.name} - ${i + 1}`"
          :class="['dc-thumb', { active: i === 0 }]"
          loading="lazy"
          width="56"
          height="40"
          decoding="async"
          role="button"
          tabindex="0"
          @click="openCoverLightbox(i)"
          @keydown.enter="openCoverLightbox(i)"
          @keydown.space.prevent="openCoverLightbox(i)"
        />
        <button v-if="entity.images.length > 4" class="dc-thumb-more" :aria-label="`Xem thêm ${entity.images.length - 4} ảnh`" @click="openCoverLightbox(4)">
          +{{ entity.images.length - 4 }}
        </button>
      </div>
      <small v-if="imageCredit" class="dc-credit">{{ imageCredit }}</small>
    </div>

    <!-- Lightbox (replaces old ImageGallery) -->
    <Teleport to="body">
      <div v-if="lightboxOpen" class="lightbox" role="dialog" aria-modal="true" aria-label="Xem ảnh" @click.self="lightboxOpen = false" @keydown.escape="lightboxOpen = false" @keydown.left="lbPrev" @keydown.right="lbNext" tabindex="-1" ref="lightboxEl">
        <button class="lb-close" aria-label="Đóng" @click="lightboxOpen = false">&times;</button>
        <button v-if="entity.images?.length > 1" class="lb-prev" aria-label="Ảnh trước" @click="lbPrev">&#8249;</button>
        <img :src="entity.images[lbIndex]" :alt="`${entity.name} - ${lbIndex + 1}`" class="lb-img" />
        <button v-if="entity.images?.length > 1" class="lb-next" aria-label="Ảnh tiếp" @click="lbNext">&#8250;</button>
        <div class="lb-counter" aria-live="polite">{{ lbIndex + 1 }} / {{ entity.images.length }}</div>
      </div>
    </Teleport>

    <!-- Body -->
    <div class="detail-body">
      <div class="detail-main">
        <!-- Highlights quét nhanh (Baymard: 78% site thiếu; chống info bị chôn dưới fold) -->
        <div v-if="hasHighlights" class="highlights">
          <a v-if="entity.attributes?.phone" class="hl hl-action" :href="'tel:' + entity.attributes.phone">📞 Gọi</a>
          <a v-if="zaloLink" class="hl hl-action" :href="zaloLink" target="_blank" rel="nofollow">💬 Zalo</a>
          <NuxtLink v-if="hasCoords" class="hl hl-action" :to="mapUrl">🗺️ Bản đồ</NuxtLink>
          <span v-if="entity.attributes?.hours" class="hl">🕒 {{ entity.attributes.hours }}</span>
          <span v-if="priceText" class="hl">💰 {{ priceText }}</span>
          <span v-if="addressText" class="hl">📍 {{ addressText }}</span>
        </div>
        <p class="lead">{{ entity.summary }}</p>

        <!-- Mô tả chi tiết -->
        <div v-if="descriptionParagraphs.length" class="entity-description">
          <p v-for="(para, i) in visibleParagraphs" :key="i">{{ para }}</p>
          <button v-if="descriptionParagraphs.length > 3" class="desc-toggle" @click="descExpanded = !descExpanded">
            {{ descExpanded ? 'Thu gọn ↑' : 'Đọc thêm ↓' }}
          </button>
        </div>

        <!-- Lưu ý thực tế — Scenarios 2,3,6,9: practical tips for food/family/OCOP/delegation -->
        <div v-if="practicalTips.length" class="practical-tips reveal">
          <h2 class="section-subtitle">📋 Lưu ý thực tế</h2>
          <ul class="pt-list">
            <li v-for="tip in practicalTips" :key="tip.icon" class="pt-item">
              <span class="pt-icon">{{ tip.icon }}</span>
              <div class="pt-content">
                <strong>{{ tip.label }}</strong>
                <span>{{ tip.value }}</span>
              </div>
            </li>
          </ul>
        </div>

        <!-- Month strip -->
        <div v-if="entity.season?.months" class="season-block reveal">
          <h2 class="section-subtitle">Mùa vụ</h2>
          <div class="month-strip">
            <span
              v-for="m in 12"
              :key="m"
              :class="['ms-cell', { on: entity.season?.months?.includes(m), peak: entity.season?.peak?.includes(m) }]"
            >T{{ m }}</span>
          </div>
          <div class="ms-legend">
            <span class="ms-cell on ms-legend-swatch"></span> Có mùa
            <span class="ms-cell on peak ms-legend-swatch"></span> Rộ nhất
          </div>
        </div>

        <!-- Relationships -->
        <div v-if="relationships.length" class="rel-block reveal">
          <h2>Liên kết</h2>
          <ul class="rel-list">
            <li v-for="rel in relationships" :key="`${rel.target_id}-${rel.rel_type}`">
              <span class="rel-label">{{ rel.label }}</span>
              <span class="rel-main">
                <NuxtLink :to="`/dia-diem/${rel.target_id}`">{{ rel.target_name }}</NuxtLink>
                <small v-if="rel.distance_km" class="rel-distance">{{ rel.distance_km }} km</small>
              </span>
            </li>
          </ul>
          <button
            v-if="hasMoreRelationships"
            class="rel-more"
            type="button"
            :disabled="loadingRelationships"
            @click="loadMoreRelationships"
          >
            {{ loadingRelationships ? 'Đang tải...' : `Xem thêm ${remainingRelationshipCount}` }}
          </button>
        </div>

        <!-- Nearby entities (same area, different type) -->
        <NuxtErrorBoundary>
          <NearbyEntities v-if="entity.place_area" :entity-id="id" :entity-type="entity.type" :area="entity.place_area" />
        </NuxtErrorBoundary>

        <!-- Community Reviews -->
        <NuxtErrorBoundary>
          <ClientOnly>
            <EntityReviews :entity-id="id" :entity-name="entity.name" />
          </ClientOnly>
        </NuxtErrorBoundary>

        <!-- AI Travel Tips -->
        <NuxtErrorBoundary>
          <ClientOnly>
            <AITravelTips v-if="entity" :entity-id="id" :entity-name="entity.name" />
          </ClientOnly>
        </NuxtErrorBoundary>

        <!-- AI Recommendations -->
        <NuxtErrorBoundary>
          <ClientOnly>
            <AIRecommendations :entity-id="id" title="Bạn cũng có thể thích" :limit="4" />
          </ClientOnly>
        </NuxtErrorBoundary>
      </div>

      <!-- Sidebar -->
      <aside class="detail-aside">
        <!-- OCOP highlight -->
        <div v-if="entity.attributes?.ocop" class="ocop-highlight">
          <div class="ocop-stars">
            <span v-for="s in ocopStars" :key="s" class="ocop-star">⭐</span>
          </div>
          <strong>Sản phẩm OCOP {{ entity.attributes.ocop }}</strong>
          <small>Chương trình Mỗi xã Một sản phẩm</small>
        </div>

        <h2>Thông tin</h2>
        <div class="fact">
          <span class="k">Loại</span>
          <span class="v">{{ typeMeta.emoji }} {{ typeMeta.label }}</span>
        </div>
        <div v-if="entity.place_name" class="fact">
          <span class="k">Địa điểm</span>
          <span class="v">
            <NuxtLink v-if="entity.placeId" :to="`/xa-phuong/${entity.placeId}`" class="fact-link">{{ entity.place_name }}</NuxtLink>
            <template v-else>{{ entity.place_name }}</template>
          </span>
        </div>
        <div v-if="entity.place_area" class="fact">
          <span class="k">Khu vực</span>
          <span class="v">
            <NuxtLink :to="`/khu-vuc/${entity.place_area}`" class="fact-link">{{ areaName }}</NuxtLink>
          </span>
        </div>
        <div v-if="entity.season" class="fact">
          <span class="k">Mùa</span>
          <span class="v">{{ seasonLabel }}</span>
        </div>

        <!-- Practical info from attributes -->
        <div v-if="entity.attributes?.price" class="fact">
          <span class="k">Giá tham khảo</span>
          <span class="v">{{ entity.attributes.price }}</span>
        </div>
        <div v-if="entity.attributes?.hours" class="fact">
          <span class="k">Giờ mở cửa</span>
          <span class="v">{{ entity.attributes.hours }}</span>
        </div>
        <div v-if="entity.attributes?.phone" class="fact">
          <span class="k">Liên hệ</span>
          <span class="v"><a :href="'tel:' + entity.attributes.phone" class="fact-link">{{ entity.attributes.phone }}</a></span>
        </div>
        <div v-if="entity.attributes?.address" class="fact">
          <span class="k">Địa chỉ</span>
          <span class="v">{{ entity.attributes.address }}</span>
        </div>
        <div v-if="entity.attributes?.website" class="fact">
          <span class="k">Website</span>
          <span class="v"><a :href="entity.attributes.website" target="_blank" rel="noopener" class="fact-link website-link">{{ entity.attributes?.website?.replace(/^https?:\/\//, '') }}</a></span>
        </div>
        <div v-if="entity.attributes?.fee" class="fact">
          <span class="k">Phí vào cửa</span>
          <span class="v">{{ entity.attributes.fee }}</span>
        </div>
        <div v-if="entity.attributes?.transport" class="fact">
          <span class="k">Di chuyển</span>
          <span class="v">{{ entity.attributes.transport }}</span>
        </div>
        <div v-if="entity.attributes?.amenities" class="fact">
          <span class="k">Tiện ích</span>
          <span class="v">{{ Array.isArray(entity.attributes.amenities) ? entity.attributes.amenities.join(', ') : entity.attributes.amenities }}</span>
        </div>

        <!-- Liên hệ trực tiếp (showcase — KHÔNG đặt hàng/giỏ hàng/thanh toán on-site) -->
        <div v-if="entity.attributes?.phone || zaloLink || buyContactUrl" class="contact-row">
          <a v-if="entity.attributes?.phone" class="ns-action contact-cta" :href="'tel:' + entity.attributes.phone">📞 Gọi</a>
          <a v-if="zaloLink" class="ns-action contact-cta" :href="zaloLink" target="_blank" rel="nofollow">💬 Zalo</a>
          <a v-if="buyContactUrl" class="ns-action contact-cta" :href="buyContactUrl" target="_blank" rel="nofollow">🛒 Hỏi mua trực tiếp</a>
        </div>
        <NuxtLink :to="claimUrl" class="ns-action claim-cta">🏷️ Đây là cơ sở của tôi — đăng ký quản lý</NuxtLink>
        <NuxtLink class="quality-report" :to="reportUrl">Báo sai dữ liệu</NuxtLink>
        <!-- Truy xuất nguồn gốc (sản phẩm) -->
        <div v-if="entity.type === 'product'" class="traceability">
          <strong>🔎 Truy xuất nguồn gốc</strong>
          <p>Xem "Nguồn dữ liệu" &amp; quan hệ "Sản xuất tại" ở trên. Thông tin tham khảo — vui lòng kiểm chứng với cơ sở.</p>
          <small v-if="entity.updatedAt">Cập nhật: {{ entity.updatedAt }}</small>
        </div>

        <NuxtErrorBoundary>
          <ClientOnly>
            <AIBestTime :entity-id="id" :entity-name="entity.name" />
          </ClientOnly>
        </NuxtErrorBoundary>

        <!-- Contextual next steps -->
        <div class="next-steps">
          <h3 class="ns-title">Bước tiếp theo</h3>
          <ClientOnly>
            <button class="ns-action" @click="toggleAndSave">
              {{ entitySaved ? '❤️ Đã lưu' : '🤍 Lưu vào lịch trình' }}
            </button>
          </ClientOnly>
        <NuxtLink to="/tao-lich-trinh" no-prefetch class="ns-action">📋 Thêm vào lịch trình</NuxtLink>
          <NuxtLink v-if="entity.type !== 'accommodation'" to="/luu-tru" class="ns-action">🏡 Tìm chỗ ở gần đây</NuxtLink>
        <NuxtLink :to="mapUrl" no-prefetch class="ns-action">🗺️ Xem trên bản đồ</NuxtLink>
          <NuxtLink to="/tuyen-duong" class="ns-action">🛤️ Tuyến đường gợi ý</NuxtLink>
        </div>
      </aside>
    </div>

    <!-- Sticky mobile CTA bar (always visible, thumb zone) -->
    <div v-if="entity.attributes?.phone || zaloLink || hasCoords" class="sticky-cta-bar">
      <a v-if="entity.attributes?.phone" class="scta-phone" :href="'tel:' + entity.attributes.phone" aria-label="Gọi điện thoại">📞 Gọi</a>
      <a v-if="zaloLink" class="scta-zalo" :href="zaloLink" target="_blank" rel="nofollow" aria-label="Nhắn Zalo">💬 Zalo</a>
      <NuxtLink v-if="hasCoords" class="scta-map" :to="mapUrl" aria-label="Xem trên bản đồ">🗺️ Bản đồ</NuxtLink>
    </div>
  </div>
  <div v-else class="page">
    <p class="empty">Không tìm thấy dữ liệu.</p>
  </div>
</template>

<script setup lang="ts">
import { TYPE_META, AREA_META, REL_FWD, REL_BWD } from '~/composables/useConstants'
import { seasonText } from '~/composables/useSeason'

useReveal()
const { isSaved, toggle: toggleFav } = useFavorites()

const route = useRoute()
const router = useRouter()
const id = computed(() => String(route.params.id || ''))
const RELATIONSHIP_BATCH_SIZE = 24

function goBack() {
  if (import.meta.client && window.history.length > 1) {
    router.back()
  } else {
    navigateTo('/du-lich')
  }
}

const { data: entity, error: fetchError } = await useAsyncData(
  computed(() => `entity-${id.value}`),
  () => $fetch<any>(`/api/entities/${id.value}`),
  { watch: [id] }
)

if (fetchError.value) {
  throw createError({ statusCode: 404, statusMessage: 'Không tìm thấy nội dung' })
}

const typeMeta = computed(() => {
  if (!entity.value) return { emoji: '•', label: '', cat: 'place' }
  return TYPE_META[entity.value.type] || { emoji: '•', label: entity.value.type, cat: 'place' }
})

const areaName = computed(() => {
  const area = entity.value?.place_area || entity.value?.area
  return AREA_META[area]?.name || area || ''
})

const coverImage = computed(() => {
  const imgs = entity.value?.images
  return Array.isArray(imgs) && imgs.length ? imgs[0] : ''
})

const imageCredit = computed(() => {
  const credits = entity.value?.image_credits
  if (!Array.isArray(credits) || !credits.length) return ''
  const c = credits[0]
  return c.author ? `${c.author} · ${c.license || 'CC'}` : ''
})

const lightboxOpen = ref(false)
const lbIndex = ref(0)
const lightboxEl = ref<HTMLElement | null>(null)
let lbTriggerEl: HTMLElement | null = null
function openCoverLightbox(idx = 0) {
  if (!entity.value?.images?.length) return
  lbTriggerEl = document.activeElement as HTMLElement
  lbIndex.value = typeof idx === 'number' ? idx : 0
  lightboxOpen.value = true
  nextTick(() => lightboxEl.value?.focus())
}
function lbPrev() {
  const len = entity.value?.images?.length || 1
  lbIndex.value = (lbIndex.value - 1 + len) % len
}
function lbNext() {
  const len = entity.value?.images?.length || 1
  lbIndex.value = (lbIndex.value + 1) % len
}
watch(lightboxOpen, (v) => {
  if (!import.meta.client) return
  document.body.style.overflow = v ? 'hidden' : ''
  if (!v) nextTick(() => lbTriggerEl?.focus())
})

const TYPE_BREADCRUMB: Record<string, string> = {
  product: '/san-pham', experience: '/du-lich', attraction: '/du-lich',
  dish: '/du-lich', craft_village: '/du-lich', accommodation: '/luu-tru',
  organization: '/danh-ba', place: '/xa-phuong',
}
const typeBreadcrumbUrl = computed(() => TYPE_BREADCRUMB[entity.value?.type] || '/du-lich')

const seasonLabel = computed(() => seasonText(entity.value?.season))

const descriptionParagraphs = computed(() => {
  const desc = entity.value?.description
  if (!desc || typeof desc !== 'string') return []
  return desc.split(/\n\s*\n/).map(p => p.trim()).filter(p => p.length > 0)
})
const descExpanded = ref(false)
const visibleParagraphs = computed(() =>
  descExpanded.value || descriptionParagraphs.value.length <= 3
    ? descriptionParagraphs.value
    : descriptionParagraphs.value.slice(0, 3)
)

// GĐ13.2: link Zalo từ attributes.zalo (số hoặc URL). KHÔNG đặt hàng — chỉ liên hệ.
const zaloLink = computed(() => {
  const z = entity.value?.attributes?.zalo
  if (!z) return ''
  return String(z).startsWith('http') ? z : `https://zalo.me/${String(z).replace(/\D/g, '')}`
})
// GĐ13.1 (MVP): chủ cơ sở "nhận listing" -> trang liên hệ kèm ngữ cảnh (luồng owner-edit đầy đủ = sau).
const claimUrl = computed(() => `/lien-he?claim=${encodeURIComponent(id.value)}`)

// D2 (2026-06-13): với sản phẩm OCOP, đưa website RIÊNG của chủ thể thành CTA "hỏi mua trực tiếp"
// — dẫn khách về kênh bán/đặt riêng của họ. KHÔNG link sàn TMĐT, KHÔNG giỏ hàng/thanh toán on-site
// (giữ showcase-only §1.4). Chỉ áp cho product để khỏi trùng link website ở phần "facts".
const buyContactUrl = computed(() => {
  if (entity.value?.type !== 'product') return ''
  const w = entity.value?.attributes?.website
  return w && String(w).startsWith('http') ? w : ''
})

// Highlights (quét nhanh đầu trang)
const priceText = computed(() => entity.value?.attributes?.price || entity.value?.attributes?.fee || '')
const addressText = computed(() => entity.value?.attributes?.address || entity.value?.place_name || '')
const hasCoords = computed(() => !!normalizeCoords(entity.value?.coordinates ?? entity.value?.coords))
// Link bản đồ FOCUS đúng điểm này (truyền id + toạ độ) — không ra bản đồ chung
const mapUrl = computed(() => {
  const c = normalizeCoords(entity.value?.coordinates ?? entity.value?.coords)
  const base = `/ban-do?id=${encodeURIComponent(id.value)}`
  return c ? `${base}&lat=${c[0]}&lng=${c[1]}` : base
})
const hasHighlights = computed(() => !!(entity.value?.attributes?.phone || zaloLink.value || entity.value?.attributes?.hours || priceText.value || addressText.value || hasCoords.value))

const practicalTips = computed(() => {
  const a = entity.value?.attributes
  if (!a) return []
  const tips: { icon: string; label: string; value: string }[] = []
  if (a.booking_note) tips.push({ icon: '📝', label: 'Đặt trước', value: a.booking_note })
  if (a.best_time) tips.push({ icon: '⏰', label: 'Thời điểm tốt nhất', value: a.best_time })
  if (a.transport) tips.push({ icon: '🚗', label: 'Di chuyển', value: a.transport })
  if (a.fee) tips.push({ icon: '🎫', label: 'Phí vào cửa', value: a.fee })
  if (a.amenities) {
    const am = Array.isArray(a.amenities) ? a.amenities.join(', ') : a.amenities
    tips.push({ icon: '✅', label: 'Tiện ích', value: am })
  }
  if (a.family_friendly || a.suitable_for?.includes('family'))
    tips.push({ icon: '👨‍👩‍👧‍👦', label: 'Gia đình', value: 'Phù hợp cho gia đình có trẻ em' })
  if (a.parking) tips.push({ icon: '🅿️', label: 'Đậu xe', value: a.parking })
  return tips
})

const quality = computed(() => entity.value?.quality || {})
const qualityMissingLabels = computed(() => {
  const labels: Record<string, string> = {
    source: 'Thiếu nguồn',
    location: 'Thiếu tọa độ',
    placeId: 'Thiếu địa bàn',
  }
  return (quality.value.missing || []).map((key: string) => labels[key] || key)
})
const sourceHost = computed(() => {
  const url = quality.value.source_url
  if (!url) return ''
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
})
const reportUrl = computed(() => `/cong-dong?report=${encodeURIComponent(id.value)}`)

const entitySaved = computed(() => entity.value ? isSaved(entity.value.id) : false)
function toggleAndSave() {
  if (entity.value) toggleFav(entity.value)
}

// GĐ10.4: normalizeCoords gom vào composables/useCoords.ts (Nuxt auto-import).

const ocopStars = computed(() => {
  const ocop = entity.value?.attributes?.ocop || ''
  const num = parseInt(ocop) || 0
  return Math.min(num, 5)
})

const relationshipRows = ref<any[]>([])
const relationshipTotal = ref(0)
const loadingRelationships = ref(false)

watch(entity, (next) => {
  relationshipRows.value = Array.isArray(next?.relationships) ? [...next.relationships] : []
  relationshipTotal.value = Number(next?.relationship_total ?? relationshipRows.value.length) || relationshipRows.value.length
}, { immediate: true })

function rawRelationshipKey(r: any) {
  const sourceId = r.source_id ?? r.from_id ?? r.from ?? ''
  const targetId = r.target_id ?? r.to_id ?? r.to ?? ''
  const relType = r.rel_type ?? r.type ?? ''
  return `${sourceId}|${targetId}|${relType}`
}

function normalizeRelationship(r: any) {
  const sourceId = r.source_id ?? r.from_id ?? r.from
  const targetId = r.target_id ?? r.to_id ?? r.to
  const relType = r.rel_type ?? r.type
  if (!sourceId || !targetId || !relType) return null
  const isNear = relType === 'near'
  const distance = typeof r.distance_km === 'number' ? r.distance_km : null
  if (isNear && (distance === null || distance > 50)) return null
  const isFwd = sourceId === id.value
  const otherId = r.other_id ?? (isFwd ? targetId : sourceId)
  const otherName = r.other_name ?? (isFwd ? (r.target_name ?? r.name) : (r.source_name ?? r.name))
  const otherType = r.other_type ?? ''
  let label = isFwd ? (REL_FWD[relType] || relType) : (REL_BWD[relType] || relType)
  if ((relType === 'related_to' || relType === 'associated_with') && otherType) {
    const meta = TYPE_META[otherType]
    if (meta) label = meta.emoji + ' ' + meta.label
  }
  return {
    target_id: otherId,
    target_name: otherName || otherId,
    rel_type: relType,
    distance_km: distance,
    label,
  }
}

const relationships = computed(() => {
  return relationshipRows.value
    .map(normalizeRelationship)
    .filter((rel): rel is NonNullable<ReturnType<typeof normalizeRelationship>> => Boolean(rel))
})

const remainingRelationshipCount = computed(() => Math.max(relationshipTotal.value - relationshipRows.value.length, 0))
const hasMoreRelationships = computed(() => remainingRelationshipCount.value > 0)

async function loadMoreRelationships() {
  if (loadingRelationships.value || !hasMoreRelationships.value) return
  loadingRelationships.value = true
  try {
    const response = await $fetch<any>(`/api/entities/${id.value}/relationships`, {
      query: {
        limit: RELATIONSHIP_BATCH_SIZE,
        offset: relationshipRows.value.length,
      },
    })
    relationshipTotal.value = Number(response?.total ?? relationshipTotal.value) || relationshipTotal.value
    const seen = new Set(relationshipRows.value.map(rawRelationshipKey))
    for (const rel of response?.relationships || []) {
      const key = rawRelationshipKey(rel)
      if (!seen.has(key)) {
        relationshipRows.value.push(rel)
        seen.add(key)
      }
    }
  } finally {
    loadingRelationships.value = false
  }
}

if (entity.value && !entity.value.error) {
  const e = entity.value
  const ogImg = Array.isArray(e.images) && e.images.length ? e.images[0] : undefined

  const seoDesc = e.description ? e.description.split(/\n\s*\n/)[0]?.trim() || e.summary : e.summary || ''
  useSeoMeta({
    title: `${e.name} — ${typeMeta.value.label} — vinhlong360`,
    description: seoDesc,
    ogTitle: `${e.name} — vinhlong360`,
    ogDescription: seoDesc,
    ...(ogImg ? { ogImage: ogImg } : {}),
  })

  const TYPE_TO_SCHEMA: Record<string, string> = {
    product: 'Product',
    accommodation: 'LodgingBusiness',
    dish: 'FoodEstablishment',
    craft_village: 'LocalBusiness',
    organization: 'LocalBusiness',
    attraction: 'TouristAttraction',
    experience: 'TouristAttraction',
    event: 'Event',
    place: 'Place',
  }
  const ldType = TYPE_TO_SCHEMA[e.type] || 'TouristAttraction'

  const ld: Record<string, any> = {
    '@context': 'https://schema.org',
    '@type': ldType,
    name: e.name,
    description: e.description || e.summary,
    inLanguage: 'vi-VN',
    url: `https://vinhlong360.vn/dia-diem/${e.id}`,
    address: {
      '@type': 'PostalAddress',
      addressLocality: e.place_name || '',
      addressRegion: areaName.value,
      addressCountry: 'VN',
    },
  }
  if (ogImg) ld.image = Array.isArray(e.images) ? e.images : [ogImg]
  if (e.attributes?.phone) ld.telephone = e.attributes.phone
  const sameAs = [e.attributes?.website, e.quality?.source_url].filter(Boolean)
  if (sameAs.length) ld.sameAs = sameAs.length === 1 ? sameAs[0] : sameAs
  if (e.quality?.source_url) {
    ld.citation = {
      '@type': 'CreativeWork',
      name: e.quality?.source_title || e.quality.source_url,
      url: e.quality.source_url,
    }
  }
  if (e.attributes?.address) ld.address.streetAddress = e.attributes.address
  const geoCoords = normalizeCoords(e.coordinates ?? e.coords)
  if (geoCoords) {
    const [lat, lng] = geoCoords
    ld.geo = { '@type': 'GeoCoordinates', latitude: lat, longitude: lng }
  }
  if (e.attributes?.hours) {
    ld.openingHours = e.attributes.hours
  }
  if (ldType === 'Event') {
    if (e.attributes?.date_start) ld.startDate = e.attributes.date_start
    if (e.attributes?.date_end) ld.endDate = e.attributes.date_end
    if (e.place_name || areaName.value) {
      ld.location = {
        '@type': 'Place',
        name: e.place_name || areaName.value,
        address: { '@type': 'PostalAddress', addressRegion: areaName.value, addressCountry: 'VN' },
      }
      if (geoCoords) {
        ld.location.geo = { '@type': 'GeoCoordinates', latitude: geoCoords[0], longitude: geoCoords[1] }
      }
    }
    ld.eventStatus = 'https://schema.org/EventScheduled'
    ld.eventAttendanceMode = 'https://schema.org/OfflineEventAttendanceMode'
  }
  if (ldType === 'Product') {
    if (e.attributes?.price) {
      ld.offers = {
        '@type': 'Offer',
        price: String(e.attributes.price).replace(/[^\d]/g, '') || '0',
        priceCurrency: 'VND',
        availability: 'https://schema.org/InStock',
      }
    }
    if (e.attributes?.ocop) {
      ld.brand = { '@type': 'Brand', name: `OCOP ${e.attributes.ocop}` }
    }
  }

  const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: 'https://vinhlong360.vn/' },
      { '@type': 'ListItem', position: 2, name: typeMeta.value.label, item: `https://vinhlong360.vn/du-lich` },
      { '@type': 'ListItem', position: 3, name: e.name },
    ],
  }

  useHead({
    link: [{ rel: 'canonical', href: entityDetailUrl(e.id) }],
    script: [
      { type: 'application/ld+json', innerHTML: JSON.stringify(ld) },
      { type: 'application/ld+json', innerHTML: JSON.stringify(breadcrumb) },
    ],
  })
}
</script>
