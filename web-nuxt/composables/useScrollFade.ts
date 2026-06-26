export function useScrollFade() {
  if (!import.meta.client) return

  const route = useRoute()
  const cleanups: Array<() => void> = []
  let routeTimeout: ReturnType<typeof setTimeout> | null = null

  function initScrollRows() {
    nextTick(() => {
      const rows = document.querySelectorAll<HTMLElement>('.scroll-row')
      rows.forEach(row => {
        if ((row as HTMLElement & { __scrollFadeBound?: boolean }).__scrollFadeBound) return
        ;(row as HTMLElement & { __scrollFadeBound?: boolean }).__scrollFadeBound = true

        let rafId = 0
        function checkEnd() {
          const atEnd = row.scrollLeft + row.clientWidth >= row.scrollWidth - 8
          row.classList.toggle('scroll-end', atEnd)
        }
        function onScroll() {
          if (!rafId) rafId = requestAnimationFrame(() => { rafId = 0; checkEnd() })
        }

        checkEnd()
        row.addEventListener('scroll', onScroll, { passive: true })
        cleanups.push(() => { row.removeEventListener('scroll', onScroll); cancelAnimationFrame(rafId) })
      })
    })
  }

  onMounted(initScrollRows)
  watch(() => route.path, () => {
    if (routeTimeout) clearTimeout(routeTimeout)
    routeTimeout = setTimeout(initScrollRows, 300)
  })
  onUnmounted(() => {
    cleanups.forEach(fn => fn())
    cleanups.length = 0
    if (routeTimeout) clearTimeout(routeTimeout)
  })
}
