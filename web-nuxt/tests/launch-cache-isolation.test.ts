// @vitest-environment node

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const configPath = resolve(process.cwd(), 'nuxt.config.ts')
const buildWrapperPath = resolve(process.cwd(), '..', 'scripts', 'build-prerender.sh')

interface LaunchOutputAuditInput {
  readonly publicFiles: readonly string[]
  readonly routeRules: Readonly<Record<string, Readonly<Record<string, unknown>>>>
}

function auditLaunchOutput(input: LaunchOutputAuditInput): void {
  const publicHtml = input.publicFiles.filter((file) =>
    file.startsWith('public/') && /\.html(?:\.(?:br|gz))?$/.test(file),
  )
  if (publicHtml.length > 0) {
    throw new Error(`launch build emitted public HTML: ${publicHtml.join(', ')}`)
  }

  for (const [path, rule] of Object.entries(input.routeRules)) {
    if ('swr' in rule || 'isr' in rule || 'cache' in rule) {
      throw new Error(`launch build emitted a policy-bearing cache rule: ${path}`)
    }
    const headers = rule.headers as Readonly<Record<string, unknown>> | undefined
    if (
      headers?.['cache-control'] !== undefined
      && (path !== '/_nuxt/**' || headers['cache-control'] !== 'public, max-age=31536000, immutable')
    ) {
      throw new Error(`launch build emitted a policy-bearing cache rule: ${path}`)
    }
  }
}

describe('launch cache isolation', () => {
  it('contains no policy-bearing SWR or prerender routes', () => {
    const config = readFileSync(configPath, 'utf8')
    for (const path of ['/dia-diem/**', '/api/entities/**', '/sitemap.xml', 'prerender:']) {
      expect(config).not.toContain(path)
    }
    expect(config).not.toContain('swr:')
    expect(config).not.toContain('isr:')
  })

  it('keeps only immutable Nuxt assets and global security headers', () => {
    const config = readFileSync(configPath, 'utf8')
    const nitroRules = config.slice(config.indexOf('    routeRules:', config.indexOf('  nitro:')))

    expect(nitroRules).toContain("'/_nuxt/**'")
    expect(nitroRules).toContain("'/**'")
    expect(nitroRules).toContain('immutable')
    expect(nitroRules).not.toContain('swr')
    expect(nitroRules).not.toContain('isr')
    expect(nitroRules).not.toContain("'/api/")
  })

  it('rejects public HTML and policy-bearing cache rules in built-output audit input', () => {
    const cleanFixture: LaunchOutputAuditInput = {
      publicFiles: ['public/_nuxt/app.abc123.js', 'public/favicon.svg'],
      routeRules: {
        '/api/**': { proxy: 'http://backend/api/**' },
        '/_nuxt/**': { headers: { 'cache-control': 'public, max-age=31536000, immutable' } },
        '/**': { headers: { 'X-Content-Type-Options': 'nosniff' } },
      },
    }
    expect(() => auditLaunchOutput(cleanFixture)).not.toThrow()

    expect(() => auditLaunchOutput({
      ...cleanFixture,
      publicFiles: [...cleanFixture.publicFiles, 'public/dia-diem/index.html'],
    })).toThrow(/public HTML/)

    expect(() => auditLaunchOutput({
      ...cleanFixture,
      routeRules: {
        ...cleanFixture.routeRules,
        '/dia-diem/**': { swr: 3600 },
      },
    })).toThrow(/cache rule/)
  })

  it('repurposes the legacy build wrapper without a backend-gated prerender step', () => {
    const script = readFileSync(buildWrapperPath, 'utf8')
    expect(script).toContain('npm run build')
    expect(script).not.toContain('localhost:8360')
    expect(script).not.toContain('nuxt generate')
  })

  it('does not expose nuxt generate through the package scripts', () => {
    const packageJson = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf8')) as {
      scripts?: Record<string, string>
    }
    expect(Object.values(packageJson.scripts ?? {})).not.toContain('nuxt generate')
  })
})
