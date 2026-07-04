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
    const encodedPostId = encodePathId(postId)
    if (!encodedPostId) return
    const key = `like:${encodedPostId}`
    if (pending.has(key)) return
    pending.add(key)
    const items = Array.isArray(targets) ? targets : [targets]
    const previous = items.map(p => ({ target: p, user_liked: p.user_liked, likes: p.likes }))
    items.forEach(p => {
      p.user_liked = !p.user_liked
      p.likes = Math.max(0, (p.likes || 0) + (p.user_liked ? 1 : -1))
    })
    try {
      await $fetch(`/api/posts/${encodedPostId}/like`, { method: 'POST', headers: authHeaders() })
    } catch (e: unknown) {
      previous.forEach(prev => {
        prev.target.user_liked = prev.user_liked
        prev.target.likes = prev.likes
      })
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
    const encodedPostId = encodePathId(postId)
    if (!encodedPostId) return
    const key = `bm:${encodedPostId}`
    if (pending.has(key)) return
    pending.add(key)
    const items = Array.isArray(targets) ? targets : [targets]
    const previous = items.map(p => ({ target: p, user_bookmarked: p.user_bookmarked }))
    const wasBookmarked = items[0]?.user_bookmarked
    items.forEach(p => { p.user_bookmarked = !p.user_bookmarked })
    try {
      await $fetch(`/api/posts/${encodedPostId}/bookmark`, { method: 'POST', headers: authHeaders() })
      if (!wasBookmarked && items[0]?.user_bookmarked) {
        showToast('Đã lưu bài viết', 'success')
        onBookmarked?.()
      }
    } catch (e: unknown) {
      previous.forEach(prev => { prev.target.user_bookmarked = prev.user_bookmarked })
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
    const encodedPostId = encodePathId(postId)
    if (!encodedPostId) return
    try {
      await $fetch(`/api/posts/${encodedPostId}`, { method: 'DELETE', headers: authHeaders() })
      showToast('Đã xoá bài viết', 'success')
      onSuccess?.()
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể xoá bài viết', 'error')
    }
  }

  return { toggleLike, toggleBookmark, deletePost, isPending, isLoggedIn }
}
