import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'
import {
  useUserProfilePresentation,
  mapProfileView,
} from '../composables/useUserProfilePresentation'
import { useUserProfilePosts } from '../composables/useUserProfilePosts'

describe('Moc 167: User Profile Posts & Presentation Composables Architecture', () => {
  describe('useUserProfilePresentation', () => {
    it('maps raw profile user stats accurately via mapProfileView', () => {
      const rawUser = {
        id: 'u1',
        username: 'trietpham',
        display_name: 'Triết Phạm',
        avatar_url: 'https://example.com/avatar.jpg',
        stats: {
          posts: 12,
          reviews: 5,
          followers: 40,
          following: 10,
        },
      }
      const view = mapProfileView(rawUser)
      expect(view.avatar).toBe('https://example.com/avatar.jpg')
      expect(view.post_count).toBe(12)
      expect(view.review_count).toBe(5)
      expect(view.follower_count).toBe(40)
      expect(view.following_count).toBe(10)
    })

    it('computes initial, profileHandle and activitySummary correctly', () => {
      const profile = ref<any>({
        username: 'vinhlong_explorer',
        display_name: 'Nguyễn Văn A',
        post_count: 3,
        review_count: 2,
        created_at: '2025-01-01T00:00:00Z',
      })
      const isSelf = ref(false)

      const presentation = useUserProfilePresentation({ profile, isSelf })

      expect(presentation.initial.value).toBe('N')
      expect(presentation.profileHandle.value).toBe('@vinhlong_explorer')
      expect(presentation.totalContributions.value).toBe(5)
      expect(presentation.activitySummary.value).toBe('5 đóng góp công khai')
      expect(presentation.displayName.value).toBe('Nguyễn Văn A')
    })

    it('calculates profile completion percentage based on core profile fields', () => {
      const profile = ref<any>({
        display_name: 'Nguyễn Văn A',
        avatar: 'avatar.jpg',
        bio: 'Yêu Vĩnh Long',
        cover_url: 'cover.jpg',
        post_count: 1,
        review_count: 0,
      })
      const isSelf = ref(true)

      const presentation = useUserProfilePresentation({ profile, isSelf })

      // 5 out of 6 fields completed: 5/6 * 100 = 83%
      expect(presentation.profileCompletion.value).toBe(83)
    })
  })

  describe('useUserProfilePosts', () => {
    it('filters posts based on active profile tab (posts vs reviews)', () => {
      const profile = ref<any>({ id: 'u1', is_private: false })
      const encodedProfileId = ref('u1')
      const tab = ref('posts')
      const authHeaders = () => ({})
      const handleSessionExpired = vi.fn()
      const showToast = vi.fn()
      const filterCommunityPosts = (p: any[]) => p

      const { posts, filteredPosts } = useUserProfilePosts({
        profile,
        encodedProfileId,
        tab,
        authHeaders,
        handleSessionExpired,
        showToast,
        filterCommunityPosts,
      })

      posts.value = [
        { id: 'p1', post_type: 'post', content: 'Bài viết 1' },
        { id: 'p2', post_type: 'review', content: 'Đánh giá 1' },
        { id: 'p3', post_type: 'post', content: 'Bài viết 2' },
      ]

      expect(filteredPosts.value).toHaveLength(3)

      tab.value = 'reviews'
      expect(filteredPosts.value).toHaveLength(1)
      expect(filteredPosts.value[0]?.id).toBe('p2')
    })
  })
})
