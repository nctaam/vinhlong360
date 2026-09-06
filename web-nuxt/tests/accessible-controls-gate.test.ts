import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

const BASE_DIR = path.resolve(__dirname, '..')

function readFile(relPath: string): string {
  return fs.readFileSync(path.join(BASE_DIR, relPath), 'utf-8')
}

describe('Mốc 107: Accessible Controls & Landmark Labeling Standards (WCAG 2.2 SC 4.1.2 & SC 1.3.1)', () => {
  describe('pages/cai-dat.vue Accessible Names', () => {
    const content = readFile('pages/cai-dat.vue')

    it('bảo đảm các trường họ tên, tên hiển thị và email có aria-label tường minh', () => {
      expect(content).toMatch(/v-model="fullName"[^>]*aria-label="Họ và tên thật"/)
      expect(content).toMatch(/v-model="displayName"[^>]*aria-label="Tên bạn muốn hiển thị"/)
      expect(content).toMatch(/v-model="email"[^>]*aria-label="Địa chỉ email"/)
    })
  })

  describe('pages/admin/danh-ba.vue Accessible Names', () => {
    const content = readFile('pages/admin/danh-ba.vue')

    it('bảo đảm tên cơ quan và nguồn URL có aria-label tường minh', () => {
      expect(content).toMatch(/v-model="f\.name"[^>]*aria-label="Tên cơ quan"/)
      expect(content).toMatch(/v-model="f\.sourceUrl"[^>]*aria-label="Nguồn URL chính thống"/)
    })
  })

  describe('pages/admin/entities.vue File Upload Accessible Name', () => {
    const content = readFile('pages/admin/entities.vue')

    it('bảo đảm input file tải ảnh có aria-label tường minh', () => {
      expect(content).toMatch(/input\s+type="file"[^>]*aria-label="Tải ảnh AI biên tập \(tự nén WebP\)"/)
    })
  })
})
