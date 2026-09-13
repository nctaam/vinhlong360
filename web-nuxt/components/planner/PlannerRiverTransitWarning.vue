<template>
  <div
    v-if="hasRiverTransit"
    class="planner-river-transit"
    data-planner-river-transit
    role="region"
    aria-labelledby="river-transit-title"
  >
    <div class="planner-river-transit__head">
      <span class="planner-river-transit__icon" aria-hidden="true">
        <IconLine name="ship" />
      </span>
      <div class="planner-river-transit__meta">
        <div class="planner-river-transit__title-row">
          <h3 id="river-transit-title" class="planner-river-transit__title">
            Lưu ý đò phà &amp; nhịp sông nước thực địa
          </h3>
          <MekongWaterBadge :interactive="false" compact />
        </div>
        <p class="planner-river-transit__dek">
          Hành trình của bạn có chặng qua sông Tiền / Cổ Chiên hoặc các cù lao miệt vườn.
        </p>
      </div>
    </div>

    <ul class="planner-river-transit__list">
      <li v-for="(tip, idx) in transitTips" :key="idx" class="planner-river-transit__item">
        <IconLine name="clock" class="planner-river-transit__bullet" aria-hidden="true" />
        <span>{{ tip }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MekongWaterBadge from '~/components/MekongWaterBadge.vue'

const props = defineProps<{
  stops: Array<{ id?: string; name?: string; place_area?: string; place_name?: string; attributes?: Record<string, any> }>
}>()

const hasRiverTransit = computed(() => {
  if (!props.stops || props.stops.length < 2) return false
  const areas = new Set(props.stops.map(s => s.place_area).filter(Boolean))
  const hasWaterCrossing = props.stops.some(s => {
    const text = `${s.name || ''} ${s.place_name || ''} ${s.place_area || ''}`.toLowerCase()
    return (
      s.place_area === 'an-binh' ||
      s.place_area === 'mang-thit' ||
      text.includes('cù lao') ||
      text.includes('an bình') ||
      text.includes('đình khao') ||
      text.includes('thầy cai') ||
      text.includes('chợ lách') ||
      text.includes('phà') ||
      text.includes('đò')
    )
  })
  return areas.size >= 2 || hasWaterCrossing
})

const transitTips = computed(() => {
  const tips: string[] = []
  const hasAnBinh = props.stops.some(s => {
    const text = `${s.name || ''} ${s.place_name || ''} ${s.place_area || ''}`.toLowerCase()
    return s.place_area === 'an-binh' || text.includes('an bình') || text.includes('cù lao')
  })
  const hasDinhKhao = props.stops.some(s => {
    const text = `${s.name || ''} ${s.place_name || ''} ${s.place_area || ''}`.toLowerCase()
    return text.includes('đình khao') || text.includes('chợ lách') || text.includes('bến tre')
  })
  const hasMangThit = props.stops.some(s => {
    const text = `${s.name || ''} ${s.place_name || ''} ${s.place_area || ''}`.toLowerCase()
    return s.place_area === 'mang-thit' || text.includes('mang thít') || text.includes('thầy cai') || text.includes('gốm')
  })

  if (hasAnBinh) {
    tips.push('Phà An Bình (sông Cổ Chiên): Hoạt động liên tục từ 4h30 đến 22h00; ban đêm sau 22h chuyển sang chuyến giãn cách (30–45 phút) hoặc đò bao.')
  }
  if (hasDinhKhao || (!hasAnBinh && !hasMangThit)) {
    tips.push('Phà Đình Khao (nối Vĩnh Long – Chợ Lách Bến Tre trên QL57 qua sông Cổ Chiên): Vận hành 24/24 liên tục; giờ cao điểm (6h30–8h00 và 16h30–18h00) có thể ùn ứ xe ô tô, nên chủ động thời gian.')
  }
  if (hasMangThit) {
    tips.push('Tuyến kênh Thầy Cai và các lò gốm Mang Thít thuận tiện đi thuyền vào buổi sáng khi con nước lớn (triều dâng); tránh giờ nước ròng cạn đáy bùn.')
  }
  tips.push('Lưu ý nhịp triều cường sông Cổ Chiên: Con nước rằm và mùng 1 có thể gây ngập nhẹ các tuyến đường đan ven rạch cù lao vào giờ đỉnh triều.')
  tips.push('Nên chuẩn bị tiền mặt lẻ mệnh giá nhỏ để mua vé phà và qua các đò ngang dọc tuyến cù lao.')
  return tips
})
</script>

<style scoped>
.planner-river-transit {
  margin: var(--space-4) 0;
  padding: var(--space-4);
  border-radius: var(--radius-sheet);
  background: var(--color-canvas);
  border: 1px solid var(--color-border);
  border-left: 4px solid var(--color-material-river);
  box-shadow: var(--shadow-sm);
}

.dark .planner-river-transit {
  box-shadow: 0 1px 3px rgba(var(--black-rgb), 0.2), 0 0 0 1px rgba(var(--white-rgb), 0.08);
}

.planner-river-transit__head {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.planner-river-transit__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: var(--radius-pill, 999px);
  background: rgba(var(--black-rgb), 0.04);
  color: var(--color-material-river);
  flex-shrink: 0;
}

.dark .planner-river-transit__icon {
  background: rgba(var(--white-rgb), 0.08);
}

.planner-river-transit__meta {
  flex: 1;
  min-width: 0;
}

.planner-river-transit__title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

.planner-river-transit__title {
  margin: 0;
  font-family: var(--font-editorial);
  font-size: var(--text-base);
  font-weight: var(--weight-bold);
  color: var(--color-text);
}

.planner-river-transit__dek {
  margin: 0;
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
  color: var(--color-text-muted);
}

.planner-river-transit__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.planner-river-transit__item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
  color: var(--color-text);
}

.planner-river-transit__bullet {
  width: 0.875rem;
  height: 0.875rem;
  margin-top: 0.15rem;
  color: var(--color-material-river);
  flex-shrink: 0;
}
</style>
