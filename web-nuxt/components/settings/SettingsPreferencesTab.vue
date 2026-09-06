<template>
  <div
    v-show="active"
    id="khu-vuc-de-xuat"
    class="settings-card card preference-card sediment-head"
    role="tabpanel"
    aria-labelledby="tab-khu-vuc-de-xuat"
    :hidden="!active"
    :tabindex="active ? 0 : -1"
  >
    <div class="preference-heading">
      <div>
        <p class="preference-kicker">GỢI Ý THEO CÁCH CỦA BẠN</p>
        <h2>Khu vực &amp; đề xuất</h2>
      </div>
      <span class="preference-revision">Bạn kiểm soát</span>
    </div>
    <p class="sf-hint preference-intro">Xem hệ thống đang dùng khu vực nào, chọn sở thích chủ động và kiểm soát các tín hiệu dùng để sắp xếp nội dung.</p>

    <div v-if="!preferenceOnline" class="preference-banner preference-offline" role="status" aria-live="polite">
      <div>
        <strong>Đang ngoại tuyến</strong>
        <p>Ảnh chụp thiết lập gần nhất vẫn đọc được. Các thay đổi được khóa để tránh ghi đè khi chưa kết nối.</p>
      </div>
      <button type="button" class="btn btn-secondary btn-sm" data-action="retry-preferences" @click="retryPreferences">Thử kết nối lại</button>
    </div>

    <div v-if="preferenceConflict" class="preference-banner preference-conflict" role="alert">
      <div>
        <strong>Dữ liệu trên máy chủ đã thay đổi</strong>
        <p>Đang hiển thị ảnh chụp mới từ máy chủ. Hãy xem lại trước khi thử lưu thay đổi của bạn.</p>
      </div>
      <button type="button" class="btn btn-secondary btn-sm" data-action="retry-conflict" :disabled="preferenceBusy" @click="retryPreferenceConflict">Thử lưu lại</button>
    </div>

    <div
      v-if="preferenceView.location_reconfirm_required"
      class="preference-banner preference-reconfirm"
      data-state="location-reconfirm"
      role="status"
      aria-live="polite"
    >
      <div>
        <strong>Chọn lại khu vực ưu tiên</strong>
        <p>Khu vực trước đây cần được chọn lại để bảo vệ quyền riêng tư. Sở thích và dữ liệu đã lưu của bạn vẫn được giữ nguyên.</p>
      </div>
      <button type="button" class="btn btn-primary btn-sm" data-action="choose-region-again" @click="focusManualRegionChoices">
        Chọn lại khu vực
      </button>
    </div>
    <p v-if="preferenceNotice" class="preference-notice" role="status" aria-live="polite">{{ preferenceNotice }}</p>
    <div v-if="preferences.loading.value && !preferenceBusy" class="sf-loading" role="status" aria-label="Đang tải thiết lập đề xuất"><div class="spinner spinner-sm"></div> Đang tải thiết lập...</div>

    <dl class="preference-summary">
      <div>
        <dt>Khu vực ưu tiên</dt>
        <dd>{{ preferenceRegionLabel }}</dd>
      </div>
      <div>
        <dt>Nguồn khu vực</dt>
        <dd>{{ preferenceSourceLabel }}</dd>
      </div>
      <div>
        <dt>Độ chính xác công bố</dt>
        <dd>{{ preferenceAccuracyLabel }}</dd>
      </div>
      <div>
        <dt>Nhóm tuổi nội dung</dt>
        <dd>{{ preferenceAgeBandLabel }}</dd>
      </div>
    </dl>

    <p class="preference-state-copy" :data-consent-state="preferenceView.location_consent_state">{{ preferenceLocationStateCopy }}</p>

    <section class="preference-section" aria-labelledby="preference-region-title">
      <div class="preference-section-head">
        <div>
          <h3 id="preference-region-title">Đổi khu vực thủ công</h3>
          <p>Chọn thủ công không cần bật vị trí và vẫn được dùng khi vị trí đang tắt.</p>
        </div>
      </div>
      <div ref="manualRegionGroup" class="preference-options" role="group" aria-label="Chọn khu vực ưu tiên" data-region-group="manual" tabindex="-1">
        <button
          v-for="region in PREFERENCE_REGIONS"
          :key="region.id || 'all'"
          type="button"
          class="preference-option"
          :class="{ selected: preferenceView.region_id === region.id && preferenceView.location_source === 'manual' }"
          :data-region="region.id || 'all'"
          :aria-pressed="preferenceView.region_id === region.id && preferenceView.location_source === 'manual'"
          :disabled="preferenceMutationsDisabled"
          @click="setPreferenceRegion(region)"
        >{{ region.label }}</button>
      </div>
    </section>

    <section class="preference-section" aria-labelledby="preference-interest-title">
      <div class="preference-section-head">
        <div>
          <h3 id="preference-interest-title">Sở thích chủ động</h3>
          <p>Những lựa chọn này được ưu tiên hơn tín hiệu suy đoán.</p>
        </div>
      </div>
      <div v-if="preferenceView.explicit_interests.length" class="preference-chips" aria-label="Sở thích đã chọn">
        <span v-for="interest in preferenceView.explicit_interests" :key="interest" class="preference-chip">{{ preferenceInterestLabel(interest) }}</span>
      </div>
      <p v-else class="sf-hint">Chưa chọn sở thích chủ động.</p>
    </section>

    <section class="preference-section preference-controls" aria-label="Kiểm soát đề xuất">
      <label class="notif-pref-item preference-control">
        <div class="notif-pref-info">
          <span class="preference-control-mark" aria-hidden="true">VỊ TRÍ</span>
          <div>
            <strong>Cho phép vị trí gần đúng</strong>
            <span class="sf-hint">Bật hoặc dừng tín hiệu GPS/IP. Khu vực thủ công không bị xóa.</span>
          </div>
        </div>
        <input
          type="checkbox"
          class="toggle"
          data-action="toggle-location"
          aria-label="Cho phép vị trí gần đúng"
          :checked="preferenceView.location_enabled"
          :disabled="preferenceMutationsDisabled"
          @change="togglePreferenceLocation"
        />
      </label>
      <label class="notif-pref-item preference-control">
        <div class="notif-pref-info">
          <span class="preference-control-mark" aria-hidden="true">GỢI Ý</span>
          <div>
            <strong>Cá nhân hóa theo hoạt động</strong>
            <span class="sf-hint">Khi tắt, chỉ dùng khu vực thủ công và nội dung công khai.</span>
          </div>
        </div>
        <input
          type="checkbox"
          class="toggle"
          data-action="toggle-personalization"
          aria-label="Cá nhân hóa theo hoạt động"
          :checked="preferenceView.personalization_enabled"
          :disabled="preferenceMutationsDisabled"
          @change="togglePreferencePersonalization"
        />
      </label>
    </section>

    <div class="preference-reset">
      <div>
        <strong>Đặt lại đề xuất</strong>
        <p class="sf-hint">Bỏ ảnh hưởng của tín hiệu cũ khỏi xếp hạng; không xóa mục đã lưu, lượt xem hay hồ sơ.</p>
      </div>
      <button
        type="button"
        class="btn btn-secondary"
        data-action="reset-recommendations"
        aria-label="Đặt lại đề xuất"
        :disabled="preferenceMutationsDisabled"
        @click="resetPreferenceRecommendations"
      >{{ preferenceBusy ? 'Đang xử lý...' : 'Đặt lại đề xuất' }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { PreferencePatch, PreferenceRegionChoice, PreferenceSnapshot } from '~/types/personalization'
import { usePersonalizationPreferences } from '~/composables/usePersonalizationPreferences'

const props = defineProps<{
  active: boolean
}>()

const preferences = usePersonalizationPreferences()
const PREFERENCE_REGIONS = [
  { id: 'province-vl', label: 'Vĩnh Long', scope: 'province' },
  { id: 'province-bt', label: 'Bến Tre', scope: 'province' },
  { id: 'province-tv', label: 'Trà Vinh', scope: 'province' },
  { id: null, label: 'Toàn tỉnh', scope: 'all' },
] satisfies PreferenceRegionChoice[]

const PREFERENCE_INTEREST_LABELS: Record<string, string> = {
  food: 'Ẩm thực',
  local_products: 'Đặc sản & OCOP',
  garden: 'Miệt vườn',
  culture: 'Văn hóa',
  craft: 'Làng nghề',
  stay: 'Lưu trú',
}

type PreferenceOperation = {
  values: PreferencePatch
  optimistic: Partial<PreferenceSnapshot>
  successMessage: string
}

function clonePreferenceSnapshot(value: PreferenceSnapshot): PreferenceSnapshot {
  return { ...value, explicit_interests: [...value.explicit_interests] }
}

const preferenceView = ref<PreferenceSnapshot>(clonePreferenceSnapshot(preferences.snapshot.value))
const preferenceOnline = ref(true)
const preferenceBusy = ref(false)
const preferenceConflict = ref(false)
const preferenceNotice = ref('')
const manualRegionGroup = ref<HTMLElement | null>(null)
let preferenceConflictOperation: PreferenceOperation | null = null

watch(preferences.snapshot, (value) => {
  if (!preferenceBusy.value) preferenceView.value = clonePreferenceSnapshot(value)
}, { deep: true, immediate: true })

watch(() => props.active, (isActive) => {
  if (isActive) loadPreferences()
}, { immediate: true })

const preferenceMutationsDisabled = computed(() => !preferenceOnline.value || preferenceBusy.value || preferences.loading.value)
const preferenceRegionLabel = computed(() => {
  if (preferenceView.value.region_scope === 'all') return 'Toàn tỉnh'
  return preferenceView.value.region_label || 'Chưa xác định'
})
const preferenceSourceLabel = computed(() => {
  const source = preferenceView.value.location_source
  if (source === 'manual') return 'Bạn chọn thủ công'
  if (source === 'gps') return 'GPS gần đúng'
  if (source === 'ip') return 'IP gần đúng'
  return 'Chưa xác định'
})
const preferenceAccuracyLabel = computed(() => {
  const accuracy = preferenceView.value.location_accuracy
  if (accuracy === 'ward') return 'Cấp xã/phường'
  if (accuracy === 'district') return 'Cấp huyện'
  if (accuracy === 'province') return 'Cấp tỉnh'
  return 'Chưa xác định'
})
const preferenceAgeBandLabel = computed(() => {
  const labels: Record<string, string> = {
    under_18: 'Dưới 18',
    '18_24': '18–24',
    '25_34': '25–34',
    '35_49': '35–49',
    '50_plus': 'Từ 50 trở lên',
    unknown: 'Chưa xác định',
  }
  return labels[preferenceView.value.derived_age_band || 'unknown'] || labels.unknown
})
const preferenceLocationStateCopy = computed(() => {
  const consent = preferenceView.value.location_consent_state
  if (consent === 'off') return 'Vị trí đang tắt; khu vực thủ công vẫn được dùng cho nội dung gần bạn.'
  if (consent === 'denied') return 'Quyền vị trí đã bị từ chối. Bạn vẫn có thể chọn khu vực thủ công.'
  if (consent === 'expired') return 'Quyền vị trí đã hết hạn. Cần xác nhận lại trước khi dùng GPS hoặc IP.'
  if (consent === 'unknown') return 'Chưa có quyết định về vị trí. Hệ thống không tự yêu cầu GPS.'
  if (preferenceView.value.location_source === 'gps') return 'GPS gần đúng đã được xác nhận; tọa độ không được giữ trong thiết lập.'
  if (preferenceView.value.location_source === 'ip') return 'Đang dùng khu vực gần đúng từ IP, không hiển thị hoặc lưu địa chỉ IP tại đây.'
  if (preferenceView.value.location_source === 'manual') return 'Khu vực này do bạn chọn thủ công và không cần quyền vị trí.'
  return 'Chưa xác định được khu vực; nội dung công khai vẫn hoạt động.'
})

function preferenceInterestLabel(key: string) {
  return PREFERENCE_INTEREST_LABELS[key] || key
}

function focusManualRegionChoices() {
  const target = manualRegionGroup.value
  if (!target) return
  target.focus({ preventScroll: true })
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  target.scrollIntoView({ block: 'center', behavior: reduced ? 'auto' : 'smooth' })
}

function syncPreferenceOnline() {
  preferenceOnline.value = !import.meta.client || navigator.onLine
}

async function loadPreferences() {
  syncPreferenceOnline()
  if (!preferenceOnline.value) return
  const loaded = await preferences.refresh()
  preferenceView.value = clonePreferenceSnapshot(preferences.snapshot.value)
  if (loaded) {
    preferenceNotice.value = ''
    preferenceConflict.value = false
    preferenceConflictOperation = null
  } else {
    preferenceNotice.value = preferences.error.value || 'Không thể tải thiết lập đề xuất lúc này.'
  }
}

async function retryPreferences() {
  syncPreferenceOnline()
  if (!preferenceOnline.value) return
  await loadPreferences()
}

async function applyPreferenceOperation(operation: PreferenceOperation) {
  syncPreferenceOnline()
  if (!preferenceOnline.value || preferenceBusy.value) return
  const before = clonePreferenceSnapshot(preferenceView.value)
  preferenceBusy.value = true
  preferenceNotice.value = ''
  preferenceConflict.value = false
  preferenceView.value = clonePreferenceSnapshot({ ...before, ...operation.optimistic })
  try {
    const result = await preferences.patch(operation.values)
    preferenceView.value = clonePreferenceSnapshot(result.snapshot)
    if (result.ok) {
      preferenceConflictOperation = null
      preferenceNotice.value = operation.successMessage
      return
    }
    if (result.status === 409) {
      preferenceConflictOperation = operation
      preferenceConflict.value = true
      return
    }
    preferenceNotice.value = preferences.error.value || 'Không thể lưu thiết lập cá nhân hóa.'
  } finally {
    preferenceBusy.value = false
  }
}

async function retryPreferenceConflict() {
  if (!preferenceConflictOperation) return
  await applyPreferenceOperation(preferenceConflictOperation)
}

async function setPreferenceRegion(region: PreferenceRegionChoice) {
  const accuracy = region.scope === 'ward' || region.scope === 'district' || region.scope === 'province' ? region.scope : 'unknown'
  await applyPreferenceOperation({
    values: {
      region_id: region.id,
      region_label: region.id ? region.label : null,
      region_scope: region.scope,
      location_source: 'manual',
      location_accuracy: accuracy,
    },
    optimistic: {
      region_id: region.id,
      region_label: region.id ? region.label : null,
      region_scope: region.scope,
      location_source: 'manual',
      location_accuracy: accuracy,
      location_reconfirm_required: false,
    },
    successMessage: `Đã cập nhật khu vực ưu tiên: ${region.label}.`,
  })
}

async function togglePreferenceLocation(event: Event) {
  const enabled = (event.target as HTMLInputElement).checked
  await applyPreferenceOperation({
    values: enabled
      ? { location_enabled: true, location_consent_state: 'granted' }
      : { location_enabled: false, location_consent_state: 'off' },
    optimistic: enabled
      ? { location_enabled: true, location_consent_state: 'granted' }
      : { location_enabled: false, location_consent_state: 'off' },
    successMessage: enabled ? 'Đã cho phép vị trí gần đúng.' : 'Đã tắt vị trí gần đúng; khu vực thủ công được giữ lại.',
  })
}

async function togglePreferencePersonalization(event: Event) {
  const enabled = (event.target as HTMLInputElement).checked
  await applyPreferenceOperation({
    values: { personalization_enabled: enabled },
    optimistic: { personalization_enabled: enabled },
    successMessage: enabled ? 'Đã bật cá nhân hóa theo hoạt động.' : 'Đã tắt cá nhân hóa theo hoạt động.',
  })
}

async function resetPreferenceRecommendations() {
  syncPreferenceOnline()
  if (!preferenceOnline.value || preferenceBusy.value) return
  preferenceBusy.value = true
  preferenceNotice.value = ''
  try {
    const result = await preferences.resetRecommendations()
    preferenceView.value = clonePreferenceSnapshot(result.snapshot)
    preferenceNotice.value = result.ok
      ? 'Đã đặt lại đề xuất. Mục đã lưu, lượt xem và hồ sơ không bị xóa.'
      : preferences.error.value || 'Không thể đặt lại đề xuất lúc này.'
  } finally {
    preferenceBusy.value = false
  }
}

onMounted(() => {
  if (import.meta.client) {
    window.addEventListener('online', syncPreferenceOnline)
    window.addEventListener('offline', syncPreferenceOnline)
  }
})

onBeforeUnmount(() => {
  if (import.meta.client) {
    window.removeEventListener('online', syncPreferenceOnline)
    window.removeEventListener('offline', syncPreferenceOnline)
  }
})
</script>

<style scoped>
.preference-card { border: 1px solid var(--line); }
.preference-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--space-3); }
.preference-heading .preference-kicker { margin: 0 0 .25rem; color: var(--ink-700); font-size: var(--text-2xs); font-weight: 700; letter-spacing: .08em; }
.preference-heading h2 { margin: 0; padding: 0; border: 0; font-family: var(--font-editorial); font-size: var(--text-lg); }
.preference-revision { flex-shrink: 0; padding: .25rem .55rem; border: 1px solid var(--line); border-radius: var(--radius-full); color: var(--ink-700); font-size: var(--text-xs); }
.preference-intro { max-width: 68ch; margin: .55rem 0 var(--space-4); line-height: var(--leading-relaxed); }
.preference-banner { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-4); padding: .8rem .9rem; border: 1px solid color-mix(in srgb, var(--amber-600) 30%, var(--line)); border-radius: var(--radius-surface); background: color-mix(in srgb, var(--amber-600) 6%, var(--bg-warm)); }
.preference-banner .btn { min-height: 44px; }
.preference-banner p { margin: .15rem 0 0; color: var(--ink-700); font-size: var(--text-xs); line-height: 1.45; }
.preference-conflict { border-color: color-mix(in srgb, var(--danger) 40%, var(--line)); background: color-mix(in srgb, var(--danger) 6%, var(--bg-warm)); }
.preference-notice { margin: 0 0 var(--space-4); padding: .7rem .8rem; border-radius: var(--radius-surface); background: var(--bg-alt); color: var(--ink-700); font-size: var(--text-sm); }
.preference-summary { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); }
.preference-summary > div { display: grid; grid-template-columns: minmax(120px, .8fr) minmax(0, 1.2fr); gap: var(--space-2); padding: .75rem 0; }
.preference-summary > div:nth-child(odd) { padding-right: var(--space-4); }
.preference-summary > div:nth-child(even) { padding-left: var(--space-4); border-left: 1px solid var(--line); }
.preference-summary dt { color: var(--ink-700); font-size: var(--text-xs); }
.preference-summary dd { margin: 0; font-size: var(--text-sm); font-weight: 650; }
.preference-state-copy { margin: var(--space-3) 0 0; padding: .6rem .85rem; border: 1px solid var(--color-action-border); border-radius: var(--radius-surface); background: var(--color-action-surface); color: var(--ink-700); font-size: var(--text-sm); line-height: 1.5; }
.preference-section { margin-top: var(--space-5); padding-top: var(--space-4); border-top: 1px solid var(--line); }
.preference-section-head h3 { margin: 0 0 .2rem; font-size: var(--text-base); }
.preference-section-head p { margin: 0; color: var(--ink-700); font-size: var(--text-xs); }
.preference-options { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-3); }
.preference-option { min-height: 44px; padding: .55rem .85rem; border: 1px solid var(--border-input); border-radius: var(--radius-full); background: var(--bg); color: var(--ink-700); font: inherit; font-size: var(--text-sm); cursor: pointer; transition: border-color .2s, background .2s, color .2s; }
.preference-option:hover:not(:disabled) { border-color: var(--muted); color: var(--ink); }
.preference-option.selected { border-color: var(--color-action); background: var(--color-action-surface); color: var(--ink); font-weight: 650; }
.preference-option:focus-visible, .preference-banner .btn:focus-visible, .preference-reset .btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.preference-option:disabled { cursor: not-allowed; opacity: .55; }
.preference-chips { display: flex; flex-wrap: wrap; gap: var(--space-2); margin-top: var(--space-3); }
.preference-chip { padding: .35rem .65rem; border-radius: var(--radius-full); background: var(--bg-alt); color: var(--ink-700); font-size: .82rem; font-weight: 600; }
.preference-controls { display: flex; flex-direction: column; gap: var(--space-2); }
.preference-control { cursor: default; min-height: 68px; }
.preference-control-mark { display: inline-flex; align-items: center; justify-content: center; min-width: 54px; min-height: 32px; border: 1px solid var(--line); border-radius: var(--radius-control); color: var(--ink-700); font-size: var(--text-2xs); font-weight: 750; letter-spacing: .06em; }
.preference-reset { display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); margin-top: var(--space-4); padding-top: var(--space-4); border-top: 1px solid var(--line); }
.preference-reset p { margin: .2rem 0 0; max-width: 60ch; }
.preference-reset .btn { min-height: 44px; flex-shrink: 0; }

.dark .preference-banner, .dark .preference-notice, .dark .preference-chip { background: var(--bg-alt); }
.dark .preference-option { background: var(--bg-alt); border-color: var(--line); }

@media (max-width: 600px) {
  .preference-heading, .preference-banner, .preference-reset { align-items: flex-start; flex-direction: column; }
  .preference-summary { grid-template-columns: 1fr; }
  .preference-summary > div, .preference-summary > div:nth-child(odd), .preference-summary > div:nth-child(even) { padding: .7rem 0; border-left: 0; }
  .preference-summary > div + div { border-top: 1px solid var(--line); }
  .preference-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .preference-option, .preference-reset .btn, .preference-banner .btn { width: 100%; justify-content: center; }
}
@media (prefers-reduced-motion: reduce) {
  .preference-option { transition: none; }
}
</style>
