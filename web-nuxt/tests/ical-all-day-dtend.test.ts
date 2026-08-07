// @vitest-environment node
//
// LỖI 2 — file .ics sinh sự kiện all-day dài 0 ngày.
//
// RFC 5545 §3.6.1: với VEVENT all-day (DTSTART/DTEND kiểu VALUE=DATE), DTEND là
// LOẠI-TRỪ (non-inclusive) và "MUST be greater than" DTSTART. Bộ sinh cũ phát
// DTEND = date_end (ngày cuối, INCLUSIVE) hoặc = DTSTART khi chỉ có 1 ngày →
// khoảng dài 0 ngày. Google Calendar / Outlook bỏ qua hoặc vẽ sai.
//
// Bẫy khi vá: cộng thêm 1 ngày cho cả sự kiện nhiều ngày là ĐÚNG (ngày-cuối + 1),
// nhưng cộng vào ngày cuối ĐÃ được coi là exclusive thì mỗi sự kiện dài thêm 1 ngày.
// Các test dưới khoá cả hai ca (1 ngày / nhiều ngày) + bất biến DTEND > DTSTART.

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { buildIcsCalendar, icsAllDayEnd } from '../utils/safe'

const appRoot = resolve(import.meta.dirname, '..')

/** Split a VCALENDAR string into its VEVENT blocks (array of unfolded lines). */
function veventBlocks(ics: string): string[][] {
  const lines = ics.split('\r\n')
  const blocks: string[][] = []
  let current: string[] | null = null
  for (const line of lines) {
    if (line === 'BEGIN:VEVENT') { current = []; continue }
    if (line === 'END:VEVENT') { if (current) blocks.push(current); current = null; continue }
    if (current) current.push(line)
  }
  return blocks
}

function prop(block: string[], name: string): string | undefined {
  const hit = block.find(l => (l.split(':')[0] ?? '').split(';')[0] === name)
  return hit === undefined ? undefined : hit.slice(hit.indexOf(':') + 1)
}

/** The first VEVENT of a generated calendar (empty block if none — assertions then fail loudly). */
function firstBlock(ics: string): string[] {
  const [block = []] = veventBlocks(ics)
  return block
}

describe('icsAllDayEnd — DTEND loại-trừ theo RFC 5545', () => {
  it('sự kiện 1 ngày (không có ngày kết thúc) → DTEND = DTSTART + 1', () => {
    expect(icsAllDayEnd('2026-03-05')).toBe('20260306')
    expect(icsAllDayEnd('2026-03-05', '')).toBe('20260306')
    expect(icsAllDayEnd('2026-03-05', null)).toBe('20260306')
  })

  it('sự kiện 1 ngày khai báo date_end == date_start → vẫn chỉ dài 1 ngày', () => {
    // Đây chính là ca sinh ra lỗi cũ: DTEND == DTSTART → dài 0 ngày.
    expect(icsAllDayEnd('2026-03-05', '2026-03-05')).toBe('20260306')
  })

  it('sự kiện nhiều ngày → DTEND = NGÀY CUỐI + 1, đúng một ngày (không cộng dư)', () => {
    // 05→08 inclusive = 4 ngày. DTEND exclusive phải là 09, KHÔNG phải 10.
    expect(icsAllDayEnd('2026-03-05', '2026-03-08')).toBe('20260309')
    expect(icsAllDayEnd('2026-03-05', '2026-03-08')).not.toBe('20260310')
    expect(icsAllDayEnd('2026-01-01', '2026-01-02')).toBe('20260103')
  })

  it('cộng ngày vượt biên tháng / năm / năm nhuận đúng lịch', () => {
    expect(icsAllDayEnd('2026-03-31')).toBe('20260401')
    expect(icsAllDayEnd('2026-12-31')).toBe('20270101')
    expect(icsAllDayEnd('2026-04-30', '2026-05-31')).toBe('20260601')
    expect(icsAllDayEnd('2027-02-28')).toBe('20270301') // 2027 không nhuận
    expect(icsAllDayEnd('2028-02-28')).toBe('20280229') // 2028 nhuận
    expect(icsAllDayEnd('2028-02-29')).toBe('20280301')
  })

  it('chấp nhận cả dạng gọn YYYYMMDD lẫn YYYY-MM-DD', () => {
    expect(icsAllDayEnd('20260305', '20260308')).toBe('20260309')
  })

  it('dữ liệu hỏng: ngày kết thúc trước ngày bắt đầu → thu về 1 ngày, không sinh khoảng âm', () => {
    expect(icsAllDayEnd('2026-03-05', '2026-03-01')).toBe('20260306')
  })

  it('dữ liệu hỏng: ngày kết thúc không phải ngày lịch thật → coi như 1 ngày', () => {
    expect(icsAllDayEnd('2026-03-05', '2026-13-45')).toBe('20260306')
    expect(icsAllDayEnd('2026-03-05', '2027-02-29')).toBe('20260306') // 2027 không nhuận
    expect(icsAllDayEnd('2026-03-05', '2026-03')).toBe('20260306')
  })

  it('ngày bắt đầu không hợp lệ → trả rỗng (người gọi bỏ qua sự kiện)', () => {
    expect(icsAllDayEnd('')).toBe('')
    expect(icsAllDayEnd('2026-02-30')).toBe('')
    expect(icsAllDayEnd('hôm nào đó')).toBe('')
  })
})

describe('buildIcsCalendar — VEVENT all-day hợp lệ', () => {
  const single = { id: 'le-hoi-a', name: 'Lễ hội A', dateStart: '2026-03-05' }
  const multi = { id: 'le-hoi-b', name: 'Lễ hội B', dateStart: '2026-03-05', dateEnd: '2026-03-08' }

  it('sự kiện 1 ngày phát DTEND = DTSTART + 1', () => {
    const block = firstBlock(buildIcsCalendar([single]))
    expect(prop(block, 'DTSTART')).toBe('20260305')
    expect(prop(block, 'DTEND')).toBe('20260306')
  })

  it('sự kiện nhiều ngày phát DTEND = ngày cuối + 1 (không kéo dài thêm)', () => {
    const block = firstBlock(buildIcsCalendar([multi]))
    expect(prop(block, 'DTSTART')).toBe('20260305')
    expect(prop(block, 'DTEND')).toBe('20260309')
  })

  it('BẤT BIẾN: mọi VEVENT đều có DTEND > DTSTART', () => {
    const items = [
      single,
      multi,
      { id: 'c', name: 'C', dateStart: '2026-12-31', dateEnd: '2026-12-31' },
      { id: 'd', name: 'D', dateStart: '2026-12-30', dateEnd: '2027-01-02' },
      { id: 'e', name: 'E', dateStart: '2026-05-01', dateEnd: '2026-04-01' }, // dữ liệu hỏng
    ]
    const blocks = veventBlocks(buildIcsCalendar(items))
    expect(blocks).toHaveLength(items.length)
    for (const block of blocks) {
      const start = prop(block, 'DTSTART')
      const end = prop(block, 'DTEND')
      expect(start).toMatch(/^\d{8}$/)
      expect(end).toMatch(/^\d{8}$/)
      expect(Number(end)).toBeGreaterThan(Number(start))
    }
  })

  it('giữ VALUE=DATE cho cả DTSTART và DTEND (all-day, không phải giờ cụ thể)', () => {
    const ics = buildIcsCalendar([multi])
    expect(ics).toContain('DTSTART;VALUE=DATE:20260305')
    expect(ics).toContain('DTEND;VALUE=DATE:20260309')
  })

  it('bọc đúng VCALENDAR, một VEVENT mỗi mục, phân tách bằng CRLF', () => {
    const ics = buildIcsCalendar([single, multi])
    expect(ics.startsWith('BEGIN:VCALENDAR\r\n')).toBe(true)
    expect(ics.endsWith('\r\nEND:VCALENDAR')).toBe(true)
    expect(ics.split('BEGIN:VEVENT').length - 1).toBe(2)
    expect(ics.includes('\n\n')).toBe(false)
  })

  it('bỏ qua mục không có ngày bắt đầu hợp lệ thay vì phát VEVENT thiếu DTEND', () => {
    const blocks = veventBlocks(buildIcsCalendar([
      { id: 'x', name: 'Không ngày', dateStart: '' },
      single,
    ]))
    expect(blocks).toHaveLength(1)
    expect(prop(blocks[0] ?? [], 'SUMMARY')).toBe('Lễ hội A')
  })

  it('escape SUMMARY/LOCATION/DESCRIPTION để không phá cấu trúc dòng ICS', () => {
    const block = firstBlock(buildIcsCalendar([{
      id: 'z',
      name: 'Lễ hội; A, B\\C',
      place_name: 'Xã X; Vĩnh Long',
      summary: 'Dòng 1\nDòng 2',
      dateStart: '2026-03-05',
    }]))
    expect(prop(block, 'SUMMARY')).toBe('Lễ hội  A  B C')
    expect(prop(block, 'LOCATION')).toBe('Xã X  Vĩnh Long')
    expect(prop(block, 'DESCRIPTION')).toBe('Dòng 1\\nDòng 2')
    expect(prop(block, 'DESCRIPTION')).not.toContain('\n')
  })
})

describe('các trang phát .ics dùng chung bộ sinh (không tái lập lỗi cũ)', () => {
  for (const page of ['pages/su-kien.vue', 'pages/le-hoi.vue']) {
    it(`${page} uỷ quyền cho downloadIcsBundle, không tự ghép dòng VEVENT`, () => {
      const src = readFileSync(resolve(appRoot, page), 'utf8')
      expect(src).toContain('downloadIcsBundle(')
      // Tự ghép lại = tự do phát DTEND inclusive lần nữa. Chặn ngay ở nguồn.
      expect(src).not.toContain('DTEND;VALUE=DATE')
      expect(src).not.toContain('BEGIN:VEVENT')
      expect(src).not.toContain('BEGIN:VCALENDAR')
    })
  }
})
