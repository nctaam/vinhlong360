import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import ChatWidget from '../components/ChatWidget.vue'
import { useAI } from '../composables/useAI'

const mocks = vi.hoisted(() => ({
  authHeaders: vi.fn(() => ({ Authorization: 'Bearer test-token' })),
  fetch: vi.fn(),
}))

mockNuxtImport('useRoute', () => () => ({ name: 'home', path: '/' }))
mockNuxtImport('useSiteSettings', () => () => ({ get: (_key: string, fallback: unknown) => fallback }))
mockNuxtImport('useFeature', () => () => ({ enabled: () => true }))
mockNuxtImport('useModalA11y', () => () => undefined)
mockNuxtImport('useAuth', () => () => ({
  authHeaders: mocks.authHeaders,
  fetchMe: vi.fn(),
  user: { value: null },
}))

function streamResponse(sessionId = 'fresh-session') {
  const payload = [
    `data: ${JSON.stringify({ type: 'text', content: 'ok' })}\n\n`,
    `data: ${JSON.stringify({ type: 'done', session_id: sessionId })}\n\n`,
  ].join('')
  return new Response(payload, { status: 200 })
}

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
}

beforeEach(() => {
  sessionStorage.clear()
  mocks.authHeaders.mockClear()
  mocks.fetch.mockReset().mockResolvedValue(streamResponse())
  vi.stubGlobal('fetch', mocks.fetch)
})

describe('chat streaming transport security', () => {
  it('ChatWidget sends prompt, history, and selector in a credentialed POST body', async () => {
    sessionStorage.setItem('chat_sid', 'stored-session')
    const wrapper = await mountSuspended(ChatWidget, {
      global: { stubs: { ClientOnly: false, IconLine: true } },
    })

    await wrapper.get('input').setValue('hello')
    await wrapper.get('input').trigger('keyup.enter')
    await flushUi()
    await flushUi()

    expect(mocks.fetch).toHaveBeenCalledTimes(1)
    const [url, init] = mocks.fetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/chat/stream')
    expect(init).toMatchObject({
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer test-token',
      },
    })
    expect(JSON.parse(String(init.body))).toEqual({
      message: 'hello',
      history: [{ role: 'user', content: 'hello' }],
      session_id: 'stored-session',
    })
  })

  it('useAI sends history and selector through the same protected POST transport', async () => {
    let ai: ReturnType<typeof useAI> | undefined
    const Harness = defineComponent({
      setup() {
        ai = useAI()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)
    ai!.aiSessionId.value = 'stored-session'
    const history = [{
      role: 'assistant' as const,
      content: 'previous answer',
      suggestions: ['not history'],
      tool_calls: [{ name: 'not-history' }],
    }]

    await ai!.aiStream('next question', vi.fn(), undefined, history)

    expect(mocks.fetch).toHaveBeenCalledTimes(1)
    const [url, init] = mocks.fetch.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/chat/stream')
    expect(init).toMatchObject({
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer test-token',
      },
    })
    expect(JSON.parse(String(init.body))).toEqual({
      message: 'next question',
      history: [{ role: 'assistant', content: 'previous answer' }],
      session_id: 'stored-session',
    })
  })

  it('does not serialize chat payloads or the anonymous owner cookie into browser URLs', () => {
    const widget = readFileSync(resolve(process.cwd(), 'components/ChatWidget.vue'), 'utf8')
    const composable = readFileSync(resolve(process.cwd(), 'composables/useAI.ts'), 'utf8')
    const chatSources = `${widget}\n${composable}`

    expect(chatSources).not.toContain('/chat/stream?')
    expect(widget).not.toContain('URLSearchParams')
    expect(chatSources).not.toContain('vl360_chat_owner')
    expect(chatSources).not.toContain('document.cookie')
  })
})
