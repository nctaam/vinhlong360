import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

const BASE_DIR = path.resolve(__dirname, '..')

function getFiles(dir: string, match: (file: string) => boolean): string[] {
  let results: string[] = []
  const list = fs.readdirSync(dir)
  list.forEach(file => {
    const full = path.join(dir, file)
    const stat = fs.statSync(full)
    if (stat && stat.isDirectory()) {
      results = results.concat(getFiles(full, match))
    } else if (match(file)) {
      results.push(full)
    }
  })
  return results
}

function readFile(relPath: string): string {
  return fs.readFileSync(path.join(BASE_DIR, relPath), 'utf-8')
}

describe('Mốc 108: Disclosure Semantics & Universal Page Title Authority (WCAG 2.2 SC 2.4.2 & SC 4.1.2)', () => {
  describe('Universal Page Title Coverage (100% of 74 pages)', () => {
    const pagesDir = path.join(BASE_DIR, 'pages')
    const pageFiles = getFiles(pagesDir, f => f.endsWith('.vue'))

    it('bảo đảm toàn bộ 74 trang đều khai báo title (qua useHead hoặc useSeoMeta)', () => {
      expect(pageFiles.length).toBe(74)
      const missingTitles: string[] = []

      pageFiles.forEach(file => {
        const code = fs.readFileSync(file, 'utf-8')
        const rel = path.relative(BASE_DIR, file).replace(/\\/g, '/')
        const hasTitle = /title\s*:\s*|title\s*=\s*|useHead\s*\(\s*\{[^}]*title|useSeoMeta\s*\(\s*\{[^}]*title/i.test(code)
        if (!hasTitle) {
          missingTitles.push(rel)
        }
      })

      expect(missingTitles).toEqual([])
    })

    it('bảo đảm pages/admin/yeu-cau.vue có tiêu đề quản trị tường minh', () => {
      const content = readFile('pages/admin/yeu-cau.vue')
      expect(content).toMatch(/useHead\(\{\s*title:\s*'Xử lý yêu cầu — Admin'\s*\}\)/)
    })
  })

  describe('Interactive Disclosure Semantics (:aria-expanded)', () => {
    it('bảo đảm nút mở rộng bài viết PostCard có :aria-expanded="expanded"', () => {
      const content = readFile('components/PostCard.vue')
      expect(content).toMatch(/class="thread-expand"[^>]*:aria-expanded="expanded"/)
    })

    it('bảo đảm nút xem đầy đủ kiểm duyệt trong admin/kiem-duyet.vue có :aria-expanded="expanded.has(p.id)"', () => {
      const content = readFile('pages/admin/kiem-duyet.vue')
      expect(content).toMatch(/class="mod-expand"[^>]*:aria-expanded="expanded\.has\(p\.id\)"/)
    })

    it('bảo đảm nút xem trước tóm tắt trong admin/entities.vue có :aria-expanded="previewSummary"', () => {
      const content = readFile('pages/admin/entities.vue')
      expect(content).toMatch(/class="btn btn-ghost btn-sm"[^>]*:aria-expanded="previewSummary"[^>]*@click="previewSummary = !previewSummary"/)
    })
  })
})
