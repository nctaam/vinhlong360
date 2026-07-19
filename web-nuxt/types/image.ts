export interface ImageDescriptor {
  url: string | null
  alt: string
  source_class: 'ai-generated' | 'placeholder' | 'user-uploaded'
  source_kind: 'entity-editorial' | 'generated-placeholder' | 'review-ugc' | 'post-ugc'
  disclosure_key: 'entity-ai' | 'entity-placeholder' | 'ugc-photo'
  short_label: string | null
  full_disclosure: string
  credit: string | null
  width: number | null
  height: number | null
}
