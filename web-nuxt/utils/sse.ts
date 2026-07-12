const DEFAULT_MAX_EVENT_CHARS = 256 * 1024
const EVENT_BOUNDARY = /(?:\r\n|\n)(?:\r\n|\n)/

function parseEventData(eventText: string) {
  const dataLines: string[] = []
  for (const line of eventText.split(/\r\n|\n/)) {
    if (!line || line.startsWith(':')) continue
    const colon = line.indexOf(':')
    const field = colon === -1 ? line : line.slice(0, colon)
    if (field !== 'data') continue
    let value = colon === -1 ? '' : line.slice(colon + 1)
    if (value.startsWith(' ')) value = value.slice(1)
    dataLines.push(value)
  }
  return dataLines.length ? dataLines.join('\n') : null
}

export async function consumeJsonSseStream<T extends Record<string, unknown>>(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onEvent: (event: T) => void,
  options: { maxEventChars?: number } = {},
) {
  const maxEventChars = options.maxEventChars ?? DEFAULT_MAX_EVENT_CHARS
  const decoder = new TextDecoder()
  let buffer = ''

  const dispatch = (eventText: string) => {
    if (eventText.length > maxEventChars) {
      throw new Error(`SSE event exceeded ${maxEventChars} characters`)
    }
    const data = parseEventData(eventText)
    if (data === null) return
    let event: unknown
    try {
      event = JSON.parse(data)
    } catch (error) {
      if (error instanceof SyntaxError) return
      throw error
    }
    if (typeof event !== 'object' || event === null) return
    onEvent(event as T)
  }

  const consume = (text: string, atEof = false) => {
    buffer += text
    let boundary = EVENT_BOUNDARY.exec(buffer)
    while (boundary) {
      dispatch(buffer.slice(0, boundary.index))
      buffer = buffer.slice(boundary.index + boundary[0].length)
      boundary = EVENT_BOUNDARY.exec(buffer)
    }
    if (atEof && buffer) {
      dispatch(buffer.replace(/(?:\r\n|\n)$/, ''))
      buffer = ''
    } else if (buffer.length > maxEventChars + 3) {
      // A split CRLF delimiter can add at most three retained characters.
      throw new Error(`SSE event exceeded ${maxEventChars} characters`)
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    consume(decoder.decode(value, { stream: true }))
  }
  consume(decoder.decode(), true)
}
