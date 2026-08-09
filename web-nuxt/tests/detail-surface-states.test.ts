import { mountSuspended } from '@nuxt/test-utils/runtime'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'

import EntityTrustPanel from '../components/EntityTrustPanel.vue'
import FramedDossier from '../components/FramedDossier.vue'
import KnowBeforeYouGo from '../components/KnowBeforeYouGo.vue'

const wrappers: Array<{ unmount: () => void }> = []
const wardDetailSource = readFileSync(resolve(process.cwd(), 'pages/xa-phuong/[id].vue'), 'utf8')

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
})

describe('detail dossier surface states', () => {
  it('keeps supplied content usable when media is partial', async () => {
    const wrapper = await mountSuspended(FramedDossier, {
      props: {
        title: 'Chợ Bến Tre',
        mediaStatus: 'partial',
      },
      slots: {
        summary: '<p data-summary>Thông tin chính vẫn dùng được.</p>',
        facts: '<dl data-facts><dt>Địa chỉ</dt><dd>Phường An Hội</dd></dl>',
      },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[data-dossier-media-state="partial"]').text()).toContain('Hình ảnh chưa tải được')
    expect(wrapper.get('[data-summary]').text()).toContain('vẫn dùng được')
    expect(wrapper.get('[data-facts] dd').text()).toBe('Phường An Hội')
  })

  it('keeps the mobile dossier sequence stable and marks the action safe area', async () => {
    const wrapper = await mountSuspended(FramedDossier, {
      props: { title: 'Nhà cổ ven sông', actionSafeArea: true },
      slots: {
        trust: '<p>Nguồn và cập nhật</p>',
        action: '<a href="/ban-do">Chỉ đường</a>',
        facts: '<dl><dt>Giờ</dt><dd>08:00</dd></dl>',
        default: '<p>Câu chuyện địa phương</p>',
        related: '<a href="/du-lich">Điểm gần đây</a>',
      },
    })
    wrappers.push(wrapper)

    expect(wrapper.findAll('[data-dossier-region]').map(node => node.attributes('data-dossier-region'))).toEqual([
      'identity',
      'trust',
      'action',
      'facts',
      'narrative',
      'related',
    ])
    expect(wrapper.get('[data-dossier-region="action"]').attributes('data-safe-area')).toBe('bottom')
  })

  it('shows stale source evidence without hiding supplied facts', async () => {
    const wrapper = await mountSuspended(EntityTrustPanel, {
      props: {
        tier: 'official',
        sourceTitle: 'Cổng thông tin tỉnh',
        sourceUrl: 'https://example.gov.vn/place',
        freshnessStatus: 'stale',
        updatedLabel: '12/07/2026',
        note: 'Kiểm tra lại trước khi đi.',
        reportTo: '/cong-dong?report=place',
      },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[data-source-mark]').text()).toContain('Chính thức')
    expect(wrapper.get('[data-freshness-line]').text()).toContain('Có thể đã cũ')
    expect(wrapper.text()).toContain('Cổng thông tin tỉnh')
    expect(wrapper.findAll('[data-report-action]')).toHaveLength(1)
  })

  it('renders every supplied conflict value with its source and time', async () => {
    const wrapper = await mountSuspended(EntityTrustPanel, {
      props: {
        tier: 'community',
        sourceTitle: 'Nguồn tổng hợp',
        freshnessStatus: 'conflict',
        updatedLabel: '',
        note: 'Các nguồn đang ghi khác nhau.',
        reportTo: '/cong-dong?report=place',
        conflicts: [
          { label: 'Giờ mở cửa', value: '07:00', sourceTitle: 'Trang đơn vị', updatedLabel: '01/08/2026' },
          { label: 'Giờ mở cửa', value: '08:00', sourceTitle: 'Danh bạ cộng đồng', updatedLabel: '02/08/2026' },
        ],
      },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    const conflicts = wrapper.get('[data-source-conflicts]')
    expect(conflicts.findAll('dd').map(node => node.text())).toEqual([
      '07:00 · Trang đơn vị · 01/08/2026',
      '08:00 · Danh bạ cộng đồng · 02/08/2026',
    ])
    expect(wrapper.get('[data-freshness-line]').text()).toContain('Thông tin có mâu thuẫn')
  })

  it('renders time-sensitive practical facts as a definition list with evidence', async () => {
    const wrapper = await mountSuspended(KnowBeforeYouGo, {
      props: {
        attributes: {
          golden_hours: '06:00-08:00',
          peak_days: 'Cuối tuần',
          crowd_level: 'Đông vừa',
        },
        entityType: 'attraction',
        sourceTier: 'official',
        freshnessStatus: 'aging',
        updatedLabel: '31/07/2026',
      },
      global: { stubs: { IconLine: true } },
    })
    wrappers.push(wrapper)

    const facts = wrapper.get('dl[data-kbyg-facts]')
    expect(facts.findAll('dt').map(node => node.text())).toEqual(['Giờ vàng', 'Ngày đông', 'Mức đông'])
    expect(facts.findAll('dd').map(node => node.text())).toEqual(['06:00-08:00', 'Cuối tuần', 'Đông vừa'])
    expect(wrapper.get('[data-kbyg-evidence] [data-source-mark]').text()).toContain('Chính thức')
    expect(wrapper.get('[data-kbyg-evidence] [data-freshness-line]').text()).toContain('Cần kiểm tra định kỳ')
  })

  it('keeps ward transport failures retryable and reserves 404 for a confirmed not_found', () => {
    expect(wardDetailSource).toContain('readonly error: unknown | null')
    expect(wardDetailSource).toContain('resolveDetailFetchError')
    expect(wardDetailSource).toContain("wardFetchResolution.value?.kind === 'not_found'")
    expect(wardDetailSource).toContain('<PageState')
    expect(wardDetailSource).not.toContain('catch {\n    return { generation, requestId, overview: null, failed: true }')
  })

  it('declares the ward mobile dossier regions in identity-to-related order', () => {
    const regions = ['identity', 'trust', 'action', 'facts', 'narrative', 'related']
    const offsets = regions.map(region => wardDetailSource.indexOf(`data-detail-region="${region}"`))

    expect(offsets.every(offset => offset >= 0)).toBe(true)
    expect(offsets).toEqual([...offsets].sort((left, right) => left - right))
    expect(wardDetailSource).toContain('data-detail-action-safe-area')
  })
})
