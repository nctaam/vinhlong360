export function useReveal(options: { threshold?: number; rootMargin?: string } = {}) {
  if (!import.meta.client) return

  const threshold = options.threshold ?? 0.1
  const rootMargin = options.rootMargin ?? '0px 0px -30px 0px'
  let observer: IntersectionObserver | null = null
  const timers: ReturnType<typeof setTimeout>[] = []

  const revealAll = () =>
    document.querySelectorAll('.reveal:not(.revealed)').forEach(el => el.classList.add('revealed'))
  const observeAll = () =>
    observer && document.querySelectorAll('.reveal:not(.revealed)').forEach(el => observer!.observe(el))

  onMounted(() => {
    nextTick(() => {
      if (!('IntersectionObserver' in window)) { revealAll(); return }

      observer = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            ;(entry.target as HTMLElement).classList.add('revealed')
            observer!.unobserve(entry.target)
          }
        }
      }, { threshold, rootMargin })

      observeAll()

      // A hydration mismatch can swap the observed nodes for fresh ones the observer
      // never saw → those sections stay stuck at opacity:0. Re-scan shortly after
      // hydration settles to observe the new nodes (keeps the scroll-reveal effect).
      timers.push(setTimeout(observeAll, 400))

      // Hard safety net: if anything at/above the fold is still unrevealed after a beat,
      // the observer is broken for it — reveal EVERYTHING so content is never invisible.
      timers.push(setTimeout(() => {
        const vh = window.innerHeight || 0
        const stuck = [...document.querySelectorAll('.reveal:not(.revealed)')]
          .some(el => el.getBoundingClientRect().top < vh)
        if (stuck) revealAll()
      }, 2000))
    })
  })

  onUnmounted(() => {
    observer?.disconnect()
    observer = null
    timers.forEach(clearTimeout)
  })
}
