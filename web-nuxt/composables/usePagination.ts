export function usePagination(opts: { pageSize?: number } = {}) {
  const pageSize = opts.pageSize ?? 20
  const page = ref(1)
  const total = ref(0)
  const loading = ref(false)
  const loadingMore = ref(false)
  const error = ref(false)

  const hasMore = computed(() => page.value * pageSize < total.value)

  function reset() {
    page.value = 1
    total.value = 0
    error.value = false
  }

  function nextPage() {
    if (hasMore.value && !loadingMore.value) {
      page.value++
    }
  }

  return { page, total, loading, loadingMore, error, hasMore, pageSize, reset, nextPage }
}
