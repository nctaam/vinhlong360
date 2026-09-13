import type { AstronomicalTideResponse } from './astronomicalTide'

export type CraftType = 'sampan' | 'canoe' | 'kayak'

export interface RouteWaypoint {
  order: number
  name: string
  lat: number
  lng: number
  note?: string
}

export interface WaterEcoRouteDefinition {
  id: string
  name: string
  corridor: string
  distance_km: number
  typical_duration_minutes: number
  difficulty: string
  recommended_craft: string
  origin: {
    id: string
    name: string
    lat: number
    lng: number
    type: string
  }
  destination: {
    id: string
    name: string
    lat: number
    lng: number
    type: string
  }
  waypoints: RouteWaypoint[]
  safety_advisory: string
  terroir_highlights: string[]
}

export interface TidalPropulsionEvaluation {
  direction: 'downstream_assist' | 'upstream_resistance' | 'cross_current' | 'slack_water'
  effort_savings_percentage: number
  flow_velocity_ms: number
  travel_azimuth_deg: number
  current_azimuth_deg: number
  alignment_cos: number
  green_fuel_savings_factor: number
  narrative_advice: string
  recommended_departure_window: string
}

export interface EvaluatedWaterEcoRoute extends WaterEcoRouteDefinition {
  tidal_propulsion: TidalPropulsionEvaluation
}

export const VERIFIED_WATER_ROUTES: readonly WaterEcoRouteDefinition[] = Object.freeze([
  {
    id: 'route-co-chien-an-binh',
    name: 'Thủy lộ Sông Cổ Chiên — Cù Lao An Bình',
    corridor: 'Sông Cổ Chiên',
    distance_km: 8.5,
    typical_duration_minutes: 35,
    difficulty: 'dễ',
    recommended_craft: 'Tàu du lịch vỏ gỗ / ghe tam bản máy đuôi tôm',
    origin: {
      id: 'pier-vinh-long-passenger',
      name: 'Bến Cảng Hành Khách Du Lịch Vĩnh Long',
      lat: 10.2544,
      lng: 105.9722,
      type: 'major_pier',
    },
    destination: {
      id: 'pier-an-binh-binh-hoa-phuoc',
      name: 'Bến Cù Lao An Bình (Xã Bình Hòa Phước)',
      lat: 10.2300,
      lng: 105.9800,
      type: 'orchard_pier',
    },
    waypoints: [
      { order: 1, name: 'Bến Cảng Du Lịch Vĩnh Long (Bến Bạc)', lat: 10.2544, lng: 105.9722, note: 'Điểm xuất phát, tập kết đón khách' },
      { order: 2, name: 'Doi cát bãi bồi Cổ Chiên', lat: 10.2430, lng: 105.9750, note: 'Khu vực làng bè cá điêu hồng trên sông' },
      { order: 3, name: 'Kênh rạch rợp bóng bần ven An Bình', lat: 10.2350, lng: 105.9780, note: 'Rẽ nhánh vào mương liếp vườn trái cây' },
      { order: 4, name: 'Bến Vườn Chôm Chôm Bình Hòa Phước', lat: 10.2300, lng: 105.9800, note: 'Điểm cập bến tham quan homestay và vườn trái cây' },
    ],
    safety_advisory: 'Lưu ý luồng sà lan cát di chuyển giữa tim sông Cổ Chiên; luôn mặc áo phao tiêu chuẩn khi rời bến.',
    terroir_highlights: [
      'Ngắm nhìn nhịp sống làng bè nuôi cá điêu hồng trải dài đôi bờ sông Cổ Chiên',
      'Rặng bần trổ hoa tím ngát hương ven các dải cù lao phù sa cổ',
      'Trải nghiệm cập cầu khỉ và cầu ván miệt vườn Nam Bộ',
    ],
  },
  {
    id: 'route-mang-thit-red-river',
    name: 'Ký sự Gốm Đỏ Kênh Thầy Cai — Sông Măng Thít',
    corridor: 'Kênh Thầy Cai & Sông Măng Thít',
    distance_km: 14.0,
    typical_duration_minutes: 55,
    difficulty: 'trung bình',
    recommended_craft: 'Ghe tam bản / tàu du lịch sinh thái',
    origin: {
      id: 'junction-co-chien-thay-cai',
      name: 'Ngã ba Cổ Chiên Thầy Cai',
      lat: 10.2600,
      lng: 106.0200,
      type: 'river_junction',
    },
    destination: {
      id: 'kiln-nhon-phu',
      name: 'Lò gạch gốm Nhơn Phú (Mang Thít)',
      lat: 10.1800,
      lng: 106.0800,
      type: 'heritage_pier',
    },
    waypoints: [
      { order: 1, name: 'Ngã ba Thầy Cai đón dòng phù sa', lat: 10.2600, lng: 106.0200, note: 'Điểm chuyển hướng từ Cổ Chiên vào kênh' },
      { order: 2, name: 'Kênh Thầy Cai rợp bóng dừa nước', lat: 10.2300, lng: 106.0400, note: 'Đoạn nước êm, mạn thuyền chạm tàu dừa' },
      { order: 3, name: 'Vòng cung lò gạch Mỹ Phước', lat: 10.2000, lng: 106.0600, note: 'Cụm lò gạch trăm năm soi bóng nước' },
      { order: 4, name: 'Bến lò gạch gốm đỏ Nhơn Phú', lat: 10.1800, lng: 106.0800, note: 'Bến gốm thủ công vương quốc gạch đỏ' },
    ],
    safety_advisory: 'Kênh nhiều khúc quanh hẹp và ghe chở trấu di chuyển chậm; giảm tốc độ khi qua ngã ba kênh.',
    terroir_highlights: [
      'Quần thể hàng ngàn lò gạch gốm đỏ hình chuông nung trấu trăm năm bên dòng kênh',
      'Những rặng dừa nước bạt ngàn xanh ngắt che mát mạn thuyền',
    ],
  },
  {
    id: 'route-my-thuan-tien-river',
    name: 'Thủy lộ Sông Tiền — Mỹ Thuận đến Cồn Phụng',
    corridor: 'Sông Tiền',
    distance_km: 32.0,
    typical_duration_minutes: 90,
    difficulty: 'nâng cao',
    recommended_craft: 'Tàu du lịch cỡ trung / ca nô',
    origin: {
      id: 'pier-my-thuan',
      name: 'Bến tàu Mỹ Thuận',
      lat: 10.2800,
      lng: 105.9100,
      type: 'major_pier',
    },
    destination: {
      id: 'con-phung-buffer',
      name: 'Vùng đệm Cồn Phụng (Chợ Lách)',
      lat: 10.3500,
      lng: 106.3300,
      type: 'island_pier',
    },
    waypoints: [
      { order: 1, name: 'Chân cầu Mỹ Thuận lịch sử', lat: 10.2800, lng: 105.9100, note: 'Cửa ngõ sông Tiền' },
      { order: 2, name: 'Cồn Đồng Phú phù sa', lat: 10.2900, lng: 106.0500, note: 'Bãi bồi trồng cây ăn trái' },
      { order: 3, name: 'Vàm rạch Chợ Lách miệt hoa kiểng', lat: 10.3200, lng: 106.2000, note: 'Điểm giao thoa văn hóa sông Tiền' },
      { order: 4, name: 'Bến Cồn Phụng rợp bóng dừa', lat: 10.3500, lng: 106.3300, note: 'Điểm kết thúc hành trình' },
    ],
    safety_advisory: 'Đoạn sông rộng gió lớn khi vào mùa chướng; theo dõi cảnh báo gió giật và mặc áo phao suốt hành trình.',
    terroir_highlights: [
      'Toàn cảnh kỳ vĩ của sông Tiền cuồn cuộn phù sa dưới nắng sớm',
      'Các cồn nổi trù phú đan xen giữa hai nhánh sông lớn',
    ],
  },
  {
    id: 'route-vung-liem-co-chien',
    name: 'Thủy lộ Phù Sa Vũng Liêm — Cù Lao Dài',
    corridor: 'Hạ lưu Sông Cổ Chiên',
    distance_km: 9.2,
    typical_duration_minutes: 40,
    difficulty: 'dễ',
    recommended_craft: 'Ghe tam bản / đò máy địa phương',
    origin: {
      id: 'pier-quoi-an',
      name: 'Bến phà Quới An',
      lat: 10.1500,
      lng: 106.1900,
      type: 'ferry_pier',
    },
    destination: {
      id: 'cu-lao-dai',
      name: 'Cù Lao Dài (Xã Thanh Bình)',
      lat: 10.0900,
      lng: 106.2600,
      type: 'island_pier',
    },
    waypoints: [
      { order: 1, name: 'Bến phà Quới An đón khách', lat: 10.1500, lng: 106.1900, note: 'Cửa ngõ cù lao' },
      { order: 2, name: 'Doi đất bồi đầu Cù Lao Dài', lat: 10.1300, lng: 106.2100, note: 'Vùng nước cạn khi triều rút' },
      { order: 3, name: 'Rạch rợp bóng bần Thanh Bình', lat: 10.1100, lng: 106.2300, note: 'Cảnh quan sông nước nguyên sơ' },
      { order: 4, name: 'Bến Cù Lao Dài cổ kính', lat: 10.0900, lng: 106.2600, note: 'Điểm hẹn miệt vườn sinh thái' },
    ],
    safety_advisory: 'Mép cù lao có bãi cát bồi ngầm khi triều rút; phương tiện cần đi theo tim luồng phao tiêu chỉ dẫn.',
    terroir_highlights: [
      'Dải cù lao cát dài nhất hạ lưu sông Cổ Chiên với những rặng sầu riêng trăm tuổi',
      'Khung cảnh yên ả với tiếng chèo khua nước và chim nước kiếm ăn ven bãi bồi',
    ],
  },
])

export function calculateBearing(
  origin: { lat: number; lng: number },
  destination: { lat: number; lng: number },
): number {
  const lat1 = (origin.lat * Math.PI) / 180
  const lat2 = (destination.lat * Math.PI) / 180
  const dLng = ((destination.lng - origin.lng) * Math.PI) / 180

  const y = Math.sin(dLng) * Math.cos(lat2)
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng)
  const brng = (Math.atan2(y, x) * 180) / Math.PI
  return (brng + 360) % 360
}

export function calculateRoutePropulsion(
  route: WaterEcoRouteDefinition,
  tide: AstronomicalTideResponse,
  _departureTime: Date = new Date(),
  craft: CraftType = 'sampan',
): EvaluatedWaterEcoRoute {
  const craftSpeed = craft === 'canoe' ? 8.0 : craft === 'kayak' ? 1.5 : 4.0
  const travelAzimuth = calculateBearing(route.origin, route.destination)
  const currentAzimuth = tide.current_azimuth_deg
  const vCurrent = tide.flow_velocity_ms

  const deltaRad = ((travelAzimuth - currentAzimuth) * Math.PI) / 180
  const alignmentCos = Math.cos(deltaRad)

  let direction: TidalPropulsionEvaluation['direction'] = 'cross_current'
  let effortSavingsPercentage = 0
  let narrativeAdvice = ''
  let recommendedWindow = '06:00 - 09:30 · Lúc con nước xuôi dòng'

  if (vCurrent < 0.15 || tide.water_flow_state === 'nuoc_dung') {
    direction = 'slack_water'
    effortSavingsPercentage = 0
    narrativeAdvice = 'Nước đứng · Sông êm, thuận lợi qua phà và cập bến cù lao.'
    recommendedWindow = 'Cả ngày · Sông tĩnh'
  } else if (alignmentCos >= 0.60) {
    direction = 'downstream_assist'
    const vRel = craftSpeed - vCurrent * alignmentCos
    const deltaP = 1 - Math.pow(vRel / craftSpeed, 2)
    effortSavingsPercentage = Math.round(deltaP * 1000) / 10
    narrativeAdvice = `Xuôi dòng nước · Tiết kiệm ~${Math.round(effortSavingsPercentage)}% lực đẩy ghe xuồng nhờ triều rút sông Cổ Chiên.`
    recommendedWindow = '06:00 - 09:30 · Lúc con nước xuôi dòng'
  } else if (alignmentCos <= -0.60) {
    direction = 'upstream_resistance'
    const vRel = craftSpeed + vCurrent * Math.abs(alignmentCos)
    const extraP = Math.pow(vRel / craftSpeed, 2) - 1
    effortSavingsPercentage = -Math.round(extraP * 1000) / 10
    narrativeAdvice = 'Ngược dòng triều cường · Khuyến nghị xuất bến sau khi đổi con nước hoặc chọn lộ trình đường bờ.'
    recommendedWindow = 'Chờ đổi dòng triều hoặc đi theo mé bồi'
  } else {
    direction = 'cross_current'
    effortSavingsPercentage = 0
    narrativeAdvice = 'Dòng chảy ngang · Cần giữ vững tay lái khi cắt luồng sông Cổ Chiên.'
    recommendedWindow = 'Chọn bến có doi đất chắn dòng'
  }

  const greenFuelFactor = Math.round((Math.max(0, effortSavingsPercentage) / 100) * 100) / 100

  return {
    ...route,
    tidal_propulsion: {
      direction,
      effort_savings_percentage: effortSavingsPercentage,
      flow_velocity_ms: vCurrent,
      travel_azimuth_deg: Math.round(travelAzimuth * 10) / 10,
      current_azimuth_deg: currentAzimuth,
      alignment_cos: Math.round(alignmentCos * 100) / 100,
      green_fuel_savings_factor: greenFuelFactor,
      narrative_advice: narrativeAdvice,
      recommended_departure_window: recommendedWindow,
    },
  }
}
