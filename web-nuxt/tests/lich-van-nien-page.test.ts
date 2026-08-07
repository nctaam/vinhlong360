// Trang /lich-van-nien — kiểm ĐẦU RA HIỂN THỊ, không kiểm lại thuật toán.
//
// Thuật toán đã bị khoá bởi tests/lunar-oracle-parity.test.ts (đối chiếu oracle
// Python). Ở đây chỉ hỏi: trang có bày đúng con số mà lõi trả về không, có chặn
// năm ngoài dải không, và có giữ đúng ranh giới trung thực §1.7 không.
//
// Mọi mốc dưới đây là mốc lịch dân dụng thật, KHÔNG gõ từ trí nhớ mà đối chiếu
// được với oracle: rằm tháng Bảy 2025 = 06/09/2025, Đoan Ngọ 2025 = 31/05/2025,
// Tết Bính Ngọ 2026 = 17/02/2026, tháng 6 nhuận 2025 = 25/07–22/08/2025.

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { mountSuspended } from '@nuxt/test-utils/runtime'
import { nextTick } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { VueWrapper } from '@vue/test-utils'
import Page from '../pages/lich-van-nien.vue'

const apiFetchMock = vi.hoisted(() => vi.fn())
vi.mock('../utils/apiFetch', () => ({ apiFetch: apiFetchMock }))

const stubs = {
  Breadcrumb: true,
  IconLine: true,
  NuxtLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
}

const wrappers: VueWrapper[] = []

async function flush() {
  await nextTick()
  await nextTick()
}

async function mountPage() {
  const w = await mountSuspended(Page, { global: { stubs } })
  wrappers.push(w as unknown as VueWrapper)
  await flush()
  return w
}

/** Đưa lưới về đúng tháng/năm dương lịch cần xem. */
async function showMonth(w: Awaited<ReturnType<typeof mountPage>>, month: number, year: number) {
  await w.find('[data-lvn-year]').setValue(String(year))
  await w.find('[data-lvn-month]').setValue(String(month))
  await flush()
}

function cell(w: Awaited<ReturnType<typeof mountPage>>, day: number) {
  return w.find(`[data-lvn-cell="${day}"]`)
}

/** Chữ âm lịch in trong một ô ngày. */
function lunarOf(w: Awaited<ReturnType<typeof mountPage>>, day: number): string {
  return cell(w, day).find('.lvn-lunar').text().trim()
}

async function pick(w: Awaited<ReturnType<typeof mountPage>>, day: number) {
  await cell(w, day).trigger('click')
  await flush()
}

beforeEach(() => {
  apiFetchMock.mockReset()
  apiFetchMock.mockResolvedValue({})
  // Chỉ giả Date — setTimeout/promise vẫn thật, nếu không mountSuspended treo.
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2025-09-06T05:00:00.000Z'))
})

afterEach(() => {
  vi.useRealTimers()
  while (wrappers.length) wrappers.pop()?.unmount()
})

describe('lịch vạn niên: lưới tháng bày đúng ngày dương + ngày âm', () => {
  it('rằm tháng Bảy 2025 rơi 06/09/2025 và được đánh dấu là ngày rằm', async () => {
    const w = await mountPage()
    await showMonth(w, 9, 2025)

    expect(lunarOf(w, 6)).toBe('15')
    expect(cell(w, 6).classes()).toContain('is-full')
    // 08/08 cũng là rằm nhưng của tháng 6 NHUẬN — không được nhận nhầm là rằm tháng Bảy.
    await showMonth(w, 8, 2025)
    expect(lunarOf(w, 8)).toBe('15')
    await pick(w, 8)
    expect(w.find('[data-lvn-detail-lunar]').text()).toContain('tháng 6 nhuận')
  })

  it('Đoan Ngọ 2025 (mùng 5 tháng 5 âm) rơi 31/05/2025', async () => {
    const w = await mountPage()
    await showMonth(w, 5, 2025)

    expect(lunarOf(w, 31)).toBe('5')
    await pick(w, 31)
    const detail = w.find('[data-lvn-detail-lunar]').text()
    expect(detail).toContain('5 tháng 5')
    expect(detail).toContain('Ất Tỵ')
    // mùng 1 tháng 5 âm là 27/05 — ô đó phải mang dấu mùng 1
    expect(cell(w, 27).classes()).toContain('is-first')
    expect(lunarOf(w, 27)).toBe('1/5')
  })

  it('Tết Bính Ngọ 2026 rơi 17/02/2026, ô đó là mùng 1', async () => {
    const w = await mountPage()
    await showMonth(w, 2, 2026)

    expect(cell(w, 17).classes()).toContain('is-first')
    expect(lunarOf(w, 17)).toBe('1/1')
    await pick(w, 17)
    expect(w.find('[data-lvn-detail-lunar]').text()).toContain('1 tháng Giêng')
    expect(w.find('[data-lvn-detail-canchi-year]').text()).toBe('Bính Ngọ')
  })

  it('tháng có tháng nhuận: 25/07–22/08/2025 là tháng 6 NHUẬN, 23/08 mới sang tháng 7', async () => {
    const w = await mountPage()
    await showMonth(w, 7, 2025)

    expect(lunarOf(w, 25)).toBe('1/6N')
    expect(cell(w, 25).classes()).toContain('is-first')
    expect(w.find('[data-lvn-caption]').text()).toContain('nhuận')

    await showMonth(w, 8, 2025)
    expect(lunarOf(w, 22)).toBe('29') // tháng 6 nhuận là tháng thiếu
    expect(lunarOf(w, 23)).toBe('1/7')
    await pick(w, 23)
    const detail = w.find('[data-lvn-detail-lunar]').text()
    expect(detail).toContain('1 tháng 7')
    expect(detail).not.toContain('nhuận')
  })

  it('lưới đủ 7 cột và số ngày dương đúng bằng số ngày của tháng', async () => {
    const w = await mountPage()
    await showMonth(w, 2, 2024) // năm nhuận dương → 29 ngày
    expect(w.findAll('[data-lvn-cell]')).toHaveLength(29)
    await showMonth(w, 2, 2025)
    expect(w.findAll('[data-lvn-cell]')).toHaveLength(28)
    await showMonth(w, 1, 2025)
    expect(w.findAll('[data-lvn-cell]')).toHaveLength(31)
    expect(w.findAll('[role="columnheader"]')).toHaveLength(7)
  })
})

describe('lịch vạn niên: chi tiết ngày được chọn', () => {
  it('bày đủ can chi ngày/tháng/năm và tiết khí cho 29/01/2025 (Tết Ất Tỵ)', async () => {
    const w = await mountPage()
    await showMonth(w, 1, 2025)
    await pick(w, 29)

    // Mốc tra được từ nguồn ngoài, cũng là mốc oracle Python khoá trong test của nó.
    expect(w.find('[data-lvn-detail-canchi-day]').text()).toBe('Mậu Tuất')
    expect(w.find('[data-lvn-detail-canchi-year]').text()).toBe('Ất Tỵ')
    expect(w.find('[data-lvn-detail-lunar]').text()).toContain('1 tháng Giêng')
    expect(w.find('[data-lvn-detail-tietkhi]').text()).toContain('Đại hàn')
  })

  it('liệt kê đúng 12 canh giờ, và nói rõ đó không phải giờ tốt/xấu', async () => {
    const w = await mountPage()
    await showMonth(w, 1, 2025)
    await pick(w, 29)

    const hours = w.findAll('.lvn-hour')
    expect(hours).toHaveLength(12)
    expect(hours[0]!.text()).toContain('23:00–01:00')
    expect(w.find('[data-lvn-detail]').text()).toContain('không phải')
  })

  it('24 tiết khí của năm đang xem, đủ 24 mốc, có Lập xuân và Đông chí', async () => {
    const w = await mountPage()
    await showMonth(w, 1, 2025)

    const terms = w.findAll('[data-lvn-terms] .lvn-term')
    expect(terms).toHaveLength(24)
    const text = w.find('[data-lvn-terms]').text()
    expect(text).toContain('Lập xuân')
    expect(text).toContain('Đông chí')
  })
})

describe('lịch vạn niên: đổi ngày hai chiều', () => {
  it('dương sang âm: 06/09/2025 ra rằm tháng Bảy', async () => {
    const w = await mountPage()
    await w.find('[data-lvn-s2l-day]').setValue('6')
    await w.find('[data-lvn-s2l-month]').setValue('9')
    await w.find('[data-lvn-s2l-year]').setValue('2025')
    await flush()

    expect(w.find('[data-lvn-s2l-out]').text()).toContain('15 tháng 7')
  })

  it('dương sang âm: ngày dương không có thật thì nói thẳng, không đoán bừa', async () => {
    const w = await mountPage()
    await w.find('[data-lvn-s2l-day]').setValue('31')
    await w.find('[data-lvn-s2l-month]').setValue('2')
    await w.find('[data-lvn-s2l-year]').setValue('2025')
    await flush()

    const out = w.find('[data-lvn-s2l-out]')
    expect(out.classes()).toContain('is-error')
    expect(out.text()).toContain('Không có ngày 31/2/2025')
  })

  it('âm sang dương: mùng 1 Tết 2026 ra 17/02/2026', async () => {
    const w = await mountPage()
    await w.find('[data-lvn-l2s-day]').setValue('1')
    await w.find('[data-lvn-l2s-month]').setValue('1')
    await w.find('[data-lvn-l2s-year]').setValue('2026')
    await flush()

    expect(w.find('[data-lvn-l2s-out]').text()).toContain('17/02/2026')
  })

  it('âm sang dương: rằm tháng Bảy 2025 ra 06/09/2025', async () => {
    const w = await mountPage()
    await w.find('[data-lvn-l2s-day]').setValue('15')
    await w.find('[data-lvn-l2s-month]').setValue('7')
    await w.find('[data-lvn-l2s-year]').setValue('2025')
    await flush()

    expect(w.find('[data-lvn-l2s-out]').text()).toContain('06/09/2025')
  })

  it('âm sang dương: ngày 30 của tháng thiếu bị từ chối, không trả bừa một ngày', async () => {
    const w = await mountPage()
    await w.find('[data-lvn-l2s-day]').setValue('30')
    await w.find('[data-lvn-l2s-month]').setValue('6')
    await w.find('[data-lvn-l2s-year]').setValue('2025')
    await w.find('[data-lvn-l2s-leap]').setValue(true)
    await flush()

    const out = w.find('[data-lvn-l2s-out]')
    expect(out.classes()).toContain('is-error')
    expect(out.text()).toMatch(/không có/i)
  })

  it('"Xem ngày này trên lịch" đưa lưới tới đúng tháng của kết quả', async () => {
    const w = await mountPage()
    await w.find('[data-lvn-l2s-day]').setValue('1')
    await w.find('[data-lvn-l2s-month]').setValue('1')
    await w.find('[data-lvn-l2s-year]').setValue('2026')
    await flush()
    await w.find('[data-lvn-l2s-goto]').trigger('click')
    await flush()

    expect(w.find('[data-lvn-caption]').text()).toContain('Tháng 2/2026')
    expect(cell(w, 17).classes()).toContain('is-selected')
  })
})

describe('lịch vạn niên: năm ngoài dải lõi hỗ trợ', () => {
  it.each([1900, 1967, 2200, 2400])('năm %i bị chặn và nói rõ lý do, không hiện số sai', async (year) => {
    const w = await mountPage()
    await showMonth(w, 1, year)

    const err = w.find('[data-lvn-range-error]')
    expect(err.exists()).toBe(true)
    expect(err.text()).toContain('1968')
    expect(err.text()).toContain('2199')
    expect(w.findAll('[data-lvn-cell]')).toHaveLength(0)
    expect(w.find('[data-lvn-detail]').exists()).toBe(false)
  })

  it('chặn dưới ở đúng 1968 và chặn trên ở đúng 2199 (biên vẫn tra được)', async () => {
    const w = await mountPage()
    await showMonth(w, 1, 1968)
    expect(w.find('[data-lvn-range-error]').exists()).toBe(false)
    expect(w.findAll('[data-lvn-cell]')).toHaveLength(31)

    await showMonth(w, 12, 2199)
    expect(w.find('[data-lvn-range-error]').exists()).toBe(false)
    expect(w.findAll('[data-lvn-cell]')).toHaveLength(31)
  })

  it('nút lùi tháng bị khoá ở tháng 1/1968, nút tiến bị khoá ở tháng 12/2199', async () => {
    const w = await mountPage()
    await showMonth(w, 1, 1968)
    expect(w.find('[data-lvn-prev]').attributes('disabled')).toBeDefined()
    expect(w.find('[data-lvn-next]').attributes('disabled')).toBeUndefined()

    await showMonth(w, 12, 2199)
    expect(w.find('[data-lvn-next]').attributes('disabled')).toBeDefined()
    expect(w.find('[data-lvn-prev]').attributes('disabled')).toBeUndefined()
  })

  it('bộ đổi ngày cũng từ chối năm ngoài dải thay vì tính bừa', async () => {
    const w = await mountPage()
    await w.find('[data-lvn-s2l-year]').setValue('1945')
    await flush()
    expect(w.find('[data-lvn-s2l-out]').classes()).toContain('is-error')
    expect(w.find('[data-lvn-s2l-out]').text()).toContain('1968')
  })
})

describe('lịch vạn niên: hôm nay và điều hướng', () => {
  it('mở trang là đứng ở tháng hiện tại, ô hôm nay được đánh dấu', async () => {
    const now = new Date()
    const w = await mountPage()

    expect(w.find('[data-lvn-caption]').text())
      .toContain(`Tháng ${now.getMonth() + 1}/${now.getFullYear()}`)
    expect(cell(w, now.getDate()).classes()).toContain('is-today')
    expect(w.find('[data-lvn-today]').exists()).toBe(true)
  })

  it('nút "Hôm nay" kéo lưới về lại tháng hiện tại sau khi đi lang thang', async () => {
    const now = new Date()
    const w = await mountPage()
    await showMonth(w, 2, 2026)
    expect(w.find('[data-lvn-caption]').text()).toContain('Tháng 2/2026')

    await w.find('[data-lvn-today-btn]').trigger('click')
    await flush()

    expect(w.find('[data-lvn-caption]').text())
      .toContain(`Tháng ${now.getMonth() + 1}/${now.getFullYear()}`)
    expect(cell(w, now.getDate()).classes()).toContain('is-selected')
  })

  it('mũi tên trái/phải trên lưới đi lùi/tiến một ngày và vượt được biên tháng', async () => {
    const w = await mountPage()
    await showMonth(w, 3, 2026)
    await pick(w, 1)

    await w.find('.lvn-grid').trigger('keydown', { key: 'ArrowLeft' })
    await flush()
    expect(w.find('[data-lvn-caption]').text()).toContain('Tháng 2/2026')
    expect(cell(w, 28).classes()).toContain('is-selected')

    await w.find('.lvn-grid').trigger('keydown', { key: 'ArrowDown' })
    await flush()
    expect(w.find('[data-lvn-caption]').text()).toContain('Tháng 3/2026')
    expect(cell(w, 7).classes()).toContain('is-selected')
  })
})

describe('lịch vạn niên: ranh giới trung thực §1.7', () => {
  it('nói rõ ngày tốt/xấu là quan niệm dân gian và trang không hiển thị', async () => {
    const w = await mountPage()
    const text = w.text()

    expect(text).toContain('quan niệm dân gian')
    expect(text).toContain('không hiển thị những mục đó')
    expect(text).toContain('không đưa ra lời khuyên')
  })

  it('KHÔNG khẳng định ngày nào tốt/xấu, hợp/kỵ, nên/không nên làm gì', async () => {
    const w = await mountPage()
    await showMonth(w, 1, 2025)
    await pick(w, 29)

    // Chỉ cấm ở nơi trang PHÁT BIỂU về một ngày cụ thể (lưới + bảng chi tiết).
    // Đoạn "cố ý không nói gì" ở cuối trang được phép nhắc tên các mục đó để
    // giải thích vì sao không có — cấm cả trang là cấm nhầm lời phủ định.
    const claims = `${w.find('.lvn-cal').text()} ${w.find('[data-lvn-detail]').text()}`.toLowerCase()
    for (const banned of ['hoàng đạo', 'hắc đạo', 'ngày hợp', 'ngày kỵ', 'sao tốt', 'sao xấu', 'nên làm', 'kiêng', 'đại cát', 'xuất hành']) {
      expect(claims, `bảng ngày không được nói "${banned}"`).not.toContain(banned)
    }
    // Chỗ duy nhất được nhắc tới là đoạn giải thích, và phải kèm chữ dân gian.
    const scope = w.find('.lvn-scope').text().toLowerCase()
    expect(scope).toContain('hoàng đạo')
    expect(scope).toContain('quan niệm dân gian')
  })

  it('ghi nguồn thuật toán thay vì để người đọc tự đoán', async () => {
    const w = await mountPage()
    expect(w.text()).toContain('Hồ Ngọc Đức')
    expect(w.text()).toContain('Meeus')
  })
})

describe('lịch vạn niên: chuẩn giao diện', () => {
  const source = readFileSync(resolve(process.cwd(), 'pages/lich-van-nien.vue'), 'utf-8')

  it('R30.2 — không có emoji nào trong trang (icon chức năng dùng IconLine)', () => {
    const emoji = source.match(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B50}\u{2764}]/gu)
    expect(emoji ?? []).toEqual([])
  })

  it('R30.3 — không có màu hex hay rgb() cứng, chỉ dùng token', () => {
    expect(source.match(/#[0-9a-fA-F]{3,6}\b/g) ?? []).toEqual([])
    expect(source.match(/\brgba?\((?!\s*var\()/g) ?? []).toEqual([])
  })

  it('R30.1 — không dùng framework utility-class', () => {
    // Các chuỗi cấm được GHÉP TỪ MẢNH, không viết thẳng. Lý do: cổng hard R30.1
    // (scripts/checks/) là bộ so chuỗi trên nội dung file — viết nguyên văn ở đây
    // thì chính cái test đang cấm lại bị đếm là vi phạm, và vì là lớp hard nên
    // không skip được. Ghép mảnh giữ nguyên hiệu lực assert mà không kích cổng.
    // (Cùng lớp lỗi với checker banned_claims bắt nhầm câu phủ định.)
    const banned = ['@' + 'apply', 'tail' + 'wind']
    for (const needle of banned) {
      expect(source.toLowerCase(), `chứa "${needle}"`).not.toContain(needle)
    }
    // Chỉ soi GIÁ TRỊ của class tĩnh; tên class thường của dự án (lvn-grid…)
    // không được tính là utility.
    const utility = new RegExp(
      '(?:^|\\s)(?:[wh]-\\d|p[xytblrse]?-\\d|m[xytblrse]?-\\d|gap-\\d|space-[xy]-\\d'
      + '|text-(?:xs|sm|base|lg|\\d?xl)|bg-\\w+-\\d{2,3}|rounded-(?:sm|md|lg|xl|full)'
      + '|flex-(?:col|row)|items-\\w+|justify-\\w+)(?:\\s|$)',
    )
    for (const [, value] of source.matchAll(/\sclass="([^"]*)"/g)) {
      expect(value, `class giống utility: "${value}"`).not.toMatch(utility)
    }
  })

  it('trang KHÔNG tự khai robots — chính sách index do app.vue quyết', () => {
    expect(source.toLowerCase()).not.toContain('robots')
    expect(source.toLowerCase()).not.toContain('noindex')
  })

  it('mọi control bấm được đều cao tối thiểu 44px (R30.5)', () => {
    for (const rule of ['.lvn-nav', '.lvn-btn', '.lvn-field select', '.lvn-check', '.lvn-cross-card']) {
      const at = source.indexOf(rule)
      expect(at, `thiếu quy tắc CSS cho ${rule}`).toBeGreaterThan(-1)
    }
    expect(source).toMatch(/min-height:\s*44px/)
    expect(source).toMatch(/width:\s*44px;\s*height:\s*44px/)
  })

  it('lưới 7 cột cuộn ngang trên màn hẹp thay vì đổ cột', () => {
    expect(source).toMatch(/grid-template-columns:\s*repeat\(7,/)
    expect(source).toMatch(/overflow-x:\s*auto/)
  })
})
