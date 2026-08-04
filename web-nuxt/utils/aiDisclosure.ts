import disclosureJson from '#launch-config/ai-disclosure.json'
import { parseAiDisclosureArtifact } from '#launch-validators'

export type AiDisclosureArtifact = {
  readonly schema_version: 1
  readonly revision: 'ai-disclosure-v1'
  readonly entity_ai: {
    readonly short_label: 'Minh h\u1ecda AI'
    readonly full_disclosure: '\u1ea2nh minh h\u1ecda do AI d\u1ef1ng \u2014 kh\u00f4ng ph\u1ea3i \u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7.'
    readonly accessible_description_key: 'entity-ai-full'
  }
  readonly placeholder: {
    readonly short_label: null
    readonly full_disclosure: 'Minh h\u1ecda \u0111\u1ed3 h\u1ecda \u2014 ch\u01b0a c\u00f3 \u1ea3nh ri\u00eang cho \u0111\u1ecba \u0111i\u1ec3m.'
    readonly accessible_description_key: 'entity-placeholder-full'
  }
  readonly ugc_photo: {
    readonly short_label: '\u1ea2nh ng\u01b0\u1eddi d\u00f9ng'
    readonly full_disclosure: '\u1ea2nh do ng\u01b0\u1eddi d\u00f9ng cung c\u1ea5p.'
    readonly accessible_description_key: 'ugc-photo-full'
  }
  readonly forbidden_entity_image_claims: readonly [
    '\u1ea3nh th\u1eadt',
    'real photo',
    'documentary photo',
    'on-site photo',
    '\u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7',
  ]
}

export function parseAiDisclosure(value: unknown): AiDisclosureArtifact {
  return parseAiDisclosureArtifact(value) as AiDisclosureArtifact
}

export const aiDisclosure = parseAiDisclosure(disclosureJson)
