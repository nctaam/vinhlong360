export function useScrollProgress() {
  const progress = ref(0)

  if (!import.meta.client) return { progress }

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

  return { progress }
}
