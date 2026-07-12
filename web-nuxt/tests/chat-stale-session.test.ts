import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import ChatWidget from '../components/ChatWidget.vue'
import { useAI } from '../composables/useAI'
import { fragmentedStreamResponse } from './chat-stream-fixtures'

const mocks = vi.hoisted(() => ({
  fetch: vi.fn(),
  nuxtFetch: vi.fn(),
}))

mockNuxtImport('useRoute', () => () => ({ name: 'home', path: '/' }))
mockNuxtImport('useSiteSettings', () => () => ({ get: (_key: string, fallback: unknown) => fallback }))
mockNuxtImport('useFeature', () => () => ({ enabled: () => true }))
mockNuxtImport('useModalA11y', () => () => undefined)
mockNuxtImport('useAuth', () => () => ({
  authHeaders: () => ({}),
  fetchMe: vi.fn(),
  user: { value: null },
}))

async function flushUi() {
  await new Promise(resolve => setTimeout(resolve, 0))
  await nextTick()
}

async function sendWidgetMessage() {
  const wrapper = await mountSuspended(ChatWidget, {
    global: { stubs: { ClientOnly: false, IconLine: true } },
  })
  await wrapper.get('input').setValue('hello')
  await wrapper.get('input').trigger('keyup.enter')
  await flushUi()
  await flushUi()
  return wrapper
}

beforeEach(() => {
  sessionStorage.clear()
  sessionStorage.setItem('chat_sid', 'stale-session')
  mocks.fetch.mockReset()
  mocks.nuxtFetch.mockReset()
  vi.stubGlobal('fetch', mocks.fetch)
  vi.stubGlobal('$fetch', mocks.nuxtFetch)
})

describe('stale chat selector recovery', () => {
  it('ChatWidget clears the stale selector and retries exactly once into a fragmented done event', async () => {
    mocks.fetch
      .mockResolvedValueOnce(new Response(null, { status: 404 }))
      .mockResolvedValueOnce(fragmentedStreamResponse('fresh-session'))

    const wrapper = await sendWidgetMessage()

    expect(mocks.fetch).toHaveBeenCalledTimes(2)
    expect(JSON.parse(String(mocks.fetch.mock.calls[0]?.[1]?.body))).toEqual({
      message: 'hello',
      history: [],
      session_id: 'stale-session',
    })
    expect(JSON.parse(String(mocks.fetch.mock.calls[1]?.[1]?.body))).toEqual({
      message: 'hello',
      history: [],
    })
    expect(wrapper.findAll('.cmsg.assistant').at(-1)?.text()).toBe('Xin chào Vĩnh Long')
    expect(sessionStorage.getItem('chat_sid')).toBe('fresh-session')
  })

  it('ChatWidget never retries a stale selector more than once', async () => {
    mocks.fetch.mockResolvedValue(new Response(null, { status: 404 }))

    await sendWidgetMessage()

    expect(mocks.fetch).toHaveBeenCalledTimes(2)
    expect(JSON.parse(String(mocks.fetch.mock.calls[1]?.[1]?.body))).toEqual({
      message: 'hello',
      history: [],
    })
    expect(sessionStorage.getItem('chat_sid')).toBeNull()
  })

  it('useAI clears stale state and retries POST chat once without a selector', async () => {
    let ai: ReturnType<typeof useAI> | undefined
    const Harness = defineComponent({
      setup() {
        ai = useAI()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)
    ai!.aiSessionId.value = 'stale-session'
    mocks.nuxtFetch
      .mockRejectedValueOnce({ response: { status: 404 } })
      .mockResolvedValueOnce({ reply: 'ok', suggestions: [], tool_calls: [], session_id: 'fresh-session' })

    const result = await ai!.aiChat('hello')

    expect(result.reply).toBe('ok')
    expect(mocks.nuxtFetch).toHaveBeenCalledTimes(2)
    expect(mocks.nuxtFetch.mock.calls[0]?.[1]?.body).toMatchObject({ session_id: 'stale-session' })
    expect(mocks.nuxtFetch.mock.calls[1]?.[1]?.body).not.toHaveProperty('session_id')
    expect(ai!.aiSessionId.value).toBe('fresh-session')
  })

  it('useAI retries a stale stream selector once and parses the fragmented done event', async () => {
    let ai: ReturnType<typeof useAI> | undefined
    const Harness = defineComponent({
      setup() {
        ai = useAI()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)
    ai!.aiSessionId.value = 'stale-session'
    mocks.fetch
      .mockResolvedValueOnce(new Response(null, { status: 404 }))
      .mockResolvedValueOnce(fragmentedStreamResponse('fresh-stream-session'))
    const onDone = vi.fn()

    const result = await ai!.aiStream('hello', vi.fn(), onDone)

    expect(result).toBe('Xin chào Vĩnh Long')
    expect(mocks.fetch).toHaveBeenCalledTimes(2)
    expect(JSON.parse(String(mocks.fetch.mock.calls[0]?.[1]?.body))).toMatchObject({
      session_id: 'stale-session',
    })
    expect(JSON.parse(String(mocks.fetch.mock.calls[1]?.[1]?.body))).not.toHaveProperty('session_id')
    expect(onDone).toHaveBeenCalledWith(expect.objectContaining({ session_id: 'fresh-stream-session' }))
    expect(ai!.aiSessionId.value).toBe('fresh-stream-session')
  })

  it('useAI stops after one selector-free retry', async () => {
    let ai: ReturnType<typeof useAI> | undefined
    const Harness = defineComponent({
      setup() {
        ai = useAI()
        return () => h('div')
      },
    })
    await mountSuspended(Harness)
    ai!.aiSessionId.value = 'stale-session'
    mocks.nuxtFetch.mockRejectedValue({ response: { status: 404 } })

    const result = await ai!.aiChat('hello')

    expect(result.reply).toBe('')
    expect(mocks.nuxtFetch).toHaveBeenCalledTimes(2)
    expect(ai!.aiSessionId.value).toBe('')
  })
})
