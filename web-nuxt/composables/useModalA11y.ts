/**
 * useModalA11y — shared accessibility behaviour for modals / bottom-sheets.
 *
 * On open:
 *   - remembers the element that had focus (the trigger)
 *   - locks body scroll (document.body.style.overflow = 'hidden')
 *   - moves focus to the first focusable element inside the dialog
 *   - listens for keydown: Escape → close, Tab → trap focus within the dialog
 *     (including the close button), cycling first↔last.
 * On close:
 *   - unlocks body scroll, removes the listener
 *   - restores focus to the trigger element
 *
 * SSR-safe (all document access guarded) and cleans up on unmount. Replaces the
 * per-component ESC/focus handlers that previously duplicated this logic.
 *
 * @param isOpen     reactive open state (the modal's visible/open ref)
 * @param modalRef   template ref pointing at the dialog root element
 * @param options.onClose    called when the user requests close (Escape)
 * @param options.trapFocus  enable Tab focus-trapping (default true)
 */
export function useModalA11y(
  isOpen: Ref<boolean>,
  modalRef: Ref<HTMLElement | null>,
  options: { onClose?: () => void; trapFocus?: boolean } = {},
) {
  const { onClose, trapFocus = true } = options
  let triggerEl: HTMLElement | null = null

  const FOCUSABLE =
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

  function focusableEls(): HTMLElement[] {
    if (!modalRef.value) return []
    return Array.from(modalRef.value.querySelectorAll<HTMLElement>(FOCUSABLE))
      // visible only (offsetParent is null for display:none / detached els)
      .filter(el => el.offsetParent !== null || el === document.activeElement)
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.stopPropagation()
      onClose?.()
      return
    }
    if (!trapFocus || e.key !== 'Tab' || !modalRef.value) return
    const list = focusableEls()
    if (!list.length) {
      // Nothing focusable yet — keep focus inside the dialog root.
      e.preventDefault()
      modalRef.value.focus?.()
      return
    }
    const first = list[0]
    const last = list[list.length - 1]
    const active = document.activeElement as HTMLElement | null
    if (e.shiftKey) {
      if (active === first || !modalRef.value.contains(active)) {
        e.preventDefault()
        last?.focus()
      }
    } else {
      if (active === last || !modalRef.value.contains(active)) {
        e.preventDefault()
        first?.focus()
      }
    }
  }

  function activate() {
    if (typeof document === 'undefined') return
    triggerEl = document.activeElement as HTMLElement
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', onKeydown)
    nextTick(() => {
      const list = focusableEls()
      ;(list[0] ?? modalRef.value)?.focus?.()
    })
  }

  function deactivate(restore = true) {
    if (typeof document === 'undefined') return
    document.body.style.overflow = ''
    document.removeEventListener('keydown', onKeydown)
    if (restore && triggerEl) {
      nextTick(() => triggerEl?.focus?.())
    }
  }

  // immediate: a modal mounted already-open (v-if pattern) sets isOpen=true before
  // the watch is registered, so without immediate the open transition is missed
  // (no scroll-lock, no focus move). Firing immediately covers both mount patterns;
  // for an always-mounted-closed modal the initial call is a harmless deactivate().
  watch(isOpen, (open) => {
    if (open) activate()
    else deactivate()
  }, { immediate: true })

  onUnmounted(() => deactivate(false))
}
