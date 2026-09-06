import { formatDistance } from '~/composables/useRouting'
import type { CurrentPlannerOptimizationResult, RoutableStop, StopWithCoords } from '~/composables/useItineraryOptimization'
import type { OpeningHourConflict } from './plannerSnapshots'

export function routedStopName<T extends StopWithCoords & { name: string }>(
  routed: RoutableStop<T>[],
  key: string,
): string {
  return routed.find(item => item.key === key)?.stop.name || key
}

export function plannerWarningMessage<T extends StopWithCoords & { name: string }>(
  warning: string,
  routed: RoutableStop<T>[],
): string {
  const separator = warning.indexOf(':')
  const code = separator >= 0 ? warning.slice(0, separator) : warning
  const key = separator >= 0 ? warning.slice(separator + 1) : ''
  const name = key ? routedStopName(routed, key) : ''
  if (code === 'opening-hours-unknown') {
    return `Chưa rõ giờ mở cửa của "${name}"; lịch không áp dụng ràng buộc giờ mở cửa.`
  }
  if (code === 'opening-hours-invalid') {
    return `Giờ mở cửa của "${name}" không theo định dạng hỗ trợ nên không được dùng để lập lịch.`
  }
  if (code === 'requested-time-invalid') {
    return `Khung giờ đã nhập cho "${name}" được giữ nguyên nhưng không dùng để lập lịch vì sai định dạng khoảng giờ.`
  }
  if (code === 'route-table-unavailable') {
    return 'Không lấy được ma trận thời gian OSRM; yêu cầu đã bỏ ma trận để máy chủ dùng dự phòng Haversine.'
  }
  if (code === 'schedule-fallback-order-only') {
    return 'Bộ lập lịch gặp lỗi; máy chủ chỉ tối ưu thứ tự tuyến.'
  }
  return warning
}

export function optimizationTradeoffs<T extends StopWithCoords & { name: string }>(
  result: CurrentPlannerOptimizationResult<T>,
  routed: RoutableStop<T>[],
  totalStopsCount: number,
  itineraryScheduleV2: boolean,
): string[] {
  const messages: string[] = []
  const { outcome } = result
  if (outcome.optimization.saved_distance_km > 0.05) {
    messages.push(`Giảm khoảng ${formatDistance(outcome.optimization.saved_distance_km * 1000)} theo ước tính hình học.`)
  } else {
    messages.push('Ước tính khoảng cách không giảm đáng kể.')
  }
  const missingCoordinates = totalStopsCount - routed.length
  if (missingCoordinates > 0) messages.push(`${missingCoordinates} điểm thiếu tọa độ được giữ nguyên vị trí.`)
  if (outcome.route && !outcome.unresolvedUturn) messages.push('Không phát hiện thao tác quay đầu trên tuyến ứng viên.')
  if (outcome.unresolvedUturn) messages.push('Tuyến ứng viên vẫn có rủi ro quay đầu; hãy kiểm tra thủ công.')
  messages.push(...result.scheduleWarnings.map(warning => plannerWarningMessage(warning, routed)))
  messages.push(...outcome.warnings.map(warning => plannerWarningMessage(warning, routed)))
  const schedule = outcome.optimization.schedule
  if (itineraryScheduleV2 && !schedule) messages.push('Không có khung giờ đề xuất; ứng viên chỉ đổi thứ tự tuyến.')
  if (schedule?.matrix_source === 'haversine-fallback') {
    messages.push('Thời gian di chuyển dùng ước tính Haversine vì ma trận OSRM không khả dụng.')
  }
  if (schedule && schedule.overtime_minutes > 0) {
    messages.push(`Ứng viên vượt cuối ngày ${Math.round(schedule.overtime_minutes)} phút.`)
  }
  return [...new Set(messages)]
}

export function openingHourConflictsFor<T extends StopWithCoords & { name: string; time?: string }>(
  result: CurrentPlannerOptimizationResult<T>,
  routed: RoutableStop<T>[],
  plannerScheduleMetadata: WeakMap<object, { openingHours?: string | null }>,
): OpeningHourConflict[] {
  const schedule = result.outcome.optimization.schedule
  return (schedule?.skipped || [])
    .filter(item => item.reason.toLowerCase().includes('opening'))
    .map((item) => {
      const routedStop = routed.find(candidate => candidate.key === item.stop_id)
      const metadata = routedStop ? plannerScheduleMetadata.get(routedStop.stop as object) : undefined
      return {
        stopId: routedStop?.stop.name || item.stop_id,
        requestedTime: routedStop?.stop.time || null,
        openingHours: metadata?.openingHours || null,
      }
    })
}
