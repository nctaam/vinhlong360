// @vitest-environment node

import { loadNuxtConfig } from '@nuxt/kit'
import { afterEach, describe, expect, it } from 'vitest'

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
  it('defaults resolved runtime config closed without a second static robots authority', async () => {
    const config = await loadConfig()

    expect(config.runtimeConfig.public.siteNoindex).toBe(true)
    expect(robotsContent(config)).toBeUndefined()
  })

  it('does not activate static robots metadata when the legacy runtime flag is false', async () => {
    const config = await loadConfig('false')

    expect(config.runtimeConfig.public.siteNoindex).toBe(false)
    expect(robotsContent(config)).toBeUndefined()
  })

  it('leaves HTML robots headers to the request-local final response writer', async () => {
    const config = await loadConfig()

    expect(globalNitroHeaders(config)).not.toHaveProperty('X-Robots-Tag')
  })

  it('removes the global static response header when indexing is opened', async () => {
    const config = await loadConfig('false')

    expect(globalNitroHeaders(config)).not.toHaveProperty('X-Robots-Tag')
  })

})
