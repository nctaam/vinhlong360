import { mountSuspended } from '@nuxt/test-utils/runtime'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import CatalogInterstitial from '../components/CatalogInterstitial.vue'
import CatalogSpotlight from '../components/CatalogSpotlight.vue'

const wrappers: Array<{ unmount: () => void }> = []
const spotlightItem = {
  id: 'legacy-craft',
  type: 'craft_village',
  name: 'Làng nghề legacy',
  summary: 'Một câu chuyện làng nghề đủ dài để component spotlight chọn làm nội dung nổi bật mà không cần mock component.',
}

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
})

describe('Catalog Tri-Region backward compatibility', () => {
  it('keeps CatalogSpotlight legacy DOM unmarked when the recipe prop is omitted', async () => {
    const wrapper = await mountSuspended(CatalogSpotlight, {
      props: { items: [spotlightItem] },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    const panel = wrapper.get('.cspot')
    expect(panel.classes()).toEqual(['cspot'])
    expect(panel.attributes('data-color-recipe')).toBeUndefined()
    expect(panel.attributes('data-material-accent')).toBeUndefined()
  })

  it('keeps CatalogInterstitial legacy DOM unmarked when materialAccent is omitted', async () => {
    const wrapper = await mountSuspended(CatalogInterstitial, {
      props: { fact: 'Thông tin legacy', variant: 'warm' },
    })
    wrappers.push(wrapper)

    const panel = wrapper.get('aside')
    expect(panel.classes()).toEqual(['interstitial', 'reveal', 'warm'])
    expect(panel.attributes('data-material-accent')).toBeUndefined()
    expect(wrapper.find('.catalog-interstitial-rule').exists()).toBe(false)
  })

  it('keeps legacy multi-tone rules as defaults and scopes solid material treatments to markers', async () => {
    const [entityCard, spotlight, interstitial] = await Promise.all([
      readFile(resolve(import.meta.dirname, '../components/EntityCard.vue'), 'utf8'),
      readFile(resolve(import.meta.dirname, '../components/CatalogSpotlight.vue'), 'utf8'),
      readFile(resolve(import.meta.dirname, '../components/CatalogInterstitial.vue'), 'utf8'),
    ])

    expect(entityCard).toMatch(/\.card-rule\s*\{[^}]*linear-gradient\(90deg,[^}]*\}/s)
    expect(entityCard).toMatch(/\.card\[data-color-recipe=['"]tri-region-v1['"]\][^{]*\.card-rule\s*\{[^}]*var\(--tri-region-material-accent/s)
    expect(entityCard).toMatch(/\.card-cover-link:focus-visible,[^{]*\{[^}]*var\(--color-brand\)/s)
    expect(entityCard).toMatch(/\.card\[data-color-recipe=['"]tri-region-v1['"]\][^{]*:focus-visible\s*\{[^}]*var\(--color-focus\)/s)
    expect(spotlight).toMatch(/\.cspot-rule\s*\{[^}]*linear-gradient\(90deg,[^}]*\}/s)
    expect(spotlight).toMatch(/\.cspot\[data-color-recipe=['"]tri-region-v1['"]\][^{]*\.cspot-rule\s*\{[^}]*var\(--tri-region-material-accent/s)
    expect(spotlight).toMatch(/\.cspot-kicker\s*\{[^}]*var\(--mangthit-700\)/s)
    expect(spotlight).toMatch(/\.cspot\[data-color-recipe=['"]tri-region-v1['"]\][^{]*\.cspot-kicker\s*\{[^}]*var\(--color-brand\)/s)
    expect(interstitial).toMatch(/\.interstitial\s*\{[^}]*var\(--color-brand-rgb\)/s)
    expect(interstitial).toMatch(/\.interstitial\[data-material-accent\][^{]*\{[^}]*var\(--tri-region-material-accent/s)
    expect(interstitial).toMatch(/\.interstitial-icon-chip\s*\{[^}]*var\(--color-brand-rgb\)/s)
    expect(interstitial).toMatch(/\.interstitial\[data-material-accent\][^{]*\.interstitial-icon-chip\s*\{[^}]*var\(--tri-region-material-accent/s)
    expect(interstitial).toMatch(/\.interstitial-link\s*\{[^}]*color:\s*var\(--color-brand\)/s)
    expect(interstitial).toMatch(/\.interstitial\[data-material-accent\][^{]*\.interstitial-link\s*\{[^}]*color:\s*var\(--color-action\)/s)
  })
})
