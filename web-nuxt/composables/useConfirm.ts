// P2-1: hộp xác nhận in-app (thay confirm()/alert() native — đẹp + đồng bộ, mobile tốt).
interface ConfirmState {
  open: boolean
  title: string
  message: string
  confirmText: string
  cancelText: string
  danger: boolean
  _resolve: ((v: boolean) => void) | null
}

export function useConfirm() {
  const state = useState<ConfirmState>('confirm-dialog', () => ({
    open: false, title: '', message: '', confirmText: 'Đồng ý', cancelText: 'Hủy', danger: false, _resolve: null,
  }))

  function confirmDialog(message: string, opts: Partial<Omit<ConfirmState, 'open' | '_resolve' | 'message'>> = {}): Promise<boolean> {
    return new Promise((resolve) => {
      state.value = {
        open: true,
        title: opts.title ?? 'Xác nhận',
        message,
        confirmText: opts.confirmText ?? 'Đồng ý',
        cancelText: opts.cancelText ?? 'Hủy',
        danger: opts.danger ?? false,
        _resolve: resolve,
      }
    })
  }

  function answer(v: boolean) {
    state.value._resolve?.(v)
    state.value = { ...state.value, open: false, _resolve: null }
  }

  return { state, confirmDialog, answer }
}
