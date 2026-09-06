import type { Ref } from 'vue'
import type { Post } from '~/types'

type PostListResponse = import('~/composables/useCommunityPostFilters').PostListResponse<Post>

export interface CommunitySearchOptions {
  authHeaders: () => Record<string, string>
  handleSessionExpired: () => void
  showToast: (msg: string, type?: 'info' | 'success' | 'warning' | 'error') => void
  filterCommunityPosts: (posts: Post[]) => Post[]
  mergeCommunityPosts: (existing: Post[], incoming: Post[]) => Post[]
  extractPostArray: (res: any) => Post[]
  responseHasMore: (res: any, posts: Post[]) => boolean
  syncSearchQuery: (q: string) => void
  firstQueryValue: (val: unknown) => string
  getRouteQueryQ?: () => unknown
}

export function useCommunitySearch(options: CommunitySearchOptions) {
  const searchInput = ref('')
  const searchQuery = ref('')
  const searchResults = ref<Post[]>([])
  const searchPage = ref(1)
  const searchHasMore = ref(false)
  const searchLoading = ref(false)
  const searchMode = computed(() => !!searchQuery.value)
  const searchUsers = ref<Array<{ id: string; display_name: string; avatar_url: string; username: string; post_count: number }>>([])

  async function fetchSearchUsers(query: string) {
    if (!query || query.length < 2) { searchUsers.value = []; return }
    try {
      const res = await $fetch<{ users: typeof searchUsers.value }>('/api/search/users', {
        params: { q: query, page: 1 },
        headers: options.authHeaders(),
      })
      searchUsers.value = (res.users || []).slice(0, 5)
    } catch {
      searchUsers.value = []
    }
  }

  async function fetchSearch(reset = false) {
    if (reset) { searchPage.value = 1; searchResults.value = [] }
    searchLoading.value = true
    try {
      const res = await $fetch<PostListResponse>(
        `/api/search/posts?q=${encodeURIComponent(searchQuery.value)}&page=${searchPage.value}`,
        { headers: options.authHeaders() },
      )
      const rawPosts = options.extractPostArray(res)
      const newPosts = options.filterCommunityPosts(rawPosts)
      searchResults.value = reset ? newPosts : options.mergeCommunityPosts(searchResults.value, newPosts)
      searchHasMore.value = options.responseHasMore(res, rawPosts)
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { options.handleSessionExpired(); return }
      options.showToast('Không thể tìm bài viết', 'error')
    } finally {
      searchLoading.value = false
    }
  }

  function runSearch() {
    const q = searchInput.value.trim()
    if (q.length < 2) { options.showToast('Nhập ít nhất 2 ký tự để tìm kiếm', 'info'); return }
    searchQuery.value = q
    options.syncSearchQuery(q)
    fetchSearchUsers(q)
    fetchSearch(true)
  }

  function clearSearch() {
    searchInput.value = ''
    searchQuery.value = ''
    searchResults.value = []
    searchUsers.value = []
    options.syncSearchQuery('')
  }

  function applyRouteSearchQuery(rawQ?: unknown) {
    const source = rawQ !== undefined ? rawQ : options.getRouteQueryQ?.()
    const q = options.firstQueryValue(source).trim()
    if (q.length < 2) {
      if (searchQuery.value) {
        searchInput.value = ''
        searchQuery.value = ''
        searchResults.value = []
      }
      return
    }
    if (q === searchQuery.value) return
    searchInput.value = q
    searchQuery.value = q
    fetchSearch(true)
  }

  return {
    searchInput,
    searchQuery,
    searchResults,
    searchPage,
    searchHasMore,
    searchLoading,
    searchMode,
    searchUsers,
    fetchSearch,
    fetchSearchUsers,
    runSearch,
    clearSearch,
    applyRouteSearchQuery,
  }
}
