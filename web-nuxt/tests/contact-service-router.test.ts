// The contact page routes by job, and promises only what something tracks.
//
// A correction has a journey with a receipt and a deadline of its own; email
// does not. Claims and account recovery have no online journey yet, and saying
// so plainly beats implying one. And no surface may quote a resolution window
// nobody signed: the kernel promises a next update, not a fix within N hours.

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const PAGE = readFileSync(resolve(__dirname, '..', 'pages', 'lien-he.vue'), 'utf8')

describe('routing by job', () => {
  it('sends corrections to the journey that tracks them', () => {
    expect(PAGE).toContain('to="/yeu-cau/sua-thong-tin"')
    expect(PAGE).toContain('to="/yeu-cau/tra-cuu"')
  })

  it('keeps the correction card ahead of the generic mailbox', () => {
    // The reader with a wrong phone number should meet their journey before
    // the catch-all email that cannot track it.
    expect(PAGE.indexOf('card-correction')).toBeGreaterThan(-1)
    expect(PAGE.indexOf('card-correction')).toBeLessThan(PAGE.indexOf('card-general'))
  })

  it('says which jobs have no online journey yet, in so many words', () => {
    // An honest "email only, no tracking page" beats a mailbox dressed as a
    // service. The reader decides what to expect before they write.
    expect(PAGE).toContain('chưa có trang theo dõi trực tuyến')
  })
})

describe('promises', () => {
  const visible = PAGE
    // Strip SVG/CSS blocks where bare numbers are geometry, not promises.
    .replace(/<svg[\s\S]*?<\/svg>/g, '')
    .replace(/<style[\s\S]*?<\/style>/g, '')

  it('quotes no resolution window nobody signed', () => {
    expect(visible).not.toMatch(/24\s*[–-]\s*48/)
    expect(visible).not.toMatch(/trong vòng \d+\s*giờ/)
    expect(visible).not.toMatch(/xử lý trong \d+/)
  })

  it('still tells the truth it can keep: people read, corrections are tracked', () => {
    expect(visible).toContain('Người thật đọc từng tin nhắn')
    expect(visible).toContain('mã tra cứu')
  })
})
