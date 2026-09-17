import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import ThemeModeControl from '../components/shell/ThemeModeControl.vue'
import DefaultLayout from '../layouts/default.vue'

const colorMode = vi.hoisted(() => ({ value: 'dark' as unknown, preference: 'dark' as unknown }))
mockNuxtImport('useColorMode', () => () => colorMode)

const mocks = vi.hoisted(() => ({
  authUser: { value: null as null | { id: string; role: string } },
  authHeaders: vi.fn(() => ({})),
  fetchMe: vi.fn(() => Promise.resolve()),
}))

mockNuxtImport('useAuth', () => () => ({
  authHeaders: mocks.authHeaders,
  fetchMe: mocks.fetchMe,
  isLoggedIn: ref(false),
  user: mocks.authUser,
}))
mockNuxtImport('useAuthModal', () => () => ({ open: ref(false) }))
mockNuxtImport('useSeasonTheme', () => () => undefined)
mockNuxtImport('useScrollFade', () => () => undefined)

const wrappers: Array<{ unmount: () => void }> = []

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  colorMode.value = 'dark'
  colorMode.preference = 'dark'
})

describe('Header Smart Editorial Refinement - Task 1: Theme Micro-Toggle', () => {
  it('renders compact micro-toggle while preserving accessible text labels for screen readers', async () => {
    const wrapper = await mountSuspended(ThemeModeControl, { attachTo: document.body })
    wrappers.push(wrapper)

    const darkBtn = wrapper.get('button[data-theme-mode="dark"]')
    const lightBtn = wrapper.get('button[data-theme-mode="light"]')

    expect(darkBtn.text()).toContain('Nocturne')
    expect(lightBtn.text()).toContain('Nền sáng dễ đọc')

    // Nhãn chữ được bọc trong class sr-only để triệt tiêu text rườm rà trên thanh điều hướng
    expect(darkBtn.find('.theme-mode-label').classes()).toContain('sr-only')
    expect(lightBtn.find('.theme-mode-label').classes()).toContain('sr-only')

    // Cả 2 nút đều có icon trực quan
    expect(darkBtn.find('.line-icon').exists()).toBe(true)
    expect(lightBtn.find('.line-icon').exists()).toBe(true)
  })
})

describe('Header Smart Editorial Refinement - Task 2: Unified Navigation Bar', () => {
  it('integrates primary navigation into command row without redundant home link on desktop', async () => {
    const wrapper = await mountSuspended(DefaultLayout, {
      attachTo: document.body,
      slots: { default: '<div>Nội dung</div>' },
      global: {
        stubs: {
          ClientOnly: { template: '<div><slot /></div>' },
          AuthModal: { template: '<div></div>' },
          LazyAuthModal: { template: '<div></div>' },
          ChatWidget: { template: '<div></div>' },
          LazyChatWidget: { template: '<div></div>' },
          ConfirmDialog: { template: '<div></div>' },
          LazyConfirmDialog: { template: '<div></div>' },
          NotificationBell: { template: '<div></div>' },
          LazyNotificationBell: { template: '<div></div>' },
          OnboardingSheet: { template: '<div></div>' },
          LazyOnboardingSheet: { template: '<div></div>' },
          ScrollToTop: { template: '<div></div>' },
          LazyScrollToTop: { template: '<div></div>' },
          ToastContainer: { template: '<div></div>' },
          LazyToastContainer: { template: '<div></div>' },
          JourneyBar: { template: '<div></div>' },
          LazyJourneyBar: { template: '<div></div>' },
          SearchDrawer: { template: '<div></div>' },
          LazySearchDrawer: { template: '<div></div>' },
          UserMenu: { template: '<div></div>' },
          LazyUserMenu: { template: '<div></div>' },
          SearchAutocomplete: { template: '<div></div>' },
          ShellPublicBottomNav: { template: '<div></div>' },
          ShellPublicContextBar: { template: '<div data-public-context-line />' },
          OfflineTerroirPanel: { template: '<div></div>' },
        },
      },
    })
    wrappers.push(wrapper)

    const nav = wrapper.get('.public-shell-inline-nav')
    expect(nav.exists()).toBe(true)

    const links = nav.findAll('a')
    const hrefs = links.map(l => l.attributes('href'))
    expect(hrefs).toEqual(['/du-lich', '/ban-do', '/cong-dong', '/lich-trinh'])
    expect(hrefs).not.toContain('/') // Không lặp lại Trang chủ vì Logo đã dẫn về '/'

    // Nút Danh mục được tích hợp liền mạch
    expect(nav.find('.public-shell-catalog-button').exists()).toBe(true)

    // Không còn tầng task row thứ 3 cồng kềnh
    expect(wrapper.find('.public-shell-task-row').exists()).toBe(false)
  })
})

describe('Header Smart Editorial Refinement - Task 3: Harmonious Utility Cluster', () => {
  it('ensures all utility buttons share consistent 32px height, touch targets, and tactile response', async () => {
    const wrapper = await mountSuspended(DefaultLayout, {
      attachTo: document.body,
      slots: { default: '<div>Nội dung</div>' },
      global: {
        stubs: {
          ClientOnly: { template: '<div><slot /></div>' },
          AuthModal: { template: '<div></div>' },
          LazyAuthModal: { template: '<div></div>' },
          ChatWidget: { template: '<div></div>' },
          LazyChatWidget: { template: '<div></div>' },
          ConfirmDialog: { template: '<div></div>' },
          LazyConfirmDialog: { template: '<div></div>' },
          NotificationBell: { template: '<div></div>' },
          LazyNotificationBell: { template: '<div></div>' },
          OnboardingSheet: { template: '<div></div>' },
          LazyOnboardingSheet: { template: '<div></div>' },
          ScrollToTop: { template: '<div></div>' },
          LazyScrollToTop: { template: '<div></div>' },
          ToastContainer: { template: '<div></div>' },
          LazyToastContainer: { template: '<div></div>' },
          JourneyBar: { template: '<div></div>' },
          LazyJourneyBar: { template: '<div></div>' },
          SearchDrawer: { template: '<div></div>' },
          LazySearchDrawer: { template: '<div></div>' },
          UserMenu: { template: '<div></div>' },
          LazyUserMenu: { template: '<div></div>' },
          SearchAutocomplete: { template: '<div></div>' },
          ShellPublicBottomNav: { template: '<div></div>' },
          ShellPublicContextBar: { template: '<div data-public-context-line />' },
          OfflineTerroirPanel: { template: '<div></div>' },
        },
      },
    })
    wrappers.push(wrapper)

    const authArea = wrapper.get('.auth-area')
    expect(authArea.find('[data-theme-control]').exists()).toBe(true)
    expect(authArea.find('.display-settings-trigger').exists()).toBe(true)
    expect(authArea.find('.auth-btn').exists()).toBe(true)
  })
})
