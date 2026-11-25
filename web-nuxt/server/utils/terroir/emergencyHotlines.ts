import { PROVINCE_CONFIG, type ProvinceEmergencyHotline } from '../../../utils/provinceConfig'

export type CivicEmergencyHotline = ProvinceEmergencyHotline

export const VERIFIED_EMERGENCY_HOTLINES: readonly CivicEmergencyHotline[] = Object.freeze(
  PROVINCE_CONFIG.emergencyHotlines,
)
