export function useDropdown(
  open: Ref<boolean>,
  containerSelector: string,
  options: { itemSelector?: string; triggerRef?: Ref<HTMLElement | undefined> } = {},
) {
  const { itemSelector = '[role="menuitem"]', triggerRef } = options

  function close() {
    open.value = false
    triggerRef?.value?.focus()
  }

  function onClickOutside(e: MouseEvent) {
    if (!(e.target as HTMLElement).closest(containerSelector)) open.value = false
  }

  function onEscKey(e: KeyboardEvent) {
    if (e.key === 'Escape' && open.value) close()
  }

  function onMenuKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') { close(); return }
    const container = e.currentTarget as HTMLElement
    const items = Array.from(container.querySelectorAll<HTMLElement>(itemSelector))
    if (!items.length) return
    if (e.key === 'Home') { e.preventDefault(); items[0]?.focus(); return }
    if (e.key === 'End') { e.preventDefault(); items[items.length - 1]?.focus(); return }
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
    e.preventDefault()
    const cur = items.indexOf(document.activeElement as HTMLElement)
    const next = e.key === 'ArrowDown'
      ? (cur + 1) % items.length
      : (cur - 1 + items.length) % items.length
    items[next]?.focus()
  }

  onMounted(() => {
    document.addEventListener('click', onClickOutside)
    document.addEventListener('keydown', onEscKey)
  })
  onUnmounted(() => {
    document.removeEventListener('click', onClickOutside)
    document.removeEventListener('keydown', onEscKey)
  })

  return { close, onMenuKeydown }
}
