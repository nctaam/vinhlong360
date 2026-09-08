import { nextTick, type Ref, type ComputedRef } from 'vue'

export type FeedTab = 'latest' | 'trending' | 'following' | 'bookmarks'
export type PostTypeValue = '' | 'share' | 'review' | 'question' | 'recommend'

export const COMMUNITY_POST_TYPES = [
  { value: 'share', label: 'Chia sẻ', icon: 'camera' },
  { value: 'review', label: 'Đánh giá', icon: 'star' },
  { value: 'question', label: 'Hỏi đáp', icon: 'circle-help' },
  { value: 'recommend', label: 'Gợi ý', icon: 'thumbs-up' },
] as const

export const COMMUNITY_FEED_TABS: Array<{ key: FeedTab; label: string; requiresAuth?: boolean }> = [
  { key: 'latest', label: 'Mới nhất' },
  { key: 'trending', label: 'Nổi bật' },
  { key: 'following', label: 'Đang theo dõi', requiresAuth: true },
  { key: 'bookmarks', label: 'Đã lưu', requiresAuth: true },
]

export interface CommunityFeedNavigationOptions {
  activeTab: Ref<FeedTab>
  filterType: Ref<PostTypeValue>
  visibleFeedTabs: ComputedRef<Array<{ key: FeedTab; label: string; requiresAuth?: boolean }>>
  filterTypeOptions: ComputedRef<Array<{ value: PostTypeValue; label: string; icon?: string }>>
  setTab: (tab: FeedTab) => void
  normalizeFeedTab: (value: unknown) => FeedTab
  normalizeFilterType: (value: unknown) => PostTypeValue
}

export function useCommunityFeedNavigation(options: CommunityFeedNavigationOptions) {
  const {
    activeTab,
    filterType,
    visibleFeedTabs,
    filterTypeOptions,
    setTab,
    normalizeFeedTab,
    normalizeFilterType,
  } = options

  function focusFeedTab(tab: FeedTab) {
    if (typeof document === 'undefined') return
    nextTick(() => document.querySelector<HTMLElement>(`.threads-filter [data-tab="${tab}"]`)?.focus())
  }

  function focusTypeFilter(value: PostTypeValue) {
    if (typeof document === 'undefined') return
    const key = value || 'all'
    nextTick(() => document.querySelector<HTMLElement>(`.type-filter-row [data-type="${key}"]`)?.focus())
  }

  function nextIndex(current: number, total: number, key: string) {
    if (key === 'Home') return 0
    if (key === 'End') return total - 1
    if (key === 'ArrowRight' || key === 'ArrowDown') return (current + 1) % total
    if (key === 'ArrowLeft' || key === 'ArrowUp') return (current - 1 + total) % total
    return current
  }

  function onFeedTabKeydown(e: KeyboardEvent) {
    if (!['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) return
    const tabs = visibleFeedTabs.value.map(tab => tab.key)
    if (!tabs.length) return
    e.preventDefault()
    const current = Math.max(0, tabs.indexOf(normalizeFeedTab(activeTab.value)))
    const tab = tabs[nextIndex(current, tabs.length, e.key)] || 'latest'
    setTab(tab)
    focusFeedTab(tab)
  }

  function onTypeFilterKeydown(e: KeyboardEvent) {
    if (!['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key)) return
    const options = filterTypeOptions.value.map(option => option.value)
    e.preventDefault()
    const current = Math.max(0, options.indexOf(normalizeFilterType(filterType.value)))
    const value = options[nextIndex(current, options.length, e.key)] || ''
    setFilterType(value)
    focusTypeFilter(value)
  }

  function setFilterType(value: PostTypeValue) {
    filterType.value = normalizeFilterType(value)
  }

  return {
    focusFeedTab,
    focusTypeFilter,
    nextIndex,
    onFeedTabKeydown,
    onTypeFilterKeydown,
    setFilterType,
  }
}
