export function useInfiniteScroll(
  callback: () => void | Promise<void>,
  options?: { rootMargin?: string; enabled?: Ref<boolean> },
) {
  const sentinel = ref<HTMLElement | null>(null)
  const loading = ref(false)

  if (import.meta.client) {
    let observer: IntersectionObserver | null = null

    onMounted(() => {
      if (!sentinel.value) return
      observer = new IntersectionObserver(
        async ([entry]) => {
          if (!entry.isIntersecting || loading.value) return
          if (options?.enabled && !options.enabled.value) return
          loading.value = true
          try { await callback() } finally { loading.value = false }
        },
        { rootMargin: options?.rootMargin ?? '0px 0px 300px 0px' },
      )
      observer.observe(sentinel.value)
    })

    onUnmounted(() => observer?.disconnect())
  }

  return { sentinel, loading }
}
