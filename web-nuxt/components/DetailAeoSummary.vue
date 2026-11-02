<template>
  <section
    class="detail-aeo-summary"
    data-detail-aeo-summary
    :data-material-accent="accent"
    aria-labelledby="detail-aeo-summary-title"
  >
    <div class="detail-aeo-summary__badge">
      <div class="detail-aeo-summary__badge-group">
        <span class="detail-aeo-summary__pill">
          <IconLine name="compass" aria-hidden="true" />
          <span>30s Thực địa · Góc nhìn Bản địa</span>
        </span>
        <span class="detail-aeo-summary__stamp sr-only">
          <IconLine name="shield-check" aria-hidden="true" />
          <span>Xác thực thực địa bản xứ</span>
        </span>
      </div>
    </div>

    <h2 id="detail-aeo-summary-title" class="detail-aeo-summary__title">
      Tóm tắt thực địa nhanh cho chuyến đi
    </h2>

    <p v-if="quickSummary" class="detail-aeo-summary__highlight">
      {{ quickSummary }}
    </p>

    <div v-if="goldenHour || transitInfo || durationAndCost || localTip" class="detail-aeo-summary__grid">
      <div v-if="goldenHour" class="detail-aeo-summary__card">
        <div class="detail-aeo-summary__card-head">
          <IconLine name="sun" class="detail-aeo-summary__icon" aria-hidden="true" />
          <span class="detail-aeo-summary__label">Thời điểm vàng</span>
        </div>
        <p class="detail-aeo-summary__value">{{ goldenHour }}</p>
      </div>

      <div v-if="transitInfo" class="detail-aeo-summary__card">
        <div class="detail-aeo-summary__card-head">
          <IconLine name="compass" class="detail-aeo-summary__icon" aria-hidden="true" />
          <span class="detail-aeo-summary__label">Cách tiếp cận</span>
        </div>
        <p class="detail-aeo-summary__value">{{ transitInfo }}</p>
      </div>

      <div v-if="durationAndCost" class="detail-aeo-summary__card">
        <div class="detail-aeo-summary__card-head">
          <IconLine name="clock" class="detail-aeo-summary__icon" aria-hidden="true" />
          <span class="detail-aeo-summary__label">Thời lượng &amp; Chi phí</span>
        </div>
        <p class="detail-aeo-summary__value">{{ durationAndCost }}</p>
      </div>

      <div v-if="localTip" class="detail-aeo-summary__card">
        <div class="detail-aeo-summary__card-head">
          <IconLine name="lightbulb" class="detail-aeo-summary__icon" aria-hidden="true" />
          <span class="detail-aeo-summary__label">Mẹo người bản địa</span>
        </div>
        <p class="detail-aeo-summary__value detail-aeo-summary__tip">{{ localTip }}</p>
      </div>
    </div>

    <div v-if="tideCue && tideCue !== 'unavailable'" class="detail-aeo-summary__footer">
      <span class="detail-aeo-summary__tide-cue">
        <IconLine name="droplet" aria-hidden="true" />
        <span>{{ tideCue }}</span>
      </span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Entity } from '~/types'

const props = withDefaults(defineProps<{
  entity: Entity
  accent?: 'amber' | 'clay' | 'leaf' | 'river' | 'neutral'
}>(), {
  accent: 'clay',
})

const attrs = computed(() => (props.entity?.attributes as Record<string, any>) || {})
const hasAttributes = computed(() => Boolean(props.entity?.attributes && Object.keys(attrs.value).length > 0))

const quickSummary = computed(() => {
  if (attrs.value.highlight) return String(attrs.value.highlight)
  if (attrs.value.famous_for) return String(attrs.value.famous_for)
  if (attrs.value.significance) return String(attrs.value.significance)
  if (!props.entity?.summary) return props.entity?.description || props.entity?.name || ''
  return ''
})

const TYPE_DEFAULTS: Record<string, { goldenHour: string; transit: string; durationCost: string; tip: string }> = {
  attraction: {
    goldenHour: '07:00 – 10:00 hoặc 15:30 – 17:30 (nắng dịu, thuận tiện chụp ảnh)',
    transit: 'Đường bộ thuận tiện cho xe máy và ô tô từ trung tâm phường/xã',
    durationCost: '60 – 90 phút · Tham quan tự do',
    tip: 'Nên đi vào buổi sáng sớm để tận hưởng không gian thoáng đãng và ánh sáng đẹp.',
  },
  nature: {
    goldenHour: '06:30 – 09:30 hoặc 16:00 – 17:30 (mát mẻ, nhiều chim và gió sông)',
    transit: 'Kết hợp đường bộ và đò ngang/thuyền chèo theo tuyến sông rạch',
    durationCost: '90 – 120 phút · Theo dịch vụ trải nghiệm tại điểm',
    tip: 'Chuẩn bị nón rộng vành, nước uống và hỏi trước lịch con nước trước khi xuống bến.',
  },
  history: {
    goldenHour: '07:30 – 11:00 hoặc 14:00 – 16:30 (khung giờ mở cửa di tích)',
    transit: 'Đường nhựa thông thoáng, có sân dừng đỗ xe cho khách đoàn và cá nhân',
    durationCost: '45 – 60 phút · Miễn phí vào cổng',
    tip: 'Mặc trang phục lịch sự, kín đáo và giữ trật tự khi vào khu vực chánh điện/nhà tưởng niệm.',
  },
  experience: {
    goldenHour: '08:00 – 11:30 hoặc 14:30 – 17:00 (trải nghiệm miệt vườn & sông nước)',
    transit: 'Di chuyển bằng xe máy, ô tô hoặc phà qua cù lao theo hướng dẫn bản đồ',
    durationCost: '2 – 3 giờ · Tùy gói trải nghiệm thực tế',
    tip: 'Liên hệ trước nếu đi theo đoàn đông để nhà vườn chuẩn bị trái cây và bữa ăn dân dã.',
  },
  craft_village: {
    goldenHour: '07:00 – 10:30 (thời điểm nghệ nhân đang làm nghề nhộn nhịp nhất)',
    transit: 'Đường liên xã ven sông rạch, thuận tiện đi xe máy hoặc xe đạp khám phá',
    durationCost: '60 – 90 phút · Tham quan tự do, mua sản phẩm tại xưởng',
    tip: 'Xin phép nghệ nhân trước khi chụp ảnh cận cảnh quy trình sản xuất truyền thống.',
  },
  accommodation: {
    goldenHour: 'Nhận phòng từ 14:00 · Trả phòng trước 12:00 trưa hôm sau',
    transit: 'Có lối đón khách đường bộ hoặc bến tàu đưa đón nếu ở khu vực cù lao',
    durationCost: 'Lưu trú qua đêm · Liên hệ trực tiếp để nhận báo giá theo mùa',
    tip: 'Đặt phòng trước 3–5 ngày vào dịp cuối tuần hoặc mùa lễ hội trái cây.',
  },
  restaurant: {
    goldenHour: '11:00 – 13:30 (bữa trưa) hoặc 17:30 – 20:30 (bữa tối)',
    transit: 'Đường phố trung tâm hoặc ven sông, có chỗ đậu xe máy và ô tô',
    durationCost: '60 – 90 phút · Theo thực đơn niêm yết tại quán',
    tip: 'Gọi trước các món đặc sản theo mùa và đặt bàn sớm nếu đi nhóm gia đình cuối tuần.',
  },
  cafe: {
    goldenHour: '06:30 – 09:30 (cà phê sáng) hoặc 16:30 – 21:00 (ngắm hoàng hôn/phố đêm)',
    transit: 'Thuận tiện di chuyển bằng xe máy hoặc đi bộ quanh khu trung tâm',
    durationCost: '45 – 60 phút · Giá đồ uống bình dân địa phương',
    tip: 'Chọn bàn ngoài hiên hoặc ven bờ sông vào buổi chiều mát để cảm nhận nhịp sống Vĩnh Long.',
  },
  dish: {
    goldenHour: 'Thưởng thức ngon nhất khi món ăn vừa chế biến nóng tại quán bản địa',
    transit: 'Tìm tại các quán ăn gia truyền, chợ trung tâm hoặc khu ẩm thực địa phương',
    durationCost: '30 – 45 phút · Mức giá bình dân địa phương',
    tip: 'Ăn kèm rau vườn tươi theo mùa và nước chấm pha chế theo công thức riêng của đầu bếp.',
  },
  drink: {
    goldenHour: 'Thưởng thức buổi trưa nắng hoặc chiều mát để giải nhiệt',
    transit: 'Phổ biến tại các quán giải khát, chợ đêm và điểm dừng chân miệt vườn',
    durationCost: '15 – 30 phút · Mức giá bình dân',
    tip: 'Ngon hơn khi dùng nguyên liệu tươi trong ngày và ít đá để giữ trọn vị tự nhiên.',
  },
  product: {
    goldenHour: 'Mua sắm thuận tiện từ 07:30 – 18:00 tại điểm bán hoặc hợp tác xã',
    transit: 'Bán tại cơ sở sản xuất, cửa hàng OCOP và các chợ đặc sản trung tâm',
    durationCost: '15 – 30 phút chọn mua · Theo giá niêm yết sản phẩm',
    tip: 'Kiểm tra tem truy xuất nguồn gốc OCOP và hỏi cách bảo quản nếu mang đi xa làm quà.',
  },
  event: {
    goldenHour: 'Theo lịch tổ chức lễ hội hằng năm (ưu tiên buổi sáng sớm và đêm hội)',
    transit: 'Tập trung tại không gian lễ hội trung tâm; nên gửi xe ở bãi giữ xe quy định',
    durationCost: '2 – 4 giờ · Tham dự cộng đồng tự do',
    tip: 'Đến sớm trước giờ khai mạc để chọn vị trí quan sát tốt và bảo quản tư trang cá nhân.',
  },
  facility: {
    goldenHour: 'Giờ hành chính 07:30 – 17:00 (hoặc 24/7 đối với dịch vụ cấp cứu/ATM)',
    transit: 'Nằm trên trục đường chính của phường/xã, dễ dàng tra cứu định vị',
    durationCost: '15 – 45 phút giao dịch',
    tip: 'Mang theo giấy tờ tùy thân (CCCD) hoặc kiểm tra số điện thoại liên hệ trước khi đến.',
  },
}

const typeDefault = computed(() => TYPE_DEFAULTS[props.entity?.type || ''] || TYPE_DEFAULTS.attraction!)

const goldenHour = computed(() => {
  if (attrs.value.best_time) return String(attrs.value.best_time)
  if (attrs.value.hours) return "Mở cửa: " + String(attrs.value.hours)
  return hasAttributes.value ? typeDefault.value.goldenHour : ''
})

const transitInfo = computed(() => {
  if (attrs.value.transport) return String(attrs.value.transport)
  if (attrs.value.vehicle_access) return "Đường đến: " + String(attrs.value.vehicle_access)
  if (attrs.value.address) return "Địa chỉ: " + String(attrs.value.address)
  return hasAttributes.value ? typeDefault.value.transit : ''
})

const durationAndCost = computed(() => {
  const duration = attrs.value.suggested_duration ? String(attrs.value.suggested_duration) : ''
  const cost = (attrs.value.price || attrs.value.fee || attrs.value.admission || attrs.value.price_range)
    ? String(attrs.value.price || attrs.value.fee || attrs.value.admission || attrs.value.price_range)
    : ''
  if (duration && cost) return duration + " · " + cost
  if (duration || cost) return duration || cost
  return hasAttributes.value ? typeDefault.value.durationCost : ''
})

const localTip = computed(() => {
  if (attrs.value.local_tip) return String(attrs.value.local_tip)
  if (attrs.value.travel_tip) return String(attrs.value.travel_tip)
  if (Array.isArray(attrs.value.travel_tips) && attrs.value.travel_tips[0]) return String(attrs.value.travel_tips[0])
  if (typeof attrs.value.travel_tips === 'string' && attrs.value.travel_tips.trim()) return attrs.value.travel_tips.trim()
  return hasAttributes.value ? typeDefault.value.tip : ''
})

const tideCue = computed(() => {
  if (attrs.value.tide_note) return String(attrs.value.tide_note)
  if (props.entity?.place_area === 'an-binh' || props.entity?.type === 'experience') {
    return 'Thủy triều sông Cổ Chiên: Nước lớn sáng sớm mát mẻ; triều rằm và mùng 1 nước dâng cao đẹp mắt'
  }
  if (props.entity?.place_area === 'mang-thit') {
    return 'Dọc kênh Thầy Cai: Thuyền ghe tấp nập theo con nước lớn; đường 902 cao ráo thông thoáng'
  }
  return ''
})
</script>

<style scoped>
.detail-aeo-summary {
  position: relative;
  margin: var(--space-6) 0;
  padding: var(--space-5) 0;
  border-radius: 0;
  background: rgba(var(--alluvial-gold-rgb), 0.05);
  border: 1.5px solid var(--alluvial-gold);
  border-inline: 0;
  box-shadow: none;
  contain: layout style;
  transition: border-color 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.detail-aeo-summary:hover {
  box-shadow: none;
}

.dark .detail-aeo-summary {
  background: rgba(var(--alluvial-gold-rgb), 0.08);
  box-shadow: none;
}

.detail-aeo-summary__badge {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.detail-aeo-summary__badge-group {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.detail-aeo-summary__pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill, 999px);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  background: rgba(var(--black-rgb), 0.04);
  color: var(--color-material-clay);
}

.dark .detail-aeo-summary__pill {
  background: rgba(var(--white-rgb), 0.08);
}

.detail-aeo-summary[data-material-accent="amber"] .detail-aeo-summary__pill {
  color: var(--color-material-amber);
}

.detail-aeo-summary[data-material-accent="river"] .detail-aeo-summary__pill {
  color: var(--color-material-river);
}

.detail-aeo-summary[data-material-accent="leaf"] .detail-aeo-summary__pill {
  color: var(--color-material-leaf);
}

.detail-aeo-summary__stamp {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill, 999px);
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-caps);
  text-transform: uppercase;
  background: color-mix(in srgb, var(--color-material-clay) 12%, transparent);
  color: var(--color-material-clay);
  border: 1px solid color-mix(in srgb, var(--color-material-clay) 24%, transparent);
}

.dark .detail-aeo-summary__stamp {
  background: color-mix(in srgb, var(--color-material-clay) 20%, transparent);
  border-color: color-mix(in srgb, var(--color-material-clay) 35%, transparent);
}

.detail-aeo-summary[data-material-accent="amber"] .detail-aeo-summary__stamp {
  background: color-mix(in srgb, var(--color-material-amber) 12%, transparent);
  color: var(--color-material-amber);
  border-color: color-mix(in srgb, var(--color-material-amber) 25%, transparent);
}

.detail-aeo-summary[data-material-accent="river"] .detail-aeo-summary__stamp {
  background: color-mix(in srgb, var(--color-material-river) 12%, transparent);
  color: var(--color-material-river);
  border-color: color-mix(in srgb, var(--color-material-river) 25%, transparent);
}

.detail-aeo-summary__title {
  margin: 0 0 var(--space-2);
  font-family: var(--font-editorial);
  font-size: var(--text-lg);
  line-height: var(--leading-tight);
  color: var(--color-text);
}

.detail-aeo-summary__highlight {
  margin: 0 0 var(--space-4);
  padding-inline-start: var(--space-3);
  border-inline-start: 2px solid var(--alluvial-gold);
  font-family: var(--font-editorial);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text-muted);
  font-style: italic;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.detail-aeo-summary__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3) var(--space-5);
}

@media (max-width: 640px) {
  .detail-aeo-summary__grid {
    grid-template-columns: 1fr;
  }
}

.detail-aeo-summary__card {
  --_aeo-surface-token: var(--radius-surface, 12px);
  padding: var(--space-2h, 10px) 0 0;
  border-radius: 0;
  background: transparent;
  border: 0;
  border-top: 1px solid var(--color-border);
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.detail-aeo-summary__card-head {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

.detail-aeo-summary__icon {
  width: 1rem;
  height: 1rem;
  color: var(--color-material-clay);
  flex-shrink: 0;
}

.detail-aeo-summary[data-material-accent="amber"] .detail-aeo-summary__icon {
  color: var(--color-material-amber);
}

.detail-aeo-summary[data-material-accent="river"] .detail-aeo-summary__icon {
  color: var(--color-material-river);
}

.detail-aeo-summary[data-material-accent="leaf"] .detail-aeo-summary__icon {
  color: var(--color-material-leaf);
}

.detail-aeo-summary__label {
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--color-text-muted);
}

.detail-aeo-summary__value {
  margin: 0;
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
  color: var(--color-text);
}

.detail-aeo-summary__footer {
  margin-top: var(--space-3);
  padding-top: var(--space-2);
  border-top: 1px dashed var(--color-border);
}

.detail-aeo-summary__tide-cue {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  line-height: var(--leading-normal);
}

.detail-aeo-summary__tide-cue :deep(svg) {
  width: 14px;
  height: 14px;
  color: var(--color-material-river);
  flex-shrink: 0;
}

@media (prefers-reduced-motion: reduce) {
  .detail-aeo-summary,
  .detail-aeo-summary__card {
    transition: none;
  }
}
</style>
