// @vitest-environment node
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(process.cwd())
const doc = (rel: string) => readFileSync(resolve(root, rel), 'utf8')

describe('SEO & Editorial Craft Guardrails', () => {
  it('Google Sitelinks Searchbox uses EntryPoint schema on home and search hubs', () => {
    const home = doc('pages/index.vue')
    const search = doc('pages/tim-kiem.vue')

    expect(home).toContain("@type': 'EntryPoint'")
    expect(home).toContain("urlTemplate: 'https://vinhlong360.vn/tim-kiem?q={search_term_string}'")
    expect(home).toContain("ogType: 'website'")
    expect(home).toContain("twitterCard: 'summary_large_image'")

    expect(search).toContain("@type': 'EntryPoint'")
    expect(search).toContain("urlTemplate: 'https://vinhlong360.vn/tim-kiem?q={search_term_string}'")
  })

  it('Search results dynamically guard crawl budget with noindex, follow', () => {
    const search = doc('pages/tim-kiem.vue')
    expect(search).toMatch(/robots:\s*\(\)\s*=>\s*q\.value\.trim\(\)\s*\?\s*'noindex,\s*follow'\s*:\s*'index,\s*follow'/)
  })

  it('All key public navigation hubs pass :json-ld="true" to Breadcrumb', () => {
    const hubs = [
      'pages/tim-kiem.vue',
      'pages/ban-do.vue',
      'pages/danh-ba.vue',
      'pages/tuyen-duong.vue',
      'pages/dia-diem/index.vue',
      'pages/cong-dong.vue',
      'pages/huong-dan.vue',
      'pages/kham-pha/[interest].vue',
      'pages/luu-tru.vue',
      'pages/su-kien.vue',
    ]

    for (const hub of hubs) {
      const src = doc(hub)
      expect(src, `${hub} should enable :json-ld="true" on Breadcrumb`).toMatch(/<Breadcrumb[^>]*:json-ld="true"/)
    }
  })

  it('Exploration category title does not prepend decorative emojis in SEO title', () => {
    const interest = doc('pages/kham-pha/[interest].vue')
    expect(interest).not.toMatch(/title:\s*`\$\{interestMeta\.value\.emoji\}/)
    expect(interest).toContain('title: `${interestMeta.value.label} — Khám phá Vĩnh Long — vinhlong360`')
  })

  it('AI search assistant has stroke-consistent vectors and purpose-driven radius-control', () => {
    const assist = doc('components/AISearchAssist.vue')
    expect(assist).toContain('<IconLine name="alert-triangle"')
    expect(assist).toContain('<IconLine name="repeat"')
    expect(assist).toContain('var(--radius-control)')
    expect(assist).not.toContain('var(--radius-sm)')
  })
})
