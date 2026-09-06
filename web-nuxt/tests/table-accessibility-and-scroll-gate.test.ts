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

describe('Mốc 110: Table Accessibility, Keyboard-Scrollable Regions & Reduced Motion Gate (WCAG 2.2 SC 1.3.1, SC 2.1.1, SC 2.4.7)', () => {
  const vueFiles = [
    ...getFiles(path.join(BASE_DIR, 'pages'), f => f.endsWith('.vue')),
    ...getFiles(path.join(BASE_DIR, 'components'), f => f.endsWith('.vue'))
  ]

  it('bảo đảm 100% thẻ <table> có accessible name (aria-label, aria-labelledby hoặc caption)', () => {
    const unlabeledTables: { file: string; line: number }[] = []

    vueFiles.forEach(file => {
      const content = fs.readFileSync(file, 'utf-8')
      const lines = content.split('\n')
      lines.forEach((line, idx) => {
        if (/<table\b/.test(line)) {
          // Check if line or adjacent lines have label
          const chunk = lines.slice(Math.max(0, idx - 1), idx + 3).join(' ')
          const hasLabel = /aria-label\s*=|aria-labelledby\s*=/i.test(chunk) || /<caption>/i.test(content)
          if (!hasLabel) {
            unlabeledTables.push({
              file: path.relative(BASE_DIR, file).replace(/\\/g, '/'),
              line: idx + 1
            })
          }
        }
      })
    })

    expect(unlabeledTables).toEqual([])
  })

  it('bảo đảm 100% thẻ <th> trong <thead> có scope="col"', () => {
    const invalidThs: { file: string; th: string }[] = []

    vueFiles.forEach(file => {
      const content = fs.readFileSync(file, 'utf-8')
      const theadMatch = content.match(/<thead>([\s\S]*?)<\/thead>/gi)
      if (theadMatch) {
        theadMatch.forEach(thead => {
          const thRegex = /<th\b([^>]*)>/gi
          let m
          while ((m = thRegex.exec(thead)) !== null) {
            const attrs = m[1]
            if (!attrs.includes('scope="col"') && !attrs.includes("scope='col'")) {
              invalidThs.push({
                file: path.relative(BASE_DIR, file).replace(/\\/g, '/'),
                th: m[0]
              })
            }
          }
        })
      }
    })

    expect(invalidThs).toEqual([])
  })

  it('bảo đảm 100% vùng bọc bảng cuộn (table-wrap) là keyboard-scrollable region (role="region", tabindex="0", aria-label)', () => {
    const nonScrollableWraps: { file: string; line: string }[] = []

    vueFiles.forEach(file => {
      const content = fs.readFileSync(file, 'utf-8')
      const wrapRegex = /<div\b([^>]*class="[^"]*(?:admin-table-wrap|legal-table-wrap|points-table-wrap)[^"]*"[^>]*)>/gi
      let match
      while ((match = wrapRegex.exec(content)) !== null) {
        const attrs = match[1]
        const hasRegion = /role="region"/i.test(attrs)
        const hasTabindex = /tabindex="0"/i.test(attrs)
        const hasLabel = /aria-label\s*=/i.test(attrs)
        if (!hasRegion || !hasTabindex || !hasLabel) {
          nonScrollableWraps.push({
            file: path.relative(BASE_DIR, file).replace(/\\/g, '/'),
            line: match[0]
          })
        }
      }
    })

    expect(nonScrollableWraps).toEqual([])
  })

  it('bảo đảm Breadcrumb navigation tuân thủ semantic WAI-ARIA breadcrumb pattern', () => {
    const breadcrumbContent = readFile('components/Breadcrumb.vue')
    expect(breadcrumbContent).toMatch(/aria-current="page"/)
    expect(breadcrumbContent).toMatch(/aria-label="Breadcrumb"|aria-label="Điều hướng phân cấp"/i)
  })

  it('bảo đảm các tệp CSS định nghĩa @keyframes đều có prefers-reduced-motion: reduce', () => {
    const cssFiles = getFiles(path.join(BASE_DIR, 'assets/css'), f => f.endsWith('.css'))
    const missingMotionGuards: string[] = []

    cssFiles.forEach(file => {
      const css = fs.readFileSync(file, 'utf-8')
      if (/@keyframes\b/.test(css)) {
        if (!/@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)/i.test(css)) {
          missingMotionGuards.push(path.relative(BASE_DIR, file).replace(/\\/g, '/'))
        }
      }
    })

    expect(missingMotionGuards).toEqual([])
  })
})
