// @vitest-environment node
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'
import { DEFAULT_ROUTES } from '../../utils/routesContent'

function walkVueFiles(dir: string, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) {
      walkVueFiles(full, acc)
    } else if (full.endsWith('.vue')) {
      acc.push(full)
    }
  }
  return acc
}

function extractTemplateWithoutComments(source: string): string {
  const match = /<template\b[^>]*>([\s\S]*?)<\/template>/i.exec(source)
  const tpl = match ? match[1] : source
  return tpl.replace(/<!--[\s\S]*?-->/g, (comment) => comment.replace(/[^\n]/g, ' '))
}

describe('HTML <button>, <img> decoding, and route metadata discipline (QW-39 & QW-40)', () => {
  const cwd = process.cwd()
  const root = existsSync(join(cwd, 'components')) ? cwd : join(cwd, 'web-nuxt')
  const vueFiles = [
    ...walkVueFiles(join(root, 'components')),
    ...walkVueFiles(join(root, 'pages')),
  ]

  it('requires every <button> in components/ and pages/ to declare an explicit type attribute', () => {
    const offenders: string[] = []
    const buttonTagRe = /<button\b((?:[^>"']|"[^"]*"|'[^']*')*)>/gs

    for (const file of vueFiles) {
      const content = extractTemplateWithoutComments(readFileSync(file, 'utf8'))
      let match: RegExpExecArray | null
      while ((match = buttonTagRe.exec(content)) !== null) {
        const attrs = match[1] || ''
        if (!/\b:?type\s*=/.test(attrs)) {
          const line = content.slice(0, match.index).split('\n').length
          offenders.push(`${relative(root, file).replace(/\\/g, '/')}:${line}`)
        }
      }
    }

    expect(offenders).toEqual([])
  })

  it('requires every <img> in components/ and pages/ to declare decoding="async"', () => {
    const offenders: string[] = []
    const imgTagRe = /<img\b((?:[^>"']|"[^"]*"|'[^']*')*)>/gs

    for (const file of vueFiles) {
      const content = extractTemplateWithoutComments(readFileSync(file, 'utf8'))
      let match: RegExpExecArray | null
      while ((match = imgTagRe.exec(content)) !== null) {
        const attrs = match[1] || ''
        if (!/\bdecoding\s*=\s*["']async["']/.test(attrs)) {
          const line = content.slice(0, match.index).split('\n').length
          offenders.push(`${relative(root, file).replace(/\\/g, '/')}:${line}`)
        }
      }
    }

    expect(offenders).toEqual([])
  })

  it('keeps DEFAULT_ROUTES free of raw pictograph emojis (R30.2 Quiet Luxury)', () => {
    const pictographRe = /[\u{1F300}-\u{1FAFF}]/u
    for (const route of DEFAULT_ROUTES) {
      expect(pictographRe.test(route.emoji)).toBe(false)
    }
  })
})
