import { entityPath } from '~/utils/routePaths'

export type HomeDecisionTone = 'event' | 'season' | 'planner' | 'food' | 'map'

export type HomeDecisionEntry = {
  id: string
  eyebrow: string
  title: string
  text: string
  to: string
  tone: HomeDecisionTone
}

export type HomeCategoryLink = {
  key: string
  label: string
  hint: string
  to: string
  icon: string
  accent: string
  countLabel?: string
}

export type HomeCategoryGroups = {
  primary: readonly HomeCategoryLink[]
  utility: readonly HomeCategoryLink[]
}

export type HomePresentationEntity = {
  id: string | number
  name?: string | null
  title?: string | null
  days_until?: number | null
  attributes?: {
    rating?: number | string | null
    review_count?: number | null
    date_start?: string | null
    [key: string]: unknown
  }
  [key: string]: unknown
}

type HomeCategoryCountKey = 'experiences' | 'dishes' | 'products' | 'events' | 'areas'

export type HomeNocturnePresentationInput = {
  currentMonth: number
  heroId?: string | number | null
  spotlightId?: string | number | null
  upcomingEvents: readonly HomePresentationEntity[]
  seasonal: readonly HomePresentationEntity[]
  topDishes: readonly HomePresentationEntity[]
  itineraries: readonly HomePresentationEntity[]
  categoryCounts: Partial<Record<HomeCategoryCountKey, number>>
}

export type HomeNocturnePresentation = {
  decisionEntries: readonly HomeDecisionEntry[]
  categoryGroups: HomeCategoryGroups
  upcomingEventEntries: readonly HomePresentationEntity[]
  seasonalEntries: readonly HomePresentationEntity[]
  dishEntries: readonly HomePresentationEntity[]
}

type CategoryDefinition = Omit<HomeCategoryLink, 'countLabel'> & {
  group: 'primary' | 'utility'
  countKey?: HomeCategoryCountKey
}

const CATEGORY_DEFINITIONS: readonly CategoryDefinition[] = [
  { group: 'primary', icon: 'leaf', label: 'Du lịch', hint: 'Vườn, sông, làng nghề', to: '/du-lich', accent: 'leaf', countKey: 'experiences', key: 'du-lich' },
  { group: 'primary', icon: 'bowl', label: 'Ẩm thực', hint: 'Quán ngon, món bản địa', to: '/kham-pha/am-thuc', accent: 'amber', countKey: 'dishes', key: 'am-thuc' },
  { group: 'primary', icon: 'gift', label: 'OCOP', hint: 'Đặc sản làm quà', to: '/ocop', accent: 'clay', countKey: 'products', key: 'ocop' },
  { group: 'primary', icon: 'lantern', label: 'Lễ hội', hint: 'Lịch và văn hóa địa phương', to: '/le-hoi', accent: 'river', countKey: 'events', key: 'le-hoi' },
  { group: 'utility', icon: 'home', label: 'Lưu trú', hint: 'Nghỉ lại theo khu vực', to: '/luu-tru', accent: 'leaf', key: 'luu-tru' },
  { group: 'utility', icon: 'compass', label: 'Lịch trình', hint: 'Gợi ý sẵn 1–3 ngày', to: '/lich-trinh', accent: 'amber', key: 'lich-trinh' },
  { group: 'utility', icon: 'map', label: 'Bản đồ', hint: 'Lọc theo vùng', to: '/ban-do', accent: 'river', countKey: 'areas', key: 'ban-do' },
]

function entityId(entity: HomePresentationEntity | null | undefined): string {
  return String(entity?.id ?? '').trim()
}

function entityLabel(entity: HomePresentationEntity | null | undefined): string {
  return String(entity?.name || entity?.title || '').trim()
}

function firstAvailable(
  entities: readonly HomePresentationEntity[],
  consumed: ReadonlySet<string>,
): HomePresentationEntity | undefined {
  return entities.find(entity => entityId(entity) && entityLabel(entity) && !consumed.has(entityId(entity)))
}

function eventEyebrow(entity: HomePresentationEntity): string {
  if (entity.days_until === 0) return 'Hôm nay'
  if (entity.days_until === 1) return 'Ngày mai'
  if (typeof entity.days_until === 'number') return `Còn ${entity.days_until} ngày`
  return 'Sắp diễn ra'
}

function foodEyebrow(entity: HomePresentationEntity): string {
  const rating = Number(entity.attributes?.rating)
  return Number.isFinite(rating) && rating > 0 ? `${rating.toFixed(1)} điểm` : 'Ẩm thực'
}

function categoryCountLabel(key: HomeCategoryCountKey | undefined, count: number | undefined): string | undefined {
  if (!key || !count || count < 1) return undefined
  if (key === 'dishes') return `${count} nổi bật`
  if (key === 'events') return `${count} sắp tới`
  if (key === 'areas') return `${count} vùng`
  return `${count} gợi ý`
}

export function createHomeNocturnePresentation(
  input: HomeNocturnePresentationInput,
): HomeNocturnePresentation {
  const month = Math.min(12, Math.max(1, Math.trunc(input.currentMonth)))
  const consumed = new Set(
    [input.heroId, input.spotlightId]
      .map(value => String(value ?? '').trim())
      .filter(Boolean),
  )
  const decisionEntries: HomeDecisionEntry[] = []

  const addDecision = (
    entity: HomePresentationEntity | undefined,
    entry: (entity: HomePresentationEntity) => Omit<HomeDecisionEntry, 'id'>,
  ) => {
    if (!entity || decisionEntries.length >= 4) return
    const id = entityId(entity)
    if (!id || consumed.has(id)) return
    consumed.add(id)
    decisionEntries.push({ id, ...entry(entity) })
  }

  addDecision(firstAvailable(input.upcomingEvents, consumed), entity => ({
    eyebrow: eventEyebrow(entity),
    title: 'Có lịch gần nhất',
    text: entityLabel(entity),
    to: entityPath(entity.id),
    tone: 'event',
  }))
  addDecision(firstAvailable(input.seasonal, consumed), entity => ({
    eyebrow: `Tháng ${month}`,
    title: 'Đang vào mùa',
    text: entityLabel(entity),
    to: `/theo-mua?mua=${encodeURIComponent(String(month))}`,
    tone: 'season',
  }))
  addDecision(firstAvailable(input.topDishes, consumed), entity => ({
    eyebrow: foodEyebrow(entity),
    title: 'Ăn gì hôm nay',
    text: entityLabel(entity),
    to: '/kham-pha/am-thuc?sort=rating',
    tone: 'food',
  }))
  addDecision(firstAvailable(input.itineraries, consumed), entity => ({
    eyebrow: 'Lịch trình gợi ý',
    title: 'Đi theo lộ trình có sẵn',
    text: entityLabel(entity),
    to: '/lich-trinh',
    tone: 'planner',
  }))

  const remaining = (entities: readonly HomePresentationEntity[]) =>
    entities.filter(entity => entityId(entity) && !consumed.has(entityId(entity)))

  const groups: { primary: HomeCategoryLink[]; utility: HomeCategoryLink[] } = {
    primary: [],
    utility: [],
  }
  for (const definition of CATEGORY_DEFINITIONS) {
    const { group, countKey, ...link } = definition
    const countLabel = categoryCountLabel(countKey, countKey ? input.categoryCounts[countKey] : undefined)
    groups[group].push(countLabel ? { ...link, countLabel } : link)
  }

  return {
    decisionEntries,
    categoryGroups: groups,
    upcomingEventEntries: remaining(input.upcomingEvents).slice(0, 3),
    seasonalEntries: remaining(input.seasonal),
    dishEntries: remaining(input.topDishes),
  }
}
