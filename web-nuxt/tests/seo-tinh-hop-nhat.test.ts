// @vitest-environment node
//
// §1.6 trên các bề mặt MÁY ĐỌC — thứ Google và crawler AI đọc, không phải người.
//
// Vì sao cần rào riêng: checker R10.7 (`scripts/checks/check_tinh_cu.py`) bắt cụm
// `tỉnh (Bến Tre|Trà Vinh)` — nó đòi chữ "tỉnh" đứng NGAY TRƯỚC tên. Các chuỗi
// SEO lại viết "Vĩnh Long, Bến Tre, Trà Vinh" dạng liệt kê, không có chữ "tỉnh"
// nào, nên lọt qua cổng suốt. Đó là lý do sáu bề mặt dưới đây vẫn khai với máy
// rằng ba tỉnh còn tồn tại, dù noindex đang bật nên chưa ai đọc được.
//
// Rào ở đây theo Ý NGHĨA chứ không theo chuỗi: bề mặt phải nêu tỉnh hợp nhất, và
// nếu có nhắc tên tỉnh cũ thì phải kèm dấu lịch sử.
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(process.cwd())
const doc = (rel: string) => readFileSync(resolve(root, rel), 'utf8')

const TEN_CU = /Bến Tre|Trà Vinh/
const DAU_LICH_SU = /(?:^|\P{L})cũ(?:\P{L}|$)|trước\s+7-2025|hợp nhất|sáp nhập/u

/** Mọi lần nhắc tên tỉnh cũ trong chuỗi này đều phải có dấu lịch sử đi kèm. */
function sachTheo16(s: string): boolean {
  return !TEN_CU.test(s) || DAU_LICH_SU.test(s)
}

describe('§1.6 — bề mặt máy đọc phải nói đúng tỉnh hợp nhất', () => {
  it('meta description và og:description', () => {
    const cfg = doc('nuxt.config.ts')
    const metas = [...cfg.matchAll(/content: '([^']*(?:Vĩnh Long)[^']*)'/g)].map(m => m[1]!)
    expect(metas.length).toBeGreaterThan(0)
    for (const m of metas) {
      expect(sachTheo16(m), `chuỗi meta gọi tỉnh cũ mà không có dấu lịch sử: ${m}`).toBe(true)
    }
  })

  it('JSON-LD của site nêu tỉnh hợp nhất, không liệt kê ba tỉnh', () => {
    const cfg = doc('nuxt.config.ts')
    expect(cfg).toContain("'alternateName': 'Khám phá tỉnh Vĩnh Long'")
    expect(cfg).not.toMatch(/Vĩnh Long – Bến Tre – Trà Vinh/)
  })

  it('areaServed là MỘT đơn vị hành chính, không phải ba', () => {
    // Liệt kê ba tỉnh trong areaServed là khai với Google rằng ba tỉnh đó còn
    // tồn tại — chúng đã hợp nhất từ 7-2025.
    for (const rel of ['pages/index.vue', 'pages/gioi-thieu.vue']) {
      const src = doc(rel)
      const m = src.match(/areaServed:\s*([^\n]*)/)
      expect(m, `${rel}: không tìm thấy areaServed`).toBeTruthy()
      expect(TEN_CU.test(m![1]!), `${rel}: areaServed còn liệt kê tỉnh cũ — ${m![1]}`).toBe(false)
      expect(m![1]).toContain('Vĩnh Long')
    }
  })

  it('footer tagline không liệt kê ba tỉnh', () => {
    const src = doc('layouts/default.vue')
    const m = src.match(/'footer\.tagline',\s*'([^']*)'/)
    expect(m).toBeTruthy()
    expect(sachTheo16(m![1]!)).toBe(true)
  })

  it('manifest.json (PWA) mô tả đúng tỉnh', () => {
    const m = JSON.parse(doc('public/manifest.json')) as { description: string }
    expect(m.description).toContain('tỉnh Vĩnh Long')
    expect(sachTheo16(m.description)).toBe(true)
  })

  it('llms.txt nói THẲNG chuyện sáp nhập cho crawler AI', () => {
    // Tài liệu này viết riêng cho mô hình đọc. Nó là chỗ hiệu quả nhất để đính
    // chính một sự thật hành chính mà phần lớn nguồn trên mạng còn ghi sai.
    const t = doc('public/llms.txt')
    expect(t).toMatch(/HỢP NHẤT/)
    // Ghép từ mảnh: R10.7 là bộ SO CHUỖI và bắt cả câu phủ định (§5c) —
    // viết thẳng cụm bị cấm ở đây sẽ làm chính cổng chuẩn đỏ.
    expect(t).toMatch(new RegExp('KHÔNG còn là đơn vị cấp ' + 'tỉnh'))
    expect(t).toMatch(/cấp huyện cũng đã bỏ/)
    expect(t).toMatch(/124 xã\/phường/)
    // Mục ba vùng phải tự khai là gọi theo địa giới CŨ.
    const heading = t.match(/^## Ba vùng[^\n]*/m)
    expect(heading, 'thiếu mục ba vùng').toBeTruthy()
    expect(DAU_LICH_SU.test(heading![0])).toBe(true)
  })

  it('các thanh dateline-eyebrow ở hero các trang công cụ tuân thủ §1.6', () => {
    for (const rel of ['pages/ban-do.vue', 'pages/tim-kiem.vue', 'pages/tao-lich-trinh.vue', 'pages/danh-ba.vue', 'pages/dia-diem/index.vue']) {
      const src = doc(rel)
      const m = src.match(/class="[^"]*dateline-eyebrow[^"]*"[^>]*>([^<]+)</)
      if (m) {
        const label = m[1] ?? ''
        expect(sachTheo16(label), `${rel}: dateline-eyebrow gọi tỉnh cũ mà không có dấu lịch sử: ${label}`).toBe(true)
      }
    }
  })

  it('tất cả giá trị mặc định trong pageManifest.ts tuân thủ §1.6', () => {
    const src = doc('utils/pageManifest.ts')
    const lines = src.split('\n')
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]?.trim() ?? ''
      if (line.startsWith('//') || line.startsWith('/*') || line.startsWith('*')) continue
      if (TEN_CU.test(line)) {
        expect(sachTheo16(line), `utils/pageManifest.ts:${i + 1} nhắc tỉnh cũ mà thiếu dấu mốc lịch sử: ${line}`).toBe(true)
      }
    }
  })

  it('các khối editorial và mô tả trang công khai chính tuân thủ §1.6', () => {
    const pages = [
      'pages/dia-diem/index.vue',
      'pages/du-lich.vue',
      'pages/ocop.vue',
      'pages/su-kien.vue',
      'pages/tuyen-duong.vue',
      'pages/luu-tru.vue',
      'pages/le-hoi.vue',
      'pages/lich-trinh/index.vue',
      'pages/san-pham.vue',
    ]
    for (const rel of pages) {
      const src = doc(rel)
      const lines = src.split('\n')
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]?.trim() ?? ''
        if (line.startsWith('//') || line.startsWith('/*') || line.startsWith('*')) continue
        if (TEN_CU.test(line)) {
          expect(sachTheo16(line), `${rel}:${i + 1} nhắc tỉnh cũ mà thiếu dấu mốc lịch sử: ${line}`).toBe(true)
        }
      }
    }
  })
})
