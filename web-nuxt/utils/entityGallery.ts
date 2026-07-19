import type { ImageDescriptor } from '~/types/image'

export interface GalleryDescriptorCarrier {
  readonly requestId: string
  readonly descriptors: readonly Readonly<ImageDescriptor>[]
}

/** Hide Nuxt's previous-key seed until the gallery response belongs to this route. */
export function currentGalleryDescriptors(
  carrier: GalleryDescriptorCarrier | null | undefined,
  currentId: string,
): readonly Readonly<ImageDescriptor>[] {
  if (!carrier || carrier.requestId !== currentId) return []
  return carrier.descriptors
}
