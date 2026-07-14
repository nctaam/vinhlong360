// @vitest-environment node

import disclosureJson from '#launch-config/ai-disclosure.json'
import { describe, expect, it } from 'vitest'
import validatorCorpusJson from '../../tests/fixtures/ai-disclosure-validator-corpus.json'
import {
  aiDisclosure,
  parseAiDisclosure,
  type AiDisclosureArtifact,
} from '../utils/aiDisclosure'

const MUTATION_OPERATIONS = ['append', 'delete', 'reverse', 'set'] as const
const MUTATION_OPERATION_SET = new Set<string>(MUTATION_OPERATIONS)
const DANGEROUS_POINTER_TOKENS = new Set(['__proto__', 'constructor', 'prototype'])
const CANONICAL_ARRAY_INDEX = /^(0|[1-9][0-9]*)$/

type MutationOperation = typeof MUTATION_OPERATIONS[number]

interface DisclosureMutation {
  name: string
  operation: MutationOperation
  pointer: string
  value?: unknown
  error: string
}

const validatorCorpus = validateValidatorCorpus(validatorCorpusJson)
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
const exactLoaderErrors: Record<string, string> = {
  'wrong-revision': 'canonical AI disclosure revision mismatch',
  'extra-root-key': 'canonical AI disclosure root keys mismatch',
  'missing-ugc': 'canonical AI disclosure root keys mismatch',
  'altered-ai-short': 'canonical AI disclosure entity_ai mismatch',
  'altered-ai-full': 'canonical AI disclosure entity_ai mismatch',
  'altered-placeholder-full': 'canonical AI disclosure placeholder mismatch',
  'altered-ugc-short': 'canonical AI disclosure ugc_photo mismatch',
  'altered-ugc-full': 'canonical AI disclosure ugc_photo mismatch',
  'altered-accessibility-key': 'canonical AI disclosure entity_ai mismatch',
  'reordered-forbidden-claims': 'canonical AI disclosure forbidden claims mismatch',
  'wrong-forbidden-type': 'canonical AI disclosure forbidden claims must be a plain dense JSON array',
  'added-forbidden-claim': 'canonical AI disclosure forbidden claims mismatch',
  'wrong-entity-scalar-type': 'canonical AI disclosure entity_ai must be a plain JSON object',
  'wrong-placeholder-array-type': 'canonical AI disclosure placeholder must be a plain JSON object',
  'wrong-ugc-short-object-type': 'canonical AI disclosure ugc_photo mismatch',
}

function expectExactError(run: () => unknown, expectedMessage: string): void {
  let thrown: unknown
  try {
    run()
  } catch (error) {
    thrown = error
  }
  expect(thrown).toBeInstanceOf(Error)
  expect((thrown as Error).message).toBe(expectedMessage)
}

function cloneDisclosure(): Record<string, unknown> {
  return structuredClone(disclosureJson) as Record<string, unknown>
}

function disclosureForMutation(mutation: DisclosureMutation): Record<string, unknown> {
  const candidate = cloneDisclosure()
  if (
    mutation.name === 'extra-root-key'
    && mutation.operation === 'set'
    && mutation.pointer === '/extra'
  ) {
    // Pre-seed the one intentional creation so applyMutation can remain typo-safe.
    Object.defineProperty(candidate, 'extra', {
      configurable: true,
      enumerable: true,
      value: undefined,
      writable: true,
    })
  }
  return candidate
}

function pointerParts(pointer: string): string[] {
  if (!pointer.startsWith('/')) {
    throw new Error(`AI disclosure corpus pointer must start with "/": ${pointer}`)
  }

  return pointer.slice(1).split('/').map((part) => {
    if (/~(?:[^01]|$)/.test(part)) {
      throw new Error(`AI disclosure corpus pointer has invalid escape: ${pointer}`)
    }
    const decoded = part.replaceAll('~1', '/').replaceAll('~0', '~')
    if (DANGEROUS_POINTER_TOKENS.has(decoded)) {
      throw new Error(`AI disclosure corpus pointer contains forbidden token: ${pointer}`)
    }
    return decoded
  })
}

function plainCorpusArray(value: unknown): unknown[] {
  if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype) {
    throw new Error('AI disclosure corpus must be a plain dense JSON array')
  }

  const ownKeys = Reflect.ownKeys(value)
  if (ownKeys.length !== value.length + 1 || !ownKeys.includes('length')) {
    throw new Error('AI disclosure corpus must be a plain dense JSON array')
  }
  for (let index = 0; index < value.length; index += 1) {
    const descriptor = Object.getOwnPropertyDescriptor(value, String(index))
    if (!descriptor?.enumerable || !('value' in descriptor)) {
      throw new Error('AI disclosure corpus must be a plain dense JSON array')
    }
  }
  return value
}

function plainCorpusRow(value: unknown, label: string): Record<string, unknown> {
  if (
    value === null
    || typeof value !== 'object'
    || Array.isArray(value)
    || Object.getPrototypeOf(value) !== Object.prototype
  ) {
    throw new Error(`AI disclosure corpus ${label} must be a plain JSON object`)
  }
  const row = value as Record<string, unknown>
  for (const key of Reflect.ownKeys(row)) {
    const descriptor = Object.getOwnPropertyDescriptor(row, key)
    if (typeof key !== 'string' || !descriptor?.enumerable || !('value' in descriptor)) {
      throw new Error(`AI disclosure corpus ${label} keys mismatch`)
    }
  }
  return row
}

function exactCorpusRowKeys(
  row: Record<string, unknown>,
  expectedKeys: readonly string[],
  label: string,
): void {
  const actual = Object.keys(row).sort()
  const expected = [...expectedKeys].sort()
  if (actual.join('\0') !== expected.join('\0')) {
    throw new Error(`AI disclosure corpus ${label} keys mismatch`)
  }
}

function mutationOperation(value: unknown): MutationOperation {
  if (typeof value !== 'string' || !MUTATION_OPERATION_SET.has(value)) {
    throw new Error(`AI disclosure corpus operation is unsupported: ${String(value)}`)
  }
  return value as MutationOperation
}

function validateMutationRow(value: unknown, label: string): DisclosureMutation {
  const row = plainCorpusRow(value, label)
  if (typeof row.name !== 'string' || row.name.length === 0) {
    throw new Error(`AI disclosure corpus ${label} name must be a non-empty string`)
  }
  const operation = mutationOperation(row.operation)
  if (typeof row.pointer !== 'string') {
    throw new Error(`AI disclosure corpus ${label} pointer must be a string`)
  }
  if (typeof row.error !== 'string' || row.error.length === 0) {
    throw new Error(`AI disclosure corpus ${label} error must be a non-empty string`)
  }

  const hasValue = Object.hasOwn(row, 'value')
  const requiresValue = operation === 'append' || operation === 'set'
  if (hasValue !== requiresValue) {
    throw new Error(`AI disclosure corpus ${label} value presence mismatch for ${operation}`)
  }
  exactCorpusRowKeys(
    row,
    ['error', 'name', 'operation', 'pointer', ...(requiresValue ? ['value'] : [])],
    label,
  )
  pointerParts(row.pointer)

  return requiresValue
    ? { name: row.name, operation, pointer: row.pointer, value: row.value, error: row.error }
    : { name: row.name, operation, pointer: row.pointer, error: row.error }
}

function validateValidatorCorpus(value: unknown): DisclosureMutation[] {
  const rows = plainCorpusArray(value)
  const names = new Set<string>()
  return rows.map((row, index) => {
    const mutation = validateMutationRow(row, `row[${index}]`)
    if (names.has(mutation.name)) {
      throw new Error(`AI disclosure corpus row[${index}] name must be unique`)
    }
    names.add(mutation.name)
    return mutation
  })
}

type PointerContainer = Record<string, unknown> | unknown[]

function pointerContainer(value: unknown, pointer: string): PointerContainer {
  if (value === null || typeof value !== 'object') {
    throw new Error(`AI disclosure corpus pointer parent is not an object: ${pointer}`)
  }
  return value as PointerContainer
}

function existingPointerKey(container: PointerContainer, token: string, pointer: string): string {
  if (Array.isArray(container)) {
    if (!CANONICAL_ARRAY_INDEX.test(token) || !Number.isSafeInteger(Number(token))) {
      throw new Error(`AI disclosure corpus pointer index is invalid: ${pointer}`)
    }
    if (Number(token) >= container.length) {
      throw new Error(`AI disclosure corpus pointer index is out of range: ${pointer}`)
    }
  }
  if (!Object.hasOwn(container, token)) {
    throw new Error(`AI disclosure corpus pointer target does not exist: ${pointer}`)
  }
  return token
}

function ownPointerValue(container: PointerContainer, key: string): unknown {
  return Array.isArray(container) ? container[Number(key)] : container[key]
}

function pointerParent(document: unknown, pointer: string): [PointerContainer, string] {
  const parts = pointerParts(pointer)
  let current = document
  for (const part of parts.slice(0, -1)) {
    const container = pointerContainer(current, pointer)
    current = ownPointerValue(container, existingPointerKey(container, part, pointer))
  }
  const parent = pointerContainer(current, pointer)
  const key = existingPointerKey(parent, parts.at(-1)!, pointer)
  return [parent, key]
}

function pointerValue(document: unknown, pointer: string): unknown {
  let current = document
  for (const part of pointerParts(pointer)) {
    const container = pointerContainer(current, pointer)
    current = ownPointerValue(container, existingPointerKey(container, part, pointer))
  }
  return current
}

function applyMutation(document: unknown, rawMutation: DisclosureMutation): void {
  const mutation = validateMutationRow(rawMutation, 'mutation')
  const [parent, key] = pointerParent(document, mutation.pointer)

  switch (mutation.operation) {
    case 'delete':
      if (Array.isArray(parent)) parent.splice(Number(key), 1)
      else delete parent[key]
      return
    case 'set':
      if (Array.isArray(parent)) parent[Number(key)] = structuredClone(mutation.value)
      else parent[key] = structuredClone(mutation.value)
      return
    case 'reverse':
    case 'append': {
      const target = ownPointerValue(parent, key)
      if (!Array.isArray(target)) {
        throw new Error(
          `AI disclosure corpus ${mutation.operation} target must be an array: ${mutation.pointer}`,
        )
      }
      if (mutation.operation === 'reverse') target.reverse()
      else target.push(structuredClone(mutation.value))
      return
    }
    default:
      throw new Error(`AI disclosure corpus operation is unsupported: ${String(mutation.operation)}`)
  }
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

  it('validates the imported corpus runtime shape before using it', () => {
    expect(validateValidatorCorpus(validatorCorpusJson)).toEqual([
      ...requiredBaseCorpus,
      ...requiredAdditionalCorpus,
    ])
  })

  it.each([
    ['non-object row', null, 'AI disclosure corpus row[0] must be a plain JSON object'],
    [
      'empty name',
      { ...requiredBaseCorpus[0], name: '' },
      'AI disclosure corpus row[0] name must be a non-empty string',
    ],
    [
      'unsupported operation',
      { ...requiredBaseCorpus[0], operation: 'copy' },
      'AI disclosure corpus operation is unsupported: copy',
    ],
    [
      'non-string pointer',
      { ...requiredBaseCorpus[0], pointer: 1 },
      'AI disclosure corpus row[0] pointer must be a string',
    ],
    [
      'empty error',
      { ...requiredBaseCorpus[0], error: '' },
      'AI disclosure corpus row[0] error must be a non-empty string',
    ],
    ['set without value', {
      name: 'set-without-value', operation: 'set', pointer: '/revision', error: 'revision',
    }, 'AI disclosure corpus row[0] value presence mismatch for set'],
    ['delete with value', {
      ...requiredBaseCorpus[2], value: null,
    }, 'AI disclosure corpus row[0] value presence mismatch for delete'],
    ['extra row key', {
      ...requiredBaseCorpus[0], extra: true,
    }, 'AI disclosure corpus row[0] keys mismatch'],
  ])('rejects malformed corpus runtime shape: %s', (_name, row, message) => {
    expectExactError(() => validateValidatorCorpus([row]), message)
  })

  it.each([
    ['missing leading slash', 'revision', 'AI disclosure corpus pointer must start with "/": revision'],
    ['invalid escape', '/entity_ai/~2', 'AI disclosure corpus pointer has invalid escape: /entity_ai/~2'],
    ['missing target', '/entity_ai/missing', 'AI disclosure corpus pointer target does not exist: /entity_ai/missing'],
    [
      'leading-zero array index',
      '/forbidden_entity_image_claims/01',
      'AI disclosure corpus pointer index is invalid: /forbidden_entity_image_claims/01',
    ],
    [
      'out-of-range array index',
      '/forbidden_entity_image_claims/9',
      'AI disclosure corpus pointer index is out of range: /forbidden_entity_image_claims/9',
    ],
    ['dangerous token', '/__proto__', 'AI disclosure corpus pointer contains forbidden token: /__proto__'],
  ])('rejects an unsafe mutation pointer: %s', (_name, pointer, message) => {
    const candidate = cloneDisclosure()
    const before = structuredClone(candidate)
    const mutation = {
      name: 'unsafe-pointer',
      operation: 'set',
      pointer,
      value: 'changed',
      error: 'unused',
    } as DisclosureMutation

    expectExactError(() => applyMutation(candidate, mutation), message)
    expect(candidate).toEqual(before)
  })

  it.each([
    ['unsupported operation', {
      name: 'unsupported-operation',
      operation: 'copy',
      pointer: '/forbidden_entity_image_claims',
      value: 'changed',
      error: 'unused',
    }, 'AI disclosure corpus operation is unsupported: copy'],
    ['reverse on scalar', {
      name: 'reverse-scalar',
      operation: 'reverse',
      pointer: '/revision',
      error: 'unused',
    }, 'AI disclosure corpus reverse target must be an array: /revision'],
    ['append on object', {
      name: 'append-object',
      operation: 'append',
      pointer: '/entity_ai',
      value: 'changed',
      error: 'unused',
    }, 'AI disclosure corpus append target must be an array: /entity_ai'],
  ])('rejects unsupported or mistargeted mutation: %s', (_name, rawMutation, message) => {
    const candidate = cloneDisclosure()
    const before = structuredClone(candidate)
    const mutation = rawMutation as unknown as DisclosureMutation

    expectExactError(() => applyMutation(candidate, mutation), message)
    expect(candidate).toEqual(before)
  })

  it.each(validatorCorpus)('rejects shared validator mutation: $name', (mutation) => {
    const candidate = disclosureForMutation(mutation)
    applyMutation(candidate, mutation)

    expectExactError(() => parseAiDisclosure(candidate), exactLoaderErrors[mutation.name]!)
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
