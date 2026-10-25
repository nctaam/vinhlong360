import { ref, computed, getCurrentInstance, getCurrentScope, onScopeDispose, type Ref } from 'vue'
import { getStatusCode } from '~/composables/useFetchError'

export const LEVEL_THRESHOLDS = [0, 20, 80, 200]

const ACHIEVEMENT_CATEGORY_ORDER: ReadonlyArray<readonly [string, string]> = Object.freeze([
  ['content', 'Nội dung'],
  ['explorer', 'Khám phá'],
  ['social', 'Cộng đồng'],
  ['veteran', 'Kỳ cựu'],
  ['special', 'Đặc biệt'],
])

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
    case 'post': return 'pencil'
    case 'review': return 'star'
    case 'follow': return 'users'
    default: return 'pin'
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

  let activityEpoch = 0
  let timelineAbort: AbortController | null = null
  let heatmapAbort: AbortController | null = null
  let achievementsAbort: AbortController | null = null

  function abortInflight() {
    timelineAbort?.abort()
    timelineAbort = null
    heatmapAbort?.abort()
    heatmapAbort = null
    achievementsAbort?.abort()
    achievementsAbort = null
  }

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
    const epoch = activityEpoch
    const targetProfileId = encodedProfileId.value
    timelineAbort?.abort()
    const ctrl = new AbortController()
    timelineAbort = ctrl
    timelineLoading.value = true
    try {
      const res = await $fetch<{ items: typeof timelineItems.value; has_more: boolean }>(
        `/api/users/${targetProfileId}/timeline`,
        {
          params: { page: timelinePage.value, limit: 20 },
          headers: authHeaders(),
          signal: ctrl.signal,
        },
      )
      if (ctrl.signal.aborted || epoch !== activityEpoch || encodedProfileId.value !== targetProfileId) return
      timelineItems.value.push(...(res.items || []))
      timelineHasMore.value = res.has_more
      timelinePage.value++
    } catch {
      /* im lặng bỏ qua — timeline chỉ là bổ sung */
    } finally {
      if (timelineAbort === ctrl) {
        timelineAbort = null
        timelineLoading.value = false
      }
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
    const epoch = activityEpoch
    const targetProfileId = encodedProfileId.value
    heatmapAbort?.abort()
    const ctrl = new AbortController()
    heatmapAbort = ctrl
    try {
      const res = await $fetch<{ days: HeatDay[]; total: number; max: number }>(
        `/api/users/${targetProfileId}/activity-heatmap`,
        { headers: authHeaders(), signal: ctrl.signal },
      )
      if (ctrl.signal.aborted || epoch !== activityEpoch || encodedProfileId.value !== targetProfileId) return
      heatmap.value = res.days || []
      heatmapMax.value = res.max || 0
      heatmapTotal.value = res.total || 0
    } catch {
      /* im lặng — heatmap chỉ là bổ sung */
    } finally {
      if (heatmapAbort === ctrl) heatmapAbort = null
    }
  }

  const heatmapWeeks = computed(() => {
    const byDate = new Map<string, number>()
    for (const day of heatmap.value) byDate.set(day.date, day.count)
    const cells: Array<{ date: string; count: number; level: number }> = []
    const today = new Date()
    const cursor = new Date(today)
    cursor.setDate(today.getDate() - 364)
    cursor.setDate(cursor.getDate() - cursor.getDay())
    const todayTime = today.getTime()
    const mx = heatmapMax.value || 1
    for (let i = 0; i < 53 * 7; i++) {
      if (i > 0) cursor.setDate(cursor.getDate() + 1)
      const iso = cursor.toISOString().slice(0, 10)
      const count = byDate.get(iso) || 0
      const level = count === 0 ? 0 : Math.min(4, Math.ceil(count / mx * 4))
      cells.push({ date: iso, count, level })
      if (cursor.getTime() > todayTime) break
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
    const epoch = activityEpoch
    achievementsAbort?.abort()
    const ctrl = new AbortController()
    achievementsAbort = ctrl
    try {
      const res = await $fetch<{ achievements: Achievement[]; earned_count: number }>(
        '/api/me/achievements',
        { headers: authHeaders(), signal: ctrl.signal },
      )
      if (ctrl.signal.aborted || epoch !== activityEpoch) return
      achievements.value = res.achievements || []
      achievementsEarned.value = res.earned_count || 0
    } catch (e: unknown) {
      if (ctrl.signal.aborted) return
      if (getStatusCode(e) === 401) { handleSessionExpired(); return }
      /* im lặng — showcase là bổ sung */
    } finally {
      if (achievementsAbort === ctrl) achievementsAbort = null
    }
  }

  const achievementCategories = computed(() => {
    if (!achievements.value.length) return []
    const grouped = new Map<string, Achievement[]>()
    for (const item of achievements.value) {
      const list = grouped.get(item.category)
      if (list) list.push(item)
      else grouped.set(item.category, [item])
    }
    const result: Array<{ key: string; label: string; items: Achievement[] }> = []
    for (const [key, label] of ACHIEVEMENT_CATEGORY_ORDER) {
      const items = grouped.get(key)
      if (items?.length) result.push({ key, label, items })
    }
    return result
  })

  function resetActivity() {
    activityEpoch += 1
    abortInflight()
    timelineItems.value = []
    timelineLoading.value = false
    timelinePage.value = 1
    timelineHasMore.value = true
    heatmap.value = []
    heatmapMax.value = 0
    heatmapTotal.value = 0
    achievements.value = []
    achievementsEarned.value = 0
  }

  if (getCurrentScope()) {
    onScopeDispose(() => abortInflight())
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
