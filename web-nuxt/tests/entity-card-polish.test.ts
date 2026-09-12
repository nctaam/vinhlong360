import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('EntityCard Polish', () => {
  const cardsCss = readFileSync(resolve(__dirname, '../assets/css/cards.css'), 'utf8')

  it('applies refined radius and hover shadow to entity cards', () => {
    expect(cardsCss).toContain('--radius-surface-refined')
    expect(cardsCss).toContain('--shadow-card-hover')
  })
})
