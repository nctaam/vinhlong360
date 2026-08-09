// @vitest-environment nuxt

import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'
import AuthModal from '../components/AuthModal.vue'
import { useAuthModal } from '../composables/useAuthModal'

const authMocks = vi.hoisted(() => ({
  checkPhone: vi.fn(),
  login: vi.fn(),
}))

mockNuxtImport('useAuth', () => () => ({
  requestOtp: vi.fn(),
  verifyOtp: vi.fn(),
  checkPhone: authMocks.checkPhone,
  login: authMocks.login,
  setPassword: vi.fn(),
  verifyTwoFactor: vi.fn(),
  user: ref(null),
  fetchMe: vi.fn().mockResolvedValue(null),
}))

async function flushUi() {
  await Promise.resolve()
  await nextTick()
  await Promise.resolve()
  await nextTick()
}

beforeEach(() => {
  authMocks.checkPhone.mockReset().mockResolvedValue({ exists: true })
  authMocks.login.mockReset().mockResolvedValue({})
})

afterEach(() => {
  document.body.innerHTML = ''
  document.body.style.overflow = ''
})

it('returns a successful real modal login to the full safe route captured when it opened', async () => {
  const origin = '/tim-kiem?q=g%E1%BB%91m&intent=place&area=vinh-long'
  const wrapper = await mountSuspended(AuthModal, {
    route: origin,
    props: { visible: true },
    attachTo: document.body,
    global: {
      stubs: {
        IconLine: true,
      },
    },
  })

  await wrapper.get('input[aria-label="Số điện thoại"]').setValue('0901234567')
  await wrapper.get('input[type="checkbox"]').setValue(true)
  await wrapper.get('.btn-primary').trigger('click')
  await flushUi()
  expect(wrapper.find('input[aria-label="Mật khẩu"]').exists()).toBe(true)

  await wrapper.vm.$router.push('/')
  await flushUi()
  await wrapper.get('input[aria-label="Mật khẩu"]').setValue('Password1')
  await wrapper.get('.btn-primary').trigger('click')
  await flushUi()

  await vi.waitFor(() => expect(wrapper.vm.$router.currentRoute.value.fullPath).toBe(origin))
  wrapper.unmount()
})

it('rejects protocol-relative and absolute auth return targets', async () => {
  let modal!: ReturnType<typeof useAuthModal>
  const Harness = defineComponent({
    setup() {
      modal = useAuthModal()
      return () => h('div')
    },
  })
  const wrapper = await mountSuspended(Harness)

  modal.rememberReturnPath('//evil.example/steal')
  expect(modal.consumeReturnPath()).toBe('')
  modal.rememberReturnPath('https://evil.example/steal')
  expect(modal.consumeReturnPath()).toBe('')

  wrapper.unmount()
})
