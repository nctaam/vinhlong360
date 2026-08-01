import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '../../..')

function pageStyle(source: string): string {
  const start = source.indexOf('<style>')
  const end = source.indexOf('</style>', start)
  if (start < 0 || end < 0) throw new Error('Missing Homepage inline style')
  return source.slice(start + '<style>'.length, end)
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
  const cssList = config.slice(config.indexOf('css: ['), config.indexOf('],', config.indexOf('css: [')))
  const orderedGlobalFiles = [...cssList.matchAll(/'~\/assets\/css\/([^']+)'/g)].map(match => match[1]!)
  const globalCss = await Promise.all(
    orderedGlobalFiles.map(file => readFile(resolve(root, 'web-nuxt/assets/css', file), 'utf8')),
  )
  const indexSource = await readFile(resolve(root, 'web-nuxt/pages/index.vue'), 'utf8')
  const homeCss = await readFile(resolve(root, 'web-nuxt/assets/css/home-nocturne.css'), 'utf8')
  const stylesheet = document.createElement('style')
  const sources = [...globalCss, pageStyle(indexSource), homeCss]
  stylesheet.textContent = (options.srgbFallback ? sources.map(stripOklchSupports) : sources).join('\n')
  document.head.append(stylesheet)
  return stylesheet
}
