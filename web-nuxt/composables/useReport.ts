/**
 * useReport — báo cáo nội dung vi phạm → mở ReportModal (POST /api/report).
 *
 * Endpoint lưu reports.jsonl cho admin xử lý (gỡ trong 24/48h theo NĐ147).
 * KHÔNG đăng/khoá tự động. Yêu cầu đăng nhập (client-gated) để giảm spam.
 *
 * Trước đây dùng window.prompt() — hỏng trên mobile & screen-reader; nay mở
 * một modal có chips lý do + ô mô tả (ReportModal.vue, gắn ở layout).
 */
export interface ReportModalState {
  open: boolean
  targetType: 'post' | 'entity' | 'comment' | 'user'
  targetId: string
}

export function useReport() {
  const { isLoggedIn } = useAuth()
  const { show: showToast } = useToast()
  const modal = useState<ReportModalState>('report-modal', () => ({ open: false, targetType: 'post', targetId: '' }))

  function open(targetType: ReportModalState['targetType'], targetId: string) {
    if (!isLoggedIn.value) {
      showToast('Vui lòng đăng nhập để báo cáo', 'error')
      return
    }
    modal.value = { open: true, targetType, targetId }
  }

  // Back-compat: existing callers use reportPost(postId).
  function reportPost(postId: string) { open('post', postId) }

  return { reportPost, openReport: open, reportModal: modal }
}
