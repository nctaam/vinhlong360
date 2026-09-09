import { ref, computed, watch, nextTick, getCurrentInstance, type Ref } from 'vue'
import { getStatusCode } from '~/composables/useFetchError'
import type { ReportModalState } from '~/composables/useReport'

export interface UseUserProfileSocialOptions {
  profile: Ref<any>
  encodedProfileId: Ref<string>
  profileId: Ref<string>
  publicProfilePath: Ref<string>
  isSelf: Ref<boolean>
  isLoggedIn: Ref<boolean>
  authHeaders?: () => Record<string, string>
  handleSessionExpired?: () => void
  showToast?: (message: string, type?: 'info' | 'success' | 'warning' | 'error') => void
  confirmDialog?: (message: string, options?: { title?: string; confirmText?: string; danger?: boolean }) => Promise<boolean>
  openReport?: (type: ReportModalState['targetType'], id: string) => void
}

export function useUserProfileSocial(options: UseUserProfileSocialOptions) {
  const {
    profile,
    encodedProfileId,
    profileId,
    publicProfilePath,
    isSelf,
    isLoggedIn,
  } = options

  const authHeaders = options.authHeaders ?? (() => ({}))
  const handleSessionExpired = options.handleSessionExpired ?? (() => {})
  const showToast = options.showToast ?? (() => {})
  const confirmDialog = options.confirmDialog ?? (() => Promise.resolve(true))
  const openReport = options.openReport ?? (() => {})

  // ── Follow status ──
  const isFollowing = ref(false)
  const followLoading = ref(false)
  const followerCount = ref<number | null>(null)
  const displayFollowerCount = computed(() => followerCount.value ?? profile.value?.follower_count ?? 0)

  async function checkFollowing() {
    if (!isLoggedIn.value || !profile.value) return
    try {
      const res = await $fetch<{ following: boolean }>(
        `/api/follow/check/user/${encodedProfileId.value}`,
        { headers: authHeaders() },
      )
      isFollowing.value = res.following
    } catch {
      /* non-critical */
    }
  }

  async function toggleFollow() {
    if (!isLoggedIn.value) {
      showToast('Đăng nhập để theo dõi', 'info')
      return
    }
    if (!profile.value) return
    followLoading.value = true
    const was = isFollowing.value
    isFollowing.value = !was
    followerCount.value = Math.max(0, displayFollowerCount.value + (was ? -1 : 1))
    try {
      await $fetch(`/api/follow/user/${encodedProfileId.value}`, {
        method: 'POST',
        headers: authHeaders(),
      })
      followLists.value = { followers: null, following: null }
    } catch (e: unknown) {
      isFollowing.value = was
      followerCount.value = Math.max(0, displayFollowerCount.value + (was ? 1 : -1))
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể theo dõi', 'error')
    } finally {
      followLoading.value = false
    }
  }

  // ── Modal danh sách follower/following ──
  const followModalOpen = ref(false)
  const followModalTab = ref<'followers' | 'following'>('followers')
  const followLists = ref<{ followers: any[] | null; following: any[] | null }>({ followers: null, following: null })
  const followLoadingList = ref(false)
  const followModalList = computed(() => followLists.value[followModalTab.value] || [])
  const followDialogEl = ref<HTMLElement | null>(null)

  async function loadFollowList(which: 'followers' | 'following') {
    if (!profile.value) return
    if (followLists.value[which]) return
    followLoadingList.value = true
    try {
      const res = await $fetch<any>(`/api/users/${encodedProfileId.value}/${which}`, { headers: authHeaders() })
      followLists.value[which] = res.users || []
    } catch (e: unknown) {
      followLists.value[which] = []
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể tải danh sách', 'error')
    } finally {
      followLoadingList.value = false
    }
  }

  function closeFollowModal() {
    followModalOpen.value = false
  }

  if (getCurrentInstance()) {
    useModalA11y(followModalOpen, followDialogEl, { onClose: closeFollowModal })
  }

  function openFollowModal(tabTarget: 'followers' | 'following') {
    followModalTab.value = tabTarget
    followModalOpen.value = true
    loadFollowList(tabTarget)
  }

  watch(followModalTab, (t) => loadFollowList(t))

  function onFollowModalTabKeydown(event: KeyboardEvent) {
    const keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End']
    if (!keys.includes(event.key)) return
    event.preventDefault()
    const tabs: Array<'followers' | 'following'> = ['followers', 'following']
    const current = tabs.indexOf(followModalTab.value)
    const next = event.key === 'Home'
      ? tabs[0]
      : event.key === 'End'
        ? tabs[1]
        : tabs[(current + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length]
    followModalTab.value = next ?? 'followers'
    nextTick(() => document.getElementById(`fm-tab-${next}`)?.focus())
  }

  // ── Block / Report ──
  const isBlocked = ref(false)

  function syncViewerRelationship(p: any) {
    const relationship = p?.viewer_relationship || {}
    if (typeof relationship.is_following === 'boolean') isFollowing.value = relationship.is_following
    if (typeof relationship.is_blocked === 'boolean') isBlocked.value = relationship.is_blocked
    followerCount.value = null
  }

  async function checkBlocked() {
    if (!isLoggedIn.value || isSelf.value || !profile.value) return
    try {
      const res = await $fetch<{ blocked: any[] }>('/api/blocked-users', { headers: authHeaders() })
      isBlocked.value = (res.blocked || []).some(u => u.id === profileId.value)
    } catch {
      /* non-critical */
    }
  }

  async function toggleBlock() {
    if (!profile.value) return
    if (isBlocked.value) {
      try {
        await $fetch(`/api/block/${encodedProfileId.value}`, { method: 'POST', headers: authHeaders() })
        isBlocked.value = false
        showToast('Đã bỏ chặn', 'success')
      } catch (e: unknown) {
        if (getStatusCode(e) === 401) { handleSessionExpired(); return }
        showToast('Không thể bỏ chặn', 'error')
      }
      return
    }
    const ok = await confirmDialog(
      'Họ sẽ không thấy bài viết, bình luận và hoạt động của bạn. Bạn cũng sẽ không thấy nội dung của họ.',
      {
        title: `Chặn ${profile.value?.display_name || 'người dùng này'}?`,
        confirmText: 'Chặn',
        danger: true,
      },
    )
    if (!ok) return
    try {
      await $fetch(`/api/block/${encodedProfileId.value}`, { method: 'POST', headers: authHeaders() })
      isBlocked.value = true
      if (isFollowing.value) {
        isFollowing.value = false
        followerCount.value = Math.max(0, displayFollowerCount.value - 1)
      }
      showToast('Đã chặn người dùng', 'success')
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      showToast('Không thể chặn', 'error')
    }
  }

  // ── More menu & actions ──
  const showMoreMenu = ref(false)

  function onClickOutsideMore(e: MouseEvent) {
    const wrap = (e.target as HTMLElement)?.closest('.profile-more-wrap')
    if (!wrap) showMoreMenu.value = false
  }

  function reportUser() {
    if (!profile.value) return
    showMoreMenu.value = false
    openReport('user', profileId.value)
  }

  async function shareProfile() {
    if (typeof window === 'undefined') return
    const url = `${window.location.origin}${publicProfilePath.value}`
    const name = profile.value?.display_name || 'Người dùng'
    if (navigator.share) {
      try { await navigator.share({ title: `${name} — vinhlong360`, url }) } catch {}
    } else {
      try {
        await navigator.clipboard.writeText(url)
        showToast('Đã sao chép liên kết hồ sơ', 'success')
      } catch {
        showToast('Không thể sao chép', 'error')
      }
    }
  }

  function resetSocial() {
    isFollowing.value = false
    isBlocked.value = false
    followerCount.value = null
    followLists.value = { followers: null, following: null }
  }

  return {
    isFollowing,
    followLoading,
    followerCount,
    displayFollowerCount,
    checkFollowing,
    toggleFollow,
    followModalOpen,
    followModalTab,
    followLists,
    followLoadingList,
    followModalList,
    followDialogEl,
    loadFollowList,
    closeFollowModal,
    openFollowModal,
    onFollowModalTabKeydown,
    isBlocked,
    syncViewerRelationship,
    checkBlocked,
    toggleBlock,
    showMoreMenu,
    onClickOutsideMore,
    reportUser,
    shareProfile,
    resetSocial,
  }
}
