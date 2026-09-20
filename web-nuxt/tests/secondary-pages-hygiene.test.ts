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

  it('features 24/7 emergency rescue hotline strip and district tabs in danh-ba.vue', () => {
    const rootDir = resolve(__dirname, '..')
    const src = readFileSync(resolve(rootDir, 'pages/danh-ba.vue'), 'utf-8')
    expect(src).toContain('emergency-hotline-strip')
    expect(src).toContain('district-filter-tabs')
  })

  it('verifies admin dashboard contains modernized KPI card grids', () => {
    const rootDir = resolve(__dirname, '..')
    const adminHome = readFileSync(resolve(rootDir, 'pages/admin/index.vue'), 'utf-8')
    expect(adminHome).toContain('admin-metric-card')
    expect(adminHome).toContain('metric-trend-indicator')
  })

  it('provides side-by-side data quality diff inspector in admin/data-quality.vue', () => {
    const rootDir = resolve(__dirname, '..')
    const dq = readFileSync(resolve(rootDir, 'pages/admin/data-quality.vue'), 'utf-8')
    expect(dq).toContain('quality-diff-inspector')
  })

  it('strictly protects line count ceilings for the 4 critical pages', () => {
    const rootDir = resolve(__dirname, '..')
    const ceilings: Record<string, number> = {
      'pages/dia-diem/[id].vue': 1200,
      'pages/tao-lich-trinh.vue': 1050,
      'pages/tim-kiem.vue': 1100,
      'pages/xa-phuong/[id].vue': 1050,
      'pages/cong-dong.vue': 990,
      'pages/cai-dat.vue': 980,
      'pages/nguoi-dung/[id].vue': 1050,
      'pages/admin/entities.vue': 950,
    }

    for (const [relPath, maxLines] of Object.entries(ceilings)) {
      const content = readFileSync(resolve(rootDir, relPath), 'utf-8')
      const lineCount = content.split('\n').length
      expect(lineCount).toBeLessThan(maxLines)
    }
  })
})
