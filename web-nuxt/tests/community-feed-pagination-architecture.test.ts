import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import type { Post } from '~/types'
import { useCommunityFeedPagination } from '../composables/useCommunityFeedPagination'
import { useCommunityUndoHide } from '../composables/useCommunityUndoHide'

describe('Moc 169: Community Feed Pagination & Undo-Hide Architecture', () => {
  const fetchMock = vi.fn()
  const showToastMock = vi.fn()
  const fetchBookmarksMock = vi.fn()
  const fetchSearchMock = vi.fn()

  function makePost(id: string, overrides: Partial<Post> = {}): Post {
    return {
      id,
      user_id: 'user-1',
      display_name: 'Nguyễn Du Khách',
      avatar_url: '',
      content: `Nội dung ${id}`,
      post_type: 'share',
      likes_count: 0,
      comments_count: 0,
      shares_count: 0,
      views_count: 0,
      liked: false,
      bookmarked: false,
      created_at: '2026-03-29T10:00:00Z',
      ...overrides,
    }
  }

  beforeEach(() => {
    fetchMock.mockReset()
    showToastMock.mockReset()
    fetchBookmarksMock.mockReset()
    fetchSearchMock.mockReset()
    vi.stubGlobal('$fetch', fetchMock)
  })

  describe('useCommunityFeedPagination', () => {
    it('initializes default pagination and error states cleanly', () => {
      const pagination = useCommunityFeedPagination({
        activeTab: ref('latest'),
        sort: ref('latest'),
        filterType: ref(''),
        activeTag: ref(''),
        searchMode: ref(false),
        bookmarks: ref([]),
        bookmarksLoading: ref(false),
        bookmarksPage: ref(1),
        bookmarksHasMore: ref(false),
        searchLoading: ref(false),
        searchPage: ref(1),
        searchHasMore: ref(false),
        authHeaders: () => ({}),
        showToast: showToastMock,
        fetchBookmarks: fetchBookmarksMock,
        fetchSearch: fetchSearchMock,
        filterCommunityPosts: (p) => p,
        mergeCommunityPosts: (prev, next) => [...prev, ...next],
        extractPostArray: (res) => res?.posts || [],
        responseHasMore: (res) => !!res?.has_more,
      })

      expect(pagination.page.value).toBe(1)
      expect(pagination.posts.value).toEqual([])
      expect(pagination.hasMore.value).toBe(false)
      expect(pagination.loading.value).toBe(false)
      expect(pagination.feedError.value).toBe(false)
      expect(pagination.ugcUnavailable.value).toBe(false)
    })

    it('fetches feed data and merges posts on page reset', async () => {
      fetchMock.mockResolvedValueOnce({
        posts: [makePost('p1'), makePost('p2')],
        has_more: true,
      })

      const pagination = useCommunityFeedPagination({
        activeTab: ref('latest'),
        sort: ref('latest'),
        filterType: ref(''),
        activeTag: ref(''),
        searchMode: ref(false),
        bookmarks: ref([]),
        bookmarksLoading: ref(false),
        bookmarksPage: ref(1),
        bookmarksHasMore: ref(false),
        searchLoading: ref(false),
        searchPage: ref(1),
        searchHasMore: ref(false),
        authHeaders: () => ({ Authorization: 'Bearer token-1' }),
        showToast: showToastMock,
        fetchBookmarks: fetchBookmarksMock,
        fetchSearch: fetchSearchMock,
        filterCommunityPosts: (p) => p,
        mergeCommunityPosts: (prev, next) => [...prev, ...next],
        extractPostArray: (res) => res?.posts || [],
        responseHasMore: (res) => !!res?.has_more,
      })

      await pagination.fetchFeed(true)

      expect(pagination.posts.value).toHaveLength(2)
      expect(pagination.posts.value[0]?.id).toBe('p1')
      expect(pagination.hasMore.value).toBe(true)
      expect(pagination.loading.value).toBe(false)
      expect(pagination.feedError.value).toBe(false)
      expect(pagination.ugcUnavailable.value).toBe(false)
    })

    it('differentiates 503 service outage from generic feed fetch failure', async () => {
      const error503 = Object.assign(new Error('Service Unavailable'), { status: 503 })
      fetchMock.mockRejectedValueOnce(error503)

      const pagination = useCommunityFeedPagination({
        activeTab: ref('latest'),
        sort: ref('latest'),
        filterType: ref(''),
        activeTag: ref(''),
        searchMode: ref(false),
        bookmarks: ref([]),
        bookmarksLoading: ref(false),
        bookmarksPage: ref(1),
        bookmarksHasMore: ref(false),
        searchLoading: ref(false),
        searchPage: ref(1),
        searchHasMore: ref(false),
        authHeaders: () => ({}),
        showToast: showToastMock,
        fetchBookmarks: fetchBookmarksMock,
        fetchSearch: fetchSearchMock,
        filterCommunityPosts: (p) => p,
        mergeCommunityPosts: (prev, next) => [...prev, ...next],
        extractPostArray: (res) => res?.posts || [],
        responseHasMore: (res) => !!res?.has_more,
      })

      await pagination.fetchFeed(true)

      expect(pagination.ugcUnavailable.value).toBe(true)
      expect(pagination.feedError.value).toBe(false)
      expect(showToastMock).not.toHaveBeenCalled()
    })
  })

  describe('useCommunityUndoHide', () => {
    it('manages optimistic hide and temporary notice state', async () => {
      const posts = ref([makePost('p1'), makePost('p2')])
      const bookmarks = ref<Post[]>([])
      const searchResults = ref<Post[]>([])
      const fetchFeedMock = vi.fn()
      const hidePostFnMock = vi.fn((_id, lists) => {
        lists[0].value = lists[0].value.filter((p: any) => p.id !== 'p1')
        return Promise.resolve(true)
      })

      const undoHideManager = useCommunityUndoHide({
        posts,
        bookmarks,
        searchResults,
        fetchFeed: fetchFeedMock,
        showToast: showToastMock,
        hidePostFn: hidePostFnMock,
      })

      expect(undoHideManager.hiddenNotice.value).toBeNull()

      await undoHideManager.hidePost('p1')

      expect(posts.value).toHaveLength(1)
      expect(undoHideManager.hiddenNotice.value).toEqual({ id: 'p1' })

      undoHideManager.dismissHiddenNotice()
      expect(undoHideManager.hiddenNotice.value).toBeNull()
    })

    it('unhides post and refreshes feed upon user undo confirmation', async () => {
      const posts = ref([makePost('p2')])
      const bookmarks = ref<Post[]>([])
      const searchResults = ref<Post[]>([])
      const fetchFeedMock = vi.fn()
      const unhidePostFnMock = vi.fn(() => Promise.resolve(true))

      const undoHideManager = useCommunityUndoHide({
        posts,
        bookmarks,
        searchResults,
        fetchFeed: fetchFeedMock,
        showToast: showToastMock,
        unhidePostFn: unhidePostFnMock,
      })

      undoHideManager.hiddenNotice.value = { id: 'p1' }
      await undoHideManager.undoHide()

      expect(unhidePostFnMock).toHaveBeenCalledWith('p1')
      expect(undoHideManager.hiddenNotice.value).toBeNull()
      expect(showToastMock).toHaveBeenCalledWith('Đã bỏ ẩn bài viết', 'success')
      expect(fetchFeedMock).toHaveBeenCalledWith(true)
    })
  })
})
