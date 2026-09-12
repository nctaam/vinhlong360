import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Public Shell Polish', () => {
  const shellCss = readFileSync(resolve(__dirname, '../assets/css/shell.css'), 'utf8')

  it('implements frosted glass backdrop and refined brand mark in shell.css', () => {
    expect(shellCss).toContain('--glass-frosted-nav')
    expect(shellCss).toContain('--radius-control-refined')
  })
})
