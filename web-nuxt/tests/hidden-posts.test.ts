/**
 * Tự dọn bảng tin — nối 3 endpoint đã có mà frontend chưa từng gọi:
 *   POST /api/posts/{id}/hide, POST /api/posts/{id}/unhide, GET /api/posts/hidden
 * (agent/social.py:3355 / :3377 / :3395 — trước đợt này grep `posts/hidden`
 * trong web-nuxt/ ra 0 hit).
 *
 * Bất biến được khoá ở đây:
 *  (a) menu bài viết có "Ẩn bài này" ĐÚNG chỗ được phép, và phát `hide`;
 *  (b) ẩn thì bài rời feed NGAY (lạc quan) và gọi đúng URL + header phiên;
 *  (c) API lỗi thì bài quay lại ĐÚNG vị trí cũ + có báo lỗi thấy được —
 *      thao tác dữ liệu KHÔNG được nuốt lỗi như beacon đo đạc;
 *  (d) 401 đẩy sang luồng hết-phiên, không hiện lỗi chung chung;
 *  (e) danh sách bài đã ẩn xem lại + bỏ ẩn được, cũng có hoàn nguyên khi lỗi;
 *  (f) nút "Ẩn" KHÔNG được bật ở màn hình mà backend không lọc bài đã ẩn.
 */
import { mountSuspended, mockNuxtImport } from '@nuxt/test-utils/runtime'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import PostCard from '../components/PostCard.vue'
import { useHiddenPosts, removePostFromLists } from '../composables/useHiddenPosts'
import type { HideablePost } from '../composables/useHiddenPosts'

const mocks = vi.hoisted(() => ({
  authHeaders: vi.fn(() => ({ Authorization: 'Bearer t', 'X-CSRF-Token': 'csrf-1' })),
  fetch: vi.fn(),
  handleSessionExpired: vi.fn(),
  isLoggedIn: { value: true },
  showToast: vi.fn(),
}))

mockNuxtImport('useAuth', () => () => ({
  authHeaders: mocks.authHeaders,
  handleSessionExpired: mocks.handleSessionExpired,
  isLoggedIn: mocks.isLoggedIn,
  user: { value: { id: 'me' } },
}))
mockNuxtImport('useToast', () => () => ({ show: mocks.showToast }))

const wrappers: Array<{ unmount: () => void }> = []

function src(relative: string) {
  return readFileSync(resolve(process.cwd(), relative), 'utf8')
}

function post(id: string, extra: Record<string, unknown> = {}): HideablePost {
  return { id, user_id: `author-${id}`, content: `Nội dung ${id}`, created_at: '2026-07-20T00:00:00Z', ...extra }
}

/** Lỗi kiểu ofetch: có `response.status` + `response._data.detail`. */
function httpError(status: number, detail?: string) {
  return Object.assign(new Error(`[POST] "/api/x": ${status}`), {
    response: { status, _data: detail ? { detail } : {} },
  })
}

beforeEach(() => {
  mocks.authHeaders.mockClear()
  mocks.fetch.mockReset()
  mocks.fetch.mockResolvedValue({ success: true })
  mocks.handleSessionExpired.mockReset()
  mocks.showToast.mockReset()
  mocks.isLoggedIn.value = true
  vi.stubGlobal('$fetch', mocks.fetch)
})

afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
  vi.unstubAllGlobals()
})

// ── (a) Điểm vào trên thẻ bài viết ────────────────────────────────────────

describe('(a) PostCard — mục "Ẩn bài này"', () => {
  async function openMenu(props: { post: Record<string, any>; canHide?: boolean }) {
    const wrapper = await mountSuspended(PostCard, { props })
    wrappers.push(wrapper)
    await wrapper.get('.thread-more').trigger('click')
    return wrapper
  }

  it('không hiện khi host chưa bật can-hide (mặc định) — không có nút chết', async () => {
    const wrapper = await openMenu({ post: post('p1') })
    expect(wrapper.find('[data-post-action="hide"]').exists()).toBe(false)
  })

  it('hiện và phát sự kiện `hide` kèm id khi can-hide bật', async () => {
    const wrapper = await openMenu({ post: post('p1'), canHide: true })
    const button = wrapper.get('[data-post-action="hide"]')
    expect(button.text()).toBe('Ẩn bài này')
    expect(button.attributes('role')).toBe('menuitem')
    await button.trigger('click')
    expect(wrapper.emitted('hide')).toEqual([['p1']])
    // menu đóng lại sau khi chọn
    expect(wrapper.find('[data-post-action="hide"]').exists()).toBe(false)
  })

  it('không hiện trên bài của chính mình (bài mình thì Sửa/Xoá, không phải ẩn)', async () => {
    const wrapper = await openMenu({ post: post('p1', { user_id: 'me' }), canHide: true })
    expect(wrapper.find('[data-post-action="hide"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Xoá bài')
  })
})

// ── (b)(c)(d) hidePost — lạc quan + hoàn nguyên ───────────────────────────

describe('(b) ẩn bài — bài rời feed ngay và gọi đúng hợp đồng', () => {
  it('gọi POST /api/posts/{id}/hide kèm header phiên và gỡ bài khỏi mọi danh sách', async () => {
    const feed = ref([post('a'), post('b'), post('c')])
    const bookmarks = ref([post('b')])
    const { hidePost } = useHiddenPosts()

    const ok = await hidePost('b', [feed, bookmarks])

    expect(ok).toBe(true)
    expect(feed.value.map(p => p.id)).toEqual(['a', 'c'])
    expect(bookmarks.value).toEqual([])
    expect(mocks.fetch).toHaveBeenCalledTimes(1)
    const [url, opts] = mocks.fetch.mock.calls[0] as [string, any]
    expect(url).toBe('/api/posts/b/hide')
    expect(opts.method).toBe('POST')
    expect(opts.headers).toEqual({ Authorization: 'Bearer t', 'X-CSRF-Token': 'csrf-1' })
  })

  it('mã hoá id trong đường dẫn (không ghép chuỗi thô)', async () => {
    const feed = ref([post('a/b?c')])
    await useHiddenPosts().hidePost('a/b?c', [feed])
    expect(mocks.fetch.mock.calls[0]![0]).toBe('/api/posts/a%2Fb%3Fc/hide')
  })

  it('chưa đăng nhập thì không gọi API và bài ở nguyên chỗ', async () => {
    mocks.isLoggedIn.value = false
    const feed = ref([post('a')])

    const ok = await useHiddenPosts().hidePost('a', [feed])

    expect(ok).toBe(false)
    expect(mocks.fetch).not.toHaveBeenCalled()
    expect(feed.value.map(p => p.id)).toEqual(['a'])
    expect(mocks.showToast).toHaveBeenCalledWith(expect.stringContaining('Đăng nhập'), 'info')
  })

  it('bấm liên tiếp cùng một bài chỉ gửi 1 request', async () => {
    let release: (v: unknown) => void = () => {}
    mocks.fetch.mockImplementation(() => new Promise((r) => { release = r }))
    const feed = ref([post('a'), post('b')])
    const { hidePost } = useHiddenPosts()

    const first = hidePost('a', [feed])
    const second = await hidePost('a', [feed])

    expect(second).toBe(false)
    expect(mocks.fetch).toHaveBeenCalledTimes(1)
    release({ success: true })
    expect(await first).toBe(true)
  })
})

describe('(c) API lỗi — bài quay lại đúng vị trí cũ + báo lỗi thấy được', () => {
  it('500 giữa danh sách: bài về lại đúng index, có toast lỗi', async () => {
    mocks.fetch.mockRejectedValue(httpError(500))
    const feed = ref([post('a'), post('b'), post('c')])

    const ok = await useHiddenPosts().hidePost('b', [feed])

    expect(ok).toBe(false)
    expect(feed.value.map(p => p.id)).toEqual(['a', 'b', 'c'])
    expect(mocks.showToast).toHaveBeenCalledWith('Không thể ẩn bài viết', 'error')
    expect(mocks.handleSessionExpired).not.toHaveBeenCalled()
  })

  it('hoàn nguyên đủ MỌI danh sách, kể cả bài xuất hiện ở nhiều nơi', async () => {
    mocks.fetch.mockRejectedValue(httpError(500))
    const feed = ref([post('a'), post('b')])
    const bookmarks = ref([post('x'), post('b')])
    const search = ref([post('b')])

    await useHiddenPosts().hidePost('b', [feed, bookmarks, search])

    expect(feed.value.map(p => p.id)).toEqual(['a', 'b'])
    expect(bookmarks.value.map(p => p.id)).toEqual(['x', 'b'])
    expect(search.value.map(p => p.id)).toEqual(['b'])
  })

  it('429 hiển thị đúng lý do backend trả (người dùng cần biết là phải chờ)', async () => {
    mocks.fetch.mockRejectedValue(httpError(429, 'Thao tác quá nhanh. Vui lòng thử lại sau.'))
    const feed = ref([post('a')])

    await useHiddenPosts().hidePost('a', [feed])

    expect(feed.value.map(p => p.id)).toEqual(['a'])
    expect(mocks.showToast).toHaveBeenCalledWith('Thao tác quá nhanh. Vui lòng thử lại sau.', 'error')
  })

  it('KHÔNG lộ chuỗi lỗi kỹ thuật của ofetch ra toast', async () => {
    mocks.fetch.mockRejectedValue(new Error('[POST] "/api/posts/a/hide": 502 Bad Gateway'))
    const feed = ref([post('a')])

    await useHiddenPosts().hidePost('a', [feed])

    expect(mocks.showToast).toHaveBeenCalledWith('Không thể ẩn bài viết', 'error')
  })

  it('404 (bài đã bị xoá) vẫn hoàn nguyên và báo lỗi, không im lặng', async () => {
    mocks.fetch.mockRejectedValue(httpError(404, 'Không tìm thấy bài viết'))
    const feed = ref([post('a')])

    const ok = await useHiddenPosts().hidePost('a', [feed])

    expect(ok).toBe(false)
    expect(feed.value.map(p => p.id)).toEqual(['a'])
    expect(mocks.showToast).toHaveBeenCalledWith('Không tìm thấy bài viết', 'error')
  })
})

describe('(d) 401 — đẩy sang luồng hết phiên', () => {
  it('gọi handleSessionExpired và KHÔNG hiện toast lỗi chung chung', async () => {
    mocks.fetch.mockRejectedValue(httpError(401))
    const feed = ref([post('a')])

    const ok = await useHiddenPosts().hidePost('a', [feed])

    expect(ok).toBe(false)
    expect(feed.value.map(p => p.id)).toEqual(['a'])
    expect(mocks.handleSessionExpired).toHaveBeenCalledTimes(1)
    expect(mocks.showToast).not.toHaveBeenCalled()
  })
})

// ── (e) Xem lại + bỏ ẩn ───────────────────────────────────────────────────

describe('(e) danh sách bài đã ẩn + bỏ ẩn', () => {
  it('GET /api/posts/hidden có phân trang và header phiên', async () => {
    mocks.fetch.mockResolvedValue({ posts: [post('a')], total: 21, page: 2, has_more: false })

    const page = await useHiddenPosts().fetchHiddenPosts(2, 20)

    const [url, opts] = mocks.fetch.mock.calls[0] as [string, any]
    expect(url).toBe('/api/posts/hidden?page=2&limit=20')
    expect(opts.headers).toEqual({ Authorization: 'Bearer t', 'X-CSRF-Token': 'csrf-1' })
    expect(page).toEqual({ posts: [expect.objectContaining({ id: 'a' })], total: 21, page: 2, has_more: false })
  })

  it('chuẩn hoá phản hồi thiếu trường thay vì để undefined rò ra giao diện', async () => {
    mocks.fetch.mockResolvedValue({})
    expect(await useHiddenPosts().fetchHiddenPosts()).toEqual({ posts: [], total: 0, page: 1, has_more: false })
  })

  it('bỏ ẩn gọi POST /unhide và gỡ dòng khỏi danh sách', async () => {
    const hidden = ref([post('a'), post('b')])

    const ok = await useHiddenPosts().unhidePost('a', [hidden])

    expect(ok).toBe(true)
    expect(mocks.fetch.mock.calls[0]![0]).toBe('/api/posts/a/unhide')
    expect(hidden.value.map(p => p.id)).toEqual(['b'])
  })

  it('bỏ ẩn lỗi thì dòng quay lại danh sách + báo lỗi', async () => {
    mocks.fetch.mockRejectedValue(httpError(500))
    const hidden = ref([post('a'), post('b')])

    const ok = await useHiddenPosts().unhidePost('b', [hidden])

    expect(ok).toBe(false)
    expect(hidden.value.map(p => p.id)).toEqual(['a', 'b'])
    expect(mocks.showToast).toHaveBeenCalledWith('Không thể bỏ ẩn bài viết', 'error')
  })

  it('bỏ ẩn từ dải "Hoàn tác" (không kèm danh sách nào) vẫn gọi API', async () => {
    expect(await useHiddenPosts().unhidePost('a')).toBe(true)
    expect(mocks.fetch.mock.calls[0]![0]).toBe('/api/posts/a/unhide')
  })
})

describe('removePostFromLists — hoàn nguyên đúng vị trí', () => {
  it('trả bài về đúng index kể cả khi nằm giữa danh sách dài', () => {
    const list = ref([post('a'), post('b'), post('c'), post('d')])
    const restore = removePostFromLists('c', [list])
    expect(list.value.map(p => p.id)).toEqual(['a', 'b', 'd'])
    restore()
    expect(list.value.map(p => p.id)).toEqual(['a', 'b', 'c', 'd'])
  })

  it('bỏ qua danh sách không chứa bài (không ném, không đụng dữ liệu)', () => {
    const list = ref([post('a')])
    removePostFromLists('zzz', [list])()
    expect(list.value.map(p => p.id)).toEqual(['a'])
  })
})

// ── (f) Ràng buộc nơi được phép bật nút "Ẩn" ──────────────────────────────

describe('(f) chỉ bật "Ẩn" ở màn hình backend THẬT SỰ lọc bài đã ẩn', () => {
  /**
   * `user_hidden_posts` chỉ được lọc ở /api/feed, /api/feed/following và
   * /api/feed/friend-reviews. Bật nút ở tab "Đã lưu" (/api/me/bookmarks), kết
   * quả tìm kiếm (/api/search/posts), hồ sơ người dùng (/api/users/{id}/posts)
   * hay trang chi tiết bài thì bài sẽ quay lại sau khi tải lại trang.
   */
  const community = src('pages/cong-dong.vue')

  it('trang cộng đồng truyền can-hide và lắng nghe @hide', () => {
    expect(community).toContain(':can-hide="canHidePosts"')
    expect(community).toContain('@hide="hidePost"')
  })

  it('canHidePosts loại tab "Đã lưu" và chế-độ tìm kiếm', () => {
    expect(community).toContain(
      "const canHidePosts = computed(() => !searchMode.value && activeTab.value !== 'bookmarks')",
    )
  })

  it('các màn PostCard khác KHÔNG bật can-hide', () => {
    expect(src('pages/nguoi-dung/[id].vue')).not.toContain('can-hide')
    expect(src('pages/bai-viet/[id].vue')).not.toContain('can-hide')
  })

  it('trang cài đặt có tab "Bài đã ẩn" nối vào composable', () => {
    const settings = src('pages/cai-dat.vue')
    expect(settings).toContain("{ key: 'bai-da-an', label: 'Bài đã ẩn'")
    expect(settings).toContain("else if (key === 'bai-da-an') loadHiddenPosts(true)")
    expect(settings).toContain('const { fetchHiddenPosts, unhidePost } = useHiddenPosts()')
    // lỗi tải phải hiện được, không nuốt như `catch { /* ignore */ }` của tab chặn/tắt tiếng
    expect(settings).toContain('hiddenError.value = true')
  })
})

// ── (g) Xuyên suốt trên trang cộng đồng thật ──────────────────────────────

describe('(g) /cong-dong — bấm "Ẩn bài này" thật trên feed', () => {
  const feedPosts = [
    post('feed-1', { display_name: 'Lan' }),
    post('feed-2', { display_name: 'Minh' }),
  ]

  function installFeedDispatch(hideImpl: () => unknown) {
    mocks.fetch.mockImplementation((url: string) => {
      if (typeof url === 'string' && url.endsWith('/hide')) return Promise.resolve(hideImpl())
      if (typeof url === 'string' && url.startsWith('/api/feed')) {
        return Promise.resolve({ posts: feedPosts.map(p => ({ ...p })), page: 1, total: 2, has_more: false })
      }
      return Promise.resolve({})
    })
  }

  async function mountCommunity() {
    const CommunityPage = (await import('../pages/cong-dong.vue')).default
    const wrapper = await mountSuspended(CommunityPage)
    wrappers.push(wrapper)
    await flush()
    return wrapper
  }

  async function flush() {
    for (let i = 0; i < 6; i++) await new Promise(resolve => setTimeout(resolve, 0))
  }

  /** Mở menu ⋯ của thẻ bài đầu tiên khớp id rồi bấm "Ẩn bài này". */
  async function clickHide(wrapper: any, postId: string) {
    const card = wrapper.findAllComponents(PostCard).find((c: any) => c.props('post')?.id === postId)
    expect(card, `không thấy thẻ bài ${postId}`).toBeTruthy()
    await card!.get('.thread-more').trigger('click')
    await card!.get('[data-post-action="hide"]').trigger('click')
    await flush()
  }

  it('ẩn thành công: thẻ biến mất khỏi feed và hiện dải "Hoàn tác"', async () => {
    installFeedDispatch(() => ({ success: true }))
    const wrapper = await mountCommunity()
    expect(wrapper.findAllComponents(PostCard)).toHaveLength(2)

    await clickHide(wrapper, 'feed-1')

    const remaining = wrapper.findAllComponents(PostCard).map((c: any) => c.props('post').id)
    expect(remaining).toEqual(['feed-2'])
    expect(mocks.fetch).toHaveBeenCalledWith('/api/posts/feed-1/hide', expect.objectContaining({ method: 'POST' }))
    expect(wrapper.find('[data-testid="hide-undo"]').exists()).toBe(true)
    expect(wrapper.find('[data-post-action="undo-hide"]').exists()).toBe(true)
  })

  it('API lỗi: bài QUAY LẠI feed, có toast lỗi, KHÔNG hiện dải "Hoàn tác"', async () => {
    installFeedDispatch(() => { throw httpError(500) })
    const wrapper = await mountCommunity()

    await clickHide(wrapper, 'feed-1')

    const remaining = wrapper.findAllComponents(PostCard).map((c: any) => c.props('post').id)
    expect(remaining).toEqual(['feed-1', 'feed-2'])
    expect(mocks.showToast).toHaveBeenCalledWith('Không thể ẩn bài viết', 'error')
    expect(wrapper.find('[data-testid="hide-undo"]').exists()).toBe(false)
  })

  it('"Hoàn tác" gọi /unhide rồi nạp lại feed', async () => {
    installFeedDispatch(() => ({ success: true }))
    const wrapper = await mountCommunity()
    await clickHide(wrapper, 'feed-1')

    await wrapper.get('[data-post-action="undo-hide"]').trigger('click')
    await flush()

    expect(mocks.fetch).toHaveBeenCalledWith('/api/posts/feed-1/unhide', expect.objectContaining({ method: 'POST' }))
    expect(wrapper.find('[data-testid="hide-undo"]').exists()).toBe(false)
    expect(wrapper.findAllComponents(PostCard).map((c: any) => c.props('post').id)).toEqual(['feed-1', 'feed-2'])
  })
})

// ── (h) Xuyên suốt trên tab "Bài đã ẩn" của /cai-dat ──────────────────────

describe('(h) /cai-dat — tab "Bài đã ẩn"', () => {
  async function flush() {
    for (let i = 0; i < 6; i++) await new Promise(resolve => setTimeout(resolve, 0))
  }

  function installSettingsDispatch(hidden: () => unknown, unhide: () => unknown = () => ({ success: true })) {
    mocks.fetch.mockImplementation((url: string) => {
      if (typeof url === 'string' && url.startsWith('/api/posts/hidden')) return Promise.resolve(hidden())
      if (typeof url === 'string' && url.endsWith('/unhide')) return Promise.resolve(unhide())
      return Promise.resolve({})
    })
  }

  async function openHiddenTab() {
    const SettingsPage = (await import('../pages/cai-dat.vue')).default
    const wrapper = await mountSuspended(SettingsPage)
    wrappers.push(wrapper)
    await flush()
    await wrapper.get('#tab-bai-da-an').trigger('click')
    await flush()
    return wrapper
  }

  it('liệt kê bài đã ẩn kèm nút "Bỏ ẩn"; bỏ ẩn xong thì dòng biến mất', async () => {
    installSettingsDispatch(() => ({
      posts: [post('h-1', { content: 'Bài đã ẩn số một' }), post('h-2', { content: 'Bài đã ẩn số hai' })],
      total: 2, page: 1, has_more: false,
    }))
    const wrapper = await openHiddenTab()

    expect(mocks.fetch).toHaveBeenCalledWith('/api/posts/hidden?page=1&limit=20', expect.anything())
    expect(wrapper.findAll('[data-testid="hidden-post-row"]')).toHaveLength(2)
    expect(wrapper.text()).toContain('Bài đã ẩn số một')

    await wrapper.findAll('[data-post-action="unhide"]')[0]!.trigger('click')
    await flush()

    expect(mocks.fetch).toHaveBeenCalledWith('/api/posts/h-1/unhide', expect.objectContaining({ method: 'POST' }))
    expect(wrapper.findAll('[data-testid="hidden-post-row"]')).toHaveLength(1)
    expect(mocks.showToast).toHaveBeenCalledWith('Đã bỏ ẩn bài viết', 'success')
  })

  it('bỏ ẩn lỗi: dòng quay lại danh sách + báo lỗi (không nuốt im lặng)', async () => {
    installSettingsDispatch(
      () => ({ posts: [post('h-1'), post('h-2')], total: 2, page: 1, has_more: false }),
      () => { throw httpError(500) },
    )
    const wrapper = await openHiddenTab()

    await wrapper.findAll('[data-post-action="unhide"]')[0]!.trigger('click')
    await flush()

    expect(wrapper.findAll('[data-testid="hidden-post-row"]')).toHaveLength(2)
    expect(mocks.showToast).toHaveBeenCalledWith('Không thể bỏ ẩn bài viết', 'error')
  })

  it('tải danh sách lỗi: hiện thông báo lỗi + nút thử lại, KHÔNG giả vờ "chưa ẩn bài nào"', async () => {
    installSettingsDispatch(() => { throw httpError(500) })
    const wrapper = await openHiddenTab()

    const panel = wrapper.get('#panel-bai-da-an')
    expect(panel.text()).toContain('Không thể tải danh sách bài đã ẩn')
    expect(panel.text()).not.toContain('Bạn chưa ẩn bài viết nào')
    expect(mocks.showToast).toHaveBeenCalledWith('Không thể tải danh sách bài đã ẩn', 'error')
  })

  it('danh sách rỗng thật thì nói rõ là chưa ẩn bài nào', async () => {
    installSettingsDispatch(() => ({ posts: [], total: 0, page: 1, has_more: false }))
    const wrapper = await openHiddenTab()
    expect(wrapper.get('#panel-bai-da-an').text()).toContain('Bạn chưa ẩn bài viết nào')
  })
})
