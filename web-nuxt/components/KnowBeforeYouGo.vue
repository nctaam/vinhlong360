<template>
  <section v-if="hasContent" class="kbyg reveal">
    <div class="sediment-head kbyg-head">
      <h2 class="kbyg-title">
        <IconLine class="icon-chip" name="briefcase" aria-hidden="true" />
        Biết trước khi đi
      </h2>
      <div v-if="hasTimeSensitiveFacts" class="kbyg-evidence" data-kbyg-evidence>
        <SourceMark :tier="sourceTier" compact />
        <FreshnessLine :status="freshnessStatus" :updated-label="updatedLabel" />
      </div>
    </div>

    <!-- Amenity badges -->
    <div v-if="amenities.length" class="kbyg-badges">
      <span v-for="b in amenities" :key="b.key" class="kbyg-badge" :title="b.label">
        <IconLine class="kbyg-badge-icon" :name="b.icon" aria-hidden="true" />
        <span class="kbyg-badge-text">{{ b.label }}</span>
      </span>
    </div>

    <!-- Golden hours -->
    <dl v-if="hasTimeSensitiveFacts" class="kbyg-golden" data-kbyg-facts>
      <div v-if="goldenHours" class="kbyg-golden-item">
        <dt><IconLine class="kbyg-golden-icon" name="clock" aria-hidden="true" /><span>Giờ vàng</span></dt>
        <dd>{{ goldenHours }}</dd>
      </div>
      <div v-if="peakDays" class="kbyg-golden-item">
        <dt><IconLine class="kbyg-golden-icon" name="calendar" aria-hidden="true" /><span>Ngày đông</span></dt>
        <dd>{{ peakDays }}</dd>
      </div>
      <div v-if="crowdLevel" class="kbyg-golden-item">
        <dt><IconLine class="kbyg-golden-icon" name="users" aria-hidden="true" /><span>Mức đông</span></dt>
        <dd>{{ crowdLevel }}</dd>
      </div>
    </dl>

    <!-- Practical facts (booking, fee, transport, parking, access) -->
    <dl v-if="practicalItems.length" class="kbyg-practical" data-kbyg-practical>
      <div v-for="item in practicalItems" :key="item.label" class="kbyg-practical-item">
        <dt>
          <IconLine class="kbyg-practical-icon" :name="item.icon" aria-hidden="true" />
          <span>{{ item.label }}</span>
        </dt>
        <dd>{{ item.value }}</dd>
      </div>
    </dl>

    <!-- Tips -->
    <div v-if="tips.length" class="kbyg-tips">
      <div v-for="(tip, i) in tips" :key="i" class="kbyg-tip">
        <IconLine class="kbyg-tip-icon" name="bulb" aria-hidden="true" />
        <span>{{ tip }}</span>
      </div>
    </div>

    <!-- Checklist -->
    <div v-if="checklist.length" class="kbyg-checklist">
      <h3 class="kbyg-checklist-title"><IconLine class="icon-chip" name="clipboard-list" aria-hidden="true" /> Nên chuẩn bị</h3>
      <ul class="kbyg-check-list">
        <li v-for="(item, i) in checklist" :key="i" class="kbyg-check-item">
          <IconLine class="kbyg-check-box" name="check" aria-hidden="true" />
          <span>{{ item }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { FreshnessStatus, SourceTier } from '../utils/regionalColor'

const props = withDefaults(defineProps<{
  attributes: Record<string, unknown> | null | undefined
  entityType: string
  sourceTier?: SourceTier
  freshnessStatus?: FreshnessStatus
  updatedLabel?: string
}>(), {
  sourceTier: 'unknown',
  freshnessStatus: 'unknown',
  updatedLabel: '',
})

const AMENITY_MAP: Record<string, { icon: string; label: string }> = {
  wifi: { icon: 'wind', label: 'Wi-Fi' },
  wheelchair: { icon: 'users', label: 'Xe lăn' },
  cash_only: { icon: 'tag', label: 'Chỉ tiền mặt' },
  pet_friendly: { icon: 'heart', label: 'Thú cưng OK' },
  air_conditioned: { icon: 'wind', label: 'Máy lạnh' },
  kid_friendly: { icon: 'users', label: 'Trẻ em OK' },
  free_entry: { icon: 'check', label: 'Miễn phí' },
  guided_tour: { icon: 'message', label: 'Có hướng dẫn' },
  restroom: { icon: 'building', label: 'Nhà vệ sinh' },
  photography: { icon: 'camera', label: 'Chụp ảnh OK' },
}

const TYPE_CHECKLIST: Record<string, string[]> = {
  attraction: ['Kem chống nắng', 'Nước uống', 'Giày thoải mái', 'Máy ảnh'],
  temple: ['Trang phục lịch sự', 'Nước uống', 'Tiền lẻ cúng dường'],
  pagoda: ['Trang phục lịch sự', 'Nước uống', 'Tiền lẻ cúng dường'],
  market: ['Tiền mặt (tiền lẻ)', 'Túi đựng đồ', 'Nón/mũ'],
  eco_tourism: ['Kem chống nắng', 'Thuốc chống muỗi', 'Giày đi bộ', 'Nước uống', 'Áo mưa'],
  craft_village: ['Tiền mặt', 'Túi đựng quà', 'Máy ảnh'],
  island: ['Kem chống nắng', 'Áo phao (nếu đi thuyền)', 'Nước uống', 'Dép đi nước'],
  dish: [],
  product: [],
  accommodation: ['CMND/CCCD', 'Đồ dùng cá nhân'],
  event: ['Xác nhận vé/đăng ký', 'Nước uống'],
  festival: ['Kem chống nắng', 'Nước uống', 'Máy ảnh', 'Tiền mặt'],
}

const attrs = computed(() => props.attributes || {})

const amenities = computed(() => {
  const badges = attrs.value.amenity_badges
  if (Array.isArray(badges)) {
    return badges.map((key: string) => {
      const meta = AMENITY_MAP[key]
      return meta ? { key, ...meta } : null
    }).filter(Boolean) as { key: string; icon: string; label: string }[]
  }
  const result: { key: string; icon: string; label: string }[] = []
  for (const [key, meta] of Object.entries(AMENITY_MAP)) {
    if (attrs.value[key]) result.push({ key, ...meta })
  }
  if (attrs.value.family_friendly) {
    const kidFriendly = AMENITY_MAP.kid_friendly
    if (kidFriendly && !result.some(r => r.key === 'kid_friendly')) {
      result.push({ key: 'kid_friendly', ...kidFriendly })
    }
  }
  return result
})

const goldenHours = computed(() => (attrs.value.golden_hours as string) || (attrs.value.best_time as string) || '')
const peakDays = computed(() => (attrs.value.peak_days as string) || '')
const crowdLevel = computed(() => (attrs.value.crowd_level as string) || '')
const hasTimeSensitiveFacts = computed(() => Boolean(goldenHours.value || peakDays.value || crowdLevel.value))

const practicalItems = computed(() => {
  const a = attrs.value
  const items: { icon: string; label: string; value: string }[] = []
  if (a.highlight) items.push({ icon: 'sparkles', label: 'Điểm nhấn', value: String(a.highlight) })
  if (a.booking_note) items.push({ icon: 'clipboard-list', label: 'Đặt trước', value: String(a.booking_note) })
  if (a.fee) items.push({ icon: 'tag', label: 'Phí vào cửa', value: String(a.fee) })
  if (a.transport) items.push({ icon: 'car', label: 'Di chuyển', value: String(a.transport) })
  if (a.parking) items.push({ icon: 'pin', label: 'Đậu xe', value: String(a.parking) })
  if (a.vehicle_access) items.push({ icon: 'car', label: 'Tiếp cận xe', value: String(a.vehicle_access) })
  if (a.family_friendly || (Array.isArray(a.suitable_for) && a.suitable_for.includes('family'))) {
    if (!amenities.value.some(b => b.key === 'kid_friendly')) {
      items.push({ icon: 'users', label: 'Gia đình', value: 'Phù hợp cho gia đình có trẻ em' })
    }
  }
  return items
})

const tips = computed(() => {
  const result: string[] = []
  const t = attrs.value.kbyg_tips
  if (Array.isArray(t)) {
    for (const s of t) {
      if (typeof s === 'string' && s.trim() && !result.includes(s.trim())) result.push(s.trim())
    }
  }
  const tt = attrs.value.travel_tips
  if (Array.isArray(tt)) {
    for (const s of tt) {
      if (typeof s === 'string' && s.trim() && !result.includes(s.trim())) result.push(s.trim())
    }
  }
  return result
})

const checklist = computed(() => {
  const custom = attrs.value.checklist
  if (Array.isArray(custom) && custom.length) return custom.filter((s: unknown) => typeof s === 'string' && s.trim()) as string[]
  return TYPE_CHECKLIST[props.entityType] || []
})

const hasContent = computed(() =>
  amenities.value.length > 0 ||
  goldenHours.value ||
  peakDays.value ||
  crowdLevel.value ||
  practicalItems.value.length > 0 ||
  tips.value.length > 0 ||
  checklist.value.length > 0
)
</script>

<style scoped>
/* Editorial frame: hairline + faint grain replaces the flat tinted-box
   idiom — reads as a printed sidebar note, not an app info-card. Grain
   sits on its own low-opacity layer (matches EntityCard.vue/PhotoGallery.vue
   convention) rather than tiling at full strength against --card. */
.kbyg {
  position: relative;
  margin: var(--space-6) 0;
  padding: var(--space-5);
  background: var(--card, var(--bg));
  border: 1px solid var(--line);
  border-radius: var(--radius-sheet);
  overflow: hidden;
}
.kbyg::before {
  content: ""; position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-image: var(--grain); background-size: 120px 120px; opacity: .05;
}
.kbyg-head, .kbyg-badges, .kbyg-golden, .kbyg-tips, .kbyg-checklist { position: relative; z-index: 1; }
.kbyg-head { display: grid; gap: var(--space-2); margin: 0 0 var(--space-4); }
.kbyg-title {
  display: flex; align-items: center; gap: var(--space-2);
  font-family: var(--font-editorial);
  font-size: var(--text-lg); font-weight: 600;
  margin: 0;
  color: var(--ink);
}

/* Compact line-icon treatment keeps labels scannable without glyph artwork. */
.icon-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.4em;
  padding: 0 .15em;
  border-radius: var(--radius-control);
  background: var(--bg-alt);
  font-size: .9em;
  line-height: 1.4;
}

/* Amenity badges */
.kbyg-badges {
  display: flex; flex-wrap: wrap; gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.kbyg-badge {
  display: inline-flex; align-items: center; gap: var(--space-1);
  padding: 5px 12px; border-radius: var(--radius-full);
  font-size: .8rem; font-weight: 500;
  background: var(--bg-alt);
  border: 1px solid var(--line);
  color: var(--ink);
  transition: border-color .2s var(--ease-out), transform .15s ease;
}
.kbyg-badge:hover { border-color: var(--amber-600); transform: scale(1.04); }
.kbyg-badge-icon { font-size: .9rem; background: transparent; padding: 0; min-width: 0; }

/* Golden hours */
.kbyg-golden {
  display: flex; flex-wrap: wrap; gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.kbyg-golden-item {
  display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--space-1);
  padding: 10px 14px; border-radius: var(--radius-surface);
  background: rgba(var(--accent-rgb), .08);
  flex: 1 1 160px; min-width: 160px;
}
.kbyg-golden-icon { font-size: 1.1rem; flex-shrink: 0; }
.kbyg-golden-item dt { display: flex; align-items: center; gap: var(--space-2); font-size: .78rem; font-weight: var(--weight-semibold); color: var(--muted); }
.kbyg-golden-item dd { margin: 0; font-size: .88rem; font-variant-numeric: tabular-nums; }
.kbyg-evidence { display: flex; flex-wrap: wrap; gap: var(--space-2); align-items: center; }

/* Practical facts */
.kbyg-practical {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.kbyg-practical-item {
  display: grid; grid-template-columns: minmax(0, 1fr); gap: var(--space-1);
  padding: 10px 14px; border-radius: var(--radius-surface);
  background: var(--bg-alt); border: 1px solid var(--line);
}
.kbyg-practical-item dt {
  display: flex; align-items: center; gap: var(--space-2);
  font-size: .78rem; font-weight: var(--weight-semibold); color: var(--muted);
  text-transform: uppercase; letter-spacing: .04em;
}
.kbyg-practical-icon { font-size: 1rem; flex-shrink: 0; color: var(--color-action); }
.kbyg-practical-item dd { margin: 0; font-size: .88rem; color: var(--ink); line-height: 1.4; }

/* Tips */
.kbyg-tips {
  display: flex; flex-direction: column; gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.kbyg-tip {
  display: flex; align-items: flex-start; gap: var(--space-2);
  padding: var(--space-2) var(--space-3); border-radius: var(--radius-surface);
  background: rgba(var(--secondary-rgb), .06);
  font-size: .88rem; line-height: 1.45;
}
.kbyg-tip-icon { flex-shrink: 0; font-size: .9rem; margin-top: 1px; }

/* Checklist */
.kbyg-checklist { margin-top: var(--space-3); padding-top: var(--space-3); border-top: 1px solid var(--line); }
.kbyg-checklist-title {
  display: flex; align-items: center; gap: var(--space-2);
  font-size: .9rem; font-weight: 600;
  margin: 0 0 var(--space-2);
  color: var(--ink);
}
.kbyg-check-list {
  list-style: none; margin: 0; padding: 0;
  display: flex; flex-wrap: wrap; gap: 6px 12px;
}
.kbyg-check-item {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: .84rem; color: var(--muted);
}
.kbyg-check-box { font-size: .7rem; opacity: .5; }

/* Dark mode */
.dark .kbyg { border-color: var(--line); }
.dark .kbyg::before { opacity: .08; }
.dark .kbyg-badge { border-color: var(--line); }
.dark .kbyg-badge:hover { border-color: var(--amber-500); }
.dark .kbyg-golden-item { background: rgba(var(--accent-rgb), .12); }
.dark .kbyg-tip { background: rgba(var(--secondary-rgb), .1); }

@media (max-width: 540px) {
  .kbyg { padding: var(--space-4); }
  .kbyg-golden { flex-direction: column; }
}

@media (prefers-reduced-motion: reduce) {
  .kbyg-badge:hover { transform: none; }
}
</style>
