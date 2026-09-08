import { ref, computed, watch, type Ref } from 'vue'
import type { Post } from '~/types'

export interface CommunityAlmanacOptions {
  posts: Ref<Post[]>
  activeTab: Ref<string>
  searchMode: Ref<boolean>
}

export function useCommunityAlmanac(options: CommunityAlmanacOptions) {
  const { posts, activeTab, searchMode } = options

  // ── Sổ tay hôm nay — masthead sống động (thuần trình bày lại dữ liệu đã có, không API mới) ──
  const todayLabel = computed(() =>
    new Date().toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'long' }),
  )

  // Bài mới nhất trong feed 'latest' — nguồn cho cả H1 động và tín hiệu "vừa có bài mới".
  const latestPost = computed(() => posts.value[0])

  const almanacHeadline = computed(() => {
    const p = latestPost.value
    if (p?.entity_name) return `Hôm nay, ai đó vừa kể chuyện về ${p.entity_name}.`
    if (p?.display_name) return `Hôm nay, ${p.display_name} vừa kể một chuyện mới.`
    return 'Chuyện kể mỗi ngày của người miền sông nước.'
  })

  // "Vừa có bài mới" — chỉ tính bài đăng trong 10 phút gần nhất, không phải bài cũ tải lại.
  const hasFreshPost = computed(() => {
    const p = latestPost.value
    if (!p?.created_at) return false
    const ageMs = Date.now() - new Date(p.created_at).getTime()
    return ageMs >= 0 && ageMs < 10 * 60 * 1000
  })

  // Vệt phù sa "bài mới": xuất hiện khi bài đầu feed đổi SAU lần tải đầu tiên của phiên
  const sessionFirstPostId = ref<string | null>(null)
  const newestSeenPostId = ref<string | null>(null)
  const newPostHintDismissed = ref(false)

  watch(() => posts.value[0]?.id, (id) => {
    if (!id) return
    if (sessionFirstPostId.value === null) {
      sessionFirstPostId.value = id
      newestSeenPostId.value = id
      return
    }
    if (id !== newestSeenPostId.value) {
      newestSeenPostId.value = id
      newPostHintDismissed.value = false
    }
  })

  const showNewPostHint = computed(() =>
    activeTab.value === 'latest' && !searchMode.value &&
    !newPostHintDismissed.value &&
    !!newestSeenPostId.value && newestSeenPostId.value !== sessionFirstPostId.value,
  )

  function scrollToNewest() {
    newPostHintDismissed.value = true
    if (typeof window === 'undefined') return
    const prefersReduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    window.scrollTo({ top: 0, behavior: prefersReduced ? 'auto' : 'smooth' })
  }

  // "Nhắc tới gần đây" — địa danh được nhắc nhiều nhất trong feed đã tải (client-side tally)
  const recentMentions = computed(() => {
    const tally = new Map<string, { entity_id: string; entity_name: string; count: number }>()
    for (const p of posts.value) {
      if (!p.entity_id || !p.entity_name) continue
      const existing = tally.get(p.entity_id)
      if (existing) existing.count++
      else tally.set(p.entity_id, { entity_id: p.entity_id, entity_name: p.entity_name, count: 1 })
    }
    return [...tally.values()].sort((a, b) => b.count - a.count).slice(0, 4)
  })

  return {
    todayLabel,
    latestPost,
    almanacHeadline,
    hasFreshPost,
    showNewPostHint,
    scrollToNewest,
    recentMentions,
  }
}
