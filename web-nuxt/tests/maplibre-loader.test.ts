import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

describe('maplibre loader', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    document.querySelectorAll('script[data-vl360-maplibre]').forEach((script) => script.remove())
  })

  it('loads the same-origin ESM wrapper and resolves the global MapLibre API', async () => {
    const { loadMapLibre } = await import('../utils/maplibre-loader')
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
      src: expect.stringContaining('/maplibre-gl-loader.mjs'),
      type: 'module',
    })
  })

  it('removes a failed script so a later call can retry successfully', async () => {
    const { loadMapLibre } = await import('../utils/maplibre-loader')
    const maplibregl = { Map: class Map {}, setWorkerUrl: vi.fn() }
    const appendChild = document.head.appendChild.bind(document.head)
    let attempt = 0

    vi.spyOn(document.head, 'appendChild').mockImplementation((node) => {
      // Keep a real DOM node without letting Happy DOM fetch the synthetic URL.
      if (node instanceof HTMLScriptElement) node.removeAttribute('src')
      const appended = appendChild(node)
      if (node instanceof HTMLScriptElement && node.dataset.vl360Maplibre === 'true') {
        attempt += 1
        if (attempt === 1) node.dispatchEvent(new Event('error'))
        else {
          vi.stubGlobal('maplibregl', maplibregl)
          node.dispatchEvent(new Event('load'))
        }
      }
      return appended
    })

    await expect(loadMapLibre()).rejects.toThrow('Failed to load MapLibre ESM asset')
    expect(document.querySelector('script[data-vl360-maplibre]')).toBeNull()
    await expect(loadMapLibre()).resolves.toBe(maplibregl)
    expect(attempt).toBe(2)
  })
})
