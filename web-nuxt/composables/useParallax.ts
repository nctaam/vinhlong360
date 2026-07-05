import { onMounted, onUnmounted } from 'vue'

type Targets = () => HTMLElement[]

/**
 * Opt-in, below-fold scroll parallax. Attaches ONE IntersectionObserver; while a
 * target is in view, sets `--parallax: <px>` on it via a rAF-throttled scroll handler.
 * Consumers apply `transform: translate3d(0, var(--parallax, 0), 0)` on the layer.
 *
 * No-op on the server, when `prefers-reduced-motion: reduce`, or when
 * IntersectionObserver is unavailable — so it is safe for SSR + a11y.
 */
export function useParallax(targets: Targets, opts: { intensity?: number } = {}) {
  if (!import.meta.client) return
  const intensity = opts.intensity ?? 0.08
  const reduce = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduce || typeof IntersectionObserver === 'undefined') return

  let observer: IntersectionObserver | null = null
  const visible = new Set<HTMLElement>()
  let ticking = false

  const update = () => {
    ticking = false
    const vh = window.innerHeight || 1
    for (const el of visible) {
      const r = el.getBoundingClientRect()
      // p: 0 at viewport centre, negative above, positive below
      const p = (r.top + r.height / 2 - vh / 2) / vh
      el.style.setProperty('--parallax', `${(-p * intensity * r.height).toFixed(1)}px`)
    }
  }
  const onScroll = () => {
    if (!ticking) { ticking = true; requestAnimationFrame(update) }
  }

  onMounted(() => {
    const els = targets()
    if (!els.length) return
    observer = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting) visible.add(e.target as HTMLElement)
        else visible.delete(e.target as HTMLElement)
      }
      if (visible.size) onScroll()
    }, { rootMargin: '10% 0px 10% 0px' })
    els.forEach(el => observer!.observe(el))
    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
  })

  onUnmounted(() => {
    observer?.disconnect()
    observer = null
    window.removeEventListener('scroll', onScroll)
  })
}
