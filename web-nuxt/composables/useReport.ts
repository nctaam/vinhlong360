/**
 * useReport — báo cáo bài viết vi phạm → POST /api/report (GĐ5.4 / GĐ13.6f).
 *
 * Endpoint lưu reports.jsonl cho admin xử lý (gỡ trong 24/48h theo NĐ147).
 * KHÔNG đăng/khoá tự động. Yêu cầu đăng nhập (client-gated) để giảm spam.
 */
export function useReport() {
  const { isLoggedIn, authHeaders } = useAuth()
  const { show: showToast } = useToast()

  async function reportPost(postId: string) {
    if (!isLoggedIn.value) {
      showToast('Vui lòng đăng nhập để báo cáo', 'error')
      return
    }
    const reason = window.prompt('Lý do báo cáo bài viết này?')
    if (!reason || reason.trim().length < 5) return
    try {
      await $fetch('/api/report', {
        method: 'POST',
        headers: authHeaders(),
        body: { target_type: 'post', target_id: postId, reason: reason.trim() },
      })
      showToast('Đã gửi báo cáo. Cảm ơn bạn!', 'success')
    } catch (e: any) {
      showToast(e?.data?.detail || e?.data?.message || 'Không thể gửi báo cáo', 'error')
    }
  }

  return { reportPost }
}
