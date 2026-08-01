import { mountSuspended } from '@nuxt/test-utils/runtime'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { defineComponent, h } from 'vue'
import { afterEach, describe, expect, it } from 'vitest'
import CatalogInterstitial from '../components/CatalogInterstitial.vue'
import CatalogSpotlight from '../components/CatalogSpotlight.vue'
import EntityCard from '../components/EntityCard.vue'

const wrappers: Array<{ unmount: () => void }> = []
const stylesheets: HTMLStyleElement[] = []
const spotlightItem = {
  id: 'legacy-craft',
  type: 'craft_village',
  name: 'Làng nghề legacy',
  summary: 'Một câu chuyện làng nghề đủ dài để component spotlight chọn làm nội dung nổi bật mà không cần mock component.',
  season: { months: Array.from({ length: 12 }, (_, index) => index + 1) },
}

function styleBlocks(source: string) {
  return [...source.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/gi)].map(match => match[1]).join('\n')
}

async function installCatalogStyles() {
  const [variables, bridge, entityCard, spotlight, interstitial] = await Promise.all([
    readFile(resolve(import.meta.dirname, '../assets/css/variables.css'), 'utf8'),
    readFile(resolve(import.meta.dirname, '../assets/css/tri-region-color.css'), 'utf8'),
    readFile(resolve(import.meta.dirname, '../components/EntityCard.vue'), 'utf8'),
    readFile(resolve(import.meta.dirname, '../components/CatalogSpotlight.vue'), 'utf8'),
    readFile(resolve(import.meta.dirname, '../components/CatalogInterstitial.vue'), 'utf8'),
  ])
  const stylesheet = document.createElement('style')
  stylesheet.textContent = [variables, bridge, styleBlocks(entityCard), styleBlocks(spotlight), styleBlocks(interstitial)].join('\n')
  document.head.append(stylesheet)
  stylesheets.push(stylesheet)
}

function catalogHarness(options: {
  className?: string
  triRegion?: boolean
  recipe?: boolean
  tokens?: Record<string, string>
}) {
  return defineComponent({
    setup: () => () => h('main', {
      class: options.className,
      'data-color-system': options.triRegion ? 'tri-region-v1' : undefined,
      'data-page-recipe': options.triRegion ? 'homepage' : undefined,
      'data-material-accent': options.triRegion ? 'clay' : undefined,
      style: options.tokens,
    }, [
      h(EntityCard, {
        entity: { id: 'entity-focus', type: 'craft_village', name: 'Thẻ kiểm tra' },
        colorRecipe: options.recipe ? 'tri-region-v1' : undefined,
      }),
      h(CatalogSpotlight, {
        items: [spotlightItem],
        colorRecipe: options.recipe ? 'tri-region-v1' : undefined,
      }),
      h(CatalogInterstitial, {
        fact: 'Thông tin cascade',
        links: [{ to: '/ban-do', label: 'Xem bản đồ' }],
        materialAccent: options.recipe ? 'amber' : undefined,
      }),
    ]),
  })
}

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  for (const stylesheet of stylesheets.splice(0)) stylesheet.remove()
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

  it('keeps a no-prop EntityCard on the Homepage legacy primary cascade while recipe focus stays semantic', async () => {
    await installCatalogStyles()
    const Harness = catalogHarness({
      triRegion: true,
      recipe: false,
      tokens: {
        '--color-action': 'rgb(3, 90, 105)',
        '--color-action-rgb': '3, 90, 105',
        '--color-focus': 'rgb(206, 167, 112)',
      },
    })
    const wrapper = await mountSuspended(Harness, { attachTo: document.body })
    wrappers.push(wrapper)

    const legacyLink = wrapper.get<HTMLElement>('.card-body-link').element
    legacyLink.focus()
    expect(getComputedStyle(legacyLink).outlineColor).toBe('rgb(3, 90, 105)')

    const RecipeHarness = catalogHarness({
      triRegion: true,
      recipe: true,
      tokens: {
        '--color-action': 'rgb(3, 90, 105)',
        '--color-action-rgb': '3, 90, 105',
        '--color-focus': 'rgb(206, 167, 112)',
      },
    })
    const recipeWrapper = await mountSuspended(RecipeHarness, { attachTo: document.body })
    wrappers.push(recipeWrapper)
    const recipeLink = recipeWrapper.get<HTMLElement>('.card-body-link').element
    recipeLink.focus()
    expect(getComputedStyle(recipeLink).outlineColor).toBe('rgb(206, 167, 112)')
  })

  it.each([
    { theme: 'light', primary: 'rgb(11, 22, 33)', rgbChannels: '11, 22, 33', fg: 'rgb(44, 55, 66)', strong: 'rgb(77, 88, 99)' },
    { theme: 'dark', primary: 'rgb(21, 32, 43)', rgbChannels: '21, 32, 43', fg: 'rgb(54, 65, 76)', strong: 'rgb(87, 98, 109)' },
  ])('keeps no-prop shared catalog visuals bound to customizable BASE aliases in $theme', async ({ theme, primary, rgbChannels, fg, strong }) => {
    await installCatalogStyles()
    const Harness = catalogHarness({
      className: theme,
      tokens: {
        '--primary': primary,
        '--primary-rgb': rgbChannels,
        '--primary-fg': fg,
        '--primary-fg-strong': strong,
      },
    })
    const wrapper = await mountSuspended(Harness, { attachTo: document.body })
    wrappers.push(wrapper)

    const kicker = wrapper.get<HTMLElement>('.cspot-kicker').element
    const panel = wrapper.get<HTMLElement>('.interstitial').element
    const icon = wrapper.get<HTMLElement>('.interstitial-icon-chip').element
    const link = wrapper.get<HTMLElement>('.interstitial-link').element
    link.focus()

    expect(getComputedStyle(kicker).color).toBe(strong)
    expect(getComputedStyle(link).color).toBe(fg)
    expect(getComputedStyle(link).outlineColor).toBe(primary)
    expect(getComputedStyle(panel).backgroundImage.replace(/\s+/g, '')).toContain(`rgba(${rgbChannels.replace(/\s+/g, '')},.${theme === 'dark' ? '06' : '04'})`)
    if (theme === 'light') {
      expect(getComputedStyle(icon).backgroundColor).toBe('rgba(11, 22, 33, .07)')
    }

    if (theme === 'dark') {
      const badge = wrapper.get<HTMLElement>('.cspot-badge').element
      badge.className = 'cspot-badge cspot-badge-year'
      expect(getComputedStyle(badge).color).toBe('#74ABB5')
    }
  })

  it('keeps opted-in catalog treatments on semantic Brand, Action and Focus instead of legacy overrides', async () => {
    await installCatalogStyles()
    const Harness = catalogHarness({
      triRegion: true,
      recipe: true,
      tokens: {
        '--primary': 'rgb(11, 22, 33)',
        '--primary-rgb': '11, 22, 33',
        '--primary-fg': 'rgb(44, 55, 66)',
        '--primary-fg-strong': 'rgb(77, 88, 99)',
        '--color-brand': 'rgb(149, 64, 43)',
        '--color-action': 'rgb(3, 90, 105)',
        '--color-focus': 'rgb(206, 167, 112)',
      },
    })
    const wrapper = await mountSuspended(Harness, { attachTo: document.body })
    wrappers.push(wrapper)

    const interstitialLink = wrapper.get<HTMLElement>('.interstitial-link').element
    expect(getComputedStyle(wrapper.get<HTMLElement>('.cspot-kicker').element).color).toBe('rgb(149, 64, 43)')
    expect(getComputedStyle(interstitialLink).color).toBe('rgb(3, 90, 105)')
    const unfocused = getComputedStyle(interstitialLink)
    expect(['', 'none']).toContain(unfocused.outlineStyle)
    expect(['', '0px']).toContain(unfocused.outlineWidth)
    interstitialLink.focus()
    expect(document.activeElement).toBe(interstitialLink)
    const focused = getComputedStyle(interstitialLink)
    expect(focused.outlineColor).toBe('rgb(206, 167, 112)')

    // HappyDOM resolves the semantic color but drops shorthand style/width when
    // its custom property is inherited, so keep this fallback contract narrow.
    const interstitialSource = await readFile(resolve(import.meta.dirname, '../components/CatalogInterstitial.vue'), 'utf8')
    const focusRule = styleBlocks(interstitialSource).match(/\.interstitial-link:focus-visible\s*\{([^}]*)\}/)?.[1]
    expect(focusRule).toBeDefined()
    expect(focusRule).toMatch(/outline:\s*2px\s+solid\s+var\(--catalog-interstitial-focus\);/)
    expect(focusRule).toMatch(/outline-offset:\s*2px;/)
  })
})
