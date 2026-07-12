import { describe, expect, it, vi } from 'vitest'
import { consumeJsonSseStream } from '../utils/sse'

function readerFor(...chunks: string[]) {
  const encoder = new TextEncoder()
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
      controller.close()
    },
  }).getReader()
}

describe('consumeJsonSseStream', () => {
  it('joins data lines, ignores comments, skips malformed events, and continues', async () => {
    const onEvent = vi.fn()
    const reader = readerFor(
      ': keep-alive\r\n\r\n',
      'data: {not-json}\n\n',
      'data: {"type":"text",\r\n',
      'data: "content":"ok"}\r\n\r\n',
    )

    await consumeJsonSseStream(reader, onEvent)

    expect(onEvent).toHaveBeenCalledTimes(1)
    expect(onEvent).toHaveBeenCalledWith({ type: 'text', content: 'ok' })
  })

  it('rejects an unterminated event that exceeds the buffer guard', async () => {
    const reader = readerFor(`data: ${'x'.repeat(33)}`)

    await expect(consumeJsonSseStream(reader, vi.fn(), { maxEventChars: 32 }))
      .rejects.toThrow('SSE event exceeded 32 characters')
  })

  it('does not mistake a consumer SyntaxError for malformed event JSON', async () => {
    const reader = readerFor('data: {"type":"text","content":"ok"}\n\n')

    await expect(consumeJsonSseStream(reader, () => {
      throw new SyntaxError('consumer failed')
    })).rejects.toThrow('consumer failed')
  })

  it('skips JSON null without aborting later valid events', async () => {
    const onEvent = vi.fn()
    const reader = readerFor(
      'data: null\n\n',
      'data: {"type":"text","content":"still valid"}\n\n',
    )

    await consumeJsonSseStream(reader, onEvent)

    expect(onEvent).toHaveBeenCalledTimes(1)
    expect(onEvent).toHaveBeenCalledWith({ type: 'text', content: 'still valid' })
  })

  it('allows an exact-limit event when the delimiter is split across chunks', async () => {
    const event = 'data: {"type":"text","content":"ok"}'
    const onEvent = vi.fn()
    const reader = readerFor(`${event}\n`, '\n')

    await consumeJsonSseStream(reader, onEvent, { maxEventChars: event.length })

    expect(onEvent).toHaveBeenCalledWith({ type: 'text', content: 'ok' })
  })

  it('allows an exact-limit EOF event with one trailing line ending', async () => {
    const event = 'data: {"type":"done"}'
    const onEvent = vi.fn()
    const reader = readerFor(`${event}\r\n`)

    await consumeJsonSseStream(reader, onEvent, { maxEventChars: event.length })

    expect(onEvent).toHaveBeenCalledWith({ type: 'done' })
  })
})
