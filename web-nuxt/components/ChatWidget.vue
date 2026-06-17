<template>
  <ClientOnly>
    <div class="chat-widget">
      <button class="chat-fab" :class="{ open }" @click="open = !open" :aria-expanded="open" aria-label="Chat AI">
        {{ open ? '✕' : '💬' }}
      </button>

      <div ref="panelEl" class="chat-panel" :class="{ show: open }" role="dialog" aria-label="Chat hỏi đáp" aria-modal="true" @keydown.escape="open = false" @keydown="onPanelKeydown">
        <div class="chat-panel-head">
          <h3>Hỏi về Vĩnh Long</h3>
          <button class="cp-close" aria-label="Đóng chat" @click="open = false">✕</button>
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
            <button v-for="s in activeSuggestions" :key="s" @click="sendMessage(s)">{{ s }}</button>
          </div>
        </div>

        <div class="chat-panel-input">
          <input v-model="inputText" placeholder="Hỏi gì đó về Vĩnh Long…" aria-label="Nhập câu hỏi" :disabled="streaming" @keyup.enter="sendMessage(inputText)" />
          <button aria-label="Gửi tin nhắn" :disabled="!inputText.trim() || streaming" @click="sendMessage(inputText)">Gửi</button>
        </div>
      </div>
    </div>
  </ClientOnly>
</template>

<script setup lang="ts">
const route = useRoute()
const open = ref(false)
const inputText = ref('')
const messages = ref<{ role: string; content: string }[]>([])
const panelEl = ref<HTMLElement | null>(null)

watch(open, (isOpen) => {
  if (typeof document === 'undefined') return
  document.body.style.overflow = isOpen ? 'hidden' : ''
  if (isOpen) {
    nextTick(() => {
      const input = panelEl.value?.querySelector<HTMLElement>('input')
      input?.focus()
    })
  }
})

function onPanelKeydown(e: KeyboardEvent) {
  if (e.key !== 'Tab' || !panelEl.value) return
  const focusable = Array.from(
    panelEl.value.querySelectorAll<HTMLElement>('input:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])')
  ).filter(el => el.offsetParent !== null)
  if (!focusable.length) return
  const first = focusable[0], last = focusable[focusable.length - 1]
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
}

onUnmounted(() => {
  if (typeof document !== 'undefined') document.body.style.overflow = ''
})

const contextSuggestions = computed(() => {
  const p = route.path
  if (p.startsWith('/dia-diem/')) return ['Nên đi vào mùa nào?', 'Gần đây có gì ăn?', 'Đi cùng gia đình được không?']
  if (p === '/du-lich') return ['Nên đi đâu cuối tuần?', 'Trải nghiệm miệt vườn?', 'Lịch trình 1 ngày không cần đặt trước']
  if (p === '/luu-tru') return ['Homestay yên tĩnh ở đâu?', 'Chỗ ở gần cù lao?', 'Chỗ nào phù hợp gia đình?']
  if (p.startsWith('/lich-trinh') || p === '/tao-lich-trinh') return ['Gợi ý lịch trình cuối tuần 2N1Đ', 'Đi Bến Tre 1 ngày nên ghé đâu?', 'Lịch trình có trẻ em?']
  if (p === '/ocop' || p === '/san-pham') return ['Quà OCOP dưới 200k?', 'Mua quà gì ở Vĩnh Long?', 'OCOP 5 sao có gì?']
  if (p === '/ban-do') return ['Quán ăn ngon gần đây?', 'Đi thuyền ở đâu?', 'Đường đến cù lao An Bình']
  if (p.startsWith('/khu-vuc/')) return ['Nên ở đâu ở vùng này?', 'Đặc sản vùng này?', 'Lịch trình 1 ngày ở đây']
  return ['Lịch trình 1 ngày không cần đặt trước', 'Đặc sản nổi tiếng?', 'Đi đâu cuối tuần này?']
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
