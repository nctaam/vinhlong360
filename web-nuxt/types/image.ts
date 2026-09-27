export interface ImageDescriptor {
  url: string | null
  alt: string
  source_class: 'ai-generated' | 'placeholder' | 'user-uploaded' | 'rights-cleared'
  source_kind: 'entity-editorial' | 'generated-placeholder' | 'review-ugc' | 'post-ugc' | 'documentary' | 'journalistic' | 'official' | 'press'
  disclosure_key: 'entity-ai' | 'entity-placeholder' | 'ugc-photo' | 'entity-sourced-photo'
  short_label: string | null
  full_disclosure: string
  credit: string | null
  source_url: string | null
  width: number | null
  height: number | null
}
