<template>
  <section v-if="hasContent" class="kbyg reveal">
    <div class="sediment-head kbyg-head">
      <h2 class="kbyg-title">
        <span class="emoji-chip" aria-hidden="true">🎒</span>
        Biết trước khi đi
      </h2>
    </div>

    <!-- Amenity badges -->
    <div v-if="amenities.length" class="kbyg-badges">
      <span v-for="b in amenities" :key="b.key" class="kbyg-badge" :title="b.label">
        <span class="kbyg-badge-icon emoji-chip" aria-hidden="true">{{ b.icon }}</span>
        <span class="kbyg-badge-text">{{ b.label }}</span>
      </span>
    </div>

    <!-- Golden hours -->
    <div v-if="goldenHours || peakDays" class="kbyg-golden">
      <div v-if="goldenHours" class="kbyg-golden-item">
        <span class="kbyg-golden-icon emoji-chip" aria-hidden="true">⏰</span>
        <div>
          <strong>Giờ vàng</strong>
          <span>{{ goldenHours }}</span>
        </div>
      </div>
      <div v-if="peakDays" class="kbyg-golden-item">
        <span class="kbyg-golden-icon emoji-chip" aria-hidden="true">📅</span>
        <div>
          <strong>Ngày đông</strong>
          <span>{{ peakDays }}</span>
        </div>
      </div>
      <div v-if="crowdLevel" class="kbyg-golden-item">
        <span class="kbyg-golden-icon emoji-chip" aria-hidden="true">👥</span>
        <div>
          <strong>Mức đông</strong>
          <span>{{ crowdLevel }}</span>
        </div>
      </div>
    </div>

    <!-- Tips -->
    <div v-if="tips.length" class="kbyg-tips">
      <div v-for="(tip, i) in tips" :key="i" class="kbyg-tip">
        <span class="kbyg-tip-icon emoji-chip" aria-hidden="true">💡</span>
        <span>{{ tip }}</span>
      </div>
    </div>

    <!-- Checklist -->
    <div v-if="checklist.length" class="kbyg-checklist">
      <h3 class="kbyg-checklist-title"><span class="emoji-chip" aria-hidden="true">🧳</span> Nên chuẩn bị</h3>
      <ul class="kbyg-check-list">
        <li v-for="(item, i) in checklist" :key="i" class="kbyg-check-item">
          <span class="kbyg-check-box" aria-hidden="true">☐</span>
          <span>{{ item }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
const props = defineProps<{
  attributes: Record<string, unknown> | null | undefined
  entityType: string
}>()

const AMENITY_MAP: Record<string, { icon: string; label: string }> = {
  wifi: { icon: '📶', label: 'Wi-Fi' },
  wheelchair: { icon: '♿', label: 'Xe lăn' },
  cash_only: { icon: '💵', label: 'Chỉ tiền mặt' },
  pet_friendly: { icon: '🐕', label: 'Thú cưng OK' },
  air_conditioned: { icon: '❄️', label: 'Máy lạnh' },
  kid_friendly: { icon: '👶', label: 'Trẻ em OK' },
  free_entry: { icon: '🆓', label: 'Miễn phí' },
  guided_tour: { icon: '🎙️', label: 'Có hướng dẫn' },
  restroom: { icon: '🚻', label: 'Nhà vệ sinh' },
  photography: { icon: '📸', label: 'Chụp ảnh OK' },
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

const goldenHours = computed(() => (attrs.value.golden_hours as string) || '')
const peakDays = computed(() => (attrs.value.peak_days as string) || '')
const crowdLevel = computed(() => (attrs.value.crowd_level as string) || '')

const tips = computed(() => {
  const t = attrs.value.kbyg_tips
  if (Array.isArray(t)) return t.filter((s: unknown) => typeof s === 'string' && s.trim()) as string[]
  return []
})

const checklist = computed(() => {
  const custom = attrs.value.checklist
  if (Array.isArray(custom) && custom.length) return custom.filter((s: unknown) => typeof s === 'string' && s.trim()) as string[]
  return TYPE_CHECKLIST[props.entityType] || []
})

const hasContent = computed(() => amenities.value.length > 0 || goldenHours.value || peakDays.value || tips.value.length > 0 || checklist.value.length > 0)
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
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.kbyg::before {
  content: ""; position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-image: var(--grain); background-size: 120px 120px; opacity: .05;
}
.kbyg-head, .kbyg-badges, .kbyg-golden, .kbyg-tips, .kbyg-checklist { position: relative; z-index: 1; }
.kbyg-head { margin: 0 0 var(--space-4); }
.kbyg-title {
  display: flex; align-items: center; gap: var(--space-2);
  font-family: var(--font-editorial);
  font-size: var(--text-lg); font-weight: 600;
  margin: 0;
  color: var(--ink);
}

/* Emoji-in-chip idiom (replicated locally per-component; see PostCard.vue
   for the shared source pattern) — never a bare emoji beside serif text. */
.emoji-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.4em;
  padding: 0 .15em;
  border-radius: var(--radius-sm);
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
  transition: border-color .2s var(--ease-out, ease), transform .15s ease;
}
.kbyg-badge:hover { border-color: var(--amber-600); transform: scale(1.04); }
.kbyg-badge-icon { font-size: .9rem; background: transparent; padding: 0; min-width: 0; }

/* Golden hours */
.kbyg-golden {
  display: flex; flex-wrap: wrap; gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.kbyg-golden-item {
  display: flex; align-items: flex-start; gap: var(--space-2);
  padding: 10px 14px; border-radius: var(--radius-md);
  background: rgba(var(--accent-rgb), .08);
  flex: 1 1 160px; min-width: 160px;
}
.kbyg-golden-icon { font-size: 1.1rem; flex-shrink: 0; margin-top: 1px; }
.kbyg-golden-item strong { display: block; font-size: .78rem; color: var(--muted); margin-bottom: 2px; }
.kbyg-golden-item span { font-size: .88rem; font-variant-numeric: tabular-nums; }

/* Tips */
.kbyg-tips {
  display: flex; flex-direction: column; gap: var(--space-2);
  margin-bottom: var(--space-4);
}
.kbyg-tip {
  display: flex; align-items: flex-start; gap: var(--space-2);
  padding: var(--space-2) var(--space-3); border-radius: var(--radius-md);
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
