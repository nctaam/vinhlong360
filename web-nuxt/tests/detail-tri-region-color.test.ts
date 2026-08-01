import { clearNuxtData } from '#app'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { defineComponent, h, nextTick } from 'vue'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ContactWidget from '../components/ContactWidget.vue'
import EntityTrustPanel from '../components/EntityTrustPanel.vue'
import EntityDetailPage from '../pages/dia-diem/[id].vue'

const apiFetchMock = vi.hoisted(() => vi.fn())
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))

const triRegionCss = readFileSync(resolve(process.cwd(), 'assets/css/tri-region-color.css'), 'utf8')

const wrappers: Array<{ unmount: () => void }> = []
const NuxtImgStub = defineComponent({
  inheritAttrs: false,
  props: { src: String, alt: String },
  setup(props, { attrs }) {
    return () => h('img', { ...attrs, src: props.src, alt: props.alt })
  },
})

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 0))
}

afterEach(async () => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  apiFetchMock.mockReset()
  await clearNuxtData()
})

describe('entity detail tri-region behavior', () => {
  it('separates official provenance, stale severity and report action', async () => {
    const wrapper = await mountSuspended(EntityTrustPanel, {
      props: {
        tier: 'official',
        sourceTitle: 'Cổng thông tin tỉnh Vĩnh Long',
        sourceUrl: 'https://example.gov.vn/source',
        freshnessStatus: 'stale',
        updatedLabel: '12/07/2026',
        note: 'Thông tin có thể đã cũ; hãy kiểm tra trước khi đi.',
        reportTo: '/cong-dong?report=entity-1',
      },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[data-source-mark]').text()).toContain('Chính thức')
    expect(wrapper.get('[data-freshness-line]').text()).toContain('Có thể đã cũ')
    expect(wrapper.get('[data-source-link]').text()).toContain('Cổng thông tin tỉnh Vĩnh Long')
    expect(wrapper.get('[data-report-action]').attributes('href')).toBe('/cong-dong?report=entity-1')
  })

  it('keeps invalid source URLs as labels instead of unsafe links', async () => {
    const wrapper = await mountSuspended(EntityTrustPanel, {
      props: {
        tier: 'unknown',
        sourceTitle: 'Nguồn chưa được xác minh',
        sourceUrl: 'javascript:alert(1)',
        freshnessStatus: 'unknown',
        updatedLabel: '',
        note: 'Hãy kiểm tra trước khi sử dụng thông tin.',
        reportTo: '/cong-dong?report=entity-unsafe',
      },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    expect(wrapper.find('[data-source-link]').exists()).toBe(false)
    expect(wrapper.get('[data-source-label]').text()).toBe('Nguồn chưa được xác minh')
    expect(wrapper.get('[data-report-action]').attributes('href')).toBe('/cong-dong?report=entity-unsafe')
  })

  it('keeps the direct-contact model and semantic action order', async () => {
    const wrapper = await mountSuspended(ContactWidget, {
      props: {
        entity: {
          id: 'entity-1',
          name: 'Nhà vườn ven sông',
          attributes: { zalo: '0900000000', phone: '0900000000' },
        },
      },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    const actions = wrapper.findAll('.cw-btn')
    expect(actions.map(action => action.text())).toEqual(['Nhắn Zalo', 'Gọi điện'])
    expect(actions[0]!.attributes('data-color-role')).toBe('action-primary')
    expect(actions[1]!.attributes('data-color-role')).toBe('action-secondary')
    expect(wrapper.text()).not.toContain('Đặt ngay')
    expect(wrapper.text()).not.toContain('Thanh toán')
  })

  it('mounts detail data and keeps material, trust and image disclosure as separate layers', async () => {
    const entity = {
      id: 'entity-1',
      type: 'craft_village',
      name: 'Làng gốm Mang Thít',
      summary: 'Không gian nghề gốm ven sông.',
      description: 'Một làng nghề lâu đời bên dòng Cổ Chiên.',
      place_name: 'Mang Thít',
      attributes: { zalo: '0900000000', phone: '0900000000', address: 'Mang Thít, Vĩnh Long' },
      coordinates: { lat: 10.211, lng: 106.116 },
      quality: {
        source_tier: 'official',
        source_title: 'Cổng thông tin tỉnh Vĩnh Long',
        source_url: 'https://example.gov.vn/source',
      },
      source_freshness: {
        source_title: 'Cổng thông tin tỉnh Vĩnh Long',
        source_url: 'https://example.gov.vn/source',
        freshness_status: 'fresh',
        updated_at: '2026-07-30T00:00:00Z',
      },
    }
    apiFetchMock.mockImplementation((url: unknown) => {
      const path = String(url)
      if (path === '/api/entities/entity-1') return Promise.resolve(entity)
      if (path === '/api/entities/entity-1/gallery') return Promise.resolve({ images: [] })
      if (path === '/seo/jsonld/entity-1') return Promise.resolve(null)
      if (path.startsWith('/api/entities/entity-1/relationships')) return Promise.resolve({ relationships: [], total: 0 })
      return Promise.resolve({})
    })

    const wrapper = await mountSuspended(EntityDetailPage, {
      route: '/dia-diem/entity-1',
      global: {
        stubs: {
          NuxtImg: NuxtImgStub,
          Breadcrumb: true,
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

    const root = wrapper.get('[data-page-recipe="detail"]')
    expect(root.attributes('data-material-accent')).toBe('clay')
    expect(wrapper.get('[data-source-mark]').text()).toContain('Chính thức')
    expect(wrapper.get('[data-freshness-line]').text()).toContain('Mới cập nhật')
    expect(wrapper.get('[data-image-disclosure]').text()).not.toContain('Chính thức')
    expect(wrapper.get('[data-entity-trust-panel]').text()).not.toContain('Ảnh minh họa')

    const highlightActions = wrapper.findAll('.highlights .hl-action')
    expect(highlightActions.map(action => action.text())).toEqual(['💬 Zalo', '📞 Gọi', '🗺️ Bản đồ'])
    expect(highlightActions.map(action => action.attributes('data-color-role'))).toEqual([
      'action-primary',
      'action-secondary',
      'action-secondary',
    ])

    const stickyActions = wrapper.findAll('.sticky-cta-bar a')
    expect(stickyActions.map(action => action.text())).toEqual(['💬 Zalo', '📞 Gọi', '🗺️ Bản đồ'])
    expect(stickyActions.map(action => action.attributes('data-color-role'))).toEqual([
      'action-primary',
      'action-secondary',
      'action-secondary',
    ])
  })

  it('generates the material border pseudo-element for every detail hero', () => {
    const heroRule = triRegionCss.match(/\[data-color-system="tri-region-v1"\]\[data-page-recipe="detail"\] \.detail-cover::after\s*\{([^}]*)\}/)

    expect(heroRule?.[1]).toMatch(/content:\s*""/)
    expect(heroRule?.[1]).toMatch(/position:\s*absolute/)
    expect(heroRule?.[1]).toMatch(/border-block-end:\s*3px solid var\(--tri-region-material-accent\)/)
  })

  it('keeps the required page class without inheriting the legacy constrained layout', () => {
    const rootRule = triRegionCss.match(/\[data-color-system="tri-region-v1"\]\[data-page-recipe="detail"\]\.page\.entity-detail\s*\{([^}]*)\}/)

    expect(rootRule?.[1]).toMatch(/max-width:\s*none/)
    expect(rootRule?.[1]).toMatch(/margin:\s*0/)
    expect(rootRule?.[1]).toMatch(/padding:\s*0/)
  })
})
