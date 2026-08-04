import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => {
  const constructMap = vi.fn()

  class FakeMap {
    constructor(options: unknown) {
      constructMap(options)
    }

    on() {
      return this
    }

    addControl() {
      return this
    }

    remove() {}
  }

  return { constructMap, FakeMap }
})

vi.mock('maplibre-gl', () => ({
  AttributionControl: class {},
  Map: mocks.FakeMap,
  NavigationControl: class {},
}))
vi.mock('maplibre-gl/dist/maplibre-gl.css', () => ({}))

import { useNDAMap } from '../composables/useNDAMap'

function setKey(value: string) {
  const config = useRuntimeConfig()
  ;(config.public as Record<string, unknown>).ndaMapKey = value
}

beforeEach(() => {
  mocks.constructMap.mockClear()
})

describe('useNDAMap tile key handling', () => {
  it('starts on the OpenStreetMap fallback instead of requesting a keyless tile style', async () => {
    setKey('')
    const { createMap } = useNDAMap()

    const result = await createMap(document.createElement('div'), { isActive: () => true })

    expect(result).not.toBeNull()
    const options = mocks.constructMap.mock.calls[0]![0] as { style: unknown }
    expect(typeof options.style).toBe('object')
    expect(JSON.stringify(options.style)).toContain('tile.openstreetmap.org')
    expect(JSON.stringify(options.style)).not.toContain('apikey')
  })

  it('uses the keyed tile style when a key is configured', async () => {
    setKey('configured-key')
    const { createMap } = useNDAMap()

    await createMap(document.createElement('div'), { isActive: () => true })

    const options = mocks.constructMap.mock.calls[0]![0] as { style: unknown }
    expect(typeof options.style).toBe('string')
    expect(options.style as string).toContain('apikey=configured-key')
  })

  it('never ships a hard-coded tile key as the public runtime default', async () => {
    const { readFile } = await import('node:fs/promises')
    const { resolve } = await import('node:path')
    const config = await readFile(resolve(import.meta.dirname, '../nuxt.config.ts'), 'utf8')

    const line = config.split('\n').find(l => l.includes('ndaMapKey:'))
    expect(line).toBeTruthy()
    expect(line).not.toMatch(/\|\|\s*['"][A-Za-z0-9]{16,}['"]/)
  })
})
