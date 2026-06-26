// Threads-style repost dùng chung (cong-dong/nguoi-dung/bai-viet).
export function useRepost() {
  const { isLoggedIn, authHeaders } = useAuth()
  const { openAuth } = useAuthModal()
  const { confirmDialog } = useConfirm()
  const { show: showToast } = useToast()

  async function repost(postId: string, onDone?: () => void): Promise<boolean> {
    if (!isLoggedIn.value) { openAuth(() => { if (isLoggedIn.value) repost(postId, onDone) }); return false }
    if (!await confirmDialog('Đăng lại bài này lên trang của bạn?', { confirmText: 'Đăng lại' })) return false
    try {
      await $fetch('/api/posts', { method: 'POST', headers: authHeaders(), body: { repost_of: postId, content: '' } })
      showToast('Đã đăng lại 🔁', 'success')
      onDone?.()
      return true
    } catch (e: any) {
      showToast(e?.data?.detail || 'Không thể đăng lại', 'error')
      return false
    }
  }
  // Trích dẫn: mở composer cộng-đồng ở chế-độ quote (composer chỉ có ở /cong-dong).
  function quote(postId: string) {
    if (!isLoggedIn.value) { openAuth(() => { if (isLoggedIn.value) quote(postId) }); return }
    navigateTo(`/cong-dong?quote=${encodeURIComponent(postId)}`)
  }

  return { repost, quote }
}
