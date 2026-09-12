import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('WCAG 2.2 AAA Accessibility Refinements', () => {
  const root = resolve(__dirname, '..')
  const catalogCss = readFileSync(resolve(root, 'assets/css/catalog.css'), 'utf8')
  const adminLayout = readFileSync(resolve(root, 'layouts/admin.vue'), 'utf8')

  it('equips .afl-clear-all with 44px minimum touch target pseudo-element', () => {
    expect(catalogCss).toMatch(/\.afl-clear-all::before\s*\{[^}]*min-height:\s*44px;/)
  })

  it('equips admin main element with tabindex="-1" for accessible skip-link focus transfer', () => {
    expect(adminLayout).toMatch(/<main[^>]*id="admin-main"[^>]*tabindex="-1"/)
  })
})
