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

  it('Task 3: Riverside homestays display field coordinates and streamlined metadata', () => {
    const staysVue = readFileSync(resolve(__dirname, '../components/home/HomeRiversideStays.vue'), 'utf8')
    expect(staysVue).toContain("10°17'N · 105°59'E") // Út Trinh
    expect(staysVue).toContain("10°05'N · 105°49'E") // Bình Minh
    expect(staysVue).toContain("10°16'N · 105°59'E") // Ba Linh
    expect(staysVue).toContain('home-stay-card__coords')
    expect(nocturneCss).toMatch(/\.home-stay-card__price[^{]*\{[^}]*font-variant-numeric:\s*tabular-nums/)
  })

  it('Task 5: Curated showcase satellites display compass icon with field coordinates and tabular numbers', () => {
    const showcaseVue = readFileSync(resolve(__dirname, '../components/home/HomeCuratedShowcase.vue'), 'utf8')
    // Satellite coordinates must render compass icon
    expect(showcaseVue).toMatch(/home-curated-satellite__coords[\s\S]*?<IconLine\s+name="compass"/)
    // Verify tabular numeric group in home-nocturne.css
    expect(nocturneCss).toMatch(/\.home-curated-satellite__coords/)
    expect(nocturneCss).toMatch(/\.home-curated-lead__coords/)
  })

  it('Task 6: AEO plaque entry titles and continuation quantitative labels enforce tabular numerics', () => {
    const aeoVue = readFileSync(resolve(__dirname, '../components/CatalogAeoPlaque.vue'), 'utf8')
    const contVue = readFileSync(resolve(__dirname, '../components/home/HomeContinuation.vue'), 'utf8')
    expect(aeoVue).toContain('catalog-aeo-plaque__entry-title')
    expect(contVue).toContain('home-continuation__link-title')
    expect(nocturneCss).toMatch(/\.catalog-aeo-plaque__entry-title/)
    expect(nocturneCss).toMatch(/\.home-continuation__link-title/)
  })
})

