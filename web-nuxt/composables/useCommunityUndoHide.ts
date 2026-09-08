import { ref, type Ref } from 'vue'
import type { Post } from '~/types'
import { useHiddenPosts } from '~/composables/useHiddenPosts'

export interface UseCommunityUndoHideOptions {
  posts: Ref<Post[]>
  bookmarks: Ref<Post[]>
  searchResults: Ref<Post[]>
  fetchFeed: (reset?: boolean) => Promise<void> | void
  showToast: (message: string, type?: 'info' | 'success' | 'warning' | 'error') => void
  hidePostFn?: (postId: string, lists: Ref<Post[]>[]) => Promise<boolean>
  unhidePostFn?: (postId: string) => Promise<boolean>
}

export function useCommunityUndoHide(options: UseCommunityUndoHideOptions) {
  const { hidePost: defaultHide, unhidePost: defaultUnhide } = useHiddenPosts()
  const _hide = options.hidePostFn || defaultHide
  const _unhide = options.unhidePostFn || defaultUnhide

  const hiddenNotice = ref<{ id: string } | null>(null)
  const undoingHide = ref(false)
  let hiddenNoticeTimer: ReturnType<typeof setTimeout> | null = null

  function dismissHiddenNotice() {
    if (hiddenNoticeTimer) {
      clearTimeout(hiddenNoticeTimer)
      hiddenNoticeTimer = null
    }
    hiddenNotice.value = null
  }

  async function hidePost(postId: string) {
    // Lạc quan + hoàn nguyên nằm trong useHiddenPosts: API lỗi thì bài quay lại
    // ĐÚNG vị trí cũ kèm toast lỗi, và `ok=false` nên không hiện dải "Hoàn tác".
    const ok = await _hide(postId, [options.posts, options.bookmarks, options.searchResults])
    if (!ok) return
    dismissHiddenNotice()
    hiddenNotice.value = { id: postId }
    hiddenNoticeTimer = setTimeout(() => {
      hiddenNotice.value = null
      hiddenNoticeTimer = null
    }, 8000)
  }

  async function undoHide() {
    const notice = hiddenNotice.value
    if (!notice || undoingHide.value) return
    undoingHide.value = true
    try {
      const ok = await _unhide(notice.id)
      if (!ok) return
      dismissHiddenNotice()
      options.showToast('Đã bỏ ẩn bài viết', 'success')
      // Nạp lại feed để bài về đúng thứ tự backend trả, không phải vị trí đoán.
      await options.fetchFeed(true)
    } finally {
      undoingHide.value = false
    }
  }

  function cleanupUndoHide() {
    dismissHiddenNotice()
  }

  return {
    hiddenNotice,
    undoingHide,
    hidePost,
    undoHide,
    dismissHiddenNotice,
    cleanupUndoHide,
  }
}
