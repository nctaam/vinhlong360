const _callback = ref<(() => void) | null>(null)

export function useAuthModal() {
  const open = useState('auth-modal-open', () => false)
  return {
    open,
    openAuth: (cb?: () => void) => { _callback.value = cb || null; open.value = true },
    closeAuth: () => { open.value = false },
    onLoginSuccess: () => { if (_callback.value) { _callback.value(); _callback.value = null } },
  }
}
