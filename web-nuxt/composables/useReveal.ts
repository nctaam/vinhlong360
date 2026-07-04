export function useReveal(options: { threshold?: number; rootMargin?: string } = {}) {
  if (!import.meta.client) return

  const threshold = options.threshold ?? 0.1
  const rootMargin = options.rootMargin ?? '0px 0px -30px 0px'
  let observer: IntersectionObserver | null = null
  let failSafe: ReturnType<typeof setTimeout> | null = null

  const revealAll = () =>
    document.querySelectorAll('.reveal:not(.revealed)').forEach(el => el.classList.add('revealed'))

  onMounted(() => {
    nextTick(() => {
      if (!('IntersectionObserver' in window)) { revealAll(); return }

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

      // Fail open: if the observer has revealed NOTHING shortly after load — e.g. a
      // hydration mismatch swapped the observed nodes for fresh ones the observer never
      // saw — force-reveal everything so page content is never stuck invisible.
      failSafe = setTimeout(() => {
        if (!document.querySelector('.reveal.revealed')) revealAll()
      }, 1200)
    })
  })

  onUnmounted(() => {
    observer?.disconnect()
    observer = null
    if (failSafe) clearTimeout(failSafe)
  })
}
