// @vitest-environment node
//
// LỖ HỔNG của bộ test iCal đợt trước (commit 4bced5e1).
//
// Bộ test đó khoá BỘ SINH (`utils/safe.ts`) rất chặt, nhưng KHÔNG khoá ĐƯỜNG TRUYỀN
// THAM SỐ ở trang. Đổi `dateEnd: eventEnd(e)` → `eventStart(e)` trong
// `pages/le-hoi.vue` vẫn để cả 23 test cũ XANH — tức lỗi cũ (mất ngày cuối của sự
// kiện nhiều ngày) có thể quay lại qua đúng cửa đó mà không ai biết.
//
// Cách khoá ở đây: lấy CHÍNH mã của trang (parse SFC → bỏ chú thích kiểu TS → trích
// đúng ba hàm `eventStart` / `eventEnd` / `downloadIcalBulk`) rồi CHẠY nó trong hộp
// cát với `downloadIcsBundle` giả để bắt tham số, cuối cùng cho tham số đó chạy qua
// `buildIcsCalendar` THẬT và soi .ics thu được.
//
// Chủ ý: KHÔNG so chuỗi mã nguồn. Đổi tên biến, format lại, tách dòng — vẫn xanh.
// Đổi Ý NGHĨA tham số (ngày cuối → ngày đầu, hoán vị đầu/cuối, rơi mất địa điểm) — đỏ.
//
// Nếu trang đổi cấu trúc tới mức không trích được hàm, hộp cát NÉM LỖI thay vì im
// lặng bỏ qua: một cái test không chạy được phải đỏ, không được xanh giả.

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { parse as parseSfc } from 'vue/compiler-sfc'
import { transformWithEsbuild } from 'vite'
import { buildIcsCalendar, type IcsEventInput } from '../utils/safe'

const appRoot = resolve(import.meta.dirname, '..')

// ── Trích mã nguồn của trang ────────────────────────────────────────────────

/** Chỉ số của ký tự `close` đóng cặp mở tại `openIdx`; bỏ qua chuỗi và chú thích. */
function matchPair(src: string, openIdx: number, open: string, close: string): number {
  let depth = 0
  for (let i = openIdx; i < src.length; i++) {
    const c = src[i]
    const next = src[i + 1]
    if (c === '/' && next === '/') {
      const nl = src.indexOf('\n', i)
      if (nl < 0) return -1
      i = nl
      continue
    }
    if (c === '/' && next === '*') {
      const end = src.indexOf('*/', i + 2)
      if (end < 0) return -1
      i = end + 1
      continue
    }
    if (c === "'" || c === '"') {
      const end = endOfQuote(src, i, c)
      if (end < 0) return -1
      i = end
      continue
    }
    if (c === '`') {
      const end = endOfTemplate(src, i)
      if (end < 0) return -1
      i = end
      continue
    }
    if (c === open) depth++
    else if (c === close) {
      depth--
      if (depth === 0) return i
    }
  }
  return -1
}

function endOfQuote(src: string, openIdx: number, quote: string): number {
  for (let i = openIdx + 1; i < src.length; i++) {
    if (src[i] === '\\') { i++; continue }
    if (src[i] === quote) return i
  }
  return -1
}

function endOfTemplate(src: string, openIdx: number): number {
  for (let i = openIdx + 1; i < src.length; i++) {
    if (src[i] === '\\') { i++; continue }
    if (src[i] === '`') return i
    if (src[i] === '$' && src[i + 1] === '{') {
      const close = matchPair(src, i + 1, '{', '}')
      if (close < 0) return -1
      i = close
    }
  }
  return -1
}

/** Khai báo `function <name>(...) { ... }` đầy đủ, lấy nguyên văn từ mã đã bỏ kiểu TS. */
function extractFunction(js: string, name: string, where: string): string {
  const decl = new RegExp(String.raw`(?:^|[\s;{}()])((?:async\s+)?function\s+${name}\s*\()`, 'm')
  const m = decl.exec(js)
  if (!m) {
    throw new Error(
      `${where}: không tìm thấy khai báo 'function ${name}('. `
      + 'Trang đã đổi cấu trúc — cập nhật hộp cát, đừng nới test.',
    )
  }
  const start = m.index + (m[0] ?? '').length - (m[1] ?? '').length
  const paramOpen = js.indexOf('(', start)
  const paramClose = matchPair(js, paramOpen, '(', ')')
  if (paramClose < 0) throw new Error(`${where}: danh sách tham số của '${name}' không đóng.`)
  const bodyOpen = js.indexOf('{', paramClose)
  const bodyClose = matchPair(js, bodyOpen, '{', '}')
  if (bodyOpen < 0 || bodyClose < 0) throw new Error(`${where}: thân hàm '${name}' không đóng.`)
  return js.slice(start, bodyClose + 1)
}

const scriptCache = new Map<string, Promise<string>>()

/** `<script setup>` của một trang .vue, đã bỏ chú thích kiểu TS (chỉ còn JS chạy được). */
function pageScript(file: string): Promise<string> {
  const cached = scriptCache.get(file)
  if (cached) return cached
  const task = (async () => {
    const src = readFileSync(resolve(appRoot, file), 'utf8')
    const { descriptor, errors } = parseSfc(src, { filename: file })
    if (errors.length) throw new Error(`${file}: SFC không parse được — ${errors[0]?.message}`)
    const setup = descriptor.scriptSetup?.content
    if (!setup) throw new Error(`${file}: không có <script setup>.`)
    const { code } = await transformWithEsbuild(setup, `${file}.ts`, { loader: 'ts' })
    return code
  })()
  scriptCache.set(file, task)
  return task
}

// ── Hộp cát: chạy downloadIcalBulk THẬT của trang ───────────────────────────

interface BulkCall {
  items: IcsEventInput[]
  filename: string
}

interface PageSpec {
  file: string
  filename: string
}

const PAGES: PageSpec[] = [
  { file: 'pages/le-hoi.vue', filename: 'le-hoi-sap-toi.ics' },
  { file: 'pages/su-kien.vue', filename: 'su-kien-sap-toi.ics' },
]

/**
 * Chạy `downloadIcalBulk` của trang với danh sách entity cho trước và bắt lấy đúng
 * bộ tham số mà trang giao cho `downloadIcsBundle`.
 *
 * Cộng tác viên bị thay bằng hàng giả: `allEvents` (ref), `todayStr`, và
 * `downloadIcsBundle`. Nếu về sau hàm đó cần thêm biến ngoài, `new Function` sẽ
 * ném ReferenceError — đỏ ồn ào, đúng ý.
 */
async function runBulkIcs(page: PageSpec, events: unknown[], todayStr: string): Promise<BulkCall> {
  const js = await pageScript(page.file)
  const body = [
    extractFunction(js, 'eventStart', page.file),
    extractFunction(js, 'eventEnd', page.file),
    extractFunction(js, 'downloadIcalBulk', page.file),
    'return downloadIcalBulk',
  ].join('\n')

  const calls: BulkCall[] = []
  const factory = new Function('allEvents', 'todayStr', 'downloadIcsBundle', body) as (
    allEvents: { value: unknown[] },
    todayStr: string,
    downloadIcsBundle: (items: IcsEventInput[], filename: string) => void,
  ) => () => void

  factory(
    { value: events },
    todayStr,
    (items, filename) => { calls.push({ items, filename }) },
  )()

  if (calls.length !== 1) {
    throw new Error(
      `${page.file}: downloadIcalBulk gọi downloadIcsBundle ${calls.length} lần (chờ đúng 1). `
      + 'Trang đã tự ghép .ics hoặc đổi cửa xuất — kiểm tra lại.',
    )
  }
  return calls[0] as BulkCall
}

/** Các khối VEVENT của một VCALENDAR, mỗi khối là map thuộc tính (`DTSTART` → `20260305`). */
function veventProps(ics: string): Record<string, string>[] {
  const out: Record<string, string>[] = []
  let current: Record<string, string> | null = null
  for (const line of ics.split('\r\n')) {
    if (line === 'BEGIN:VEVENT') { current = {}; continue }
    if (line === 'END:VEVENT') { if (current) out.push(current); current = null; continue }
    if (!current) continue
    const colon = line.indexOf(':')
    if (colon < 0) continue
    const name = (line.slice(0, colon).split(';')[0] ?? '')
    current[name] = line.slice(colon + 1)
  }
  return out
}

/** Từ entity → .ics thật, đi qua đúng đường trang dùng. */
async function icsFor(page: PageSpec, events: unknown[], todayStr = TODAY) {
  const call = await runBulkIcs(page, events, todayStr)
  return { call, events: veventProps(buildIcsCalendar(call.items)) }
}

// ── Dữ liệu mẫu ────────────────────────────────────────────────────────────

const TODAY = '2026-01-01'

const MULTI_DAY = {
  id: 'le-hoi-cu-lao-an-binh',
  name: 'Lễ hội cù lao An Bình',
  summary: 'Bốn ngày hội bên bờ Cổ Chiên',
  place_name: 'Xã An Bình',
  attributes: { date_start: '2026-03-05', date_end: '2026-03-08' },
}

const SINGLE_DAY = {
  id: 'ngay-hoi-cam-sanh',
  name: 'Ngày hội cam sành',
  attributes: { date_start: '2026-03-05' },
}

const SAME_DAY = {
  id: 'phien-cho-noi-cuoi-nam',
  name: 'Phiên chợ nổi cuối năm',
  attributes: { date_start: '2026-12-31', date_end: '2026-12-31' },
}

const ISO_PREFERRED = {
  id: 'tuan-le-gom-do',
  name: 'Tuần lễ gốm đỏ',
  attributes: {
    date_start: '2026-04-01',
    date_start_iso: '2026-04-02',
    date_end: '2026-04-08',
    date_end_iso: '2026-04-10',
  },
}

const PAST = {
  id: 'hoi-da-qua',
  name: 'Hội đã qua',
  attributes: { date_start: '2025-12-20', date_end: '2025-12-22' },
}

/** Khai mạc ĐÚNG hôm nay — biên `>=`; đổi thành `>` là đánh rơi hội của chính hôm đó. */
const STARTS_TODAY = {
  id: 'hoi-khai-mac-hom-nay',
  name: 'Hội khai mạc hôm nay',
  attributes: { date_start: TODAY, date_end: '2026-01-03' },
}

// ── Test ───────────────────────────────────────────────────────────────────

describe.each(PAGES)('$file — đường truyền entity → tham số .ics', (page) => {
  it('hộp cát chạy được đúng mã của trang (không có test này thì mọi test dưới là giả)', async () => {
    const { call } = await icsFor(page, [MULTI_DAY])
    expect(call.filename).toBe(page.filename)
    expect(call.items).toHaveLength(1)
    expect(call.items[0]?.id).toBe(MULTI_DAY.id)
  })

  it('sự kiện NHIỀU NGÀY giữ nguyên ngày cuối: DTEND = ngày cuối + 1', async () => {
    const { events } = await icsFor(page, [MULTI_DAY])
    expect(events).toHaveLength(1)
    expect(events[0]?.DTSTART).toBe('20260305')
    expect(events[0]?.DTEND).toBe('20260309')
    // Chính là đột biến sống sót đợt trước: `dateEnd: eventEnd(e)` → `eventStart(e)`
    // làm sự kiện 4 ngày teo còn 1 ngày. 20260306 = dấu vết của nó.
    expect(events[0]?.DTEND).not.toBe('20260306')
  })

  it('không hoán vị đầu/cuối: DTSTART lấy từ date_start, không phải date_end', async () => {
    const { events } = await icsFor(page, [MULTI_DAY])
    expect(events[0]?.DTSTART).toBe('20260305')
    expect(events[0]?.DTSTART).not.toBe('20260308')
  })

  it('sự kiện 1 ngày (thiếu date_end) vẫn dài đúng 1 ngày', async () => {
    const { events } = await icsFor(page, [SINGLE_DAY])
    expect(events[0]?.DTSTART).toBe('20260305')
    expect(events[0]?.DTEND).toBe('20260306')
  })

  it('date_end == date_start → 1 ngày, không phải khoảng rỗng', async () => {
    const { events } = await icsFor(page, [SAME_DAY])
    expect(events[0]?.DTSTART).toBe('20261231')
    expect(events[0]?.DTEND).toBe('20270101')
  })

  it('ưu tiên *_iso: DTSTART/DTEND theo date_start_iso / date_end_iso', async () => {
    const { events } = await icsFor(page, [ISO_PREFERRED])
    expect(events[0]?.DTSTART).toBe('20260402')
    expect(events[0]?.DTEND).toBe('20260411')
  })

  it('mang theo tên / địa điểm / mô tả / liên kết, không rơi trường nào', async () => {
    const { events } = await icsFor(page, [MULTI_DAY])
    expect(events[0]?.SUMMARY).toBe(MULTI_DAY.name)
    expect(events[0]?.LOCATION).toBe(MULTI_DAY.place_name)
    expect(events[0]?.DESCRIPTION).toBe(MULTI_DAY.summary)
    expect(events[0]?.URL).toContain(MULTI_DAY.id)
  })

  it('chỉ xuất sự kiện từ hôm nay trở đi, và không đánh rơi sự kiện sắp tới', async () => {
    const { call, events } = await icsFor(page, [PAST, STARTS_TODAY, MULTI_DAY, SINGLE_DAY])
    expect(call.items.map(i => i.id)).toEqual([STARTS_TODAY.id, MULTI_DAY.id, SINGLE_DAY.id])
    expect(events).toHaveLength(3)
    // Hội khai mạc hôm nay vẫn phải mang đủ ngày cuối của nó.
    expect(events[0]?.DTSTART).toBe('20260101')
    expect(events[0]?.DTEND).toBe('20260104')
  })

  it('BẤT BIẾN qua đường của trang: mọi VEVENT có DTEND > DTSTART', async () => {
    const { events } = await icsFor(page, [MULTI_DAY, SINGLE_DAY, SAME_DAY, ISO_PREFERRED])
    expect(events).toHaveLength(4)
    for (const ev of events) {
      expect(ev.DTSTART).toMatch(/^\d{8}$/)
      expect(ev.DTEND).toMatch(/^\d{8}$/)
      expect(Number(ev.DTEND)).toBeGreaterThan(Number(ev.DTSTART))
    }
  })
})

describe('hai trang không được lệch nhau', () => {
  it('cùng entity → cùng .ics (chỉ khác tên file)', async () => {
    const input = [MULTI_DAY, SINGLE_DAY, SAME_DAY, ISO_PREFERRED]
    const [leHoi, suKien] = await Promise.all(PAGES.map(p => icsFor(p, input)))
    expect(leHoi?.events).toEqual(suKien?.events)
    expect(leHoi?.call.items).toEqual(suKien?.call.items)
    expect(leHoi?.call.filename).not.toBe(suKien?.call.filename)
  })
})
