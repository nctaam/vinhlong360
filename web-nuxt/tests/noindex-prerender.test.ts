// @vitest-environment node

import { loadNuxtConfig } from '@nuxt/kit'
import { afterEach, describe, expect, it } from 'vitest'

const permissiveRobots = 'index, follow, max-image-preview:large, max-snippet:-1'
const originalSiteNoindex = process.env.NUXT_PUBLIC_SITE_NOINDEX

const loadConfig = async (siteNoindex?: string) => {
  if (siteNoindex === undefined) {
    delete process.env.NUXT_PUBLIC_SITE_NOINDEX
  }
  else {
    process.env.NUXT_PUBLIC_SITE_NOINDEX = siteNoindex
  }

  return loadNuxtConfig({ cwd: process.cwd(), dotenv: false })
}

const robotsContent = (config: Awaited<ReturnType<typeof loadNuxtConfig>>) =>
  (config.app.head.meta ?? []).find(entry => 'name' in entry && entry.name === 'robots')?.content

const globalNitroHeaders = (config: Awaited<ReturnType<typeof loadNuxtConfig>>) =>
  config.nitro?.routeRules?.['/**']?.headers

afterEach(() => {
  if (originalSiteNoindex === undefined) {
    delete process.env.NUXT_PUBLIC_SITE_NOINDEX
  }
  else {
    process.env.NUXT_PUBLIC_SITE_NOINDEX = originalSiteNoindex
  }
})

describe('global noindex posture', () => {
  it('defaults resolved runtime config and prerender metadata to noindex', async () => {
    const config = await loadConfig()

    expect(config.runtimeConfig.public.siteNoindex).toBe(true)
    expect(robotsContent(config)).toBe('noindex, follow')
  })

  it('opens resolved runtime config and prerender metadata together', async () => {
    const config = await loadConfig('false')

    expect(config.runtimeConfig.public.siteNoindex).toBe(false)
    expect(robotsContent(config)).toBe(permissiveRobots)
  })

  it('defaults prerender and static responses to the global noindex header', async () => {
    const config = await loadConfig()

    expect(globalNitroHeaders(config)).toHaveProperty('X-Robots-Tag', 'noindex, follow')
  })

  it('removes the global static response header when indexing is opened', async () => {
    const config = await loadConfig('false')

    expect(globalNitroHeaders(config)).not.toHaveProperty('X-Robots-Tag')
  })

})
