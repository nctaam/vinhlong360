<template>
  <div class="search-ac" :class="{ active: showDropdown }">
    <form role="search" @submit.prevent="onSubmit">
      <input
        ref="inputEl"
        v-model="query"
        type="search"
        placeholder="Tìm đặc sản, trải nghiệm…"
        aria-label="Tìm kiếm"
        role="combobox"
        aria-autocomplete="list"
        aria-controls="ac-listbox"
        :aria-expanded="showDropdown"
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
      <!-- Recent searches (when no query) -->
      <div v-if="!query.trim() && recentSearches.length" class="ac-section">
        <div class="ac-section-header">
          <span class="ac-section-title">Gần đây</span>
          <button type="button" class="ac-section-clear" @click="clearRecents">Xóa</button>
        </div>
        <button type="button"
          v-for="(term, i) in recentSearches"
          :key="'r-' + i"
          class="ac-item ac-recent"
          :class="{ highlighted: i === highlightIndex }"
          role="option"
          :aria-selected="i === highlightIndex"
          @mousedown.prevent="useRecent(term)"
        >
          <span class="ac-emoji">🕐</span>
          <span class="ac-info"><span class="ac-name">{{ term }}</span></span>
          <button type="button" class="ac-remove-recent" @mousedown.stop.prevent="removeRecent(i)" aria-label="Xóa">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </button>
      </div>

      <!-- Suggestions -->
      <NuxtLink
        v-for="(item, i) in suggestions"
        :key="item.id"
        :to="`/dia-diem/${item.id}`"
        class="ac-item"
        :class="{ highlighted: recentOffset + i === highlightIndex }"
        role="option"
        :aria-selected="recentOffset + i === highlightIndex"
        @mousedown.prevent="goTo(item)"
      >
        <span class="ac-emoji">{{ typeEmoji(item.type) }}</span>
        <span class="ac-info">
          <span class="ac-name" v-html="highlightMatch(item.name)"></span>
          <span v-if="item.place_name" class="ac-place">{{ item.place_name }}</span>
        </span>
      </NuxtLink>

      <!-- See all -->
      <NuxtLink
        v-if="query.trim()"
        :to="`/tim-kiem?q=${encodeURIComponent(query.trim())}`"
        class="ac-item ac-all"
        :class="{ highlighted: highlightIndex === totalItems - 1 }"
        role="option"
        @mousedown.prevent="onSubmit"
      >
        🔍 Xem tất cả kết quả cho "{{ query.trim() }}"
      </NuxtLink>

      <!-- Empty state -->
      <div v-if="query.trim() && !suggestions.length && !loading" class="ac-empty">
        Không tìm thấy kết quả
      </div>

      <!-- Loading -->
      <div v-if="loading" class="ac-loading">
        <div class="spinner spinner-sm"></div>
      </div>
    </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { TYPE_META } from '~/composables/useConstants'

const RECENT_KEY = 'vl360_recent_searches'
const MAX_RECENTS = 5

const router = useRouter()
const query = ref('')
const suggestions = ref<any[]>([])
const highlightIndex = ref(-1)
const showDropdown = ref(false)
const loading = ref(false)
const inputEl = ref<HTMLInputElement | null>(null)
const recentSearches = ref<string[]>([])
let debounceTimer: ReturnType<typeof setTimeout> | null = null

const recentOffset = computed(() => !query.value.trim() ? recentSearches.value.length : 0)
const totalItems = computed(() => {
  if (!query.value.trim()) return recentSearches.value.length
  return suggestions.value.length + (query.value.trim() ? 1 : 0)
})

function loadRecents() {
  try {
    const raw = localStorage.getItem(RECENT_KEY)
    recentSearches.value = raw ? JSON.parse(raw) : []
  } catch { recentSearches.value = [] }
}

function saveRecent(term: string) {
  const clean = term.trim()
  if (!clean || clean.length < 2) return
  recentSearches.value = [clean, ...recentSearches.value.filter(r => r !== clean)].slice(0, MAX_RECENTS)
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(recentSearches.value)) } catch {}
}

function removeRecent(idx: number) {
  recentSearches.value.splice(idx, 1)
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(recentSearches.value)) } catch {}
}

function clearRecents() {
  recentSearches.value = []
  try { localStorage.removeItem(RECENT_KEY) } catch {}
}

function useRecent(term: string) {
  query.value = term
  onInput()
}

function typeEmoji(type: string) {
  return TYPE_META[type]?.emoji || '📍'
}

function highlightMatch(name: string): string {
  const q = query.value.trim()
  if (!q) return name
  const idx = name.toLowerCase().indexOf(q.toLowerCase())
  if (idx === -1) return name
  const before = name.slice(0, idx)
  const match = name.slice(idx, idx + q.length)
  const after = name.slice(idx + q.length)
  return `${before}<mark>${match}</mark>${after}`
}

async function fetchSuggestions(q: string) {
  if (!q || q.length < 2) {
    suggestions.value = []
    return
  }
  loading.value = true
  try {
    const data = await $fetch<any>(`/api/entities?q=${encodeURIComponent(q)}&limit=5`)
    suggestions.value = data?.entities || []
  } catch {
    suggestions.value = []
  }
  loading.value = false
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
  if (suggestions.value.length > 0 || query.value.trim().length >= 2 || recentSearches.value.length > 0) {
    showDropdown.value = true
  }
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

function moveDown() {
  const max = totalItems.value - 1
  highlightIndex.value = highlightIndex.value < max ? highlightIndex.value + 1 : 0
  showDropdown.value = true
}

function moveUp() {
  const max = totalItems.value - 1
  highlightIndex.value = highlightIndex.value > 0 ? highlightIndex.value - 1 : max
}

function goTo(item: any) {
  saveRecent(item.name)
  close()
  query.value = ''
  navigateTo(`/dia-diem/${item.id}`)
}

function onSubmit() {
  const q = query.value.trim()
  if (!q) return

  if (!query.value.trim() && highlightIndex.value >= 0 && highlightIndex.value < recentSearches.value.length) {
    useRecent(recentSearches.value[highlightIndex.value])
    return
  }

  if (highlightIndex.value >= recentOffset.value && highlightIndex.value < recentOffset.value + suggestions.value.length) {
    goTo(suggestions.value[highlightIndex.value - recentOffset.value])
    return
  }

  saveRecent(q)
  close()
  navigateTo(`/tim-kiem?q=${encodeURIComponent(q)}`)
}

if (import.meta.client) {
  const onClick = (e: Event) => {
    const el = inputEl.value
    if (el && !el.closest('.search-ac')?.contains(e.target as Node)) {
      close()
    }
  }
  onMounted(() => { document.addEventListener('click', onClick); loadRecents() })
  onUnmounted(() => document.removeEventListener('click', onClick))
}
</script>
