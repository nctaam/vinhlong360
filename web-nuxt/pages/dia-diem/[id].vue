<template>
  <div v-if="entity">
    <!-- Cover -->
    <div :class="['detail-cover', `cat-${typeMeta.cat}`]">
      <div class="dc-inner">
        <a class="back" href="#" @click.prevent="goBack">← Quay lại</a>
        <span class="dc-emoji">{{ typeMeta.emoji }}</span>
        <span class="dc-type">{{ typeMeta.label }}</span>
        <h1>{{ entity.name }}</h1>
        <p v-if="entity.place_name" class="dc-place">📍 {{ entity.place_name }}</p>
        <div class="dc-actions">
          <ClientOnly>
            <SaveButton :entity="entity" :show-label="true" />
          </ClientOnly>
          <ClientOnly>
            <ShareButton :title="entity.name" :text="entity.summary" />
          </ClientOnly>
        </div>
      </div>
    </div>

    <!-- Image Gallery -->
    <ImageGallery v-if="entity.images?.length" :images="entity.images" :alt="entity.name" />

    <!-- Body -->
    <div class="detail-body">
      <div class="detail-main">
        <p class="lead">{{ entity.summary }}</p>

        <!-- Month strip -->
        <div v-if="entity.season?.months" style="margin-top: 20px">
          <h2 style="font-size: 1.1rem; margin: 0 0 8px">Mùa vụ</h2>
          <div class="month-strip">
            <span
              v-for="m in 12"
              :key="m"
              :class="['ms-cell', { on: entity.season?.months?.includes(m), peak: entity.season?.peak?.includes(m) }]"
            >T{{ m }}</span>
          </div>
          <div class="ms-legend">
            <span class="ms-cell on" style="width:16px;height:16px"></span> Có mùa
            <span class="ms-cell on peak" style="width:16px;height:16px"></span> Rộ nhất
          </div>
        </div>

        <!-- Relationships -->
        <div v-if="relationships.length" class="rel-block">
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
        <NearbyEntities v-if="entity.place_area" :entity-id="id" :entity-type="entity.type" :area="entity.place_area" />

        <!-- Community Reviews -->
        <ClientOnly>
          <EntityReviews :entity-id="id" :entity-name="entity.name" />
        </ClientOnly>

        <!-- AI Travel Tips -->
        <ClientOnly>
          <AITravelTips v-if="entity" :entity-id="id" :entity-name="entity.name" />
        </ClientOnly>

        <!-- AI Recommendations -->
        <ClientOnly>
          <AIRecommendations :entity-id="id" title="Bạn cũng có thể thích" :limit="4" />
        </ClientOnly>
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
          <span class="v">{{ entity.place_name }}</span>
        </div>
        <div v-if="entity.place_area" class="fact">
          <span class="k">Khu vực</span>
          <span class="v">
            <NuxtLink :to="`/khu-vuc/${entity.place_area}`" style="color: var(--primary); font-weight: 600">{{ areaName }}</NuxtLink>
          </span>
        </div>
        <div v-if="entity.season" class="fact">
          <span class="k">Mùa</span>
          <span class="v">{{ seasonLabel }}</span>
        </div>

        <div class="quality-panel" :class="{ 'needs-review': !quality.has_source }">
          <div class="quality-head">
            <span class="quality-dot" :class="quality.has_source ? 'ok' : 'warn'"></span>
            <strong>{{ quality.has_source ? 'Đã có nguồn dữ liệu' : 'Cần bổ sung nguồn' }}</strong>
          </div>
          <a
            v-if="quality.source_url"
            class="quality-source"
            :href="quality.source_url"
            target="_blank"
            rel="noopener noreferrer"
          >{{ quality.source_title || sourceHost || 'Nguồn tham khảo' }}</a>
          <p v-else class="quality-note">Thông tin này đang chờ bổ sung nguồn xác minh.</p>
          <div v-if="qualityMissingLabels.length" class="quality-tags">
            <span v-for="label in qualityMissingLabels" :key="label">{{ label }}</span>
          </div>
          <NuxtLink class="quality-report" :to="reportUrl">Báo sai dữ liệu</NuxtLink>
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
          <span class="v"><a :href="'tel:' + entity.attributes.phone" style="color: var(--primary)">{{ entity.attributes.phone }}</a></span>
        </div>
        <div v-if="entity.attributes?.address" class="fact">
          <span class="k">Địa chỉ</span>
          <span class="v">{{ entity.attributes.address }}</span>
        </div>
        <div v-if="entity.attributes?.website" class="fact">
          <span class="k">Website</span>
          <span class="v"><a :href="entity.attributes.website" target="_blank" rel="noopener" style="color: var(--primary); word-break: break-all">{{ entity.attributes?.website?.replace(/^https?:\/\//, '') }}</a></span>
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

        <!-- GĐ13.2: liên hệ trực tiếp (showcase — KHÔNG đặt hàng) -->
        <div v-if="entity.attributes?.phone || zaloLink" style="display:flex; gap:8px; flex-wrap:wrap; margin:14px 0 8px;">
          <a v-if="entity.attributes?.phone" class="ns-action" :href="'tel:' + entity.attributes.phone" style="flex:1; text-align:center;">📞 Gọi</a>
          <a v-if="zaloLink" class="ns-action" :href="zaloLink" target="_blank" rel="nofollow" style="flex:1; text-align:center;">💬 Zalo</a>
        </div>
        <!-- GĐ13.1 (MVP): chủ cơ sở nhận listing -->
        <NuxtLink :to="claimUrl" class="ns-action" style="display:block; text-align:center;">🏷️ Đây là cơ sở của tôi — đăng ký quản lý</NuxtLink>
        <!-- GĐ13.8: truy xuất nguồn gốc (sản phẩm) -->
        <div v-if="entity.type === 'product'" style="margin-top:12px; padding:10px 12px; border:1px solid rgba(0,0,0,.1); border-radius:8px; font-size:.85rem;">
          <strong>🔎 Truy xuất nguồn gốc</strong>
          <p style="margin:4px 0; color:var(--muted,#777)">Xem "Nguồn dữ liệu" &amp; quan hệ "Sản xuất tại" ở trên. Thông tin tham khảo — vui lòng kiểm chứng với cơ sở. (Không thay mã vùng trồng/đóng gói chính thức cho xuất khẩu.)</p>
          <small v-if="entity.updatedAt">Cập nhật: {{ entity.updatedAt }}</small>
        </div>

        <ClientOnly>
          <AIBestTime :entity-id="id" :entity-name="entity.name" />
        </ClientOnly>

        <!-- Contextual next steps -->
        <div class="next-steps">
          <h3 class="ns-title">Bước tiếp theo</h3>
          <ClientOnly>
            <button class="ns-action" @click="toggleAndSave">
              {{ entitySaved ? '❤️ Đã lưu' : '🤍 Lưu vào hành trình' }}
            </button>
          </ClientOnly>
        <NuxtLink to="/tao-lich-trinh" no-prefetch class="ns-action">📋 Thêm vào lịch trình</NuxtLink>
          <NuxtLink v-if="entity.type !== 'accommodation'" to="/luu-tru" class="ns-action">🏡 Tìm chỗ ở gần đây</NuxtLink>
        <NuxtLink to="/ban-do" no-prefetch class="ns-action">🗺️ Xem trên bản đồ</NuxtLink>
          <NuxtLink to="/tuyen-duong" class="ns-action">🛤️ Tuyến đường gợi ý</NuxtLink>
        </div>
      </aside>
    </div>
  </div>
  <div v-else class="page">
    <p class="empty">Không tìm thấy dữ liệu.</p>
  </div>
</template>

<script setup lang="ts">
import { TYPE_META, AREA_META, REL_FWD, REL_BWD } from '~/composables/useConstants'
import { seasonText } from '~/composables/useSeason'

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

const seasonLabel = computed(() => seasonText(entity.value?.season))

// GĐ13.2: link Zalo từ attributes.zalo (số hoặc URL). KHÔNG đặt hàng — chỉ liên hệ.
const zaloLink = computed(() => {
  const z = entity.value?.attributes?.zalo
  if (!z) return ''
  return String(z).startsWith('http') ? z : `https://zalo.me/${String(z).replace(/\D/g, '')}`
})
// GĐ13.1 (MVP): chủ cơ sở "nhận listing" -> trang liên hệ kèm ngữ cảnh (luồng owner-edit đầy đủ = sau).
const claimUrl = computed(() => `/lien-he?claim=${encodeURIComponent(id.value)}`)

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
  return {
    target_id: otherId,
    target_name: otherName || otherId,
    rel_type: relType,
    distance_km: distance,
    label: isFwd ? (REL_FWD[relType] || relType) : (REL_BWD[relType] || relType),
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

  useSeoMeta({
    title: `${e.name} — ${typeMeta.value.label} — vinhlong360`,
    description: e.summary || '',
    ogTitle: `${e.name} — vinhlong360`,
    ogDescription: e.summary || '',
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
    place: 'Place',
  }
  const ldType = TYPE_TO_SCHEMA[e.type] || 'TouristAttraction'

  const ld: Record<string, any> = {
    '@context': 'https://schema.org',
    '@type': ldType,
    name: e.name,
    description: e.summary,
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
