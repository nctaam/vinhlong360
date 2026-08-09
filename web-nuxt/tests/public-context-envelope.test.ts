import { describe, expect, it } from 'vitest'
import { usePublicContextEnvelope } from '~/composables/usePublicContextEnvelope'

describe('public context envelope', () => {
  it('defaults location to unavailable and does not expose coordinates', () => {
    const { envelope } = usePublicContextEnvelope()
    expect(['unavailable', 'selected']).toContain(envelope.value.location.mode)
    expect(JSON.stringify(envelope.value)).not.toMatch(/latitude|longitude|coords|gps/i)
  })
})
