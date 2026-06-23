// Global auth-modal state so ANY page can open the login modal (P0-2).
// The modal itself is mounted once in layouts/default.vue.
export function useAuthModal() {
  const open = useState('auth-modal-open', () => false)
  return {
    open,
    openAuth: () => { open.value = true },
    closeAuth: () => { open.value = false },
  }
}
