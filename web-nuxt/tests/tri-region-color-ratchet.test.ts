import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

describe('tri-region color debt ratchet', () => {
  it('keeps scoped wave files semantic and shared compatibility debt non-increasing', () => {
    const output = execFileSync(process.execPath, ['scripts/check-tri-region-color-debt.mjs'], {
      cwd: resolve(import.meta.dirname, '..'),
      encoding: 'utf8',
    })
    expect(output).toContain('tri-region color debt: PASS')
  })
})
