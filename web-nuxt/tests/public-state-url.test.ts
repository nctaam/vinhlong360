import { describe, expect, it } from 'vitest'
import { parseSearchViewState, serializeSearchViewState } from '~/utils/publicStateUrl'

describe('public state URL', () => {
  it('never serializes raw location coordinates', () => {
    const encoded = serializeSearchViewState({ query: 'gốm', intent: 'place', filters: {}, area: { id: 'vinh-long' }, viewport: { center: [10.2, 105.9], zoom: 12 }, panel: 'list' })
    expect(encoded).not.toContain('10.2')
    expect(encoded).not.toContain('105.9')
    expect(encoded).toContain('area=vinh-long')
    expect(encoded).toContain('viewport=')
  })
  it('rejects malformed values with deterministic defaults', () => {
    expect(parseSearchViewState('?intent=wat&query=').intent).toBe('all')
    expect(parseSearchViewState('?filters=%7Bbad').filters).toEqual({})
  })
  it('round-trips only a sanitized tile and rejects invalid tiles/areas', () => {
    const encoded = serializeSearchViewState({ viewport: { center: [105.9, 10.2], zoom: 12 } })
    const restored = parseSearchViewState(encoded)
    expect(restored.viewport?.zoom).toBe(12)
    expect(restored.viewport?.center[0]).toBeGreaterThan(-180)
    expect(restored.viewport?.center[0]).toBeLessThan(180)
    expect(restored.viewport?.center[1]).toBeGreaterThan(-90)
    expect(restored.viewport?.center[1]).toBeLessThan(90)
    const z = restored.viewport!.zoom; const n = 2 ** z
    const x = Math.floor(((restored.viewport!.center[0] + 180) / 360) * n)
    const y = Math.floor((1 - Math.asinh(Math.tan((restored.viewport!.center[1] * Math.PI) / 180)) / Math.PI) / 2 * n)
    expect(encoded).toContain(`viewport=${z}%2F${x}%2F${y}`)
    expect(parseSearchViewState('?viewport=99/1/1').viewport).toBeUndefined()
    expect(parseSearchViewState('?area=../../secret').area).toBeUndefined()
    expect(encoded).not.toMatch(/105\.9|10\.2/)
  })
  it('bounds and whitelists nested filter values', () => {
    const huge = 'x'.repeat(500)
    const parsed = parseSearchViewState(`?filters=${encodeURIComponent(JSON.stringify({ ok: huge, 'bad.key': huge, list: [huge, 3] }))}`)
    expect((parsed.filters.ok as string).length).toBe(80)
    expect(parsed.filters['bad.key']).toBeUndefined()
    expect(parsed.filters.list).toEqual([huge.slice(0, 40)])
  })
  it('uses the same filter key grammar while serializing and parsing', () => {
    const encoded = serializeSearchViewState({ filters: { 'bad.key': 'drop', valid_key: 'keep' } })
    expect(encoded).not.toContain('bad.key')
    expect(parseSearchViewState(encoded).filters).toEqual({ valid_key: 'keep' })
  })
})
