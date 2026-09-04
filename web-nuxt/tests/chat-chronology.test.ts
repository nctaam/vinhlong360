import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const source = readFileSync(resolve(__dirname, '..', 'components', 'ChatWidget.vue'), 'utf8')

describe('chat chronology contract', () => {
  it('renders a machine-readable time for every delivered message kind', () => {
    expect(source).toContain('<time')
    expect(source).toContain('datetime=')
    expect(source).toContain('createdAt')
    expect(source).toContain('failed')
  })

  it('carries server chronology metadata and deduplicates reconnect retries', () => {
    expect(source).toContain('display_timezone')
    expect(source).toContain('generation')
    expect(source).toContain('message_id')
    expect(source).toContain('new Set')
    expect(source).not.toContain('owner_key')
    expect(source).not.toContain('correlation_id')
  })

  it('checks failed terminal done frames before appending the assistant fallback', () => {
    expect(source).toContain('if (data.failed === true && !streamError) streamError = data')
  })

  it('does not expose correlation identifiers in correction UI', () => {
    const form = readFileSync(resolve(__dirname, '..', 'components', 'cases', 'CorrectionIntakeForm.vue'), 'utf8')
    expect(form).not.toContain('correlation_id')
    expect(form).not.toContain('Mã đối soát')
  })

  it('uses the canonical error surface for failed chat messages', () => {
    const base = readFileSync(resolve(__dirname, '..', 'assets', 'css', 'base.css'), 'utf8')
    expect(base).toContain('.chat-panel-msgs .cmsg.error')
    expect(base).toContain('var(--error-bg)')
    expect(base).toContain('var(--error-border)')
  })
})
