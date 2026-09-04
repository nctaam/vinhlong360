<template>
  <section class="page" data-page-recipe="planner">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Lịch trình', to: '/lich-trinh' }, { label: 'Tạo lịch trình' }]" />

    <!-- Hero: chrome-only CE pass — masthead eyebrow + serif H1, builder/picker logic untouched -->
    <section class="catalog-hero cat-itinerary">
      <div class="catalog-hero-inner planner-hero-inner">
        <span class="dateline-eyebrow">Sổ tay hành trình · Vĩnh Long · Bến Tre · Trà Vinh</span>
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
            <span class="btn btn-sm btn-ghost" aria-hidden="true">+</span>
          </button>
          <p v-if="status === 'pending' && !pickerResults.length" class="empty picker-empty" data-picker-state="loading" role="status">Đang tải danh sách điểm đến…</p>
          <p v-else-if="fetchError" class="empty picker-empty"><IconLine name="alert-triangle" aria-hidden="true" /> Không thể tải danh sách. <button type="button" class="btn btn-outline btn-sm" @click="refreshPicker()">Thử lại</button></p>
          <div v-else-if="sourceTab === 'saved' && !favCount" class="premium-empty-state">
            <EmptyState title="Chưa có điểm đã lưu" message="Nhấn hình trái tim ở các điểm đến để lưu lại, rồi quay lại đây thêm vào lịch trình." />
          </div>
          <div v-else-if="!pickerResults.length" class="premium-empty-state">
            <EmptyState title="Không tìm thấy" message="Thử từ khóa khác hoặc bỏ bộ lọc loại nhé." />
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
          <EmptyState message="Chưa có điểm nào. Chọn điểm đến từ danh sách bên trái để bắt đầu." />
        </div>

        <div v-else class="stop-list">
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
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import type { EntityListResponse } from '~/types/api'
import { usePublicApi } from '~/composables/usePublicApi'
import { TYPE_META, CARD_TYPES, getTypeMeta } from '~/composables/useConstants'
import { fetchRoute, fetchRouteTable, formatDistance, formatDuration, resolvePlannerRouteSurface, type TransportMode, type RouteResult } from '~/composables/useRouting'
import {
  applySchedulePlacements,
  collectRoutableStops,
  commitPlannerOptimizationResult,
  createSuspendedRouteScheduler,
  enrichPlannerStopFromDetail,
  formatScheduledInterval,
  invalidatePlannerInputs,
  mergeOptimizedStops,
  plannerMetadataForEntity,
  plannerMetadataForLoadedStop,
  plannerFreshnessEvidenceForEntity,
  isPlannerStopFreshnessStale,
  requestOptimizedOrder,
  routeLegForStopIndex,
  runPlannerOptimization,
  serializePlanStops,
  createPlannerOptimizationPreview,
  createPlannerDraftSnapshot,
  parsePlannerDraftSnapshot,
  projectPlannerFrictions,
  type PlannerInputState,
  type PlannerFrictionNotice as PlannerFriction,
  type PlannerOptimizationPreview as PlannerPreviewTransaction,
  type CurrentPlannerOptimizationResult,
  type RoutableStop,
  type PlannerScheduleMetadata,
  type PlannerStopFreshnessEvidence,
} from '~/composables/useItineraryOptimization'
import PlannerFrictionNotice from '~/components/planner/PlannerFrictionNotice.vue'
import PlannerOptimizationPreview from '~/components/planner/PlannerOptimizationPreview.vue'
import PlannerSummary from '~/components/planner/PlannerSummary.vue'
import ActionDock from '~/components/public/ActionDock.vue'
import {
  type PlanStop,
  type SavedPlan,
  type PlanSnapshot,
  type PlannerConflictDifference,
  type OpeningHourConflict,
  positiveRevision,
  plannerStopFromDraft,
  normalizePlanSnapshot,
  conflictSnapshot,
  diffPlannerPlanStops,
} from '~/utils/plannerSnapshots'
import {
  optimizationTradeoffs,
  openingHourConflictsFor,
} from '~/utils/plannerTradeoffs'
import {
  usePlannerServerPlans,
  LS_PLANS,
} from '~/composables/usePlannerServerPlans'

const route = useRoute()
const router = useRouter()
const runtimeConfig = useRuntimeConfig()
const itineraryScheduleV2 = runtimeConfig.public.itineraryScheduleV2 === true

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
const routeError = ref(false)   // OSRM không tính được route (≥2 điểm có toạ độ)
const planBusy = ref(-1)

type PlannerType = (typeof CARD_TYPES)[number]
const TYPES = CARD_TYPES as readonly PlannerType[]
const typeChips = TYPES.map((t) => {
  const meta = TYPE_META[t] ?? getTypeMeta(t)
  return {
    value: t,
    label: meta.label,
  }
})

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
const planTitle = ref('')
const stops = ref<PlanStop[]>([])
const savedPlans = ref<SavedPlan[]>([])
const transportMode = ref<TransportMode>('driving')
const routeResult = ref<RouteResult | null>(null)
const routeLoading = ref(false)
const optimizing = ref(false)
const optimizationMessage = ref('')
const summaryDrawerOpen = ref(false)
const optimizationPreview = ref<PlannerPreviewTransaction<PlanStop> | null>(null)
let pendingOptimization: {
  result: CurrentPlannerOptimizationResult<PlanStop>
  routed: RoutableStop<PlanStop>[]
} | null = null
const suspendAutoRoute = ref(false)
let latestAutoRouteRequest: number | null = null
const plannerInputState = reactive<PlannerInputState>({ version: 0 })
const plannerScheduleMetadata = new WeakMap<object, PlannerScheduleMetadata>()
const plannerRouteMapRef = ref<{ updateMap: (route: RouteResult | null) => Promise<void>; retryMap: () => Promise<void> } | null>(null)

async function updateMap(result: RouteResult | null = routeResult.value) {
  await plannerRouteMapRef.value?.updateMap(result)
}
const addingId = ref<string | null>(null)
let addingTimer: ReturnType<typeof setTimeout> | null = null
const savePulse = ref(false)
const saving = ref(false)
const stopAnnounce = ref('')
const draggedStopIndex = ref<number | null>(null)
const dragOverStopIndex = ref<number | null>(null)
const plannerOnline = ref(true)
const draftSavedAt = ref<string | null>(null)
const draftSource = ref<'local' | 'server'>('local')
const localDraftRevision = ref(0)
const localDirty = ref(false)
const activeServerPlanId = ref<string | null>(null)
const baseServerRevision = ref<number | null>(null)
const plannerRevisionConflict = ref<PlanSnapshot | null>(null)
const plannerDraftGeneration = ref(0)
const plannerConflictEl = ref<{ focus: () => void } | null>(null)
const travelBudgetMinutes = ref<number | null>(null)
const candidateOpeningHourConflicts = ref<OpeningHourConflict[]>([])
const confirmedOpeningHourConflicts = ref<OpeningHourConflict[]>([])
const MAX_STOPS = 20
const LS_DRAFT = 'vl360_planner_draft'
let savePulseTimer: ReturnType<typeof setTimeout> | null = null
let plannerLifecycleActive = true
let draftPersistenceReady = false

function isPlannerLifecycleActive() {
  return plannerLifecycleActive
}

const currentRoutableStops = computed(() => collectRoutableStops(stops.value))
const canOptimizeRoute = computed(() => {
  if (!optimizerEnabled.value) return false
  const routed = currentRoutableStops.value
  return routed.length >= 3
    && routed[0]?.originalIndex === 0
    && routed[routed.length - 1]?.originalIndex === stops.value.length - 1
})
const optimizeRouteTitle = computed(() => {
  if (!optimizerEnabled.value) return 'Tối ưu nâng cao đang tạm tắt; bạn vẫn có thể chỉnh và lưu lịch trình'
  if (stops.value.length < 3) return 'Cần ít nhất 3 điểm để tối ưu thứ tự'
  if (currentRoutableStops.value.length < 3) return 'Cần ít nhất 3 điểm có tọa độ'
  if (!canOptimizeRoute.value) return 'Điểm đầu và điểm cuối cần có tọa độ hợp lệ'
  return 'Giữ nguyên điểm đầu, điểm cuối và tối ưu các điểm ở giữa'
})

const stalePlannerStops = computed(() => stops.value
  .filter(stop => isPlannerStopFreshnessStale(stop.sourceFreshness))
  .map(stop => ({
    stopId: stop.id,
    label: stop.name || stop.id,
    status: stop.sourceFreshness?.status,
    updatedAt: stop.sourceFreshness?.updatedAt,
  })))
const visibleOpeningHourConflicts = computed(() => (
  optimizationPreview.value
    ? candidateOpeningHourConflicts.value
    : confirmedOpeningHourConflicts.value
))

const plannerFrictionNotices = computed<PlannerFriction[]>(() => projectPlannerFrictions({
  openingHourConflicts: visibleOpeningHourConflicts.value,
  travelMinutes: routeResult.value ? Math.round(routeResult.value.totalDuration / 60) : null,
  travelBudgetMinutes: travelBudgetMinutes.value,
  staleStops: stalePlannerStops.value,
  missingCoordinateStopIds: stops.value
    .filter(stop => !stop.coords)
    .map(stop => stop.name || stop.id),
  offlineDraft: plannerOnline.value ? false : {
    revision: localDraftRevision.value,
    savedAt: draftSavedAt.value,
    source: draftSource.value,
  },
  routeUnavailable: routeError.value,
}))

const plannerSummaryWarnings = computed(() => plannerFrictionNotices.value.map(notice => notice.reason))
const plannerConflictDifferences = computed<PlannerConflictDifference[]>(() => (
  plannerRevisionConflict.value
    ? diffPlannerPlanStops(stops.value, plannerRevisionConflict.value.stops)
    : []
))
const plannerVisitDuration = computed(() => {
  return stops.value.reduce((total, stop) => (
    total + ((plannerScheduleMetadata.get(stop)?.visitMinutes || 0) * 60)
  ), 0)
})
const plannerTravelDuration = computed<number | null>(() => {
  if (stops.value.length < 2) return 0
  return routeResult.value?.totalDuration ?? null
})
const plannerTotalDurationPartial = computed(() => (
  stops.value.length >= 2 && plannerTravelDuration.value === null
))
const plannerTotalDuration = computed<number | null>(() => {
  const visitDuration = plannerVisitDuration.value
  const travelDuration = plannerTravelDuration.value
  return travelDuration === null
    ? (visitDuration > 0 ? visitDuration : null)
    : travelDuration + visitDuration
})

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


// F4: dùng chuẩn chung normalizeCoords (validate + hoán đổi lat/lng đảo)
function extractCoords(entity: Entity): [number, number] | null {
  return normalizeCoords(entity.coordinates)
}

function clearPendingOptimizationPreview() {
  optimizationPreview.value = null
  pendingOptimization = null
  candidateOpeningHourConflicts.value = []
}

function advancePlannerDraftGeneration() {
  plannerDraftGeneration.value += 1
}

function clearActiveServerPlan() {
  advancePlannerDraftGeneration()
  activeServerPlanId.value = null
  baseServerRevision.value = null
  plannerRevisionConflict.value = null
}

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
  isDraftPersistenceReady: () => draftPersistenceReady,
  setDraftPersistenceReady: (ready: boolean) => { draftPersistenceReady = ready },
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

async function choosePlannerConflict(choice: 'local' | 'server' | 'manual') {
  if (saving.value) return
  if (choice === 'manual') {
    await nextTick()
    plannerConflictEl.value?.focus()
    return
  }
  const snapshot = plannerRevisionConflict.value
  if (!snapshot) return
  const persistenceWasReady = draftPersistenceReady
  draftPersistenceReady = false
  acceptServerComparisonBase(snapshot)
  if (choice === 'server') {
    invalidatePlannerSchedule()
    planTitle.value = snapshot.title
    stops.value = serializePlanStops(snapshot.stops) as PlanStop[]
    stops.value.forEach(stop => plannerScheduleMetadata.set(stop, plannerMetadataForLoadedStop(stop.type)))
    localDraftRevision.value += 1
    localDirty.value = false
  } else {
    localDirty.value = true
  }
  plannerRevisionConflict.value = null
  await nextTick()
  draftPersistenceReady = persistenceWasReady
  persistPlannerDraft()
}

function persistPlannerDraft() {
  if (!import.meta.client) return
  const savedAt = new Date().toISOString()
  draftSavedAt.value = savedAt
  try {
    localStorage.setItem(LS_DRAFT, JSON.stringify(createPlannerDraftSnapshot({
      title: planTitle.value,
      stops: stops.value,
      revision: localDraftRevision.value,
      savedAt,
      source: draftSource.value,
      travelBudgetMinutes: travelBudgetMinutes.value,
      serverPlanId: activeServerPlanId.value,
      serverRevision: baseServerRevision.value,
    })))
  } catch { /* local storage is an optional offline cache */ }
}

function restorePlannerDraft() {
  if (!import.meta.client || stops.value.length) return
  try {
    const raw = localStorage.getItem(LS_DRAFT)
    if (!raw) return
    const parsed = parsePlannerDraftSnapshot(JSON.parse(raw))
    if (!parsed?.stops.length) return
    stops.value = parsed.stops.map(stop => plannerStopFromDraft(stop))
    planTitle.value = parsed.title
    localDraftRevision.value = parsed.revision
    plannerInputState.version = localDraftRevision.value
    draftSavedAt.value = parsed.savedAt
    draftSource.value = parsed.source
    if (parsed.serverPlanId && positiveRevision(parsed.serverRevision)) {
      activeServerPlanId.value = parsed.serverPlanId
      baseServerRevision.value = parsed.serverRevision
    } else {
      activeServerPlanId.value = null
      baseServerRevision.value = null
    }
    travelBudgetMinutes.value = parsed.travelBudgetMinutes
    localDirty.value = true
    stops.value.forEach((stop) => {
      plannerScheduleMetadata.set(stop, plannerMetadataForLoadedStop(stop.type))
    })
  } catch { /* malformed draft is ignored without blocking the timeline */ }
}

function handleFrictionRecovery(notice: PlannerFriction) {
  if (!import.meta.client) return
  if (notice.recovery.action === 'edit-budget') {
    document.getElementById('planner-time-budget')?.focus()
    return
  }
  if (notice.recovery.action === 'edit-time') {
    document.querySelector<HTMLInputElement>('.stop-time-input')?.focus()
    return
  }
  if (notice.recovery.action === 'refresh-stop') {
    if (notice.stopId) void refreshPlannerStopEvidence(notice.stopId)
    return
  }
  if (notice.recovery.action === 'edit-stop' || notice.recovery.action === 'use-timeline') {
    document.querySelector<HTMLElement>('.stop-list, .planner-timeline-column')?.focus()
  }
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
    const access = String(entity.attributes.vehicle_access || entity.attributes.road_access).trim()
    if (access) stopAccessFactsMap.set(entity.id, access)
  }
  // P0-19: saved items (favorites) carry no coordinates → fetch detail so the
  // stop can be routed/mapped. Falls back silently (stop still listed) on error.
  if ((!stop.coords || !stop.sourceFreshness) && entity.id) {
    try {
      const detail = await publicApi.getEntity(entity.id)
      if (detail?.attributes?.vehicle_access || detail?.attributes?.road_access) {
        const access = String(detail.attributes.vehicle_access || detail.attributes.road_access).trim()
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

function removeStop(idx: number) {
  invalidatePlannerSchedule()
  const name = stops.value[idx]?.name || ''
  stops.value.splice(idx, 1)
  optimizationMessage.value = ''
  stopAnnounce.value = ''
  nextTick(() => { stopAnnounce.value = `Đã xóa ${name}. ${stops.value.length} điểm.` })
}

function moveStop(idx: number, dir: number) {
  const target = idx + dir
  if (target < 0 || target >= stops.value.length) return
  const temp = stops.value[idx]
  const targetStop = stops.value[target]
  if (!temp || !targetStop) return
  invalidatePlannerSchedule()
  stops.value[idx] = targetStop
  stops.value[target] = temp
  optimizationMessage.value = ''
  stopAnnounce.value = ''
  nextTick(() => { stopAnnounce.value = `${temp.name} chuyển sang vị trí ${target + 1}.` })
}

function beginStopDrag(index: number, event: DragEvent) {
  draggedStopIndex.value = index
  dragOverStopIndex.value = null
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(index))
  }
}

function handleStopDragOver(index: number, event: DragEvent) {
  event.preventDefault()
  if (draggedStopIndex.value !== null && draggedStopIndex.value !== index) {
    dragOverStopIndex.value = index
  }
}

function handleStopDragLeave(index: number) {
  if (dragOverStopIndex.value === index) {
    dragOverStopIndex.value = null
  }
}

function dropStop(targetIndex: number) {
  const sourceIndex = draggedStopIndex.value
  draggedStopIndex.value = null
  dragOverStopIndex.value = null
  if (sourceIndex === null || sourceIndex === targetIndex) return
  const stop = stops.value[sourceIndex]
  if (!stop) return
  invalidatePlannerSchedule()
  stops.value.splice(sourceIndex, 1)
  stops.value.splice(targetIndex, 0, stop)
  optimizationMessage.value = ''
  stopAnnounce.value = ''
  nextTick(() => { stopAnnounce.value = `${stop.name} chuyển sang vị trí ${targetIndex + 1}.` })
}

function endStopDrag() {
  draggedStopIndex.value = null
  dragOverStopIndex.value = null
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

function plannerRouteLeg(stopIndex: number) {
  return routeLegForStopIndex(
    stopIndex,
    currentRoutableStops.value,
    routeResult.value?.legs || [],
  )
}

function invalidatePlannerSchedule() {
  clearPendingOptimizationPreview()
  confirmedOpeningHourConflicts.value = []
  invalidatePlannerInputs(
    plannerInputState,
    stops.value,
    plannerScheduleMetadata,
  )
}

function scheduledIntervalForStop(stop: PlanStop): string {
  void plannerInputState.version
  return formatScheduledInterval(plannerScheduleMetadata.get(stop)?.placement)
}

const stopAccessFactsMap = reactive(new Map<string, string>())

function stopAccessFact(stop: PlanStop): string | null {
  if (stopAccessFactsMap.has(stop.id)) {
    return stopAccessFactsMap.get(stop.id) || null
  }
  const match = (allEntities.value as Entity[]).find(e => e.id === stop.id)
    || ((favList.value || []) as any[]).find(e => e.id === stop.id)
  const access = match?.attributes?.vehicle_access || match?.attributes?.road_access
  if (access && typeof access === 'string') {
    const trimmed = access.trim()
    stopAccessFactsMap.set(stop.id, trimmed)
    return trimmed
  }
  return null
}

function isVehicleAccessRestricted(stop: PlanStop): boolean {
  if (transportMode.value !== 'driving') return false
  const fact = (stopAccessFact(stop) || '').toLowerCase()
  return fact.includes('chỉ xe máy') || fact.includes('không vào được ô tô') || fact.includes('hẹp')
}

async function announceOptimization(message: string) {
  optimizationMessage.value = message
  if (!isPlannerLifecycleActive()) return
  stopAnnounce.value = ''
  await nextTick()
  if (isPlannerLifecycleActive()) stopAnnounce.value = message
}

async function optimizePlanRoute() {
  if (!canOptimizeRoute.value || optimizing.value) {
    optimizationMessage.value = optimizeRouteTitle.value
    return
  }

  const routed = currentRoutableStops.value
  optimizing.value = true
  suspendAutoRoute.value = true
  routeLoading.value = true
  routeError.value = false
  clearPendingOptimizationPreview()
  optimizationMessage.value = ''
  autoRouteScheduler.cancelScheduled()

  try {
    const plannerResult = await runPlannerOptimization({
      scheduleEnabled: itineraryScheduleV2,
      routed,
      metadataByStop: plannerScheduleMetadata,
      inputState: plannerInputState,
      mode: transportMode.value,
      fetchTable: (coordinates, mode) => fetchRouteTable(coordinates, mode),
      requestOptimization: (ordered, blockedEdges, schedule) => schedule
        ? requestOptimizedOrder(ordered, blockedEdges, schedule)
        : requestOptimizedOrder(ordered, blockedEdges),
      route: coordinates => fetchRoute(coordinates, transportMode.value),
    })
    if (!isPlannerLifecycleActive() || plannerResult.status === 'stale') return

    const candidateStops = mergeOptimizedStops(
      stops.value,
      routed,
      plannerResult.outcome.ordered.map(item => item.key),
    )
    pendingOptimization = { result: plannerResult, routed }
    candidateOpeningHourConflicts.value = openingHourConflictsFor(plannerResult, routed, plannerScheduleMetadata)
    optimizationPreview.value = await createPlannerOptimizationPreview(
      stops.value,
      candidateStops,
      { tradeoffs: optimizationTradeoffs(plannerResult, routed, stops.value.length, itineraryScheduleV2) },
    )
    await announceOptimization('Đã tạo bản xem trước. Thứ tự hiện tại chưa thay đổi.')
  } catch (error: unknown) {
    if (!isPlannerLifecycleActive()) return
    const message = extractErrorMessage(error, 'Không thể tối ưu tuyến lúc này')
    optimizationMessage.value = message
    showToast(message, 'error')
  } finally {
    if (!isPlannerLifecycleActive()) return
    routeLoading.value = false
    await nextTick()
    if (!isPlannerLifecycleActive()) return
    suspendAutoRoute.value = false
    autoRouteScheduler.resume()
    optimizing.value = false
  }
}

async function confirmOptimizationPreview() {
  const transaction = pendingOptimization
  if (!transaction || !optimizationPreview.value) return
  for (let attempt = 0; attempt < 3 && optimizing.value; attempt += 1) {
    await nextTick()
  }
  if (optimizing.value || !isPlannerLifecycleActive()) return
  optimizing.value = true
  suspendAutoRoute.value = true
  routeLoading.value = true
  autoRouteScheduler.cancelScheduled()
  const routeRequestBeforeCommit = latestAutoRouteRequest
  let reorderInputVersion: number | null = null
  let optimizerWatcherRequest: number | null = null

  try {
    const committedResult = await commitPlannerOptimizationResult(transaction.result, {
      isActive: isPlannerLifecycleActive,
      applyPlacements: (result) => {
        const schedule = result.outcome.optimization.schedule
        if (schedule) {
          applySchedulePlacements(
            transaction.routed,
            schedule.placements,
            plannerScheduleMetadata,
            plannerInputState,
          )
        } else if (itineraryScheduleV2) {
          applySchedulePlacements(transaction.routed, [], plannerScheduleMetadata, plannerInputState)
        }
      },
      reorderStops: (orderedKeys) => {
        reorderInputVersion = plannerInputState.version
        stops.value = mergeOptimizedStops(stops.value, transaction.routed, orderedKeys)
      },
      applyRoute: (route) => {
        routeResult.value = route
        routeError.value = resolvePlannerRouteSurface(transaction.routed.length, route).kind === 'fallback'
      },
      updateMap: async (route) => {
        await nextTick()
        if (!isPlannerLifecycleActive()) return
        if (
          reorderInputVersion !== null
          && plannerInputState.version === reorderInputVersion
          && latestAutoRouteRequest !== routeRequestBeforeCommit
        ) {
          optimizerWatcherRequest = latestAutoRouteRequest
        }
        await updateMap(route)
      },
    })
    if (!committedResult || !isPlannerLifecycleActive()) return
    autoRouteScheduler.discardPending(optimizerWatcherRequest)
    const message = optimizationTradeoffs(committedResult, transaction.routed, stops.value.length, itineraryScheduleV2).join(' ')
    confirmedOpeningHourConflicts.value = candidateOpeningHourConflicts.value.map(conflict => ({ ...conflict }))
    clearPendingOptimizationPreview()
    await announceOptimization(message || 'Đã áp dụng thứ tự đề xuất.')
  } finally {
    if (!isPlannerLifecycleActive()) return
    routeLoading.value = false
    suspendAutoRoute.value = false
    autoRouteScheduler.resume()
    optimizing.value = false
  }
}

async function cancelOptimizationPreview() {
  if (!optimizationPreview.value) return
  optimizationPreview.value.cancel()
  clearPendingOptimizationPreview()
  await announceOptimization('Đã giữ nguyên thứ tự hiện tại.')
}

async function computeRoute() {
  const coords = stops.value.map(s => s.coords).filter(Boolean) as [number, number][]
  if (coords.length < 2) {
    routeResult.value = null
    routeError.value = false
    updateMap(null)
    return
  }
  routeLoading.value = true
  routeError.value = false
  const result = await fetchRoute(coords, transportMode.value)
  routeResult.value = result
  routeError.value = resolvePlannerRouteSurface(coords.length, result).kind === 'fallback'
  routeLoading.value = false
  updateMap(result)
}

const autoRouteScheduler = createSuspendedRouteScheduler(
  computeRoute,
  () => suspendAutoRoute.value,
)

function scheduleRouteCalc() {
  latestAutoRouteRequest = autoRouteScheduler.request()
}


// Chỉ tính lại route khi TOẠ-ĐỘ/THỨ-TỰ stop hoặc phương-tiện đổi — KHÔNG khi sửa giờ/ghi-chú.
watch(
  () => [stops.value.map(s => (s.coords ? s.coords.join(',') : 'x')).join('|'), transportMode.value],
  scheduleRouteCalc,
)
watch(transportMode, invalidatePlannerSchedule)

watch([planTitle, stops, travelBudgetMinutes], () => {
  if (!draftPersistenceReady) return
  localDraftRevision.value += 1
  localDirty.value = true
  persistPlannerDraft()
}, { deep: true })

function updatePlannerConnectivity() {
  if (!import.meta.client) return
  plannerOnline.value = navigator.onLine
}

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
  draftPersistenceReady = true
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
      // có plan khách lưu trước khi đăng nhập → đẩy lên rồi xoá local
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
      savedPlans.value = local  // lỗi mạng → hiển thị tạm local
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
  if (savePulseTimer) clearTimeout(savePulseTimer)
})

await plannerAsyncData

useSeoMeta({
  title: 'Tạo lịch trình — vinhlong360',
  description: 'Lập kế hoạch chuyến đi Vĩnh Long: chọn điểm đến, sắp xếp thứ tự và lưu lịch trình cá nhân.',
})

useHead({
  link: [{ rel: 'canonical', href: canonicalUrl('/tao-lich-trinh') }],
  script: [{
    type: 'application/ld+json',
    innerHTML: JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'WebApplication',
      name: 'Công cụ tạo lịch trình vinhlong360',
      applicationCategory: 'TravelApplication',
      operatingSystem: 'Web',
      url: canonicalUrl('/tao-lich-trinh'),
    }),
  }],
})
</script>

<style scoped>
/* ── Masthead: chrome-only CE consistency pass (builder/picker logic untouched) ──
   .dateline-eyebrow is defined locally (not global — same convention as
   tim-kiem.vue/ban-do.vue's scoped copies) per this unit's edit boundary. */
.planner-hero-inner { display: flex; flex-direction: column; align-items: flex-start; }
.planner-hero-inner .dateline-eyebrow {
  display: block;
  font-family: var(--font-sans);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--muted);
  margin: 0 0 var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: .5px solid var(--line);
  width: 100%;
}
.dark .planner-hero-inner .dateline-eyebrow { border-bottom-color: var(--line); }

/* ── Section heads: WCAG 1.3.1 fix — these were h3.sediment-head with a
   scoped override reusing the shared tick recipe, but the page had no h2 at
   all, so h3 skipped straight from h1 with no h2 in between. Bumped the
   markup to h2.sediment-head, which now matches components.css's global
   `.sediment-head h2, h2.sediment-head` rule exactly (same gradient/spacing),
   so the scoped h3 override above is no longer needed and was removed. */

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
.picker-item:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; border-radius: var(--radius-surface); }
.picker-emoji { font-size: var(--text-lg); flex-shrink: 0; }
.picker-info { flex: 1; min-width: 0; }
.picker-info strong { display: block; font-size: var(--text-sm); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.picker-info small { color: var(--muted); font-size: var(--text-xs); }
.picker-empty { text-align: center; padding: var(--space-5); color: var(--muted); font-size: var(--text-sm); }
.builder-header { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: center; margin-bottom: var(--space-4); }
.builder-actions { display: flex; gap: var(--space-2); }
.stop-item {
  display: flex; gap: var(--space-3); position: relative; animation: stopIn .3s var(--ease-out) both;
  transition: opacity .2s var(--ease-out), transform .2s var(--ease-out);
}
.stop-item.is-dragging {
  opacity: .45;
  transform: scale(.985);
}
.stop-item.drag-over .stop-card {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(var(--primary-rgb), .25), var(--shadow-sm);
  background: color-mix(in srgb, var(--primary) 3%, var(--card));
}
@keyframes stopIn { from { opacity: 0; transform: translateY(6px); } }
.stop-num {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--primary); color: var(--text-on-dark, var(--white));
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-sm); font-weight: var(--weight-bold);
  flex-shrink: 0; z-index: 1;
}
.stop-connector { position: absolute; left: 13px; top: 28px; bottom: -12px; width: 2px; background: var(--primary); opacity: .25; }
.stop-card {
  flex: 1; background: var(--card); border: .5px solid var(--line);
  border-radius: var(--radius-sheet); padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-3);
  transition: border-color .3s var(--ease-out), box-shadow .35s var(--ease-out-expo), transform .35s var(--ease-out-expo);
}
.stop-card:hover { border-color: var(--border); box-shadow: var(--shadow-sm); }
.stop-card:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.stop-card-head { display: flex; align-items: center; gap: var(--space-3); }
.stop-emoji { font-size: var(--text-lg); }
.stop-card-info { flex: 1; min-width: 0; }
.stop-card-info strong { display: block; font-size: var(--text-sm); }
.stop-card-info small { color: var(--muted); font-size: var(--text-xs); }
.stop-access-fact {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-2xs);
  color: var(--color-material-river);
  background: color-mix(in srgb, var(--color-material-river) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--color-material-river) 22%, transparent);
  border-radius: var(--radius-full);
  padding: 1px var(--space-2);
  margin-top: var(--space-1);
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.stop-access-fact.is-restricted {
  color: var(--color-warning);
  background: color-mix(in srgb, var(--color-warning) 12%, transparent);
  border-color: color-mix(in srgb, var(--color-warning) 30%, transparent);
  font-weight: var(--weight-semibold);
}
.dark .stop-access-fact {
  color: var(--night-river);
  background: color-mix(in srgb, var(--night-river) 14%, transparent);
  border-color: color-mix(in srgb, var(--night-river) 25%, transparent);
}
.dark .stop-access-fact.is-restricted {
  color: var(--night-amber);
  background: color-mix(in srgb, var(--night-amber) 16%, transparent);
  border-color: color-mix(in srgb, var(--night-amber) 32%, transparent);
}
.scheduled-interval { display: block; margin-top: var(--space-2); color: var(--primary-fg); font-size: var(--text-xs); font-weight: var(--weight-semibold); }
.stop-card-actions { display: flex; gap: var(--space-1); }
.stop-list { margin-bottom: var(--space-4); }
.stop-card-actions button { min-height: 44px; min-width: 44px; display: inline-flex; align-items: center; justify-content: center; border-radius: var(--radius-control); transition: background .3s var(--ease-out), transform .35s var(--ease-out-expo); }
.stop-card-actions button:hover { background: var(--bg-warm); }
.stop-card-actions button:active { transform: scale(.88); transition-duration: .08s; }
.stop-card-actions button:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.dark .picker-item:hover { background: var(--glass-light); }
.dark .stop-card { background: var(--card); border-color: var(--line); }
.dark .stop-card-actions button:hover { background: rgba(var(--white-rgb),.06); }
.dark .stop-card:hover { border-color: var(--border); }
.dark .stop-connector { background: var(--primary-fg); }
.dark .picker-list::-webkit-scrollbar-thumb { background: var(--glass-medium); }
.dark .picker-list::-webkit-scrollbar-thumb:hover { background: rgba(var(--white-rgb),.2); }
.dark .route-leg-info { background: rgba(var(--white-rgb),.04); }
.dark .route-total { background: rgba(var(--white-rgb),.04); }
.dark .builder-title { background: var(--bg-alt); border-color: var(--line); color: var(--ink); }
.dark .stop-time-input, .dark .stop-note-input { background: var(--bg-alt); border-color: var(--line); color: var(--ink); }

/* ── Premium picker empty state surface ───────────────────── */
.premium-empty-state {
  background:
    radial-gradient(120% 90% at 50% -10%, rgba(var(--primary-rgb), .06), transparent 60%),
    var(--card);
  border: .5px solid var(--line);
  border-radius: var(--radius-sheet);
  padding: var(--space-8) var(--space-4);
  position: relative; overflow: hidden;
}
.premium-empty-state::before {
  content: ""; position: absolute; inset: auto 0 0 0; height: 90px;
  opacity: .06; pointer-events: none;
  background-repeat: no-repeat; background-position: center bottom; background-size: 480px auto;
  background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22480%22%20height%3D%2290%22%20viewBox%3D%220%200%20480%2090%22%20fill%3D%22none%22%20stroke%3D%22%23586860%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%3E%3Cpath%20d%3D%22M-20%2030%20Q60%2014%20140%2030%20T300%2030%20T460%2030%22%2F%3E%3Cpath%20d%3D%22M-20%2060%20Q60%2044%20140%2060%20T300%2060%20T460%2060%22%2F%3E%3C%2Fsvg%3E");
}
.premium-empty-state > * { position: relative; z-index: 1; }
.dark .premium-empty-state {
  background:
    radial-gradient(120% 90% at 50% -10%, rgba(var(--primary-rgb), .08), transparent 60%),
    var(--card);
}
.dark .premium-empty-state::before {
  opacity: .07;
  background-image: url("data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22480%22%20height%3D%2290%22%20viewBox%3D%220%200%20480%2090%22%20fill%3D%22none%22%20stroke%3D%22%23ffffff%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%3E%3Cpath%20d%3D%22M-20%2030%20Q60%2014%20140%2030%20T300%2030%20T460%2030%22%2F%3E%3Cpath%20d%3D%22M-20%2060%20Q60%2044%20140%2060%20T300%2060%20T460%2060%22%2F%3E%3C%2Fsvg%3E");
}

/* ── Picker item: brief highlight when added ──────────────── */
.picker-item.adding { background: rgba(var(--primary-rgb), .12); transform: scale(1.02); }

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
  .picker-item:hover { transform: none; }
  .picker-item:active { transform: none; }
  .picker-item.adding { transform: none; }
  .stop-card:hover { transform: none; }
  .stop-item { animation: none; }
  .save-pulse { animation: none; }
  .route-loading { animation: none; opacity: .7; }
}
</style>
