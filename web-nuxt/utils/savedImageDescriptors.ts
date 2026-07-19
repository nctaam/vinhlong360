import type { ImageDescriptor } from '../types/image'
import { aiDisclosure } from './aiDisclosure'
import { describeEntityImages, describeEntityPlaceholder } from './imageDescriptors'

export const SAVED_DESCRIPTOR_REVISION = aiDisclosure.revision

const KNOWN_ENTITY_TYPES = new Set([
  'experience', 'product', 'dish', 'restaurant', 'cafe', 'craft_village',
  'attraction', 'accommodation', 'organization', 'place', 'nature', 'history',
  'event', 'economy', 'person', 'drink', 'facility',
])

type SavedImageInput = {
  name?: unknown
  kind?: unknown
  image?: unknown
  images?: unknown
  image_descriptor?: unknown
  image_descriptors?: unknown
}

export type SavedImageSnapshot = {
  image_descriptor: ImageDescriptor
  descriptor_revision: typeof SAVED_DESCRIPTOR_REVISION
}

export function isKnownEntityType(type: unknown): boolean {
  return typeof type === 'string' && KNOWN_ENTITY_TYPES.has(type.trim().toLowerCase())
}

function isKnownEditorialItem(item: SavedImageInput): boolean {
  if (typeof item.kind === 'string' && item.kind.trim()) {
    return item.kind.trim().toLowerCase() === 'entity'
  }
  return isKnownEntityType((item as SavedImageInput & { type?: unknown }).type)
}

function isGeneratedPlaceholderUrl(value: unknown): boolean {
  if (typeof value !== 'string') return false
  const url = value.trim()
  return /^url\(\s*['"]?data:image\/svg\+xml,/i.test(url)
    || /^data:image\/svg\+xml,/i.test(url)
}

function hasStructuredDescriptor(item: SavedImageInput): boolean {
  return Object.prototype.hasOwnProperty.call(item, 'image_descriptor')
    || Object.prototype.hasOwnProperty.call(item, 'image_descriptors')
}

/** Normalize thin saved/recent snapshots without guessing provenance for raw UGC. */
export function normalizeSavedImageSnapshot<T extends object>(item: T & SavedImageInput): Omit<T, 'image' | 'images' | 'image_descriptors'> & SavedImageSnapshot {
  const normalized = { ...item } as Record<string, unknown>
  const descriptorSource = { ...item } as SavedImageInput
  delete normalized.image
  delete normalized.images
  delete normalized.image_descriptors
  delete normalized.descriptor_revision

  const supplied = hasStructuredDescriptor(descriptorSource)
    ? describeEntityImages(descriptorSource)[0]
    : null
  const rawLegacy = descriptorSource.image
  const legacy = !hasStructuredDescriptor(descriptorSource) && isKnownEditorialItem(descriptorSource)
    && !isGeneratedPlaceholderUrl(rawLegacy)
    ? describeEntityImages(descriptorSource)[0]
    : null
  const descriptor = supplied || legacy || describeEntityPlaceholder(descriptorSource)

  normalized.image_descriptor = descriptor
  normalized.descriptor_revision = SAVED_DESCRIPTOR_REVISION
  return normalized as Omit<T, 'image' | 'images' | 'image_descriptors'> & SavedImageSnapshot
}
