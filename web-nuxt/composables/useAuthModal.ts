const _callback = ref<(() => void) | null>(null)

export function safeAuthReturnPath(value: unknown): string {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//')) return ''
  try {
    const url = new URL(value, 'https://vinhlong360.local')
    if (url.origin !== 'https://vinhlong360.local') return ''
    return `${url.pathname}${url.search}${url.hash}`.slice(0, 1_024)
  } catch {
    return ''
  }
}

export function useAuthModal() {
  const open = useState('auth-modal-open', () => false)
  const returnPath = useState('auth-modal-return-path', () => '')
  const route = useRoute()

  function rememberReturnPath(value: unknown) {
    returnPath.value = safeAuthReturnPath(value)
  }

  function consumeReturnPath() {
    const value = safeAuthReturnPath(returnPath.value)
    returnPath.value = ''
    return value
  }

  return {
    open,
    openAuth: (cb?: () => void) => {
      _callback.value = cb || null
      rememberReturnPath(route.fullPath)
      open.value = true
    },
    closeAuth: () => { open.value = false },
    rememberReturnPath,
    consumeReturnPath,
    onLoginSuccess: () => {
      const nextPath = consumeReturnPath()
      if (_callback.value) {
        const callback = _callback.value
        _callback.value = null
        callback()
      }
      return nextPath
    },
  }
}
