// «Tin chính đặc sản» — điểm dừng thị giác 2 của trang chủ.
//
// Ba hợp đồng được khoá ở đây, mỗi cái đều từng suýt bị phá trong lúc dựng:
//  1. Mục CHỈ hiện khi có CỜ và có DỮ LIỆU — thiếu một trong hai thì khuyết êm,
//     không để lại khung rỗng hay nhãn treo (payload prod có thể không có lead:
//     kho ứng viên đo local chỉ 9 sản phẩm, prod đã phân kỳ theo §1.1).
//  2. KHÔNG mang `data-media-led-feature`. Thuộc tính đó là NGÂN SÁCH THỊ GIÁC
//     "mỗi trang một đầu tàu ảnh" mà HomeFeatureDossier đang giữ; hai test khác
//     chốt nó bằng toHaveLength(1) và sẽ đỏ nếu mục này cũng nhận vai đó.
//  3. Ảnh nhận qua prop `descriptor`, KHÔNG bao giờ tự chạm entity.images —
//     đó là điều kiện để cổng R20.10 không đòi hàng registry.
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'

import HomeProductLead from '../components/home/HomeProductLead.vue'
import type { ImageDescriptor } from '../types/image'
import { FEATURE_FLAGS, isEstablishedFeatureFlag, resolveFeatureFlag } from '../utils/featureFlags'

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

// `satisfies ImageDescriptor` chứ không phải `: ImageDescriptor`: vẫn giữ nguyên
// kiểu hẹp của từng khoá cho test đọc, nhưng bắt TS kiểm literal ngay tại đây.
// Thiếu nó, `source_class` bị suy ra là `string` và `nuxt typecheck` đỏ ở chính
// dòng truyền vào props — lỗi có sẵn từ trước, lộ ra khi chạy cổng typecheck.
const descriptor = {
  url: '/img/entities/ca-phi-sa-ot-thanh-phuoc.webp',
  alt: 'Cá phi sả ớt Thạnh Phước — ảnh minh họa',
  source_class: 'ai-generated',
  source_kind: 'entity-editorial',
  disclosure_key: 'entity-ai',
  short_label: 'Minh họa AI',
  full_disclosure: 'Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ.',
  credit: null,
  width: null,
  height: null,
} satisfies ImageDescriptor

async function mount(props: Record<string, unknown> = {}) {
  const wrapper = await mountSuspended(HomeProductLead, {
    props: {
      scaleLine: '218 đặc sản Vĩnh Long',
      eyebrow: 'Đề cử của ban biên tập',
      title: 'Cá phi sả ớt Thạnh Phước',
      summary: 'Sản phẩm chế biến từ cá rô phi nuôi sinh thái tại xã Thạnh Phước.',
      descriptor,
      disclosureId: 'home-product-lead-test',
      detailTo: '/dia-diem/ca-phi-sa-ot-thanh-phuoc',
      ...props,
    },
    global: { stubs: { IconLine: true, ImageDisclosure: true } },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('cờ home_product_lead', () => {
  it('có mặt trong registry và mặc định TẮT', () => {
    const flag = FEATURE_FLAGS.find(f => f.key === 'home_product_lead')
    expect(flag, 'cờ phải khai trong FEATURE_FLAGS để AdminCP tự sinh nút bật/tắt').toBeTruthy()
    expect(flag!.default).toBe(false)
  })

  it('chưa established nên fail-closed cho tới khi bật TAY từ AdminCP', () => {
    // Đây là đường lùi 10 giây không cần deploy — quan trọng vì máy chủ KHÔNG
    // giữ bản N-1 (installer xoá hẳn bản cũ khi cài).
    expect(isEstablishedFeatureFlag('home_product_lead')).toBe(false)
    expect(resolveFeatureFlag('home_product_lead', {})).toBe(false)
    expect(resolveFeatureFlag('home_product_lead', { home_product_lead: true })).toBe(true)
    expect(resolveFeatureFlag('home_product_lead', { home_product_lead: false })).toBe(false)
  })
})

describe('HomeProductLead', () => {
  it('KHÔNG nhận vai đầu tàu ảnh của trang', async () => {
    const wrapper = await mount()
    expect(wrapper.find('[data-media-led-feature]').exists()).toBe(false)
    expect(wrapper.find('[data-home-product-lead]').exists()).toBe(true)
  })

  it('đặt tên mục ngoài allowlist thứ tự nên không phá hai test bố cục', async () => {
    const wrapper = await mount()
    const section = wrapper.get('[data-home-section]').attributes('data-home-section')
    expect(section).toBe('product-lead')
    expect(['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation'])
      .not.toContain(section)
  })

  it('render con số quy mô, tên và CTA dẫn tới trang chi tiết', async () => {
    const wrapper = await mount()
    expect(wrapper.get('[id="home-product-lead-title"]').text()).toContain('218 đặc sản')
    expect(wrapper.text()).toContain('Cá phi sả ớt Thạnh Phước')
    expect(wrapper.get('[data-home-product-lead-cta]').attributes('href'))
      .toBe('/dia-diem/ca-phi-sa-ot-thanh-phuoc')
  })

  it('nối ảnh với nhãn công bố bằng aria-describedby', async () => {
    const wrapper = await mount()
    const img = wrapper.get('img')
    expect(img.attributes('aria-describedby')).toBe('home-product-lead-test')
    expect(img.attributes('alt')).toBe(descriptor.alt)
    // width/height tường minh để không nhảy layout khi ảnh về (CLS).
    expect(img.attributes('width')).toBe('960')
    expect(img.attributes('height')).toBe('540')
  })

  it('descriptor không có ảnh thì rơi về ô trống có nhãn, không vỡ', async () => {
    const wrapper = await mount({ descriptor: { ...descriptor, url: '' } })
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.find('.home-product-lead__media--empty').exists()).toBe(true)
  })

  it('thiếu summary hoặc region thì bỏ hẳn dòng, không in nhãn rỗng', async () => {
    const wrapper = await mount({ summary: undefined, region: undefined })
    expect(wrapper.find('.home-product-lead__summary').exists()).toBe(false)
    expect(wrapper.find('.home-product-lead__region').exists()).toBe(false)
  })
})
