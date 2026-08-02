import { readdir, readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(import.meta.dirname, '..')
const legacyActionToken = /var\(--primary(?:-[a-z-]+)?\)/

type CssSource = { from: string, css: string }
type CssRule = { from: string, selector: string, body: string, atRules: string[] }

function skipComment(source: string, start: number) {
  const close = source.indexOf('*/', start + 2)
  if (close < 0) throw new Error('Unclosed CSS comment')
  return close + 2
}

function skipString(source: string, start: number) {
  const quote = source[start]
  let cursor = start + 1
  while (cursor < source.length) {
    if (source[cursor] === '\\') cursor += 2
    else if (source[cursor] === quote) return cursor + 1
    else cursor += 1
  }
  throw new Error('Unclosed CSS string')
}

function findClosingBrace(source: string, open: number, limit: number) {
  let depth = 1
  let cursor = open + 1
  while (cursor < limit) {
    if (source.startsWith('/*', cursor)) cursor = skipComment(source, cursor)
    else if (source[cursor] === '"' || source[cursor] === "'") cursor = skipString(source, cursor)
    else if (source[cursor] === '{') {
      depth += 1
      cursor += 1
    }
    else if (source[cursor] === '}') {
      depth -= 1
      if (depth === 0) return cursor
      cursor += 1
    }
    else cursor += 1
  }
  throw new Error('Unclosed CSS block')
}

function cleanCssFragment(value: string) {
  return value.replace(/\/\*[\s\S]*?\*\//g, ' ').trim()
}

function readCssRules({ from, css }: CssSource): CssRule[] {
  const rules: CssRule[] = []

  function walk(start: number, end: number, atRules: string[]) {
    let cursor = start
    while (cursor < end) {
      while (cursor < end) {
        if (/\s/.test(css[cursor]!)) cursor += 1
        else if (css.startsWith('/*', cursor)) cursor = skipComment(css, cursor)
        else break
      }
      if (cursor >= end) return

      const preludeStart = cursor
      let parentheses = 0
      let brackets = 0
      let terminated = false

      while (cursor < end) {
        if (css.startsWith('/*', cursor)) {
          cursor = skipComment(css, cursor)
          continue
        }
        if (css[cursor] === '"' || css[cursor] === "'") {
          cursor = skipString(css, cursor)
          continue
        }

        const char = css[cursor]
        if (char === '(') parentheses += 1
        else if (char === ')') parentheses -= 1
        else if (char === '[') brackets += 1
        else if (char === ']') brackets -= 1
        else if (parentheses === 0 && brackets === 0 && char === ';') {
          cursor += 1
          terminated = true
          break
        }
        else if (parentheses === 0 && brackets === 0 && char === '{') {
          const prelude = cleanCssFragment(css.slice(preludeStart, cursor))
          if (!prelude) throw new Error(`Missing CSS prelude in ${from}`)
          const close = findClosingBrace(css, cursor, end)
          if (prelude.startsWith('@')) walk(cursor + 1, close, [...atRules, prelude])
          else rules.push({ from, selector: prelude, body: css.slice(cursor + 1, close), atRules })
          cursor = close + 1
          terminated = true
          break
        }
        else if (parentheses === 0 && brackets === 0 && char === '}') {
          throw new Error(`Unexpected CSS closing brace in ${from}`)
        }
        cursor += 1
      }

      if (!terminated) {
        if (cleanCssFragment(css.slice(preludeStart, end))) throw new Error(`Unterminated CSS statement in ${from}`)
        return
      }
    }
  }

  walk(0, css.length, [])
  return rules
}

function readDeclarations(rule: CssRule) {
  const declarations: Array<{ property: string, value: string }> = []
  let cursor = 0
  let start = 0
  let parentheses = 0
  let brackets = 0

  const addDeclaration = (end: number) => {
    const statement = cleanCssFragment(rule.body.slice(start, end))
    if (!statement) return
    if (statement.includes('{') || statement.includes('}')) {
      throw new Error(`Unsupported nested selector in ${rule.from}: ${rule.selector}`)
    }
    const colon = statement.indexOf(':')
    if (colon < 1) throw new Error(`Malformed declaration in ${rule.from}: ${statement}`)
    declarations.push({
      property: statement.slice(0, colon).trim().toLowerCase(),
      value: statement.slice(colon + 1).trim(),
    })
  }

  while (cursor < rule.body.length) {
    if (rule.body.startsWith('/*', cursor)) cursor = skipComment(rule.body, cursor)
    else if (rule.body[cursor] === '"' || rule.body[cursor] === "'") cursor = skipString(rule.body, cursor)
    else {
      const char = rule.body[cursor]
      if (char === '(') parentheses += 1
      else if (char === ')') parentheses -= 1
      else if (char === '[') brackets += 1
      else if (char === ']') brackets -= 1
      else if (char === ';' && parentheses === 0 && brackets === 0) {
        addDeclaration(cursor)
        start = cursor + 1
      }
      cursor += 1
    }
  }
  addDeclaration(rule.body.length)
  return declarations
}

function selectorTargets(selector: string, target: '.auth-btn' | '.chat-fab') {
  const className = target.slice(1)
  return new RegExp(`(^|[^a-zA-Z0-9_-])\\.${className}(?![a-zA-Z0-9_-])`).test(selector)
}

function isForcedColorsRule(rule: CssRule) {
  return rule.atRules.some(atRule => /^@media\b/i.test(atRule) && /forced-colors\s*:\s*active/i.test(atRule))
}

function expectedTokens(target: '.auth-btn' | '.chat-fab', property: string) {
  if (target === '.chat-fab') {
    if (property === 'background' || property === 'background-color') return ['--color-action', '--color-action-hover']
    if (property === 'color' || property === 'fill' || property === 'stroke') return ['--color-on-action']
    if (property === 'box-shadow' || property === 'text-shadow') return ['--color-action-rgb']
    if (property === 'outline' || property === 'outline-color') return ['--color-focus']
    if (/^border(?:-(?:top|right|bottom|left))?(?:-color)?$/.test(property)) return []
  }
  else {
    if (property === 'background' || property === 'background-color') return ['--color-action-surface', '--color-action-surface-hover']
    if (property === 'color' || property === 'fill' || property === 'stroke') return ['--color-action', '--color-action-hover']
    if (property === 'box-shadow' || property === 'text-shadow') return ['--color-action-rgb']
    if (property === 'outline' || property === 'outline-color') return ['--color-focus']
    if (/^border(?:-(?:top|right|bottom|left))?(?:-color)?$/.test(property)) {
      return ['--color-action-border', '--color-action', '--color-action-hover']
    }
  }
  return null
}

function isNeutralProtectedValue(property: string, value: string) {
  const normalized = value.replace(/\s*!important\s*$/i, '').trim().toLowerCase()
  if ((property === 'fill' || property === 'stroke') && normalized === 'currentcolor') return true
  return /^(?:none|0(?:\s+none)?)$/.test(normalized)
}

function expectSemanticCascade(sources: CssSource[], target: '.auth-btn' | '.chat-fab') {
  const relevantRules = sources.flatMap(readCssRules).filter(rule => selectorTargets(rule.selector, target))
  expect(relevantRules.length, `Missing ${target} cascade`).toBeGreaterThan(0)

  for (const rule of relevantRules) {
    for (const { property, value } of readDeclarations(rule)) {
      if (legacyActionToken.test(value)) {
        throw new Error(`Legacy action token in ${rule.from} ${rule.selector}: ${property}: ${value}`)
      }

      const tokens = expectedTokens(target, property)
      if (tokens === null || isForcedColorsRule(rule) || isNeutralProtectedValue(property, value)) continue
      if (!tokens.some(token => value.includes(`var(${token})`))) {
        throw new Error(`Non-semantic ${target} color in ${rule.from} ${rule.selector}: ${property}: ${value}`)
      }
    }
  }
}

async function readActionCssSources() {
  const cssRoot = resolve(root, 'assets/css')
  const names = (await readdir(cssRoot)).filter(name => name.endsWith('.css')).sort()
  return Promise.all(names.map(async name => ({
    from: `assets/css/${name}`,
    css: await readFile(resolve(cssRoot, name), 'utf8'),
  })))
}

function readRule(source: string, selector: string) {
  const marker = `${selector} {`
  const start = source.indexOf(marker)
  if (start < 0) throw new Error(`Missing CSS rule: ${selector}`)
  const open = source.indexOf('{', start)
  const close = source.indexOf('}', open)
  if (close < 0) throw new Error(`Unclosed CSS rule: ${selector}`)
  return source.slice(open + 1, close)
}

function expectLoginRecipe(css: string) {
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
}

function expectChatRecipe(css: string) {
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
}

describe('Global public-shell action color contract', () => {
  it('keeps the secondary login recipe entirely on River action semantics', async () => {
    const css = await readFile(resolve(root, 'assets/css/components.css'), 'utf8')
    expectLoginRecipe(css)
    expectSemanticCascade(await readActionCssSources(), '.auth-btn')
  })

  it('keeps the primary Chat AI recipe entirely on River action semantics', async () => {
    const css = await readFile(resolve(root, 'assets/css/base.css'), 'utf8')
    expectChatRecipe(css)
  })

  it('keeps every Chat AI cascade source, including Nocturne shadows, on River semantics', async () => {
    expectSemanticCascade(await readActionCssSources(), '.chat-fab')
  })

  it('rejects a later theme-qualified Chat AI legacy override', async () => {
    const css = await readFile(resolve(root, 'assets/css/base.css'), 'utf8')
    const mutated = `${css}\n@media (prefers-color-scheme: dark) { .dark .chat-fab { background: var(--primary); } }`

    expect(() => expectSemanticCascade([{ from: 'mutated-base.css', css: mutated }], '.chat-fab'))
      .toThrow(/Legacy action token.*--primary/)
  })

  it('rejects a later stronger login legacy override', async () => {
    const css = await readFile(resolve(root, 'assets/css/components.css'), 'utf8')
    const mutated = `${css}\n@media (min-width: 1px) { .public-shell .auth-btn { color: var(--primary-fg); } }`

    expect(() => expectSemanticCascade([{ from: 'mutated-components.css', css: mutated }], '.auth-btn'))
      .toThrow(/Legacy action token.*--primary-fg/)
  })
})
