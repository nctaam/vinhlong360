interface PostLike {
  id: string
  user_liked?: boolean
  likes?: number
  user_bookmarked?: boolean
}

export function usePostActions() {
  const { authHeaders, handleSessionExpired, isLoggedIn } = useAuth()
  const { show: showToast } = useToast()
  const { confirmDialog } = useConfirm()
  const pending = reactive(new Set<string>())

  function isPending(key: string) {
    return pending.has(key)
  }

  async function toggleLike<T extends PostLike>(
    postId: string,
    targets: T | T[],
  ) {
    if (!isLoggedIn.value) { showToast('Đăng nhập để thích bài viết', 'info'); return }
    const key = `like:${postId}`
    if (pending.has(key)) return
    pending.add(key)
    const items = Array.isArray(targets) ? targets : [targets]
    const flip = () => items.forEach(p => {
      p.user_liked = !p.user_liked
      p.likes = (p.likes || 0) + (p.user_liked ? 1 : -1)
    })
    flip()
    try {
      await $fetch(`/api/posts/${postId}/like`, { method: 'POST', headers: authHeaders() })
    } catch (e: unknown) {
      flip()
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể thích bài viết', 'error')
    } finally { pending.delete(key) }
  }

  async function toggleBookmark<T extends PostLike>(
    postId: string,
    targets: T | T[],
    onBookmarked?: () => void,
  ) {
    if (!isLoggedIn.value) { showToast('Đăng nhập để lưu bài viết', 'info'); return }
    const key = `bm:${postId}`
    if (pending.has(key)) return
    pending.add(key)
    const items = Array.isArray(targets) ? targets : [targets]
    const wasBookmarked = items[0]?.user_bookmarked
    items.forEach(p => { p.user_bookmarked = !p.user_bookmarked })
    try {
      await $fetch(`/api/posts/${postId}/bookmark`, { method: 'POST', headers: authHeaders() })
      if (!wasBookmarked && items[0]?.user_bookmarked) {
        showToast('Đã lưu bài viết', 'success')
        onBookmarked?.()
      }
    } catch (e: unknown) {
      items.forEach(p => { p.user_bookmarked = !p.user_bookmarked })
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể lưu bài viết', 'error')
    } finally { pending.delete(key) }
  }

  async function deletePost(
    postId: string,
    onSuccess?: () => void,
  ) {
    const ok = await confirmDialog('Bạn có chắc muốn xoá bài viết này? Hành động không thể hoàn tác.', { confirmText: 'Xoá', danger: true })
    if (!ok) return
    try {
      await $fetch(`/api/posts/${postId}`, { method: 'DELETE', headers: authHeaders() })
      showToast('Đã xoá bài viết', 'success')
      onSuccess?.()
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể xoá bài viết', 'error')
    }
  }

  return { toggleLike, toggleBookmark, deletePost, isPending, isLoggedIn }
}
