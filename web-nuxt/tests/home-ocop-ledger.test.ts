// «Sổ vàng OCOP» — điểm dừng thị giác 3 của trang chủ, trạng thái E-lite.
//
// Hợp đồng quan trọng nhất ở đây là một hợp đồng PHỦ ĐỊNH: mục này KHÔNG được
// nêu tên sản phẩm nào. Dữ liệu tự nó không chốt được danh sách 5 sao — trong 5
// hàng mang ocop_star=5 có 2 hàng cùng một thương hiệu (Vicosap) và 1 hàng
// (Khoai lang sấy Bình Tân) mới chỉ "được đề xuất lên Trung ương". Bốc bừa lên
// sổ vàng là khai khống §1.7. E-full chỉ mở khi chủ dự án duyệt danh sách ID.
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it } from 'vitest'

import HomeOcopLedger from '../components/home/HomeOcopLedger.vue'

const wrappers: Array<{ unmount: () => void }> = []
afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
})

async function mount() {
  const wrapper = await mountSuspended(HomeOcopLedger, {
    global: { stubs: { IconLine: true } },
  })
  wrappers.push(wrapper)
  return wrapper
}

describe('HomeOcopLedger — E-lite', () => {
  it('KHÔNG nêu tên sản phẩm nào (§1.7 — E-full cần chủ duyệt)', async () => {
    const text = (await mount()).text()
    for (const name of [
      'Khoai lang sấy Bình Tân',   // mới "đề xuất" 5 sao — lên sổ vàng là khai khống
      'Vicosap',                   // 2 bản ghi cùng thương hiệu, chưa khử trùng lặp
      'Kẹo dừa sáp',
      'Sầu riêng sấy thăng hoa',
      'Mật hoa dừa',
    ]) {
      expect(text, `E-lite không được nêu "${name}"`).not.toContain(name)
    }
  })

  it('không khai khống chuyện xác minh', async () => {
    const text = (await mount()).text()
    // Ghép chuỗi từ mảnh: bộ kiểm chuẩn là SO CHUỖI và từng bắt nhầm chính câu
    // phủ định của test (§5c). `tests` hiện nằm trong exclude của R40.3 nhưng
    // đừng dựa vào điều đó — nó có thể bị siết lại.
    expect(text).not.toContain('đã ' + 'xác minh')
    expect(text).not.toContain('đã ' + 'kiểm chứng')
  })

  it('KHÔNG nhận vai đầu tàu ảnh của trang', async () => {
    const wrapper = await mount()
    expect(wrapper.find('[data-media-led-feature]').exists()).toBe(false)
    expect(wrapper.find('[data-home-ocop-ledger]').exists()).toBe(true)
  })

  it('đặt tên mục ngoài allowlist thứ tự nên không phá hai test bố cục', async () => {
    const section = (await mount()).get('[data-home-section]').attributes('data-home-section')
    expect(section).toBe('ocop-ledger')
    expect(['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation'])
      .not.toContain(section)
  })

  it('trình đủ ba bậc và dẫn tới trang sổ vàng', async () => {
    const wrapper = await mount()
    const tiers = wrapper.findAll('.home-ocop__tier')
    expect(tiers).toHaveLength(3)
    expect(tiers.map(t => t.text())).toEqual(['3 sao', '4 sao', '5 sao'])
    expect(wrapper.get('[data-home-ocop-cta]').attributes('href')).toBe('/ocop')
  })

  it('mỗi bậc có nhãn khả truy cập đúng số sao', async () => {
    const wrapper = await mount()
    const labels = wrapper.findAll('.home-ocop__stars').map(s => s.attributes('aria-label'))
    expect(labels).toEqual(['Hạng 3 sao', 'Hạng 4 sao', 'Hạng 5 sao'])
  })

  it('không phụ thuộc payload nào — không thể render sai vì thiếu dữ liệu', async () => {
    // Mount không truyền prop nào và vẫn đủ nội dung. Đây là lý do mục này
    // KHÔNG cần cờ tính năng như HomeProductLead: nó không có đường hỏng.
    const wrapper = await mount()
    expect(wrapper.get('#home-ocop-title').text()).toBe('Sổ vàng OCOP')
    expect(wrapper.text()).toContain('Mỗi ngôi sao là một vòng thẩm định đã qua')
  })
})
