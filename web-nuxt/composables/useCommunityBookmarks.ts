import type { Ref } from 'vue'
import type { Post } from '~/types'

type PostListResponse = import('~/composables/useCommunityPostFilters').PostListResponse<Post>

export interface CommunityBookmarksOptions {
  authHeaders: () => Record<string, string>
  handleSessionExpired: () => void
  showToast: (msg: string, type?: 'info' | 'success' | 'warning' | 'error') => void
  filterCommunityPosts: (posts: Post[]) => Post[]
  mergeCommunityPosts: (existing: Post[], incoming: Post[]) => Post[]
  extractPostArray: (res: unknown, key?: 'posts' | 'bookmarks') => Post[]
  responseHasMore: (res: unknown, posts: Post[]) => boolean
}

export function useCommunityBookmarks(options: CommunityBookmarksOptions) {
  const bookmarks = ref<Post[]>([])
  const bookmarksLoading = ref(false)
  const bookmarksPage = ref(1)
  const bookmarksHasMore = ref(false)
  const sessionBookmarked = ref(false)
  const bookmarkBannerDismissed = ref(false)

  async function fetchBookmarks(reset = false) {
    if (reset) { bookmarksPage.value = 1; bookmarks.value = [] }
    bookmarksLoading.value = true
    try {
      const res = await $fetch<PostListResponse>(`/api/me/bookmarks?page=${bookmarksPage.value}&limit=20`, {
        headers: options.authHeaders(),
      })
      const rawPosts = options.extractPostArray(res, 'bookmarks')
      const newPosts = options.filterCommunityPosts(rawPosts)
      bookmarks.value = reset ? newPosts : options.mergeCommunityPosts(bookmarks.value, newPosts)
      bookmarksHasMore.value = options.responseHasMore(res, rawPosts)
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { options.handleSessionExpired(); return }
      options.showToast('Không thể tải bài viết đã lưu', 'error')
    } finally {
      bookmarksLoading.value = false
    }
  }

  return {
    bookmarks,
    bookmarksLoading,
    bookmarksPage,
    bookmarksHasMore,
    sessionBookmarked,
    bookmarkBannerDismissed,
    fetchBookmarks,
  }
}
