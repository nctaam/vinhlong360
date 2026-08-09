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
})
