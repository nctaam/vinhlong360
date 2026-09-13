<template>
  <svg
    class="vernacular-glyph"
    :class="[
      `glyph--${normalizedName}`,
      accentClass ? `glyph--accent-${accentClass}` : '',
      { 'glyph--interactive': interactive }
    ]"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.6"
    stroke-linecap="round"
    stroke-linejoin="round"
    :width="resolvedSize"
    :height="resolvedSize"
    :style="customStyle"
    :role="role"
    :aria-label="ariaLabelText"
    :aria-hidden="role === 'presentation' || !ariaLabelText ? 'true' : undefined"
    v-html="glyphInnerSvg"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface VernacularGlyphProps {
  name: string
  size?: number | string
  color?: string
  accent?: 'clay' | 'silt' | 'culao' | 'cochien' | 'ink' | 'current'
  role?: string
  ariaLabel?: string
  interactive?: boolean
}

const props = withDefaults(defineProps<VernacularGlyphProps>(), {
  size: 24,
  color: undefined,
  accent: 'current',
  role: 'img',
  ariaLabel: undefined,
  interactive: false,
})

// Complete library of all 32 indigenous Mekong Delta vector glyphs
const GLYPHS: Record<string, string> = {
  // 1. Lò Gốm Tròn Mang Thít
  'mangthit-kiln': '<path d="M4 21h16M6 21v-8a6 6 0 0112 0v8M10 21v-4a2 2 0 014 0v4M12 7V3m-3 2h6"/>',
  // 2. Mắt Ghe Sông Tiền
  'mekong-boat-eye': '<ellipse cx="12" cy="12" rx="9" ry="5"/><circle cx="12" cy="12" r="2.5"/><path d="M3 12c3-4 15-4 18 0"/>',
  // 3. Hoa Bần Nở Đêm
  'barringtonia-flower': '<circle cx="12" cy="12" r="2"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M4.9 19.1l2.8-2.8M16.3 7.7l2.8-2.8"/>',
  // 4. Bông Súng Mùa Nước Nổi
  'water-lily': '<path d="M12 22s-6-4-6-10a6 6 0 0112 0c0 6-6 10-6 10zM12 12v6M9 9l3 3 3-3"/>',
  // 5. Xuồng Ba Lá Cửu Long
  'three-plank-sampan': '<path d="M2 15c4 3 16 3 20 0l-3 4H5l-3-4zM12 5v8M8 9l4-4 4 4"/>',
  // 6. Nón Lá Điền Dã
  'conical-hat': '<path d="M2 18L12 4l10 14H2zM12 4v14M6 14h12"/>',
  // 7. Khói Un Trấu Lò Gạch
  'rice-husk-smoke': '<path d="M8 21c-2-3-2-6 1-8s3-5 1-8M14 21c-2-3-2-6 1-8s3-5 1-8M11 16c-1-2-1-4 1-6"/>',
  // 8. Cây Dừa Cù Lao
  'coconut-palm': '<path d="M12 22c0-8 3-14 3-14M12 8c-3-2-7-2-9 1M12 8c3-2 7-2 9 1M12 7c-4-4-2-7 1-7M12 7c4-4 2-7-1-7M12 9c-2 3-5 5-8 5M12 9c2 3 5 5 8 5"/>',
  // 9. Bàn Xoay Vuốt Gốm
  'pottery-wheel': '<ellipse cx="12" cy="16" rx="8" ry="3"/><ellipse cx="12" cy="8" rx="5" ry="2"/><path d="M12 10v6M7 8v8M17 8v8"/>',
  // 10. Mái Đình Cổ Long Thanh
  'temple-roof': '<path d="M2 10l10-7 10 7M4 10v10h16V10M9 20v-6h6v6M3 10h18"/>',
  // 11. Cái Lờ Bẫy Cá
  'fishing-basket': '<path d="M4 8c4-2 12-2 16 0v8c-4 2-12 2-16 0V8zM8 7v10M16 7v10"/>',
  // 12. Dòng Phù Sa Cổ Chiên
  'silt-current': '<path d="M3 7c3-2 6-2 9 0s6 2 9 0M3 12c3-2 6-2 9 0s6 2 9 0M3 17c3-2 6-2 9 0s6 2 9 0"/>',
  // 13. Gió Mùa Sông Nước
  'wind-monsoon': '<path d="M4 8h12a3 3 0 10-3-3M2 12h16a3 3 0 11-3 3M5 16h8a2 2 0 10-2-2"/>',
  // 14. Kính Lão Điền Dã
  'elder-glasses': '<circle cx="7" cy="13" r="4"/><circle cx="17" cy="13" r="4"/><path d="M11 13h2M7 9V6M17 9V6"/>',
  // 15. Nắng Gắt Sông Nước
  'sun-glare': '<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.2 2.2M16.9 16.9l2.2 2.2M4.9 19.1l2.2-2.2M16.9 7.1l2.2-2.2"/>',
  // 16. Hoa Văn Bảo An Thẻ Bỏ Túi
  'guilloche-pass': '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8c2 2 2 6 0 8M17 8c-2 2-2 6 0 8M3 12h18"/>',
  // 17. Con Dấu Sáp Đỏ Nung
  'wax-seal': '<path d="M12 2l3 5 6 1-4 4 1 6-6-3-6 3 1-6-4-4 6-1 3-5z"/>',
  // 18. Búp Sen Xanh Cù Lao
  'green-lotus': '<path d="M12 3c-3 4-5 8-5 12 0 4 3 6 5 6s5-2 5-6c0-4-2-8-5-12zM7 15c-3-2-4-5-4-8 4 1 7 4 8 8M17 15c3-2 4-5 4-8-4 1-7 4-8 8"/>',
  // 19. La Bàn Điền Dã
  'field-compass': '<circle cx="12" cy="12" r="9"/><polygon points="12 6 14 12 12 18 10 12"/><circle cx="12" cy="12" r="1"/>',
  // 20. Đề Xuất Lộ Trình Thuận Nước (Eco-Routing)
  'eoc-routing': '<path d="M3 12c3-3 6-3 9 0s6 3 9 0M16 8l5 4-5 4M3 6c2-1 4-1 6 0M3 18c2 1 4 1 6 0"/>',
  // 21. Viên Gạch Mộc Đất Nung
  'ancient-brick': '<path d="M3 8l9-4 9 4-9 4-9-4zM3 8v8l9 4 9-4V8M12 12v8"/>',
  // 22. Tàu Dừa Nước Ven Sông
  'water-coconut': '<path d="M12 21V3M12 3c-4 3-7 8-7 13M12 3c4 3 7 8 7 13M12 9c-3 1-5 4-5 7M12 9c3 1 5 4 5 7"/>',
  // 23. Nhịp Con Nước Lớn Ròng
  'lunar-tide': '<path d="M12 3a9 9 0 100 18 7 7 0 010-18zM3 21c3-1 6-1 9 0s6 1 9 0"/>',
  // 24. Trái Chôm Chôm Miệt Vườn
  'rambutan-fruit': '<circle cx="12" cy="13" r="6"/><path d="M12 7V3M10 3h4M6 10l-3-2M18 10l3-2M6 16l-3 2M18 16l3 2M12 19v3"/>',
  // 25. Trái Sầu Riêng Ri6 Cơm Vàng
  'durian-orchard': '<ellipse cx="12" cy="13" rx="7" ry="8"/><path d="M12 5V2M10 2h4M7 8l-2-1M17 8l2-1M5 13H2M22 13h-3M7 18l-2 1M17 18l2 1M12 9v8"/>',
  // 26. Khối Ghi Chú Lề Học Thuật Edward Tufte
  'tufte-marginalia': '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h5M4 3v18"/>',
  // 27. Bến Đò Ngang / Bến Phà
  'ferry-landing': '<path d="M3 17h18M5 17l2-6h10l2 6M12 11V5M9 7h6M2 21h20"/>',
  // 28. Chài Lưới Quăng Sông
  'mekong-net': '<path d="M12 2L3 20h18L12 2zM7 12h10M5 16h14M9 8h6M12 2v18"/>',
  // 29. Nghệ Nhân Vuốt Gốm
  'clay-artisan': '<circle cx="12" cy="7" r="4"/><path d="M5 21v-3a4 4 0 014-4h6a4 4 0 014 4v3M8 14l-3 4M16 14l3 4"/>',
  // 30. Đỉnh Tháp Chùa Nam Tông Khmer
  'pagoda-spire': '<path d="M12 2v4M10 6h4M12 6l-4 7h8l-4-7zM7 13l-3 8h16l-3-8H7zM10 17h4"/>',
  // 31. Vườn Chim Tràm Sông Nước
  'bird-sanctuary': '<path d="M2 13c3-3 6-3 8 0 2-3 5-3 8 0M10 13c1 3 3 5 6 6M4 9c2-2 4-2 6 0M14 9c2-2 4-2 6 0"/>',
  // 32. Châu Thổ Ba Nhánh Sông
  'sediment-delta': '<path d="M12 2v8M12 10L6 22M12 10l6 12M3 17c3-1 6-1 9 0s6 1 9 0"/>',
}

// Synonyms / aliases mapping for robustness
const ALIASES: Record<string, string> = {
  'mang-thit-kiln': 'mangthit-kiln',
  'eco-routing': 'eoc-routing',
  'water-coconut-palm': 'water-coconut',
  'ancient-communal-roof': 'temple-roof',
  'communal-house': 'temple-roof',
  'fish-trap-lo': 'fishing-basket',
  'bamboo-fish-trap': 'fishing-basket',
  'water-tide-pulse': 'silt-current',
  'elder-reading': 'elder-glasses',
  'high-glare-sun': 'sun-glare',
  'pocket-pass': 'guilloche-pass',
  'sourcemark-seal': 'wax-seal',
  'provenance-seal': 'wax-seal',
  'sourcemark-stamp': 'wax-seal',
  'lotus-lamp-ao-ba-om': 'green-lotus',
  'lotus-leaf': 'green-lotus',
  'clay-brick': 'ancient-brick',
  'tide-high': 'lunar-tide',
  'tide-low': 'lunar-tide',
  'durian-ri6': 'durian-orchard',
  'field-dossier-scroll': 'tufte-marginalia',
  'monocle-quill': 'tufte-marginalia',
  'ferry-crossing': 'ferry-landing',
  'an-binh-ferry': 'ferry-landing',
  'safe-haven': 'ferry-landing',
  'earthenware-jar': 'clay-artisan',
  'khmer-kbach-ornament': 'pagoda-spire',
  'co-chien-wave': 'sediment-delta',
  'nam-roi-pomelo': 'rambutan-fruit',
}

const normalizedName = computed(() => {
  const raw = (props.name || '').trim().toLowerCase()
  if (GLYPHS[raw]) return raw
  if (ALIASES[raw]) return ALIASES[raw]
  return 'mangthit-kiln' // Graceful fallback per epistemic spec
})

const glyphInnerSvg = computed(() => {
  return GLYPHS[normalizedName.value] || GLYPHS['mangthit-kiln']
})

const resolvedSize = computed(() => {
  if (typeof props.size === 'number') return props.size
  switch (props.size) {
    case 'sm': return 16
    case 'md': return 24
    case 'lg': return 32
    case 'xl': return 48
    default: {
      const parsed = parseInt(props.size, 10)
      return Number.isNaN(parsed) ? 24 : parsed
    }
  }
})

const accentClass = computed(() => {
  if (props.accent && props.accent !== 'current') return props.accent
  return ''
})

const customStyle = computed(() => {
  if (!props.color) return undefined
  const c = props.color.trim().toLowerCase()
  if (c === 'clay' || c === 'mangthit') return { color: 'var(--mangthit-500)' }
  if (c === 'silt' || c === 'harvest') return { color: 'var(--harvest-600)' }
  if (c === 'culao' || c === 'orchard' || c === 'leaf') return { color: 'var(--orchard-600)' }
  if (c === 'cochien' || c === 'river') return { color: 'var(--river-600)' }
  if (c === 'ink') return { color: 'var(--mekong-ink)' }
  if (c === 'gold') return { color: 'var(--alluvial-gold)' }
  return { color: props.color }
})

const ariaLabelText = computed(() => {
  if (props.ariaLabel) return props.ariaLabel
  return normalizedName.value.replace(/-/g, ' ')
})
</script>

<style scoped>
.vernacular-glyph {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
  transition: transform 0.3s var(--ease-terroir-flow, cubic-bezier(0.22, 1, 0.36, 1));
}

.glyph--interactive:hover {
  transform: scale(1.1);
}

.glyph--accent-clay { color: var(--mangthit-500); }
.glyph--accent-silt { color: var(--harvest-600); }
.glyph--accent-culao { color: var(--orchard-600); }
.glyph--accent-cochien { color: var(--river-600); }
.glyph--accent-ink { color: var(--mekong-ink); }
</style>
