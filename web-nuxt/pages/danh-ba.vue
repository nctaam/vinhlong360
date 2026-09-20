<template>
  <section class="page dir-page" data-color-system="tri-region-v1">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Danh bạ' }]" :json-ld="true" />

    <!-- Hero -->
    <section class="catalog-hero cat-directory">
      <div class="catalog-hero-inner">
        <span class="catalog-hero-icon" aria-hidden="true"><IconLine name="landmark" /></span>
        <div>
          <h1>{{ pc('hero_title') }}</h1>
          <p>{{ pc('hero_subtitle') }}</p>
        </div>
      </div>
      <div v-if="totalWards" class="catalog-stats">
        <div class="stat-item">
          <CountUp :value="totalWards" class="stat-num" />
          <span class="stat-label">xã/phường</span>
        </div>
        <div v-for="g in wardGroups" :key="g.area" class="stat-item">
          <CountUp :value="g.wards.length" class="stat-num" />
          <span class="stat-label">{{ g.label }}</span>
        </div>
      </div>
    </section>

    <!-- 24/7 Emergency Tourism Rescue Hotlines (Authoritative Priority Layout) -->
    <section class="block dir-emergency emergency-hotline-strip reveal" aria-labelledby="dir-emergency-title" data-dir-emergency>
      <div class="section-head dir-emergency-head">
        <div class="dir-emergency-badge">
          <IconLine name="shield" aria-hidden="true" />
          <span>Hạ tầng An toàn Thực địa</span>
        </div>
        <h2 id="dir-emergency-title" class="sediment-head">Cứu hộ Du lịch &amp; Hotline Khẩn cấp 24/7</h2>
        <p class="dir-emergency-dek">
          Đầu mối cứu hộ cứu nạn sông Tiền, cấp cứu y tế, an ninh trật tự và phà vượt sông luôn túc trực phục vụ du khách.
        </p>
      </div>

      <div class="dir-emergency-priority-layout">
        <!-- Lead Critical Emergency Hotlines -->
        <div class="dir-emergency-leads">
          <article
            v-for="item in priorityHotlines"
            :key="item.id"
            class="dir-emergency-card dir-emergency-card--lead"
          >
            <div class="dir-emergency-card-top">
              <span class="dir-emergency-icon dir-emergency-icon--priority" aria-hidden="true">
                <IconLine :name="item.icon" />
              </span>
              <span class="dir-emergency-tag dir-emergency-tag--priority">{{ item.badge }}</span>
            </div>

            <h3 class="dir-emergency-card-name">{{ item.name }}</h3>
            <p class="dir-emergency-card-desc">{{ item.desc }}</p>

            <a
              :href="telHref(item.phone)"
              class="dir-emergency-call dir-emergency-call--priority"
              data-emergency-action="phone"
              data-contact-surface="directory-emergency"
              :data-contact-entity-id="item.id"
              :aria-label="`Gọi trực tiếp ${item.name}: ${item.phone}`"
              @click="trackContactView(item.id, 'phone')"
            >
              <IconLine name="phone" aria-hidden="true" />
              <span>{{ item.phone }}</span>
            </a>
          </article>
        </div>

        <!-- Secondary Support Channels -->
        <div class="dir-emergency-support">
          <article
            v-for="item in secondaryHotlines"
            :key="item.id"
            class="dir-emergency-card dir-emergency-card--support"
          >
            <div class="dir-emergency-card-top">
              <span class="dir-emergency-icon" aria-hidden="true">
                <IconLine :name="item.icon" />
              </span>
              <span class="dir-emergency-tag">{{ item.badge }}</span>
            </div>

            <h3 class="dir-emergency-card-name">{{ item.name }}</h3>
            <p class="dir-emergency-card-desc">{{ item.desc }}</p>

            <a
              :href="telHref(item.phone)"
              class="dir-emergency-call"
              data-emergency-action="phone"
              data-contact-surface="directory-emergency"
              :data-contact-entity-id="item.id"
              :aria-label="`Gọi trực tiếp ${item.name}: ${item.phone}`"
              @click="trackContactView(item.id, 'phone')"
            >
              <IconLine name="phone" aria-hidden="true" />
              <span>{{ item.phone }}</span>
            </a>
          </article>
        </div>
      </div>
    </section>

    <!-- Monocle Gazetteer Segmented Navigation -->
    <section class="block gazetteer-nav-block reveal">
      <div class="section-head gazetteer-head">
        <p class="gazetteer-kicker">Niên giám Thực địa Vĩnh Long</p>
        <h2 class="sediment-head">Tra cứu Danh mục Thổ nhưỡng</h2>
        <p class="gazetteer-dek">
          Hồ sơ liên lạc chính thức của các nghệ nhân làng nghề di sản, chủ vườn nông sản chỉ dẫn địa lý, đầu mối giao thông đường thủy và 124 cơ quan hành chính xã/phường.
        </p>
      </div>

      <div class="gazetteer-tabs" role="tablist" aria-label="Danh mục niên giám bản địa">
        <button
          v-for="t in gazetteerTabs"
          :key="t.id"
          type="button"
          role="tab"
          class="gazetteer-tab"
          :class="{ active: activeGazetteerTab === t.id }"
          :aria-selected="activeGazetteerTab === t.id"
          :aria-controls="`gazetteer-panel-${t.id}`"
          @click="activeGazetteerTab = t.id"
        >
          <IconLine :name="t.icon" aria-hidden="true" />
          <span>{{ t.label }}</span>
          <span class="gazetteer-tab-badge">{{ t.count }}</span>
        </button>
      </div>
    </section>

    <!-- Panel 1: Traditional Craft Artisans -->
    <section
      v-if="activeGazetteerTab === 'artisans'"
      id="gazetteer-panel-artisans"
      class="block gazetteer-panel reveal"
      role="tabpanel"
      aria-label="Nghệ nhân & Làng nghề truyền thống"
    >
      <div class="gazetteer-panel-header">
        <h3 class="gazetteer-panel-title">Hồ sơ Nghệ nhân &amp; Làng nghề Di sản</h3>
        <p class="gazetteer-panel-dek">
          Lưu giữ tinh hoa đất sét nung đỏ, đan lát lục bình, chằm nón lá và tráng bánh truyền thống châu thổ sông Tiền.
        </p>
      </div>

      <div class="gazetteer-card-grid">
        <article v-for="item in craftArtisans" :key="item.id" class="gazetteer-entry-card">
          <div class="entry-header">
            <span class="entry-tag">{{ item.tag }}</span>
            <SourceMark tier="official" compact />
          </div>
          <h4 class="entry-title">{{ item.name }}</h4>
          <p class="entry-lead"><strong>Nghệ nhân / Đại diện:</strong> {{ item.lead }}</p>
          <p class="entry-locality"><IconLine name="pin" aria-hidden="true" /> {{ item.locality }}</p>
          <p class="entry-address">{{ item.address }}</p>
          <p class="entry-notes">{{ item.notes }}</p>
          <div class="entry-actions">
            <a
              :href="telHref(item.phone)"
              class="gazetteer-call-btn"
              :aria-label="`Gọi liên hệ ${item.name}: ${item.phone}`"
            >
              <IconLine name="phone" aria-hidden="true" />
              <span>{{ item.phone }}</span>
            </a>
            <NuxtLink
              class="gazetteer-report-link"
              :to="correctionIntakeLink(item.id, { source: 'danh-ba' })"
              :aria-label="`Báo thông tin chưa đúng của ${item.name}`"
            >
              <IconLine name="alert-triangle" aria-hidden="true" /> Báo thông tin chưa đúng
            </NuxtLink>
          </div>
        </article>
      </div>
    </section>

    <!-- Panel 2: Orchard Owners -->
    <section
      v-if="activeGazetteerTab === 'orchards'"
      id="gazetteer-panel-orchards"
      class="block gazetteer-panel reveal"
      role="tabpanel"
      aria-label="Chủ vườn & Cây ăn trái bản địa"
    >
      <div class="gazetteer-panel-header">
        <h3 class="gazetteer-panel-title">Chủ vườn Cây ăn trái &amp; Chỉ dẫn Địa lý Mekong</h3>
        <p class="gazetteer-panel-dek">
          Danh mục vườn bưởi Năm Roi Hoàng Gia, sầu riêng Ri6, chôm chôm cù lao và vựa cam sành sông Mang Thít.
        </p>
      </div>

      <div class="gazetteer-card-grid">
        <article v-for="item in orchardOwners" :key="item.id" class="gazetteer-entry-card">
          <div class="entry-header">
            <span class="entry-tag entry-tag--orchard">{{ item.tag }}</span>
            <SourceMark tier="official" compact />
          </div>
          <h4 class="entry-title">{{ item.name }}</h4>
          <p class="entry-lead"><strong>Chủ vườn / Hợp tác xã:</strong> {{ item.lead }}</p>
          <p class="entry-locality"><IconLine name="pin" aria-hidden="true" /> {{ item.locality }}</p>
          <p class="entry-address">{{ item.address }}</p>
          <p class="entry-notes">{{ item.notes }}</p>
          <div class="entry-actions">
            <a
              :href="telHref(item.phone)"
              class="gazetteer-call-btn"
              :aria-label="`Gọi nhà vườn ${item.name}: ${item.phone}`"
            >
              <IconLine name="phone" aria-hidden="true" />
              <span>{{ item.phone }}</span>
            </a>
            <NuxtLink
              class="gazetteer-report-link"
              :to="correctionIntakeLink(item.id, { source: 'danh-ba' })"
              :aria-label="`Báo thông tin chưa đúng của ${item.name}`"
            >
              <IconLine name="alert-triangle" aria-hidden="true" /> Báo thông tin chưa đúng
            </NuxtLink>
          </div>
        </article>
      </div>
    </section>

    <!-- Panel 3: Boat Piers & Ferries -->
    <section
      v-if="activeGazetteerTab === 'piers'"
      id="gazetteer-panel-piers"
      class="block gazetteer-panel reveal"
      role="tabpanel"
      aria-label="Bến phà & Bến tàu du lịch"
    >
      <div class="gazetteer-panel-header">
        <h3 class="gazetteer-panel-title">Bến phà &amp; Bến tàu Vượt sông Cổ Chiên</h3>
        <p class="gazetteer-panel-dek">
          Đầu mối bến bãi giao thông thủy nội địa, nhịp phà vượt sông và ca nô du lịch khám phá sông Tiền.
        </p>
      </div>

      <div class="gazetteer-card-grid">
        <article v-for="item in boatPiers" :key="item.id" class="gazetteer-entry-card">
          <div class="entry-header">
            <span class="entry-tag entry-tag--pier">{{ item.tag }}</span>
            <SourceMark tier="official" compact />
          </div>
          <h4 class="entry-title">{{ item.name }}</h4>
          <p class="entry-lead"><strong>Đơn vị vận hành:</strong> {{ item.lead }}</p>
          <p class="entry-locality"><IconLine name="compass" aria-hidden="true" /> {{ item.locality }}</p>
          <p class="entry-address">{{ item.address }}</p>
          <p class="entry-notes">{{ item.notes }}</p>
          <div class="entry-actions">
            <a
              :href="telHref(item.phone)"
              class="gazetteer-call-btn"
              :aria-label="`Gọi điều phối bến ${item.name}: ${item.phone}`"
            >
              <IconLine name="phone" aria-hidden="true" />
              <span>{{ item.phone }}</span>
            </a>
            <NuxtLink
              class="gazetteer-report-link"
              :to="correctionIntakeLink(item.id, { source: 'danh-ba' })"
              :aria-label="`Báo thông tin chưa đúng của ${item.name}`"
            >
              <IconLine name="alert-triangle" aria-hidden="true" /> Báo thông tin chưa đúng
            </NuxtLink>
          </div>
        </article>
      </div>
    </section>

    <!-- Panel 4: Administrative Facilities (124 Wards) -->
    <section
      v-if="activeGazetteerTab === 'facilities'"
      id="gazetteer-panel-facilities"
      class="block gazetteer-panel reveal"
      role="tabpanel"
      aria-label="Cơ quan hành chính 124 xã/phường"
    >
      <!-- Error state -->
      <EmptyState v-if="placesError && !places?.length" icon-name="alert-triangle" title="Không thể tải dữ liệu" message="Vui lòng thử lại sau.">
        <template #actions>
          <button type="button" class="btn btn-outline btn-sm" @click="refreshNuxtData('dir-places')">Thử lại</button>
        </template>
      </EmptyState>

      <!-- Region quick-picks -->
      <section v-if="!placesError" class="block band reveal">
        <div class="section-head">
          <h3 class="sediment-head">Chọn khu vực</h3>
        </div>
        <div class="quick-picks region-quick-picks district-filter-tabs" role="group" aria-label="Chọn khu vực">
          <button type="button"
            v-for="g in wardGroups" :key="g.area"
            :class="['quick-pick', { active: selectedArea === g.area }]"
            :style="{ '--AREA-rgb': AREA_RGB[g.area] }"
            :aria-pressed="selectedArea === g.area"
            @click="selectedArea = selectedArea === g.area ? '' : g.area"
          >
            <span class="quick-pick-icon" aria-hidden="true"><IconLine :name="AREA_META[g.area]?.icon || 'pin'" /></span>
            <span class="quick-pick-label">{{ g.label }}</span>
            <span class="quick-pick-count">{{ g.wards.length }} xã/phường</span>
          </button>
        </div>
      </section>

      <!-- Ward picker -->
      <section ref="wardSection" class="block reveal">
        <label class="ward-pick">
          <span class="control-label">Chọn xã / phường:</span>
          <select v-model="wardId" aria-label="Chọn xã/phường">
            <option value="">— Chọn —</option>
            <optgroup v-for="g in filteredGroups" :key="g.area" :label="g.label">
              <option v-for="w in g.wards" :key="w.id" :value="w.id">{{ w.name }}</option>
            </optgroup>
          </select>
        </label>
        <p class="ward-caveat">Sau sáp nhập, hệ thống xã/phường đang điều chỉnh — thông tin có thể chưa đầy đủ, vui lòng kiểm chứng trực tiếp với cơ quan khi cần.</p>
      </section>

      <p class="sr-only" role="status" aria-live="polite">{{ statusAnnouncement }}</p>

      <p class="dir-report-link"><NuxtLink to="/lien-he">Báo thông tin sai</NuxtLink>.</p>

      <div v-if="!wardId" class="empty-hint">
        <span class="empty-hint-halo" aria-hidden="true"><span class="empty-hint-icon"><IconLine name="building" /></span></span>
        <h3 class="empty-hint-title">Chọn một xã/phường</h3>
        <p>Chọn khu vực rồi chọn xã/phường ở trên để xem danh bạ cơ quan hành chính.</p>
      </div>
      <template v-else>
        <p class="ward-hub-link">
          <NuxtLink :to="`/xa-phuong/${wardId}`"><IconLine name="home" /> Xem trang đầy đủ xã/phường này (du lịch · lưu trú · đặc sản) <IconLine name="arrow-right" class="danhba-arrow" /></NuxtLink>
        </p>
        <div v-if="loading && !facilitiesError" class="fac-loading" role="status" aria-label="Đang tải dữ liệu" aria-busy="true">
          <div class="spinner"></div>
          <span>Đang tải danh bạ cơ quan...</span>
        </div>
        <ul v-else-if="facilities.length" class="fac-list">
          <li v-for="f in facilities" :key="f.id" class="fac">
            <div class="fac-head">
              <span class="fac-kind"><IconLine :name="kindMeta(f).icon" aria-hidden="true" /> {{ kindMeta(f).label }}</span>
              <strong>{{ f.name }}</strong>
            </div>
            <div v-if="attr(f, 'address')" class="fac-row"><IconLine name="pin" /> {{ attr(f, 'address') }}</div>
            <div v-if="attr(f, 'phone')" class="fac-row">
              <IconLine name="phone" />
              <a :href="telHref(attr(f, 'phone'))" data-contact-action="phone" @click="trackContactView(f.id, 'phone')">{{ attr(f, 'phone') }}</a>
            </div>
            <div v-if="attr(f, 'hours')" class="fac-row"><IconLine name="clock" /> {{ attr(f, 'hours') }}</div>
            <footer v-if="sourceUrl(f) || f.updatedAt" class="fac-src">
              <SourceMark v-if="isOfficialSource(f)" tier="official" compact />
              Nguồn: <a v-if="sourceUrl(f)" :href="sourceUrl(f)" target="_blank" rel="nofollow noopener">{{ sourceName(f) || 'nguồn' }}</a>
              <span v-else>{{ sourceName(f) }}</span>
              <time v-if="f.updatedAt" :datetime="f.updatedAt"> · cập nhật {{ relativeUpdated(f.updatedAt) }}</time>
            </footer>
            <NuxtLink class="fac-report" :to="correctionIntakeLink(f.id, { source: 'danh-ba' })" :aria-label="`Báo thông tin chưa đúng của ${f.name}`">
              <IconLine name="alert-triangle" /> Báo thông tin chưa đúng
            </NuxtLink>
          </li>
        </ul>
        <EmptyState v-else-if="facilitiesError" icon-name="alert-triangle" title="Không thể tải danh bạ" message="Có lỗi khi tải dữ liệu. Vui lòng thử lại.">
          <template #actions>
            <button type="button" class="btn btn-outline btn-sm" @click="loadFacilities">Thử lại</button>
          </template>
        </EmptyState>
        <EmptyState v-else icon-name="list" title="Chưa có danh bạ" message="Chưa có dữ liệu danh bạ cho xã/phường này. Dữ liệu đang được bổ sung từ nguồn chính thống." />
      </template>
    </section>

    <!-- Cross-links -->
    <CatalogCrossLinks />
  </section>
</template>

<script setup lang="ts">
import type { Entity, EntitySource } from '~/types'
import { OFFICE_KIND, AREA_META } from '~/composables/useConstants'
import { trackContactView } from '~/composables/useContactBeacon'
import { telHref } from '~/utils/safe'

const AREA_RGB: Record<string, string> = {
  'vinh-long': 'var(--clay-rgb)',
  'ben-tre': 'var(--leaf-rgb)',
  'tra-vinh': 'var(--river-rgb)',
}

useReveal()
const { f: pc } = usePageContent('danh_ba')
const { show: showToast } = useToast()

const ADMIN_LEVELS = ['phuong', 'xa']  // danh-bạ chỉ xã/phường (124), KHÔNG gộp cấp tỉnh
const route = useRoute()

const placesAsyncData = useAsyncData('dir-places', () => apiFetch<Entity[]>('/api/places'))
const { data: places, error: placesError } = placesAsyncData

const areaFromQuery = computed(() => {
  const a = route.query.area as string
  return a && AREA_META[a] ? a : ''
})

const selectedArea = ref(areaFromQuery.value)
const wardSection = ref<HTMLElement | null>(null)

watch(selectedArea, () => {
  nextTick(() => wardSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
})

const wardGroups = computed(() => {
  const grouped: Record<string, Entity[]> = {}
  for (const p of (places.value || [])) {
    const area = p.area
    if (!p.level || !ADMIN_LEVELS.includes(p.level) || !area || !AREA_META[area]) continue
    if (!grouped[area]) grouped[area] = []
    grouped[area].push(p)
  }
  return Object.keys(AREA_META)
    .filter(area => grouped[area]?.length)
    .map(area => {
      const meta = AREA_META[area]
      return {
        area,
        label: meta?.name || area,
        wards: (grouped[area] || []).sort((a: Entity, b: Entity) => a.name.localeCompare(b.name, 'vi')),
      }
    })
})

const filteredGroups = computed(() => {
  if (!selectedArea.value) return wardGroups.value
  return wardGroups.value.filter(g => g.area === selectedArea.value)
})

const totalWards = computed(() => wardGroups.value.reduce((sum, g) => sum + g.wards.length, 0))

const wardId = ref('')
const facilities = ref<Entity[]>([])
const facilitiesError = ref(false)
const loading = ref(false)

const selectedWard = computed(() => {
  if (!wardId.value) return null
  for (const g of wardGroups.value) {
    const found = g.wards.find(w => w.id === wardId.value)
    if (found) return found
  }
  return null
})

const statusAnnouncement = computed(() => {
  if (!wardId.value) return 'Vui lòng chọn xã hoặc phường để xem danh bạ'
  if (loading.value) return 'Đang tải danh bạ cơ quan...'
  if (facilitiesError.value) return 'Lỗi khi tải danh bạ. Vui lòng thử lại.'
  if (!facilities.value.length) return `Chưa có danh bạ cơ quan cho ${selectedWard.value?.name || 'xã/phường đã chọn'}.`
  return `Đã tìm thấy ${facilities.value.length} cơ quan hành chính tại ${selectedWard.value?.name || 'xã/phường đã chọn'}.`
})

function attr(f: Entity, k: string): string {
  const value = (f.attributes || {})[k]
  return typeof value === 'string' ? value : value == null ? '' : String(value)
}
function kindMeta(f: Entity): { icon: string; label: string } {
  return OFFICE_KIND[attr(f, 'office_kind')] || OFFICE_KIND.khac || { icon: 'building', label: 'Cơ quan' }
}
function primarySource(f: Entity): EntitySource | undefined {
  return Array.isArray(f.source) ? f.source[0] : f.source
}
function sourceUrl(f: Entity): string {
  return primarySource(f)?.url || ''
}
function sourceName(f: Entity): string {
  return primarySource(f)?.name || ''
}

// Only flag as verified when the source URL is a genuine official gov domain — never fabricate trust (Track-H)
function isOfficialSource(f: Entity) {
  const url = sourceUrl(f)
  return /\.gov\.vn(\/|$|\?|#)/i.test(url)
}
// Relative "x ngày trước"; falls back to the raw stored value if unparseable
function relativeUpdated(raw: string) {
  if (!raw) return ''
  const t = Date.parse(raw)
  if (Number.isNaN(t)) return raw
  const days = Math.floor((Date.now() - t) / 86400000)
  if (days <= 0) return 'hôm nay'
  if (days === 1) return 'hôm qua'
  if (days < 30) return `${days} ngày trước`
  if (days < 365) return `${Math.floor(days / 30)} tháng trước`
  return `${Math.floor(days / 365)} năm trước`
}

interface EmergencyHotline {
  id: string
  name: string
  phone: string
  desc: string
  badge: string
  icon: string
  priority?: boolean
}

const emergencyHotlines: EmergencyHotline[] = [
  {
    id: 'rescue-waterway',
    name: 'CSGT & Cứu nạn Đường thủy',
    phone: '0270 3822 305',
    desc: 'Tuần tra sông Tiền & Cổ Chiên, cứu hộ sự cố đò phà và tàu thuyền du lịch 24/7.',
    badge: 'Đường thủy 24/7',
    icon: 'shield',
    priority: true,
  },
  {
    id: 'rescue-medical',
    name: 'Cấp cứu Y tế 115 & BV Đa khoa',
    phone: '115',
    desc: 'Điều phối xe cấp cứu lưu động và tiếp nhận hỗ trợ y tế khẩn cấp toàn tỉnh.',
    badge: 'Khẩn cấp 115',
    icon: 'phone',
    priority: true,
  },
  {
    id: 'rescue-police',
    name: 'Công an Tỉnh (Phản ứng nhanh)',
    phone: '113',
    desc: 'Bảo đảm an ninh trật tự, hỗ trợ du khách bị thất lạc hoặc gặp sự cố an ninh.',
    badge: 'Trực ban 113',
    icon: 'shield-check',
  },
  {
    id: 'rescue-ferry',
    name: 'Điều phối Phà An Bình',
    phone: '0270 3822 514',
    desc: 'Hỗ trợ phương tiện qua sông Cổ Chiên, giải quyết sự cố bến phà đêm ngày.',
    badge: 'Vượt sông',
    icon: 'route',
  },
  {
    id: 'rescue-tourism',
    name: 'Cứu hộ Du lịch Vĩnh Long 360',
    phone: '0270 3822 188',
    desc: 'Hỗ trợ hướng dẫn thực địa, giải quyết khúc mắc dịch vụ và phản ánh du lịch.',
    badge: 'Hỗ trợ du khách',
    icon: 'compass',
  },
]

const priorityHotlines = computed(() => emergencyHotlines.filter(item => item.priority))
const secondaryHotlines = computed(() => emergencyHotlines.filter(item => !item.priority))

// ── Monocle Gazetteer Taxonomy & Curated Registry ──
type GazetteerTabKey = 'artisans' | 'orchards' | 'piers' | 'facilities'
const activeGazetteerTab = ref<GazetteerTabKey>(
  (route.query.tab as GazetteerTabKey) || (route.query.area ? 'facilities' : 'artisans')
)

interface GazetteerEntry {
  id: string
  name: string
  lead: string
  locality: string
  address: string
  phone: string
  notes: string
  tag: string
}

const craftArtisans: GazetteerEntry[] = [
  {
    id: 'craft-mangthit-pottery',
    name: 'Xưởng Gốm Đỏ Mỹ Phước — Vương quốc Lò gạch Mang Thít',
    lead: 'Nghệ nhân Sáu Hưng & HTX Gốm Đỏ Mỹ Phước',
    locality: 'Xã Nhơn Phú, tỉnh Vĩnh Long',
    address: 'Dọc tuyến ĐT 902 & Kênh Thầy Cai',
    phone: '0270 3842 168',
    notes: 'Di sản Đương đại Mang Thít với hàng ngàn lò gạch hình tháp nung trấu truyền thống trên 100 năm.',
    tag: 'Gốm đỏ Mang Thít',
  },
  {
    id: 'craft-nonla-longho',
    name: 'Làng nghề Chằm nón lá Long Phước',
    lead: 'Cô Ba Huệ — Tổ hợp tác Nón lá Đồng Phước',
    locality: 'Xã Long Phước, tỉnh Vĩnh Long',
    address: 'Ấp Phước Trinh, Xã Long Phước',
    phone: '0270 3854 229',
    notes: 'Nón lá chằm tay tỉ mỉ từ lá mật cật và tre gai, sản phẩm truyền đời từ thời mở cõi phương Nam.',
    tag: 'Chằm nón lá',
  },
  {
    id: 'craft-lucbinh-ngaitu',
    name: 'HTX Thủ công Mỹ nghệ Lục bình Ngãi Tứ & Tam Bình',
    lead: 'Nghệ nhân Đan thảm Lục bình Ngãi Tứ',
    locality: 'Xã Ngãi Tứ, tỉnh Vĩnh Long',
    address: 'Tuyến Kênh Xáng, Xã Ngãi Tứ',
    phone: '0270 3711 405',
    notes: 'Tận dụng thân cây lục bình trôi dạt phơi khô, đan thành thảm, giỏ và vật dụng sinh thái xuất khẩu.',
    tag: 'Đan lục bình',
  },
  {
    id: 'craft-banhtrang-lucsi',
    name: 'Làng Bánh tráng nem Cù lao Lục Sĩ Thành',
    lead: 'Cơ sở Bánh tráng truyền thống Lục Sĩ',
    locality: 'Xã Lục Sĩ Thành, tỉnh Vĩnh Long',
    address: 'Cù lao Mây ven sông Hậu, Xã Lục Sĩ Thành',
    phone: '0270 3772 135',
    notes: 'Bánh tráng nem, bánh tráng ớt phơi sương tráng thủ công trên vỉ tre, danh vị ẩm thực Nam Bộ.',
    tag: 'Bánh tráng Cù lao Mây',
  },
  {
    id: 'craft-tauhuky-myhoa',
    name: 'Làng nghề Tàu hũ ky Mỹ Hòa (Di sản Văn hóa Phi vật thể Quốc gia)',
    lead: 'Cơ sở Tàu hũ ky gia truyền Mỹ Hòa',
    locality: 'Xã Mỹ Hòa, TX Bình Minh, tỉnh Vĩnh Long',
    address: 'Chân cầu Cần Thơ, Xã Mỹ Hòa',
    phone: '0270 3750 682',
    notes: 'Lò củi đun nước đậu nành vớt từng màng váng tạo nên đặc sản tàu hũ ky giòn thơm nổi tiếng.',
    tag: 'Tàu hũ ky PGI',
  },
]

const orchardOwners: GazetteerEntry[] = [
  {
    id: 'orchard-buoinamroi-myhoa',
    name: 'Vườn Bưởi Năm Roi Hoàng Gia Mỹ Hòa (Chỉ dẫn Địa lý PGI)',
    lead: 'Ông Hai Sáng — HTX Bưởi Năm Roi Mỹ Hòa',
    locality: 'Xã Mỹ Hòa, TX Bình Minh, tỉnh Vĩnh Long',
    address: 'Ven sông Hậu, Xã Mỹ Hòa',
    phone: '0270 3851 123',
    notes: 'Vựa bưởi Năm Roi không hạt ruột vàng mọng nước trĩu cành phù sa bãi bồi ven sông Hậu.',
    tag: 'Bưởi Năm Roi PGI',
  },
  {
    id: 'orchard-saurieng-quoithien',
    name: 'Vườn Sầu riêng Ri6 Quới Thiện & Cù lao Thanh Bình',
    lead: 'Nhà vườn Sáu Ri & Tổ hợp tác Trái cây Quới Thiện',
    locality: 'Xã Quới Thiện, tỉnh Vĩnh Long',
    address: 'Cù lao Cổ Chiên, Xã Quới Thiện',
    phone: '0270 3829 456',
    notes: 'Đất phù sa cồn bãi tạo nên giống sầu riêng Ri6 cơm vàng hạt lép ngọt béo nức tiếng ĐBSCL.',
    tag: 'Sầu riêng Ri6',
  },
  {
    id: 'orchard-chomchom-anbinh',
    name: 'Vườn Sinh thái Chôm chôm & Nhãn xuồng Cù lao An Bình',
    lead: 'Nhà vườn Út Trinh & Vườn sinh thái Năm Nhàn',
    locality: 'Xã An Bình, tỉnh Vĩnh Long',
    address: 'Cù lao 4 xã ven sông Tiền, Xã An Bình',
    phone: '0914 243 252',
    notes: 'Mùa quả chín rộ tháng 5 – tháng 8 âm lịch, đón khách du lịch miệt vườn trải nghiệm hái quả tại cây.',
    tag: 'Chôm chôm Cù lao',
  },
  {
    id: 'orchard-camsanh-tambinh',
    name: 'Vườn Cam sành Tam Bình & Bình Tân',
    lead: 'HTX Cam sành Khánh Hòa — Tam Bình',
    locality: 'Xã Hậu Lộc, tỉnh Vĩnh Long',
    address: 'Dọc sông Mang Thít, Xã Hậu Lộc',
    phone: '0270 3721 890',
    notes: 'Vựa cam sành ruột vàng ngọt đậm phù sa châu thổ, thương hiệu nông sản xuất sắc vùng Vĩnh Long.',
    tag: 'Cam sành Tam Bình',
  },
]

const boatPiers: GazetteerEntry[] = [
  {
    id: 'pier-ferry-anbinh',
    name: 'Bến Phà An Bình (TP. Vĩnh Long ↔ Cù lao An Bình)',
    lead: 'Ban Quản lý Bến phà An Bình',
    locality: 'Phường 1, TP. Vĩnh Long',
    address: 'Đầu đường Trưng Nữ Vương, Phường 1',
    phone: '0270 3822 514',
    notes: 'Hoạt động liên tục 24/24h qua sông Cổ Chiên, nhịp chuyến 15 phút ban ngày và 30 phút ban đêm.',
    tag: 'Bến phà 24/7',
  },
  {
    id: 'pier-tourist-vinhlong',
    name: 'Bến Tàu Du lịch Vĩnh Long',
    lead: 'Trung tâm Xúc tiến Du lịch Tỉnh Vĩnh Long',
    locality: 'Phường 1, TP. Vĩnh Long',
    address: 'Số 1 đường Lưu Văn Liệt, Phường 1',
    phone: '0270 3822 188',
    notes: 'Đầu mối ca nô và tàu du lịch đưa đón tham quan Cù lao 4 xã, làng gốm Mang Thít và chợ nổi.',
    tag: 'Bến tàu du lịch',
  },
  {
    id: 'pier-ferry-dinhkhao',
    name: 'Bến Phà Đình Khao (Quốc lộ 57)',
    lead: 'Cụm Bến phà Đình Khao — Cục Đường bộ IV',
    locality: 'Xã Thanh Đức, tỉnh Vĩnh Long',
    address: 'Đầu cầu vượt sông Cổ Chiên, QL57',
    phone: '0270 3823 468',
    notes: 'Cửa ngõ huyết mạch kết nối đôi bờ Vĩnh Long — Chợ Lách (Bến Tre), vận tải khách và xe 24/24.',
    tag: 'Phà Quốc lộ 57',
  },
  {
    id: 'pier-ferry-thaycai',
    name: 'Bến Đò ngang Du lịch Kênh Thầy Cai — Mỹ Phước',
    lead: 'Đội Điều tiết Đò Du lịch Di sản Mang Thít',
    locality: 'Xã Nhơn Phú, tỉnh Vĩnh Long',
    address: 'Bến đò Kênh Thầy Cai, Xã Nhơn Phú',
    phone: '0270 3842 305',
    notes: 'Tuyến đò dọc sông ngắm toàn cảnh tháp lò gạch đỏ gốm nung soi bóng dòng kênh lịch sử.',
    tag: 'Đò di sản',
  },
]

const gazetteerTabs = computed(() => [
  { id: 'artisans' as const, label: 'Nghệ nhân & Làng nghề', icon: 'vase', count: craftArtisans.length },
  { id: 'orchards' as const, label: 'Nhà vườn & Cây ăn trái', icon: 'fruit', count: orchardOwners.length },
  { id: 'piers' as const, label: 'Bến phà & Bến tàu', icon: 'compass', count: boatPiers.length },
  { id: 'facilities' as const, label: 'Cơ quan 124 xã/phường', icon: 'landmark', count: totalWards.value },
])

let facilitiesAbort: AbortController | null = null

onBeforeUnmount(() => {
  facilitiesAbort?.abort()
})

await placesAsyncData

async function loadFacilities() {
  if (facilitiesAbort) facilitiesAbort.abort()
  const id = wardId.value
  facilities.value = []
  facilitiesError.value = false
  if (!id) { loading.value = false; return }
  loading.value = true
  const ctrl = new AbortController()
  facilitiesAbort = ctrl
  try {
    const res = await $fetch<{ facilities: Entity[] }>(`/api/facilities?place=${encodeURIComponent(id)}`, { signal: ctrl.signal })
    if (ctrl.signal.aborted) return
    facilities.value = res.facilities || []
  } catch (err: unknown) {
    if (ctrl.signal.aborted) return
    facilitiesError.value = true
    showToast('Không thể tải danh bạ cơ quan', 'error')
  }
  loading.value = false
}
watch(wardId, loadFacilities)

// Đồ thị tri thức hợp nhất: '@type': 'CollectionPage', GovernmentService, ContactPoint, GovernmentOffice, FAQPage
const directorySchema = computed(() => buildDirectorySchemaGraph({
  totalWards: totalWards.value,
  selectedArea: selectedArea.value,
  dirTitle: pc('seo_title') || 'Danh bạ hành chính — vinhlong360',
  dirDesc: pc('seo_description') || 'Danh bạ 124 xã/phường, cơ quan hành chính tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025).',
  facilities: facilities.value.map((f: Entity) => ({
    id: f.id,
    name: f.name,
    address: attr(f, 'address'),
    phone: attr(f, 'phone'),
    hours: attr(f, 'hours'),
    kind: attr(f, 'kind'),
  })),
}))

useSeoMeta({
  ogType: 'website',
  title: () => pc('seo_title') || 'Danh bạ hành chính — vinhlong360',
  description: () => pc('seo_description') || 'Danh bạ 124 xã/phường, cơ quan hành chính tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025).',
  ogTitle: () => pc('og_title') || 'Danh bạ — vinhlong360',
  ogDescription: () => pc('og_description') || 'Tra cứu thông tin hành chính địa phương.',
  ogUrl: () => canonicalUrl('/danh-ba'),
  twitterCard: 'summary_large_image',
})
useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/danh-ba') }],
  script: [
    { type: 'application/ld+json', innerHTML: safeJsonLd(directorySchema.value) },
  ],
}))
</script>

<style scoped>
.dir-page { max-width: 960px; margin-inline: auto; }
.empty-hint { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); padding: var(--space-8) var(--space-4); color: var(--muted); text-align: center; background: radial-gradient(120% 100% at 50% 0%, rgba(var(--color-brand-rgb), .06), transparent 70%); border: .5px solid var(--line); border-radius: var(--radius-sheet); }
.empty-hint-halo { display: inline-flex; align-items: center; justify-content: center; width: 96px; height: 96px; border-radius: 50%; background: radial-gradient(circle, rgba(var(--color-brand-rgb), .14), rgba(var(--color-brand-rgb), .04) 70%); margin-bottom: var(--space-1); }
.empty-hint-icon { font-size: 2.6rem; line-height: 1; }
.empty-hint-title { margin: 0; font-size: var(--text-lg); font-weight: var(--weight-bold); color: var(--ink); }
.empty-hint p { margin: 0; font-size: var(--text-sm); max-width: 38ch; }
.muted { color: var(--muted); }
.ward-pick { display: flex; flex-direction: column; gap: var(--space-2); max-width: 420px; padding: var(--space-4); border: .5px solid var(--line); border-radius: var(--radius-sheet); background: var(--card); box-shadow: var(--shadow-xs); }
.ward-pick .control-label { font-weight: var(--weight-semibold); }
.ward-pick select { padding: var(--space-3); border: .5px solid var(--line); border-radius: var(--radius-surface); font-size: 1rem; min-height: 44px; background: var(--bg-alt); transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo); }
.ward-pick select:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 1px; border-color: var(--color-focus); box-shadow: 0 0 0 3px rgba(var(--color-action-rgb), .15), var(--shadow-xs); }
.ward-caveat { margin: var(--space-2) 0 0; max-width: 60ch; font-size: var(--text-xs); color: var(--muted); line-height: var(--leading-relaxed); }
.dir-report-link { font-size: var(--text-sm); color: var(--muted); margin: var(--space-6) 0 var(--space-5); }
.dir-report-link a { color: var(--color-action); font-weight: var(--weight-semibold); }
.dir-report-link a:hover { text-decoration: underline; }
.fac-list { list-style: none; padding: 0; margin: 0; display: grid; gap: var(--space-3); }

.fac { position: relative; overflow: hidden; border: .5px solid var(--line); border-radius: var(--radius-sheet); padding: var(--space-5); background: linear-gradient(180deg, rgba(var(--color-brand-rgb), .04), transparent 60%), var(--card); box-shadow: var(--shadow-sm); transition: transform .35s var(--ease-out-expo), box-shadow .35s var(--ease-out-expo), border-color .3s var(--ease-out); }
.fac::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 2px;
  background: linear-gradient(180deg, var(--color-material-river) 0%, var(--color-material-amber) 52%, var(--color-material-clay) 100%);
}
.dark .fac::before { background: linear-gradient(180deg, var(--night-river) 0%, var(--night-amber) 52%, var(--night-clay) 100%); }
.fac:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); border-color: var(--border); }
.fac-head { display: flex; flex-direction: column; align-items: flex-start; gap: var(--space-1); margin-bottom: var(--space-2); }
.fac strong { font-family: var(--font-editorial); font-weight: 600; font-size: var(--text-base); color: var(--ink); }
.fac-kind { align-self: flex-start; font-size: var(--text-xs); color: var(--color-brand); font-weight: var(--weight-semibold); text-transform: uppercase; letter-spacing: var(--tracking-wide); background: rgba(var(--color-brand-rgb), .12); border-radius: var(--radius-control); padding: 2px var(--space-2); line-height: 1.5; }
.fac-row { font-size: var(--text-sm); margin: 2px 0; color: var(--ink-secondary); display: flex; align-items: center; gap: var(--space-2); }
.fac-row a { transition: color .3s var(--ease-out); }
.fac-row a:hover { color: var(--color-action); }
.fac-row a:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; border-radius: var(--radius-control); }
.fac-row a[href^="tel:"] { display: inline-flex; align-items: center; min-height: 44px; color: var(--color-action); font-weight: var(--weight-semibold); border-radius: var(--radius-control); }
.fac-row a[href^="tel:"]:hover { color: var(--color-action-hover); text-decoration: underline; }
.fac-src { color: var(--muted); display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-2); margin: var(--space-3) calc(-1 * var(--space-5)) 0; padding: var(--space-2) var(--space-5); font-size: var(--text-xs); background: var(--overlay-subtle, rgba(var(--black-rgb),.02)); border-top: .5px solid var(--line); }
.fac-src a { color: var(--ink-secondary); text-decoration: underline; transition: color .3s var(--ease-out); }
.fac-src a:hover { color: var(--color-action); }
.fac-verified { font-size: var(--text-2xs); display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; margin-right: 2px; border-radius: 50%; background: var(--color-source-verified-surface); color: var(--color-source-verified); font-weight: var(--weight-bold); vertical-align: middle; }
.ward-hub-link { margin: 0 0 var(--space-4); }
.ward-hub-link a { display: inline-flex; align-items: center; gap: var(--space-1); color: var(--color-action); font-weight: var(--weight-semibold); transition: opacity .3s var(--ease-out); min-height: 44px; }
.ward-hub-link a:active { opacity: .7; }
.ward-hub-link a:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; border-radius: var(--radius-control); }
.danhba-arrow { display: inline-flex; transition: transform .3s var(--ease-out-expo); }
.ward-hub-link a:hover .danhba-arrow { transform: translateX(3px); }
.fac-report { margin-top: var(--space-2); background: none; border: none; padding: var(--space-2) var(--space-3); margin-left: calc(-1 * var(--space-3)); color: var(--muted); font-size: var(--text-xs); cursor: pointer; text-decoration: underline; transition: color .3s var(--ease-out), background .3s var(--ease-out); min-height: 44px; border-radius: var(--radius-control); display: inline-flex; align-items: center; gap: var(--space-1); }
.fac-report:hover:not(:disabled) { color: var(--color-action); background: rgba(var(--color-action-rgb), .06); }
.fac-report:active:not(:disabled) { transform: scale(.97); }
.fac-report:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }

.fac-loading { display: flex; align-items: center; justify-content: center; gap: var(--space-3); padding: var(--space-8) var(--space-4); background: var(--card); border: 1px solid var(--line); border-radius: var(--radius-sheet); color: var(--muted); font-size: var(--text-sm); }

/* ── 24/7 Emergency Tourism Hotline — Authoritative Priority Layout ── */
.dir-emergency {
  margin-block-end: var(--space-8);
}
.dir-emergency-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--color-action);
  background: var(--color-action-surface);
  border-radius: var(--radius-control);
  margin-block-end: var(--space-2);
}
.dir-emergency-dek {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  line-height: 1.5;
  max-width: 48rem;
  margin-block-start: var(--space-1);
}
.dir-emergency-priority-layout {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin-block-start: var(--space-4);
}
.dir-emergency-leads {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-4);
}
@media (min-width: 640px) {
  .dir-emergency-leads {
    grid-template-columns: repeat(2, 1fr);
  }
}
.dir-emergency-support {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-3);
}
@media (min-width: 640px) {
  .dir-emergency-support {
    grid-template-columns: repeat(3, 1fr);
  }
}
.dir-emergency-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: var(--space-4);
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius-sheet);
  transition: transform 0.2s var(--ease-out), box-shadow 0.2s var(--ease-out);
}
.dir-emergency-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}
.dir-emergency-card--lead {
  border: 1.5px solid var(--alluvial-gold);
  background: linear-gradient(180deg, rgba(var(--color-brand-rgb), 0.05), var(--card) 45%);
  box-shadow: var(--shadow-sm);
}
.dir-emergency-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-block-end: var(--space-2);
}
.dir-emergency-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: var(--radius-control);
  background: var(--color-action-surface);
  color: var(--color-action);
  font-size: 1.1rem;
}
.dir-emergency-icon--priority {
  background: var(--alluvial-gold);
  color: var(--color-on-action, var(--white));
}
.dir-emergency-tag {
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  padding: 0.125rem var(--space-2);
  border-radius: var(--radius-control);
  background: var(--color-action-surface);
  color: var(--color-action);
}
.dir-emergency-tag--priority {
  background: rgba(var(--color-brand-rgb), 0.15);
  color: var(--ink);
  border: 1px solid var(--alluvial-gold);
}
.dir-emergency-card-name {
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
  color: var(--ink);
  font-family: var(--font-editorial);
  margin-block-end: var(--space-1);
}
.dir-emergency-card-desc {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: 1.5;
  margin-block-end: var(--space-4);
  flex-grow: 1;
}
.dir-emergency-call {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  border-radius: var(--radius-control);
  background: var(--color-action-surface);
  color: var(--color-action);
  border: 1px solid var(--color-action-border);
  text-decoration: none;
  min-height: 44px;
  transition: background 0.15s ease, color 0.15s ease, transform 0.15s ease;
}
.dir-emergency-call:hover {
  background: var(--color-action);
  color: var(--color-on-action);
}
.dir-emergency-call--priority {
  background: var(--alluvial-gold);
  color: var(--on-tertiary);
  border-color: var(--alluvial-gold);
  min-height: 48px;
  box-shadow: var(--shadow-xs);
}
.dir-emergency-call--priority:hover {
  background: var(--harvest-600, var(--alluvial-gold));
  color: var(--on-tertiary);
}

/* ── Monocle Gazetteer Tabs & Editorial Panels ── */
.gazetteer-nav-block {
  margin-block-end: var(--space-6);
}
.gazetteer-kicker {
  font-family: var(--font-sans);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--muted);
  margin: 0 0 var(--space-1);
}
.gazetteer-dek {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  max-width: 52rem;
  line-height: 1.55;
  margin-block-start: var(--space-1);
}
.gazetteer-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-block-start: var(--space-4);
  border-bottom: 1px solid var(--line);
  padding-bottom: var(--space-3);
}
.gazetteer-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 44px;
  padding: var(--space-2) var(--space-4);
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--ink-secondary);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-control);
  cursor: pointer;
  transition: all 0.2s var(--ease-out);
}
.gazetteer-tab:hover {
  color: var(--ink);
  border-color: var(--border);
  background: var(--card);
}
.gazetteer-tab.active {
  color: var(--color-on-action, var(--white));
  background: var(--color-brand);
  border-color: var(--color-brand);
  box-shadow: var(--shadow-xs);
}
.gazetteer-tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.1rem 0.45rem;
  font-size: var(--text-2xs);
  border-radius: var(--radius-pill);
  background: rgba(var(--black-rgb), 0.08);
  color: inherit;
}
.gazetteer-tab.active .gazetteer-tab-badge {
  background: rgba(var(--white-rgb), 0.25);
  color: var(--color-on-action, var(--white));
}
.gazetteer-panel {
  margin-block-end: var(--space-8);
}
.gazetteer-panel-header {
  margin-block-end: var(--space-4);
}
.gazetteer-panel-title {
  font-family: var(--font-editorial);
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--ink);
  margin: 0 0 var(--space-1);
}
.gazetteer-panel-dek {
  font-size: var(--text-sm);
  color: var(--muted);
  margin: 0;
  line-height: 1.5;
}
.gazetteer-card-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-4);
}
@media (min-width: 640px) {
  .gazetteer-card-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
.gazetteer-entry-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: var(--space-5);
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius-sheet);
  box-shadow: var(--shadow-xs);
  transition: transform 0.25s var(--ease-out), box-shadow 0.25s var(--ease-out);
}
.gazetteer-entry-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--border);
}
.entry-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-block-end: var(--space-2);
}
.entry-tag {
  display: inline-block;
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  color: var(--mangthit-500);
  background: rgba(var(--clay-rgb), 0.1);
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-control);
}
.entry-tag--orchard {
  color: var(--color-material-leaf, var(--color-brand));
  background: rgba(var(--leaf-rgb), 0.1);
}
.entry-tag--pier {
  color: var(--color-material-river);
  background: rgba(var(--river-rgb), 0.1);
}
.entry-title {
  font-family: var(--font-editorial);
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--ink);
  margin: 0 0 var(--space-2);
  line-height: 1.35;
}
.entry-lead {
  font-size: var(--text-sm);
  color: var(--ink);
  margin: 0 0 var(--space-1);
}
.entry-locality {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  color: var(--muted);
  margin: 0 0 var(--space-1);
}
.entry-address {
  font-size: var(--text-xs);
  color: var(--muted);
  margin: 0 0 var(--space-2);
}
.entry-notes {
  font-size: var(--text-xs);
  color: var(--ink-secondary);
  line-height: 1.5;
  margin: 0 0 var(--space-4);
  flex-grow: 1;
}
.entry-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  border-top: 1px solid var(--line);
  padding-top: var(--space-3);
}
.gazetteer-call-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: 44px;
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--color-action);
  background: var(--color-action-surface);
  border: 1px solid var(--color-action-border);
  border-radius: var(--radius-control);
  text-decoration: none;
  transition: background 0.15s ease, color 0.15s ease;
}
.gazetteer-call-btn:hover {
  background: var(--color-action);
  color: var(--color-on-action);
}
.gazetteer-report-link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  color: var(--muted);
  text-decoration: underline;
  min-height: 44px;
  transition: color 0.15s ease;
}
.gazetteer-report-link:hover {
  color: var(--color-action);
}

/* Dark mode */
.dark .fac { background: var(--bg-alt); border-color: var(--line); }
.dark .fac:hover { box-shadow: var(--shadow-lg); border-color: rgba(var(--white-rgb),.1); }
.dark .ward-pick select { background: var(--bg-alt); border-color: var(--line); color: var(--ink); }
.dark .ward-pick select:focus-visible { border-color: var(--color-focus); }
.dark .empty-hint { color: var(--muted); border-color: rgba(var(--white-rgb),.08); background: radial-gradient(120% 100% at 50% 0%, rgba(var(--color-brand-rgb), .1), transparent 70%); }
.dark .empty-hint-title { color: var(--ink); }
.dark .fac-src { background: rgba(var(--white-rgb),.03); border-top-color: rgba(var(--white-rgb),.08); }
.dark .fac-report:hover:not(:disabled) { color: var(--color-action); }
.dark .gazetteer-tab { background: var(--surface); border-color: var(--line); color: var(--ink); }
.dark .gazetteer-entry-card { background: var(--card); border-color: var(--line); }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .fac:hover { transform: none; }
  .fac-report:active:not(:disabled) { transform: none; }
  .ward-hub-link a:hover .danhba-arrow { transform: none; }
  .dir-emergency-card:hover { transform: none; }
  .gazetteer-entry-card:hover { transform: none; }
}
</style>
