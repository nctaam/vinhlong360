import { ref, computed, getCurrentInstance, type Ref } from 'vue'
import { getStatusCode } from '~/composables/useFetchError'

export const LEVEL_THRESHOLDS = [0, 20, 80, 200]

export type HeatDay = { date: string; count: number }

export type Achievement = {
  id: string
  name: string
  description: string
  icon: string
  category: string
  current: number
  target: number
  earned: boolean
  unlocked_at: string | null
}

export function timelineIcon(type: string): string {
  switch (type) {
    case 'post': return '✍️'
    case 'review': return '⭐'
    case 'follow': return '👥'
    default: return '📌'
  }
}

export interface UseUserProfileActivityOptions {
  profile: Ref<any>
  encodedProfileId: Ref<string>
  isSelf: Ref<boolean>
  tab: Ref<string>
  authHeaders?: () => Record<string, string>
  handleSessionExpired?: () => void
}

export function useUserProfileActivity(options: UseUserProfileActivityOptions) {
  const { profile, encodedProfileId, isSelf, tab } = options
  const authHeaders = options.authHeaders ?? (() => ({}))
  const handleSessionExpired = options.handleSessionExpired ?? (() => {})

  // ── Reputation & Streaks ──
  const xpProgress = computed(() => {
    const pts = profile.value?.reputation?.points ?? 0
    const lvl = profile.value?.reputation?.level ?? 1
    if (lvl >= 4) return { pct: 100, toNext: 0, max: true }
    const lo = LEVEL_THRESHOLDS[lvl - 1] ?? 0
    const hi = LEVEL_THRESHOLDS[lvl] ?? 20
    const pct = Math.max(0, Math.min(100, Math.round((pts - lo) / (hi - lo) * 100)))
    return { pct, toNext: Math.max(0, hi - pts), max: false }
  })

  const isStreakMilestone = computed(() => {
    const days = profile.value?.login_streak ?? 0
    return days > 0 && days % 7 === 0
  })

  // ── Timeline ──
  const timelineItems = ref<Array<{ type: string; created_at: string; data: Record<string, any> }>>([])
  const timelineLoading = ref(false)
  const timelinePage = ref(1)
  const timelineHasMore = ref(true)

  async function loadTimeline() {
    if (timelineLoading.value || !timelineHasMore.value || !profile.value) return
    timelineLoading.value = true
    try {
      const res = await $fetch<{ items: typeof timelineItems.value; has_more: boolean }>(
        `/api/users/${encodedProfileId.value}/timeline`,
        {
          params: { page: timelinePage.value, limit: 20 },
          headers: authHeaders(),
        },
      )
      timelineItems.value.push(...(res.items || []))
      timelineHasMore.value = res.has_more
      timelinePage.value++
    } catch {
      /* im lặng bỏ qua — timeline chỉ là bổ sung */
    } finally {
      timelineLoading.value = false
    }
  }

  const { sentinel: timelineSentinel } = getCurrentInstance()
    ? useInfiniteScroll(loadTimeline, {
        enabled: computed(() => tab.value === 'timeline' && timelineHasMore.value),
      })
    : { sentinel: ref(null) }

  // ── Heatmap (GitHub-style 365 days) ──
  const heatmap = ref<HeatDay[]>([])
  const heatmapMax = ref(0)
  const heatmapTotal = ref(0)

  async function loadHeatmap() {
    if (!profile.value) return
    try {
      const res = await $fetch<{ days: HeatDay[]; total: number; max: number }>(
        `/api/users/${encodedProfileId.value}/activity-heatmap`,
        { headers: authHeaders() },
      )
      heatmap.value = res.days || []
      heatmapMax.value = res.max || 0
      heatmapTotal.value = res.total || 0
    } catch {
      /* im lặng — heatmap chỉ là bổ sung */
    }
  }

  const heatmapWeeks = computed(() => {
    const byDate = new Map(heatmap.value.map(d => [d.date, d.count]))
    const cells: Array<{ date: string; count: number; level: number }> = []
    const today = new Date()
    const start = new Date(today)
    start.setDate(today.getDate() - 364)
    start.setDate(start.getDate() - start.getDay())
    const mx = heatmapMax.value || 1
    for (let i = 0; i < 53 * 7; i++) {
      const d = new Date(start)
      d.setDate(start.getDate() + i)
      const iso = d.toISOString().slice(0, 10)
      const count = byDate.get(iso) || 0
      const level = count === 0 ? 0 : Math.min(4, Math.ceil(count / mx * 4))
      cells.push({ date: iso, count, level })
      if (d > today) break
    }
    const weeks: (typeof cells)[] = []
    for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7))
    return weeks
  })

  // ── Achievements ──
  const achievements = ref<Achievement[]>([])
  const achievementsEarned = ref(0)

  async function loadAchievements() {
    if (!isSelf.value) return
    try {
      const res = await $fetch<{ achievements: Achievement[]; earned_count: number }>(
        '/api/me/achievements',
        { headers: authHeaders() },
      )
      achievements.value = res.achievements || []
      achievementsEarned.value = res.earned_count || 0
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      /* im lặng — showcase là bổ sung */
    }
  }

  const achievementCategories = computed(() => {
    const order: Array<[string, string]> = [
      ['content', 'Nội dung'],
      ['explorer', 'Khám phá'],
      ['social', 'Cộng đồng'],
      ['veteran', 'Kỳ cựu'],
      ['special', 'Đặc biệt'],
    ]
    return order
      .map(([key, label]) => ({ key, label, items: achievements.value.filter(a => a.category === key) }))
      .filter(c => c.items.length)
  })

  function resetActivity() {
    timelineItems.value = []
    timelinePage.value = 1
    timelineHasMore.value = true
    heatmap.value = []
    heatmapMax.value = 0
    heatmapTotal.value = 0
  }

  return {
    xpProgress,
    isStreakMilestone,
    timelineItems,
    timelineLoading,
    timelinePage,
    timelineHasMore,
    timelineIcon,
    loadTimeline,
    timelineSentinel,
    heatmap,
    heatmapMax,
    heatmapTotal,
    loadHeatmap,
    heatmapWeeks,
    achievements,
    achievementsEarned,
    loadAchievements,
    achievementCategories,
    resetActivity,
  }
}
