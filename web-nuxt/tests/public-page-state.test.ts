import { mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ActionDock from '../components/public/ActionDock.vue'
import PageState from '../components/public/PageState.vue'
import WhyThisControl from '../components/public/WhyThisControl.vue'

const wrappers: Array<{ unmount: () => void }> = []

function deferred<T = void>() {
  let resolve!: (value: T | PromiseLike<T>) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
})

describe('public page-state primitives', () => {
  it('renders loading and ready states without inventing an error', async () => {
    const loading = await mountSuspended(PageState, { props: { state: { kind: 'loading' } } })
    const ready = await mountSuspended(PageState, {
      props: { state: { kind: 'ready', data: {} } },
      slots: { default: '<p data-ready-content>Nội dung sẵn sàng</p>' },
    })
    wrappers.push(loading, ready)

    expect(loading.get('[data-page-state="loading"]').attributes('role')).toBe('status')
    expect(ready.get('[data-page-state="ready"]').attributes('role')).toBeUndefined()
    expect(ready.get('[data-ready-content]').text()).toContain('Nội dung sẵn sàng')
  })

  it('renders stale evidence without presenting it as an error', async () => {
    const wrapper = await mountSuspended(PageState, {
      props: { state: { kind: 'stale', data: {}, updatedAt: '2026-08-01' } },
      slots: { default: '<p>Thông tin vẫn dùng được</p>' },
    })
    wrappers.push(wrapper)

    const panel = wrapper.get('[data-page-state="stale"]')
    expect(panel.text()).toContain('Có thể đã cũ')
    expect(panel.text()).toContain('2026-08-01')
    expect(panel.attributes('role')).not.toBe('alert')
    expect(panel.attributes('aria-live')).toBe('polite')
    expect(panel.text()).toContain('Thông tin vẫn dùng được')
  })

  it('keeps partial content and limits local recovery to one pending retry', async () => {
    const pending = deferred()
    const retry = vi.fn(() => pending.promise)
    const wrapper = await mountSuspended(PageState, {
      props: { state: { kind: 'partial', data: {}, failedPanels: ['media', 'directions'] }, retry },
      slots: { default: '<p data-available-content>Phần thông tin còn lại</p>' },
    })
    wrappers.push(wrapper)

    expect(wrapper.get('[data-available-content]')).toBeTruthy()
    const actions = wrapper.findAll('[data-page-state-retry]')
    expect(actions).toHaveLength(2)
    await actions[1]!.trigger('click')
    await actions[1]!.trigger('click')
    expect(retry).toHaveBeenCalledWith('directions')
    expect(retry).toHaveBeenCalledOnce()
    expect(wrapper.emitted('retry')).toBeUndefined()
    expect(actions.every(action => action.attributes('disabled') !== undefined)).toBe(true)
    expect(actions[1]!.text()).toContain('Đang tải lại')

    pending.resolve()
    await pending.promise
    await vi.waitFor(() => expect(actions[1]!.attributes('disabled')).toBeUndefined())
    await actions[1]!.trigger('click')
    expect(retry).toHaveBeenCalledTimes(2)
  })

  it('limits an error retry to one pending request and uses assertive alert semantics', async () => {
    const pending = deferred()
    const retry = vi.fn(() => pending.promise)
    const wrapper = await mountSuspended(PageState, {
      props: { state: { kind: 'error', retry: { label: 'Tải lại' }, fallback: {} }, retry },
      slots: { default: '<p data-fallback-content>Nội dung lưu tạm</p>' },
    })
    wrappers.push(wrapper)

    const panel = wrapper.get('[data-page-state="error"]')
    const action = wrapper.get('[data-page-state-retry]')
    expect(panel.attributes('role')).toBe('alert')
    expect(panel.attributes('aria-live')).toBe('assertive')
    expect(wrapper.get('[data-fallback-content]').text()).toContain('Nội dung lưu tạm')

    await action.trigger('click')
    await action.trigger('click')
    expect(retry).toHaveBeenCalledOnce()
    expect(wrapper.emitted('retry')).toBeUndefined()
    expect(action.attributes('disabled')).toBeDefined()
    pending.resolve()
    await pending.promise
    await vi.waitFor(() => expect(action.attributes('disabled')).toBeUndefined())
    await action.trigger('click')
    expect(retry).toHaveBeenCalledTimes(2)
  })

  it('does not expose an event-only retry path outside the callback guard', async () => {
    const eventOnlyRetry = vi.fn(() => Promise.resolve())
    const wrapper = await mountSuspended(PageState, {
      props: {
        state: { kind: 'error', retry: { label: 'Tải lại' } },
        onRetry: eventOnlyRetry,
      } as never,
    })
    wrappers.push(wrapper)

    expect(wrapper.find('[data-page-state-retry]').exists()).toBe(false)
    expect(eventOnlyRetry).not.toHaveBeenCalled()
  })

  it('renders empty recovery and cached offline content', async () => {
    const recovery = vi.fn()
    const empty = await mountSuspended(PageState, {
      props: { state: { kind: 'empty', recovery: { id: 'browse', label: 'Xem tất cả' } }, recovery },
    })
    const offline = await mountSuspended(PageState, {
      props: { state: { kind: 'offline', cached: {}, cachedAt: '2026-08-01' } },
      slots: { default: '<p data-cached-content>Nội dung đã lưu</p>' },
    })
    wrappers.push(empty, offline)

    await empty.get('[data-page-state-recovery]').trigger('click')
    expect(recovery).toHaveBeenCalledOnce()
    expect(empty.emitted('recovery')).toHaveLength(1)
    expect(offline.get('[data-cached-content]').text()).toContain('Nội dung đã lưu')
    expect(offline.get('[data-page-state="offline"]').text()).toContain('2026-08-01')
  })

  it('renders only the first primary action from the ActionDock slot', async () => {
    const wrapper = await mountSuspended(ActionDock, {
      slots: {
        primary: '<button data-primary="first">Chỉ đường</button><button data-primary="second">Gọi điện</button>',
        default: '<a href="/save">Lưu</a>',
      },
    })
    wrappers.push(wrapper)

    expect(wrapper.findAll('[data-action-dock-primary] button')).toHaveLength(1)
    expect(wrapper.find('[data-primary="first"]').exists()).toBe(true)
    expect(wrapper.find('[data-primary="second"]').exists()).toBe(false)
  })

  it('discloses why a suggestion appears and allows a reset', async () => {
    const onReset = vi.fn()
    const wrapper = await mountSuspended(WhyThisControl, {
      props: {
        reason: 'Phù hợp với khu vực bạn đã chọn',
        signals: ['Khu vực đã chọn', 'Chủ đề bạn quan tâm'],
        onReset,
      },
    })
    wrappers.push(wrapper)

    await wrapper.get('[data-why-this-trigger]').trigger('click')
    expect(wrapper.get('[data-why-this-control]').text()).toContain('Phù hợp với khu vực bạn đã chọn')
    expect(wrapper.get('[data-why-this-signals]').text()).toContain('Khu vực đã chọn')
    await wrapper.get('[data-why-this-reset]').trigger('click')
    expect(onReset).toHaveBeenCalledOnce()
    expect(wrapper.emitted('reset')).toHaveLength(1)
  })
})
