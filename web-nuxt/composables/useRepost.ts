// Threads-style repost dùng chung (cong-dong/nguoi-dung/bai-viet).
export function useRepost() {
  const { isLoggedIn, authFetch } = useAuth()
  const { openAuth } = useAuthModal()
  const { confirmDialog } = useConfirm()
  const { show: showToast } = useToast()
  const pendingReposts = useState<Record<string, boolean>>('repost:pending', () => ({}))

  async function repost(postId: string, onDone?: () => void): Promise<boolean> {
    const normalizedId = postId.trim()
    if (!normalizedId || pendingReposts.value[normalizedId]) return false
    if (!isLoggedIn.value) { openAuth(() => { if (isLoggedIn.value) void repost(normalizedId, onDone) }); return false }
    if (!await confirmDialog('Đăng lại bài này lên trang của bạn?', { confirmText: 'Đăng lại' })) return false
    if (pendingReposts.value[normalizedId]) return false
    pendingReposts.value[normalizedId] = true
    try {
      await authFetch('/api/posts', { method: 'POST', body: { repost_of: normalizedId, content: '' } })
      showToast('Đã đăng lại', 'success')
      onDone?.()
      return true
    } catch (e: unknown) {
      showToast(extractErrorMessage(e, 'Không thể đăng lại'), 'error')
      return false
    } finally {
      delete pendingReposts.value[normalizedId]
    }
  }
  // Trích dẫn: mở composer cộng-đồng ở chế-độ quote (composer chỉ có ở /cong-dong).
  function quote(postId: string) {
    const normalizedId = postId.trim()
    if (!normalizedId) return
    if (!isLoggedIn.value) { openAuth(() => { if (isLoggedIn.value) quote(normalizedId) }); return }
    navigateTo(`/cong-dong?quote=${encodeURIComponent(normalizedId)}`)
  }

  return { repost, quote }
}
