<template>
  <div class="search-ac" :class="{ active: showDropdown }">
    <form role="search" @submit.prevent="onSubmit">
      <input
        ref="inputEl"
        v-model="query"
        type="search"
        placeholder="Tìm đặc sản, trải nghiệm…"
        aria-label="Tìm kiếm"
        autocomplete="off"
        @input="onInput"
        @focus="onFocus"
        @keydown.down.prevent="moveDown"
        @keydown.up.prevent="moveUp"
        @keydown.escape="close"
      />
    </form>
    <div v-if="showDropdown" class="ac-dropdown" role="listbox">
      <NuxtLink
        v-for="(item, i) in suggestions"
        :key="item.id"
        :to="`/dia-diem/${item.id}`"
        class="ac-item"
        :class="{ highlighted: i === highlightIndex }"
        role="option"
        :aria-selected="i === highlightIndex"
        @mousedown.prevent="goTo(item)"
      >
        <span class="ac-emoji">{{ typeEmoji(item.type) }}</span>
        <span class="ac-info">
          <span class="ac-name">{{ item.name }}</span>
          <span v-if="item.place_name" class="ac-place">{{ item.place_name }}</span>
        </span>
      </NuxtLink>
      <NuxtLink
        v-if="query.trim()"
        :to="`/tim-kiem?q=${encodeURIComponent(query.trim())}`"
        class="ac-item ac-all"
        :class="{ highlighted: highlightIndex === suggestions.length }"
        role="option"
        @mousedown.prevent="onSubmit"
      >
        🔍 Xem tất cả kết quả cho "{{ query.trim() }}"
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { TYPE_META } from '~/composables/useConstants'

const router = useRouter()
const query = ref('')
const suggestions = ref<any[]>([])
const highlightIndex = ref(-1)
const showDropdown = ref(false)
const inputEl = ref<HTMLInputElement | null>(null)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

function typeEmoji(type: string) {
  return TYPE_META[type]?.emoji || '📍'
}

async function fetchSuggestions(q: string) {
  if (!q || q.length < 2) {
    suggestions.value = []
    return
  }
  try {
    const data = await $fetch<any>(`/api/entities?q=${encodeURIComponent(q)}&limit=5`)
    suggestions.value = data?.entities || []
  } catch {
    suggestions.value = []
  }
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
  if (suggestions.value.length > 0 || query.value.trim().length >= 2) {
    showDropdown.value = true
  }
}

function close() {
  showDropdown.value = false
  highlightIndex.value = -1
}

function moveDown() {
  const max = suggestions.value.length
  highlightIndex.value = highlightIndex.value < max ? highlightIndex.value + 1 : 0
  showDropdown.value = true
}

function moveUp() {
  const max = suggestions.value.length
  highlightIndex.value = highlightIndex.value > 0 ? highlightIndex.value - 1 : max
}

function goTo(item: any) {
  close()
  query.value = ''
  navigateTo(`/dia-diem/${item.id}`)
}

function onSubmit() {
  if (highlightIndex.value >= 0 && highlightIndex.value < suggestions.value.length) {
    goTo(suggestions.value[highlightIndex.value])
    return
  }
  if (query.value.trim()) {
    close()
    navigateTo(`/tim-kiem?q=${encodeURIComponent(query.value.trim())}`)
  }
}

if (import.meta.client) {
  const onClick = (e: Event) => {
    const el = inputEl.value
    if (el && !el.closest('.search-ac')?.contains(e.target as Node)) {
      close()
    }
  }
  onMounted(() => document.addEventListener('click', onClick))
  onUnmounted(() => document.removeEventListener('click', onClick))
}
</script>
