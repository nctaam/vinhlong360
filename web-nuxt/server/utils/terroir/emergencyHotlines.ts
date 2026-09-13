export interface CivicEmergencyHotline {
  readonly id: string
  readonly name: string
  readonly phone: string
  readonly tel_uri: string
  readonly service_scope: string
  readonly badge: string
  readonly priority: boolean
}

export const VERIFIED_EMERGENCY_HOTLINES: readonly CivicEmergencyHotline[] = Object.freeze([
  {
    id: 'rescue-waterway',
    name: 'CSGT & Cứu nạn Đường thủy',
    phone: '0270 3822 305',
    tel_uri: 'tel:+842703822305',
    service_scope: 'Tuần tra sông Tiền & Cổ Chiên, cứu hộ sự cố đò phà và tàu thuyền du lịch 24/7.',
    badge: 'Đường thủy 24/7',
    priority: true,
  },
  {
    id: 'rescue-medical',
    name: 'Cấp cứu Y tế 115 & BV Đa khoa Tỉnh',
    phone: '115',
    tel_uri: 'tel:115',
    service_scope: 'Điều phối xe cấp cứu lưu động và tiếp nhận hỗ trợ y tế khẩn cấp toàn tỉnh.',
    badge: 'Khẩn cấp 115',
    priority: true,
  },
  {
    id: 'rescue-police',
    name: 'Công an Tỉnh (Phản ứng nhanh)',
    phone: '113',
    tel_uri: 'tel:113',
    service_scope: 'Bảo đảm an ninh trật tự, hỗ trợ du khách bị thất lạc hoặc gặp sự cố an ninh.',
    badge: 'Trực ban 113',
    priority: false,
  },
  {
    id: 'rescue-ferry',
    name: 'Điều phối Phà An Bình',
    phone: '0270 3822 514',
    tel_uri: 'tel:+842703822514',
    service_scope: 'Hỗ trợ phương tiện qua sông Cổ Chiên, giải quyết sự cố bến phà đêm ngày.',
    badge: 'Vượt sông',
    priority: false,
  },
  {
    id: 'rescue-tourism',
    name: 'Cứu hộ Du lịch Vĩnh Long 360',
    phone: '0270 3822 188',
    tel_uri: 'tel:+842703822188',
    service_scope: 'Hỗ trợ hướng dẫn thực địa, giải quyết khúc mắc dịch vụ và phản ánh du lịch.',
    badge: 'Hỗ trợ du khách',
    priority: false,
  },
])
