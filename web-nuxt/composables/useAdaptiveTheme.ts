// useAdaptiveTheme — Tự động điều hướng chế độ sáng/tối theo nhịp nhật nguyệt Vĩnh Long (10.25°N, 105.97°E)
//
// Mekong Solar Clock:
// Vĩnh Long nằm ở vĩ tuyến 10.25° Bắc, thời gian rạng đông và hoàng hôn dao động ổn định
// quanh năm trong khoảng 05:35–06:10 sáng và 17:35–18:15 chiều.
// Khung giờ nắng ban ngày: 05:45 – 17:45.
//
// Logic:
// 1. Tôn trọng tuyệt đối lựa chọn thủ công nếu người dùng đã lưu trong localStorage.
// 2. Với lượt truy cập tự nhiên chưa thiết lập:
//    - Ban ngày (05:45 -> 17:45): Parchment (nền sáng chống lóa nắng sông Tiền).
//    - Ban đêm (17:45 -> 05:45): Nocturne (nền tối ấm dịu mắt, tiết kiệm pin OLED).

import { ACCESSIBILITY_STORAGE_KEY } from '~/composables/useAccessibilityProfile'

export function getVinhLongSolarTheme(date: Date = new Date()): 'parchment' | 'nocturne' {
  const hours = date.getHours()
  const minutes = date.getMinutes()
  const currentMinutes = hours * 60 + minutes

  // 05:45 = 5 * 60 + 45 = 345
  // 17:45 = 17 * 60 + 45 = 1065
  const SUNRISE_MINUTES = 345
  const SUNSET_MINUTES = 1065

  return (currentMinutes >= SUNRISE_MINUTES && currentMinutes < SUNSET_MINUTES)
    ? 'parchment'
    : 'nocturne'
}

export function useAdaptiveTheme() {
  const colorMode = useColorMode()
  const accessibility = useAccessibilityProfile({ colorMode, autoHydrate: false })

  function applySolarThemeIfUnset() {
    if (import.meta.server) return
    try {
      const stored = localStorage.getItem(ACCESSIBILITY_STORAGE_KEY)
      if (!stored) {
        const solarTheme = getVinhLongSolarTheme()
        if (accessibility.profile.value.theme !== solarTheme) {
          accessibility.setProfile({ theme: solarTheme })
        }
      }
    } catch {
      // LocalStorage may be blocked in some browser contexts
    }
  }

  return {
    getVinhLongSolarTheme,
    applySolarThemeIfUnset,
  }
}

export default useAdaptiveTheme
