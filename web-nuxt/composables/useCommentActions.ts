/**
 * Quyền của người dùng với BÌNH LUẬN của chính họ.
 *
 * `PUT /api/comments/{id}` (agent/social.py:2464) và `DELETE /api/comments/{id}`
 * (agent/social.py:2508) đã hoàn chỉnh từ lâu nhưng frontend chưa từng gọi, nên
 * người dùng không sửa/xoá được bình luận của mình. Composable này nối hai
 * endpoint đó theo đúng khuôn của `usePostActions` (authHeaders có CSRF,
 * confirmDialog trước thao tác xoá, 401 → handleSessionExpired, lỗi khác →
 * toast). KHÔNG nuốt lỗi im lặng: đây là thao tác dữ liệu, không phải beacon.
 *
 * Quyền lấy từ hành vi thật của backend, đã khoá bằng
 * tests/test_social_comment_ownership.py:
 *   - Sửa: CHỈ tác giả, trong 24 giờ đầu. Admin cũng bị 403 — quản trị không
 *     mạo danh lời người khác.
 *   - Xoá: tác giả HOẶC admin/moderator (social.py:2528).
 *   - Xoá là soft-delete và kéo theo mọi trả lời con (social.py:2534) → phải
 *     cảnh báo số trả lời sẽ bị ẩn theo TRƯỚC khi gọi API.
 */
/** Khớp config.COMMENT_EDIT_WINDOW_HOURS (mặc định 24). Chỉ dùng để ẩn nút cho
 *  đỡ bấm vào chỗ chết — backend vẫn là nơi quyết định, và 400 của nó được hiển
 *  thị nguyên văn nếu hai bên lệch nhau. */
export const COMMENT_EDIT_WINDOW_HOURS = 24

export const COMMENT_MIN_LENGTH = 2
export const COMMENT_MAX_LENGTH = 2000

const MODERATOR_ROLES = ['admin', 'moderator']

export interface CommentLike {
  id: string
  content?: string
  created_at?: string
  author?: { id?: string | null }
  replies?: Array<{ id: string }>
}

/** Giờ đã trôi qua kể từ lúc bình luận được tạo; `null` khi mốc thời gian không đọc được. */
export function hoursSince(iso?: string): number | null {
  if (!iso) return null
  const ms = Date.parse(iso)
  if (Number.isNaN(ms)) return null
  return (Date.now() - ms) / 3_600_000
}

export function useCommentActions() {
  const { authHeaders, handleSessionExpired, user } = useAuth()
  const { show: showToast } = useToast()
  const { confirmDialog } = useConfirm()

  function isAuthor(comment: CommentLike | null | undefined): boolean {
    const me = user.value?.id
    const them = comment?.author?.id
    return !!me && !!them && String(me) === String(them)
  }

  /** Sửa: chỉ tác giả, chỉ trong cửa sổ 24h. Mốc thời gian hỏng → vẫn cho bấm,
   *  để backend phán quyết thay vì FE tự khoá oan. */
  function canEdit(comment: CommentLike | null | undefined): boolean {
    if (!isAuthor(comment)) return false
    const age = hoursSince(comment?.created_at)
    return age === null || age < COMMENT_EDIT_WINDOW_HOURS
  }

  /** Xoá: tác giả hoặc admin/moderator — giống nhánh quyền ở social.py:2528. */
  function canDelete(comment: CommentLike | null | undefined): boolean {
    if (!comment) return false
    if (isAuthor(comment)) return true
    return MODERATOR_ROLES.includes(String(user.value?.role || ''))
  }

  /**
   * Lưu nội dung mới. Trả `null` khi thất bại để nơi gọi giữ nguyên ô sửa và
   * người dùng không mất chữ đã gõ.
   *
   * `moderation_status` là trạng thái kiểm duyệt của CHÍNH bình luận vừa sửa —
   * backend chỉ trả nó cho chủ bình luận (agent/social.py `_format_comment`).
   * Sửa xong có thể bị hạ xuống 'pending' và bình luận biến khỏi danh sách; nhờ
   * trường này nơi gọi biết ngay thay vì phải tải lại rồi suy ra. `undefined`
   * nghĩa là backend không nói (ví dụ nhánh dự phòng bên dưới) — KHÔNG phải
   * "đã duyệt".
   */
  async function saveComment(
    commentId: string,
    content: string,
  ): Promise<{ id: string; content: string; moderation_status?: string } | null> {
    const trimmed = content.trim()
    if (trimmed.length < COMMENT_MIN_LENGTH) {
      showToast('Bình luận quá ngắn', 'error')
      return null
    }
    if (trimmed.length > COMMENT_MAX_LENGTH) {
      showToast(`Bình luận tối đa ${COMMENT_MAX_LENGTH} ký tự`, 'error')
      return null
    }
    const encoded = encodePathId(commentId)
    if (!encoded) return null
    try {
      const res = await $fetch<{ comment?: { id: string; content: string; moderation_status?: string } }>(`/api/comments/${encoded}`, {
        method: 'PUT',
        headers: authHeaders(),
        body: { content: trimmed },
      })
      return res?.comment ?? { id: commentId, content: trimmed }
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return null }
      showToast(extractErrorMessage(e, 'Không thể lưu bình luận — vui lòng thử lại'), 'error')
      return null
    }
  }

  /**
   * Xoá sau khi người dùng xác nhận. Trả `false` khi người dùng huỷ HOẶC khi
   * API lỗi — nơi gọi không được coi là đã xoá.
   */
  async function deleteComment(comment: CommentLike): Promise<boolean> {
    const replyCount = comment.replies?.length || 0
    const message = replyCount
      ? `Xoá bình luận này? ${replyCount} trả lời bên dưới cũng sẽ bị ẩn theo.`
      : 'Xoá bình luận này?'
    const ok = await confirmDialog(message, { confirmText: 'Xoá', danger: true })
    if (!ok) return false

    const encoded = encodePathId(comment.id)
    if (!encoded) return false
    try {
      await $fetch(`/api/comments/${encoded}`, { method: 'DELETE', headers: authHeaders() })
      showToast('Đã xoá bình luận', 'success')
      return true
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return false }
      showToast(extractErrorMessage(e, 'Không thể xoá bình luận — vui lòng thử lại'), 'error')
      return false
    }
  }

  return { isAuthor, canEdit, canDelete, saveComment, deleteComment }
}
