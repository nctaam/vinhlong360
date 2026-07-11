<template>
  <ClientOnly>
    <div v-if="ff('chat_widget') && !isEntityDetail" class="chat-widget">
      <button type="button" class="chat-fab" :class="{ open }" @click="open = !open" :aria-expanded="open" aria-label="Chat AI">
        <IconLine :name="open ? 'x' : 'message'" />
      </button>

      <div ref="panelEl" class="chat-panel" :class="{ show: open }" role="dialog" aria-label="Chat hỏi đáp" aria-modal="true">
        <div class="chat-panel-head">
          <h3>{{ chatTitle }}</h3>
          <button type="button" class="cp-close" aria-label="Đóng chat" @click="open = false"><IconLine name="x" /></button>
        </div>

        <div ref="messagesEl" class="chat-panel-msgs" aria-live="polite">
          <div v-for="msg in renderedMessages" :key="msg._key" :class="['cmsg', msg.role, { 'cmsg-failed': msg.failed }]">
            <span v-if="msg.role === 'assistant'" v-html="formatMd(msg.content)"></span>
            <template v-else>{{ msg.content }}</template>
            <button v-if="msg.failed" type="button" class="cmsg-retry" aria-label="Gửi lại" @click="resend(msg)">↻ Thử lại</button>
          </div>
          <div v-if="streaming && streamText" class="cmsg assistant">
            <span v-html="formatMd(streamText)"></span>
          </div>
          <div v-else-if="streaming" class="c-typing" role="status" aria-label="Đang trả lời...">
            <span aria-hidden="true"></span><span aria-hidden="true"></span><span aria-hidden="true"></span>
          </div>
          <div v-if="activeSuggestions.length" class="csuggestions">
            <button type="button" v-for="s in activeSuggestions" :key="s" @click="sendMessage(s)">{{ s }}</button>
          </div>
        </div>

        <div class="chat-panel-input">
          <input v-model="inputText" :placeholder="chatPlaceholder" aria-label="Nhập câu hỏi" enterkeyhint="send" :disabled="streaming" maxlength="500" @keyup.enter="sendMessage(inputText)" />
          <button v-if="streaming" type="button" aria-label="Dừng trả lời" @click="stopStream">Dừng</button>
          <button v-else type="button" aria-label="Gửi tin nhắn" :disabled="!inputText.trim()" @click="sendMessage(inputText)">Gửi</button>
        </div>

        <p v-if="chatDisclaimer" class="chat-disclaimer">{{ chatDisclaimer }}</p>
      </div>
    </div>
  </ClientOnly>
</template>

<script setup lang="ts">
const route = useRoute()
// declutter-2 A4: ẩn FAB trên trang chi tiết entity — nơi đã có AITravelTips +
// SmartRecommendations inline (2 khối AI đủ); route-name (không regex path — id có %2F).
const isEntityDetail = computed(() => route.name === 'dia-diem-id')
const { get: ss } = useSiteSettings()
const { enabled: ff } = useFeature()
const chatTitle = computed(() => ss('chat.title', 'Hỏi về Vĩnh Long'))
const chatPlaceholder = computed(() => ss('chat.placeholder', 'Hỏi gì đó về Vĩnh Long…'))
const chatDisclaimer = computed(() => ss('chat.disclaimer', 'Nội dung do AI tạo, có thể chưa chính xác — vui lòng kiểm chứng.'))
const open = ref(false)
const inputText = ref('')
const messages = ref<{ role: string; content: string; failed?: boolean }[]>([])
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

const contextSuggestions = computed<string[]>(() => {
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
      best = map[key] ?? null
      bestLen = key.length
    }
  }
  return best ?? map.default ?? defaultSuggestionsByRoute.default ?? []
})

const suggestions = ref<string[]>([])
const activeSuggestions = computed<string[]>(() => suggestions.value.length ? suggestions.value : (messages.value.length === 0 ? contextSuggestions.value : []))
const streaming = ref(false)
const streamText = ref('')
const abortCtrl = ref<AbortController | null>(null)  // P1-1: cho phép dừng/timeout SSE
function stopStream() { abortCtrl.value?.abort() }
const sessionId = ref('')
if (import.meta.client) {
  try { sessionId.value = sessionStorage.getItem('chat_sid') || '' } catch { /* private/disabled */ }
}
const messagesEl = ref<HTMLElement | null>(null)
const renderedMessages = computed(() => {
  // key theo index TUYỆT ĐỐI (start+i) — slice(-50) trượt cửa sổ nên index cục bộ đổi
  // nghĩa giữa các message → :key phải ổn định để tránh Vue tái dùng DOM sai (v-html lẫn).
  const start = Math.max(0, messages.value.length - 50)
  return messages.value.slice(start).map((m, i) => ({ ...m, _key: start + i }))
})

function sanitize(t: string) {
  return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function formatMd(text: string) {
  const s = sanitize(text)
  return s.replace(/\*\*(.*?)\*\*/g, (_, g) => `<strong>${g}</strong>`).replace(/\n/g, '<br>')
}

async function resend(msg: { role: string; content: string; failed?: boolean }) {
  if (streaming.value) return
  const idx = messages.value.indexOf(msg)
  if (idx === -1) return
  messages.value.splice(idx, 1)
  const errIdx = messages.value.findIndex((m, i) => i >= idx && m.role === 'assistant' && (m.content === 'Xin lỗi, có lỗi xảy ra.' || m.content === 'Xin lỗi, không thể kết nối. Vui lòng thử lại.'))
  if (errIdx !== -1) messages.value.splice(errIdx, 1)
  await sendMessage(msg.content)
}

let scrollRaf: number | null = null
function scrollBottom() {
  if (scrollRaf) return
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = null
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

  abortCtrl.value?.abort()
  const controller = new AbortController()
  abortCtrl.value = controller
  const timeoutId = setTimeout(() => controller.abort(), 45000)
  let reader: ReadableStreamDefaultReader<Uint8Array> | null = null
  try {
    const params = new URLSearchParams({
      message: userMsg,
      history: JSON.stringify(history),
      session_id: sessionId.value,
    })
    const res = await fetch(`/chat/stream?${params}`, { signal: controller.signal })
    if (!res.ok || !res.body) {
      messages.value.push({ role: 'assistant', content: 'Xin lỗi, không thể kết nối. Vui lòng thử lại.' })
      streaming.value = false
      streamText.value = ''
      scrollBottom()
      return
    }
    reader = res.body.getReader()
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
            if (data.session_id) {
              sessionId.value = data.session_id
              try { sessionStorage.setItem('chat_sid', data.session_id) } catch { /* */ }
            }
            if (data.suggestions?.length) suggestions.value = data.suggestions
          }
        } catch { /* skip malformed SSE line */ }
      }
    }

    messages.value.push({ role: 'assistant', content: fullText || 'Không có phản hồi.' })
  } catch {
    const aborted = controller.signal.aborted
    const userMsg2 = messages.value.findLast(m => m.role === 'user')
    if (userMsg2 && !aborted) userMsg2.failed = true
    messages.value.push({
      role: 'assistant',
      content: aborted ? 'Đã dừng hoặc quá thời gian chờ.' : 'Xin lỗi, có lỗi xảy ra.',
    })
  } finally {
    clearTimeout(timeoutId)
    try { reader?.cancel() } catch { /* already closed */ }
    abortCtrl.value = null
    streaming.value = false
    streamText.value = ''
    if (messages.value.length > 200) messages.value = messages.value.slice(-100)
    scrollBottom()
  }
}

onBeforeUnmount(() => {
  abortCtrl.value?.abort()
  if (scrollRaf) cancelAnimationFrame(scrollRaf)
})
</script>

<style scoped>
.chat-disclaimer {
  margin: 0;
  padding: 6px var(--space-3) 10px;
  font-size: var(--text-2xs);
  line-height: 1.4;
  color: var(--text-muted, var(--muted));
  text-align: center;
}
.cmsg-failed { opacity: .7; border-left: 2px solid var(--error); }
.cmsg-retry { display: inline-block; margin-top: var(--space-1); font-size: var(--text-2xs); color: var(--primary-fg); background: none; border: none; cursor: pointer; text-decoration: underline; padding: 2px 4px; min-height: 44px; border-radius: var(--radius-sm, 4px); }
.cmsg-retry:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.csuggestions button { min-height: 44px; }
.chat-panel-input button { min-height: 44px; }
</style>
