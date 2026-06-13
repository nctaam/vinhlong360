export function useAI() {
  const aiSessionId = useState('ai-session-id', () => '')
  const { authHeaders } = useAuth()

  async function aiChat(message: string, history: any[] = []): Promise<{ reply: string; suggestions: string[]; tool_calls: any[] }> {
    try {
      const res = await $fetch<any>('/chat', {
        method: 'POST',
        body: { message, history, session_id: aiSessionId.value },
      })
      if (res.session_id) aiSessionId.value = res.session_id
      return { reply: res.reply || '', suggestions: res.suggestions || [], tool_calls: res.tool_calls || [] }
    } catch {
      return { reply: '', suggestions: [], tool_calls: [] }
    }
  }

  async function aiStream(message: string, onChunk: (text: string) => void, onDone?: (data: any) => void) {
    try {
      const res = await fetch('/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, session_id: aiSessionId.value }),
      })
      if (!res.ok || !res.body) return ''
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let fullText = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        for (const line of decoder.decode(value, { stream: true }).split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'text') { fullText += data.content; onChunk(fullText) }
            else if (data.type === 'done') {
              if (data.session_id) aiSessionId.value = data.session_id
              onDone?.(data)
            }
          } catch { /* skip */ }
        }
      }
      return fullText
    } catch { return '' }
  }

  async function aiRecommend(opts: { entityId?: string; month?: number; weather?: string; limit?: number } = {}) {
    try {
      const params = new URLSearchParams()
      if (opts.entityId) params.set('entity_id', opts.entityId)
      if (opts.month) params.set('month', String(opts.month))
      if (opts.weather) params.set('weather', opts.weather)
      if (opts.limit) params.set('limit', String(opts.limit))
      return await $fetch<any>(`/recommend?${params}`)
    } catch { return null }
  }

  async function aiHealth() {
    try { return await $fetch<any>('/health') } catch { return null }
  }

  async function aiSmartSearch(query: string): Promise<{ reply: string; entities: any[]; suggestions: string[] }> {
    const prompt = `Tìm kiếm: "${query}". Hãy liệt kê các entity phù hợp nhất (tên, loại, mô tả ngắn) và gợi ý tìm kiếm liên quan.`
    const res = await aiChat(prompt)
    return { reply: res.reply, entities: [], suggestions: res.suggestions }
  }

  async function aiEntityTips(entityId: string, entityName: string): Promise<string> {
    const res = await aiChat(`Cho tôi 3-4 tips ngắn gọn khi đến "${entityName}" (ID: ${entityId}). Trả lời bằng bullet points, mỗi tip 1 dòng.`)
    return res.reply
  }

  async function aiBestTime(entityId: string, entityName: string): Promise<string> {
    const res = await aiChat(`Thời điểm tốt nhất để đến "${entityName}" là khi nào? Trả lời ngắn 2-3 câu, kèm lý do.`)
    return res.reply
  }

  async function aiCompare(entity1: string, entity2: string): Promise<string> {
    const res = await aiChat(`So sánh ngắn gọn "${entity1}" và "${entity2}" — điểm mạnh, điểm khác biệt, nên chọn cái nào tùy mục đích.`)
    return res.reply
  }

  async function aiSuggestFollowups(context: string): Promise<string[]> {
    const res = await aiChat(`Dựa vào ngữ cảnh: "${context}". Gợi ý 3 câu hỏi tiếp theo ngắn gọn mà người dùng có thể quan tâm.`)
    return res.suggestions.length ? res.suggestions : []
  }

  return {
    aiSessionId,
    aiChat,
    aiStream,
    aiRecommend,
    aiHealth,
    aiSmartSearch,
    aiEntityTips,
    aiBestTime,
    aiCompare,
    aiSuggestFollowups,
  }
}
