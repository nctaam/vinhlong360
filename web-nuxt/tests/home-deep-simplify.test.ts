import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Deep & Simple Homepage UI Refinements', () => {
  const indexVue = readFileSync(resolve(__dirname, '../pages/index.vue'), 'utf8')
  const nocturneCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')

  it('Task 1: Hero subtitle uses authentic poetic heritage phrasing without filler words', () => {
    expect(indexVue).toContain('Hành trình di sản cù lao, làng gốm trăm năm và vị ngọt cây trái giữa đôi bờ Cổ Chiên.')
    expect(indexVue).not.toContain('Tìm điểm đến, món ngon, lễ hội và lịch trình phù hợp cho chuyến về xứ cù lao Vĩnh Long hôm nay.')
    // Verify absence of banned voice words (R50.2)
    expect(indexVue).not.toMatch(/miền Tây|sông nước hữu tình|thiên đường|hidden gem|must-see|không thể bỏ lỡ|đắm chìm|hòa mình vào|điểm đến lý tưởng/)
  })

  it('Task 1: Hero terroir chips and cognitive chips enforce tabular-nums numeric styling', () => {
    expect(nocturneCss).toMatch(/font-variant-numeric:\s*tabular-nums/)
    expect(nocturneCss).toContain('.hero-terroir-chip')
  })

  it('Task 2: Culinary trail dishes display field coordinates and tabular prices', () => {
    const culinaryVue = readFileSync(resolve(__dirname, '../components/home/HomeCulinaryTrail.vue'), 'utf8')
    expect(culinaryVue).toContain('10°17\'N · 105°59\'E') // Cù lao An Bình
    expect(culinaryVue).toContain('10°07\'N · 106°11\'E') // Cù lao Dài
    expect(culinaryVue).toContain('home-culinary-card__coords')
    expect(culinaryVue).toContain('home-culinary-card__price-badge')
    expect(nocturneCss).toMatch(/\.home-culinary-card__price-badge[^{]*\{[^}]*font-variant-numeric:\s*tabular-nums/)
  })
})
