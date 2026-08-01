import { describe, expect, it } from 'vitest'
import { createHomeNocturnePresentation } from '../utils/homeNocturnePresentation'

const event = (id: string, name: string, daysUntil: number) => ({
  id,
  name,
  days_until: daysUntil,
  attributes: { date_start: '2026-08-02' },
})

describe('homepage Nocturne presentation adapter', () => {
  it('builds deterministic data-backed decisions and omits unavailable filler', () => {
    const result = createHomeNocturnePresentation({
      currentMonth: 8,
      heroId: 'hero-1',
      spotlightId: 'spot-1',
      upcomingEvents: [event('event-1', 'Lễ hội sông nước', 2)],
      seasonal: [{ id: 'season-1', name: 'Chôm chôm Bình Hòa Phước' }],
      topDishes: [],
      itineraries: [],
      categoryCounts: { experiences: 4, dishes: 0, products: 3, events: 1, areas: 3 },
    })

    expect(result.decisionEntries.map(entry => entry.tone)).toEqual(['event', 'season'])
    expect(result.decisionEntries.map(entry => entry.title)).toEqual([
      'Có lịch gần nhất',
      'Đang vào mùa',
    ])
    expect(result.decisionEntries.every(entry => entry.id && entry.to && entry.text)).toBe(true)
    expect(result.decisionEntries.some(entry => entry.tone === 'map')).toBe(false)
  })

  it('de-duplicates hero, spotlight, decisions, and immediately following lists', () => {
    const result = createHomeNocturnePresentation({
      currentMonth: 8,
      heroId: 'shared-hero',
      spotlightId: 'shared-spotlight',
      upcomingEvents: [
        event('shared-hero', 'Không lặp hero', 0),
        event('event-1', 'Sự kiện quyết định', 1),
        event('event-2', 'Sự kiện còn lại', 4),
      ],
      seasonal: [
        { id: 'shared-spotlight', name: 'Không lặp spotlight' },
        { id: 'season-1', name: 'Mùa quyết định' },
        { id: 'season-2', name: 'Mùa còn lại' },
      ],
      topDishes: [
        { id: 'dish-1', name: 'Món quyết định', attributes: { rating: 4.8 } },
        { id: 'dish-2', name: 'Món còn lại', attributes: { rating: 4.6 } },
      ],
      itineraries: [{ id: 'plan-1', title: 'Một ngày ven sông' }],
      categoryCounts: {},
    })

    expect(result.decisionEntries.map(entry => entry.tone)).toEqual(['event', 'season', 'food', 'planner'])
    expect(result.upcomingEventEntries.map(item => item.id)).toEqual(['event-2'])
    expect(result.seasonalEntries.map(item => item.id)).toEqual(['season-2'])
    expect(result.dishEntries.map(item => item.id)).toEqual(['dish-2'])
  })

  it('preserves every current category route exactly once in primary and utility groups', () => {
    const result = createHomeNocturnePresentation({
      currentMonth: 8,
      upcomingEvents: [],
      seasonal: [],
      topDishes: [],
      itineraries: [],
      categoryCounts: { experiences: 5, dishes: 2, products: 4, events: 1, areas: 3 },
    })
    const links = [...result.categoryGroups.primary, ...result.categoryGroups.utility]

    expect(links.map(link => link.to)).toEqual([
      '/du-lich',
      '/kham-pha/am-thuc',
      '/ocop',
      '/le-hoi',
      '/luu-tru',
      '/lich-trinh',
      '/ban-do',
    ])
    expect(new Set(links.map(link => link.to)).size).toBe(links.length)
    expect(links.map(link => link.accent)).toEqual([
      'leaf',
      'amber',
      'clay',
      'amber',
      'river',
      'river',
      'river',
    ])
    expect(links.find(link => link.key === 'du-lich')?.countLabel).toBe('5 gợi ý')
    expect(links.find(link => link.key === 'luu-tru')?.countLabel).toBeUndefined()
  })
})
