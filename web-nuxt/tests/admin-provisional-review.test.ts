import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import ProvisionalReviewPage from '../pages/admin/duyet-tu-hoc.vue'

const mocks = vi.hoisted(() => ({
  authHeaders: vi.fn(() => ({ 'X-Admin-Key': 'test-key' })),
  confirmDialog: vi.fn(() => Promise.resolve(true)),
  fetch: vi.fn(),
  fetchMe: vi.fn(() => Promise.resolve()),
  showToast: vi.fn(),
}))

mockNuxtImport('useAuth', () => () => ({
  authHeaders: mocks.authHeaders,
  fetchMe: mocks.fetchMe,
  user: { value: null },
}))
mockNuxtImport('useConfirm', () => () => ({ confirmDialog: mocks.confirmDialog }))
mockNuxtImport('useToast', () => () => ({ show: mocks.showToast }))

const page = readFileSync(resolve(process.cwd(), 'pages/admin/duyet-tu-hoc.vue'), 'utf8')
  .replaceAll('\r\n', '\n')

const longSummary = `Nội dung đầy đủ cần duyệt ${'rất dài '.repeat(30)}<img src=x onerror=alert(1)>`
const review = {
  id: 'prov-mounted',
  review_token: 'a'.repeat(64),
  entity: {
    id: 'prov-mounted',
    name: 'Entity thử nghiệm',
    type: 'attraction',
    summary: longSummary,
    source: { title: 'Nguồn object', entries: ['mảng nguồn', 'chuỗi nguồn'] },
    coordinates: [10.253, 106.012],
    images: ['https://safe.example/image.webp', 'javascript:alert(1)', { label: '<script>bad</script>' }],
    attributes: { phone: '0900000000', address: '12 đường Thử Nghiệm' },
    address: '12 đường Thử Nghiệm, Vĩnh Long',
    area: 'vinh-long',
    placeId: 'phuong-thanh-duc',
    provider_trace_id: 'uncommon-provider-field',
  },
}

function approveButton(wrapper: Awaited<ReturnType<typeof mountSuspended>>) {
  const button = wrapper.findAll('button').find((item: { text: () => string }) => item.text() === 'Duyệt')
  if (!button) throw new Error('Approve button not found')
  return button
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
}

beforeEach(() => {
  mocks.authHeaders.mockClear()
  mocks.confirmDialog.mockClear()
  mocks.confirmDialog.mockResolvedValue(true)
  mocks.fetch.mockReset()
  mocks.fetchMe.mockClear()
  mocks.showToast.mockClear()
  vi.stubGlobal('$fetch', mocks.fetch)
})

describe('admin provisional review snapshot', () => {
  it('uses the explicit review envelope and complete entity snapshot', () => {
    expect(page).toContain('interface ProvisionalEntitySnapshot')
    expect(page).toContain('interface ProvisionalReview')
    expect(page).toContain('ref<ProvisionalReview[]>([])')
    expect(page).not.toContain('as Entity[]')
    expect(page).toContain('e.entity')
  })

  it('keeps explicit review types and lazy snapshot rendering', () => {
    expect(page).toContain('e.entity.summary')
    expect(page).toContain('expandedSnapshots.has(e.id)')
  })

  it('mounts the page, renders safe complete review content, and submits the exact token', async () => {
    mocks.fetch
      .mockResolvedValueOnce({ provisional: [review] })
      .mockResolvedValueOnce({ ok: true })

    const wrapper = await mountSuspended(ProvisionalReviewPage)
    await flushUi()

    expect(wrapper.text()).toContain(longSummary)
    expect(wrapper.text()).toContain('Nguồn object')
    expect(wrapper.text()).toContain('mảng nguồn')
    expect(wrapper.text()).toContain('10.253')
    expect(wrapper.text()).toContain('0900000000')
    expect(wrapper.text()).toContain('javascript:alert(1)')
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.findAll('a').map(link => link.attributes('href')).filter(Boolean)).toEqual([
      'https://safe.example/image.webp',
    ])

    const details = wrapper.get('details')
    expect(details.text()).not.toContain('uncommon-provider-field')
    ;(details.element as HTMLDetailsElement).open = true
    await details.trigger('toggle')
    expect(details.text()).toContain('uncommon-provider-field')

    await approveButton(wrapper).trigger('click')
    await flushUi()

    expect(mocks.fetch).toHaveBeenNthCalledWith(2, '/admin-api/provisional/prov-mounted/approve', {
      method: 'POST',
      headers: { 'X-Admin-Key': 'test-key' },
      body: { review_token: 'a'.repeat(64) },
    })
  })

  it('keeps the stale card visible until the refreshed snapshot arrives', async () => {
    let resolveRefresh: (value: unknown) => void = () => undefined
    const refresh = new Promise(resolve => { resolveRefresh = resolve })
    const refreshedReview = {
      ...review,
      review_token: 'b'.repeat(64),
      entity: { ...review.entity, attributes: { ...review.entity.attributes, phone: '0911111111' } },
    }
    mocks.fetch
      .mockResolvedValueOnce({ provisional: [review] })
      .mockRejectedValueOnce({ response: { status: 409, _data: { detail: 'stale_review' } } })
      .mockReturnValueOnce(refresh)

    const wrapper = await mountSuspended(ProvisionalReviewPage)
    await flushUi()
    await approveButton(wrapper).trigger('click')
    await flushUi()

    expect(wrapper.text()).toContain('0900000000')
    expect(mocks.showToast).toHaveBeenCalledWith(
      'Dữ liệu đã thay đổi. Vui lòng xem lại snapshot mới trước khi duyệt.',
      'error',
    )

    resolveRefresh({ provisional: [refreshedReview] })
    await flushUi()

    expect(wrapper.text()).toContain('0911111111')
    expect(wrapper.text()).not.toContain('0900000000')
  })
})
