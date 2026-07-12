function concatBytes(...chunks: Uint8Array[]) {
  const length = chunks.reduce((total, chunk) => total + chunk.length, 0)
  const result = new Uint8Array(length)
  let offset = 0
  for (const chunk of chunks) {
    result.set(chunk, offset)
    offset += chunk.length
  }
  return result
}

function findBytes(haystack: Uint8Array, needle: Uint8Array) {
  outer: for (let i = 0; i <= haystack.length - needle.length; i++) {
    for (let j = 0; j < needle.length; j++) {
      if (haystack[i + j] !== needle[j]) continue outer
    }
    return i
  }
  return -1
}

export function fragmentedStreamResponse(sessionId = 'fragmented-session') {
  const encoder = new TextEncoder()
  const first = encoder.encode(`data: ${JSON.stringify({ type: 'text', content: 'Xin ' })}\r\n\r\n`)
  const second = encoder.encode(`data: ${JSON.stringify({ type: 'text', content: 'chào ' })}\n\n`)
  const third = encoder.encode(`: keep-alive\r\n\r\ndata: ${JSON.stringify({ type: 'text', content: 'Vĩnh ' })}\n\n`)
  const fourth = encoder.encode(`data: ${JSON.stringify({ type: 'text', content: 'Long' })}\n\n`)
  const done = encoder.encode(`data: ${JSON.stringify({ type: 'done', session_id: sessionId, suggestions: ['Khám phá tiếp'] })}`)

  const jsonSplit = encoder.encode('data: {"type":"te').length
  const vietnameseBytes = encoder.encode('à')
  const vietnameseOffset = findBytes(second, vietnameseBytes)
  if (vietnameseOffset < 0) throw new Error('Vietnamese fixture byte not found')
  const doneSplit = encoder.encode('data: {"type":"do').length

  const chunks = [
    first.slice(0, 2),
    first.slice(2, jsonSplit),
    first.slice(jsonSplit, first.length - 1),
    concatBytes(first.slice(first.length - 1), second.slice(0, vietnameseOffset + 1)),
    concatBytes(second.slice(vietnameseOffset + 1), third, fourth, done.slice(0, doneSplit)),
    done.slice(doneSplit),
  ]

  return new Response(new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(chunk)
      controller.close()
    },
  }), { status: 200 })
}
