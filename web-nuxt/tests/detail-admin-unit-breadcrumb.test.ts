import { clearNuxtData } from '#app'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import EntityDetailPage from '../pages/dia-diem/[id].vue'
import { adminUnitCrumb, adminUnitLabel, withAdminUnitBreadcrumb } from '../utils/adminUnit'

/**
 * §1.6 CLAUDE.md: từ 1/7/2025 chỉ còn MỘT tỉnh Vĩnh Long, hành chính 2 cấp.
 * Mắt xích giữa của breadcrumb phải là ĐƠN VỊ HÀNH CHÍNH (xã/phường theo
 * `placeId`), không phải `area` (vùng cũ ben-tre/tra-vinh/vinh-long).
 * Breadcrumb hiển thị và JSON-LD BreadcrumbList phải KHỚP nhau.
 */

const apiFetchMock = vi.hoisted(() => vi.fn())
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))

const SITE = 'https://vinhlong360.vn'

const wrappers: Array<{ unmount: () => void }> = []

const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: String, alt: String },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})

interface DetailFixture {
  id: string
  name: string
  placeId?: string
  place_name?: string
  place_area?: string
  area?: string
  type?: string
}

function detailEntity(fixture: DetailFixture) {
  return {
    type: 'experience',
    summary: `Gioi thieu ${fixture.name}.`,
    description: `Thong tin chi tiet ve ${fixture.name}.`,
    attributes: {},
    images: [],
    ...fixture,
  }
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

async function mountDetail(entity: ReturnType<typeof detailEntity>, backendJsonLd: unknown = null) {
  apiFetchMock.mockImplementation((url: unknown) => {
    const path = String(url)
    if (path.startsWith('/seo/jsonld/')) return Promise.resolve(backendJsonLd)
    const match = path.match(/^\/api\/entities\/([^/?]+)(?:\/(gallery|relationships))?/)
    if (match) {
      if (match[2] === 'gallery') return Promise.resolve({ images: [] })
      if (match[2] === 'relationships') return Promise.resolve({ relationships: [], total: 0 })
      if (decodeURIComponent(match[1] || '') === entity.id) return Promise.resolve(entity)
    }
    return Promise.resolve({})
  })

  const wrapper = await mountSuspended(EntityDetailPage, {
    route: `/dia-diem/${entity.id}`,
    global: {
      stubs: {
        NuxtImg: NuxtImgStub,
        SaveButton: true,
        ShareButton: true,
        IconLine: { props: ['name'], template: '<i :data-icon="name" />' },
        EntityMap: true,
        EntityFeed: true,
        ReviewSection: true,
        JourneyBar: true,
        AIBestTime: true,
        ContactWidget: true,
        LazyContactWidget: true,
      },
    },
  })
  wrappers.push(wrapper)
  await flushUi()
  return wrapper
}

function breadcrumbTrail(wrapper: { findAll: (selector: string) => Array<{ text: () => string }> }) {
  return wrapper.findAll('nav.breadcrumb ol li').map(li => li.text())
}

function headBreadcrumbList(): Record<string, any> | undefined {
  const payloads = [...document.head.querySelectorAll('script[type="application/ld+json"]')]
    .map(script => {
      try { return JSON.parse(script.textContent || '{}') } catch { return {} }
    })
  const flat: any[] = []
  const walk = (node: any) => {
    if (!node || typeof node !== 'object') return
    if (Array.isArray(node)) { node.forEach(walk); return }
    flat.push(node)
    if (Array.isArray(node['@graph'])) node['@graph'].forEach(walk)
    if (node.breadcrumb) walk(node.breadcrumb)
  }
  payloads.forEach(walk)
  return flat.find(node => node['@type'] === 'BreadcrumbList')
}

afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  document.head.querySelectorAll('script[type="application/ld+json"]').forEach(node => node.remove())
  vi.restoreAllMocks()
  apiFetchMock.mockReset()
  await clearNuxtData()
})

describe('adminUnitLabel', () => {
  it('prefixes phường with "P." and keeps xã spelled out', () => {
    expect(adminUnitLabel('Phường An Hội')).toBe('P. An Hội')
    expect(adminUnitLabel('Phường Bến Tre')).toBe('P. Bến Tre')
    expect(adminUnitLabel('Xã Long Hòa')).toBe('Xã Long Hòa')
    expect(adminUnitLabel('Xã Thạnh Phong')).toBe('Xã Thạnh Phong')
  })

  it('drops the province prefix so no defunct tier reaches the trail', () => {
    expect(adminUnitLabel('Tỉnh Vĩnh Long')).toBe('Vĩnh Long')
  })

  it('lets an explicit level win over the name prefix', () => {
    expect(adminUnitLabel('An Hội', 'phuong')).toBe('P. An Hội')
    expect(adminUnitLabel('Long Hòa', 'xa')).toBe('Xã Long Hòa')
  })

  it('never yields an empty or "undefined" label for a real name', () => {
    expect(adminUnitLabel('  Phường   An   Hội  ')).toBe('P. An Hội')
    expect(adminUnitLabel('An Hội')).toBe('An Hội')
    expect(adminUnitLabel(undefined)).toBe('')
    expect(adminUnitLabel(null)).toBe('')
    expect(adminUnitLabel('   ')).toBe('')
  })
})

describe('adminUnitCrumb fallbacks', () => {
  it('links a resolved ward to its xã/phường page', () => {
    expect(adminUnitCrumb({ id: 'cho-ben-tre', placeId: 'p-an-hoi', place_name: 'Phường An Hội' }))
      .toEqual({ label: 'P. An Hội', to: '/xa-phuong/p-an-hoi' })
  })

  it('drops the tier when placeId is missing', () => {
    expect(adminUnitCrumb({ id: 'x', place_area: 'ben-tre' } as any)).toBeNull()
  })

  it('drops the tier when placeId points at an id that does not exist', () => {
    // Backend chỉ gắn place_name khi tra được place; placeId chết → không có place_name.
    expect(adminUnitCrumb({ id: 'x', placeId: 'p-khong-ton-tai' })).toBeNull()
  })

  it('drops the self-referential tier on a place entity', () => {
    expect(adminUnitCrumb({ id: 'p-an-hoi', placeId: 'p-an-hoi', place_name: 'Phường An Hội' })).toBeNull()
  })

  it('never puts a ward above a place entity, even when its placeId points elsewhere', () => {
    // 39/125 place trong web/data.json có placeId ≠ id (32 trỏ nhầm p-long-chau)
    // — trang "Xã An Bình" không được đội mắt xích "P. Long Châu".
    expect(adminUnitCrumb({
      id: 'xa-an-binh',
      type: 'place',
      placeId: 'p-long-chau',
      place_name: 'Phường Long Châu',
    })).toBeNull()
  })

  it('keeps the label unlinked when the name resolved without an id', () => {
    expect(adminUnitCrumb({ id: 'x', place_name: 'Xã Long Hòa' }))
      .toEqual({ label: 'Xã Long Hòa', to: '' })
  })

  it('encodes ids that are unsafe in a path', () => {
    expect(adminUnitCrumb({ id: 'x', placeId: 'p a/b', place_name: 'Phường A' })?.to)
      .toBe('/xa-phuong/p%20a%2Fb')
  })
})

describe('withAdminUnitBreadcrumb', () => {
  const areaPayload = () => ({
    '@context': 'https://schema.org',
    '@type': 'TouristAttraction',
    name: 'Chợ Bến Tre',
    breadcrumb: {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE}/` },
        { '@type': 'ListItem', position: 2, name: 'Du lịch', item: `${SITE}/du-lich` },
        { '@type': 'ListItem', position: 3, name: 'Bến Tre', item: `${SITE}/khu-vuc/ben-tre` },
        { '@type': 'ListItem', position: 4, name: 'Chợ Bến Tre', item: `${SITE}/dia-diem/cho-ben-tre` },
      ],
    },
  })

  const crumb = { label: 'P. An Hội', to: '/xa-phuong/p-an-hoi' }

  it('replaces the defunct area tier with the ward tier and renumbers', () => {
    const out: any = withAdminUnitBreadcrumb(areaPayload(), crumb)
    expect(out.breadcrumb.itemListElement).toEqual([
      { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE}/` },
      { '@type': 'ListItem', position: 2, name: 'Du lịch', item: `${SITE}/du-lich` },
      { '@type': 'ListItem', position: 3, name: 'P. An Hội', item: `${SITE}/xa-phuong/p-an-hoi` },
      { '@type': 'ListItem', position: 4, name: 'Chợ Bến Tre', item: `${SITE}/dia-diem/cho-ben-tre` },
    ])
    expect(JSON.stringify(out)).not.toContain('/khu-vuc/')
  })

  it('drops the area tier entirely when no ward can be resolved', () => {
    const out: any = withAdminUnitBreadcrumb(areaPayload(), null)
    expect(out.breadcrumb.itemListElement.map((i: any) => i.name)).toEqual(['Trang chủ', 'Du lịch', 'Chợ Bến Tre'])
    expect(out.breadcrumb.itemListElement.map((i: any) => i.position)).toEqual([1, 2, 3])
  })

  it('inserts the ward tier when the backend emitted none', () => {
    const payload = {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE}/` },
        { '@type': 'ListItem', position: 2, name: 'Chợ Bến Tre', item: `${SITE}/dia-diem/cho-ben-tre` },
      ],
    }
    const out: any = withAdminUnitBreadcrumb(payload, crumb)
    expect(out.itemListElement.map((i: any) => i.name)).toEqual(['Trang chủ', 'P. An Hội', 'Chợ Bến Tre'])
  })

  it('reaches BreadcrumbList nested inside an @graph', () => {
    const out: any = withAdminUnitBreadcrumb({ '@context': 'https://schema.org', '@graph': [areaPayload()] }, crumb)
    expect(out['@graph'][0].breadcrumb.itemListElement[2].name).toBe('P. An Hội')
  })

  it('is idempotent on an already-correct payload', () => {
    const once = withAdminUnitBreadcrumb(areaPayload(), crumb)
    expect(withAdminUnitBreadcrumb(once, crumb)).toEqual(once)
  })

  it('keeps the /xa-phuong catalog tier — only a specific ward tier is replaceable', () => {
    const payload = {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE}/` },
        { '@type': 'ListItem', position: 2, name: 'Xã/Phường', item: `${SITE}/xa-phuong` },
        { '@type': 'ListItem', position: 3, name: 'Phường An Hội', item: `${SITE}/dia-diem/p-an-hoi` },
      ],
    }
    expect(withAdminUnitBreadcrumb(payload, null)).toEqual(payload)
  })

  it('leaves payloads without a breadcrumb untouched', () => {
    const payload = { '@type': 'TouristAttraction', name: 'Chợ Bến Tre' }
    expect(withAdminUnitBreadcrumb(payload, crumb)).toEqual(payload)
    expect(withAdminUnitBreadcrumb(null, crumb)).toBeNull()
  })
})

describe('entity detail breadcrumb walks the administrative unit', () => {
  it('shows "P. <ward>" instead of the defunct area tier', async () => {
    const wrapper = await mountDetail(detailEntity({
      id: 'cho-ben-tre',
      name: 'Chợ Bến Tre',
      placeId: 'p-an-hoi',
      place_name: 'Phường An Hội',
      place_area: 'ben-tre',
      area: 'ben-tre',
    }))

    expect(breadcrumbTrail(wrapper as any)).toEqual(['Trang chủ', 'Trải nghiệm', 'P. An Hội', 'Chợ Bến Tre'])
    const wardLink = wrapper.get('nav.breadcrumb ol li:nth-child(3) a')
    expect(wardLink.attributes('href')).toBe('/xa-phuong/p-an-hoi')
    expect(wrapper.get('nav.breadcrumb').html()).not.toContain('/khu-vuc/')
  })

  it('spells out a xã tier without the "P." prefix', async () => {
    const wrapper = await mountDetail(detailEntity({
      id: 'vuon-dua-long-hoa',
      name: 'Vườn dừa Long Hòa',
      placeId: 'x-long-hoa',
      place_name: 'Xã Long Hòa',
      place_area: 'ben-tre',
    }))

    expect(breadcrumbTrail(wrapper as any)).toEqual(['Trang chủ', 'Trải nghiệm', 'Xã Long Hòa', 'Vườn dừa Long Hòa'])
  })

  it('drops the tier — never renders an empty crumb — when placeId is missing', async () => {
    const wrapper = await mountDetail(detailEntity({
      id: 'khong-co-place',
      name: 'Điểm chưa gán xã',
      place_area: 'ben-tre',
      area: 'ben-tre',
    }))

    expect(breadcrumbTrail(wrapper as any)).toEqual(['Trang chủ', 'Trải nghiệm', 'Điểm chưa gán xã'])
    const html = wrapper.get('nav.breadcrumb').html()
    expect(html).not.toContain('undefined')
    expect(html).not.toContain('/khu-vuc/')
  })

  it('drops the tier when placeId points at an id that does not exist', async () => {
    const wrapper = await mountDetail(detailEntity({
      id: 'place-id-chet',
      name: 'Điểm có placeId chết',
      placeId: 'p-khong-ton-tai',
      place_area: 'ben-tre',
    }))

    expect(breadcrumbTrail(wrapper as any)).toEqual(['Trang chủ', 'Trải nghiệm', 'Điểm có placeId chết'])
    expect(wrapper.get('nav.breadcrumb').html()).not.toContain('undefined')
  })

  it('renders a place entity without a ward tier above itself', async () => {
    const wrapper = await mountDetail(detailEntity({
      id: 'xa-an-binh',
      name: 'Xã An Bình',
      type: 'place',
      placeId: 'p-long-chau',
      place_name: 'Phường Long Châu',
      place_area: 'vinh-long',
    }))

    expect(breadcrumbTrail(wrapper as any)).toEqual(['Trang chủ', 'Xã/Phường', 'Xã An Bình'])
    expect(wrapper.get('nav.breadcrumb').html()).not.toContain('Long Châu')
  })

  it('keeps the fallback JSON-LD BreadcrumbList in step with the rendered trail', async () => {
    const wrapper = await mountDetail(detailEntity({
      id: 'cho-ben-tre',
      name: 'Chợ Bến Tre',
      placeId: 'p-an-hoi',
      place_name: 'Phường An Hội',
      place_area: 'ben-tre',
    }))

    const list = headBreadcrumbList()
    expect(list).toBeDefined()
    expect(list!.itemListElement.map((i: any) => i.name)).toEqual(breadcrumbTrail(wrapper as any))
    expect(list!.itemListElement[2].item).toBe(`${SITE}/xa-phuong/p-an-hoi`)
    expect(list!.itemListElement.map((i: any) => i.position)).toEqual([1, 2, 3, 4])
  })

  it('rewrites the backend BreadcrumbList so structured data cannot drift from the page', async () => {
    const wrapper = await mountDetail(
      detailEntity({
        id: 'cho-ben-tre',
        name: 'Chợ Bến Tre',
        placeId: 'p-an-hoi',
        place_name: 'Phường An Hội',
        place_area: 'ben-tre',
      }),
      {
        '@context': 'https://schema.org',
        '@type': 'TouristAttraction',
        name: 'Chợ Bến Tre',
        breadcrumb: {
          '@type': 'BreadcrumbList',
          itemListElement: [
            { '@type': 'ListItem', position: 1, name: 'Trang chủ', item: `${SITE}/` },
            { '@type': 'ListItem', position: 2, name: 'Trải nghiệm', item: `${SITE}/du-lich` },
            { '@type': 'ListItem', position: 3, name: 'Bến Tre', item: `${SITE}/khu-vuc/ben-tre` },
            { '@type': 'ListItem', position: 4, name: 'Chợ Bến Tre', item: `${SITE}/dia-diem/cho-ben-tre` },
          ],
        },
      },
    )

    const list = headBreadcrumbList()
    expect(list).toBeDefined()
    expect(list!.itemListElement.map((i: any) => i.name)).toEqual(breadcrumbTrail(wrapper as any))
    expect(list!.itemListElement[2]).toEqual({
      '@type': 'ListItem',
      position: 3,
      name: 'P. An Hội',
      item: `${SITE}/xa-phuong/p-an-hoi`,
    })
  })
})
