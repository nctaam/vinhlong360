export function useReveal(options: { threshold?: number; rootMargin?: string } = {}) {
  if (!import.meta.client) return

  const threshold = options.threshold ?? 0.1
  const rootMargin = options.rootMargin ?? '0px 0px -30px 0px'

  let observer: IntersectionObserver | null = null

  onMounted(() => {
    nextTick(() => {
      const els = document.querySelectorAll('.reveal:not(.revealed)')
      if (!els.length) return

      observer = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            ;(entry.target as HTMLElement).classList.add('revealed')
            observer!.unobserve(entry.target)
          }
        }
      }, { threshold, rootMargin })

      els.forEach(el => observer!.observe(el))
    })
  })

  onUnmounted(() => {
    if (observer) {
      observer.disconnect()
      observer = null
    }
  })
}
