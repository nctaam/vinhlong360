export interface HarvestQuarter {
  key: 'spring' | 'bloom' | 'summer' | 'harvest' | 'flood'
  tag: string
  label: string
  description: string
}

export interface AgriculturalIndicator {
  id: string
  name: string
  category: 'fruit' | 'crop' | 'aquaculture'
  peak_season: string
  status: string
  terroir_origin: string
  flavor_profile: string
  certifications: string[]
}

export interface CulinaryIndicator {
  id: string
  name: string
  category: 'seasonal_dish' | 'traditional_dish'
  season_range: string
  status: string
  terroir_origin: string
  culinary_note: string
}

export interface SeasonalHarvestResponse {
  quarter: HarvestQuarter
  agricultural_indicators: AgriculturalIndicator[]
  culinary_indicators: CulinaryIndicator[]
}

export function resolveSeasonalHarvest(date: Date = new Date()): SeasonalHarvestResponse {
  // Vietnam month (1-12)
  const month = date.getMonth() + 1

  let quarter: HarvestQuarter = {
    key: 'harvest',
    tag: 'mùa thu hoạch',
    label: 'Mùa thu hoạch miệt vườn',
    description: 'Đồng quê trĩu quả, hợp trải nghiệm miệt vườn và thưởng thức tại chỗ.',
  }

  if (month >= 1 && month <= 3) {
    quarter = {
      key: 'spring',
      tag: 'mùa xuân',
      label: 'Mùa xuân hoa trái cù lao',
      description: 'Tiết trời thanh dịu, cam sành vụ sớm và dưa hấu bãi bồi trĩu ngọt.',
    }
  } else if (month >= 4 && month <= 5) {
    quarter = {
      key: 'bloom',
      tag: 'hoa trái',
      label: 'Mùa đơm hoa kết trái',
      description: 'Đầu mùa nắng ấm, sầu riêng Ri6 bắt đầu vào vụ, chôm chôm chín bói.',
    }
  } else if (month >= 6 && month <= 8) {
    quarter = {
      key: 'summer',
      tag: 'mùa trái cây',
      label: 'Cao điểm miệt vườn trái cây',
      description: 'Chôm chôm Java chín đỏ rực vườn cây, nhãn xuồng cơm vàng trĩu cành.',
    }
  } else if (month >= 9 && month <= 10) {
    quarter = {
      key: 'harvest',
      tag: 'mùa thu hoạch',
      label: 'Mùa thu hoạch miệt vườn',
      description: 'Đồng quê trĩu quả, hợp trải nghiệm miệt vườn và thưởng thức tại chỗ.',
    }
  } else {
    quarter = {
      key: 'flood',
      tag: 'mùa nước nổi',
      label: 'Mùa nước nổi sông Tiền & Cổ Chiên',
      description: 'Phù sa dâng tràn đồng nội, cá linh non về nguồn cùng hoa điên điển trổ vàng.',
    }
  }

  const allAgri: AgriculturalIndicator[] = [
    {
      id: 'buoi-nam-roi',
      name: 'Bưởi Năm Roi Bình Minh',
      category: 'fruit',
      peak_season: 'T8–T12',
      status: (month >= 8 && month <= 12) ? 'chính vụ' : 'nghịch vụ',
      terroir_origin: 'Vùng bãi bồi phù sa ven sông Hậu, thị xã Bình Minh',
      flavor_profile: 'Vị ngọt thanh pha chua dịu đặc trưng, múi ráo, tép mọng nước',
      certifications: ['Chỉ dẫn địa lý', 'OCOP 4 sao'],
    },
    {
      id: 'cam-sanh-tam-binh',
      name: 'Cam Sành Tam Bình',
      category: 'fruit',
      peak_season: 'T9–T11',
      status: (month >= 9 && month <= 11) ? 'chính vụ' : 'rải vụ',
      terroir_origin: 'Vùng đất sét pha phù sa sông Măng Thít, huyện Tam Bình',
      flavor_profile: 'Vỏ sần đậm tinh dầu, tép cam vàng óng, vị ngọt đậm đà',
      certifications: ['OCOP 3 sao'],
    },
    {
      id: 'khoai-lang-binh-tan',
      name: 'Khoai lang tím Nhật Bình Tân',
      category: 'crop',
      peak_season: 'T9–T11',
      status: (month >= 9 && month <= 11) ? 'thu hoạch rộ' : 'chăm sóc',
      terroir_origin: 'Vùng đất giồng cát phù sa bồi huyện Bình Tân',
      flavor_profile: 'Ruột tím thẫm, dẻo bùi tự nhiên, độ ngọt đượm',
      certifications: ['OCOP 4 sao'],
    },
    {
      id: 'sau-rieng-ri6',
      name: 'Sầu riêng Ri6 Bình Hòa Phước',
      category: 'fruit',
      peak_season: 'T4–T7',
      status: (month >= 4 && month <= 7) ? 'chính vụ' : 'cuối vụ',
      terroir_origin: 'Cù lao An Bình, huyện Long Hồ',
      flavor_profile: 'Cơm vàng hạt lép, béo ngậy đượm hương, không xơ',
      certifications: ['OCOP 4 sao'],
    },
  ]

  const allCulinary: CulinaryIndicator[] = [
    {
      id: 'lau-ca-linh-bong-dien-dien',
      name: 'Lẩu cá linh bông điên điển',
      category: 'seasonal_dish',
      season_range: 'T8–T11',
      status: (month >= 8 && month <= 11) ? 'đỉnh vụ nước nổi' : 'chờ vụ nước mới',
      terroir_origin: 'Hạ lưu sông Cổ Chiên & đồng bằng Vĩnh Long',
      culinary_note: 'Cá linh non đầu mùa xương mềm, béo ngậy nấu lẩu me thanh mát cùng hoa điên điển vàng tươi hái ven sông',
    },
    {
      id: 'canh-chua-ca-linh-bong-sung',
      name: 'Canh chua cá linh bông súng ma',
      category: 'seasonal_dish',
      season_range: 'T8–T11',
      status: (month >= 8 && month <= 11) ? 'đang mùa' : 'trái mùa',
      terroir_origin: 'Đồng trũng phù sa sông Tiền',
      culinary_note: 'Bông súng ma thân dài giòn ngọt kết hợp cá linh non nấu me dốt chấm nước mắm nhĩ ớt hiểm',
    },
    {
      id: 'lau-mam-ca-linh',
      name: 'Lẩu mắm miệt vườn cá linh & cá sặc',
      category: 'traditional_dish',
      season_range: 'Quanh năm',
      status: 'quanh năm',
      terroir_origin: 'Làng nghề ủ mắm truyền thống phù sa Nam Bộ',
      culinary_note: 'Cốt mắm ủ lu sành đậm đà ăn kèm hơn 20 loại rau đồng nội miệt vườn',
    },
  ]

  return {
    quarter,
    agricultural_indicators: allAgri,
    culinary_indicators: allCulinary,
  }
}
