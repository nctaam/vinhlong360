<template>
  <div class="search-ac" :class="{ active: showDropdown }">
    <form role="search" @submit.prevent="onSubmit">
      <input
        ref="inputEl"
        v-model="query"
        type="search"
        enterkeyhint="search"
        :placeholder="placeholder"
        aria-label="Tìm kiếm"
        role="combobox"
        aria-autocomplete="list"
        aria-controls="ac-listbox"
        :aria-expanded="showDropdown"
        :aria-activedescendant="highlightIndex >= 0 ? 'ac-opt-' + highlightIndex : undefined"
        autocomplete="off"
        @input="onInput"
        @focus="onFocus"
        @keydown.down.prevent="moveDown"
        @keydown.up.prevent="moveUp"
        @keydown.escape="close"
      />
      <button type="button" v-if="query" class="ac-clear" aria-label="Xóa tìm kiếm" @click="clearQuery">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </form>
    <span class="sr-only" aria-live="polite" aria-atomic="true">{{ suggestions.length ? `${suggestions.length} kết quả` : '' }}</span>
    <Transition name="menu-pop">
    <div v-if="showDropdown" id="ac-listbox" class="ac-dropdown" role="listbox">
      <!-- Initial-state hint: categories when no query (and no recents) -->
      <div v-if="!query.trim() && !recentSearches.length" class="ac-hint-section">
        <div class="ac-hint-head">
          <span class="ac-hint-tick" aria-hidden="true"></span>
          <span class="ac-hint-title">Tìm theo danh mục</span>
        </div>
        <div class="ac-chips">
          <NuxtLink v-for="c in quickCategories" :key="c.to" :to="c.to" class="ac-chip" @mousedown.prevent="goCategory(c.to)" @keydown.enter.prevent="goCategory(c.to)" @keydown.space.prevent="goCategory(c.to)">
            <span aria-hidden="true">{{ c.emoji }}</span> {{ c.label }}
          </NuxtLink>
        </div>
      </div>

      <!-- Recent searches (when no query) -->
      <div v-if="!query.trim() && recentSearches.length" class="ac-section">
        <div class="ac-section-header">
          <span class="ac-section-title">Gần đây</span>
          <button type="button" class="ac-section-clear" @click="clearRecents">Xóa</button>
        </div>
        <div
          v-for="(term, i) in recentSearches"
          :key="'r-' + i"
          class="ac-recent-row"
        >
          <span class="ac-emoji">🕐</span>
          <div
            class="ac-item ac-recent"
            :id="'ac-opt-' + i"
            :class="{ highlighted: i === highlightIndex }"
            role="option"
            :aria-selected="i === highlightIndex"
            @mousedown.prevent="useRecent(term)"
          >
            <span class="ac-info"><span class="ac-name">{{ term }}</span></span>
          </div>
          <button type="button" class="ac-remove-recent" @mousedown.stop.prevent="removeRecent(i)" aria-label="Xóa khỏi lịch sử">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      </div>

      <!-- Suggestions -->
      <NuxtLink
        v-for="(item, i) in suggestions"
        :key="item.id"
        :to="entityPath(item.id)"
        class="ac-item"
        :id="'ac-opt-' + (recentOffset + i)"
        :class="{ highlighted: recentOffset + i === highlightIndex }"
        role="option"
        :aria-selected="recentOffset + i === highlightIndex"
        @mousedown.prevent="goTo(item)"
      >
        <span class="ac-emoji">{{ typeEmoji(item.type) }}</span>
        <span class="ac-info">
          <span class="ac-name" v-html="highlightMatch(item.name)"></span>
          <span class="ac-meta">
            <span v-if="typeLabel(item.type)" class="ac-type">{{ typeLabel(item.type) }}</span>
            <span v-if="item.place_name" class="ac-place">{{ item.place_name }}</span>
          </span>
        </span>
      </NuxtLink>

      <!-- See all -->
      <NuxtLink
        v-if="query.trim()"
        :to="`/tim-kiem?q=${encodeURIComponent(query.trim())}`"
        class="ac-item ac-all"
        :id="'ac-opt-' + (totalItems - 1)"
        :class="{ highlighted: highlightIndex === totalItems - 1 }"
        role="option"
        @mousedown.prevent="onSubmit"
      >
        🔍 Xem tất cả kết quả cho "{{ query.trim() }}"
      </NuxtLink>

      <!-- Fetch error -->
      <div v-if="fetchFailed && !loading && query.trim()" class="ac-empty" role="status">
        <span class="ac-empty-icon" aria-hidden="true">⚠️</span>
        <p class="ac-empty-title">Lỗi kết nối</p>
        <p class="ac-empty-hint">Không thể tải gợi ý. Thử nhập lại hoặc tìm theo danh mục.</p>
      </div>

      <!-- Empty state -->
      <div v-if="query.trim() && !suggestions.length && !loading && !fetchFailed" class="ac-empty">
        <span class="ac-empty-icon" aria-hidden="true">🔍</span>
        <p class="ac-empty-title">Chưa tìm thấy nơi nào khớp</p>
        <p class="ac-empty-hint">Thử từ khóa khác, hoặc xem gợi ý theo danh mục:</p>
        <div class="ac-chips ac-empty-chips">
          <NuxtLink v-for="c in quickCategories" :key="c.to" :to="c.to" class="ac-chip" @mousedown.prevent="goCategory(c.to)" @keydown.enter.prevent="goCategory(c.to)" @keydown.space.prevent="goCategory(c.to)">
            <span aria-hidden="true">{{ c.emoji }}</span> {{ c.label }}
          </NuxtLink>
        </div>
        <NuxtLink :to="`/tim-kiem?q=${encodeURIComponent(query.trim())}`" class="ac-empty-all" @mousedown.prevent="onSubmit">
          Xem tất cả kết quả →
        </NuxtLink>
      </div>

      <!-- Loading (delayed 150ms to avoid flicker on fast networks) -->
      <div v-if="showLoading" class="ac-loading" role="status" aria-label="Đang tìm kiếm">
        <div class="spinner spinner-sm"></div>
      </div>
    </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import type { Entity } from '~/types'
import { TYPE_META } from '~/composables/useConstants'

withDefaults(defineProps<{ placeholder?: string }>(), {
  placeholder: 'Tìm đặc sản, trải nghiệm…',
})

const router = useRouter()
const query = ref('')
const suggestions = ref<Entity[]>([])
const highlightIndex = ref(-1)
const showDropdown = ref(false)
const loading = ref(false)
const fetchFailed = ref(false)
const showLoading = ref(false)
let loadingTimer: ReturnType<typeof setTimeout> | null = null
const inputEl = ref<HTMLInputElement | null>(null)
let debounceTimer: ReturnType<typeof setTimeout> | null = null
let fetchAbort: AbortController | null = null
const { fetchEntitySuggestions } = useUnifiedSearch()

const { recentSearches, loadRecents, saveRecent, removeRecent, clearRecents } = useSearchRecents()

const quickCategories = [
  { to: '/du-lich', emoji: '🌿', label: 'Du lịch' },
  { to: '/san-pham', emoji: '🍊', label: 'Đặc sản' },
  { to: '/luu-tru', emoji: '🏡', label: 'Lưu trú' },
  { to: '/ocop', emoji: '⭐', label: 'OCOP' },
]

function goCategory(to: string) {
  close()
  query.value = ''
  navigateTo(to)
}

const recentOffset = computed(() => !query.value.trim() ? recentSearches.value.length : 0)
const totalItems = computed(() => {
  if (!query.value.trim()) return recentSearches.value.length
  return suggestions.value.length + (query.value.trim() ? 1 : 0)
})

function useRecent(term: string) {
  query.value = term
  onInput()
}

function typeEmoji(type: string) {
  return TYPE_META[type]?.emoji || '📍'
}

function typeLabel(type: string) {
  return TYPE_META[type]?.label || ''
}

function highlightMatch(name: string): string {
  const q = query.value.trim()
  const safe = escapeHtml(name)
  if (!q) return safe
  const idx = name.toLowerCase().indexOf(q.toLowerCase())
  if (idx === -1) return safe
  const before = escapeHtml(name.slice(0, idx))
  const match = escapeHtml(name.slice(idx, idx + q.length))
  const after = escapeHtml(name.slice(idx + q.length))
  return `${before}<mark>${match}</mark>${after}`
}

async function fetchSuggestions(q: string) {
  if (!q || q.length < 2) {
    suggestions.value = []
    return
  }
  fetchAbort?.abort()
  const ctrl = new AbortController()
  fetchAbort = ctrl
  loading.value = true
  if (loadingTimer) clearTimeout(loadingTimer)
  loadingTimer = setTimeout(() => { if (loading.value) showLoading.value = true }, 150)
  try {
    const data = await fetchEntitySuggestions(q, 5, { signal: ctrl.signal })
    if (!ctrl.signal.aborted) { suggestions.value = data || []; fetchFailed.value = false }
  } catch {
    if (!ctrl.signal.aborted) { suggestions.value = []; fetchFailed.value = true }
  }
  loading.value = false
  if (loadingTimer) { clearTimeout(loadingTimer); loadingTimer = null }
  showLoading.value = false
}

function onInput() {
  highlightIndex.value = -1
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    fetchSuggestions(query.value.trim())
    showDropdown.value = true
  }, 250)
}

function onFocus() {
  loadRecents()
  // Always open on focus: shows suggestions/recents when present, or the
  // category-discovery hint when the input is empty (frictionless start).
  showDropdown.value = true
}

function close() {
  showDropdown.value = false
  highlightIndex.value = -1
}

function clearQuery() {
  query.value = ''
  suggestions.value = []
  highlightIndex.value = -1
  inputEl.value?.focus()
}

function scrollHighlightedIntoView() {
  nextTick(() => {
    const el = document.getElementById(`ac-opt-${highlightIndex.value}`)
    el?.scrollIntoView({ block: 'nearest' })
  })
}

function moveDown() {
  if (totalItems.value <= 0) {
    highlightIndex.value = -1
    showDropdown.value = true
    return
  }
  const max = totalItems.value - 1
  highlightIndex.value = highlightIndex.value < max ? highlightIndex.value + 1 : 0
  showDropdown.value = true
  scrollHighlightedIntoView()
}

function moveUp() {
  if (totalItems.value <= 0) {
    highlightIndex.value = -1
    return
  }
  const max = totalItems.value - 1
  highlightIndex.value = highlightIndex.value > 0 ? highlightIndex.value - 1 : max
  scrollHighlightedIntoView()
}

function goTo(item: Entity) {
  saveRecent(item.name)
  close()
  query.value = ''
  navigateTo(entityPath(item.id))
}

function onSubmit() {
  const q = query.value.trim()
  if (!q) {
    if (highlightIndex.value >= 0 && highlightIndex.value < recentSearches.value.length) {
      const recent = recentSearches.value[highlightIndex.value]
      if (recent) useRecent(recent)
    }
    return
  }

  if (highlightIndex.value >= recentOffset.value && highlightIndex.value < recentOffset.value + suggestions.value.length) {
    const item = suggestions.value[highlightIndex.value - recentOffset.value]
    if (item) goTo(item)
    return
  }

  saveRecent(q)
  close()
  navigateTo(`/tim-kiem?q=${encodeURIComponent(q)}`)
}

function focusInput() { inputEl.value?.focus() }
defineExpose({ focusInput })

if (import.meta.client) {
  const onClick = (e: Event) => {
    const el = inputEl.value
    if (el && !el.closest('.search-ac')?.contains(e.target as Node)) {
      close()
    }
  }
  const onGlobalKey = (e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault()
      focusInput()
    }
  }
  onMounted(() => { document.addEventListener('click', onClick); document.addEventListener('keydown', onGlobalKey); loadRecents() })
  onUnmounted(() => {
    document.removeEventListener('click', onClick)
    document.removeEventListener('keydown', onGlobalKey)
    if (debounceTimer) clearTimeout(debounceTimer)
    if (loadingTimer) clearTimeout(loadingTimer)
    fetchAbort?.abort()
  })
}
</script>

<style scoped>
/* ── Keyboard navigation indicator (iOS-style focus accent) ────────────────
   Stronger visual distinction for the highlighted item than bg-alt alone, and
   guaranteed 44px touch targets on mobile. Tri-province hairline (river→amber→
   clay) instead of a flat solid line — same accent language as sediment-tick
   section-heads elsewhere, at zero added motion/latency. */
.ac-dropdown :deep(.ac-item) { min-height: 44px; }
.ac-dropdown :deep(.ac-item.highlighted) {
  border-left: 3px solid;
  border-image: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%) 1;
  padding-left: calc(var(--space-4) - 3px);
}
.dark .ac-dropdown :deep(.ac-item.highlighted) {
  border-image: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%) 1;
}
.ac-recent-row {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}
.ac-recent-row > .ac-emoji {
  flex: 0 0 auto;
  padding-left: var(--space-4);
}
.ac-recent-row > .ac-item {
  flex: 1 1 auto;
  min-width: 0;
}
.ac-remove-recent {
  flex: 0 0 auto;
  min-width: 44px;
  min-height: 44px;
}

/* dark overrides for .ac-type / .ac-place moved to dark-overrides.css —
   :global(.dark) in scoped CSS compiles to bare .dark{} */

/* ── Loading entry motion ──────────────────────────────────────────────────*/
.ac-loading { animation: acLoadingFade .25s var(--ease-out) both; }
@keyframes acLoadingFade { from { opacity: 0; } to { opacity: 1; } }

/* ── Initial-state category hint ───────────────────────────────────────────*/
.ac-hint-section { padding: var(--space-3) var(--space-4) var(--space-4); }
.ac-hint-head { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-3); }
/* Tri-province tick (river→amber→clay) — same sediment-head idiom as section
   headings elsewhere, scaled to a small-caps label instead of an <h2>. */
.ac-hint-tick {
  flex-shrink: 0;
  width: 3px;
  height: .85em;
  border-radius: var(--radius-full);
  background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .ac-hint-tick {
  background: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%);
}
.ac-hint-title {
  font-size: var(--text-xs); font-weight: var(--weight-semibold);
  color: var(--muted); text-transform: uppercase; letter-spacing: .04em;
}
.ac-chips { display: flex; flex-wrap: wrap; gap: var(--space-2); }
.ac-chip {
  display: inline-flex; align-items: center; gap: var(--space-1);
  min-height: 44px; padding: var(--space-2) var(--space-3);
  background: var(--bg-alt); border: .5px solid var(--line);
  border-radius: var(--radius-full); color: var(--ink);
  font-size: var(--text-sm); font-weight: var(--weight-medium);
  text-decoration: none; cursor: pointer;
  transition: background .25s var(--ease-out), border-color .25s var(--ease-out), transform .25s var(--ease-spring-gentle);
}
.ac-chip:hover { background: var(--card); border-color: var(--primary-fg); transform: translateY(-1px); }
.ac-chip:active { transform: scale(.97); transition-duration: .08s; }
.ac-chip:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

/* ── Expanded empty state ──────────────────────────────────────────────────*/
.ac-empty { display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.ac-empty-icon { font-size: 1.6rem; line-height: 1; }
.ac-empty-title { font-weight: var(--weight-semibold); color: var(--ink); margin: 0; }
.ac-empty-hint { font-size: var(--text-xs); color: var(--muted); margin: 0; }
.ac-empty-chips { justify-content: center; margin-top: var(--space-1); }
.ac-empty-all {
  margin-top: var(--space-2); font-size: var(--text-sm);
  font-weight: var(--weight-semibold); color: var(--primary-fg);
  text-decoration: none; min-height: 44px; display: inline-flex; align-items: center;
}
.ac-empty-all:hover { text-decoration: underline; }
.ac-empty-all:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; border-radius: var(--radius-sm); }

/* dark overrides for .ac-chip / .ac-empty-title in dark-overrides.css */

/* ── Reduced motion ────────────────────────────────────────────────────────*/
@media (pointer: coarse) { .ac-chip { min-height: 44px; } }
@media (prefers-reduced-motion: reduce) {
  .ac-loading { animation: none; }
  .ac-chip:hover { transform: none; }
  .ac-chip:active { transform: none; }
}
@media (forced-colors: active) {
  .ac-dropdown { border: 1px solid CanvasText; background: Canvas; }
  .ac-item.highlighted { border-left-color: Highlight; }
  .ac-chip { border: 1px solid ButtonText; }
  .ac-remove-recent { border: 1px solid GrayText; }
}
</style>
