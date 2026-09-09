import { computed, type Ref, type ComputedRef } from 'vue'

export type ProfileView = Record<string, any> & {
  id?: string; username?: string; display_name?: string; phone?: string; bio?: string
  avatar?: string | null; avatar_url?: string | null; cover_url?: string | null; created_at?: string
  post_count?: number; review_count?: number; follower_count?: number; following_count?: number
}

export function mapProfileView(u: Record<string, any>): ProfileView {
  const stats = u.stats || {}
  return {
    ...u,
    avatar: u.avatar_url ?? u.avatar ?? null,
    post_count: stats.posts ?? u.post_count ?? 0,
    review_count: stats.reviews ?? u.review_count ?? 0,
    follower_count: stats.followers ?? u.follower_count ?? 0,
    following_count: stats.following ?? u.following_count ?? 0,
  }
}

export interface UseUserProfilePresentationOptions {
  profile: ComputedRef<ProfileView | null> | Ref<ProfileView | null>
  isSelf: ComputedRef<boolean> | Ref<boolean>
}

export function useUserProfilePresentation(options: UseUserProfilePresentationOptions) {
  const { profile, isSelf } = options

  const profileHandle = computed(() => profile.value?.username ? `@${profile.value.username}` : '')
  const totalContributions = computed(() => (profile.value?.post_count || 0) + (profile.value?.review_count || 0))

  const activitySummary = computed(() => {
    if (totalContributions.value === 0) {
      return isSelf.value ? 'Bắt đầu chia sẻ trải nghiệm đầu tiên' : 'Thành viên mới, chưa có đóng góp công khai'
    }
    return `${totalContributions.value} đóng góp công khai`
  })

  const initial = computed(() => (profile.value?.display_name || profile.value?.phone || '?').charAt(0).toUpperCase())
  const joinDate = computed(() => formatDateVN(profile.value?.created_at))

  const profileCompletion = computed(() => {
    if (!profile.value) return 0
    const p = profile.value
    const checks = [p.display_name, p.avatar, p.bio, p.cover_url, (p.post_count || 0) > 0, (p.review_count || 0) > 0]
    return Math.round((checks.filter(Boolean).length / checks.length) * 100)
  })

  const displayName = computed(() => profile.value?.display_name || profile.value?.phone || 'Người dùng')
  const emptyHint = computed(() => {
    if (isSelf.value) return 'Chia sẻ trải nghiệm của bạn với cộng đồng.'
    return `Theo dõi ${displayName.value} để nhận cập nhật mới.`
  })

  return {
    profileHandle,
    totalContributions,
    activitySummary,
    initial,
    joinDate,
    profileCompletion,
    displayName,
    emptyHint,
  }
}
