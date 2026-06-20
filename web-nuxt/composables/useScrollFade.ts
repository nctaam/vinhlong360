export function useScrollFade() {
  if (!import.meta.client) return

  const route = useRoute()

  function initScrollRows() {
    nextTick(() => {
      const rows = document.querySelectorAll<HTMLElement>('.scroll-row')
      rows.forEach(row => {
        if ((row as HTMLElement & { __scrollFadeBound?: boolean }).__scrollFadeBound) return
        ;(row as HTMLElement & { __scrollFadeBound?: boolean }).__scrollFadeBound = true

        function checkEnd() {
          const atEnd = row.scrollLeft + row.clientWidth >= row.scrollWidth - 8
          row.classList.toggle('scroll-end', atEnd)
        }

        checkEnd()
        row.addEventListener('scroll', checkEnd, { passive: true })
      })
    })
  }

  onMounted(initScrollRows)
  watch(() => route.path, () => { setTimeout(initScrollRows, 300) })
}
