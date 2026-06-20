// B2 — default suggested-route data for /tuyen-duong.
// Editable via the CMS key `tuyen_duong.routes` (JSON). The page reads
// override-or-default, so it renders identically until an admin edits it and
// reverts to these defaults if the override is cleared.

export interface RouteStop { name: string; note?: string }
export interface RouteDef {
  id: string
  name: string
  emoji: string
  area: string
  duration: string
  distance: string
  description: string
  stops: RouteStop[]
  tips?: string
}

export const DEFAULT_ROUTES: RouteDef[] = [
  {
    id: 'vong-trai-cay-vinh-long',
    name: 'Vòng trái cây Vĩnh Long',
    emoji: '🍊',
    area: 'vinh-long',
    duration: '1 ngày',
    distance: '~40 km',
    description: 'Vòng lặp qua các vườn trái cây dọc cù lao An Bình và Bình Hòa Phước — thưởng thức trái cây tại vườn, ghé homestay miệt vườn và tận hưởng sông nước.',
    stops: [
      { name: 'Bến phà An Bình', note: 'Xuất phát từ TP Vĩnh Long' },
      { name: 'Vườn chôm chôm cù lao An Bình', note: 'Hái và thưởng thức tại vườn' },
      { name: 'Vườn nhãn Bình Hòa Phước', note: 'Mùa nhãn T5-T7' },
      { name: 'Homestay miệt vườn', note: 'Nghỉ trưa, ăn cơm vườn' },
      { name: 'Vườn bưởi Năm Roi', note: 'Đặc sản Vĩnh Long' },
      { name: 'Chợ Vĩnh Long', note: 'Mua đặc sản mang về' },
    ],
    tips: 'Đi vào mùa chôm chôm (T5-T7) để tận hưởng trọn vẹn. Mang theo mũ, kem chống nắng.',
  },
  {
    id: 'vong-dua-ben-tre',
    name: 'Vòng dừa Bến Tre',
    emoji: '🥥',
    area: 'ben-tre',
    duration: '1 ngày',
    distance: '~35 km',
    description: 'Khám phá xứ dừa từ gốc đến thành phẩm — thăm rẫy dừa, cơ sở kẹo dừa, xưởng mật hoa dừa và thưởng thức ẩm thực dừa.',
    stops: [
      { name: 'Cồn Phụng', note: 'Di tích + vườn dừa' },
      { name: 'Cơ sở kẹo dừa', note: 'Xem quy trình làm kẹo, mua sỉ' },
      { name: 'Xưởng mật hoa dừa', note: 'Sản phẩm OCOP 4 sao' },
      { name: 'Vườn bưởi da xanh', note: 'Trái cây đặc trưng Bến Tre' },
      { name: 'Chợ Bến Tre', note: 'Đặc sản: bánh tráng, bánh phồng' },
    ],
    tips: 'Kết hợp chèo xuồng trên rạch dừa. Nên đi sáng sớm để tránh nắng.',
  },
  {
    id: 'vong-chua-khmer-tra-vinh',
    name: 'Vòng chùa Khmer Trà Vinh',
    emoji: '🛕',
    area: 'tra-vinh',
    duration: '1–2 ngày',
    distance: '~60 km',
    description: 'Tuyến văn hóa Khmer độc đáo — ghé thăm các chùa cổ hàng trăm năm, ao Bà Om huyền thoại và thưởng thức bún nước lèo chính gốc.',
    stops: [
      { name: 'Ao Bà Om', note: 'Di tích lịch sử, cây cổ thụ' },
      { name: 'Chùa Âng', note: 'Chùa Khmer cổ nhất Trà Vinh' },
      { name: 'Chùa Hang', note: 'Kiến trúc hang động độc đáo' },
      { name: 'Làng Khmer', note: 'Tìm hiểu đời sống văn hóa' },
      { name: 'Quán bún nước lèo', note: 'Món đặc trưng Trà Vinh' },
      { name: 'Vườn dừa sáp Cầu Kè', note: 'Dừa sáp chỉ có ở đây' },
    ],
    tips: 'Mặc trang phục lịch sự khi vào chùa. Nên thuê xe máy cho linh hoạt.',
  },
  {
    id: 'vong-lang-nghe-mang-thit',
    name: 'Vòng làng nghề Mang Thít',
    emoji: '🏺',
    area: 'vinh-long',
    duration: 'Nửa ngày',
    distance: '~20 km',
    description: 'Khám phá "vương quốc gạch gốm" — thăm các lò gốm truyền thống, xem nghệ nhân tạo hình và mua gốm thủ công mang về.',
    stops: [
      { name: 'Làng gốm Mang Thít', note: 'Hàng trăm lò gốm dọc sông' },
      { name: 'Xưởng gốm truyền thống', note: 'Xem nghệ nhân làm gốm' },
      { name: 'Lò gạch cổ', note: 'Chụp ảnh, tìm hiểu lịch sử' },
      { name: 'Chợ gốm', note: 'Mua sản phẩm gốm thủ công' },
    ],
    tips: 'Kết hợp với Vòng trái cây cho chuyến đi trọn ngày. Đi buổi sáng khi lò đang hoạt động.',
  },
  {
    id: 'vong-am-thuc-mien-tay',
    name: 'Vòng ẩm thực miền Tây',
    emoji: '🍲',
    area: 'vinh-long',
    duration: '1–2 ngày',
    distance: '~50 km',
    description: 'Tour ẩm thực xuyên 3 tỉnh — từ bánh xèo Vĩnh Long, kẹo dừa Bến Tre đến bún nước lèo Trà Vinh.',
    stops: [
      { name: 'Quán cháo cá lóc Vĩnh Long', note: 'Bữa sáng đậm chất miền Tây' },
      { name: 'Bánh xèo miệt vườn', note: 'Cuốn rau vườn, chấm nước mắm' },
      { name: 'Chợ Vĩnh Long', note: 'Ăn vặt: hủ tiếu, bánh tầm' },
      { name: 'Kẹo dừa Bến Tre', note: 'Nếm + mua về làm quà' },
      { name: 'Bún nước lèo Trà Vinh', note: 'Món Khmer không thể bỏ qua' },
    ],
    tips: 'Đi vào cuối tuần để trải nghiệm chợ phiên. Mang dạ dày trống!',
  },
  {
    id: 'vong-mua-nuoc-noi',
    name: 'Vòng mùa nước nổi',
    emoji: '🌊',
    area: 'vinh-long',
    duration: '1 ngày',
    distance: '~30 km',
    description: 'Trải nghiệm mùa nước nổi (T8-T11) — hái bông điên điển, bắt cá linh, thưởng thức lẩu cá linh bông điên điển giữa đồng nước.',
    stops: [
      { name: 'Cánh đồng mùa nước nổi', note: 'Hái bông điên điển, bông súng' },
      { name: 'Điểm bắt cá linh', note: 'Trải nghiệm đánh bắt cùng nông dân' },
      { name: 'Quán lẩu cá linh', note: 'Món đặc trưng mùa nước nổi' },
      { name: 'Đồng sen', note: 'Chụp ảnh, hái sen (nếu có)' },
    ],
    tips: 'Chỉ có từ tháng 8 đến tháng 11. Mang áo mưa và giày chống nước.',
  },
]
