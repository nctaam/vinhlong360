import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => {
  let releaseImport!: () => void
  const importReady = new Promise<void>((resolve) => {
    releaseImport = resolve
  })
  const constructMap = vi.fn()
  const addControl = vi.fn()
  const addListener = vi.fn()
  const removeMap = vi.fn()
  let afterConstruct: (() => void) | null = null

  class FakeMap {
    constructor(options: unknown) {
      constructMap(options)
      afterConstruct?.()
    }

    on(...args: unknown[]) {
      addListener(...args)
      return this
    }

    addControl(...args: unknown[]) {
      addControl(...args)
      return this
    }

    remove() {
      removeMap()
    }
  }

  class FakeAttributionControl {}
  class FakeNavigationControl {}

  return {
    addControl,
    addListener,
    constructMap,
    FakeAttributionControl,
    FakeMap,
    FakeNavigationControl,
    importReady,
    releaseImport,
    removeMap,
    get afterConstruct() {
      return afterConstruct
    },
    set afterConstruct(value: (() => void) | null) {
      afterConstruct = value
    },
  }
})

vi.mock('maplibre-gl', async () => {
  await mocks.importReady
  return {
    AttributionControl: mocks.FakeAttributionControl,
    Map: mocks.FakeMap,
    NavigationControl: mocks.FakeNavigationControl,
  }
})
vi.mock('maplibre-gl/dist/maplibre-gl.css', () => ({}))

import { useNDAMap } from '../composables/useNDAMap'

beforeEach(() => {
  mocks.constructMap.mockClear()
  mocks.addListener.mockClear()
  mocks.addControl.mockClear()
  mocks.removeMap.mockClear()
  mocks.afterConstruct = null
})

describe('useNDAMap lifecycle boundary', () => {
  it('does not construct or configure a map after disposal during MapLibre import', async () => {
    let active = true
    const { createMap } = useNDAMap()
    const pendingMap = createMap(document.createElement('div'), {
      isActive: () => active,
    })

    active = false
    mocks.releaseImport()
    const result = await pendingMap

    expect(result).toBeNull()
    expect(mocks.constructMap).not.toHaveBeenCalled()
    expect(mocks.addListener).not.toHaveBeenCalled()
    expect(mocks.addControl).not.toHaveBeenCalled()
    expect(mocks.removeMap).not.toHaveBeenCalled()
  })

  it('tears down a map constructed just before disposal before configuring it', async () => {
    let active = true
    mocks.afterConstruct = () => {
      active = false
    }
    const { createMap } = useNDAMap()

    const result = await createMap(document.createElement('div'), {
      isActive: () => active,
    })

    expect(result).toBeNull()
    expect(mocks.constructMap).toHaveBeenCalledTimes(1)
    expect(mocks.removeMap).toHaveBeenCalledTimes(1)
    expect(mocks.addListener).not.toHaveBeenCalled()
    expect(mocks.addControl).not.toHaveBeenCalled()
  })
})
