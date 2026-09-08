import { ref } from 'vue'

export const AMENITY_OPTIONS: Record<string, { icon: string; label: string }> = {
  wifi: { icon: '📶', label: 'Wi-Fi' },
  wheelchair: { icon: '♿', label: 'Xe lăn' },
  cash_only: { icon: '💵', label: 'Chỉ tiền mặt' },
  pet_friendly: { icon: '🐕', label: 'Thú cưng OK' },
  air_conditioned: { icon: '❄️', label: 'Máy lạnh' },
  kid_friendly: { icon: '👶', label: 'Trẻ em OK' },
  free_entry: { icon: '🆓', label: 'Miễn phí' },
  guided_tour: { icon: '🎙️', label: 'Có hướng dẫn' },
  restroom: { icon: '🚻', label: 'Nhà vệ sinh' },
  photography: { icon: '📸', label: 'Chụp ảnh OK' },
}

export const MONTH_LABELS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']

export const KBYG_KEYS = ['kbyg_tips', 'golden_hours', 'peak_days', 'crowd_level', 'amenity_badges', 'checklist']

export function useAdminEntityAttributes() {
  // KBYG State
  const kbygTips = ref('')
  const kbygGoldenHours = ref('')
  const kbygPeakDays = ref('')
  const kbygCrowdLevel = ref('')
  const kbygAmenities = ref<string[]>([])
  const kbygChecklist = ref('')

  function toggleAmenity(key: string) {
    const idx = kbygAmenities.value.indexOf(key)
    if (idx >= 0) kbygAmenities.value.splice(idx, 1)
    else kbygAmenities.value.push(key)
  }

  function initKbyg(attrs?: Record<string, unknown>) {
    const a = attrs || {}
    kbygTips.value = Array.isArray(a.kbyg_tips) ? (a.kbyg_tips as string[]).join('\n') : ''
    kbygGoldenHours.value = (a.golden_hours as string) || ''
    kbygPeakDays.value = (a.peak_days as string) || ''
    kbygCrowdLevel.value = (a.crowd_level as string) || ''
    kbygAmenities.value = Array.isArray(a.amenity_badges) ? [...(a.amenity_badges as string[])] : []
    kbygChecklist.value = Array.isArray(a.checklist) ? (a.checklist as string[]).join('\n') : ''
  }

  function mergeKbygIntoAttrs(attrs: Record<string, unknown>): Record<string, unknown> {
    const result = { ...attrs }
    const tips = kbygTips.value.split('\n').map(s => s.trim()).filter(Boolean)
    if (tips.length) result.kbyg_tips = tips
    else delete result.kbyg_tips
    if (kbygGoldenHours.value.trim()) result.golden_hours = kbygGoldenHours.value.trim()
    else delete result.golden_hours
    if (kbygPeakDays.value.trim()) result.peak_days = kbygPeakDays.value.trim()
    else delete result.peak_days
    if (kbygCrowdLevel.value) result.crowd_level = kbygCrowdLevel.value
    else delete result.crowd_level
    if (kbygAmenities.value.length) result.amenity_badges = [...kbygAmenities.value]
    else delete result.amenity_badges
    const checklist = kbygChecklist.value.split('\n').map(s => s.trim()).filter(Boolean)
    if (checklist.length) result.checklist = checklist
    else delete result.checklist
    return result
  }

  // Season State
  const seasonMonths = ref<number[]>([])
  const seasonPeak = ref<number[]>([])
  const seasonTouched = ref(false)

  function initSeason(season?: { months?: number[]; peak?: number[] } | null) {
    seasonMonths.value = Array.isArray(season?.months) ? [...season!.months] : []
    seasonPeak.value = Array.isArray(season?.peak) ? [...season!.peak] : []
    seasonTouched.value = false
  }

  function monthState(m: number): 'off' | 'in' | 'peak' {
    if (seasonPeak.value.includes(m)) return 'peak'
    if (seasonMonths.value.includes(m)) return 'in'
    return 'off'
  }

  function cycleMonth(m: number) {
    seasonTouched.value = true
    const st = monthState(m)
    if (st === 'off') {
      seasonMonths.value = [...seasonMonths.value, m].sort((a, b) => a - b)
    } else if (st === 'in') {
      seasonPeak.value = [...seasonPeak.value, m].sort((a, b) => a - b)
    } else {
      seasonMonths.value = seasonMonths.value.filter(x => x !== m)
      seasonPeak.value = seasonPeak.value.filter(x => x !== m)
    }
  }

  // Advanced attributes JSON
  const advancedJson = ref('')
  const advancedError = ref('')

  function initAdvanced(attrs?: Record<string, unknown>, currentSchemaKeys: string[] = []) {
    advancedError.value = ''
    const a = attrs || {}
    const managed = new Set([...currentSchemaKeys, ...KBYG_KEYS])
    const tail: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(a)) {
      if (!managed.has(k)) tail[k] = v
    }
    advancedJson.value = Object.keys(tail).length ? JSON.stringify(tail, null, 2) : ''
  }

  function parseAdvancedJson(): { ok: true; data: Record<string, unknown> } | { ok: false; error: string } {
    if (!advancedJson.value.trim()) {
      advancedError.value = ''
      return { ok: true, data: {} }
    }
    try {
      const parsed = JSON.parse(advancedJson.value)
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        throw new Error('not-object')
      }
      advancedError.value = ''
      return { ok: true, data: parsed }
    } catch {
      const errorMsg = 'JSON không hợp lệ — kiểm tra lại dấu ngoặc/nháy.'
      advancedError.value = errorMsg
      return { ok: false, error: errorMsg }
    }
  }

  function assembleAttributes(options: {
    existingAttrs?: Record<string, unknown>
    currentSchemaKeys: string[]
    typedAttrs: Record<string, unknown>
    advancedObj: Record<string, unknown>
  }): Record<string, unknown> {
    const { existingAttrs = {}, currentSchemaKeys, typedAttrs, advancedObj } = options
    const targetAttrs: Record<string, unknown> = { ...existingAttrs }
    const managed = new Set([...currentSchemaKeys, ...KBYG_KEYS])

    for (const k of Object.keys(targetAttrs)) {
      if (!managed.has(k)) delete targetAttrs[k]
    }
    for (const [k, v] of Object.entries(advancedObj)) {
      if (!managed.has(k)) targetAttrs[k] = v
    }

    for (const k of currentSchemaKeys) {
      const v = typedAttrs[k]
      const empty = v === undefined || v === '' || (Array.isArray(v) && v.length === 0)
      if (empty) delete targetAttrs[k]
      else targetAttrs[k] = v
    }

    return mergeKbygIntoAttrs(targetAttrs)
  }

  return {
    AMENITY_OPTIONS,
    kbygTips,
    kbygGoldenHours,
    kbygPeakDays,
    kbygCrowdLevel,
    kbygAmenities,
    kbygChecklist,
    toggleAmenity,
    initKbyg,
    mergeKbygIntoAttrs,

    MONTH_LABELS,
    seasonMonths,
    seasonPeak,
    seasonTouched,
    initSeason,
    monthState,
    cycleMonth,

    advancedJson,
    advancedError,
    initAdvanced,
    parseAdvancedJson,
    assembleAttributes,
  }
}
