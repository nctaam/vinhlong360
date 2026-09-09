<template>
  <section class="page" data-color-system="tri-region-v1" data-page-recipe="planner">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lịch trình', to: '/lich-trinh' }, { label: 'Tạo lịch trình' }]" :json-ld="true" />

    <!-- Hero: chrome-only CE pass — masthead eyebrow + serif H1, builder/picker logic untouched -->
    <section class="catalog-hero cat-itinerary">
      <div class="catalog-hero-inner planner-hero-inner">
        <span class="dateline-eyebrow">Sổ tay hành trình · Tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025)</span>
        <h1>Tạo lịch trình</h1>
        <p>Lập kế hoạch chuyến đi của bạn — chọn điểm đến, sắp xếp thứ tự và lưu lại.</p>
      </div>
    </section>

    <!-- Guided flow indicator -->
    <PlannerSteps :stop-count="stops.length" />

    <div class="planner-layout">
      <!-- Left: Entity picker -->
      <div class="planner-picker">
        <!-- Source tabs: All vs Favorites -->
        <FilterChips
          :filters="sourceTabOptions"
          :model-value="[sourceTab]"
          single-select
          class="chip-row-spaced"
          aria-label="Nguồn"
          @update:model-value="v => sourceTab = v[0] || 'all'"
        />
        <div class="search-row search-row-spaced">
          <input v-model="searchQ" type="search" enterkeyhint="search" aria-label="Tìm điểm đến" placeholder="Tìm điểm đến, đặc sản, lưu trú…" />
        </div>
        <FilterChips
          v-if="sourceTab === 'all'"
          :filters="typeFilterOptions"
          :model-value="[typeFilter]"
          single-select
          class="chip-row-spaced"
          aria-label="Lọc theo loại"
          @update:model-value="v => typeFilter = v[0] || 'all'"
        />
        <div class="picker-list">
          <button
            v-for="e in pickerResults"
            :key="e.id"
            type="button"
            :class="['picker-item', { adding: addingId === e.id }]"
            @click="addStop(e)"
          >
            <IconLine class="picker-emoji" :name="getTypeMeta(e.type).icon" aria-hidden="true" />
            <div class="picker-info">
              <strong :title="e.name">{{ e.name }}</strong>
              <small>{{ e.place_name || '' }} · {{ getTypeMeta(e.type).label }}</small>
            </div>
            <span class="btn btn-sm btn-ghost" aria-hidden="true"><IconLine name="plus" /></span>
          </button>
          <p v-if="status === 'pending' && !pickerResults.length" class="empty picker-empty" data-picker-state="loading" role="status">Đang tải danh sách điểm đến…</p>
          <p v-else-if="fetchError" class="empty picker-empty"><IconLine name="alert-triangle" aria-hidden="true" /> Không thể tải danh sách. <button type="button" class="btn btn-outline btn-sm" @click="refreshPicker()">Thử lại</button></p>
          <div v-else-if="sourceTab === 'saved' && !favCount" class="premium-empty-state">
            <EmptyState icon-name="heart" title="Chưa có điểm đã lưu" message="Nhấn hình trái tim ở các điểm đến để lưu lại, rồi quay lại đây thêm vào lịch trình." />
          </div>
          <div v-else-if="!pickerResults.length" class="premium-empty-state">
            <EmptyState icon-name="search" title="Không tìm thấy" message="Thử từ khóa khác hoặc bỏ bộ lọc loại nhé.">
              <template #actions>
                <button type="button" class="btn btn-outline btn-sm" @click="resetPickerFilters">Xóa bộ lọc</button>
              </template>
            </EmptyState>
          </div>
        </div>
      </div>

      <!-- Right: Itinerary builder -->
      <div class="planner-builder">
        <div class="planner-timeline-column">
        <div class="builder-header">
          <div class="builder-title-wrap">
            <input v-model="planTitle" class="input builder-title" placeholder="Tên lịch trình (VD: 2 ngày khám phá Vĩnh Long)" aria-label="Tên lịch trình" maxlength="100" />
            <span v-if="planTitle.length > 80" class="title-counter" :class="{ warn: planTitle.length >= 95 }">{{ planTitle.length }}/100</span>
          </div>
        </div>

        <!-- Transport mode selector -->
        <div v-if="stops.length >= 2" class="transport-mode">
          <span class="tm-label">Phương tiện:</span>
          <button type="button" v-for="m in transportModes" :key="m.value" :class="['chip', { active: transportMode === m.value }]" :aria-pressed="transportMode === m.value" :disabled="optimizing" @click="transportMode = m.value">
            <IconLine :name="m.icon" aria-hidden="true" /> {{ m.label }}
          </button>
          <button
            v-if="stops.length >= 3 && optimizerEnabled"
            type="button"
            class="btn btn-sm btn-outline optimize-route-btn"
            :disabled="!canOptimizeRoute || optimizing"
            :title="optimizeRouteTitle"
            @click="optimizePlanRoute"
          >
            {{ optimizing ? 'Đang tối ưu…' : 'Tối ưu tuyến' }}
          </button>
          <div v-if="routeResult" class="route-total">
            {{ formatDistance(routeResult.totalDistance) }} · {{ formatDuration(routeResult.totalDuration) }}
          </div>
          <div v-if="routeLoading" class="route-total route-loading">Đang tính...</div>
          <div v-else-if="routeError" class="route-total" role="status"><IconLine name="alert-triangle" aria-hidden="true" /> Chưa tính được lộ trình (thử lại sau)</div>
        </div>
        <p
          v-if="optimizationMessage || (stops.length >= 3 && !canOptimizeRoute)"
          class="optimization-status"
          role="status"
        >
          {{ optimizationMessage || optimizeRouteTitle }}
        </p>

        <div v-if="stops.length >= 2" class="planner-budget" data-planner-budget>
          <label for="planner-time-budget">Ngân sách thời gian di chuyển</label>
          <div class="planner-budget__control">
            <input
              id="planner-time-budget"
              v-model.number="travelBudgetMinutes"
              class="input"
              type="number"
              min="1"
              step="5"
              placeholder="Không đặt giới hạn"
              @input="invalidatePlannerSchedule"
            />
            <span>phút</span>
          </div>
        </div>

        <div v-if="plannerFrictionNotices.length" class="planner-frictions" data-planner-frictions aria-label="Lưu ý lịch trình">
          <PlannerFrictionNotice
            v-for="notice in plannerFrictionNotices"
            :key="`${notice.code}-${notice.stopId || 'plan'}`"
            :code="notice.code"
            :severity="notice.severity"
            :reason="notice.reason"
            :recovery="notice.recovery"
            @recover="handleFrictionRecovery(notice)"
          />
        </div>

        <PlannerConflictDiff
          v-if="plannerRevisionConflict"
          ref="plannerConflictEl"
          :conflict="plannerRevisionConflict"
          :plan-title="planTitle"
          :differences="plannerConflictDifferences"
          :saving="saving"
          @choose="choosePlannerConflict"
        />

        <PlannerOptimizationPreview
          v-if="optimizationPreview"
          :before="optimizationPreview.before"
          :after="optimizationPreview.after"
          :changes="optimizationPreview.changes"
          :tradeoffs="optimizationPreview.tradeoffs"
          @confirm="confirmOptimizationPreview"
          @cancel="cancelOptimizationPreview"
        />

        <p v-if="stops.length >= 20" class="max-stops-warn" role="status">Đã đạt tối đa 20 điểm mỗi lịch trình.</p>
        <span class="sr-only" aria-live="polite" aria-atomic="true">{{ stopAnnounce }}</span>
        <div v-if="!stops.length" class="builder-empty">
          <EmptyState
            icon-name="compass"
            title="Chưa có điểm dừng nào"
            message="Chọn điểm đến từ danh sách bên trái hoặc tìm kiếm để bắt đầu tạo hành trình."
          />
        </div>

        <div v-else class="stop-list">
          <PlannerRiverTransitWarning :stops="stops" />
          <template v-for="(stop, idx) in stops" :key="stop.id + '-' + idx">
            <div
              class="stop-item"
              :class="{
                'is-dragging': draggedStopIndex === idx,
                'drag-over': dragOverStopIndex === idx && draggedStopIndex !== idx
              }"
              :style="{ animationDelay: `${idx * 50}ms` }"
              draggable="true"
              :data-stop-index="idx"
              @dragstart="beginStopDrag(idx, $event)"
              @dragover="handleStopDragOver(idx, $event)"
              @dragleave="handleStopDragLeave(idx)"
              @drop="dropStop(idx)"
              @dragend="endStopDrag"
            >
              <div class="stop-num">{{ idx + 1 }}</div>
              <div class="stop-connector" v-if="idx < stops.length - 1"></div>
              <div
                class="stop-card"
                tabindex="0"
                role="group"
                :aria-label="`Điểm dừng ${idx + 1}: ${stop.name}. Nhấn Alt+Lên hoặc Alt+Xuống để đổi vị trí.`"
                @keydown.alt.up.prevent="moveStop(idx, -1)"
                @keydown.alt.down.prevent="moveStop(idx, 1)"
              >
                <div class="stop-card-head">
                  <IconLine class="stop-emoji" :name="getTypeMeta(stop.type).icon" aria-hidden="true" />
                  <div class="stop-card-info">
                    <strong>{{ stop.name }}</strong>
                    <small>{{ stop.place_name || '' }} · {{ getTypeMeta(stop.type).label }}</small>
                    <span
                      v-if="stopAccessFact(stop)"
                      :class="['stop-access-fact', { 'is-restricted': isVehicleAccessRestricted(stop) }]"
                      :title="stopAccessFact(stop)!"
                    >
                      <IconLine :name="isVehicleAccessRestricted(stop) ? 'alert-triangle' : 'car'" aria-hidden="true" />
                      {{ stopAccessFact(stop) }}
                    </span>
                  </div>
                  <div class="stop-card-actions">
                    <button type="button" v-if="idx > 0" class="btn-icon-sm move" title="Lên (Alt+↑)" aria-label="Di chuyển lên" @click="moveStop(idx, -1)"><IconLine name="arrow-up" aria-hidden="true" /></button>
                    <button type="button" v-if="idx < stops.length - 1" class="btn-icon-sm move" title="Xuống (Alt+↓)" aria-label="Di chuyển xuống" @click="moveStop(idx, 1)"><IconLine name="arrow-down" aria-hidden="true" /></button>
                    <button type="button" class="btn-icon-sm danger" title="Xóa" aria-label="Xóa điểm dừng" @click="removeStop(idx)"><IconLine name="trash" aria-hidden="true" /></button>
                  </div>
                </div>
                <div class="stop-card-fields">
                  <input
                    v-model="stop.time"
                    class="input stop-time-input"
                    type="text"
                    aria-label="Thời gian dừng"
                    placeholder="VD: 8:00 - 10:00"
                    @input="invalidatePlannerSchedule"
                  />
                  <input
                    v-model="stop.notes"
                    class="input stop-note-input"
                    type="text"
                    aria-label="Ghi chú điểm dừng"
                    placeholder="Ghi chú (tùy chọn)"
                  />
                </div>
                <small v-if="scheduledIntervalForStop(stop)" class="scheduled-interval">
                  Lịch đề xuất: {{ scheduledIntervalForStop(stop) }}
                </small>
              </div>
            </div>
            <!-- Route leg info between stops -->
            <div v-if="idx < stops.length - 1 && plannerRouteLeg(idx)" class="route-leg">
              <div class="route-leg-line"></div>
              <div class="route-leg-info">
                <IconLine :name="transportMode === 'driving' ? 'car' : transportMode === 'cycling' ? 'bike' : 'foot'" aria-hidden="true" />
                <span>{{ formatDistance(plannerRouteLeg(idx)?.distance || 0) }} · {{ formatDuration(plannerRouteLeg(idx)?.duration || 0) }}</span>
              </div>
            </div>
          </template>
        </div>
        </div>

        <!-- Route map -->
        <PlannerRouteMap
          ref="plannerRouteMapRef"
          :stops="stops"
          :route-result="routeResult"
          :is-active="isPlannerLifecycleActive"
        />

        <button
          type="button"
          class="btn btn-outline planner-summary-toggle"
          :aria-expanded="summaryDrawerOpen"
          aria-controls="planner-summary-drawer"
          @click="summaryDrawerOpen = !summaryDrawerOpen"
        >
          Tóm tắt lịch trình
        </button>
        <div id="planner-summary-drawer" class="planner-summary-shell" :class="{ 'is-open': summaryDrawerOpen }">
          <PlannerSummary
            :stop-count="stops.length"
            :total-duration="plannerTotalDuration"
            :total-duration-partial="plannerTotalDurationPartial"
            :travel-duration="plannerTravelDuration"
            :warnings="plannerSummaryWarnings"
          />
        </div>

        <ActionDock class="planner-action-dock" data-planner-action-safe-area>
          <template #primary>
            <button type="button" :class="['btn', optimizationPreview ? 'btn-outline' : 'btn-primary', { 'save-pulse': savePulse }]" @click="savePlan" :disabled="!stops.length || saving">
              {{ saving ? 'Đang lưu…' : 'Lưu lịch trình' }}
            </button>
          </template>
          <button
            v-if="stops.length"
            type="button"
            class="btn btn-outline"
            @click="showPassModal = true"
          >
            <IconLine name="ticket" aria-hidden="true" /> Thẻ thực địa
          </button>
          <button type="button" class="btn btn-ghost" @click="clearPlan" :disabled="!stops.length || saving">Xóa tất cả</button>
        </ActionDock>

        <!-- Saved itineraries -->
        <PlannerSavedPlans
          :saved-plans="savedPlans"
          :saving="saving"
          :plan-busy="planBusy"
          :publish-blocked-by-conflict="publishBlockedByConflict"
          @load="loadPlan"
          @publish="publishPlan"
          @share="sharePlan"
          @delete="deletePlan"
        />

        <PlannerMobilePassModal
          v-model:open="showPassModal"
          :title="planTitle"
          :stops="stops"
        />
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import type { EntityListResponse } from '~/types/api'
import { usePublicApi } from '~/composables/usePublicApi'
import { TYPE_META, CARD_TYPES, getTypeMeta } from '~/composables/useConstants'
import { formatDistance, formatDuration, type TransportMode, type RouteResult } from '~/composables/useRouting'
import {
  enrichPlannerStopFromDetail,
  plannerMetadataForEntity,
  plannerMetadataForLoadedStop,
  plannerFreshnessEvidenceForEntity,
  type PlannerInputState,
  type PlannerScheduleMetadata,
} from '~/composables/useItineraryOptimization'
import PlannerFrictionNotice from '~/components/planner/PlannerFrictionNotice.vue'
import PlannerOptimizationPreview from '~/components/planner/PlannerOptimizationPreview.vue'
import PlannerSummary from '~/components/planner/PlannerSummary.vue'
import ActionDock from '~/components/public/ActionDock.vue'
import PlannerRiverTransitWarning from '~/components/planner/PlannerRiverTransitWarning.vue'
import PlannerMobilePassModal from '~/components/planner/PlannerMobilePassModal.vue'
import type { PlanStop, SavedPlan } from '~/utils/plannerSnapshots'
import { usePlannerStopOperations } from '~/composables/usePlannerStopOperations'
import { usePlannerServerPlans, LS_PLANS } from '~/composables/usePlannerServerPlans'
import { usePlannerRouteOptimization } from '~/composables/usePlannerRouteOptimization'
import { usePlannerDraftState } from '~/composables/usePlannerDraftState'
import { usePlannerFrictions } from '~/composables/usePlannerFrictions'

const route = useRoute()
const router = useRouter()
const showPassModal = ref(false)
const runtimeConfig = useRuntimeConfig()
const itineraryScheduleV2 = runtimeConfig.public.itineraryScheduleV2 === true

const plannerSchema = computed(() => ({
  '@context': 'https://schema.org',
  '@type': 'WebApplication',
  '@id': canonicalUrl('/tao-lich-trinh') + '#webapp',
  url: canonicalUrl('/tao-lich-trinh'),
  name: 'Tạo lịch trình khám phá — vinhlong360',
  applicationCategory: 'TravelApplication',
  operatingSystem: 'All',
  description: 'Công cụ lập kế hoạch và tối ưu lộ trình du lịch tự túc tại tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025).',
  publisher: {
    '@type': 'Organization',
    name: 'vinhlong360',
    url: 'https://vinhlong360.vn',
  },
}))

useSeoMeta({
  title: 'Tạo lịch trình — vinhlong360',
  description: 'Công cụ lập kế hoạch chuyến đi tự túc tại tỉnh Vĩnh Long hợp nhất (3 vùng trước 7-2025).',
  robots: 'noindex, nofollow',
  ogTitle: 'Tạo lịch trình — vinhlong360',
  ogDescription: 'Lập kế hoạch chuyến đi của bạn — chọn điểm đến, sắp xếp thứ tự và lưu lại.',
  ogUrl: () => canonicalUrl('/tao-lich-trinh'),
  twitterCard: 'summary_large_image',
})

useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/tao-lich-trinh') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: safeJsonLd(plannerSchema.value),
  }],
}))

const { favorites: favList, count: favCount } = useFavorites()
const { confirmDialog } = useConfirm()
const { show: showToast } = useToast()
const { user, isLoggedIn, authHeaders } = useAuth()
const { capabilityMode } = useFeature()
const optimizerEnabled = computed(() => capabilityMode('optimizer') === 'enhanced')
const revisionSafeSaveEnabled = optimizerEnabled
const journeyThread = useJourneyThread({
  ownerScope: () => isLoggedIn.value ? String(user.value?.id || 'authenticated') : 'guest',
})
const journeyOwner = computed(() => isLoggedIn.value ? String(user.value?.id || 'authenticated') : 'guest')

const planBusy = ref(-1)
const saving = ref(false)
const savePulse = ref(false)
const stopAnnounce = ref('')
let plannerLifecycleActive = true

function isPlannerLifecycleActive() {
  return plannerLifecycleActive
}

type PlannerType = (typeof CARD_TYPES)[number]
const TYPES = CARD_TYPES as readonly PlannerType[]
const typeChips = TYPES.map(t => ({ value: t, label: (TYPE_META[t] ?? getTypeMeta(t)).label }))

function isPlannerType(type: string): type is PlannerType {
  return (TYPES as readonly string[]).includes(type)
}

const transportModes = [
  { value: 'driving' as TransportMode, icon: 'car', label: 'Ô tô' },
  { value: 'cycling' as TransportMode, icon: 'bike', label: 'Xe đạp' },
  { value: 'foot' as TransportMode, icon: 'foot', label: 'Đi bộ' },
]

const sourceTab = ref(normalizeRouteParam(route.query.source as any) === 'saved' ? 'saved' : 'all')
const searchQ = ref('')
const typeFilter = ref('all')
const publicApi = usePublicApi()

const sourceTabOptions = computed(() => [
  { key: 'all', label: 'Tất cả' },
  { key: 'saved', label: 'Đã lưu', count: favCount.value },
])
const typeFilterOptions = computed(() => [
  { key: 'all', label: 'Tất cả' },
  ...typeChips.map(t => ({ key: t.value, label: t.label })),
])

function resetPickerFilters() {
  searchQ.value = ''
  typeFilter.value = 'all'
}

const planTitle = ref(normalizeRouteParam(route.query.title as any) || '')
const stops = ref<PlanStop[]>([])
const savedPlans = ref<SavedPlan[]>([])
const transportMode = ref<TransportMode>('driving')
const travelBudgetMinutes = ref<number | null>(null)
const summaryDrawerOpen = ref(false)
const MAX_STOPS = 20
let addingTimer: ReturnType<typeof setTimeout> | null = null
const addingId = ref<string | null>(null)

const plannerInputState = reactive<PlannerInputState>({ version: 0 })
const plannerScheduleMetadata = new WeakMap<object, PlannerScheduleMetadata>()
const plannerRouteMapRef = ref<{ updateMap: (route: RouteResult | null) => Promise<void>; retryMap: () => Promise<void> } | null>(null)

async function updateMap(result: RouteResult | null = routeResult.value) {
  await plannerRouteMapRef.value?.updateMap(result)
}

// ── Domain 1: Route Optimization Composable ───────────────────
const {
  routeResult,
  routeLoading,
  routeError,
  optimizing,
  optimizationMessage,
  optimizationPreview,
  suspendAutoRoute,
  currentRoutableStops,
  canOptimizeRoute,
  optimizeRouteTitle,
  visibleOpeningHourConflicts,
  invalidatePlannerSchedule,
  announceOptimization,
  optimizePlanRoute,
  confirmOptimizationPreview,
  cancelOptimizationPreview,
  computeRoute,
  autoRouteScheduler,
  scheduleRouteCalc,
} = usePlannerRouteOptimization({
  stops,
  transportMode,
  plannerScheduleMetadata,
  plannerInputState,
  itineraryScheduleV2,
  optimizerEnabled,
  isPlannerLifecycleActive,
  updateMap,
  showToast,
  stopAnnounce,
})

// ── Domain 2: Draft State & Offline Persistence Composable ────
const {
  plannerOnline,
  draftSavedAt,
  draftSource,
  localDraftRevision,
  localDirty,
  activeServerPlanId,
  baseServerRevision,
  plannerRevisionConflict,
  plannerDraftGeneration,
  plannerConflictEl,
  draftPersistenceReady,
  isDraftPersistenceReady,
  setDraftPersistenceReady,
  advancePlannerDraftGeneration,
  clearActiveServerPlan,
  persistPlannerDraft,
  restorePlannerDraft,
  updatePlannerConnectivity,
  choosePlannerConflict,
} = usePlannerDraftState({
  planTitle,
  stops,
  travelBudgetMinutes,
  plannerScheduleMetadata,
  plannerInputState,
  plannerMetadataForLoadedStop,
  invalidatePlannerSchedule,
  saving,
  acceptServerComparisonBase: (snapshot) => acceptServerComparisonBase(snapshot),
})

// ── Domain 3: Frictions & Recovery Composable ──────────────────
const {
  stalePlannerStops,
  plannerFrictionNotices,
  plannerSummaryWarnings,
  plannerConflictDifferences,
  handleFrictionRecovery,
} = usePlannerFrictions({
  stops,
  visibleOpeningHourConflicts,
  routeResult,
  travelBudgetMinutes,
  plannerOnline,
  localDraftRevision,
  draftSavedAt,
  draftSource,
  routeError,
  plannerRevisionConflict,
  refreshPlannerStopEvidence,
})

// ── Server Plans Composable ───────────────────────────────────
const {
  savePlan,
  loadPlan,
  deletePlan,
  publishPlan,
  sharePlan,
  publishBlockedByConflict,
  replaceSavedServerPlan,
  acceptServerComparisonBase,
  persistLocal,
} = usePlannerServerPlans({
  planTitle,
  stops,
  savedPlans,
  saving,
  planBusy,
  savePulse,
  activeServerPlanId,
  baseServerRevision,
  localDraftRevision,
  draftSource,
  localDirty,
  plannerRevisionConflict,
  plannerDraftGeneration,
  revisionSafeSaveEnabled,
  plannerConflictEl,
  plannerScheduleMetadata,
  routeResult,
  optimizationMessage,
  isDraftPersistenceReady,
  setDraftPersistenceReady,
  persistPlannerDraft,
  invalidatePlannerSchedule,
  refreshPlannerStopEvidence,
  plannerMetadataForLoadedStop,
  clearActiveServerPlan,
  advancePlannerDraftGeneration,
  showToast,
  confirmDialog,
  isLoggedIn,
  authHeaders,
})

// ── Entity Picker Data Fetching ───────────────────────────────
const plannerQueryKey = computed(() => [
  sourceTab.value,
  searchQ.value.trim(),
  typeFilter.value,
].join('|'))

const emptyEntityList = (): EntityListResponse => ({ total: 0, entities: [] })
type PickerDataCarrier = { readonly key: string; readonly data: EntityListResponse; readonly resolved: boolean }

const plannerAsyncData = useAsyncData<PickerDataCarrier>('planner-entities', async () => {
  const key = plannerQueryKey.value
  const value = sourceTab.value !== 'all'
    ? emptyEntityList()
    : await publicApi.listEntities({
        q: searchQ.value.trim() || undefined,
        type: typeFilter.value !== 'all' ? typeFilter.value : undefined,
        fields: 'minimal',
        limit: 50,
        offset: 0,
      })
  return { key, data: value, resolved: true }
}, {
  watch: [plannerQueryKey],
  default: () => ({ key: plannerQueryKey.value, data: emptyEntityList(), resolved: false }),
})
const { data, error: fetchError, status, refresh: refreshPicker } = plannerAsyncData

const lastSuccessfulPickerData = ref<PickerDataCarrier | null>(null)
watch(data, (value) => {
  if (value?.resolved && value.data.entities?.length) lastSuccessfulPickerData.value = value
}, { immediate: true })
const currentPickerData = computed(() => data.value?.resolved && data.value.key === plannerQueryKey.value ? data.value.data : null)
const retainedPickerData = computed(() => lastSuccessfulPickerData.value?.key === plannerQueryKey.value
  ? lastSuccessfulPickerData.value.data
  : null)
const effectivePickerData = computed(() => currentPickerData.value || (fetchError.value ? retainedPickerData.value : null))

const allEntities = computed(() => {
  const raw = effectivePickerData.value
  if (!raw) return []
  return (raw.entities || []).filter((e: Entity) => isPlannerType(e.type))
})

const pickerResults = computed(() => {
  let list: Entity[]

  if (sourceTab.value === 'saved') {
    list = favList.value.map(f => {
      const fav = f as any
      return {
        id: fav.id,
        name: fav.name,
        type: fav.type,
        place_name: fav.place_name,
        summary: fav.summary,
        coordinates: fav.coordinates,
        attributes: fav.attributes,
        source_freshness: fav.source_freshness,
        quality: fav.quality,
      }
    })
  } else {
    list = allEntities.value
  }

  if (sourceTab.value === 'saved' && searchQ.value.trim()) {
    const query = searchQ.value.toLowerCase()
    list = list.filter((e: Entity) =>
      (e.name || '').toLowerCase().includes(query) ||
      (e.summary || '').toLowerCase().includes(query) ||
      (e.place_name || '').toLowerCase().includes(query)
    )
  }

  return list.slice(0, 50)
})

// ── Stop Operations (Drag, Drop, Reorder, Durations) ──────────
const {
  draggedStopIndex,
  dragOverStopIndex,
  stopAccessFactsMap,
  beginStopDrag,
  handleStopDragOver,
  handleStopDragLeave,
  dropStop,
  endStopDrag,
  moveStop,
  removeStop,
  plannerRouteLeg,
  scheduledIntervalForStop,
  stopAccessFact,
  isVehicleAccessRestricted,
  plannerVisitDuration,
  plannerTravelDuration,
  plannerTotalDurationPartial,
  plannerTotalDuration,
} = usePlannerStopOperations({
  stops,
  allEntities,
  favList,
  transportMode,
  routeResult,
  currentRoutableStops,
  plannerScheduleMetadata,
  plannerInputState,
  invalidatePlannerSchedule,
  optimizationMessage,
  stopAnnounce,
})

function extractCoords(entity: Entity): [number, number] | null {
  return normalizeCoords(entity.coordinates)
}

async function refreshPlannerStopEvidence(stopId: string): Promise<boolean> {
  const stop = stops.value.find(candidate => candidate.id === stopId)
  if (!stop) return false
  try {
    const detail = await publicApi.getEntity(stopId)
    if (!stops.value.includes(stop)) return false
    const evidence = plannerFreshnessEvidenceForEntity(detail)
    if (!evidence || evidence.status === 'unknown') return false
    stop.sourceFreshness = evidence
    return true
  } catch {
    return false
  }
}

async function addStop(entity: Entity) {
  if (stops.value.length >= MAX_STOPS) {
    stopAnnounce.value = ''
    nextTick(() => { stopAnnounce.value = `Tối đa ${MAX_STOPS} điểm.` })
    return
  }
  invalidatePlannerSchedule()
  optimizationMessage.value = ''
  const sourceFreshness = plannerFreshnessEvidenceForEntity(entity)
  const stop = reactive<PlanStop>({
    id: entity.id,
    name: entity.name,
    type: entity.type,
    place_name: entity.place_name,
    coords: extractCoords(entity),
    time: '',
    notes: '',
    ...(sourceFreshness ? { sourceFreshness } : {}),
  })
  plannerScheduleMetadata.set(
    stop,
    plannerMetadataForEntity(entity.type, entity.attributes),
  )
  stops.value.push(stop)
  stopAnnounce.value = ''
  nextTick(() => { stopAnnounce.value = `Đã thêm ${entity.name}. ${stops.value.length} điểm.` })
  addingId.value = entity.id
  if (addingTimer) clearTimeout(addingTimer)
  addingTimer = setTimeout(() => { addingId.value = null }, 300)
  if (entity.attributes?.vehicle_access || entity.attributes?.road_access) {
    const access = String(entity.attributes.vehicle_access || entity.attributes?.road_access).trim()
    if (access) stopAccessFactsMap.set(entity.id, access)
  }
  if ((!stop.coords || !stop.sourceFreshness) && entity.id) {
    try {
      const detail = await publicApi.getEntity(entity.id)
      if (detail?.attributes?.vehicle_access || detail?.attributes?.road_access) {
        const access = String(detail.attributes.vehicle_access || detail.attributes?.road_access).trim()
        if (access) stopAccessFactsMap.set(stop.id, access)
      }
      await enrichPlannerStopFromDetail({
        stop,
        fetchDetail: () => Promise.resolve(detail),
        isCurrentStop: currentStop => stops.value.includes(currentStop),
        coordinatesFromDetail: detail => normalizeCoords(detail?.coordinates),
        metadataFromDetail: detail => plannerMetadataForEntity(
          detail?.type || stop.type,
          detail?.attributes,
        ),
        metadataByStop: plannerScheduleMetadata,
        invalidate: invalidatePlannerSchedule,
      })
      const evidence = plannerFreshnessEvidenceForEntity(detail)
      if (evidence) stop.sourceFreshness = evidence
    } catch { /* coords stay null */ }
  }
}

async function clearPlan() {
  if (saving.value) return
  if (stops.value.length && !await confirmDialog('Xóa toàn bộ điểm trong lịch trình đang tạo?', { danger: true, confirmText: 'Xóa' })) return
  if (saving.value) return
  invalidatePlannerSchedule()
  stops.value = []
  planTitle.value = ''
  routeResult.value = null
  optimizationMessage.value = ''
  draftSource.value = 'local'
  clearActiveServerPlan()
  journeyThread.clear()
}

// ── Query Parameter Auto-Add Handler ──────────────────────────
const pendingAddId = ref(normalizeRouteParam(route.query.add as any))
const autoAddedFromQuery = ref(false)

function clearPlannerAddQuery() {
  if (!route.query.add) return
  const query = { ...route.query }
  delete query.add
  router.replace({ query, hash: route.hash }).catch(() => {})
}

watch(() => route.query.add, (value) => {
  const next = normalizeRouteParam(value as any)
  if (next === pendingAddId.value) return
  pendingAddId.value = next
  autoAddedFromQuery.value = false
})

async function resolvePlannerEntity(id: string) {
  const cached = allEntities.value.find((e: Entity) => e.id === id)
  if (cached) return cached
  try {
    return await publicApi.getEntity(id)
  } catch {
    return null
  }
}

watch([allEntities, pendingAddId], async () => {
  if (autoAddedFromQuery.value || !pendingAddId.value) return
  const requestedId = pendingAddId.value
  autoAddedFromQuery.value = true
  const entity = await resolvePlannerEntity(requestedId)
  if (!entity) {
    showToast('Không tìm thấy điểm để thêm vào lịch trình', 'error')
    pendingAddId.value = ''
    clearPlannerAddQuery()
    return
  }
  if (stops.value.some(s => s.id === entity.id)) {
    showToast(`"${entity.name}" đã có trong lịch trình`, 'info')
    pendingAddId.value = ''
    clearPlannerAddQuery()
    return
  }
  await addStop(entity)
  pendingAddId.value = ''
  clearPlannerAddQuery()
  showToast(`Đã thêm "${entity.name}" vào lịch trình`, 'success')
}, { immediate: true })

const formatDate = formatDateVN

function advancePlannerJourney() {
  const restored = journeyThread.restore()
  journeyThread.pushIntent('plan', { currentPath: route.fullPath, returnPath: restored?.returnPath || '/du-lich' })
}

watch(journeyOwner, advancePlannerJourney)

onMounted(async () => {
  advancePlannerJourney()
  updatePlannerConnectivity()
  window.addEventListener('online', updatePlannerConnectivity)
  window.addEventListener('offline', updatePlannerConnectivity)
  restorePlannerDraft()
  await nextTick()
  setDraftPersistenceReady(true)
  let local: SavedPlan[] = []
  try {
    const raw = localStorage.getItem(LS_PLANS)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) local = parsed
    }
  } catch { /* ignore */ }

  if (isLoggedIn.value) {
    try {
      if (local.length) {
        const merged = await $fetch<{ plans: SavedPlan[] }>('/api/my-plans/merge', {
          method: 'POST', headers: authHeaders(), body: { plans: local },
        })
        savedPlans.value = merged.plans || []
        localStorage.removeItem(LS_PLANS)
      } else {
        const res = await $fetch<{ plans: SavedPlan[] }>('/api/my-plans', { headers: authHeaders() })
        savedPlans.value = res.plans || []
      }
    } catch {
      savedPlans.value = local
    }
  } else {
    savedPlans.value = local
  }
})

onBeforeUnmount(() => {
  plannerLifecycleActive = false
  window.removeEventListener('online', updatePlannerConnectivity)
  window.removeEventListener('offline', updatePlannerConnectivity)
  autoRouteScheduler.dispose()
  if (addingTimer) clearTimeout(addingTimer)
})

await plannerAsyncData
</script>

<style scoped>
/* ── Masthead: chrome-only CE consistency pass (builder/picker logic untouched) ──
   .dateline-eyebrow is defined locally (not global — same convention as
   tim-kiem.vue/ban-do.vue's scoped copies) per this unit's edit boundary. */
.planner-hero-inner { display: flex; flex-direction: column; align-items: flex-start; }
.planner-hero-inner .dateline-eyebrow { display: block; font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: var(--weight-bold); text-transform: uppercase; letter-spacing: var(--tracking-caps); color: var(--muted); margin: 0 0 var(--space-3); padding-bottom: var(--space-2); border-bottom: .5px solid var(--line); width: 100%; }
.dark .planner-hero-inner .dateline-eyebrow { border-bottom-color: var(--line); }

.builder-title-wrap { position: relative; flex: 1; min-width: 0; }
.title-counter { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); font-size: var(--text-xs); color: var(--muted); pointer-events: none; }
.title-counter.warn { color: var(--error); font-weight: var(--weight-semibold); }
.max-stops-warn { font-size: var(--text-sm); color: var(--warning); margin: var(--space-2) 0; }
.optimization-status {
  margin: calc(var(--space-2) * -1) 0 var(--space-4);
  color: var(--muted);
  font-size: var(--text-sm);
  line-height: 1.55;
}
.optimize-route-btn { white-space: nowrap; }
.stop-card-actions .btn-icon-sm { min-width: 44px; min-height: 44px; }
@media (pointer: coarse) { .stop-card-actions .btn-icon-sm { min-width: 44px; min-height: 44px; } }
.picker-list { max-height: 50vh; overflow-y: auto; scrollbar-width: thin; scrollbar-color: var(--line) transparent; }
.picker-list::-webkit-scrollbar { width: 6px; }
.picker-list::-webkit-scrollbar-track { background: transparent; }
.picker-list::-webkit-scrollbar-thumb { background: var(--line); border-radius: var(--radius-control); }
.picker-list::-webkit-scrollbar-thumb:hover { background: var(--muted); }
.picker-item {
  width: 100%; border: 0; background: transparent; color: inherit; font: inherit; text-align: left;
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-3); border-radius: var(--radius-control);
  cursor: pointer;
  transition: background .3s var(--ease-out), transform .35s var(--ease-out-expo);
}
.picker-item:hover { background: var(--bg-warm); }
.picker-item:active { transform: scale(.98); transition-duration: .08s; }
.picker-item:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; border-radius: var(--radius-surface); }
.picker-emoji { font-size: var(--text-lg); flex-shrink: 0; }
.picker-info { flex: 1; min-width: 0; }
.picker-info strong { display: block; font-size: var(--text-sm); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.picker-info small { color: var(--muted); font-size: var(--text-xs); }
.picker-empty { text-align: center; padding: var(--space-5); color: var(--muted); font-size: var(--text-sm); }
.builder-header { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: center; margin-bottom: var(--space-4); }
.builder-actions { display: flex; gap: var(--space-2); }
.stop-item { display: flex; gap: var(--space-3); position: relative; animation: stopIn .3s var(--ease-out) both; transition: opacity .2s var(--ease-out), transform .2s var(--ease-out); }
.stop-item.is-dragging { opacity: .45; transform: scale(.985); }
.stop-item.drag-over .stop-card { border-color: var(--color-action); box-shadow: 0 0 0 2px rgba(var(--color-action-rgb), .25), var(--shadow-sm); background: color-mix(in srgb, var(--color-action) 3%, var(--card)); }
@keyframes stopIn { from { opacity: 0; transform: translateY(6px); } }
.stop-num {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--color-brand); color: var(--color-on-action, var(--white));
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-sm); font-weight: var(--weight-bold);
  flex-shrink: 0; z-index: 1;
}
.stop-connector { position: absolute; left: 13px; top: 28px; bottom: -12px; width: 2px; background: var(--color-brand); opacity: .25; }
.stop-card { flex: 1; background: var(--card); border: .5px solid var(--line); border-radius: var(--radius-sheet); padding: var(--space-3) var(--space-4); margin-bottom: var(--space-3); transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo), transform .35s var(--ease-out-expo); }
.stop-card:hover { border-color: var(--border); box-shadow: var(--shadow-sm); }
.stop-card:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.stop-card-head { display: flex; align-items: center; gap: var(--space-3); }
.stop-emoji { font-size: var(--text-lg); }
.stop-card-info { flex: 1; min-width: 0; }
.stop-card-info strong { display: block; font-size: var(--text-sm); }
.stop-card-info small { color: var(--muted); font-size: var(--text-xs); }
.stop-access-fact { display: inline-flex; align-items: center; gap: var(--space-1); font-size: var(--text-2xs); color: var(--color-material-river); background: color-mix(in srgb, var(--color-material-river) 10%, transparent); border: 1px solid color-mix(in srgb, var(--color-material-river) 22%, transparent); border-radius: var(--radius-full); padding: 1px var(--space-2); margin-top: var(--space-1); max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.stop-access-fact.is-restricted { color: var(--color-warning); background: color-mix(in srgb, var(--color-warning) 12%, transparent); border-color: color-mix(in srgb, var(--color-warning) 30%, transparent); font-weight: var(--weight-semibold); }
.dark .stop-access-fact { color: var(--night-river); background: color-mix(in srgb, var(--night-river) 14%, transparent); border-color: color-mix(in srgb, var(--night-river) 25%, transparent); }
.dark .stop-access-fact.is-restricted { color: var(--night-amber); background: color-mix(in srgb, var(--night-amber) 16%, transparent); border-color: color-mix(in srgb, var(--night-amber) 32%, transparent); }
.scheduled-interval { display: block; margin-top: var(--space-2); color: var(--color-action); font-size: var(--text-xs); font-weight: var(--weight-semibold); }
.stop-card-actions { display: flex; gap: var(--space-1); }
.stop-list { margin-bottom: var(--space-4); }
.stop-card-actions button { min-height: 44px; min-width: 44px; display: inline-flex; align-items: center; justify-content: center; border-radius: var(--radius-control); transition: background .3s var(--ease-out), transform .35s var(--ease-out-expo); }
.stop-card-actions button:hover { background: var(--bg-warm); }
.stop-card-actions button:active { transform: scale(.88); transition-duration: .08s; }
.stop-card-actions button:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
.dark .picker-item:hover { background: var(--glass-light); }
.dark .stop-card { background: var(--card); border-color: var(--line); }
.dark .stop-card-actions button:hover { background: rgba(var(--white-rgb),.06); }
.dark .stop-card:hover { border-color: var(--border); }
.dark .stop-connector { background: var(--color-brand); }
.dark .picker-list::-webkit-scrollbar-thumb { background: var(--glass-medium); }
.dark .picker-list::-webkit-scrollbar-thumb:hover { background: rgba(var(--white-rgb),.2); }
.dark .route-leg-info { background: rgba(var(--white-rgb),.04); }
.dark .route-total { background: rgba(var(--white-rgb),.04); }
.dark .builder-title { background: var(--bg-alt); border-color: var(--line); color: var(--ink); }
.dark .stop-time-input, .dark .stop-note-input { background: var(--bg-alt); border-color: var(--line); color: var(--ink); }

/* ── Premium picker empty state surface ───────────────────── */
.premium-empty-state { background: radial-gradient(120% 90% at 50% -10%, rgba(var(--color-brand-rgb), .06), transparent 60%), var(--card); border: .5px solid var(--line); border-radius: var(--radius-sheet); padding: var(--space-8) var(--space-4); position: relative; overflow: hidden; }
.premium-empty-state::before { content: ""; position: absolute; inset: auto 0 0 0; height: 90px; opacity: .06; pointer-events: none; background-repeat: no-repeat; background-position: center bottom; background-size: 480px auto; background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22480%22%20height%3D%2290%22%20viewBox%3D%220%200%20480%2090%22%20fill%3D%22none%22%20stroke%3D%22%23586860%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%3E%3Cpath%20d%3D%22M-20%2030%20Q60%2014%20140%2030%20T300%2030%20T460%2030%22%2F%3E%3Cpath%20d%3D%22M-20%2060%20Q60%2044%20140%2060%20T300%2060%20T460%2060%22%2F%3E%3C%2Fsvg%3E"); }
.premium-empty-state > * { position: relative; z-index: 1; }
.dark .premium-empty-state { background: radial-gradient(120% 90% at 50% -10%, rgba(var(--color-brand-rgb), .08), transparent 60%), var(--card); }
.dark .premium-empty-state::before { opacity: .07; background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22480%22%20height%3D%2290%22%20viewBox%3D%220%200%20480%2090%22%20fill%3D%22none%22%20stroke%3D%22%23ffffff%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%3E%3Cpath%20d%3D%22M-20%2030%20Q60%2014%20140%2030%20T300%2030%20T460%2030%22%2F%3E%3Cpath%20d%3D%22M-20%2060%20Q60%2044%20140%2060%20T300%2060%20T460%2060%22%2F%3E%3C%2Fsvg%3E"); }

/* ── Picker item: brief highlight when added ──────────────── */
.picker-item.adding { background: rgba(var(--color-action-rgb), .12); transform: scale(1.02); }

/* ── Move buttons: draggable affordance on hover ──────────── */
.stop-card-actions button.move:hover { background: var(--bg-warm); border-radius: var(--radius-full); }

/* ── Save button: smooth deceleration feedback on save ─────── */
.save-pulse { animation: save-pop .24s var(--ease-out-expo); }
@keyframes save-pop { 0% { transform: scale(1); } 40% { transform: scale(.97); } 100% { transform: scale(1); } }

/* ── Route loading: pulsing text while computing ──────────── */
.route-loading { animation: route-loading-pulse 1.2s var(--ease-out) infinite; }
@keyframes route-loading-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .picker-item:hover, .picker-item:active, .picker-item.adding, .stop-card:hover { transform: none; }
  .stop-item { animation: none; }
  .save-pulse { animation: none; }
  .route-loading { animation: none; opacity: .7; }
}
</style>
