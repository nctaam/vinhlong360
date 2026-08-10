export function useFilterUrl(filters: Record<string, Ref<string>>, defaults: Record<string, string> = {}) {
  const route = useRoute()
  const router = useRouter()
  let restoringFromRoute = false

  function restoreFromRoute() {
    restoringFromRoute = true
    for (const [key, filterRef] of Object.entries(filters)) {
      const rawValue = route.query[key]
      const queryValue = Array.isArray(rawValue) ? rawValue[0] : rawValue
      filterRef.value = typeof queryValue === 'string' && queryValue ? queryValue : defaults[key] ?? 'all'
    }
    nextTick(() => { restoringFromRoute = false })
  }
  restoreFromRoute()

  function syncToUrl() {
    if (restoringFromRoute) return
    const query: Record<string, string | undefined> = { ...route.query as Record<string, string> }
    for (const [key, filterRef] of Object.entries(filters)) {
      const defaultVal = defaults[key] ?? 'all'
      if (filterRef.value && filterRef.value !== defaultVal) {
        query[key] = filterRef.value
      } else {
        delete query[key]
      }
    }
    return router.replace({ query })
  }

  watch(() => route.query, restoreFromRoute, { deep: true })
  for (const filterRef of Object.values(filters)) {
    watch(filterRef, syncToUrl)
  }

  return { syncToUrl }
}
