import { ref, computed, onBeforeUnmount, type Ref } from 'vue'
import { escapeHtml } from '~/utils/safe'
import { entityPath } from '~/utils/routePaths'

export interface UseSearchTypeaheadOptions {
  searchInput: Ref<string>
  fetchSuggestions: (term: string, limit?: number, options?: { signal?: AbortSignal }) => Promise<any[]>
  onSelectSuggestion?: (suggestion: any) => void
  onSelectAll?: () => void
}

export function useSearchTypeahead(options: UseSearchTypeaheadOptions) {
  const { searchInput, fetchSuggestions, onSelectSuggestion, onSelectAll } = options

  const suggestions = ref<any[]>([])
  const sugIdx = ref(-1)
  const showSuggestions = ref(false)
  const sugLoading = ref(false)
  let sugTimer: ReturnType<typeof setTimeout> | null = null
  let blurTimer: ReturnType<typeof setTimeout> | null = null
  let sugAbort: AbortController | null = null

  const activeSuggestionId = computed(() => {
    if (sugIdx.value < 0 || !showSuggestions.value) return undefined
    if (sugIdx.value < suggestions.value.length) return `sug-${suggestions.value[sugIdx.value].id}`
    if (sugIdx.value === suggestions.value.length) return 'sug-search-all'
    return undefined
  })

  function highlightMatch(name: string): string {
    const q = searchInput.value.trim()
    const safe = escapeHtml(name)
    if (!q) return safe
    const idx = name.toLowerCase().indexOf(q.toLowerCase())
    if (idx === -1) return safe
    const before = escapeHtml(name.slice(0, idx))
    const match = escapeHtml(name.slice(idx, idx + q.length))
    const after = escapeHtml(name.slice(idx + q.length))
    return `${before}<mark class="sug-mark">${match}</mark>${after}`
  }

  function sugClose() {
    showSuggestions.value = false
    sugIdx.value = -1
  }

  function onTypeahead() {
    const term = searchInput.value.trim()
    if (sugTimer) clearTimeout(sugTimer)
    if (term.length < 2) {
      sugClose()
      sugLoading.value = false
      return
    }
    sugLoading.value = true
    sugTimer = setTimeout(async () => {
      sugAbort?.abort()
      const ctrl = new AbortController()
      sugAbort = ctrl
      try {
        const res = await fetchSuggestions(term, 5, { signal: ctrl.signal })
        if (ctrl.signal.aborted) return
        suggestions.value = res || []
        sugIdx.value = -1
        showSuggestions.value = suggestions.value.length > 0
      } catch {
        if (!ctrl.signal.aborted) {
          suggestions.value = []
          showSuggestions.value = false
        }
      }
      sugLoading.value = false
    }, 300)
  }

  function sugNext() {
    if (!showSuggestions.value) return
    sugIdx.value = Math.min(sugIdx.value + 1, suggestions.value.length)
  }

  function sugPrev() {
    if (!showSuggestions.value) return
    sugIdx.value = Math.max(sugIdx.value - 1, -1)
  }

  function sugBlur() {
    blurTimer = setTimeout(sugClose, 150)
  }

  function onInputBlur() {
    sugBlur()
  }

  function goToSuggestion(s: any) {
    sugClose()
    if (onSelectSuggestion) {
      onSelectSuggestion(s)
    } else {
      navigateTo(entityPath(s.id))
    }
  }

  function onEnter() {
    if (showSuggestions.value && sugIdx.value >= 0 && sugIdx.value < suggestions.value.length) {
      goToSuggestion(suggestions.value[sugIdx.value])
    } else if (onSelectAll) {
      onSelectAll()
    }
  }

  onBeforeUnmount(() => {
    if (sugTimer) clearTimeout(sugTimer)
    if (blurTimer) clearTimeout(blurTimer)
    sugAbort?.abort()
  })

  return {
    suggestions,
    sugIdx,
    showSuggestions,
    sugLoading,
    activeSuggestionId,
    highlightMatch,
    onTypeahead,
    sugNext,
    sugPrev,
    sugClose,
    onInputBlur,
    goToSuggestion,
    onEnter,
  }
}
