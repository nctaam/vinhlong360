import type { ChatMessage, ChatResponse, ChatToolCall, Entity } from '~/types'
import { consumeJsonSseStream } from '~/utils/sse'

export function useAI() {
  const aiSessionId = useState('ai-session-id', () => '')
  const { authHeaders } = useAuth()

  function isMissingConversation(error: unknown) {
    const value = error as { status?: number; statusCode?: number; response?: { status?: number } }
    return value?.response?.status === 404 || value?.statusCode === 404 || value?.status === 404
  }

  function chatBody(message: string, history: ChatMessage[] = []) {
    const conversationHistory = history.map(({ role, content }) => ({ role, content }))
    return aiSessionId.value
      ? { message, history: conversationHistory, session_id: aiSessionId.value }
      : { message, history: conversationHistory }
  }

  async function aiChat(message: string, history: ChatMessage[] = []): Promise<ChatResponse> {
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const res = await $fetch<ChatResponse & { session_id?: string }>('/chat', {
          method: 'POST',
          body: chatBody(message, history),
        })
        if (res.session_id) aiSessionId.value = res.session_id
        return { reply: res.reply || '', suggestions: res.suggestions || [], tool_calls: res.tool_calls || [] }
      } catch (error) {
        if (attempt === 0 && aiSessionId.value && isMissingConversation(error)) {
          aiSessionId.value = ''
          continue
        }
        return { reply: '', suggestions: [], tool_calls: [] }
      }
    }
    return { reply: '', suggestions: [], tool_calls: [] }
  }

  async function aiStream(
    message: string,
    onChunk: (text: string) => void,
    onDone?: (data: Record<string, unknown>) => void,
    history: ChatMessage[] = [],
  ) {
    try {
      const request = () => fetch('/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        credentials: 'same-origin',
        body: JSON.stringify(chatBody(message, history)),
      })
      let res = await request()
      if (res.status === 404 && aiSessionId.value) {
        aiSessionId.value = ''
        res = await request()
      }
      if (!res.ok || !res.body) return ''
      const reader = res.body.getReader()
      let fullText = ''
      await consumeJsonSseStream(reader, (data) => {
        if (data.type === 'text' && typeof data.content === 'string') {
          fullText += data.content
          onChunk(fullText)
        } else if (data.type === 'done') {
          if (typeof data.session_id === 'string' && data.session_id) {
            aiSessionId.value = data.session_id
          }
          onDone?.(data)
        }
      })
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
    try { return await $fetch<Record<string, unknown>>('/health') } catch { return null }
  }

  async function aiSmartSearch(query: string): Promise<{ reply: string; entities: Entity[]; suggestions: string[] }> {
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
