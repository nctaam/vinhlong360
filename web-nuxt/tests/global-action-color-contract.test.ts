import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(import.meta.dirname, '..')

function readRule(source: string, selector: string) {
  const marker = `${selector} {`
  const start = source.indexOf(marker)
  if (start < 0) throw new Error(`Missing CSS rule: ${selector}`)
  const open = source.indexOf('{', start)
  const close = source.indexOf('}', open)
  if (close < 0) throw new Error(`Unclosed CSS rule: ${selector}`)
  return source.slice(open + 1, close)
}

describe('Global public-shell action color contract', () => {
  it('keeps the secondary login recipe entirely on River action semantics', async () => {
    const css = await readFile(resolve(root, 'assets/css/components.css'), 'utf8')
    const defaultRule = readRule(css, '.auth-btn')
    const hoverRule = readRule(css, '.auth-btn:hover')
    const activeRule = readRule(css, '.auth-btn:active')
    const focusRule = readRule(css, '.auth-btn:focus-visible')
    const recipe = [defaultRule, hoverRule, activeRule, focusRule].join('\n')

    expect(defaultRule).toMatch(/border:\s*2px solid var\(--color-action-border\)/)
    expect(defaultRule).toMatch(/background:\s*var\(--color-action-surface\)/)
    expect(defaultRule).toMatch(/color:\s*var\(--color-action\)/)
    expect(hoverRule).toMatch(/border-color:\s*var\(--color-action\)/)
    expect(hoverRule).toMatch(/background:\s*var\(--color-action-surface-hover\)/)
    expect(hoverRule).toMatch(/color:\s*var\(--color-action-hover\)/)
    expect(activeRule).toMatch(/border-color:\s*var\(--color-action-hover\)/)
    expect(activeRule).toMatch(/background:\s*var\(--color-action-surface-hover\)/)
    expect(focusRule).toMatch(/outline:\s*2px solid var\(--color-focus\)/)
    expect(recipe).not.toMatch(/var\(--primary(?:-[a-z-]+)?\)/)
  })

  it('keeps the primary Chat AI recipe entirely on River action semantics', async () => {
    const css = await readFile(resolve(root, 'assets/css/base.css'), 'utf8')
    const defaultRule = readRule(css, '.chat-fab')
    const hoverRule = readRule(css, '.chat-fab:hover')
    const activeRule = readRule(css, '.chat-fab:active')
    const focusRule = readRule(css, '.chat-fab:focus-visible')
    const openRule = readRule(css, '.chat-fab.open')
    const recipe = [defaultRule, hoverRule, activeRule, focusRule, openRule].join('\n')

    expect(defaultRule).toMatch(/background:\s*var\(--color-action\)/)
    expect(defaultRule).toMatch(/color:\s*var\(--color-on-action\)/)
    expect(defaultRule).toMatch(/rgba\(var\(--color-action-rgb\),\s*\.25\)/)
    expect(hoverRule).toMatch(/background:\s*var\(--color-action-hover\)/)
    expect(hoverRule).toMatch(/rgba\(var\(--color-action-rgb\),\s*\.35\)/)
    expect(activeRule).toMatch(/background:\s*var\(--color-action-hover\)/)
    expect(focusRule).toMatch(/outline:\s*2px solid var\(--color-focus\)/)
    expect(openRule).toMatch(/background:\s*var\(--color-action-hover\)/)
    expect(recipe).not.toMatch(/var\(--primary(?:-[a-z-]+)?\)/)
  })
})
