export function useFilterUrl(filters: Record<string, Ref<string>>, defaults: Record<string, string> = {}) {
  const route = useRoute()
  const router = useRouter()

  for (const [key, ref] of Object.entries(filters)) {
    const queryVal = route.query[key]
    if (typeof queryVal === 'string' && queryVal) {
      ref.value = queryVal
    }
  }

  function syncToUrl() {
    const query: Record<string, string> = {}
    for (const [key, ref] of Object.entries(filters)) {
      const defaultVal = defaults[key] || 'all'
      if (ref.value && ref.value !== defaultVal) {
        query[key] = ref.value
      }
    }
    router.replace({ query })
  }

  for (const ref of Object.values(filters)) {
    watch(ref, syncToUrl)
  }
}
