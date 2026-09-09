import { ref, type Ref } from 'vue'
import type { Post } from '~/types'
import type { PostListResponse } from '~/composables/useCommunityPostFilters'

export interface UseCommunityFeedPaginationOptions {
  activeTab: Ref<string>
  sort: Ref<string>
  filterType: Ref<string>
  activeTag: Ref<string>
  searchMode: Ref<boolean>
  bookmarks: Ref<Post[]>
  bookmarksLoading: Ref<boolean>
  bookmarksPage: Ref<number>
  bookmarksHasMore: Ref<boolean>
  searchLoading: Ref<boolean>
  searchPage: Ref<number>
  searchHasMore: Ref<boolean>
  authHeaders: () => Record<string, string>
  showToast: (message: string, type?: 'info' | 'success' | 'warning' | 'error') => void
  fetchBookmarks: (reset?: boolean) => Promise<void> | void
  fetchSearch: (reset?: boolean) => Promise<void> | void
  filterCommunityPosts: (raw: Post[]) => Post[]
  mergeCommunityPosts: (prev: Post[], next: Post[]) => Post[]
  extractPostArray: (res: any) => Post[]
  responseHasMore: (res: any, raw: Post[]) => boolean
  normalizeCommunityRouteState?: () => void
}

export function useCommunityFeedPagination(options: UseCommunityFeedPaginationOptions) {
  const page = ref(1)
  const posts = ref<Post[]>([])
  const hasMore = ref(false)
  const loading = ref(false)
  const feedError = ref(false)
  const ugcUnavailable = ref(false)
  let feedAbort: AbortController | null = null

  async function fetchFeed(reset = false) {
    options.normalizeCommunityRouteState?.()
    if (options.activeTab.value === 'bookmarks') {
      await options.fetchBookmarks(reset)
      return
    }
    if (reset) {
      page.value = 1
      posts.value = []
      feedError.value = false
      ugcUnavailable.value = false
    }
    feedAbort?.abort()
    feedAbort = new AbortController()
    loading.value = true
    try {
      const url = options.activeTab.value === 'following'
        ? `/api/feed/following?page=${page.value}&limit=20`
        : (() => {
            const params = new URLSearchParams({
              page: String(page.value),
              limit: '20',
              sort: options.sort.value,
            })
            if (options.filterType.value) params.set('post_type', options.filterType.value)
            if (options.activeTag.value) params.set('tag', options.activeTag.value)
            return `/api/feed?${params}`
          })()
      const res = await $fetch<PostListResponse<Post>>(url, {
        headers: options.authHeaders(),
        signal: feedAbort.signal,
      })
      const rawPosts = options.extractPostArray(res)
      const newPosts = options.filterCommunityPosts(rawPosts)
      posts.value = reset ? newPosts : options.mergeCommunityPosts(posts.value, newPosts)
      hasMore.value = options.responseHasMore(res, rawPosts)
    } catch (e: unknown) {
      if (e instanceof DOMException && e.name === 'AbortError') return
      const status = (e as any)?.response?.status || (e as any)?.status || (e as any)?.statusCode
      if (status === 503) {
        ugcUnavailable.value = true
        return
      }
      if (reset && !posts.value.length) feedError.value = true
      options.showToast(reset ? 'Không thể tải bảng tin' : 'Không thể tải thêm', 'error')
    } finally {
      loading.value = false
    }
  }

  function refreshFeed() {
    if (options.searchMode.value) {
      options.fetchSearch(true)
      return
    }
    if (options.activeTab.value === 'bookmarks') {
      options.fetchBookmarks(true)
      return
    }
    fetchFeed(true)
  }

  function loadMore() {
    if (loading.value || options.searchLoading.value || options.bookmarksLoading.value) return
    if (options.searchMode.value) {
      options.searchPage.value++
      options.fetchSearch()
    } else if (options.activeTab.value === 'bookmarks') {
      options.bookmarksPage.value++
      options.fetchBookmarks()
    } else {
      page.value++
      fetchFeed()
    }
  }

  function abortFeed() {
    feedAbort?.abort()
  }

  return {
    page,
    posts,
    hasMore,
    loading,
    feedError,
    ugcUnavailable,
    fetchFeed,
    refreshFeed,
    loadMore,
    abortFeed,
  }
}
