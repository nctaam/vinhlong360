import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Public Shell Polish', () => {
  const shellCss = readFileSync(resolve(__dirname, '../assets/css/shell.css'), 'utf8')

  it('implements frosted glass backdrop and refined brand mark in shell.css', () => {
    expect(shellCss).toContain('--glass-frosted-nav')
    expect(shellCss).toContain('--radius-control-refined')
  })

  it('equips desktop .public-shell-command-row .auth-btn with >= 44x44px touch target expansion', () => {
    expect(shellCss).toMatch(/\.public-shell-command-row\s+\.auth-btn\s*\{[^}]*position:\s*relative;/)
    expect(shellCss).toMatch(/\.public-shell-command-row\s+\.auth-btn::before\s*\{[^}]*min-height:\s*44px;/)
    expect(shellCss).toMatch(/\.public-shell-command-row\s+\.auth-btn::before\s*\{[^}]*min-width:\s*44px;/)
  })
})
