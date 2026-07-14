import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import validatorCorpusJson from '../../tests/fixtures/launch-route-validator-corpus.json'
import {
  classifyRequestTarget,
  extractStaticSitemapPaths,
  launchRouteManifest,
  parseLaunchRouteManifest,
} from '../server/utils/launch/launchRouteManifest'

interface ManifestMutation {
  operation: 'delete' | 'set' | 'append-copy' | 'append'
  pointer: string
  value?: unknown
}

interface RouteCorpusRow {
  target: string
  method: string
  classification: string
  canonical: string | null
  variant?: {
    name: string
    mutations: Array<{
      operation: 'append'
      pointer: '/exact_routes' | '/dynamic_templates'
      value: Record<string, unknown>
    }>
    static_sitemap_paths?: string[]
  }
}

interface ValidatorMutation extends ManifestMutation {
  name: string
  error: string | null
}

const routeCorpus = JSON.parse(readFileSync(
  resolve(process.cwd(), '../tests/fixtures/launch-route-parity-corpus.json'),
  'utf8',
)) as RouteCorpusRow[]
const validatorCorpus = validatorCorpusJson as ValidatorMutation[]
const staticSitemapPaths = [
  '/',
  '/ban-do',
  '/chinh-sach-bao-mat',
  '/danh-ba',
  '/dia-diem',
  '/dieu-khoan-su-dung',
  '/du-lich',
  '/gioi-thieu',
  '/huong-dan',
  '/huong-dan-thanh-vien',
  '/kham-pha/am-thuc',
  '/kham-pha/lang-nghe',
  '/kham-pha/mua-sam',
  '/kham-pha/thien-nhien',
  '/kham-pha/van-hoa',
  '/khu-vuc/ben-tre',
  '/khu-vuc/tra-vinh',
  '/khu-vuc/vinh-long',
  '/le-hoi',
  '/lien-he',
  '/luu-tru',
  '/ocop',
  '/san-pham',
  '/su-kien',
  '/theo-mua',
  '/tuyen-duong',
]

function pointerParts(pointer: string): string[] {
  return pointer.slice(1).split('/').map(part => part.replaceAll('~1', '/').replaceAll('~0', '~'))
}

function pointerParent(document: unknown, pointer: string): [Record<string, unknown> | unknown[], string] {
  const parts = pointerParts(pointer)
  let current = document
  for (const part of parts.slice(0, -1)) {
    current = Array.isArray(current)
      ? current[Number(part)]
      : (current as Record<string, unknown>)[part]
  }
  if (current === null || typeof current !== 'object') {
    throw new Error(`invalid mutation pointer: ${pointer}`)
  }
  return [current as Record<string, unknown> | unknown[], parts.at(-1)!]
}

function applyMutation(document: unknown, mutation: ManifestMutation): void {
  const [parent, key] = pointerParent(document, mutation.pointer)
  if (mutation.operation === 'delete') {
    if (Array.isArray(parent)) parent.splice(Number(key), 1)
    else delete parent[key]
    return
  }
  if (mutation.operation === 'set') {
    if (Array.isArray(parent)) parent[Number(key)] = structuredClone(mutation.value)
    else parent[key] = structuredClone(mutation.value)
    return
  }
  if (mutation.operation === 'append-copy') {
    if (!Array.isArray(parent)) throw new Error(`append-copy requires array: ${mutation.pointer}`)
    parent.push(structuredClone(parent[Number(key)]))
    return
  }

  const target = Array.isArray(parent) ? parent[Number(key)] : parent[key]
  if (!Array.isArray(target)) throw new Error(`append requires array: ${mutation.pointer}`)
  target.push(structuredClone(mutation.value))
}

function pointerValue(document: unknown, pointer: string): unknown {
  let current = document
  for (const part of pointerParts(pointer)) {
    current = Array.isArray(current)
      ? current[Number(part)]
      : (current as Record<string, unknown>)[part]
  }
  return current
}

function manifestForRouteRow(row: RouteCorpusRow) {
  const candidate = structuredClone(launchRouteManifest)
  for (const mutation of row.variant?.mutations ?? []) applyMutation(candidate, mutation)
  return parseLaunchRouteManifest(candidate)
}

function validateRouteCorpusShape(): void {
  const required = ['target', 'method', 'classification', 'canonical']
  const variantNames = new Set<string>()
  for (const row of routeCorpus as unknown as Array<Record<string, unknown>>) {
    expect(Object.keys(row).sort()).toEqual([
      ...required,
      ...('variant' in row ? ['variant'] : []),
    ].sort())
    expect(typeof row.target).toBe('string')
    expect(typeof row.method).toBe('string')
    expect(typeof row.classification).toBe('string')
    expect(row.canonical === null || typeof row.canonical === 'string').toBe(true)
    if (!('variant' in row)) continue
    const variant = row.variant as Record<string, unknown>
    expect(Object.keys(variant).sort()).toEqual([
      'mutations',
      'name',
      ...('static_sitemap_paths' in variant ? ['static_sitemap_paths'] : []),
    ].sort())
    expect(typeof variant.name).toBe('string')
    expect((variant.name as string).length).toBeGreaterThan(0)
    expect(variantNames.has(variant.name as string)).toBe(false)
    variantNames.add(variant.name as string)
    expect(Array.isArray(variant.mutations)).toBe(true)
    expect((variant.mutations as unknown[]).length).toBeGreaterThan(0)
    for (const rawMutation of variant.mutations as Array<Record<string, unknown>>) {
      expect(Object.keys(rawMutation).sort()).toEqual(['operation', 'pointer', 'value'])
      expect(rawMutation.operation).toBe('append')
      expect(['/exact_routes', '/dynamic_templates']).toContain(rawMutation.pointer)
      expect(rawMutation.value).not.toBeNull()
      expect(typeof rawMutation.value).toBe('object')
      expect(Array.isArray(rawMutation.value)).toBe(false)
    }
    if ('static_sitemap_paths' in variant) {
      expect(Array.isArray(variant.static_sitemap_paths)).toBe(true)
      expect((variant.static_sitemap_paths as unknown[]).length).toBe(2)
      expect((variant.static_sitemap_paths as unknown[]).every(path => typeof path === 'string')).toBe(true)
    }
  }
}

describe('launch route runtime parity corpus', () => {
  it('validates the shared route corpus shape', () => {
    validateRouteCorpusShape()
  })

  it('accepts the canonical manifest templates before applying mutations', () => {
    const parsed = parseLaunchRouteManifest(structuredClone(launchRouteManifest))

    expect(parsed.dynamic_templates.map(item => item.template)).toEqual([
      '/dia-diem/{entity_id}',
      '/xa-phuong/{ward_id}',
      '/bai-viet/{id}',
      '/nguoi-dung/{id}',
      '/lich-trinh/{id}',
      '/lich-trinh-chia-se/{id}',
    ])
  })

  it.each(validatorCorpus)('applies shared validator mutation: $name', (mutation) => {
    const candidate = structuredClone(launchRouteManifest)
    applyMutation(candidate, mutation)

    if (mutation.error === null) {
      expect(() => parseLaunchRouteManifest(candidate)).not.toThrow()
    } else {
      expect(() => parseLaunchRouteManifest(candidate)).toThrow(new RegExp(mutation.error, 'i'))
    }
  })

  it.each(routeCorpus)('classifies $method $target', (row) => {
    const manifest = manifestForRouteRow(row)
    for (const mutation of row.variant?.mutations ?? []) {
      expect(pointerValue(manifest, mutation.pointer)).toContainEqual(mutation.value)
    }
    const decision = classifyRequestTarget(row.target, manifest, row.method)

    expect(decision).toEqual({
      classification: row.classification,
      canonical_path: row.canonical,
    })
    if (row.variant?.static_sitemap_paths) {
      const expected = row.variant.static_sitemap_paths
      expect(extractStaticSitemapPaths(manifest).filter(path => expected.includes(path))).toEqual(expected)
    }
  })

  it('extracts only the reviewed static sitemap inventory', () => {
    expect(extractStaticSitemapPaths(launchRouteManifest)).toEqual(staticSitemapPaths)
  })

  it('normalizes the shared accepted ingress exception model', () => {
    const candidate = structuredClone(launchRouteManifest)
    for (const mutation of validatorCorpus) {
      if (mutation.name.startsWith('accepted-ingress-') || mutation.name === 'accepted-nel-ingress-review') {
        applyMutation(candidate, mutation)
      }
    }

    expect(parseLaunchRouteManifest(candidate).backend_ingress_exceptions).toEqual([
      { prefix: '/hook', upstream: 'agent', review_reason: 'reviewed callback' },
      { prefix: '/nel-hook', upstream: 'bot-gateway', review_reason: '\u0085' },
    ])
  })
})
