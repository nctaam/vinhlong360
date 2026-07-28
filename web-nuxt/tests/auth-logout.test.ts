import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { useState } from '#app'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import UserMenu from '../components/UserMenu.vue'

type AuthComposable = typeof import('../composables/useAuth')
let useRealAuth: AuthComposable['useAuth']

const mocks = vi.hoisted(() => ({
  fetch: vi.fn(),
  logout: vi.fn(),
  showToast: vi.fn(),
  user: {
    __v_isRef: true,
    value: { id: 'user-1', display_name: 'Nguoi dung' },
  },
  unreadCount: { __v_isRef: true, value: 0 },
}))

mockNuxtImport('useAuth', () => () => ({
  user: mocks.user,
  logout: mocks.logout,
  authHeaders: vi.fn(() => ({})),
}))
mockNuxtImport('useToast', () => () => ({ show: mocks.showToast }))
mockNuxtImport('useNotifications', () => () => ({ unreadCount: mocks.unreadCount }))
mockNuxtImport('useDropdown', () => () => ({ onMenuKeydown: vi.fn() }))

const wrappers: Array<{ unmount: () => void }> = []

beforeAll(async () => {
  const actual = await vi.importActual<AuthComposable>('../composables/useAuth')
  useRealAuth = actual.useAuth
})

function csrfState() {
  return useState<string | null>('auth-csrf-token', () => null)
}

function seedAuthState() {
  const auth = useRealAuth()
  auth.user.value = { id: 'user-1', display_name: 'Nguoi dung' }
  auth.token.value = 'session-token'
  csrfState().value = 'csrf-token'
  auth.twoFactorChallenge.value = { challenge_id: 'challenge-1' }
  return auth
}

beforeEach(() => {
  const auth = useRealAuth()
  auth.user.value = null
  auth.token.value = null
  csrfState().value = null
  auth.twoFactorChallenge.value = null

  mocks.fetch.mockReset()
  mocks.logout.mockReset()
  mocks.showToast.mockReset()
  vi.stubGlobal('$fetch', mocks.fetch)
})

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  vi.unstubAllGlobals()
})

describe('useAuth logout', () => {
  it('rejects and preserves every auth state value when the backend rejects logout', async () => {
    const auth = seedAuthState()
    mocks.fetch.mockRejectedValueOnce(new Error('csrf rejected'))

    await expect(auth.logout()).rejects.toThrow('csrf rejected')

    expect(auth.user.value?.id).toBe('user-1')
    expect(auth.token.value).toBe('session-token')
    expect(csrfState().value).toBe('csrf-token')
    expect(auth.twoFactorChallenge.value).toEqual({ challenge_id: 'challenge-1' })
  })

  it('clears every auth state value only after the backend accepts logout', async () => {
    const auth = seedAuthState()
    mocks.fetch.mockResolvedValueOnce({ success: true })

    await auth.logout()

    expect(auth.user.value).toBeNull()
    expect(auth.token.value).toBeNull()
    expect(csrfState().value).toBeNull()
    expect(auth.twoFactorChallenge.value).toBeNull()
  })
})

describe('UserMenu logout failure', () => {
  it('shows the exact error toast when logout is rejected', async () => {
    mocks.logout.mockRejectedValueOnce(new Error('csrf rejected'))
    const wrapper = await mountSuspended(UserMenu)
    wrappers.push(wrapper)

    await wrapper.get('button.auth-user').trigger('click')
    const logoutButton = wrapper.findAll('button').find(button => button.text().includes('Đăng xuất'))
    expect(logoutButton).toBeDefined()

    await logoutButton!.trigger('click')

    await vi.waitFor(() => {
      expect(mocks.showToast).toHaveBeenCalledWith(
        'Không thể đăng xuất. Phiên của bạn vẫn đang hoạt động.',
        'error',
        5000,
      )
    })
  })
})
