// @vitest-environment node

import { loadNuxtConfig } from '@nuxt/kit'
import { afterEach, describe, expect, it, vi } from 'vitest'

import noindexMiddleware from '../server/middleware/noindex'

const runtimeConfigState = vi.hoisted(() => ({ siteNoindex: true }))

vi.mock('nitropack/runtime', () => ({
  useRuntimeConfig: () => ({ public: { siteNoindex: runtimeConfigState.siteNoindex } }),
}))

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
  runtimeConfigState.siteNoindex = true

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

  it.each([
    { siteNoindex: true, expectedHeader: 'noindex, follow' },
    { siteNoindex: false, expectedHeader: undefined },
  ])('sets the dynamic header only when siteNoindex is $siteNoindex', async ({ siteNoindex, expectedHeader }) => {
    runtimeConfigState.siteNoindex = siteNoindex
    const setHeader = vi.fn()
    const event = {
      node: { res: { setHeader } },
    }

    await noindexMiddleware(event as never)

    if (expectedHeader) {
      expect(setHeader).toHaveBeenCalledWith('X-Robots-Tag', expectedHeader)
    }
    else {
      expect(setHeader).not.toHaveBeenCalled()
    }
  })
})
