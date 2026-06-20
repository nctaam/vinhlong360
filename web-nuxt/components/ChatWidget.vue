<template>
  <ClientOnly>
    <div v-if="ff('chat_widget')" class="chat-widget">
      <button type="button" class="chat-fab" :class="{ open }" @click="open = !open" :aria-expanded="open" aria-label="Chat AI">
        {{ open ? '✕' : '💬' }}
      </button>

      <div ref="panelEl" class="chat-panel" :class="{ show: open }" role="dialog" aria-label="Chat hỏi đáp" aria-modal="true">
        <div class="chat-panel-head">
          <h3>{{ chatTitle }}</h3>
          <button type="button" class="cp-close" aria-label="Đóng chat" @click="open = false">✕</button>
        </div>

        <div ref="messagesEl" class="chat-panel-msgs" aria-live="polite">
          <div v-for="(msg, i) in messages" :key="i" :class="['cmsg', msg.role]">
            {{ msg.content }}
          </div>
          <div v-if="streaming && streamText" class="cmsg assistant">
            {{ streamText }}
          </div>
          <div v-else-if="streaming" class="c-typing" role="status" aria-label="Đang trả lời...">
            <span aria-hidden="true"></span><span aria-hidden="true"></span><span aria-hidden="true"></span>
          </div>
          <div v-if="activeSuggestions.length" class="csuggestions">
            <button type="button" v-for="s in activeSuggestions" :key="s" @click="sendMessage(s)">{{ s }}</button>
          </div>
        </div>

        <div class="chat-panel-input">
          <input v-model="inputText" :placeholder="chatPlaceholder" aria-label="Nhập câu hỏi" :disabled="streaming" @keyup.enter="sendMessage(inputText)" />
          <button type="button" aria-label="Gửi tin nhắn" :disabled="!inputText.trim() || streaming" @click="sendMessage(inputText)">Gửi</button>
        </div>

        <p v-if="chatDisclaimer" class="chat-disclaimer">{{ chatDisclaimer }}</p>
      </div>
    </div>
  </ClientOnly>
</template>

<script setup lang="ts">
const route = useRoute()
const { get: ss } = useSiteSettings()
const { enabled: ff } = useFeature()
const chatTitle = computed(() => ss('chat.title', 'Hỏi về Vĩnh Long'))
const chatPlaceholder = computed(() => ss('chat.placeholder', 'Hỏi gì đó về Vĩnh Long…'))
const chatDisclaimer = computed(() => ss('chat.disclaimer', 'Nội dung do AI tạo, có thể chưa chính xác — vui lòng kiểm chứng.'))
const open = ref(false)
const inputText = ref('')
const messages = ref<{ role: string; content: string }[]>([])
const panelEl = ref<HTMLElement | null>(null)

// Body-scroll lock, focus trap, Escape-to-close + focus restore (SSR-safe).
useModalA11y(open, panelEl, { onClose: () => { open.value = false } })

// Prefer focusing the text input (not the close button) when the panel opens.
watch(open, (isOpen) => {
  if (isOpen && typeof document !== 'undefined') {
    nextTick(() => panelEl.value?.querySelector<HTMLElement>('input')?.focus())
  }
})

// Default per-route suggestion lists (inline fallback — keeps behavior identical
// when no DB seed exists). Keys are route prefixes; 'default' is the catch-all.
const defaultSuggestionsByRoute: Record<string, string[]> = {
  '/dia-diem/': ['Nên đi vào mùa nào?', 'Gần đây có gì ăn?', 'Đi cùng gia đình được không?'],
  '/du-lich': ['Nên đi đâu cuối tuần?', 'Trải nghiệm miệt vườn?', 'Lịch trình 1 ngày không cần đặt trước'],
  '/luu-tru': ['Homestay yên tĩnh ở đâu?', 'Chỗ ở gần cù lao?', 'Chỗ nào phù hợp gia đình?'],
  '/lich-trinh': ['Gợi ý lịch trình cuối tuần 2N1Đ', 'Đi Bến Tre 1 ngày nên ghé đâu?', 'Lịch trình có trẻ em?'],
  '/tao-lich-trinh': ['Gợi ý lịch trình cuối tuần 2N1Đ', 'Đi Bến Tre 1 ngày nên ghé đâu?', 'Lịch trình có trẻ em?'],
  '/ocop': ['Quà OCOP dưới 200k?', 'Mua quà gì ở Vĩnh Long?', 'OCOP 5 sao có gì?'],
  '/san-pham': ['Quà OCOP dưới 200k?', 'Mua quà gì ở Vĩnh Long?', 'OCOP 5 sao có gì?'],
  '/ban-do': ['Quán ăn ngon gần đây?', 'Đi thuyền ở đâu?', 'Đường đến cù lao An Bình'],
  '/khu-vuc/': ['Nên ở đâu ở vùng này?', 'Đặc sản vùng này?', 'Lịch trình 1 ngày ở đây'],
  default: ['Lịch trình 1 ngày không cần đặt trước', 'Đặc sản nổi tiếng?', 'Đi đâu cuối tuần này?'],
}

const contextSuggestions = computed(() => {
  const p = route.path
  // Empty/unset setting → use the inline default map (so seeding {} is safe).
  const cfg = ss('chat.suggestions_by_route', {}) as Record<string, string[]>
  const map = (cfg && Object.keys(cfg).length) ? cfg : defaultSuggestionsByRoute
  // Match the current path against route-prefix keys, preferring the longest match.
  let best: string[] | null = null
  let bestLen = -1
  for (const key in map) {
    if (key === 'default') continue
    const matches = key.endsWith('/') ? p.startsWith(key) : (p === key || p.startsWith(key + '/'))
    if (matches && key.length > bestLen) {
      best = map[key]
      bestLen = key.length
    }
  }
  return best ?? map.default ?? defaultSuggestionsByRoute.default
})

const suggestions = ref<string[]>([])
const activeSuggestions = computed(() => suggestions.value.length ? suggestions.value : (messages.value.length === 0 ? contextSuggestions.value : []))
const streaming = ref(false)
const streamText = ref('')
const sessionId = ref('')
const messagesEl = ref<HTMLElement | null>(null)

function scrollBottom() {
  nextTick(() => {
    if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  })
}

async function sendMessage(text: string) {
  if (!text.trim() || streaming.value) return
  const userMsg = text.trim()
  inputText.value = ''
  suggestions.value = []
  messages.value.push({ role: 'user', content: userMsg })
  scrollBottom()

  streaming.value = true
  streamText.value = ''

  const history = messages.value.slice(-10).map(m => ({ role: m.role, content: m.content }))

  try {
    const params = new URLSearchParams({
      message: userMsg,
      history: JSON.stringify(history),
      session_id: sessionId.value,
    })
    const res = await fetch(`/chat/stream?${params}`)
    if (!res.ok || !res.body) {
      messages.value.push({ role: 'assistant', content: 'Xin lỗi, không thể kết nối. Vui lòng thử lại.' })
      streaming.value = false
      streamText.value = ''
      scrollBottom()
      return
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let fullText = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      for (const line of chunk.split('\n')) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.type === 'text') {
            fullText += data.content
            streamText.value = fullText
            scrollBottom()
          } else if (data.type === 'done') {
            if (data.session_id) sessionId.value = data.session_id
            if (data.suggestions?.length) suggestions.value = data.suggestions
          }
        } catch { /* skip malformed SSE line */ }
      }
    }

    messages.value.push({ role: 'assistant', content: fullText || 'Không có phản hồi.' })
  } catch {
    messages.value.push({ role: 'assistant', content: 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.' })
  }

  streaming.value = false
  streamText.value = ''
  scrollBottom()
}
</script>

<style scoped>
.chat-disclaimer {
  margin: 0;
  padding: 6px 12px 10px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--c-text-muted, #888);
  text-align: center;
}
</style>
