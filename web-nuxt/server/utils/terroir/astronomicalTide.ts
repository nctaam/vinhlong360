import {
  solarToLunar,
  todayInVietnam,
  canChiYear,
  canChiMonth,
  canChiDay,
  tietKhiName,
  tietKhiIndex,
  lunarPhrase,
} from '../../../composables/useLunar'

export type TidePhase = 'rong' | 'kem' | 'chuyen'
export type WaterFlowState = 'nuoc_lon' | 'nuoc_rong_can' | 'nuoc_dung'

export interface AstronomicalTideResponse {
  lunar_date: {
    day: number
    month: number
    year: number
    leap: boolean
    can_chi_year: string
    can_chi_month: string
    can_chi_day: string
    lunar_phrase: string
  }
  solar_term: {
    index: number
    name: string
  }
  tide_phase: TidePhase
  tide_phase_label: string
  tide_phase_desc: string
  water_level_meters: number
  water_flow_state: WaterFlowState
  water_flow_label: string
  water_flow_desc: string
  dhdt: number
  flow_velocity_ms: number
  current_azimuth_deg: number
  folk_wisdom: string
  folkWisdom?: string
}

const RIVER_AZIMUTH_SEAWARD = 135.0 // Northwest to Southeast dominant corridor (towards East Sea)
const RIVER_AZIMUTH_LANDWARD = 315.0 // Reverse flood tide flow corridor
const MEAN_STAGE_METERS = 1.10
const SYNODIC_MONTH = 29.530588853
const TAU_1 = 3.5 // Diurnal lag (hours)
const TAU_2 = 1.2 // Semi-diurnal lag (hours)

export function calculateTidalAmplitudeFactor(lunarDay: number): number {
  const phaseAngle = (4 * Math.PI * (lunarDay - 1)) / SYNODIC_MONTH
  return 1.00 + 0.35 * Math.cos(phaseAngle)
}

export function calculateAstronomicalTide(date: Date = new Date()): AstronomicalTideResponse {
  const vn = todayInVietnam(date)
  const lunar = solarToLunar(vn.day, vn.month, vn.year)
  const dL = lunar.day

  // 1. Tidal Phase Classification
  let tidePhase: TidePhase = 'chuyen'
  let tidePhaseLabel = 'Kỳ Nước chuyển'
  let tidePhaseDesc = 'Triều chuyển dòng điều hòa'

  if ([29, 30, 1, 2, 3, 14, 15, 16, 17, 18].includes(dL)) {
    tidePhase = 'rong'
    tidePhaseLabel = 'Kỳ Nước rong'
    tidePhaseDesc = 'Triều dâng cao theo tuần trăng (Rằm & Mùng một)'
  } else if ([7, 8, 9, 10, 22, 23, 24, 25].includes(dL)) {
    tidePhase = 'kem'
    tidePhaseLabel = 'Kỳ Nước kém'
    tidePhaseDesc = 'Triều kém dòng êm, biên độ nhỏ (Mùng bảy & Hăm ba)'
  }

  // 2. Local Vietnam hours
  const hours = ((date.getUTCHours() + 7) % 24) + date.getUTCMinutes() / 60 + date.getUTCSeconds() / 3600
  const alpha = calculateTidalAmplitudeFactor(dL)
  const a1 = 0.65 * alpha
  const a2 = 0.45 * alpha
  const omega1 = (2 * Math.PI) / 24.84
  const omega2 = (4 * Math.PI) / 24.84

  const phase1 = omega1 * (hours - TAU_1)
  const phase2 = omega2 * (hours - TAU_2)

  const waterLevel = MEAN_STAGE_METERS + a1 * Math.cos(phase1) + a2 * Math.cos(phase2)
  const dhdt = -a1 * omega1 * Math.sin(phase1) - a2 * omega2 * Math.sin(phase2)

  // 3. Instantaneous Water Flow State
  let waterFlowState: WaterFlowState = 'nuoc_dung'
  let waterFlowLabel = 'Nước đứng'
  let waterFlowDesc = 'Mặt sông êm ả, dòng chảy tĩnh'
  let currentAzimuth = RIVER_AZIMUTH_SEAWARD
  let flowVelocity = 0.10

  if (dhdt > 0.15) {
    waterFlowState = 'nuoc_lon'
    waterFlowLabel = 'Nước lớn'
    waterFlowDesc = 'Triều dâng, nước từ biển dồn vào sông Cổ Chiên'
    currentAzimuth = RIVER_AZIMUTH_LANDWARD
    flowVelocity = Math.min(1.3, 0.6 + 0.7 * Math.min(1, dhdt / 0.5))
  } else if (dhdt < -0.15) {
    waterFlowState = 'nuoc_rong_can'
    waterFlowLabel = 'Nước ròng'
    waterFlowDesc = 'Triều rút, dòng nước phù sa đổ mạnh ra biển'
    currentAzimuth = RIVER_AZIMUTH_SEAWARD
    flowVelocity = Math.min(1.5, 0.8 + 0.7 * Math.min(1, Math.abs(dhdt) / 0.5))
  }

  const sTermIdx = tietKhiIndex(vn.day, vn.month, vn.year)
  const sTermName = tietKhiName(vn.day, vn.month, vn.year)

  return {
    lunar_date: {
      day: lunar.day,
      month: lunar.month,
      year: lunar.year,
      leap: lunar.leap,
      can_chi_year: canChiYear(lunar.year),
      can_chi_month: canChiMonth(lunar.month, lunar.year),
      can_chi_day: canChiDay(vn.day, vn.month, vn.year),
      lunar_phrase: lunarPhrase(lunar),
    },
    solar_term: {
      index: sTermIdx,
      name: sTermName,
    },
    tide_phase: tidePhase,
    tide_phase_label: tidePhaseLabel,
    tide_phase_desc: tidePhaseDesc,
    water_level_meters: Math.round(waterLevel * 100) / 100,
    water_flow_state: waterFlowState,
    water_flow_label: waterFlowLabel,
    water_flow_desc: waterFlowDesc,
    dhdt: Math.round(dhdt * 1000) / 1000,
    flow_velocity_ms: Math.round(flowVelocity * 100) / 100,
    current_azimuth_deg: currentAzimuth,
    folk_wisdom: 'Nước rong rằm & mùng một, nước kém mùng bảy & hăm ba',
    folkWisdom: 'Nước rong rằm & mùng một, nước kém mùng bảy & hăm ba',
  }
}
