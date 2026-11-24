export interface UseScrollProgressOptions {
  cssDriven?: boolean
}

export function useScrollProgress(options: UseScrollProgressOptions = {}) {
  const progress = ref(0)
  const isCssDriven = Boolean(
    options.cssDriven
    && import.meta.client
    && typeof CSS !== 'undefined'
    && typeof CSS.supports === 'function'
    && CSS.supports('animation-timeline', 'scroll()'),
  )

  if (!import.meta.client || isCssDriven) {
    return { progress, isCssDriven }
  }

  let rafId = 0

  function update() {
    const docHeight = document.documentElement.scrollHeight - window.innerHeight
    progress.value = docHeight > 0 ? Math.min(1, window.scrollY / docHeight) : 0
    rafId = 0
  }

  function onScroll() {
    if (!rafId) rafId = requestAnimationFrame(update)
  }

  onMounted(() => {
    window.addEventListener('scroll', onScroll, { passive: true })
    update()
  })

  onUnmounted(() => {
    window.removeEventListener('scroll', onScroll)
    if (rafId) cancelAnimationFrame(rafId)
  })

  return { progress, isCssDriven: false }
}
