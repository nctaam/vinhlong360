import { defineEventHandler, getQuery, setResponseHeader } from 'h3'
import { sendProblemDetails } from '../../../utils/terroir/problemDetails'
import { calculateAstronomicalTide } from '../../../utils/terroir/astronomicalTide'
import { resolveSeasonalHarvest } from '../../../utils/terroir/seasonalHarvest'
import { resolveWeatherTerroirContext } from '../../../utils/terroir/weatherTerroir'
import { VERIFIED_EMERGENCY_HOTLINES } from '../../../utils/terroir/emergencyHotlines'

const CACHE_CONTROL_HEADER = 'public, max-age=300, s-maxage=3600, stale-while-revalidate=86400'
const OVERVIEW_CACHE_MAX_ENTRIES = 64

type OverviewComputedSnapshot = {
  tide: ReturnType<typeof calculateAstronomicalTide>
  seasonal: ReturnType<typeof resolveSeasonalHarvest>
  weather: ReturnType<typeof resolveWeatherTerroirContext>
  vnIso: string
}

const overviewSnapshotCache = new Map<number, OverviewComputedSnapshot>()

function getOverviewComputedSnapshot(targetDate: Date): OverviewComputedSnapshot {
  const bucketKey = Math.floor(targetDate.getTime() / 1000)
  const cached = overviewSnapshotCache.get(bucketKey)
  if (cached) return cached

  const snapshot: OverviewComputedSnapshot = {
    tide: calculateAstronomicalTide(targetDate),
    seasonal: resolveSeasonalHarvest(targetDate),
    weather: resolveWeatherTerroirContext(targetDate),
    vnIso: new Date(targetDate.getTime() + 7 * 3600 * 1000).toISOString().replace('Z', '+07:00'),
  }
  if (overviewSnapshotCache.size >= OVERVIEW_CACHE_MAX_ENTRIES) {
    const oldestKey = overviewSnapshotCache.keys().next().value
    if (oldestKey !== undefined) overviewSnapshotCache.delete(oldestKey)
  }
  overviewSnapshotCache.set(bucketKey, snapshot)
  return snapshot
}

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

  const { tide, seasonal, weather, vnIso } = getOverviewComputedSnapshot(targetDate)

  // 4. Attach Caching & Civic Headers
  setResponseHeader(event, 'Content-Type', 'application/json; charset=utf-8')
  setResponseHeader(event, 'Cache-Control', CACHE_CONTROL_HEADER)
  setResponseHeader(event, 'Access-Control-Allow-Origin', '*')

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
