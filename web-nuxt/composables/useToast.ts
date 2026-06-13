interface Toast {
  id: number
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
}

let nextId = 0

export function useToast() {
  const toasts = useState<Toast[]>('toast-list', () => [])
  function show(message: string, type: Toast['type'] = 'success', duration = 3000) {
    const id = nextId++
    toasts.value.push({ id, message, type })
    if (duration > 0) {
      setTimeout(() => {
        toasts.value = toasts.value.filter(t => t.id !== id)
      }, duration)
    }
  }

  return { toasts, show }
}
