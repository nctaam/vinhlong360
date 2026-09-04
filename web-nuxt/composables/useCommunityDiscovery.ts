import { computed, ref } from 'vue'
import { getStatusCode } from '~/composables/useFetchError'

export function useCommunityDiscovery(options: {
  openAuth: () => void
}) {
  const { user, isLoggedIn, authHeaders, handleSessionExpired } = useAuth()
  const { show: showToast } = useToast()

  const communityStats = ref<{ posts: number; reviews: number; members: number } | null>(null)
  const feedStats = computed(() => ({
    postCount: communityStats.value?.posts ?? '—',
    reviewCount: communityStats.value?.reviews ?? '—',
  }))

  async function loadCommunityStats() {
    try {
      communityStats.value = await $fetch<{ posts: number; reviews: number; members: number }>('/api/community/stats')
    } catch { /* giữ '—' */ }
  }

  const trendingTags = ref<{ tag: string; count: number }[]>([])
  async function loadTrendingTags() {
    try {
      const res = await $fetch<{ tags: { tag: string; count: number }[] }>('/api/community/trending-tags')
      trendingTags.value = res.tags || []
    } catch { /* ẩn card nếu lỗi */ }
  }

  const topMembers = ref<{ id: string; display_name: string; points: number; username?: string }[]>([])
  async function loadLeaderboard() {
    try {
      const res = await $fetch<{ leaders: any[] }>('/api/community/leaderboard?limit=5')
      topMembers.value = res.leaders || []
    } catch { /* ẩn card nếu lỗi */ }
  }

  const suggestedUsers = ref<any[]>([])
  function normalizeSuggestedUsers(users: any[]) {
    const seen = new Set<string>()
    const selfId = String(user.value?.id || '')
    return users.filter((item) => {
      const id = String(item?.id || '')
      if (!id || id === selfId || seen.has(id) || item.is_following || item._following) return false
      seen.add(id)
      return true
    })
  }

  async function loadSuggested() {
    if (!isLoggedIn.value) { suggestedUsers.value = []; return }
    try {
      const res = await $fetch<{ users: any[] }>('/api/community/suggested-follows?limit=5', { headers: authHeaders() })
      suggestedUsers.value = normalizeSuggestedUsers(res.users || [])
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) handleSessionExpired()
    }
  }

  async function followSuggested(s: any) {
    if (!isLoggedIn.value) { options.openAuth(); return }
    if (s._following) return
    s._following = true
    try {
      await $fetch(`/api/follow/user/${s.id}`, { method: 'POST', headers: authHeaders() })
      suggestedUsers.value = suggestedUsers.value.filter(item => item.id !== s.id)
      showToast(`Đã theo dõi ${s.display_name}`, 'success')
    } catch (e: unknown) {
      s._following = false
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể theo dõi', 'error')
    }
  }

  return {
    communityStats,
    feedStats,
    loadCommunityStats,
    trendingTags,
    loadTrendingTags,
    topMembers,
    loadLeaderboard,
    suggestedUsers,
    loadSuggested,
    followSuggested,
  }
}
