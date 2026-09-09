import { afterEach, describe, expect, it, vi } from 'vitest'

import { loadMapLibre } from '../utils/maplibre-loader'

describe('maplibre loader', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    document.querySelectorAll('script[data-vl360-maplibre]').forEach((script) => script.remove())
  })

  it('loads the UMD CSP asset and resolves the global MapLibre API', async () => {
    const maplibregl = { Map: class Map {}, setWorkerUrl: vi.fn() }
    let appendedScript: HTMLScriptElement | undefined

    vi.spyOn(document.head, 'appendChild').mockImplementation((node) => {
      if (node instanceof HTMLScriptElement && node.dataset.vl360Maplibre === 'true') {
        appendedScript = node
        vi.stubGlobal('maplibregl', maplibregl)
        node.dispatchEvent(new Event('load'))
      }
      return node
    })

    await expect(loadMapLibre()).resolves.toBe(maplibregl)
    expect(appendedScript).toMatchObject({
      src: expect.stringContaining('/maplibre-gl-csp.js'),
    })
  })
})
