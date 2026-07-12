import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import ChatWidget from '../components/ChatWidget.vue'
import { useAI } from '../composables/useAI'
import { fragmentedStreamResponse } from './chat-stream-fixtures'

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
  it('ChatWidget snapshots only prior turns in each credentialed POST body', async () => {
    sessionStorage.setItem('chat_sid', 'stored-session')
    const wrapper = await mountSuspended(ChatWidget, {
      global: { stubs: { ClientOnly: false, IconLine: true } },
    })

    await wrapper.get('input').setValue('first question')
    await wrapper.get('input').trigger('keyup.enter')
    await flushUi()
    await flushUi()

    await wrapper.get('input').setValue('next question')
    await wrapper.get('input').trigger('keyup.enter')
    await flushUi()
    await flushUi()

    expect(mocks.fetch).toHaveBeenCalledTimes(2)
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
      message: 'first question',
      history: [],
      session_id: 'stored-session',
    })
    expect(JSON.parse(String(mocks.fetch.mock.calls[1]?.[1]?.body))).toEqual({
      message: 'next question',
      history: [
        { role: 'user', content: 'first question' },
        { role: 'assistant', content: 'ok' },
      ],
      session_id: 'fresh-session',
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

  it('ChatWidget renders fragmented UTF-8 SSE text and the EOF done event completely', async () => {
    mocks.fetch.mockResolvedValue(fragmentedStreamResponse('widget-session'))
    const wrapper = await mountSuspended(ChatWidget, {
      global: { stubs: { ClientOnly: false, IconLine: true } },
    })

    await wrapper.get('input').setValue('fragment this response')
    await wrapper.get('input').trigger('keyup.enter')
    await flushUi()
    await flushUi()

    expect(wrapper.findAll('.cmsg.assistant').at(-1)?.text()).toBe('Xin chào Vĩnh Long')
    expect(sessionStorage.getItem('chat_sid')).toBe('widget-session')
    expect(wrapper.findAll('.csuggestions button').map(button => button.text())).toContain('Khám phá tiếp')
  })

  it('useAI accumulates fragmented UTF-8 SSE text and forwards the EOF done event', async () => {
    mocks.fetch.mockResolvedValue(fragmentedStreamResponse('composable-session'))
    let ai: ReturnType<typeof useAI> | undefined
    const Harness = defineComponent({
      setup() {
        ai = useAI()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)
    const onChunk = vi.fn()
    const onDone = vi.fn()

    const text = await ai!.aiStream('fragment this response', onChunk, onDone)

    expect(text).toBe('Xin chào Vĩnh Long')
    expect(onChunk).toHaveBeenLastCalledWith('Xin chào Vĩnh Long')
    expect(onDone).toHaveBeenCalledWith(expect.objectContaining({
      type: 'done',
      session_id: 'composable-session',
    }))
    expect(ai!.aiSessionId.value).toBe('composable-session')
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
