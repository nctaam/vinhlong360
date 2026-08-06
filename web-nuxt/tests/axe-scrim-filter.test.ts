import { describe, expect, it } from 'vitest'
import { SCRIM_SELECTORS, scrimShieldsText } from '../../scripts/axe_scrim_filter.mjs'

/**
 * `scripts/axe_scan.mjs` bỏ qua vi phạm color-contrast trên chữ nằm trong
 * `.spread-scrim`, vì axe không nhìn được nền ở `z-index: -1` và quy nhầm nền
 * về nền TRANG (đo được: axe báo bgColor `#fdfcf9`, tỉ lệ 1.02, trong khi nền
 * thật dưới chữ là `rgba(8,9,12,.84)`).
 *
 * Việc bỏ qua đó chỉ chính đáng CHỪNG NÀO scrim còn thật sự tối. Test này khoá
 * đúng điều kiện ấy — nếu ai làm scrim nhạt đi, mờ đi hay ẩn hẳn thì bộ lọc
 * phải bung ra để vi phạm THẬT nổi lên trên cổng R30.6.
 *
 * Kiểm bằng hàm thuần chứ không qua DOM thật: thử qua trình duyệt cho kết quả
 * mâu thuẫn giữa các lần (transition `1e-05s` khiến computed opacity chưa kịp
 * đổi, rAF không chạy khi pane ẩn) — tức phép thử tự nó không đáng tin.
 */
describe('axe scan — bộ lọc scrim tự vô hiệu', () => {
  const scrimTot = {
    display: 'block',
    visibility: 'visible',
    opacity: '1',
    backgroundImage: 'linear-gradient(to right top, rgba(8, 9, 12, 0.84), rgba(8, 9, 12, 0.52) 40%)',
  }

  it('bỏ qua khi scrim còn đủ tối — đúng cấu hình đang chạy', () => {
    expect(scrimShieldsText(scrimTot)).toBe(true)
  })

  it('bung khi gradient bị làm nhạt dưới ngưỡng .8', () => {
    expect(scrimShieldsText({
      ...scrimTot,
      backgroundImage: 'linear-gradient(to right top, rgba(8, 9, 12, 0.30), rgba(8, 9, 12, 0.04))',
    })).toBe(false)
  })

  it('bung khi scrim bị hạ opacity', () => {
    expect(scrimShieldsText({ ...scrimTot, opacity: '0.5' })).toBe(false)
    expect(scrimShieldsText({ ...scrimTot, opacity: '0.94' })).toBe(false)
  })

  it('bung khi scrim bị ẩn', () => {
    expect(scrimShieldsText({ ...scrimTot, display: 'none' })).toBe(false)
    expect(scrimShieldsText({ ...scrimTot, visibility: 'hidden' })).toBe(false)
  })

  it('bung khi không còn scrim hoặc nền không phải màu tối có alpha', () => {
    expect(scrimShieldsText(null)).toBe(false)
    expect(scrimShieldsText({ ...scrimTot, backgroundImage: 'none' })).toBe(false)
    expect(scrimShieldsText({ ...scrimTot, backgroundImage: '' })).toBe(false)
  })

  it('ngưỡng .8 là biên đóng — .8 giữ, ngay dưới thì bung', () => {
    const withAlpha = (a: string) => ({ ...scrimTot, backgroundImage: `linear-gradient(to right top, rgba(8, 9, 12, ${a}))` })
    expect(scrimShieldsText(withAlpha('0.8'))).toBe(true)
    expect(scrimShieldsText(withAlpha('0.79'))).toBe(false)
  })

  it('chỉ che đúng các selector của spread, không mở rộng ra ngoài', () => {
    expect(SCRIM_SELECTORS).toEqual(['.spread-kicker', '.spread-title', '.spread-sub', '#spread-title'])
  })
})
