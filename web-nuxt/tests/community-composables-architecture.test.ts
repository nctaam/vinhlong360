import { describe, it, expect, vi } from 'vitest'
import { ref, computed } from 'vue'
import { useCommunityAlmanac } from '../composables/useCommunityAlmanac'
import { useCommunityFeedNavigation, type FeedTab, type PostTypeValue } from '../composables/useCommunityFeedNavigation'
import { useCommunityPostInteractions } from '../composables/useCommunityPostInteractions'
import type { Post } from '~/types'

describe('Moc 162: Community Modular Composables Architecture & Accessibility', () => {
  describe('useCommunityAlmanac', () => {
    it('computes dynamic headlines based on latest post metadata', () => {
      const posts = ref<Post[]>([])
      const activeTab = ref('latest')
      const searchMode = ref(false)

      const { almanacHeadline, hasFreshPost } = useCommunityAlmanac({
        posts,
        activeTab,
        searchMode,
      })

      expect(almanacHeadline.value).toBe('Chuyện kể mỗi ngày của người miền sông nước.')
      expect(hasFreshPost.value).toBe(false)

      // With entity_name
      posts.value = [
        {
          id: 'p1',
          entity_name: 'Cầu Mỹ Thuận 2',
          created_at: new Date().toISOString(),
          content: 'Test',
        } as Post,
      ]
      expect(almanacHeadline.value).toBe('Hôm nay, ai đó vừa kể chuyện về Cầu Mỹ Thuận 2.')
      expect(hasFreshPost.value).toBe(true)

      // With display_name only
      posts.value = [
        {
          id: 'p2',
          display_name: 'Bác Ba Sông Tiền',
          created_at: new Date(Date.now() - 3600 * 1000).toISOString(), // 1h ago
          content: 'Test 2',
        } as Post,
      ]
      expect(almanacHeadline.value).toBe('Hôm nay, Bác Ba Sông Tiền vừa kể một chuyện mới.')
      expect(hasFreshPost.value).toBe(false) // older than 10m
    })

    it('tallies recent mentions from loaded feed posts without extra API calls', () => {
      const posts = ref<Post[]>([
        { id: '1', entity_id: 'e1', entity_name: 'Chùa Tiên Châu' } as Post,
        { id: '2', entity_id: 'e2', entity_name: 'Văn Thánh Miếu' } as Post,
        { id: '3', entity_id: 'e1', entity_name: 'Chùa Tiên Châu' } as Post,
        { id: '4', entity_id: 'e1', entity_name: 'Chùa Tiên Châu' } as Post,
        { id: '5', entity_id: 'e3', entity_name: 'Cù Lao An Bình' } as Post,
      ])
      const activeTab = ref('latest')
      const searchMode = ref(false)

      const { recentMentions } = useCommunityAlmanac({ posts, activeTab, searchMode })

      expect(recentMentions.value).toHaveLength(3)
      expect(recentMentions.value[0]).toEqual({
        entity_id: 'e1',
        entity_name: 'Chùa Tiên Châu',
        count: 3,
      })
      expect(recentMentions.value[1].count).toBe(1)
    })
  })

  describe('useCommunityFeedNavigation', () => {
    it('manages accessible cyclic keyboard navigation for feed tabs', () => {
      const activeTab = ref<FeedTab>('latest')
      const filterType = ref<PostTypeValue>('')
      const visibleFeedTabs = computed(() => [
        { key: 'latest' as FeedTab, label: 'Mới nhất' },
        { key: 'trending' as FeedTab, label: 'Nổi bật' },
        { key: 'following' as FeedTab, label: 'Đang theo dõi' },
      ])
      const filterTypeOptions = computed(() => [
        { value: '' as PostTypeValue, label: 'Tất cả' },
        { value: 'share' as PostTypeValue, label: 'Chia sẻ' },
      ])

      const setTab = vi.fn((tab: FeedTab) => {
        activeTab.value = tab
      })
      const normalizeFeedTab = (v: unknown) => (['latest', 'trending', 'following'].includes(v as string) ? (v as FeedTab) : 'latest')
      const normalizeFilterType = (v: unknown) => (['', 'share'].includes(v as string) ? (v as PostTypeValue) : '')

      const nav = useCommunityFeedNavigation({
        activeTab,
        filterType,
        visibleFeedTabs,
        filterTypeOptions,
        setTab,
        normalizeFeedTab,
        normalizeFilterType,
      })

      const eventRight = {
        key: 'ArrowRight',
        preventDefault: vi.fn(),
      } as unknown as KeyboardEvent

      nav.onFeedTabKeydown(eventRight)
      expect(eventRight.preventDefault).toHaveBeenCalled()
      expect(setTab).toHaveBeenCalledWith('trending')

      const eventEnd = {
        key: 'End',
        preventDefault: vi.fn(),
      } as unknown as KeyboardEvent

      nav.onFeedTabKeydown(eventEnd)
      expect(setTab).toHaveBeenCalledWith('following')

      const eventHome = {
        key: 'Home',
        preventDefault: vi.fn(),
      } as unknown as KeyboardEvent

      nav.onFeedTabKeydown(eventHome)
      expect(setTab).toHaveBeenCalledWith('latest')
    })
  })

  describe('useCommunityPostInteractions', () => {
    it('locates all copies of a post across multiple reactive feeds', () => {
      const post1 = { id: 'post-1', content: 'hello' } as Post
      const post2 = { id: 'post-2', content: 'world' } as Post
      const posts = ref<Post[]>([post1, post2])
      const bookmarks = ref<Post[]>([post1])
      const searchResults = ref<Post[]>([post1])
      const sessionBookmarked = ref(false)

      const { _copies } = useCommunityPostInteractions({
        posts,
        bookmarks,
        searchResults,
        sessionBookmarked,
      })

      const copies = _copies('post-1')
      expect(copies).toHaveLength(3)
      expect(_copies('post-2')).toHaveLength(1)
      expect(_copies('non-existent')).toHaveLength(0)
    })
  })

  describe('useCommunityQuoteAndComposer', () => {
    it('manages quoting post state and cancelling', () => {
      const posts = ref<Post[]>([{ id: 'p1', content: 'Original content' } as Post])
      const isLoggedIn = ref(true)
      const openAuth = vi.fn()
      const authHeaders = vi.fn(() => ({}))
      const activeTab = ref('latest')
      const schedulePost = ref(false)
      const scheduledAt = ref('')
      const onMentionInput = vi.fn()
      const onMentionKeydownComposer = vi.fn(() => false)
      const submitPost = vi.fn()
      const closeMention = vi.fn()
      const mentionOpen = ref(false)
      const firstQueryValue = (v: unknown) => String(v || '')
      const route = { query: {}, hash: '' }

      const composer = useCommunityQuoteAndComposer({
        posts,
        isLoggedIn,
        openAuth,
        authHeaders,
        activeTab,
        schedulePost,
        scheduledAt,
        onMentionInput,
        onMentionKeydownComposer,
        submitPost,
        closeMention,
        mentionOpen,
        firstQueryValue,
        route,
      })

      expect(composer.quotingPost.value).toBeNull()
      composer.startQuote('p1')
      expect(composer.quotingPost.value).toEqual(posts.value[0])

      composer.cancelQuote()
      expect(composer.quotingPost.value).toBeNull()
    })
  })
})
