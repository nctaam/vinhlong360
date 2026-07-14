import disclosureJson from '#launch-config/ai-disclosure.json'

const ROOT_KEYS = [
  'entity_ai',
  'forbidden_entity_image_claims',
  'placeholder',
  'revision',
  'schema_version',
  'ugc_photo',
] as const
const COPY_KEYS = ['accessible_description_key', 'full_disclosure', 'short_label'] as const

function deepFreeze<T>(value: T): T {
  if (value !== null && typeof value === 'object' && !Object.isFrozen(value)) {
    Object.freeze(value)
    for (const child of Object.values(value as Record<string, unknown>)) {
      deepFreeze(child)
    }
  }
  return value
}

const CANONICAL_DISCLOSURE = deepFreeze({
  schema_version: 1,
  revision: 'ai-disclosure-v1',
  entity_ai: {
    short_label: 'Minh h\u1ecda AI',
    full_disclosure: '\u1ea2nh minh h\u1ecda do AI d\u1ef1ng \u2014 kh\u00f4ng ph\u1ea3i \u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7.',
    accessible_description_key: 'entity-ai-full',
  },
  placeholder: {
    short_label: null,
    full_disclosure: 'Minh h\u1ecda \u0111\u1ed3 h\u1ecda \u2014 ch\u01b0a c\u00f3 \u1ea3nh ri\u00eang cho \u0111\u1ecba \u0111i\u1ec3m.',
    accessible_description_key: 'entity-placeholder-full',
  },
  ugc_photo: {
    short_label: '\u1ea2nh ng\u01b0\u1eddi d\u00f9ng',
    full_disclosure: '\u1ea2nh do ng\u01b0\u1eddi d\u00f9ng cung c\u1ea5p.',
    accessible_description_key: 'ugc-photo-full',
  },
  forbidden_entity_image_claims: [
    '\u1ea3nh th\u1eadt',
    'real photo',
    'documentary photo',
    'on-site photo',
    '\u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7',
  ],
} as const)

export type AiDisclosureArtifact = typeof CANONICAL_DISCLOSURE

function plainRecord(value: unknown, label: string): Record<string, unknown> {
  if (
    value === null
    || typeof value !== 'object'
    || Array.isArray(value)
    || Object.getPrototypeOf(value) !== Object.prototype
  ) {
    throw new Error(`canonical AI disclosure ${label} must be a plain JSON object`)
  }
  return value as Record<string, unknown>
}

function exactKeys(
  value: Record<string, unknown>,
  expectedKeys: readonly string[],
  label: string,
): void {
  const actual: string[] = []
  for (const key of Reflect.ownKeys(value)) {
    const descriptor = Object.getOwnPropertyDescriptor(value, key)
    if (typeof key !== 'string' || !descriptor?.enumerable || !('value' in descriptor)) {
      throw new Error(`canonical AI disclosure ${label} keys mismatch`)
    }
    actual.push(key)
  }
  actual.sort()
  const expected = [...expectedKeys].sort()
  if (actual.join('\0') !== expected.join('\0')) {
    throw new Error(`canonical AI disclosure ${label} keys mismatch`)
  }
}

function plainDenseArray(value: unknown, label: string): unknown[] {
  if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype) {
    throw new Error(`canonical AI disclosure ${label} must be a plain dense JSON array`)
  }

  const ownKeys = Reflect.ownKeys(value)
  if (ownKeys.length !== value.length + 1 || !ownKeys.includes('length')) {
    throw new Error(`canonical AI disclosure ${label} must be a plain dense JSON array`)
  }
  for (let index = 0; index < value.length; index += 1) {
    const descriptor = Object.getOwnPropertyDescriptor(value, String(index))
    if (!descriptor?.enumerable || !('value' in descriptor)) {
      throw new Error(`canonical AI disclosure ${label} must be a plain dense JSON array`)
    }
  }
  return value
}

function assertExactCopy(
  value: unknown,
  expected: Readonly<Record<string, unknown>>,
  label: string,
): void {
  const copy = plainRecord(value, label)
  exactKeys(copy, COPY_KEYS, label)
  if (Object.entries(expected).some(([key, expectedValue]) => copy[key] !== expectedValue)) {
    throw new Error(`canonical AI disclosure ${label} mismatch`)
  }
}

function assertForbiddenClaims(value: unknown): void {
  const claims = plainDenseArray(value, 'forbidden claims')
  const expected = CANONICAL_DISCLOSURE.forbidden_entity_image_claims
  if (
    claims.length !== expected.length
    || claims.some((claim, index) => claim !== expected[index])
  ) {
    throw new Error('canonical AI disclosure forbidden claims mismatch')
  }
}

export function parseAiDisclosure(value: unknown): AiDisclosureArtifact {
  const disclosure = plainRecord(value, 'root')
  exactKeys(disclosure, ROOT_KEYS, 'root')

  if (disclosure.schema_version !== CANONICAL_DISCLOSURE.schema_version) {
    throw new Error('canonical AI disclosure schema_version mismatch')
  }
  if (disclosure.revision !== CANONICAL_DISCLOSURE.revision) {
    throw new Error('canonical AI disclosure revision mismatch')
  }

  assertExactCopy(disclosure.entity_ai, CANONICAL_DISCLOSURE.entity_ai, 'entity_ai')
  assertExactCopy(disclosure.placeholder, CANONICAL_DISCLOSURE.placeholder, 'placeholder')
  assertExactCopy(disclosure.ugc_photo, CANONICAL_DISCLOSURE.ugc_photo, 'ugc_photo')
  assertForbiddenClaims(disclosure.forbidden_entity_image_claims)

  const parsed: AiDisclosureArtifact = {
    schema_version: CANONICAL_DISCLOSURE.schema_version,
    revision: CANONICAL_DISCLOSURE.revision,
    entity_ai: { ...CANONICAL_DISCLOSURE.entity_ai },
    placeholder: { ...CANONICAL_DISCLOSURE.placeholder },
    ugc_photo: { ...CANONICAL_DISCLOSURE.ugc_photo },
    forbidden_entity_image_claims: [
      CANONICAL_DISCLOSURE.forbidden_entity_image_claims[0],
      CANONICAL_DISCLOSURE.forbidden_entity_image_claims[1],
      CANONICAL_DISCLOSURE.forbidden_entity_image_claims[2],
      CANONICAL_DISCLOSURE.forbidden_entity_image_claims[3],
      CANONICAL_DISCLOSURE.forbidden_entity_image_claims[4],
    ],
  }
  return deepFreeze(parsed)
}

export const aiDisclosure = parseAiDisclosure(disclosureJson)
