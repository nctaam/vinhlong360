import { describe, it, expect } from 'vitest'
import { buildEntityDetailSchemaGraph } from '../composables/useSeoHelpers'

describe('Google Images License structured data (AEO / Search Central)', () => {
  it('generates ImageObject with creator, creditText, license, and acquireLicensePage for verified photos', () => {
    const entity = {
      id: 'le-hoi-ok-om-bok',
      name: 'Lễ hội Ok Om Bok',
      type: 'event',
      images: ['/img/entities/le-hoi-ok-om-bok.webp'],
      attributes: {
        date_start: '2026-11-23',
        date_end: '2026-11-25',
        image_author: 'Bá Thi',
        image_source: 'Báo Trà Vinh',
        image_type: 'documentary',
        is_verified_photo: true,
      },
    }
    const heroDescriptor = {
      url: '/img/entities/le-hoi-ok-om-bok.webp',
      alt: 'Lễ hội Ok Om Bok — ảnh minh họa',
      source_class: 'ai-generated' as const,
      source_kind: 'entity-editorial' as const,
      disclosure_key: 'entity-ai' as const,
      short_label: 'Ảnh AI',
      full_disclosure: 'Ảnh tư liệu báo chí',
      credit: null,
      width: null,
      height: null,
    }
    const graph = buildEntityDetailSchemaGraph({
      entity,
      heroDescriptor,
      areaName: 'Trà Vinh',
    })

    expect(graph).not.toBeNull()
    const entityNode = graph?.['@graph']?.find((node: any) => node['@type'] === 'Event')
    expect(entityNode).toBeDefined()
    expect(entityNode.image).toBeDefined()
    expect(entityNode.image['@type']).toBe('ImageObject')
    expect(entityNode.image.creator).toEqual({ '@type': 'Person', name: 'Bá Thi' })
    expect(entityNode.image.creditText).toBe('Bá Thi · Báo Trà Vinh')
    expect(entityNode.image.copyrightNotice).toBe('Ảnh tư liệu báo chí: Bá Thi · Báo Trà Vinh')
    expect(entityNode.image.license).toBe('https://vinhlong360.vn/dieu-khoan-su-dung')
    expect(entityNode.image.acquireLicensePage).toBe('https://vinhlong360.vn/lien-he')
  })
})
