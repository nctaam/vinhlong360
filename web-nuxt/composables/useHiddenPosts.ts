/**
 * useHiddenPosts — người dùng tự dọn bảng tin của mình.
 *
 * Nối 3 endpoint đã có sẵn ở backend nhưng frontend chưa từng gọi:
 *   POST /api/posts/{id}/hide     (agent/social.py:3355)
 *   POST /api/posts/{id}/unhide   (agent/social.py:3377)
 *   GET  /api/posts/hidden        (agent/social.py:3395)
 *
 * BẤT BIẾN — đọc kỹ trước khi mở rộng chỗ gọi:
 *
 *  1. ẨN LÀ RIÊNG TƯ, KHÔNG PHẢI KIỂM DUYỆT. Backend ghi vào
 *     `user_hidden_posts(user_id, post_id)` và chỉ lọc theo `user_id` của
 *     NGƯỜI ĐANG XEM. Bài vẫn hiện bình thường với mọi người khác. Không được
 *     đặt nhãn kiểu "gỡ bài" / "xoá bài" cho hành động này.
 *
 *  2. CHỈ 3 FEED HONOR BỘ LỌC NÀY. `user_hidden_posts` chỉ xuất hiện trong
 *     `_feed_build_conditions` (GET /api/feed), `get_following_feed`
 *     (GET /api/feed/following) và `get_friend_reviews`. Các endpoint liệt kê
 *     bài KHÁC — `/api/me/bookmarks`, `/api/users/{id}/posts`,
 *     `/api/search/posts`, `/api/entities/{id}/feed` — KHÔNG lọc bài đã ẩn.
 *     Gắn nút "Ẩn" vào các màn đó = bài biến mất rồi quay lại sau khi tải lại
 *     trang, tức là nói dối người dùng. Muốn mở rộng thì sửa backend TRƯỚC.
 *
 *  3. LẠC QUAN CÓ HOÀN NGUYÊN. Bài rời danh sách ngay khi bấm, nhưng nếu API
 *     lỗi thì phải quay về ĐÚNG vị trí cũ và báo lỗi thấy được — đây là thao
 *     tác dữ liệu, không phải beacon đo đạc (beacon nuốt lỗi mới là đúng).
 *
 *  4. KHÔNG hộp thoại xác nhận khi ẩn. Ẩn là hành động ĐẢO NGƯỢC ĐƯỢC (có
 *     unhide + trang "Bài đã ẩn" trong Cài đặt) và caller phải kèm lối hoàn
 *     tác ngay tại chỗ. Chèn confirm vào đây sẽ giết đúng cái giá trị của tính
 *     năng: người dùng tự lọc nhanh → admin đỡ phải xử lý.
 */

/** Chỉ cần `id` — dùng chung cho Post của feed lẫn item trong danh sách đã ẩn. */
export interface HideablePost {
  id: string
  [key: string]: unknown
}

export interface HiddenPostsPage {
  posts: HideablePost[]
  total: number
  page: number
  has_more: boolean
}

/**
 * Thông điệp lỗi cho người dùng: ưu tiên `detail` do backend trả (ví dụ 429
 * "Thao tác quá nhanh. Vui lòng thử lại sau." — người dùng cần biết để chờ),
 * nhưng KHÔNG bao giờ rơi xuống `err.message` của ofetch
 * (`[POST] "/api/...": 500 Internal Server Error`) — đó là chuỗi dành cho dev.
 */
function apiMessage(e: unknown, fallback: string): string {
  const err = e as {
    response?: { _data?: { detail?: string; message?: string } }
    data?: { detail?: string; message?: string }
  }
  const detail = err?.response?._data?.detail || err?.response?._data?.message
    || err?.data?.detail || err?.data?.message
  return typeof detail === 'string' && detail.trim() ? detail : fallback
}

/** Gỡ bài khỏi mọi danh sách đang giữ nó; trả về hàm đặt lại đúng chỗ cũ. */
export function removePostFromLists(
  postId: string,
  lists: Array<Ref<HideablePost[]>>,
): () => void {
  const removals: Array<{ list: Ref<HideablePost[]>; index: number; post: HideablePost }> = []
  for (const list of lists) {
    // Lặp ngược: cùng một bài có thể nằm 2 lần trong 1 mảng (feed + merge trang sau).
    for (let i = list.value.length - 1; i >= 0; i--) {
      if (list.value[i]?.id !== postId) continue
      const [post] = list.value.splice(i, 1)
      if (post) removals.push({ list, index: i, post })
    }
  }
  return () => {
    // Chèn lại theo thứ tự index tăng dần để index cũ vẫn đúng sau mỗi lần chèn.
    for (const { list, index, post } of [...removals].reverse()) {
      list.value.splice(Math.min(index, list.value.length), 0, post)
    }
  }
}

export function useHiddenPosts() {
  const { authHeaders, handleSessionExpired, isLoggedIn } = useAuth()
  const { show: showToast } = useToast()
  const pending = reactive(new Set<string>())

  function isPending(postId: string) {
    return pending.has(postId)
  }

  /**
   * Ẩn một bài khỏi bảng tin của chính người đang đăng nhập.
   *
   * Trả `true` nếu backend đã ghi nhận. Trả `false` (kèm toast) khi chưa đăng
   * nhập, id rỗng, đang có request cho đúng bài đó, hoặc API lỗi — mọi nhánh
   * `false` đều đã hoàn nguyên danh sách về trạng thái trước khi bấm.
   */
  async function hidePost(
    postId: string,
    lists: Array<Ref<HideablePost[]>>,
  ): Promise<boolean> {
    if (!isLoggedIn.value) {
      showToast('Đăng nhập để ẩn bài viết khỏi bảng tin của bạn', 'info')
      return false
    }
    const encodedPostId = encodePathId(postId)
    if (!encodedPostId) return false
    if (pending.has(postId)) return false
    pending.add(postId)

    const restore = removePostFromLists(postId, lists)
    try {
      await $fetch(`/api/posts/${encodedPostId}/hide`, { method: 'POST', headers: authHeaders() })
      return true
    } catch (e: unknown) {
      restore()
      if (getStatusCode(e) === 401) { handleSessionExpired(); return false }
      showToast(apiMessage(e, 'Không thể ẩn bài viết'), 'error')
      return false
    } finally {
      pending.delete(postId)
    }
  }

  /**
   * Bỏ ẩn — bài quay lại bảng tin ở lần tải kế tiếp.
   *
   * `lists` là các danh sách "bài đã ẩn" cần gỡ item ra (lạc quan, hoàn nguyên
   * khi lỗi). Gọi không kèm list cũng hợp lệ (nút "Hoàn tác" ngay sau khi ẩn).
   */
  async function unhidePost(
    postId: string,
    lists: Array<Ref<HideablePost[]>> = [],
  ): Promise<boolean> {
    if (!isLoggedIn.value) {
      showToast('Đăng nhập để quản lý bài đã ẩn', 'info')
      return false
    }
    const encodedPostId = encodePathId(postId)
    if (!encodedPostId) return false
    if (pending.has(postId)) return false
    pending.add(postId)

    const restore = removePostFromLists(postId, lists)
    try {
      await $fetch(`/api/posts/${encodedPostId}/unhide`, { method: 'POST', headers: authHeaders() })
      return true
    } catch (e: unknown) {
      restore()
      if (getStatusCode(e) === 401) { handleSessionExpired(); return false }
      showToast(apiMessage(e, 'Không thể bỏ ẩn bài viết'), 'error')
      return false
    } finally {
      pending.delete(postId)
    }
  }

  /**
   * Danh sách bài đã ẩn (mới ẩn trước). Ném lỗi lên cho caller tự hiển thị —
   * composable không tự quyết chỗ đặt thông báo cho một màn danh sách.
   */
  async function fetchHiddenPosts(page = 1, limit = 20): Promise<HiddenPostsPage> {
    const params = new URLSearchParams({ page: String(page), limit: String(limit) })
    const res = await $fetch<Partial<HiddenPostsPage>>(`/api/posts/hidden?${params}`, {
      headers: authHeaders(),
    })
    return {
      posts: Array.isArray(res?.posts) ? res.posts : [],
      total: Number(res?.total) || 0,
      page: Number(res?.page) || page,
      has_more: !!res?.has_more,
    }
  }

  return { hidePost, unhidePost, fetchHiddenPosts, isPending }
}
