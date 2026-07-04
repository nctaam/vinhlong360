/**
 * useScrollReveal — reveal elements as they scroll into view, for the cinematic-editorial
 * pages. Add class `reveal` (from editorial.css) to any element; this adds `is-visible`
 * when it enters the viewport. No dependency (IntersectionObserver).
 *
 * Honours prefers-reduced-motion: if the user prefers reduced motion, everything is marked
 * visible immediately and no observer runs. SSR-safe (client-only side effects).
 *
 * Usage in a page:
 *   useScrollReveal()                      // observes the whole document
 *   useScrollReveal(() => rootEl.value)    // scope to a container ref
 */
export function useScrollReveal(root?: () => HTMLElement | null | undefined) {
  if (!import.meta.client) return

  let observer: IntersectionObserver | null = null

  const revealAll = (scope: ParentNode) => {
    scope.querySelectorAll<HTMLElement>('.reveal:not(.is-visible)').forEach((el) => el.classList.add('is-visible'))
  }

  const start = () => {
    const scope: ParentNode = (root?.() as ParentNode) || document
    const prefersReduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const supported = typeof IntersectionObserver !== 'undefined'

    // Reduced motion or unsupported → show everything, skip observing.
    if (prefersReduced || !supported) { revealAll(scope); return }

    observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible')
          observer?.unobserve(entry.target)
        }
      }
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 })

    scope.querySelectorAll<HTMLElement>('.reveal').forEach((el) => observer!.observe(el))
  }

  onMounted(() => nextTick(start))
  onBeforeUnmount(() => { observer?.disconnect(); observer = null })
}
