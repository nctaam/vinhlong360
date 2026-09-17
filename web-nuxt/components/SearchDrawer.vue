<template>
  <Teleport to="body">
    <Transition name="drawer-fade">
      <div
        v-if="isOpen"
        class="search-drawer-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="search-drawer-title"
        aria-describedby="search-drawer-desc"
        @click.self="closeDrawer"
        @keydown="onKeydown"
      >
        <div class="search-drawer-scrim" aria-hidden="true" @click="closeDrawer" />

        <div
          ref="drawerRef"
          class="search-drawer-sheet"
          data-search-drawer
        >
          <!-- Drawer Header -->
          <header class="search-drawer-header">
            <div class="search-drawer-title-group">
              <div class="search-drawer-eyebrow">
                <VernacularGlyph name="mekong-boat-eye" :size="18" accent="silt" />
                <span id="search-drawer-desc">Chỉ mục Điểm đến &amp; Khu vực</span>
              </div>
              <h2 id="search-drawer-title" class="search-drawer-heading">
                Tìm kiếm Điền dã
              </h2>
            </div>

            <div class="search-drawer-controls">
              <span class="search-drawer-kbd-hint" aria-hidden="true">ESC</span>
              <button
                ref="closeBtnRef"
                type="button"
                class="search-drawer-close-btn"
                aria-label="Đóng khay tìm kiếm"
                @click="closeDrawer"
              >
                <IconLine name="x" aria-hidden="true" />
              </button>
            </div>
          </header>

          <!-- Omni Search Input Box -->
          <div class="search-drawer-input-wrap" role="search">
            <IconLine name="search" class="search-drawer-input-icon" aria-hidden="true" />
            <input
              ref="inputRef"
              v-model="searchQuery"
              type="search"
              class="search-drawer-input"
              placeholder="Tìm di sản, lò gạch, cù lao, món ngon…"
              aria-label="Nhập từ khóa tìm kiếm"
              enterkeyhint="search"
              @keydown.enter="executeSearch"
            />
            <button
              v-if="searchQuery.trim()"
              type="button"
              class="search-drawer-clear-btn"
              aria-label="Xóa từ khóa"
              @click="searchQuery = ''"
            >
              <IconLine name="x" aria-hidden="true" />
            </button>
          </div>

          <!-- Multi-dimensional Filter Groups -->
          <div class="search-drawer-filters">
            <!-- Dimension 1: Khu vực -->
            <section class="search-drawer-filter-group" aria-labelledby="filter-region-label">
              <h3 id="filter-region-label" class="search-drawer-filter-label">
                <VernacularGlyph name="mangthit-kiln" :size="16" accent="clay" />
                <span>Khu vực</span>
              </h3>
              <div class="search-drawer-chips" role="group" aria-label="Chọn khu vực">
                <button
                  v-for="region in REGIONS"
                  :key="region.key"
                  type="button"
                  :class="['search-drawer-chip', 'chip-region-' + region.key, { active: activeRegion === region.key }]"
                  :aria-pressed="activeRegion === region.key"
                  @click="toggleRegion(region.key)"
                >
                  <span class="chip-indicator" aria-hidden="true" />
                  <span>{{ region.label }}</span>
                </button>
              </div>
            </section>

            <!-- Dimension 2: Mùa Vụ & Thời Khắc -->
            <section class="search-drawer-filter-group" aria-labelledby="filter-season-label">
              <h3 id="filter-season-label" class="search-drawer-filter-label">
                <VernacularGlyph name="water-lily" :size="16" accent="culao" />
                <span>Mùa Vụ Sông Nước</span>
              </h3>
              <div class="search-drawer-chips" role="group" aria-label="Chọn mùa">
                <button
                  v-for="season in SEASONS"
                  :key="season.key"
                  type="button"
                  :class="['search-drawer-chip', { active: activeSeason === season.key }]"
                  :aria-pressed="activeSeason === season.key"
                  @click="toggleSeason(season.key)"
                >
                  <IconLine :name="season.icon" aria-hidden="true" />
                  <span>{{ season.label }}</span>
                </button>
              </div>
            </section>

            <!-- Dimension 3: Con Nước Triều Thiên Văn -->
            <section class="search-drawer-filter-group" aria-labelledby="filter-tide-label">
              <h3 id="filter-tide-label" class="search-drawer-filter-label">
                <VernacularGlyph name="three-plank-sampan" :size="16" accent="cochien" />
                <span>Nhịp Con Nước Triều Sông</span>
              </h3>
              <div class="search-drawer-chips" role="group" aria-label="Chọn con nước">
                <button
                  v-for="tide in TIDE_OPTIONS"
                  :key="tide.key"
                  type="button"
                  :class="['search-drawer-chip', { active: activeTide === tide.key }]"
                  :aria-pressed="activeTide === tide.key"
                  @click="toggleTide(tide.key)"
                >
                  <span class="tide-dot" aria-hidden="true" />
                  <span>{{ tide.label }}</span>
                </button>
              </div>
            </section>
          </div>

          <!-- Answer Plaques / Suggestions Section -->
          <div class="search-drawer-results" role="region" aria-label="Kết quả gợi ý">
            <div class="search-drawer-results-head">
              <span class="results-count-text">
                {{ displayedSuggestions.length > 0
                   ? `Gợi ý điền dã đối chiếu (${displayedSuggestions.length})`
                   : 'Không tìm thấy kết quả phù hợp (0)' }}
              </span>
              <button
                v-if="hasActiveFilters"
                type="button"
                class="search-drawer-reset-btn"
                aria-label="Đặt lại tất cả bộ lọc tìm kiếm"
                @click="resetFilters"
              >
                Đặt lại bộ lọc
              </button>
            </div>

            <div v-if="displayedSuggestions.length > 0" class="search-drawer-plaques">
              <article
                v-for="item in displayedSuggestions"
                :key="item.id"
                class="search-drawer-plaque"
              >
                <div class="plaque-header">
                  <span class="plaque-category-badge">{{ item.category }}</span>
                  <span class="plaque-coords">{{ item.coords }}</span>
                </div>
                <h4 class="plaque-title">
                  <NuxtLink :to="item.to" @click="closeDrawer">
                    {{ item.title }}
                  </NuxtLink>
                </h4>
                <p class="plaque-snippet">{{ item.snippet }}</p>
                <div class="plaque-meta">
                  <span class="plaque-tag">{{ item.tag }}</span>
                  <SourceMark
                    tier="official"
                    :source-title="item.sourceTitle"
                    verified-at="2026-09-13"
                    compact
                  />
                </div>
              </article>
            </div>

            <!-- Authentic Editorial Empty State -->
            <div
              v-else
              class="search-drawer-empty-state"
              role="status"
              aria-live="polite"
            >
              <div class="empty-state-icon-halo" aria-hidden="true">
                <VernacularGlyph name="three-plank-sampan" :size="36" accent="clay" />
              </div>
              <h4 class="empty-state-title">Chưa tìm thấy di sản hay tọa độ phù hợp</h4>
              <p class="empty-state-desc">
                <template v-if="searchQuery.trim()">
                  Không có dữ liệu thực địa nào khớp với từ khóa <em>"{{ searchQuery.trim() }}"</em> theo tiêu chí lọc hiện tại.
                </template>
                <template v-else>
                  Không có điểm đến nào thỏa mãn đồng thời các bộ lọc Khu vực, Mùa vụ và Con nước đã chọn.
                </template>
              </p>
              <button
                type="button"
                class="empty-state-reset-btn"
                aria-label="Đặt lại toàn bộ bộ lọc và từ khóa để xem danh mục"
                @click="resetFilters"
              >
                <IconLine name="repeat" aria-hidden="true" />
                <span>Đặt lại bộ lọc &amp; xem tất cả</span>
              </button>
            </div>
          </div>

          <!-- Bottom Action Dock -->
          <footer class="search-drawer-footer">
            <button
              type="button"
              class="search-drawer-submit-btn"
              @click="executeSearch"
            >
              <IconLine name="search" aria-hidden="true" />
              <span>Xem kết quả toàn cảnh</span>
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  modelValue?: boolean
  open?: boolean
}>(), {
  modelValue: false,
  open: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'update:open', val: boolean): void
  (e: 'close'): void
}>()

const isOpen = computed(() => props.open || props.modelValue)

const searchQuery = ref('')
const activeRegion = ref<'all' | 'mang-thit' | 'cu-lao-an-binh' | 'co-chien'>('all')
const activeSeason = ref<'all' | 'nuoc_noi' | 'trai_cay' | 'xuan_hoa' | 'kho_nang'>('all')
const activeTide = ref<'all' | 'rong' | 'kem' | 'lon' | 'rong_can'>('all')

const drawerRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const closeBtnRef = ref<HTMLButtonElement | null>(null)

const REGIONS = [
  { key: 'all' as const, label: 'Toàn tỉnh Vĩnh Long' },
  { key: 'mang-thit' as const, label: 'Mang Thít (Đất nung)' },
  { key: 'cu-lao-an-binh' as const, label: 'Cù lao An Bình (Miệt vườn)' },
  { key: 'co-chien' as const, label: 'Sông Cổ Chiên (Sông nước)' },
]

const SEASONS = [
  { key: 'all' as const, label: 'Cả năm', icon: 'calendar' },
  { key: 'nuoc_noi' as const, label: 'Nước nổi (T8–T11)', icon: 'droplet' },
  { key: 'trai_cay' as const, label: 'Trái chín (T5–T7)', icon: 'fruit' },
  { key: 'xuan_hoa' as const, label: 'Xuân hoa (T12–T2)', icon: 'sprout' },
  { key: 'kho_nang' as const, label: 'Khô ráo (T3–T5)', icon: 'sun' },
]

const TIDE_OPTIONS = [
  { key: 'all' as const, label: 'Mọi con nước' },
  { key: 'rong' as const, label: 'Nước rong (+1.75m)' },
  { key: 'kem' as const, label: 'Nước kém (êm dòng)' },
  { key: 'lon' as const, label: 'Nước lớn (ghe xuôi)' },
  { key: 'rong_can' as const, label: 'Nước ròng (lộ bãi gốm)' },
]

const CURATED_SUGGESTIONS = [
  {
    id: 'sug-1',
    region: 'mang-thit',
    season: 'all',
    tide: 'rong_can',
    category: 'Di sản Làng nghề',
    title: 'Quần thể Lò gạch gốm đỏ Mang Thít & Kênh Thầy Cai',
    snippet: 'Hơn 1.000 lò nung gạch thủ công hình vòm tròn trải dài ven kênh, rực đỏ sắc đất phù sa dưới nắng sớm.',
    coords: '10.254° N, 105.972° E',
    to: '/dia-diem/lang-gom-mang-thit',
    tag: 'Đề cử UNESCO',
    sourceTitle: 'Sở VHTTDL Vĩnh Long',
  },
  {
    id: 'sug-2',
    region: 'cu-lao-an-binh',
    season: 'trai_cay',
    tide: 'lon',
    category: 'Sinh thái Miệt vườn',
    title: 'Cù lao An Bình — Vườn chôm chôm & Bưởi Năm Roi',
    snippet: 'Dải đất phù sa giữa hai nhánh sông Tiền và Cổ Chiên, vườn cây trái sum suê trĩu cành bốn mùa mát rượi.',
    coords: '10.271° N, 105.989° E',
    to: '/dia-diem/cu-lao-an-binh',
    tag: 'OCOP 4 Sao',
    sourceTitle: 'UBND Tỉnh Vĩnh Long',
  },
  {
    id: 'sug-3',
    region: 'co-chien',
    season: 'nuoc_noi',
    tide: 'rong',
    category: 'Hành trình Sông nước',
    title: 'Tuyến đò ngang sông Cổ Chiên & Bến phà Đình Khao',
    snippet: 'Xuôi dòng nước lớn ngắm rặng bần xanh rì, thưởng thức canh chua cá linh bông điên điển mùa nước nổi.',
    coords: '10.260° N, 106.012° E',
    to: '/tuyen-duong',
    tag: 'Thuận dòng nước',
    sourceTitle: 'Cục Du lịch Quốc gia',
  },
]

const hasActiveFilters = computed(() => {
  return activeRegion.value !== 'all' || activeSeason.value !== 'all' || activeTide.value !== 'all' || searchQuery.value.trim() !== ''
})

const displayedSuggestions = computed(() => {
  let list = CURATED_SUGGESTIONS

  if (activeRegion.value !== 'all') {
    list = list.filter(item => item.region === activeRegion.value)
  }
  if (activeSeason.value !== 'all') {
    list = list.filter(item => item.season === 'all' || item.season === activeSeason.value)
  }
  if (activeTide.value !== 'all') {
    list = list.filter(item => item.tide === activeTide.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(item =>
      item.title.toLowerCase().includes(q) ||
      item.snippet.toLowerCase().includes(q) ||
      item.category.toLowerCase().includes(q)
    )
  }

  return list
})

function toggleRegion(key: typeof activeRegion.value) {
  activeRegion.value = activeRegion.value === key ? 'all' : key
}

function toggleSeason(key: typeof activeSeason.value) {
  activeSeason.value = activeSeason.value === key ? 'all' : key
}

function toggleTide(key: typeof activeTide.value) {
  activeTide.value = activeTide.value === key ? 'all' : key
}

function resetFilters() {
  activeRegion.value = 'all'
  activeSeason.value = 'all'
  activeTide.value = 'all'
  searchQuery.value = ''
}

function closeDrawer() {
  emit('update:modelValue', false)
  emit('update:open', false)
  emit('close')
}

function executeSearch() {
  const q = searchQuery.value.trim()
  closeDrawer()
  const params = new URLSearchParams()
  if (q) params.set('q', q)
  if (activeRegion.value !== 'all') params.set('region', activeRegion.value)
  if (activeSeason.value !== 'all') params.set('season', activeSeason.value)
  const queryStr = params.toString()
  navigateTo(queryStr ? '/tim-kiem?' + queryStr : '/tim-kiem')
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    e.stopPropagation()
    closeDrawer()
    return
  }

  // Focus trap
  if (e.key === 'Tab' && drawerRef.value) {
    const focusables = Array.from(
      drawerRef.value.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter(el => el.offsetParent !== null)

    if (focusables.length === 0) return

    const first = focusables[0]
    const last = focusables[focusables.length - 1]

    if (!first || !last) return

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }
}

watch(isOpen, (open) => {
  if (typeof document === 'undefined') return
  if (open) {
    document.body.style.overflow = 'hidden'
    nextTick(() => {
      inputRef.value?.focus()
    })
  } else {
    document.body.style.overflow = ''
  }
})

onMounted(() => {
  if (isOpen.value && typeof document !== 'undefined') {
    document.body.style.overflow = 'hidden'
  }
})

onUnmounted(() => {
  if (typeof document !== 'undefined') {
    document.body.style.overflow = ''
  }
})
</script>

<style scoped>
.search-drawer-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  justify-content: flex-end;
  outline: none;
}

.search-drawer-scrim {
  position: absolute;
  inset: 0;
  background: color-mix(in srgb, var(--night-canvas) 65%, transparent);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.search-drawer-sheet {
  position: relative;
  width: 100%;
  max-width: 480px;
  height: 100%;
  background: var(--color-surface);
  color: var(--color-text);
  border-left: 1px solid var(--border-liquid-glass);
  border-top-left-radius: var(--radius-sheet);
  border-bottom-left-radius: var(--radius-sheet);
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-xl);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.search-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-fib-3) var(--space-fib-3) var(--space-fib-2);
  border-bottom: 1px solid var(--color-border);
}

.search-drawer-eyebrow {
  display: flex;
  align-items: center;
  gap: var(--space-fib-1);
  font-size: var(--font-size-label);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-text-muted);
}

.search-drawer-heading {
  font-family: var(--font-editorial, 'Lora', serif);
  font-size: var(--font-size-title);
  font-weight: var(--weight-title);
  margin: var(--space-fib-1) 0 0;
  color: var(--color-text);
}

.search-drawer-controls {
  display: flex;
  align-items: center;
  gap: var(--space-fib-1);
}

.search-drawer-kbd-hint {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 6px;
  font-size: var(--text-2xs);
  font-family: monospace;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  color: var(--color-text-muted);
}

.search-drawer-close-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 44px;
  min-height: 44px;
  border-radius: var(--radius-control);
  border: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
  color: var(--color-text);
  cursor: pointer;
  transition: background 0.15s ease;
}

.search-drawer-close-btn:hover {
  background: var(--color-surface-raised);
}

.search-drawer-input-wrap {
  position: relative;
  display: flex;
  align-items: center;
  margin: var(--space-fib-3);
}

.search-drawer-input-icon {
  position: absolute;
  left: var(--space-fib-2);
  color: var(--color-text-muted);
  pointer-events: none;
}

.search-drawer-input {
  width: 100%;
  min-height: 48px;
  padding: 0 var(--space-fib-5) 0 var(--space-fib-4);
  font-family: var(--font-body, inherit);
  font-size: var(--font-size-body);
  color: var(--color-text);
  background: var(--color-surface-subtle);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-control);
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.search-drawer-input:focus {
  border-color: var(--alluvial-gold);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--alluvial-gold) 20%, transparent);
}

.search-drawer-clear-btn {
  position: absolute;
  right: 4px;
  min-width: 44px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  cursor: pointer;
}

.search-drawer-filters {
  display: flex;
  flex-direction: column;
  gap: var(--space-fib-3);
  padding: 0 var(--space-fib-3);
}

.search-drawer-filter-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-fib-1);
}

.search-drawer-filter-label {
  display: flex;
  align-items: center;
  gap: var(--space-fib-1);
  font-size: var(--font-size-caption);
  font-weight: var(--weight-title-sm);
  color: var(--color-text-muted);
  margin: 0;
}

.search-drawer-chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-fib-1);
}

.search-drawer-chip {
  display: inline-flex;
  align-items: center;
  gap: var(--space-fib-1);
  min-height: 44px;
  padding: 0 var(--space-fib-2);
  font-size: var(--font-size-caption);
  color: var(--color-text);
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.search-drawer-chip:hover {
  background: var(--color-surface-raised);
}

.search-drawer-chip:active {
  transform: scale(0.98);
}

.search-drawer-chip.active {
  background: var(--color-surface-raised);
  border-color: var(--alluvial-gold);
  font-weight: var(--weight-title-sm);
}

.chip-indicator,
.tide-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-text-muted);
}

.search-drawer-chip.active .chip-indicator,
.search-drawer-chip.active .tide-dot {
  background: var(--alluvial-gold);
}

.chip-region-mang-thit.active {
  border-color: var(--color-material-clay);
}
.chip-region-mang-thit.active .chip-indicator {
  background: var(--color-material-clay);
}

.chip-region-cu-lao-an-binh.active {
  border-color: var(--color-material-leaf);
}
.chip-region-cu-lao-an-binh.active .chip-indicator {
  background: var(--color-material-leaf);
}

.chip-region-co-chien.active {
  border-color: var(--color-material-river);
}
.chip-region-co-chien.active .chip-indicator {
  background: var(--color-material-river);
}

.search-drawer-results {
  flex: 1;
  padding: var(--space-fib-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-fib-2);
}

.search-drawer-results-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--font-size-label);
  color: var(--color-text-muted);
}

.search-drawer-reset-btn {
  background: transparent;
  border: none;
  color: var(--alluvial-gold);
  font-size: var(--font-size-caption);
  cursor: pointer;
  text-decoration: underline;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
}

.search-drawer-plaques {
  display: flex;
  flex-direction: column;
  gap: var(--space-fib-2);
}

.search-drawer-plaque {
  padding: var(--space-fib-2) var(--space-fib-3);
  background: var(--color-surface-subtle);
  border: 1.5px solid var(--alluvial-gold);
  border-radius: var(--radius-surface);
  display: flex;
  flex-direction: column;
  gap: var(--space-fib-1);
}

.plaque-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--font-size-label);
}

.plaque-category-badge {
  text-transform: uppercase;
  font-weight: var(--weight-title-sm);
  color: var(--color-material-clay);
}

.plaque-coords {
  font-family: monospace;
  color: var(--color-text-muted);
}

.plaque-title {
  margin: 0;
  font-family: var(--font-editorial, 'Lora', serif);
  font-size: var(--font-size-title-sm);
}

.plaque-title a {
  color: var(--color-text);
  text-decoration: none;
}

.plaque-title a:hover {
  text-decoration: underline;
}

.plaque-snippet {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--color-text-muted);
  line-height: 1.5;
}

.plaque-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--space-fib-1);
  font-size: var(--font-size-label);
}

.plaque-tag {
  padding: 2px 8px;
  background: var(--color-surface-raised);
  border-radius: var(--radius-control);
  color: var(--color-text);
}

.search-drawer-footer {
  padding: var(--space-fib-3);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.search-drawer-submit-btn {
  width: 100%;
  min-height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-fib-1);
  background: var(--color-action);
  color: var(--sand-50);
  border: none;
  border-radius: var(--radius-control);
  font-weight: var(--weight-title-sm);
  font-size: var(--font-size-body);
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.search-drawer-submit-btn:hover {
  opacity: 0.92;
}

.search-drawer-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--space-fib-4) var(--space-fib-3);
  margin: var(--space-fib-2) 0;
  background: var(--color-surface-subtle);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-surface);
  gap: var(--space-fib-2);
}

.empty-state-icon-halo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: var(--radius-full);
  background: color-mix(in srgb, var(--color-material-clay) 12%, transparent);
  color: var(--color-material-clay);
}

.empty-state-title {
  margin: 0;
  font-family: var(--font-editorial, 'Lora', serif);
  font-size: var(--font-size-body);
  font-weight: var(--weight-title-sm);
  color: var(--color-text);
}

.empty-state-desc {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--color-text-muted);
  line-height: var(--line-height-relaxed);
  max-width: 300px;
}

.empty-state-desc em {
  font-style: normal;
  font-weight: var(--weight-bold);
  color: var(--color-text);
}

.empty-state-reset-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-fib-1);
  min-height: 44px;
  padding: 0 var(--space-fib-3);
  background: var(--color-action);
  color: var(--sand-50);
  border: none;
  border-radius: var(--radius-control);
  font-size: var(--font-size-label);
  font-weight: var(--weight-title-sm);
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.empty-state-reset-btn:hover {
  opacity: 0.92;
}

.empty-state-reset-btn:focus-visible {
  outline: 2px solid var(--alluvial-gold);
  outline-offset: 2px;
}

/* Animations */
.drawer-fade-enter-active,
.drawer-fade-leave-active {
  transition: opacity 0.3s ease;
}

.drawer-fade-enter-from,
.drawer-fade-leave-to {
  opacity: 0;
}

.drawer-fade-enter-active .search-drawer-sheet,
.drawer-fade-leave-active .search-drawer-sheet {
  transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}

.drawer-fade-enter-from .search-drawer-sheet,
.drawer-fade-leave-to .search-drawer-sheet {
  transform: translateX(100%);
}
</style>
