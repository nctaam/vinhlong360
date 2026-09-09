import { ref, computed, type Ref, type ComputedRef } from 'vue'
import { getStatusCode } from '~/composables/useFetchError'
import { usePostActions } from '~/composables/usePostActions'

export interface UseUserProfilePostsOptions {
  profile: ComputedRef<any> | Ref<any>
  encodedProfileId: ComputedRef<string> | Ref<string>
  tab: Ref<string>
  authHeaders: () => Record<string, string>
  handleSessionExpired: () => void
  showToast: (msg: string, type: 'success' | 'warning' | 'error' | 'info') => void
  filterCommunityPosts: (posts: any[]) => any[]
}

export function useUserProfilePosts(options: UseUserProfilePostsOptions) {
  const {
    profile,
    encodedProfileId,
    tab,
    authHeaders,
    handleSessionExpired,
    showToast,
    filterCommunityPosts,
  } = options

  const posts = ref<any[]>([])
  const loading = ref(true)
  const postsFetchFailed = ref(false)

  const filteredPosts = computed(() => {
    if (tab.value === 'reviews') return posts.value.filter(p => p.post_type === 'review')
    return posts.value
  })

  async function fetchPosts() {
    if (!profile.value || profile.value.is_private) {
      posts.value = []
      loading.value = false
      return
    }
    loading.value = true
    postsFetchFailed.value = false
    try {
      const res = await $fetch<Record<string, unknown>>(`/api/users/${encodedProfileId.value}/posts?limit=50`, { headers: authHeaders() })
      const list = res?.posts
      posts.value = Array.isArray(list) ? filterCommunityPosts(list as any[]) : []
    } catch (e: unknown) {
      postsFetchFailed.value = true
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể tải bài viết', 'error')
    } finally {
      loading.value = false
    }
  }

  const { toggleLike: _like, toggleBookmark: _bookmark, deletePost: _delete } = usePostActions()

  function toggleLike(pid: string) {
    const p = posts.value.find(x => x.id === pid)
    if (p) _like(pid, p)
  }

  function toggleBookmark(pid: string) {
    const p = posts.value.find(x => x.id === pid)
    if (p) _bookmark(pid, p)
  }

  function deletePost(pid: string) {
    _delete(pid, () => { posts.value = posts.value.filter(x => x.id !== pid) })
  }

  return {
    posts,
    loading,
    postsFetchFailed,
    filteredPosts,
    fetchPosts,
    toggleLike,
    toggleBookmark,
    deletePost,
  }
}
