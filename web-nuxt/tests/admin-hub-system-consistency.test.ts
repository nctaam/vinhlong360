import { describe, expect, it } from 'vitest'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { resolve, join } from 'node:path'

function getVueFiles(dir: string): string[] {
  let results: string[] = []
  const list = readdirSync(dir)
  for (const file of list) {
    const filePath = join(dir, file)
    const stat = statSync(filePath)
    if (stat && stat.isDirectory()) {
      results = results.concat(getVueFiles(filePath))
    } else if (file.endsWith('.vue')) {
      results.push(filePath)
    }
  }
  return results
}

describe('Admin Hub & Complete 74-Page System Consistency (Moc 135)', () => {
  describe('Admin Shell Layout (layouts/admin.vue)', () => {
    it('sets tri-region color system and accessible workbench chrome', () => {
      const src = readFileSync(resolve(__dirname, '../layouts/admin.vue'), 'utf8')
      expect(src).toContain('data-color-system="tri-region-v1"')
      expect(src).toContain('data-admin-density="dense-workbench"')
      expect(src).toContain('href="#admin-main"')
    })
  })

  describe('Admin Backoffice Pages Quality Standards (pages/admin/*)', () => {
    const adminDir = resolve(__dirname, '../pages/admin')
    const adminPages = getVueFiles(adminDir)

    it('finds at least 30 admin management pages', () => {
      expect(adminPages.length).toBeGreaterThanOrEqual(30)
    })

    const FILLERS = [
      'miền Tây',
      'sông nước hữu tình',
      'thiên đường',
      'hidden gem',
      'must-see',
      'không thể bỏ lỡ',
      'đắm chìm',
      'hòa mình vào',
      'điểm đến lý tưởng',
    ]

    for (const pagePath of adminPages) {
      const relPath = pagePath.replace(resolve(__dirname, '..'), '').replace(/\\/g, '/')
      it(`${relPath} complies with radius scale, zero hex debt, and tone of voice`, () => {
        const src = readFileSync(pagePath, 'utf8')

        // 1. No old radius scale
        const style = src.match(/<style[^>]*>([\s\S]*?)<\/style>/)?.[1] || ''
        expect(style).not.toMatch(/--radius-(?:xs|sm|md|lg|xl)\b/)

        // 2. No CSS raw hex
        expect(style).not.toMatch(/:\s*#[0-9a-fA-F]{3,8}\b/)

        // 3. No voice fillers
        for (const filler of FILLERS) {
          expect(src.toLowerCase()).not.toContain(filler.toLowerCase())
        }
      })
    }
  })

  describe('Full 74-Page Catalog Coverage', () => {
    const pagesDir = resolve(__dirname, '../pages')
    const allPages = getVueFiles(pagesDir)

    it('contains all 74 application pages across public and admin domains', () => {
      expect(allPages.length).toBe(74)
    })

    it('enforces Clean Code SFC line ceilings on the largest core pages', () => {
      const checkMaxLines = (rel: string, max: number) => {
        const full = resolve(pagesDir, rel)
        const lines = readFileSync(full, 'utf8').split('\n').length
        expect(lines).toBeLessThanOrEqual(max)
      }

      checkMaxLines('dia-diem/[id].vue', 1200)
      checkMaxLines('tao-lich-trinh.vue', 1500)
      checkMaxLines('tim-kiem.vue', 1100)
      checkMaxLines('xa-phuong/[id].vue', 1050)
    })
  })
})
