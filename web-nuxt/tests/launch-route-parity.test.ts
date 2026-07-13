import { describe, expect, it } from 'vitest'
import routeCorpusJson from '../../tests/fixtures/launch-route-parity-corpus.json'
import validatorCorpusJson from '../../tests/fixtures/launch-route-validator-corpus.json'
import {
  classifyRequestTarget,
  extractStaticSitemapPaths,
  launchRouteManifest,
  parseLaunchRouteManifest,
} from '../server/utils/launch/launchRouteManifest'

interface RouteCorpusRow {
  target: string
  method: string
  classification: string
  canonical: string | null
}

interface ValidatorMutation {
  name: string
  operation: 'delete' | 'set' | 'append-copy' | 'append'
  pointer: string
  value?: unknown
  error: string | null
}

const routeCorpus = routeCorpusJson as RouteCorpusRow[]
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

function applyMutation(document: unknown, mutation: ValidatorMutation): void {
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

describe('launch route runtime parity corpus', () => {
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
    const decision = classifyRequestTarget(row.target, launchRouteManifest, row.method)

    expect(decision).toEqual({
      classification: row.classification,
      canonical_path: row.canonical,
    })
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
