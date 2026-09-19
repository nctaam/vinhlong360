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

  it('Task 7: Curated satellite cards maintain unobtrusive scrim allowing >= 75% photographic focus', () => {
    const showcaseVue = readFileSync(resolve(__dirname, '../components/home/HomeCuratedShowcase.vue'), 'utf8')
    expect(showcaseVue).toContain('home-curated-satellite__title')
    expect(showcaseVue).toMatch(/home-curated-satellite__overlay[\s\S]*?padding:\s*var\(--space-4\)/)
  })

  it('Task 8: Hero Feature Dossier coordinates consistently render compass icon', () => {
    const dossierVue = readFileSync(resolve(__dirname, '../components/home/HomeFeatureDossier.vue'), 'utf8')
    expect(dossierVue).toMatch(/home-feature-dossier__coords[\s\S]*?<IconLine\s+name="compass"/)
  })

  it('Task 9: Hotline numbers, itinerary durations, and remaining coordinates enforce tabular numerics', () => {
    expect(nocturneCss).toMatch(/\.home-hotline-btn__num/)
    expect(nocturneCss).toMatch(/\.home-continuation__link-sub/)
    expect(nocturneCss).toMatch(/\.home-culinary-card__coords/)
    expect(nocturneCss).toMatch(/\.home-stay-card__coords/)
    // Verify orphaned product lead name is pruned from heading balance group
    expect(nocturneCss).not.toMatch(/:is\([^)]*\.home-product-lead__name[^)]*\)/)
  })

  it('Task 10: Culinary trail and riverside stays employ calmed photographic scrims', () => {
    const culinaryVue = readFileSync(resolve(__dirname, '../components/home/HomeCulinaryTrail.vue'), 'utf8')
    const staysVue = readFileSync(resolve(__dirname, '../components/home/HomeRiversideStays.vue'), 'utf8')

    // Both must use relaxed transparent mid-stop
    expect(culinaryVue).toMatch(/home-culinary-card__scrim[\s\S]*?transparent 28%/)
    expect(staysVue).toMatch(/home-stay-card__scrim[\s\S]*?transparent 28%/)
  })

  it('Task 11: Curated lead heritage card employs calmed optical photographic scrim', () => {
    const showcaseVue = readFileSync(resolve(__dirname, '../components/home/HomeCuratedShowcase.vue'), 'utf8')
    // Must use relaxed transparent mid-stop instead of heavy 0.55 opacity at 50%
    expect(showcaseVue).toMatch(/home-curated-lead__scrim[\s\S]*?transparent 28%/)
    expect(showcaseVue).not.toMatch(/rgba\(var\(--black-rgb\),\s*0\.55\)\s*50%/)
  })

  it('Task 12: Hero Feature Dossier action link consistently renders arrow-right icon', () => {
    const dossierVue = readFileSync(resolve(__dirname, '../components/home/HomeFeatureDossier.vue'), 'utf8')
    expect(dossierVue).toMatch(/home-feature-dossier__action[\s\S]*?Khám phá[\s\S]*?<IconLine\s+name="arrow-right"/)
  })

  it('Task 13: Orphaned product lead layout rules pruned from home-nocturne.css while preserving required tactile scale', () => {
    // Media active scale rule is required by home-layout-asymmetry.test.ts
    expect(nocturneCss).toMatch(/\.home-product-lead__media:active\s*\{[\s\S]*?transform:\s*scale\(0\.99\)/)
    // Orphaned matte and grid body rules should be pruned to maintain strict CSS headroom
    expect(nocturneCss).not.toMatch(/\[data-home-pilot="nocturne-b1"\]\s+\.home-product-lead__matte\s*\{/)
  })

  it('Task 14: Emergency hotline companion banner removed from homepage template to preserve visual calm', () => {
    const freshIndexVue = readFileSync(resolve(__dirname, '../pages/index.vue'), 'utf8')
    expect(freshIndexVue).not.toContain('<HomeTravelCompanion')
    expect(freshIndexVue).not.toContain('import HomeTravelCompanion')
  })

  it('Task 15: Hero Feature Dossier action buttons enforce unified border-radius control token', () => {
    const freshNocturneCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
    expect(freshNocturneCss).toMatch(/\.home-feature-dossier__action\s*\{[^}]*border-radius:\s*var\(--radius-control\);/)
  })

  it('Task 16: Catalog AEO Plaque CTA button enforces unified border-radius control token', () => {
    const aeoVue = readFileSync(resolve(__dirname, '../components/CatalogAeoPlaque.vue'), 'utf8')
    expect(aeoVue).toMatch(/\.catalog-aeo-plaque__cta\s*\{[^}]*border-radius:\s*var\(--radius-control\);/)
  })

  it('Task 17: Folio V Continuation waypoints structured as tactile cards with unified control radius and featured accent', () => {
    const freshNocturneCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
    expect(freshNocturneCss).toMatch(/\.home-continuation__links\s+a\s*\{[^}]*border-radius:\s*var\(--radius-control\);/)
    expect(freshNocturneCss).toMatch(/\.home-continuation__links\s+a\s*\{[^}]*background:\s*var\(--color-canvas\);/)
    expect(freshNocturneCss).toMatch(/\.home-continuation__link--featured\s*\{[^}]*border-left:\s*3px\s+solid\s+var\(--alluvial-gold/)
  })

  it('Task 18: Tabular numerics applied to itinerary stop numbers and schedule timings', () => {
    const freshNocturneCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
    expect(freshNocturneCss).toMatch(/\.home-planner-stop__number[\s\S]*?tabular-nums/)
    expect(freshNocturneCss).toMatch(/\.home-planner-stop__time[\s\S]*?tabular-nums/)
  })

  it('Task 19: Curated showcase and riverside stays action buttons consistently animate directional arrows on hover', () => {
    const showcaseVue = readFileSync(resolve(__dirname, '../components/home/HomeCuratedShowcase.vue'), 'utf8')
    const staysVue = readFileSync(resolve(__dirname, '../components/home/HomeRiversideStays.vue'), 'utf8')

    // Folio I Lead button and Satellite link arrows
    expect(showcaseVue).toMatch(/\.home-curated-lead__actions\s+\.btn:hover\s+\.line-icon:last-child\s*\{[^}]*transform:\s*translateX\(3px\)/)
    expect(showcaseVue).toMatch(/\.home-curated-satellite__link:hover\s+\.line-icon\s*\{[^}]*transform:\s*translateX\(3px\)/)

    // Folio III Stay card action button arrow
    expect(staysVue).toMatch(/\.home-stay-card__action\s+\.btn:hover\s+\.line-icon:last-child\s*\{[^}]*transform:\s*translateX\(3px\)/)
  })

  it('Task 20: Catalog AEO Plaque CTA button enforces tactile active press scale', () => {
    const aeoVue = readFileSync(resolve(__dirname, '../components/CatalogAeoPlaque.vue'), 'utf8')
    expect(aeoVue).toMatch(/\.catalog-aeo-plaque__cta:active\s*\{[^}]*transform:\s*scale\(0\.98\);/)
  })

  it('Task 21: Hero feature dossier action button animates directional arrow on hover', () => {
    const nocturneCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
    expect(nocturneCss).toMatch(/\[data-home-pilot="nocturne-b1"\]\s+\.home-feature-dossier__action:hover\s+\.home-feature-dossier__action-arrow\s*\{[^}]*transform:\s*translateX\(3px\);/)
  })

  it('Task 23: Section header counts enforce tabular-nums and cards support card-level hover directional arrow animation', () => {
    const nocturneCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
    const showcaseVue = readFileSync(resolve(__dirname, '../components/home/HomeCuratedShowcase.vue'), 'utf8')
    const culinaryVue = readFileSync(resolve(__dirname, '../components/home/HomeCulinaryTrail.vue'), 'utf8')
    const staysVue = readFileSync(resolve(__dirname, '../components/home/HomeRiversideStays.vue'), 'utf8')

    // Tabular numbers for section header links
    expect(nocturneCss).toMatch(/tabular-nums[\s\S]*?\.see-all|\.see-all[\s\S]*?tabular-nums/)

    // Card-level hover directional arrows
    expect(showcaseVue).toMatch(/\.home-curated-lead:hover\s+\.home-curated-lead__actions\s+\.btn\s+\.line-icon:last-child/)
    expect(culinaryVue).toMatch(/\.home-culinary-card:hover\s+\.home-culinary-card__arrow/)
    expect(staysVue).toMatch(/\.home-stay-card:hover\s+\.home-stay-card__action\s+\.btn\s+\.line-icon:last-child/)
  })

  it('Task 24: Hero section decluttered with elegant subtitle, refined cognitive chips, no hint, and iconic dossier image fallback', () => {
    const freshIndexVue = readFileSync(resolve(__dirname, '../pages/index.vue'), 'utf8')
    const freshNocturneCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')

    // 1. Redundant search hint removed
    expect(freshIndexVue).not.toContain('hero-search-island__hint')
    expect(freshIndexVue).not.toContain('Tìm cù lao, lò gạch cổ')
    expect(freshNocturneCss).not.toContain('.hero-search-island__hint')

    // 2. Hero subtitle has refined styling and dynamic computed fallback
    expect(freshIndexVue).toMatch(/heroSubtitle\s*=\s*computed/)
    expect(freshNocturneCss).toMatch(/\[data-home-pilot="nocturne-b1"\]\s+\.hero-sub\s*\{[^}]*border-radius:\s*var\(--radius-control/)

    // 3. Iconic entity image fallback enabled in heroFeatureDescriptor
    expect(freshIndexVue).toMatch(/describeEntityImages\(\{\s*id:\s*iconicId/)

    // 4. Dossier summary has line-clamp for breathing room
    expect(freshNocturneCss).toMatch(/\.home-feature-dossier\s+\.framed-dossier__summary\s+p\s*\{[^}]*-webkit-line-clamp:\s*2/)
  })
})




