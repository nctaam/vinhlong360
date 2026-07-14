// @vitest-environment node

import disclosureJson from '#launch-config/ai-disclosure.json'
import { describe, expect, it } from 'vitest'
import validatorCorpusJson from '../../tests/fixtures/ai-disclosure-validator-corpus.json'
import {
  aiDisclosure,
  parseAiDisclosure,
  type AiDisclosureArtifact,
} from '../utils/aiDisclosure'

interface DisclosureMutation {
  name: string
  operation: 'append' | 'delete' | 'reverse' | 'set'
  pointer: string
  value?: unknown
  error: string
}

const validatorCorpus = validatorCorpusJson as DisclosureMutation[]
const requiredBaseCorpus: DisclosureMutation[] = [
  { name: 'wrong-revision', operation: 'set', pointer: '/revision', value: 'ai-disclosure-v0', error: 'revision' },
  { name: 'extra-root-key', operation: 'set', pointer: '/extra', value: true, error: 'root keys' },
  { name: 'missing-ugc', operation: 'delete', pointer: '/ugc_photo', error: 'root keys' },
  {
    name: 'altered-ai-short',
    operation: 'set',
    pointer: '/entity_ai/short_label',
    value: 'AI',
    error: 'entity_ai',
  },
  {
    name: 'altered-ai-full',
    operation: 'set',
    pointer: '/entity_ai/full_disclosure',
    value: 'altered',
    error: 'entity_ai',
  },
  {
    name: 'altered-placeholder-full',
    operation: 'set',
    pointer: '/placeholder/full_disclosure',
    value: 'altered',
    error: 'placeholder',
  },
  {
    name: 'altered-ugc-short',
    operation: 'set',
    pointer: '/ugc_photo/short_label',
    value: 'photo',
    error: 'ugc_photo',
  },
  {
    name: 'altered-ugc-full',
    operation: 'set',
    pointer: '/ugc_photo/full_disclosure',
    value: 'altered',
    error: 'ugc_photo',
  },
  {
    name: 'altered-accessibility-key',
    operation: 'set',
    pointer: '/entity_ai/accessible_description_key',
    value: 'wrong',
    error: 'entity_ai',
  },
  {
    name: 'reordered-forbidden-claims',
    operation: 'reverse',
    pointer: '/forbidden_entity_image_claims',
    error: 'forbidden claims',
  },
  {
    name: 'wrong-forbidden-type',
    operation: 'set',
    pointer: '/forbidden_entity_image_claims',
    value: 'real photo',
    error: 'forbidden claims',
  },
]
const requiredAdditionalCorpus: DisclosureMutation[] = [
  {
    name: 'added-forbidden-claim',
    operation: 'append',
    pointer: '/forbidden_entity_image_claims',
    value: 'current entity photo',
    error: 'forbidden claims',
  },
  {
    name: 'wrong-entity-scalar-type',
    operation: 'set',
    pointer: '/entity_ai',
    value: 'entity-ai',
    error: 'entity_ai',
  },
  {
    name: 'wrong-placeholder-array-type',
    operation: 'set',
    pointer: '/placeholder',
    value: [],
    error: 'placeholder',
  },
  {
    name: 'wrong-ugc-short-object-type',
    operation: 'set',
    pointer: '/ugc_photo/short_label',
    value: { label: 'user photo' },
    error: 'ugc_photo',
  },
]

function cloneDisclosure(): Record<string, unknown> {
  return structuredClone(disclosureJson) as Record<string, unknown>
}

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

function pointerValue(document: unknown, pointer: string): unknown {
  let current = document
  for (const part of pointerParts(pointer)) {
    current = Array.isArray(current)
      ? current[Number(part)]
      : (current as Record<string, unknown>)[part]
  }
  return current
}

function applyMutation(document: unknown, mutation: DisclosureMutation): void {
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

  const target = Array.isArray(parent) ? parent[Number(key)] : parent[key]
  if (!Array.isArray(target)) {
    throw new Error(`${mutation.operation} requires array: ${mutation.pointer}`)
  }
  if (mutation.operation === 'reverse') target.reverse()
  else target.push(structuredClone(mutation.value))
}

function withClaims(claims: unknown): Record<string, unknown> {
  return { ...cloneDisclosure(), forbidden_entity_image_claims: claims }
}

function assertReadonlyDisclosureTypes(disclosure: AiDisclosureArtifact): void {
  const revision: 'ai-disclosure-v1' = disclosure.revision
  const entityShort: 'Minh h\u1ecda AI' = disclosure.entity_ai.short_label
  const placeholderShort: null = disclosure.placeholder.short_label
  const ugcFull: '\u1ea2nh do ng\u01b0\u1eddi d\u00f9ng cung c\u1ea5p.' = disclosure.ugc_photo.full_disclosure
  const claims: readonly [
    '\u1ea3nh th\u1eadt',
    'real photo',
    'documentary photo',
    'on-site photo',
    '\u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7',
  ] = disclosure.forbidden_entity_image_claims

  void revision
  void entityShort
  void placeholderShort
  void ugcFull
  void claims

  // @ts-expect-error parsed root fields are readonly
  disclosure.revision = 'ai-disclosure-v0'
  // @ts-expect-error parsed nested fields are readonly
  disclosure.entity_ai.short_label = 'AI'
  // @ts-expect-error parsed claims are a readonly tuple
  disclosure.forbidden_entity_image_claims.push('extra')
  // @ts-expect-error parsed claim entries are readonly
  disclosure.forbidden_entity_image_claims[0] = 'changed'
}

void assertReadonlyDisclosureTypes

describe('parseAiDisclosure', () => {
  it('parses the canonical artifact at module load with exact reviewed copy', () => {
    expect(aiDisclosure).toEqual(disclosureJson)
    expect(parseAiDisclosure(disclosureJson)).toEqual(disclosureJson)
  })

  it('preserves the exact eleven required shared validator rows and additions', () => {
    expect(validatorCorpus.slice(0, requiredBaseCorpus.length)).toEqual(requiredBaseCorpus)
    expect(validatorCorpus.slice(requiredBaseCorpus.length)).toEqual(requiredAdditionalCorpus)
  })

  it.each(validatorCorpus)('rejects shared validator mutation: $name', (mutation) => {
    const candidate = cloneDisclosure()
    applyMutation(candidate, mutation)

    expect(() => parseAiDisclosure(candidate)).toThrow(new RegExp(mutation.error, 'i'))
  })

  it.each([
    ['wrong schema scalar type', { ...cloneDisclosure(), schema_version: true }, /schema_version/i],
    ['missing entity key', {
      ...cloneDisclosure(),
      entity_ai: {
        short_label: disclosureJson.entity_ai.short_label,
        full_disclosure: disclosureJson.entity_ai.full_disclosure,
      },
    }, /entity_ai.*keys/i],
    ['extra placeholder key', {
      ...cloneDisclosure(),
      placeholder: { ...disclosureJson.placeholder, extra: true },
    }, /placeholder.*keys/i],
    ['extra UGC key', {
      ...cloneDisclosure(),
      ugc_photo: { ...disclosureJson.ugc_photo, extra: true },
    }, /ugc_photo.*keys/i],
  ])('rejects exact schema and nested keys: %s', (_name, candidate, error) => {
    expect(() => parseAiDisclosure(candidate)).toThrow(error as RegExp)
  })

  it.each([
    ['null root', null],
    ['array root', []],
    ['scalar root', 'ai-disclosure-v1'],
  ])('rejects a non-object JSON root: %s', (_name, candidate) => {
    expect(() => parseAiDisclosure(candidate)).toThrow(/root.*plain JSON object/i)
  })

  it.each([
    ['custom root prototype', { inherited: true }],
    ['null root prototype', null],
  ])('rejects a %s', (_name, prototype) => {
    const candidate = cloneDisclosure()
    Object.setPrototypeOf(candidate, prototype)

    expect(() => parseAiDisclosure(candidate)).toThrow(/root.*plain JSON object/i)
  })

  it('rejects a nested copy object with an unusual prototype', () => {
    const candidate = cloneDisclosure()
    const entity = candidate.entity_ai as Record<string, unknown>
    Object.setPrototypeOf(entity, { inherited: true })

    expect(() => parseAiDisclosure(candidate)).toThrow(/entity_ai.*plain JSON object/i)
  })

  it('rejects symbol, non-enumerable, and accessor object properties', () => {
    const symbolCandidate = cloneDisclosure()
    Object.defineProperty(symbolCandidate, Symbol('extra'), { enumerable: true, value: true })
    expect(() => parseAiDisclosure(symbolCandidate)).toThrow(/root keys/i)

    const hiddenCandidate = cloneDisclosure()
    Object.defineProperty(hiddenCandidate, 'extra', { enumerable: false, value: true })
    expect(() => parseAiDisclosure(hiddenCandidate)).toThrow(/root keys/i)

    const accessorCandidate = cloneDisclosure()
    const entity = accessorCandidate.entity_ai as Record<string, unknown>
    Object.defineProperty(entity, 'short_label', {
      configurable: true,
      enumerable: true,
      get: () => disclosureJson.entity_ai.short_label,
    })
    expect(() => parseAiDisclosure(accessorCandidate)).toThrow(/entity_ai.*keys/i)
  })

  it.each([
    ['sparse array', () => new Array<unknown>(disclosureJson.forbidden_entity_image_claims.length)],
    ['extra own property', () => {
      const claims = [...disclosureJson.forbidden_entity_image_claims]
      Object.defineProperty(claims, 'reviewed', { enumerable: true, value: true })
      return claims
    }],
    ['custom prototype', () => {
      const claims = [...disclosureJson.forbidden_entity_image_claims]
      Object.setPrototypeOf(claims, Object.create(Array.prototype))
      return claims
    }],
    ['accessor item', () => {
      const claims = [...disclosureJson.forbidden_entity_image_claims]
      Object.defineProperty(claims, '0', {
        configurable: true,
        enumerable: true,
        get: () => disclosureJson.forbidden_entity_image_claims[0],
      })
      return claims
    }],
  ])('rejects a forbidden claims %s', (_name, buildClaims) => {
    expect(() => parseAiDisclosure(withClaims(buildClaims()))).toThrow(/plain dense JSON array/i)
  })

  it('rejects an Array subclass for forbidden claims', () => {
    class ClaimArray extends Array<string> {}
    const claims = new ClaimArray(...disclosureJson.forbidden_entity_image_claims)

    expect(() => parseAiDisclosure(withClaims(claims))).toThrow(/plain dense JSON array/i)
  })

  it('does not mutate or retain aliases and deeply freezes its owned result', () => {
    const input = cloneDisclosure()
    const before = structuredClone(input)
    const parsed = parseAiDisclosure(input)

    expect(input).toEqual(before)
    expect(parsed).not.toBe(input)
    expect(parsed.entity_ai).not.toBe(input.entity_ai)
    expect(parsed.placeholder).not.toBe(input.placeholder)
    expect(parsed.ugc_photo).not.toBe(input.ugc_photo)
    expect(parsed.forbidden_entity_image_claims).not.toBe(input.forbidden_entity_image_claims)
    expect(Object.isFrozen(parsed)).toBe(true)
    expect(Object.isFrozen(parsed.entity_ai)).toBe(true)
    expect(Object.isFrozen(parsed.placeholder)).toBe(true)
    expect(Object.isFrozen(parsed.ugc_photo)).toBe(true)
    expect(Object.isFrozen(parsed.forbidden_entity_image_claims)).toBe(true)
    expect(Object.isFrozen(input)).toBe(false)

    const entity = input.entity_ai as Record<string, unknown>
    entity.short_label = 'changed after parsing'
    const claims = input.forbidden_entity_image_claims as string[]
    claims.reverse()
    expect(parsed).toEqual(disclosureJson)
  })

  it('returns only canonical owned values after validation', () => {
    const input = cloneDisclosure()
    const parsed = parseAiDisclosure(input)

    for (const pointer of [
      '/entity_ai/short_label',
      '/placeholder/full_disclosure',
      '/ugc_photo/accessible_description_key',
      '/forbidden_entity_image_claims/0',
    ]) {
      expect(pointerValue(parsed, pointer)).toBe(pointerValue(disclosureJson, pointer))
    }
  })
})
