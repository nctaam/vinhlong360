import { defineEventHandler, getQuery, setResponseHeader } from 'h3'
import { sendProblemDetails } from '../../../utils/terroir/problemDetails'
import { calculateAstronomicalTide } from '../../../utils/terroir/astronomicalTide'
import { resolveSeasonalHarvest } from '../../../utils/terroir/seasonalHarvest'
import { resolveWeatherTerroirContext } from '../../../utils/terroir/weatherTerroir'
import { VERIFIED_EMERGENCY_HOTLINES } from '../../../utils/terroir/emergencyHotlines'

const CACHE_CONTROL_HEADER = 'public, max-age=300, s-maxage=3600, stale-while-revalidate=86400'

export default defineEventHandler((event) => {
  const query = getQuery(event)
  let targetDate = new Date()

  if (query.date !== undefined && query.date !== null && String(query.date).trim() !== '') {
    const rawDateStr = String(query.date).trim()
    const parsed = new Date(rawDateStr)
    if (Number.isNaN(parsed.getTime())) {
      return sendProblemDetails(event, {
        status: 400,
        type: 'https://vinhlong360.vn/problems/invalid-query-parameter',
        title: 'Invalid Query Parameter',
        detail: `Tham số 'date' với giá trị '${rawDateStr}' không phải là chuỗi thời gian ISO 8601 hợp lệ.`,
        code: 'TERROIR_INVALID_DATE_FORMAT',
        invalidParams: [{ name: 'date', reason: 'Must be a valid ISO 8601 date string' }],
      })
    }
    targetDate = parsed
  }

  // 1. Calculate Astronomical Tide Phase (Meeus/Hồ Ngọc Đức algorithm)
  const tide = calculateAstronomicalTide(targetDate)

  // 2. Resolve Seasonal Harvest & Culinary Indicators
  const seasonal = resolveSeasonalHarvest(targetDate)

  // 3. Resolve Weather Terroir Context (Conforming to CLAUDE.md §1.7)
  const weather = resolveWeatherTerroirContext(targetDate)

  // 4. Attach Caching & Civic Headers
  setResponseHeader(event, 'Content-Type', 'application/json; charset=utf-8')
  setResponseHeader(event, 'Cache-Control', CACHE_CONTROL_HEADER)
  setResponseHeader(event, 'Access-Control-Allow-Origin', '*')

  // Vietnam local time formatted
  const vnIso = new Date(targetDate.getTime() + 7 * 3600 * 1000).toISOString().replace('Z', '+07:00')

  return {
    api_version: '1.0.0',
    evaluated_at: new Date().toISOString(),
    local_time_vietnam: vnIso,
    terroir_basin: 'Lưu vực Thủy thổ Sông Tiền & Cổ Chiên (Vĩnh Long)',
    astronomical_tide: tide,
    seasonal_harvest: seasonal,
    weather_terroir: weather,
    emergency_hotlines: VERIFIED_EMERGENCY_HOTLINES,
  }
})
