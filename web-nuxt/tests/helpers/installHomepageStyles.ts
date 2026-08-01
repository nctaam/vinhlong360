import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '../../..')

export type PageStyleEntry =
  | { kind: 'inline', css: string }
  | { kind: 'asset', path: string }

export function extractNuxtCssPaths(source: string): string[] {
  const cssKey = source.search(/\bcss\s*:/)
  if (cssKey < 0) throw new Error('Missing Nuxt css array')
  const open = source.indexOf('[', cssKey)
  if (open < 0) throw new Error('Missing Nuxt css array opening bracket')
  let depth = 0
  let close = -1
  for (let index = open; index < source.length; index += 1) {
    if (source[index] === '[') depth += 1
    if (source[index] === ']') depth -= 1
    if (depth === 0) {
      close = index
      break
    }
  }
  if (close < 0) throw new Error('Missing Nuxt css array closing bracket')
  const paths = [...source.slice(open + 1, close).matchAll(/["']~\/assets\/css\/([^"']+)["']/g)]
    .map(match => match[1]!)
  if (paths.length === 0) throw new Error('Nuxt css array contains no asset paths')
  return paths
}

export function extractPageStyleEntries(source: string): PageStyleEntry[] {
  const entries = [...source.matchAll(/<style\b([^>]*)>([\s\S]*?)<\/style>/gi)].map((match): PageStyleEntry => {
    const src = /\bsrc\s*=\s*["']~\/assets\/css\/([^"']+)["']/i.exec(match[1]!)
    return src ? { kind: 'asset', path: src[1]! } : { kind: 'inline', css: match[2]! }
  })
  if (entries.length === 0) throw new Error('Homepage contains no style blocks')
  if (!entries.some(entry => entry.kind === 'inline')) throw new Error('Homepage inline style block is missing')
  if (!entries.some(entry => entry.kind === 'asset' && entry.path === 'home-nocturne.css')) {
    throw new Error('Homepage home-nocturne.css style block is missing')
  }
  return entries
}

function stripOklchSupports(source: string): string {
  const marker = '@supports (color: oklch(0% 0 0))'
  let output = source
  let start = output.indexOf(marker)
  while (start >= 0) {
    const open = output.indexOf('{', start)
    if (open < 0) throw new Error('Malformed OKLCH support block')
    let depth = 0
    let end = -1
    for (let index = open; index < output.length; index += 1) {
      if (output[index] === '{') depth += 1
      if (output[index] === '}') depth -= 1
      if (depth === 0) {
        end = index + 1
        break
      }
    }
    if (end < 0) throw new Error('Unclosed OKLCH support block')
    output = `${output.slice(0, start)}${output.slice(end)}`
    start = output.indexOf(marker, start)
  }
  return output
}

export async function installActualHomepageStyles(options: { srgbFallback?: boolean } = {}): Promise<HTMLStyleElement> {
  const config = await readFile(resolve(root, 'web-nuxt/nuxt.config.ts'), 'utf8')
  const orderedGlobalFiles = extractNuxtCssPaths(config)
  if (!orderedGlobalFiles.includes('variables.css')) throw new Error('Nuxt variables.css input is missing')
  if (!orderedGlobalFiles.includes('tri-region-color.css')) throw new Error('Nuxt tri-region-color.css input is missing')
  const globalCss = await Promise.all(
    orderedGlobalFiles.map(file => readFile(resolve(root, 'web-nuxt/assets/css', file), 'utf8')),
  )
  const indexSource = await readFile(resolve(root, 'web-nuxt/pages/index.vue'), 'utf8')
  const pageCss = await Promise.all(extractPageStyleEntries(indexSource).map(entry => {
    return entry.kind === 'inline'
      ? Promise.resolve(entry.css)
      : readFile(resolve(root, 'web-nuxt/assets/css', entry.path), 'utf8')
  }))
  const stylesheet = document.createElement('style')
  const sources = [...globalCss, ...pageCss]
  stylesheet.textContent = (options.srgbFallback ? sources.map(stripOklchSupports) : sources).join('\n')
  document.head.append(stylesheet)
  return stylesheet
}
