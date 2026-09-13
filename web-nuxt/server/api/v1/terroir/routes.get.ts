import { defineEventHandler, getQuery, setResponseHeader } from 'h3'
import { sendProblemDetails } from '../../../utils/terroir/problemDetails'
import { calculateAstronomicalTide } from '../../../utils/terroir/astronomicalTide'
import {
  VERIFIED_WATER_ROUTES,
  calculateRoutePropulsion,
  type CraftType,
} from '../../../utils/terroir/waterEcoRoutes'

const CACHE_CONTROL_HEADER = 'public, max-age=300, s-maxage=3600, stale-while-revalidate=86400'
const VALID_CRAFTS = new Set<CraftType>(['sampan', 'canoe', 'kayak'])

export default defineEventHandler((event) => {
  const query = getQuery(event)
  let targetDate = new Date()

  if (query.departure_time !== undefined && query.departure_time !== null && String(query.departure_time).trim() !== '') {
    const raw = String(query.departure_time).trim()
    const parsed = new Date(raw)
    if (Number.isNaN(parsed.getTime())) {
      return sendProblemDetails(event, {
        status: 400,
        type: 'https://vinhlong360.vn/problems/invalid-query-parameter',
        title: 'Invalid Query Parameter',
        detail: `Tham số 'departure_time' với giá trị '${raw}' không phải là chuỗi thời gian hợp lệ.`,
        code: 'TERROIR_INVALID_DEPARTURE_TIME',
        invalidParams: [{ name: 'departure_time', reason: 'Must be a valid ISO 8601 string' }],
      })
    }
    targetDate = parsed
  }

  let craft: CraftType = 'sampan'
  if (query.craft_type !== undefined && query.craft_type !== null && String(query.craft_type).trim() !== '') {
    const rawCraft = String(query.craft_type).trim().toLowerCase() as CraftType
    if (!VALID_CRAFTS.has(rawCraft)) {
      return sendProblemDetails(event, {
        status: 400,
        type: 'https://vinhlong360.vn/problems/invalid-query-parameter',
        title: 'Invalid Query Parameter',
        detail: `Loại phương tiện '${rawCraft}' không được hỗ trợ. Các loại được phép: sampan, canoe, kayak.`,
        code: 'TERROIR_UNSUPPORTED_CRAFT_TYPE',
        invalidParams: [{ name: 'craft_type', reason: 'Must be one of: sampan, canoe, kayak' }],
      })
    }
    craft = rawCraft
  }

  // Check single route filter if requested
  let routes = VERIFIED_WATER_ROUTES
  if (query.route_id !== undefined && query.route_id !== null && String(query.route_id).trim() !== '') {
    const routeId = String(query.route_id).trim()
    const matched = VERIFIED_WATER_ROUTES.filter(r => r.id === routeId)
    if (matched.length === 0) {
      return sendProblemDetails(event, {
        status: 404,
        type: 'https://vinhlong360.vn/problems/resource-not-found',
        title: 'Resource Not Found',
        detail: `Không tìm thấy tuyến thủy lộ với mã '${routeId}'.`,
        code: 'TERROIR_ROUTE_NOT_FOUND',
      })
    }
    routes = matched
  }

  const tide = calculateAstronomicalTide(targetDate)
  const evaluatedRoutes = routes.map(r => calculateRoutePropulsion(r, tide, targetDate, craft))

  setResponseHeader(event, 'Content-Type', 'application/json; charset=utf-8')
  setResponseHeader(event, 'Cache-Control', CACHE_CONTROL_HEADER)
  setResponseHeader(event, 'Access-Control-Allow-Origin', '*')

  return {
    api_version: '1.0.0',
    evaluated_at: new Date().toISOString(),
    craft_type: craft,
    nominal_craft_speed_ms: craft === 'canoe' ? 8.0 : craft === 'kayak' ? 1.5 : 4.0,
    hydrological_reference: {
      tide_phase: tide.tide_phase,
      water_flow_state: tide.water_flow_state,
      current_azimuth_deg: tide.current_azimuth_deg,
      flow_velocity_ms: tide.flow_velocity_ms,
    },
    total_routes: evaluatedRoutes.length,
    routes: evaluatedRoutes,
  }
})
