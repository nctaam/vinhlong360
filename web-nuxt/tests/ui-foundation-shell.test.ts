import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'

import CommandPalette from '../components/CommandPalette.vue'
import IconLine from '../components/IconLine.vue'
import PublicBottomNav from '../components/shell/PublicBottomNav.vue'
import PublicContextBar from '../components/shell/PublicContextBar.vue'
import { AREA_META } from '../composables/useConstants'
import AdminLayout from '../layouts/admin.vue'
import DefaultLayout from '../layouts/default.vue'
import { ADMIN_KINDS } from '../utils/adminKinds'
import {
  ADMIN_NAV_GROUPS,
  isAdminNavItemActive,
  resolveAdminPageLabel,
  type AdminNavItem,
} from '../utils/adminNavigation'

const mocks = vi.hoisted(() => ({
  authUser: { value: null as null | { id: string; role: string; admin_scopes?: string[] } },
  authHeaders: vi.fn(() => ({})),
  fetchMe: vi.fn(() => Promise.resolve()),
  setPref: vi.fn(),
}))

mockNuxtImport('useAuth', () => () => ({
  authHeaders: mocks.authHeaders,
  fetchMe: mocks.fetchMe,
  isLoggedIn: ref(false),
  // Hai dòng này cố ý KHÔNG cùng kiểu, và đó là chủ ý chứ không phải sót khi hợp nhánh:
  // `isLoggedIn` phải là `ref` thật (xem chú thích ngay dưới) vì nó đi thẳng vào một
  // prop Boolean; còn `user` là holder `{ value }` khai trong `vi.hoisted` để các test
  // RBAC gán lại `mocks.authUser.value = {...}` giữa chừng. Không đổi `user` thành
  // `ref()` được: `vi.hoisted` chạy TRƯỚC khi import `vue` được dùng.
  user: mocks.authUser,
}))
// `ref(false)` chứ KHÔNG phải `{ value: false }`: composable thật trả `useState`
// (một ref), nên template `:visible="showAuth"` tự unwrap thành boolean. Mock bằng
// object thường thì prop nhận nguyên object — luôn truthy — nên AuthModal mở thật.
// Đó là gốc của cảnh báo CI `Invalid prop … Expected Boolean, got Object`.
mockNuxtImport('useAuthModal', () => () => ({ open: ref(false) }))
mockNuxtImport('useSeasonTheme', () => () => undefined)
mockNuxtImport('useScrollFade', () => () => undefined)
mockNuxtImport('useAdminPrefs', () => () => ({
  prefs: { value: { sidebarCollapsed: false, pageSize: 50, entityTypeFilter: '' } },
  setPref: mocks.setPref,
}))

const wrappers: Array<{ unmount: () => void }> = []

function mountAdminLayout() {
  return mountSuspended(AdminLayout, {
    attachTo: document.body,
    global: {
      stubs: {
        ClientOnly: { template: '<div><slot /></div>' },
        LazyCommandPalette: CommandPalette,
      },
    },
  })
}

function mountDefaultLayout() {
  return mountSuspended(DefaultLayout, {
    attachTo: document.body,
    slots: { default: '<div>Nội dung</div>' },
    global: {
      // Stub CẢ hai tên cho mỗi component lười. Nuxt auto-import biến `<LazyFoo>` thành
      // import tĩnh, nên Vue Test Utils khớp stub theo `__name` của SFC (`AuthModal`),
      // KHÔNG theo tên viết trong template (`LazyAuthModal`). Khai mỗi tên Lazy* là
      // trượt. Local không lộ vì async chunk chưa resolve kịp trong vòng đời test —
      // bỏ hẳn stub ở local vẫn 15/15 xanh, nên đây là lỗi CI-only (run 31068058171).
      stubs: {
        AuthModal: true,
        LazyAuthModal: true,
        ChatWidget: true,
        LazyChatWidget: true,
        ConfirmDialog: true,
        LazyConfirmDialog: true,
        NotificationBell: true,
        LazyNotificationBell: true,
        OnboardingSheet: true,
        LazyOnboardingSheet: true,
        ScrollToTop: true,
        LazyScrollToTop: true,
        ToastContainer: true,
        LazyToastContainer: true,
        UserMenu: true,
        LazyUserMenu: true,
        SearchAutocomplete: true,
        ShellPublicBottomNav: true,
        ShellPublicContextBar: true,
      },
    },
  })
}

beforeEach(() => {
  mocks.authUser.value = null
  mocks.authHeaders.mockClear()
  mocks.fetchMe.mockClear()
  mocks.setPref.mockClear()
  vi.stubGlobal('$fetch', vi.fn(() => Promise.resolve({})))
})

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  localStorage.clear()
  document.body.style.overflow = ''
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('UI foundation shell', () => {
  it.each(['menu', 'layout-dashboard', 'panel-left-open'])('renders the %s shell icon as SVG', async (name) => {
    const wrapper = await mountSuspended(IconLine, { props: { name } })
    wrappers.push(wrapper)

    expect(wrapper.find('svg').exists()).toBe(true)
    expect(wrapper.find('svg').attributes('stroke-width')).toBe('1.75')
  })

  it('renders a safe help icon when a requested icon is unknown', async () => {
    const wrapper = await mountSuspended(IconLine, { props: { name: 'khong-ton-tai' } })
    wrappers.push(wrapper)

    expect(wrapper.find('svg').exists()).toBe(true)
    expect(wrapper.find('.li-circle-help').exists()).toBe(true)
  })

  it('keeps the SVG mobile menu icon transparent and untransformed', async () => {
    const stylesheet = document.createElement('style')
    stylesheet.textContent = '.nav-toggle span { background-color: rgb(1, 2, 3); transform: translateY(6px) rotate(45deg); }'
    document.head.append(stylesheet)

    const MenuButton = defineComponent({
      setup: () => () => h('button', {
        class: 'nav-toggle public-shell-menu-button',
        'aria-expanded': 'true',
      }, [h(IconLine, { name: 'menu' })]),
    })
    try {
      const wrapper = await mountSuspended(MenuButton, { attachTo: document.body })
      wrappers.push(wrapper)

      const icon = wrapper.get<HTMLElement>('.line-icon').element
      expect(getComputedStyle(icon).backgroundColor).not.toBe('rgb(1, 2, 3)')
      expect(getComputedStyle(icon).transform).not.toContain('rotate(45deg)')
    } finally {
      stylesheet.remove()
    }
  })

  it('maps every Admin entity kind to the shared SVG icon family', async () => {
    const expectedIcons = ['landmark', 'sprout', 'fruit', 'bowl', 'home', 'calendar', 'building', 'user', 'pin']

    expect(ADMIN_KINDS.map(kind => kind.icon)).toEqual(expectedIcons)
    for (const kind of ADMIN_KINDS) {
      const wrapper = await mountSuspended(IconLine, { props: { name: kind.icon } })
      wrappers.push(wrapper)
      expect(wrapper.find('.li-circle-help').exists()).toBe(false)
    }
  })

  it('uses live area metadata while persisting the preferred region', async () => {
    const originalLabel = AREA_META['ben-tre']!.name
    AREA_META['ben-tre']!.name = 'Bến Tre từ cấu hình'

    try {
      const wrapper = await mountSuspended(PublicContextBar)
      wrappers.push(wrapper)

      const select = wrapper.get('select')
      await select.setValue('ben-tre')

      expect(select.element.value).toBe('ben-tre')
      expect(wrapper.text()).toContain('Bến Tre từ cấu hình')
      expect(localStorage.getItem('vl360-region-pref')).toBe('ben-tre')
    } finally {
      AREA_META['ben-tre']!.name = originalLabel
    }
  })

  it('separates the all-region option from its current-context summary', async () => {
    const wrapper = await mountSuspended(PublicContextBar)
    wrappers.push(wrapper)
    await wrapper.get('select').setValue('all')

    expect(wrapper.get('option[value="all"]').text()).toBe('Tất cả khu vực')
    expect(wrapper.get('.public-context-current').text()).toBe('Vĩnh Long · Bến Tre · Trà Vinh')
  })

  it('renders five mobile destinations and marks the current route', async () => {
    const wrapper = await mountSuspended(PublicBottomNav, { route: '/ban-do' })
    wrappers.push(wrapper)

    const links = wrapper.findAll('a')
    expect(links).toHaveLength(5)
    expect(links.map(link => link.attributes('href'))).toEqual(['/', '/du-lich', '/ban-do', '/cong-dong', '/tai-khoan'])
    expect(links.find(link => link.attributes('href') === '/ban-do')?.attributes('aria-current')).toBe('page')
  })

  it('restores focus to the public mobile menu trigger after Escape', async () => {
    const wrapper = await mountDefaultLayout()
    wrappers.push(wrapper)
    vi.useFakeTimers()
    try {
      const trigger = wrapper.get('button[aria-label="Mở danh mục"]')
      ;(trigger.element as HTMLElement).focus()
      await trigger.trigger('click')
      await nextTick()
      await nextTick()

      expect(wrapper.get('#main-nav').classes()).toContain('open')
      expect(wrapper.get('#main-nav').element.contains(document.activeElement)).toBe(true)

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
      await vi.advanceTimersByTimeAsync(250)
      await nextTick()

      expect(wrapper.get('#main-nav').classes()).not.toContain('open')
      expect(document.activeElement).toBe(trigger.element)
    } finally {
      vi.useRealTimers()
    }
  })

  it('keeps the compact mobile login control accessible as a secondary action', async () => {
    const wrapper = await mountDefaultLayout()
    wrappers.push(wrapper)
    await nextTick()

    const login = wrapper.get('button.auth-btn')
    expect(login.attributes('type')).toBe('button')
    expect(login.attributes('aria-label')).toBe('Đăng nhập')
    expect(login.attributes('data-color-role')).toBe('action-secondary')
    expect(login.find('.line-icon').exists()).toBe(true)
    expect(login.get('.auth-btn-label').text()).toBe('Đăng nhập')
  })

  it('resolves exact, prefix and entity-kind Admin navigation states', () => {
    const dashboard: AdminNavItem = { id: 'dashboard', label: 'Tổng quan', to: '/admin', icon: 'layout-dashboard' }
    const settings: AdminNavItem = { id: 'settings', label: 'Cài đặt', to: '/admin/cai-dat', icon: 'settings', prefix: true }
    const products: AdminNavItem = {
      id: 'kind-product',
      label: 'Sản phẩm & OCOP',
      to: { path: '/admin/entities', query: { kind: 'product' } },
      icon: 'fruit',
    }

    expect(isAdminNavItemActive(dashboard, '/admin')).toBe(true)
    expect(isAdminNavItemActive(dashboard, '/admin/thong-ke')).toBe(false)
    expect(isAdminNavItemActive(settings, '/admin/cai-dat/seo')).toBe(true)
    expect(isAdminNavItemActive(products, '/admin/entities', 'product')).toBe(true)
    expect(isAdminNavItemActive(products, '/admin/entities', 'food')).toBe(false)
  })

  it('provides four Admin workstreams and Vietnamese breadcrumb labels without emoji', () => {
    expect(ADMIN_NAV_GROUPS.map(group => group.id)).toEqual(['overview', 'content', 'community', 'system'])
    expect(resolveAdminPageLabel('/admin/cai-dat/seo')).toBe('Cài đặt trang')
    expect(resolveAdminPageLabel('/admin/entities', 'product')).toBe('Sản phẩm & OCOP')
    expect(resolveAdminPageLabel('/admin/kiem-duyet')).toBe('Kiểm duyệt')
    expect(resolveAdminPageLabel('/admin/entities', 'product')).not.toMatch(/\p{Extended_Pictographic}/u)
  })

  it('shows a moderator only the moderation workstream', async () => {
    mocks.authUser.value = {
      id: 'moderator-1',
      role: 'moderator',
      admin_scopes: ['moderation.manager'],
    }
    const wrapper = await mountAdminLayout()
    wrappers.push(wrapper)

    const navigation = wrapper.get('nav[aria-label="Menu quản trị"]')
    expect(navigation.text()).toContain('Kiểm duyệt')
    expect(navigation.text()).toContain('Báo cáo')
    expect(navigation.text()).not.toContain('Thành viên')
    expect(navigation.text()).not.toContain('Chất lượng dữ liệu')
    expect(navigation.text()).not.toContain('Knowledge Agent')
    expect(navigation.findAll('a')).toHaveLength(2)
  })

  it('opens the existing Admin command palette from the topbar hint', async () => {
    const wrapper = await mountAdminLayout()
    wrappers.push(wrapper)

    await wrapper.get('button[aria-label="Mở bảng lệnh"]').trigger('click')
    await nextTick()

    expect(wrapper.get('[role="dialog"][aria-label="Tìm nhanh"]').isVisible()).toBe(true)
  })

  it('filters the command palette by scope and uses SVG icons', async () => {
    mocks.authUser.value = {
      id: 'moderator-2',
      role: 'moderator',
      admin_scopes: ['moderation.manager'],
    }
    const wrapper = await mountAdminLayout()
    wrappers.push(wrapper)

    await wrapper.get('button[aria-label="Mở bảng lệnh"]').trigger('click')
    await nextTick()

    const palette = wrapper.get('[role="dialog"][aria-label="Tìm nhanh"]')
    expect(palette.text()).toContain('Kiểm duyệt')
    expect(palette.text()).toContain('Báo cáo')
    expect(palette.text()).not.toContain('Users')
    expect(palette.text()).not.toContain('Knowledge Agent')
    expect(palette.findAll('.cmd-icon svg')).toHaveLength(3)
    expect(palette.text()).not.toMatch(/\p{Extended_Pictographic}/u)

    await palette.get('input').setValue('không có kết quả')
    expect(palette.get('.cmd-empty-hint').text()).toBe('Thử: Kiểm duyệt, Báo cáo, Về trang chủ…')
  })

  it('traps focus in the mobile Admin drawer and restores it after Escape', async () => {
    const originalOffsetParent = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetParent')
    Object.defineProperty(HTMLElement.prototype, 'offsetParent', {
      configurable: true,
      get: () => document.body,
    })

    try {
      const wrapper = await mountAdminLayout()
      wrappers.push(wrapper)

      const trigger = wrapper.get('button[aria-label="Mở menu quản trị"]')
      ;(trigger.element as HTMLElement).focus()
      await trigger.trigger('click')
      await nextTick()
      await nextTick()

      const drawer = wrapper.get('aside[aria-label="Menu quản trị"]')
      const focusable = drawer.findAll<HTMLElement>('a[href], button:not([disabled])')
      expect(drawer.classes()).toContain('mobile-open')
      expect(drawer.attributes('role')).toBe('dialog')
      expect(drawer.attributes('aria-modal')).toBe('true')
      expect(document.body.style.overflow).toBe('hidden')
      expect(drawer.element.contains(document.activeElement)).toBe(true)

      focusable.at(-1)!.element.focus()
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }))
      expect(document.activeElement).toBe(focusable[0]!.element)

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
      await nextTick()
      await nextTick()
      expect(drawer.classes()).not.toContain('mobile-open')
      expect(document.body.style.overflow).toBe('')
      expect(document.activeElement).toBe(trigger.element)
    } finally {
      if (originalOffsetParent) Object.defineProperty(HTMLElement.prototype, 'offsetParent', originalOffsetParent)
      else Reflect.deleteProperty(HTMLElement.prototype, 'offsetParent')
    }
  })

})
