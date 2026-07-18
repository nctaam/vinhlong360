// @vitest-environment node

import { readFileSync, readdirSync } from 'node:fs'
import { resolve } from 'node:path'
import { loadNuxtConfig } from '@nuxt/kit'
import { describe, expect, it } from 'vitest'

import { buildLaunchHead } from '../composables/useLaunchSafety'
import { buildLaunchResponseHeaders } from '../server/utils/launch/launchHeaders'
import type { LaunchPageDecision } from '../types/launch'

const fingerprint = 'b'.repeat(64)

const closedDecision: LaunchPageDecision = {
  operational_state: 'closed',
  indexing_posture: 'closed',
  policy_fingerprint: null,
  route_manifest_revision: null,
  backend_policy_revision: null,
  sitemap_batch_revision: null,
  sitemap_action: 'closed-empty',
  reason: 'closed-default',
  robots: 'noindex, follow',
  sitemapDiscovery: false,
}

const selectiveStaticDecision: LaunchPageDecision = {
  operational_state: 'selective-open',
  indexing_posture: 'selective-open',
  policy_fingerprint: fingerprint,
  route_manifest_revision: 'launch-indexing-policy-v1',
  backend_policy_revision: 'index-policy-v1',
  sitemap_batch_revision: null,
  sitemap_action: 'guarded-proxy',
  reason: 'valid-two-key-unlock',
  robots: 'index, follow',
  sitemapDiscovery: true,
}

const selectiveNegativeEntityDecision: LaunchPageDecision = {
  ...selectiveStaticDecision,
  robots: 'noindex, follow',
}

const failedOpenDecision: LaunchPageDecision = {
  operational_state: 'failed-open',
  indexing_posture: 'closed',
  policy_fingerprint: null,
  route_manifest_revision: null,
  backend_policy_revision: null,
  sitemap_batch_revision: null,
  sitemap_action: 'unavailable',
  reason: 'entity-policy-unavailable',
  robots: 'noindex, follow',
  sitemapDiscovery: false,
}

function source(path: string): string {
  return readFileSync(resolve(process.cwd(), path), 'utf8').replaceAll('\r\n', '\n')
}

function vueFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => entry.isDirectory()
    ? vueFiles(resolve(directory, entry.name))
    : entry.name.endsWith('.vue') ? [resolve(directory, entry.name)] : [])
}

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => entry.isDirectory()
    ? sourceFiles(resolve(directory, entry.name))
    : /\.(?:ts|vue)$/u.test(entry.name) ? [resolve(directory, entry.name)] : [])
}

describe('launch head authority', () => {
  it.each([
    [closedDecision, 'noindex, follow', 0],
    [selectiveStaticDecision, 'index, follow', 1],
    [selectiveNegativeEntityDecision, 'noindex, follow', 1],
    [failedOpenDecision, 'noindex, follow', 0],
  ] as const)('emits one robots meta and conditional sitemap link', (decision, robots, sitemapLinks) => {
    const head = buildLaunchHead(decision)

    expect(head.meta.filter(item => item.name === 'robots')).toEqual([{ name: 'robots', content: robots }])
    expect(head.link.filter(item => item.rel === 'sitemap')).toHaveLength(sitemapLinks)
    if (sitemapLinks) {
      expect(head.link).toEqual([{
        rel: 'sitemap',
        type: 'application/xml',
        href: '/sitemap-index.xml',
      }])
    }
    expect(buildLaunchResponseHeaders({ decision, html: true })['X-Robots-Tag']).toBe(robots)
  })

  it('keeps launch head ownership out of static Nuxt config while defaulting runtime closed', async () => {
    const config = await loadNuxtConfig({ cwd: process.cwd(), dotenv: false })
    const meta = config.app.head.meta ?? []
    const links = config.app.head.link ?? []

    expect(config.runtimeConfig.public.siteNoindex).toBe(true)
    expect(meta.filter(item => 'name' in item && item.name === 'robots')).toEqual([])
    expect(links.filter(item => 'rel' in item && item.rel === 'sitemap')).toEqual([])
    expect(config.nitro?.routeRules?.['/**']?.headers).not.toHaveProperty('X-Robots-Tag')
  })

  it('registers the launch head once at the application boundary', () => {
    const app = source('app.vue')

    expect(app.match(/useLaunchSafety\(\)/g)).toHaveLength(1)
    expect(app.match(/buildLaunchHead\(/g)).toHaveLength(1)
    expect(app).toContain('launchSafety.resetForNavigation()')
  })

  it('rejects page-owned robots declarations and quality predicates', () => {
    const roots = [resolve(process.cwd(), 'pages'), resolve(process.cwd(), 'layouts')]
    const offenders = roots.flatMap(vueFiles).filter((path) => {
      const page = readFileSync(path, 'utf8')
      return /\brobots\s*:|name\s*:\s*["']robots["']/u.test(page)
    })

    expect(offenders).toEqual([])
    expect(source('pages/xa-phuong/[id].vue')).not.toContain('totalContent.value <= 1')
  })

  it('scans all frontend surfaces case-insensitively for alternate robots predicates', () => {
    const roots = [
      resolve(process.cwd(), 'pages'),
      resolve(process.cwd(), 'layouts'),
      resolve(process.cwd(), 'components'),
      resolve(process.cwd(), 'composables'),
      resolve(process.cwd(), 'plugins'),
      resolve(process.cwd(), 'utils'),
    ]
    const offenders = roots.flatMap(sourceFiles).filter((path) => {
      if (path.endsWith('composables\\useLaunchSafety.ts') || path.endsWith('composables/useLaunchSafety.ts')) return false
      const normalized = readFileSync(path, 'utf8')
        .toLowerCase()
        .replace(/[\s'"`+()[\]{}]/gu, '')
      return normalized.includes('robots:')
        || normalized.includes('name:robots')
        || normalized.includes('[robots]')
    })

    expect(offenders).toEqual([])
  })
})
