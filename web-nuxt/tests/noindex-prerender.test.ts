import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const readSource = (file: string) => readFileSync(resolve(process.cwd(), file), 'utf8').replaceAll('\r\n', '\n')

describe('global noindex posture', () => {
  it('keeps the global app head fail-closed for prerendered HTML', () => {
    const config = readSource('nuxt.config.ts')
    const robotsContent = config.match(/\{\s*name:\s*'robots',\s*content:\s*'([^']+)'\s*\}/)?.[1]

    expect(robotsContent).toBe('noindex, follow')
    expect(config).not.toContain("name: 'robots', content: 'index, follow")
  })

  it('keeps the dynamic noindex response middleware in place', () => {
    const middleware = readSource('server/middleware/noindex.ts')

    expect(middleware).toContain("setResponseHeader(event, 'X-Robots-Tag', 'noindex, follow')")
  })
})
