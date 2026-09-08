import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'
import {
  useUserProfileActivity,
  LEVEL_THRESHOLDS,
  timelineIcon,
} from '../composables/useUserProfileActivity'
import { useUserProfileSocial } from '../composables/useUserProfileSocial'
import { useUserProfileCollections } from '../composables/useUserProfileCollections'

describe('Moc 164: User Profile Composables Architecture & State Hygiene', () => {
  describe('useUserProfileActivity', () => {
    it('defines standard reputation level thresholds [0, 20, 80, 200]', () => {
      expect(LEVEL_THRESHOLDS).toEqual([0, 20, 80, 200])
    })

    it('maps timeline item types to evocative visual icons', () => {
      expect(timelineIcon('post')).toBe('✍️')
      expect(timelineIcon('review')).toBe('⭐')
      expect(timelineIcon('follow')).toBe('👥')
      expect(timelineIcon('custom')).toBe('📌')
    })

    it('computes XP level progress and distance to next rank accurately', () => {
      const profile = ref<any>({ reputation: { level: 1, points: 10 } })
      const activity = useUserProfileActivity({
        profile,
        encodedProfileId: ref('u1'),
        isSelf: ref(false),
        tab: ref('posts'),
      })

      // Level 1: 0..20, 10 pts -> 50%, toNext 10
      expect(activity.xpProgress.value.pct).toBe(50)
      expect(activity.xpProgress.value.toNext).toBe(10)
      expect(activity.xpProgress.value.max).toBe(false)

      // Level 4: max rank reached
      profile.value = { reputation: { level: 4, points: 300 } }
      expect(activity.xpProgress.value.pct).toBe(100)
      expect(activity.xpProgress.value.toNext).toBe(0)
      expect(activity.xpProgress.value.max).toBe(true)
    })

    it('detects weekly streak milestones on multiples of 7', () => {
      const profile = ref<any>({ login_streak: 0 })
      const activity = useUserProfileActivity({
        profile,
        encodedProfileId: ref('u1'),
        isSelf: ref(false),
        tab: ref('posts'),
      })

      expect(activity.isStreakMilestone.value).toBe(false)

      profile.value = { login_streak: 6 }
      expect(activity.isStreakMilestone.value).toBe(false)

      profile.value = { login_streak: 7 }
      expect(activity.isStreakMilestone.value).toBe(true)

      profile.value = { login_streak: 14 }
      expect(activity.isStreakMilestone.value).toBe(true)

      profile.value = { login_streak: 15 }
      expect(activity.isStreakMilestone.value).toBe(false)
    })
  })

  describe('useUserProfileSocial', () => {
    it('synchronizes viewer relationship flags safely from profile payload', () => {
      const social = useUserProfileSocial({
        profile: ref({ id: 'target-1' }),
        encodedProfileId: ref('target-1'),
        profileId: ref('target-1'),
        publicProfilePath: ref('/nguoi-dung/target-1'),
        isSelf: ref(false),
        isLoggedIn: ref(true),
      })

      expect(social.isFollowing.value).toBe(false)
      expect(social.isBlocked.value).toBe(false)

      social.syncViewerRelationship({
        viewer_relationship: { is_following: true, is_blocked: false },
      })
      expect(social.isFollowing.value).toBe(true)
      expect(social.isBlocked.value).toBe(false)

      social.syncViewerRelationship({
        viewer_relationship: { is_following: false, is_blocked: true },
      })
      expect(social.isFollowing.value).toBe(false)
      expect(social.isBlocked.value).toBe(true)
    })

    it('resets social states when switching viewed profiles', () => {
      const social = useUserProfileSocial({
        profile: ref({ id: 'target-1' }),
        encodedProfileId: ref('target-1'),
        profileId: ref('target-1'),
        publicProfilePath: ref('/nguoi-dung/target-1'),
        isSelf: ref(false),
        isLoggedIn: ref(true),
      })

      social.isFollowing.value = true
      social.isBlocked.value = true
      social.followerCount.value = 42

      social.resetSocial()
      expect(social.isFollowing.value).toBe(false)
      expect(social.isBlocked.value).toBe(false)
      expect(social.followerCount.value).toBeNull()
      expect(social.followLists.value).toEqual({ followers: null, following: null })
    })
  })

  describe('useUserProfileCollections', () => {
    it('initializes collection creation modal in closed state with clean inputs', () => {
      const collections = useUserProfileCollections()
      expect(collections.showCreateCollection.value).toBe(false)
      expect(collections.newCollectionName.value).toBe('')
      expect(collections.newCollectionDesc.value).toBe('')
      expect(collections.creatingCollection.value).toBe(false)
    })
  })
})
