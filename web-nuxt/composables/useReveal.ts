import { getCurrentScope, onScopeDispose } from 'vue'

export function useReveal(options: { threshold?: number; rootMargin?: string } = {}) {
  if (!import.meta.client) return

  const threshold = options.threshold ?? 0.1
  const rootMargin = options.rootMargin ?? '0px 0px -30px 0px'
  let observer: IntersectionObserver | null = null
  let mutations: MutationObserver | null = null
  const timers: ReturnType<typeof setTimeout>[] = []
  let observed = new WeakSet<Element>()

  const revealAll = () =>
    document.querySelectorAll('.reveal:not(.revealed)').forEach(el => el.classList.add('revealed'))

  const observeElement = (el: Element) => {
    if (!observer || observed.has(el) || el.classList.contains('revealed')) return
    observed.add(el)
    observer.observe(el)
  }

  const observeAll = () => {
    if (!observer) return
    document.querySelectorAll('.reveal:not(.revealed)').forEach(observeElement)
  }

  const cleanup = () => {
    observer?.disconnect()
    observer = null
    mutations?.disconnect()
    mutations = null
    while (timers.length > 0) {
      clearTimeout(timers.pop()!)
    }
    observed = new WeakSet<Element>()
  }

  onMounted(() => {
    nextTick(() => {
      const reducedMotion = document.documentElement.dataset.reducedMotion === 'true'
        || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true
      if (!('IntersectionObserver' in window) || reducedMotion) {
        revealAll()
        return
      }

      observer = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            ;(entry.target as HTMLElement).classList.add('revealed')
            observer?.unobserve(entry.target)
          }
        }
      }, { threshold, rootMargin })

      observeAll()

      timers.push(setTimeout(observeAll, 400))

      timers.push(setTimeout(() => {
        const vh = window.innerHeight || 0
        const stuck = [...document.querySelectorAll('.reveal:not(.revealed)')]
          .some(el => el.getBoundingClientRect().top < vh)
        if (stuck) revealAll()
      }, 2000))

      mutations = new MutationObserver((records) => {
        for (const record of records) {
          for (const node of record.addedNodes) {
            if (!(node instanceof HTMLElement)) continue
            if (node.classList.contains('reveal') && !node.classList.contains('revealed')) {
              observeElement(node)
            }
            if (node.childElementCount > 0) {
              node.querySelectorAll('.reveal:not(.revealed)').forEach(observeElement)
            }
          }
        }
      })
      mutations.observe(document.body, { childList: true, subtree: true })
    })
  })

  onUnmounted(cleanup)
  if (getCurrentScope()) onScopeDispose(cleanup)
}
