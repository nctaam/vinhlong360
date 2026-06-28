export function useDebounce<T extends (...args: any[]) => void>(fn: T, delay: number) {
  let timer: ReturnType<typeof setTimeout> | null = null

  const debounced = (...args: Parameters<T>) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => fn(...args), delay)
  }

  const cancel = () => {
    if (timer) { clearTimeout(timer); timer = null }
  }

  if (getCurrentInstance()) {
    onUnmounted(cancel)
  }

  return { debounced, cancel }
}
