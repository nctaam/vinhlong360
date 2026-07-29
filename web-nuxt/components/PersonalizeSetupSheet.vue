<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="visible" class="onboarding-overlay personalize-overlay" @click.self="skip">
        <section
          ref="sheetEl"
          class="onboarding-sheet personalize-sheet"
          role="dialog"
          aria-modal="true"
          aria-label="Thiết lập khu vực và sở thích"
          :data-step="currentStep + 1"
        >
          <button type="button" class="sheet-close" aria-label="Đóng thiết lập" @click="skip">
            <IconLine name="x" />
          </button>

          <div class="personalize-kicker">
            <span class="personalize-eyebrow">Thiết lập nhanh</span>
            <span class="location-source-chip" :data-source="sourceKey" :data-consent="preferences.snapshot.value.location_consent_state">
              <IconLine :name="sourceIcon" aria-hidden="true" />
              {{ sourceLabel }}
            </span>
          </div>

          <nav class="setup-rail" aria-label="Các bước thiết lập">
            <span
              v-for="(step, index) in steps"
              :key="step.key"
              class="setup-rail-item"
              :class="{ active: currentStep === index, complete: currentStep > index }"
              :aria-current="currentStep === index ? 'step' : undefined"
            >
              <span class="setup-rail-mark">
                <IconLine v-if="currentStep > index" name="shield-check" aria-hidden="true" />
                <span v-else>{{ index + 1 }}</span>
              </span>
              <span>{{ step.label }}</span>
            </span>
          </nav>

          <header class="sheet-header personalize-header">
            <span class="sheet-icon-chip" aria-hidden="true">
              <IconLine :name="steps[currentStep]?.icon || 'sliders'" />
            </span>
            <h2>{{ steps[currentStep]?.title }}</h2>
            <p>{{ steps[currentStep]?.description }}</p>
          </header>

          <div class="personalize-body">
            <div v-if="currentStep === 0" class="setup-panel" data-panel="region">
              <div class="setup-option-grid" role="listbox" aria-label="Chọn khu vực ưu tiên">
                <button
                  v-for="region in regions"
                  :key="region.id || 'all'"
                  type="button"
                  class="setup-option"
                  :class="{ selected: selectedRegion?.id === region.id }"
                  :data-region="region.id || 'all'"
                  :aria-selected="selectedRegion?.id === region.id"
                  role="option"
                  @click="selectedRegion = region"
                >
                  <IconLine :name="region.icon" aria-hidden="true" />
                  <span>{{ region.label }}</span>
                  <IconLine v-if="selectedRegion?.id === region.id" name="shield-check" aria-hidden="true" />
                </button>
              </div>
              <p class="setup-note"><IconLine name="shield-check" aria-hidden="true" /> Chọn thủ công không cần bật vị trí.</p>
            </div>

            <div v-else-if="currentStep === 1" class="setup-panel" data-panel="interests">
              <div class="setup-option-grid interest-grid" role="group" aria-label="Chọn tối đa ba sở thích">
                <button
                  v-for="interest in interests"
                  :key="interest.key"
                  type="button"
                  class="setup-option"
                  :class="{ selected: selectedInterests.includes(interest.key) }"
                  :data-interest="interest.key"
                  :aria-pressed="selectedInterests.includes(interest.key)"
                  @click="toggleInterest(interest.key)"
                >
                  <IconLine :name="interest.icon" aria-hidden="true" />
                  <span>{{ interest.label }}</span>
                  <IconLine v-if="selectedInterests.includes(interest.key)" name="shield-check" aria-hidden="true" />
                </button>
              </div>
              <p class="setup-note"><IconLine name="list" aria-hidden="true" /> {{ selectedInterests.length }}/3 sở thích đã chọn</p>
            </div>

            <div v-else class="setup-panel" data-panel="location">
              <div v-if="locationState === 'idle'" class="location-prompt">
                <div class="location-prompt-icon"><IconLine name="locate" aria-hidden="true" /></div>
                <div>
                  <strong>Dùng vị trí gần đúng một lần</strong>
                  <p>Chỉ dùng để gợi ý khu vực phù hợp. Tọa độ không được lưu vào hồ sơ.</p>
                </div>
              </div>
              <div v-else-if="locationState === 'loading'" class="location-prompt" role="status" aria-live="polite">
                <div class="location-prompt-icon"><IconLine name="locate" aria-hidden="true" /></div>
                <div><strong>Đang tìm khu vực gần bạn…</strong><p>Không lưu vị trí chính xác.</p></div>
              </div>
              <div v-else-if="locationState === 'resolved' && resolvedLocation" class="location-prompt resolved-location">
                <div class="location-prompt-icon"><IconLine name="pin" aria-hidden="true" /></div>
                <div><strong>{{ resolvedLocation.region_label || 'Khu vực gần bạn' }}</strong><p>Độ chính xác: {{ accuracyLabel(resolvedLocation.location_accuracy) }}.</p></div>
              </div>
              <p v-else-if="locationState === 'denied'" class="setup-status" role="status"><IconLine name="alert-triangle" aria-hidden="true" /> Quyền vị trí bị từ chối. Bạn vẫn có thể dùng khu vực thủ công.</p>
              <p v-else class="setup-status" role="status"><IconLine name="alert-triangle" aria-hidden="true" /> Chưa xác định được khu vực. Bạn có thể thiết lập sau.</p>
            </div>
          </div>

          <p v-if="preferences.error.value" class="setup-error" role="alert">{{ preferences.error.value }}</p>

          <div class="sheet-actions personalize-actions">
            <button type="button" class="btn btn-ghost" data-action="skip" @click="skip">Bỏ qua, thiết lập sau</button>
            <button
              v-if="currentStep < 2"
              type="button"
              class="btn btn-primary"
              data-action="continue"
              :disabled="preferences.loading.value"
              @click="continueStep"
            >Tiếp tục <IconLine class="next-icon" name="chevron-down" aria-hidden="true" /></button>
            <template v-else>
              <button
                v-if="locationState === 'idle'"
                type="button"
                class="btn btn-primary"
                data-action="use-location"
                :disabled="preferences.loading.value || locationAttempted"
                @click="useLocation"
              ><IconLine name="locate" aria-hidden="true" /> Dùng vị trí gần đúng</button>
              <button
                v-else-if="locationState === 'resolved'"
                type="button"
                class="btn btn-primary"
                data-action="confirm-location"
                :disabled="preferences.loading.value"
                @click="confirmLocation"
              >Dùng khu vực này</button>
              <button v-else type="button" class="btn btn-primary" data-action="finish" @click="finish">Xong</button>
            </template>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import IconLine from './IconLine.vue'
import { usePersonalizationPreferences } from '~/composables/usePersonalizationPreferences'
import type { LocationResolution, PreferenceRegionChoice } from '~/types/personalization'

const props = withDefaults(defineProps<{ modelValue?: boolean }>(), { modelValue: false })
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  complete: []
  skip: []
}>()

const preferences = usePersonalizationPreferences()
const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})
const sheetEl = ref<HTMLElement | null>(null)
const currentStep = ref(0)
const selectedRegion = ref<PreferenceRegionChoice | null>(null)
const selectedInterests = ref<string[]>([])
const locationAttempted = ref(false)
const locationState = ref<'idle' | 'loading' | 'resolved' | 'denied' | 'unknown'>('idle')
const resolvedLocation = ref<LocationResolution | null>(null)

const steps = [
  { key: 'region', label: 'Khu vực', title: 'Bạn muốn bắt đầu từ đâu?', description: 'Chọn một khu vực để sắp xếp nội dung gần với bạn hơn.', icon: 'pin' },
  { key: 'interests', label: 'Sở thích', title: 'Bạn thường tìm gì?', description: 'Chọn tối đa ba mối quan tâm. Bạn có thể đổi lại bất cứ lúc nào.', icon: 'sparkles' },
  { key: 'location', label: 'Vị trí', title: 'Thêm một lớp gợi ý?', description: 'Tùy chọn: dùng vị trí gần đúng một lần, không lưu tọa độ.', icon: 'locate' },
] as const

const regions = [
  { id: 'province-vl', label: 'Vĩnh Long', scope: 'province', icon: 'fruit' },
  { id: 'province-bt', label: 'Bến Tre', scope: 'province', icon: 'leaf' },
  { id: 'province-tv', label: 'Trà Vinh', scope: 'province', icon: 'landmark' },
  { id: null, label: 'Toàn tỉnh', scope: 'all', icon: 'map' },
] satisfies Array<PreferenceRegionChoice & { icon: string }>

const interests = [
  { key: 'food', label: 'Ẩm thực', icon: 'bowl' },
  { key: 'local_products', label: 'Đặc sản & OCOP', icon: 'fruit' },
  { key: 'garden', label: 'Miệt vườn', icon: 'sprout' },
  { key: 'culture', label: 'Văn hóa', icon: 'landmark' },
  { key: 'craft', label: 'Làng nghề', icon: 'vase' },
  { key: 'stay', label: 'Lưu trú', icon: 'home' },
]

const sourceKey = computed(() => preferences.snapshot.value.location_source)
const sourceIcon = computed(() => {
  const consent = preferences.snapshot.value.location_consent_state
  if (consent === 'denied' || consent === 'expired') return 'alert-triangle'
  if (consent === 'off') return 'shield-check'
  return sourceKey.value === 'manual' ? 'pin' : sourceKey.value === 'gps' ? 'locate' : sourceKey.value === 'ip' ? 'globe' : 'shield-check'
})
const sourceLabel = computed(() => {
  const consent = preferences.snapshot.value.location_consent_state
  if (consent === 'denied') return 'Vị trí bị từ chối'
  if (consent === 'off') return 'Vị trí đang tắt'
  if (consent === 'expired') return 'Cần xác nhận vị trí'
  return sourceKey.value === 'manual' ? 'Bạn chọn thủ công' : sourceKey.value === 'gps' ? 'GPS một lần' : sourceKey.value === 'ip' ? 'IP gần đúng' : 'Chưa dùng vị trí'
})

useModalA11y(visible, sheetEl, { onClose: skip })

watch(() => props.modelValue, (open) => {
  if (!open) {
    currentStep.value = 0
    selectedRegion.value = null
    selectedInterests.value = []
    locationAttempted.value = false
    locationState.value = 'idle'
    resolvedLocation.value = null
  }
})

async function continueStep() {
  if (currentStep.value === 0) {
    if (selectedRegion.value) await preferences.setRegion(selectedRegion.value)
    currentStep.value = 1
    return
  }
  if (currentStep.value === 1) {
    await preferences.setInterests(selectedInterests.value)
    currentStep.value = 2
  }
}

function toggleInterest(key: string) {
  if (selectedInterests.value.includes(key)) {
    selectedInterests.value = selectedInterests.value.filter(item => item !== key)
  } else if (selectedInterests.value.length < 3) {
    selectedInterests.value = [...selectedInterests.value, key]
  }
}

function useLocation() {
  if (locationAttempted.value) return
  locationAttempted.value = true
  if (!import.meta.client || !navigator.geolocation) {
    locationState.value = 'unknown'
    return
  }
  locationState.value = 'loading'
  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const result = await preferences.resolveLocation('gps', {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      })
      resolvedLocation.value = result
      locationState.value = result.region_id ? 'resolved' : 'unknown'
    },
    async () => {
      locationState.value = 'denied'
      await preferences.patch({ location_enabled: false, location_consent_state: 'denied' })
    },
    { enableHighAccuracy: false, maximumAge: 300_000, timeout: 8_000 },
  )
}

async function confirmLocation() {
  const result = resolvedLocation.value
  if (!result?.region_id) return finish()
  const current = preferences.snapshot.value
  const keepsManualRegion = current.location_source === 'manual' && !!current.region_id
  await preferences.patch(keepsManualRegion
    ? { location_consent_state: 'granted', location_enabled: true }
    : {
        region_id: result.region_id,
        region_label: result.region_label,
        region_scope: result.region_scope,
        location_source: 'gps',
        location_accuracy: result.location_accuracy,
        location_consent_state: 'granted',
        location_enabled: true,
      })
  finish()
}

function finish() {
  emit('complete')
  visible.value = false
}

function skip() {
  emit('skip')
  visible.value = false
}

function accuracyLabel(value: string) {
  return value === 'ward' ? 'xã/phường' : value === 'district' ? 'khu vực' : value === 'province' ? 'tỉnh' : 'gần đúng'
}
</script>

<style scoped>
/* Stitch mapping: 9dac45c42bd7470797ff912060690909 informs the mobile bottom-sheet
   chrome and db76e318f0354ee3b1b8e3a0860443a5 informs grouped workspace density.
   Live Stitch retrieval is unavailable here; production uses existing Nuxt tokens. */
.personalize-sheet { gap: var(--space-4); padding-top: var(--space-6); }
.personalize-kicker { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); padding-right: 2.9rem; }
.personalize-eyebrow { color: var(--muted); font-size: var(--text-xs); font-weight: var(--weight-semibold); letter-spacing: .08em; text-transform: uppercase; }
.location-source-chip { display: inline-flex; align-items: center; gap: var(--space-2); min-height: 32px; padding: 0 var(--space-3); border: .5px solid var(--line); border-radius: var(--radius-full); color: var(--primary-fg); background: var(--bg-warm); font-size: var(--text-xs); white-space: nowrap; }
.location-source-chip[data-source="default"] { color: var(--muted); }
.setup-rail { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); padding: var(--space-2) 0; border-top: .5px solid var(--line); border-bottom: .5px solid var(--line); }
.setup-rail-item { display: inline-flex; align-items: center; gap: var(--space-2); color: var(--muted); font-size: var(--text-xs); font-weight: var(--weight-semibold); white-space: nowrap; }
.setup-rail-item.active, .setup-rail-item.complete { color: var(--ink); }
.setup-rail-mark { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border: 1px solid var(--line); border-radius: var(--radius-full); font-size: var(--text-xs); }
.setup-rail-item.active .setup-rail-mark { border-color: var(--primary-fg); color: var(--primary-fg); box-shadow: 0 0 0 3px rgba(var(--primary-rgb), .12); }
.setup-rail-item.complete .setup-rail-mark { border-color: var(--primary-fg); background: var(--primary-fg); color: var(--text-on-dark, #fff); }
.personalize-header { margin: 0; }
.sheet-icon-chip { display: inline-flex; align-items: center; justify-content: center; width: 48px; height: 48px; margin: 0 auto var(--space-3); border-radius: var(--radius-full); color: var(--primary-fg); background: var(--bg-warm); }
.personalize-header h2 { margin-bottom: var(--space-2); font-family: var(--font-editorial); font-weight: 600; letter-spacing: -.01em; }
.personalize-body { min-height: 0; }
.setup-option-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-2); }
.setup-option { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: var(--space-2); min-height: 56px; padding: var(--space-3); border: .5px solid var(--line); border-radius: var(--radius-md); color: var(--ink); background: var(--bg-warm); cursor: pointer; text-align: left; font: inherit; font-size: var(--text-sm); transition: background .2s var(--ease-out), border-color .2s var(--ease-out), box-shadow .2s var(--ease-out); }
.setup-option:hover { background: var(--bg-alt); border-color: var(--primary-fg); }
.setup-option.selected { border-color: var(--primary-fg); background: color-mix(in srgb, var(--primary-fg) 10%, var(--bg-warm)); box-shadow: inset 0 0 0 1px var(--primary-fg); }
.setup-option .line-icon { color: var(--primary-fg); font-size: 1.1rem; }
.setup-note, .setup-status { display: flex; align-items: flex-start; gap: var(--space-2); margin: var(--space-3) 0 0; color: var(--muted); font-size: var(--text-xs); line-height: var(--leading-relaxed); }
.setup-note .line-icon, .setup-status .line-icon { color: var(--primary-fg); margin-top: .1rem; }
.location-prompt { display: flex; align-items: flex-start; gap: var(--space-3); padding: var(--space-4); border: .5px solid var(--line); border-radius: var(--radius-md); background: var(--bg-warm); }
.location-prompt-icon { display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; flex: 0 0 auto; border-radius: var(--radius-sm); color: var(--primary-fg); background: var(--bg-alt); }
.location-prompt strong { display: block; margin-bottom: 2px; color: var(--ink); font-size: var(--text-sm); }
.location-prompt p { margin: 0; color: var(--muted); font-size: var(--text-xs); line-height: var(--leading-relaxed); }
.setup-error { margin: 0; color: var(--error); font-size: var(--text-xs); }
.personalize-actions { align-items: center; justify-content: space-between; flex-wrap: wrap; gap: var(--space-2); }
.personalize-actions .btn { min-height: 44px; }
.personalize-actions .btn-primary { display: inline-flex; align-items: center; gap: var(--space-2); }
.personalize-actions .next-icon { transform: rotate(-90deg); }
@media (max-width: 420px) {
  .personalize-sheet { padding-left: var(--space-4); padding-right: var(--space-4); }
  .setup-rail-item { font-size: .68rem; }
  .setup-rail-item span:last-child { display: none; }
  .personalize-actions { flex-direction: column-reverse; align-items: stretch; }
  .personalize-actions .btn { width: 100%; justify-content: center; }
}
@media (prefers-reduced-motion: reduce) {
  .setup-option { transition: none; }
}
</style>
