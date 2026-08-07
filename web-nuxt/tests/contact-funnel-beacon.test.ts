/**
 * Contact-funnel beacon — CTA liên hệ phải ĐO ĐƯỢC mà KHÔNG cản người dùng.
 *
 * Backend `POST /api/entities/{id}/view-contact` (agent/public_api.py:3382) đã có
 * rate-limit + JSONL xoay vòng + `GET /admin/contact-funnel`; trước đợt này frontend
 * chưa từng gọi (grep `view-contact` trong web-nuxt/ ra 0 hit) nên không ai biết có
 * người bấm số điện thoại nào hay không.
 *
 * Ba bất biến được khoá ở đây:
 *  (a) bấm CTA thì có beacon (POST + keepalive, đúng entity id + kênh);
 *  (b) endpoint chết/lỗi mạng thì điều hướng `tel:` / bản đồ / website VẪN chạy;
 *  (c) bấm liên tiếp không gửi trùng (không đốt rate-limit 10 lượt/60s/IP).
 */
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ContactWidget from '../components/ContactWidget.vue'
import { resetContactBeaconDedupe, trackContactView } from '../composables/useContactBeacon'

const detailSource = readFileSync(resolve(process.cwd(), 'pages/dia-diem/[id].vue'), 'utf8')
const directorySource = readFileSync(resolve(process.cwd(), 'pages/danh-ba.vue'), 'utf8')

const wrappers: Array<{ unmount: () => void }> = []
let fetchMock: ReturnType<typeof vi.fn>

function stubFetch(impl: (...args: any[]) => any = () => Promise.resolve({ ok: true })) {
  fetchMock = vi.fn(impl)
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

/**
 * Click thật (cancelable) trên element và báo lại xem hành vi mặc định — tức là
 * điều hướng `tel:` / `https:` — có bị chặn không. `dispatchEvent` trả `false`
 * đúng khi có ai đó gọi `preventDefault()`.
 */
function clickAndReportNavigation(wrapper: any, selector: string) {
  const el = wrapper.get(selector).element as HTMLElement
  const event = new MouseEvent('click', { bubbles: true, cancelable: true })
  const navigationAllowed = el.dispatchEvent(event)
  return { navigationAllowed, defaultPrevented: event.defaultPrevented, href: el.getAttribute('href') }
}

async function mountWidget(attributes: Record<string, unknown>, id = 'nha-vuon-ven-song') {
  const wrapper = await mountSuspended(ContactWidget, {
    props: { entity: { id, name: 'Nhà vườn ven sông', attributes } },
    global: { stubs: { IconLine: true } },
  })
  wrappers.push(wrapper)
  return wrapper
}

beforeEach(() => {
  resetContactBeaconDedupe()
  stubFetch()
})

afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
  vi.unstubAllGlobals()
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('(a) bấm CTA liên hệ thì gửi beacon', () => {
  it('gửi POST keepalive khi bấm "Gọi điện"', async () => {
    const wrapper = await mountWidget({ phone: '0270 3822 100' })

    await wrapper.get('[data-contact-action="phone"]').trigger('click')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toBe('/api/entities/nha-vuon-ven-song/view-contact?action=phone')
    expect(init.method).toBe('POST')
    expect(init.keepalive).toBe(true)
  })

  it('gửi đúng kênh cho Website và Chỉ đường (bản đồ)', async () => {
    const withWebsite = await mountWidget({ phone: '0270 3822 100', website: 'https://vd.example/x' })
    await withWebsite.get('[data-contact-action="website"]').trigger('click')
    expect(fetchMock.mock.calls.at(-1)![0]).toBe('/api/entities/nha-vuon-ven-song/view-contact?action=website')

    // Không có phone/zalo → widget đổi sang CTA bản đồ.
    const mapOnly = await mountWidget({}, 'chua-phu-ly')
    await mapOnly.get('[data-contact-action="map"]').trigger('click')
    expect(fetchMock.mock.calls.at(-1)![0]).toBe('/api/entities/chua-phu-ly/view-contact?action=map')
  })

  it('escape id lạ và chỉ gửi entity id + kênh — KHÔNG dữ liệu cá nhân', async () => {
    trackContactView('xa/phuong 1', 'phone')

    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toBe('/api/entities/xa%2Fphuong%201/view-contact?action=phone')
    // Không cookie phiên, không body, không header thủ công (user-agent/toạ độ).
    expect(init.credentials).toBe('omit')
    expect(init.body).toBeUndefined()
    expect(init.headers).toBeUndefined()
    expect(Object.keys(init).sort()).toEqual(['credentials', 'keepalive', 'method'])
  })

  it('bỏ qua khi thiếu entity id', () => {
    expect(trackContactView('', 'phone')).toBe(false)
    expect(trackContactView(null, 'map')).toBe(false)
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('(b) endpoint lỗi thì điều hướng VẪN chạy', () => {
  it('fetch reject (mạng chết / 500) không chặn tel: và không throw', async () => {
    stubFetch(() => Promise.reject(new Error('network down')))
    const wrapper = await mountWidget({ phone: '0270 3822 100' })

    const result = clickAndReportNavigation(wrapper, '[data-contact-action="phone"]')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(result.navigationAllowed).toBe(true)
    expect(result.defaultPrevented).toBe(false)
    expect(result.href).toBe('tel:0270 3822 100')
  })

  it('fetch throw đồng bộ vẫn không chặn điều hướng', async () => {
    stubFetch(() => { throw new TypeError('Failed to fetch') })
    const wrapper = await mountWidget({ phone: '0270 3822 100', website: 'https://vd.example/x' })

    const result = clickAndReportNavigation(wrapper, '[data-contact-action="website"]')

    expect(result.navigationAllowed).toBe(true)
    expect(result.defaultPrevented).toBe(false)
    expect(result.href).toBe('https://vd.example/x')
    expect(trackContactView('bat-ky', 'phone')).toBe(false)
  })

  it('không có fetch trong runtime thì im lặng, không nổ', () => {
    vi.stubGlobal('fetch', undefined)
    expect(() => trackContactView('nha-vuon-ven-song', 'map')).not.toThrow()
  })

  it('trackContactView là đồng bộ — caller không thể await chặn điều hướng', () => {
    let resolveFetch: (v: unknown) => void = () => {}
    stubFetch(() => new Promise(res => { resolveFetch = res }))

    // Trả boolean, KHÔNG trả Promise: không có gì để await.
    const returned = trackContactView('nha-vuon-ven-song', 'phone')
    expect(returned).toBe(true)
    expect(typeof (returned as unknown as Promise<unknown>)?.then).toBe('undefined')
    resolveFetch({ ok: true })
  })
})

describe('(c) bấm liên tiếp không gửi trùng', () => {
  it('gộp các lần bấm cùng entity+kênh trong cửa sổ chống-trùng', async () => {
    const wrapper = await mountWidget({ phone: '0270 3822 100' })

    await wrapper.get('[data-contact-action="phone"]').trigger('click')
    await wrapper.get('[data-contact-action="phone"]').trigger('click')
    await wrapper.get('[data-contact-action="phone"]').trigger('click')

    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('kênh khác nhau và entity khác nhau vẫn được tính riêng', () => {
    trackContactView('a', 'phone')
    trackContactView('a', 'map')
    trackContactView('b', 'phone')
    trackContactView('a', 'phone')  // trùng → bỏ

    expect(fetchMock).toHaveBeenCalledTimes(3)
  })

  it('hết cửa sổ chống-trùng thì bấm lại được tính', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-08-07T00:00:00Z'))

    expect(trackContactView('a', 'phone')).toBe(true)
    vi.advanceTimersByTime(1999)
    expect(trackContactView('a', 'phone')).toBe(false)
    vi.advanceTimersByTime(2)
    expect(trackContactView('a', 'phone')).toBe(true)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})

describe('hợp đồng nguồn — CTA của trang chi tiết & danh bạ đã nối', () => {
  it('trang chi tiết nối beacon cho phone / map / website', () => {
    expect(detailSource).toContain("import { trackContactView, type ContactAction } from '~/composables/useContactBeacon'")
    for (const [action, count] of [['phone', 3], ['map', 2], ['website', 2]] as const) {
      const wired = detailSource.match(new RegExp(`data-contact-action="${action}"[^>]*@click="trackContact\\('${action}'\\)"`, 'g')) || []
      expect(wired.length, `${action} CTA đã nối`).toBe(count)
    }
  })

  it('trang danh bạ nối beacon cho số điện thoại cơ quan', () => {
    expect(directorySource).toContain("import { trackContactView } from '~/composables/useContactBeacon'")
    expect(directorySource).toMatch(/href="telHref\(attr\(f, 'phone'\)\)"[^>]*@click="trackContactView\(f\.id, 'phone'\)"/)
  })

  it('nhãn CTA giữ luật §1.4 — không có chữ giao dịch', () => {
    // Đối chiếu agent/moderation.py::_TRANSACTIONAL_CTA — copy của mình không được
    // vi phạm chính luật mình áp cho UGC.
    const banned = /(đặt\s*(ngay|tour|phòng|vé|hàng)|mua\s*ngay|thanh\s*toán|giỏ\s*hàng|checkout|add\s*to\s*cart|book\s*now|buy\s*now|đặt\s*cọc|chuyển\s*khoản|pay\s*now|order\s*now|đặt\s*bàn|giữ\s*chỗ|đặt\s*lịch)/i
    const widgetSource = readFileSync(resolve(process.cwd(), 'components/ContactWidget.vue'), 'utf8')
    for (const [name, source] of [['ContactWidget', widgetSource], ['dia-diem/[id]', detailSource], ['danh-ba', directorySource]] as const) {
      const labels = source.match(/data-contact-action="[^"]+"[\s\S]{0,400}?<\/(?:a|NuxtLink)>/g) || []
      expect(labels.length, `${name} có CTA đã nối`).toBeGreaterThan(0)
      for (const label of labels) expect(label, `${name}: ${label.slice(0, 80)}`).not.toMatch(banned)
    }
  })
})
