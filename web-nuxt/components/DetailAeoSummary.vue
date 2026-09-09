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
          <IconLine name="sparkles" aria-hidden="true" />
          <span>30s Thực địa · Góc nhìn Bản địa</span>
        </span>
        <span class="detail-aeo-summary__stamp">
          <IconLine name="shield-check" aria-hidden="true" />
          <span>Xác thực thực địa bản xứ</span>
        </span>
      </div>
      <span class="detail-aeo-summary__watermark" aria-hidden="true">AEO</span>
    </div>

    <h2 id="detail-aeo-summary-title" class="detail-aeo-summary__title">
      Tóm tắt thực địa nhanh cho chuyến đi
    </h2>

    <p v-if="quickSummary" class="detail-aeo-summary__highlight">
      {{ quickSummary }}
    </p>

    <div class="detail-aeo-summary__grid">
      <div class="detail-aeo-summary__card">
        <div class="detail-aeo-summary__card-head">
          <IconLine name="sun" class="detail-aeo-summary__icon" aria-hidden="true" />
          <span class="detail-aeo-summary__label">Thời điểm vàng</span>
        </div>
        <p class="detail-aeo-summary__value">{{ goldenHour }}</p>
      </div>

      <div class="detail-aeo-summary__card">
        <div class="detail-aeo-summary__card-head">
          <IconLine name="compass" class="detail-aeo-summary__icon" aria-hidden="true" />
          <span class="detail-aeo-summary__label">Cách tiếp cận</span>
        </div>
        <p class="detail-aeo-summary__value">{{ transitInfo }}</p>
      </div>

      <div class="detail-aeo-summary__card">
        <div class="detail-aeo-summary__card-head">
          <IconLine name="clock" class="detail-aeo-summary__icon" aria-hidden="true" />
          <span class="detail-aeo-summary__label">Thời lượng &amp; Chi phí</span>
        </div>
        <p class="detail-aeo-summary__value">{{ durationAndCost }}</p>
      </div>

      <div class="detail-aeo-summary__card">
        <div class="detail-aeo-summary__card-head">
          <IconLine name="lightbulb" class="detail-aeo-summary__icon" aria-hidden="true" />
          <span class="detail-aeo-summary__label">Mẹo người bản địa</span>
        </div>
        <p class="detail-aeo-summary__value detail-aeo-summary__tip">{{ localTip }}</p>
      </div>
    </div>

    <div class="detail-aeo-summary__footer">
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

const quickSummary = computed(() => {
  return attrs.value.highlight || props.entity?.description || props.entity?.name
})

const goldenHour = computed(() => {
  if (attrs.value.best_time) return String(attrs.value.best_time)
  if (attrs.value.hours) return "Mở cửa: " + attrs.value.hours + " (đẹp nhất lúc 7h-9h hoặc 16h-17h30)"
  if (props.entity?.type === 'craft_village') return 'Sáng sớm 7h00 - 10h00 khi nghệ nhân vào mẻ gốm/dệt chiếu'
  if (props.entity?.type === 'experience') return '7h30 - 10h00 hoặc 15h30 - 17h30 tránh nắng gắt trên sông'
  if (props.entity?.type === 'dish') return 'Bữa sáng 6h30 - 8h30 hoặc chiều tà 16h00 - 19h00'
  return 'Buổi sáng dịu mát 7h30 - 10h00 hoặc hoàng hôn bên sông'
})

const transitInfo = computed(() => {
  if (attrs.value.transport) return String(attrs.value.transport)
  if (attrs.value.vehicle_access) return "Đường đến: " + attrs.value.vehicle_access
  if (props.entity?.place_area === 'an-binh') return 'Qua phà An Bình (xe máy/ô tô), đi đường đan rợp bóng cây trái'
  if (props.entity?.place_area === 'mang-thit') return 'Đường tỉnh 902 hoặc theo thuyền dọc kênh Thầy Cai'
  return 'Đường nhựa ô tô vào tận nơi hoặc chuyển đò ngang qua sông'
})

const durationAndCost = computed(() => {
  const duration = attrs.value.suggested_duration || 'Khoảng 1.5 - 2.5 giờ'
  const cost = attrs.value.price || attrs.value.fee || attrs.value.price_range || 'Miễn phí hoặc chi tiêu tự do'
  return duration + " · " + cost
})

const localTip = computed(() => {
  if (attrs.value.local_tip) return String(attrs.value.local_tip)
  if (props.entity?.type === 'craft_village') return 'Nên xin phép trước khi chụp ảnh thợ lò gốm đang làm việc'
  if (props.entity?.type === 'experience') return 'Chuẩn bị tiền mặt lẻ để mua vé đò và thưởng thức trái cây miệt vườn'
  if (props.entity?.type === 'dish') return 'Hỏi người bản địa món ăn kèm hoặc rau đồng đúng mùa nước'
  return 'Mang mũ nón che nắng và mang theo bình nước cá nhân khi đi bộ'
})

const tideCue = computed(() => {
  if (attrs.value.tide_note) return String(attrs.value.tide_note)
  if (props.entity?.place_area === 'an-binh' || props.entity?.type === 'experience') {
    return 'Thủy triều sông Cổ Chiên: Nước lớn sáng sớm mát mẻ; triều rằm và mùng 1 nước dâng cao đẹp mắt'
  }
  if (props.entity?.place_area === 'mang-thit') {
    return 'Dọc kênh Thầy Cai: Thuyền ghe tấp nập theo con nước lớn; đường 902 cao ráo thông thoáng'
  }
  return 'Nhịp sống sông nước: Khởi hành buổi sớm ngắm bình minh trên sông Tiền & Cổ Chiên'
})
</script>

<style scoped>
.detail-aeo-summary {
  position: relative;
  margin: var(--space-6) 0;
  padding: var(--space-5);
  border-radius: var(--radius-sheet);
  background: var(--color-canvas);
  border: 1px solid var(--color-border);
  border-top: 3px solid var(--color-material-clay);
  box-shadow: 0 2px 8px -2px rgba(var(--black-rgb), 0.05), 0 0 0 1px rgba(var(--white-rgb), 0.5);
  contain: layout style;
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.detail-aeo-summary:hover {
  box-shadow: 0 4px 14px -2px rgba(var(--black-rgb), 0.08), 0 0 0 1px rgba(var(--white-rgb), 0.7);
}

.detail-aeo-summary[data-material-accent="amber"] {
  border-top-color: var(--color-material-amber);
}

.detail-aeo-summary[data-material-accent="leaf"] {
  border-top-color: var(--color-material-leaf);
}

.detail-aeo-summary[data-material-accent="river"] {
  border-top-color: var(--color-material-river);
}

.dark .detail-aeo-summary {
  box-shadow: 0 1px 3px rgba(var(--black-rgb), 0.2), 0 0 0 1px rgba(var(--white-rgb), 0.08);
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

.detail-aeo-summary__watermark {
  font-size: var(--text-2xs);
  font-weight: var(--weight-bold);
  letter-spacing: var(--tracking-caps);
  color: var(--color-text-muted);
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
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text-muted);
  font-style: italic;
}

.detail-aeo-summary__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

@media (max-width: 640px) {
  .detail-aeo-summary__grid {
    grid-template-columns: 1fr;
  }
}

.detail-aeo-summary__card {
  padding: var(--space-3);
  border-radius: var(--radius-surface, 12px);
  background: rgba(var(--black-rgb), 0.02);
  border: 1px solid var(--color-border);
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.dark .detail-aeo-summary__card {
  background: rgba(var(--white-rgb), 0.03);
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
