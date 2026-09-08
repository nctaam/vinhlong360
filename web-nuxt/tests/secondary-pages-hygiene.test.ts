import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Moc 146: Secondary & Account Pages Radius Hygiene & Integrity', () => {
  it('enforces R30.8 Radius Token Law across account, notifications, user, and regional pages', () => {
    const rootDir = resolve(__dirname, '..')
    const pagesToCheck = [
      'pages/khu-vuc/[area].vue',
      'pages/lich-trinh-chia-se/[id].vue',
      'pages/tai-khoan.vue',
      'pages/thong-bao.vue',
      'pages/nguoi-dung/[id].vue',
    ]

    for (const relPath of pagesToCheck) {
      const content = readFileSync(resolve(rootDir, relPath), 'utf-8')
      expect(content).not.toContain('var(--radius-full)')
      expect(content).not.toMatch(/--radius-full\b/)
    }
  })

  it('strictly protects line count ceilings for the 4 critical pages', () => {
    const rootDir = resolve(__dirname, '..')
    const ceilings: Record<string, number> = {
      'pages/dia-diem/[id].vue': 1200,
      'pages/tao-lich-trinh.vue': 1050,
      'pages/tim-kiem.vue': 1100,
      'pages/xa-phuong/[id].vue': 1050,
      'pages/cong-dong.vue': 1050,
      'pages/cai-dat.vue': 1100,
      'pages/nguoi-dung/[id].vue': 1100,
      'pages/admin/entities.vue': 1050,
    }

    for (const [relPath, maxLines] of Object.entries(ceilings)) {
      const content = readFileSync(resolve(rootDir, relPath), 'utf-8')
      const lineCount = content.split('\n').length
      expect(lineCount).toBeLessThan(maxLines)
    }
  })
})
