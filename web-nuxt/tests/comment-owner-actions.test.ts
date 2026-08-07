/**
 * Quyền của người dùng với bình luận của CHÍNH HỌ — nối 2 endpoint đã có mà
 * frontend chưa từng gọi:
 *   PUT /api/comments/{id}  (agent/social.py:2464)
 *   DELETE /api/comments/{id} (agent/social.py:2508)
 * Trước đợt này grep `/api/comments/` trong web-nuxt/ ra 0 hit, nghĩa là người
 * dùng KHÔNG sửa/xoá được lời của mình.
 *
 * Quyền ở đây phải khớp hành vi thật của backend, đã đo bằng TestClient ở
 * tests/test_social_comment_ownership.py:
 *   sửa = chỉ tác giả trong 24h (admin cũng 403); xoá = tác giả hoặc admin.
 *
 * Bất biến được khoá:
 *  (a) nút chỉ hiện đúng người — không có nút chết trên giao diện;
 *  (b) sửa inline, huỷ thì nội dung cũ còn nguyên, lỗi thì chữ đã gõ không mất;
 *  (c) xoá phải qua xác nhận, và xác nhận nói rõ trả lời con bị ẩn theo;
 *  (d) lỗi API hiển thị được cho người dùng — thao tác dữ liệu KHÔNG nuốt lỗi
 *      im lặng như beacon đo đạc, và 401 đi đúng luồng hết-phiên;
 *  (e) trang bài viết nối cả bình luận gốc LẪN trả lời, không lệch nhánh.
 */
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { flushPromises } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import CommentEditable from '../components/CommentEditable.vue'
import PostDetailPage from '../pages/bai-viet/[id].vue'
import { useConfirm } from '../composables/useConfirm'

const mocks = vi.hoisted(() => ({
  authHeaders: vi.fn(() => ({ Authorization: 'Bearer t', 'X-CSRF-Token': 'csrf-1' })),
  fetch: vi.fn(),
  handleSessionExpired: vi.fn(),
  isLoggedIn: { value: true },
  showToast: vi.fn(),
  user: { value: { id: 'me', role: 'user' } as { id: string; role: string } | null },
}))

mockNuxtImport('useAuth', () => () => ({
  authHeaders: mocks.authHeaders,
  handleSessionExpired: mocks.handleSessionExpired,
  isLoggedIn: mocks.isLoggedIn,
  user: mocks.user,
}))
mockNuxtImport('useToast', () => () => ({ show: mocks.showToast }))

const wrappers: Array<{ unmount: () => void }> = []

const HOUR = 3_600_000

function isoAgo(hours: number) {
  return new Date(Date.now() - hours * HOUR).toISOString()
}

function comment(over: Record<string, unknown> = {}) {
  return {
    id: 'c1',
    post_id: 'p1',
    user_id: 'me',
    content: 'Bánh tét Trà Cuôn ở chợ sáng bán tới 9 giờ.',
    created_at: isoAgo(1),
    author: { id: 'me', display_name: 'Tôi' },
    ...over,
  }
}

/** Lỗi kiểu ofetch: có `response.status` + `response._data.detail`. */
function httpError(status: number, detail?: string) {
  return Object.assign(new Error(`[PUT] "/api/comments/c1": ${status}`), {
    response: { status, _data: detail ? { detail } : {} },
  })
}

async function mountComment(over: Record<string, unknown> = {}) {
  const wrapper = await mountSuspended(CommentEditable, { props: { comment: comment(over) } })
  wrappers.push(wrapper)
  return wrapper
}

/** Trả lời hộp xác nhận đang mở. Ném lỗi nếu KHÔNG có hộp nào — "quên hỏi" phải đỏ. */
async function answerConfirm(value: boolean) {
  const { state, answer } = useConfirm()
  await nextTick()
  expect(state.value.open, 'phải hỏi xác nhận trước khi gọi API xoá').toBe(true)
  const message = state.value.message
  answer(value)
  await flushPromises()
  return message
}

beforeEach(() => {
  mocks.authHeaders.mockClear()
  mocks.fetch.mockReset()
  mocks.fetch.mockResolvedValue({ comment: { id: 'c1', content: 'Nội dung mới' } })
  mocks.handleSessionExpired.mockReset()
  mocks.showToast.mockReset()
  mocks.isLoggedIn.value = true
  mocks.user.value = { id: 'me', role: 'user' }
  vi.stubGlobal('$fetch', mocks.fetch)
})

afterEach(() => {
  while (wrappers.length) wrappers.pop()!.unmount()
  vi.unstubAllGlobals()
})

// ── (a) Nút chỉ hiện đúng người ──────────────────────────────────────────────

describe('(a) ai thấy nút Sửa / Xoá', () => {
  it('tác giả thấy cả Sửa và Xoá', async () => {
    const wrapper = await mountComment()
    expect(wrapper.find('[data-comment-action="edit"]').exists()).toBe(true)
    expect(wrapper.find('[data-comment-action="delete"]').exists()).toBe(true)
  })

  it('người khác KHÔNG thấy nút nào', async () => {
    const wrapper = await mountComment({ author: { id: 'nguoi-khac' }, user_id: 'nguoi-khac' })
    expect(wrapper.find('[data-comment-action="edit"]').exists()).toBe(false)
    expect(wrapper.find('[data-comment-action="delete"]').exists()).toBe(false)
  })

  it('khách chưa đăng nhập KHÔNG thấy nút nào', async () => {
    mocks.user.value = null
    mocks.isLoggedIn.value = false
    const wrapper = await mountComment()
    expect(wrapper.find('[data-comment-action="edit"]').exists()).toBe(false)
    expect(wrapper.find('[data-comment-action="delete"]').exists()).toBe(false)
  })

  it('admin xoá được bình luận người khác nhưng KHÔNG sửa được — khớp social.py:2528', async () => {
    mocks.user.value = { id: 'admin-1', role: 'admin' }
    const wrapper = await mountComment({ author: { id: 'nguoi-khac' }, user_id: 'nguoi-khac' })
    expect(wrapper.find('[data-comment-action="delete"]').exists()).toBe(true)
    expect(wrapper.find('[data-comment-action="edit"]').exists()).toBe(false)
  })

  it('moderator cũng xoá được', async () => {
    mocks.user.value = { id: 'mod-1', role: 'moderator' }
    const wrapper = await mountComment({ author: { id: 'nguoi-khac' }, user_id: 'nguoi-khac' })
    expect(wrapper.find('[data-comment-action="delete"]').exists()).toBe(true)
  })

  it('quá cửa sổ 24h thì tác giả chỉ còn Xoá — backend đã 400 với nút Sửa', async () => {
    const wrapper = await mountComment({ created_at: isoAgo(25) })
    expect(wrapper.find('[data-comment-action="edit"]').exists()).toBe(false)
    expect(wrapper.find('[data-comment-action="delete"]').exists()).toBe(true)
  })

  it('mốc thời gian hỏng thì vẫn cho bấm Sửa — để backend phán, đừng khoá oan', async () => {
    const wrapper = await mountComment({ created_at: 'khong-phai-ngay' })
    expect(wrapper.find('[data-comment-action="edit"]').exists()).toBe(true)
  })
})

// ── (b) Sửa inline ───────────────────────────────────────────────────────────

describe('(b) sửa inline', () => {
  it('bấm Sửa thì hiện ô sửa mang sẵn nội dung cũ', async () => {
    const wrapper = await mountComment()
    await wrapper.get('[data-comment-action="edit"]').trigger('click')

    const input = wrapper.get('[data-comment-action="edit-input"]')
    expect((input.element as HTMLTextAreaElement).value)
      .toBe('Bánh tét Trà Cuôn ở chợ sáng bán tới 9 giờ.')
  })

  it('Huỷ thì nội dung cũ còn nguyên và KHÔNG gọi API', async () => {
    const wrapper = await mountComment()
    await wrapper.get('[data-comment-action="edit"]').trigger('click')
    await wrapper.get('[data-comment-action="edit-input"]').setValue('Chữ gõ dở rồi bỏ')
    await wrapper.get('[data-comment-action="edit-cancel"]').trigger('click')

    expect(mocks.fetch).not.toHaveBeenCalled()
    expect(wrapper.find('[data-comment-action="edit-input"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Bánh tét Trà Cuôn ở chợ sáng bán tới 9 giờ.')
    expect(wrapper.text()).not.toContain('Chữ gõ dở rồi bỏ')
  })

  it('Lưu gọi PUT đúng địa chỉ, kèm header phiên + CSRF, nội dung đã cắt khoảng trắng', async () => {
    const wrapper = await mountComment()
    await wrapper.get('[data-comment-action="edit"]').trigger('click')
    await wrapper.get('[data-comment-action="edit-input"]').setValue('  Nội dung mới  ')
    await wrapper.get('[data-comment-action="edit-save"]').trigger('click')
    await flushPromises()

    expect(mocks.fetch).toHaveBeenCalledTimes(1)
    const [url, init] = mocks.fetch.mock.calls[0]!
    expect(url).toBe('/api/comments/c1')
    expect(init.method).toBe('PUT')
    expect(init.body).toEqual({ content: 'Nội dung mới' })
    expect(init.headers).toMatchObject({ 'X-CSRF-Token': 'csrf-1' })
  })

  it('Lưu xong phát `updated` kèm nội dung backend trả về', async () => {
    const wrapper = await mountComment()
    await wrapper.get('[data-comment-action="edit"]').trigger('click')
    await wrapper.get('[data-comment-action="edit-input"]').setValue('Nội dung mới')
    await wrapper.get('[data-comment-action="edit-save"]').trigger('click')
    await flushPromises()

    expect(wrapper.emitted('updated')).toEqual([[{ id: 'c1', content: 'Nội dung mới' }]])
    expect(wrapper.find('[data-comment-action="edit-input"]').exists()).toBe(false)
  })

  it('API lỗi thì ô sửa VẪN mở, chữ đã gõ không mất, và người dùng đọc được lý do', async () => {
    mocks.fetch.mockRejectedValue(httpError(400, 'Chỉ có thể sửa bình luận trong 24 giờ đầu'))
    const wrapper = await mountComment()
    await wrapper.get('[data-comment-action="edit"]').trigger('click')
    await wrapper.get('[data-comment-action="edit-input"]').setValue('Chữ tôi vừa gõ')
    await wrapper.get('[data-comment-action="edit-save"]').trigger('click')
    await flushPromises()

    const input = wrapper.get('[data-comment-action="edit-input"]')
    expect((input.element as HTMLTextAreaElement).value).toBe('Chữ tôi vừa gõ')
    expect(wrapper.emitted('updated')).toBeUndefined()
    expect(mocks.showToast).toHaveBeenCalledWith('Chỉ có thể sửa bình luận trong 24 giờ đầu', 'error')
  })

  it('401 đi luồng hết-phiên, không hiện lỗi chung chung', async () => {
    mocks.fetch.mockRejectedValue(httpError(401))
    const wrapper = await mountComment()
    await wrapper.get('[data-comment-action="edit"]').trigger('click')
    await wrapper.get('[data-comment-action="edit-input"]').setValue('Nội dung mới')
    await wrapper.get('[data-comment-action="edit-save"]').trigger('click')
    await flushPromises()

    expect(mocks.handleSessionExpired).toHaveBeenCalledTimes(1)
    expect(mocks.showToast).not.toHaveBeenCalled()
  })

  it('nội dung quá ngắn thì nút Lưu khoá, không đốt lượt rate-limit', async () => {
    const wrapper = await mountComment()
    await wrapper.get('[data-comment-action="edit"]').trigger('click')
    await wrapper.get('[data-comment-action="edit-input"]').setValue('x')

    const save = wrapper.get('[data-comment-action="edit-save"]')
    expect((save.element as HTMLButtonElement).disabled).toBe(true)
    await save.trigger('click')
    await flushPromises()
    expect(mocks.fetch).not.toHaveBeenCalled()
  })
})

// ── (c) + (d) Xoá: xác nhận trước, lỗi hiện ra ───────────────────────────────

describe('(c) xoá bình luận', () => {
  it('người dùng huỷ xác nhận thì KHÔNG gọi API', async () => {
    const wrapper = await mountComment()
    wrapper.get('[data-comment-action="delete"]').trigger('click')
    await answerConfirm(false)

    expect(mocks.fetch).not.toHaveBeenCalled()
    expect(wrapper.emitted('deleted')).toBeUndefined()
  })

  it('xác nhận rồi mới gọi DELETE, kèm header phiên + CSRF', async () => {
    mocks.fetch.mockResolvedValue({ success: true })
    const wrapper = await mountComment()
    wrapper.get('[data-comment-action="delete"]').trigger('click')
    await answerConfirm(true)

    expect(mocks.fetch).toHaveBeenCalledTimes(1)
    const [url, init] = mocks.fetch.mock.calls[0]!
    expect(url).toBe('/api/comments/c1')
    expect(init.method).toBe('DELETE')
    expect(init.headers).toMatchObject({ 'X-CSRF-Token': 'csrf-1' })
    expect(wrapper.emitted('deleted')).toEqual([['c1']])
  })

  it('bình luận có trả lời thì xác nhận nói rõ số trả lời sẽ bị ẩn theo', async () => {
    mocks.fetch.mockResolvedValue({ success: true })
    const wrapper = await mountComment({ replies: [{ id: 'r1' }, { id: 'r2' }] })
    wrapper.get('[data-comment-action="delete"]').trigger('click')
    const message = await answerConfirm(true)

    expect(message).toContain('2 trả lời')
  })

  it('API lỗi thì báo cho người dùng và KHÔNG coi như đã xoá', async () => {
    mocks.fetch.mockRejectedValue(httpError(403, 'Bạn chỉ có thể xóa bình luận của mình'))
    const wrapper = await mountComment()
    wrapper.get('[data-comment-action="delete"]').trigger('click')
    await answerConfirm(true)

    expect(mocks.showToast).toHaveBeenCalledWith('Bạn chỉ có thể xóa bình luận của mình', 'error')
    expect(wrapper.emitted('deleted')).toBeUndefined()
  })

  it('lỗi mạng trần (không có detail) vẫn hiện được thông điệp, không im lặng', async () => {
    mocks.fetch.mockRejectedValue(new Error('Network request failed'))
    const wrapper = await mountComment()
    wrapper.get('[data-comment-action="delete"]').trigger('click')
    await answerConfirm(true)

    expect(mocks.showToast).toHaveBeenCalledTimes(1)
    expect(mocks.showToast.mock.calls[0]![1]).toBe('error')
    expect(wrapper.emitted('deleted')).toBeUndefined()
  })

  it('401 khi xoá đi luồng hết-phiên', async () => {
    mocks.fetch.mockRejectedValue(httpError(401))
    const wrapper = await mountComment()
    wrapper.get('[data-comment-action="delete"]').trigger('click')
    await answerConfirm(true)

    expect(mocks.handleSessionExpired).toHaveBeenCalledTimes(1)
    expect(wrapper.emitted('deleted')).toBeUndefined()
  })
})

// ── (e) Nối vào trang bài viết — cả bình luận gốc lẫn trả lời ────────────────

describe('(e) trang bài viết nối đủ hai nhánh', () => {
  const post = {
    id: 'p1', user_id: 'tac-gia-bai', display_name: 'Người đăng',
    content: 'Ghé chợ Vĩnh Long sáng nay', created_at: isoAgo(3), comments_count: 2,
  }

  function commentsPayload() {
    return {
      comments: [{
        id: 'c1', post_id: 'p1', user_id: 'me', content: 'Bình luận gốc của tôi',
        created_at: isoAgo(1), author: { id: 'me', display_name: 'Tôi' },
        replies: [{
          id: 'c2', post_id: 'p1', user_id: 'me', parent_id: 'c1',
          content: 'Trả lời của tôi', created_at: isoAgo(1),
          author: { id: 'me', display_name: 'Tôi' },
        }],
      }],
    }
  }

  function routeFetch(url: string) {
    if (url.includes('/comments')) return Promise.resolve(commentsPayload())
    if (url.includes('/related')) return Promise.resolve({ posts: [] })
    if (url.includes('/api/posts/p1')) return Promise.resolve({ post })
    return Promise.resolve({})
  }

  async function mountPage() {
    mocks.fetch.mockImplementation((url: string) => routeFetch(url))
    const wrapper = await mountSuspended(PostDetailPage, {
      route: '/bai-viet/p1',
      global: {
        stubs: {
          Breadcrumb: true, PostCard: true, SkeletonList: true,
          EmptyState: true, ReportModal: true, LazyReportModal: true,
        },
      },
    })
    wrappers.push(wrapper)
    await flushPromises()
    return wrapper
  }

  it('bình luận gốc VÀ trả lời đều có nút Sửa/Xoá cho tác giả', async () => {
    const wrapper = await mountPage()
    expect(wrapper.findAll('[data-comment-action="edit"]')).toHaveLength(2)
    expect(wrapper.findAll('[data-comment-action="delete"]')).toHaveLength(2)
  })

  it('xoá xong thì tải lại danh sách và bình luận biến khỏi màn hình', async () => {
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('Bình luận gốc của tôi')

    // Sau khi xoá, backend soft-delete cả trả lời con → danh sách rỗng.
    mocks.fetch.mockImplementation((url: string) => {
      if (url.includes('/comments') && !url.startsWith('/api/comments/')) {
        return Promise.resolve({ comments: [] })
      }
      if (url.startsWith('/api/comments/')) return Promise.resolve({ success: true })
      return routeFetch(url)
    })

    wrapper.findAll('[data-comment-action="delete"]')[0]!.trigger('click')
    await answerConfirm(true)
    await flushPromises()

    expect(wrapper.text()).not.toContain('Bình luận gốc của tôi')
    expect(wrapper.text()).not.toContain('Trả lời của tôi')
  })
})
