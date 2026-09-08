import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import {
  useSettingsProfileEditor,
  ALLOWED_PROFILE_IMG,
  MAX_PROFILE_IMG_SIZE,
} from '../composables/useSettingsProfileEditor'

describe('Moc 168: Settings Profile Editor Composable Architecture', () => {
  const fetchMock = vi.fn()
  const showToastMock = vi.fn()
  const fetchMeMock = vi.fn(() => Promise.resolve())
  const handleSessionExpiredMock = vi.fn()

  beforeEach(() => {
    fetchMock.mockReset()
    showToastMock.mockReset()
    fetchMeMock.mockReset()
    handleSessionExpiredMock.mockReset()
    vi.stubGlobal('$fetch', fetchMock)
  })

  it('declares valid image format restrictions and maximum upload size', () => {
    expect(ALLOWED_PROFILE_IMG).toContain('image/jpeg')
    expect(ALLOWED_PROFILE_IMG).toContain('image/png')
    expect(ALLOWED_PROFILE_IMG).toContain('image/webp')
    expect(MAX_PROFILE_IMG_SIZE).toBe(12 * 1024 * 1024)
  })

  it('initializes profile editor state from user object and tracks clean dirty state', () => {
    const user = ref({
      id: 'u1',
      display_name: 'Nguyễn Văn A',
      full_name: 'Nguyễn Văn An',
      email: 'an@example.com',
      contact_info: '0901234567',
    })

    const editor = useSettingsProfileEditor({ user })

    expect(editor.displayName.value).toBe('Nguyễn Văn A')
    expect(editor.fullName.value).toBe('Nguyễn Văn An')
    expect(editor.email.value).toBe('an@example.com')
    expect(editor.contactInfo.value).toBe('0901234567')
    expect(editor.isDirty.value).toBe(false)

    // Editing any field marks editor as dirty
    editor.bio.value = 'Chuyên gia ẩm thực Vĩnh Long'
    expect(editor.isDirty.value).toBe(true)

    editor.bio.value = ''
    expect(editor.isDirty.value).toBe(false)

    editor.displayName.value = 'Nguyễn Văn B'
    expect(editor.isDirty.value).toBe(true)
  })

  it('validates minimum display name length before saving', async () => {
    const user = ref({ id: 'u1', display_name: 'A' })
    const editor = useSettingsProfileEditor({
      user,
      showToast: showToastMock,
    })

    editor.displayName.value = 'A' // 1 char < 2
    await editor.save()

    expect(editor.nameError.value).toBe('Tên hiển thị phải từ 2 ký tự trở lên')
    expect(fetchMock).not.toHaveBeenCalled()

    editor.displayName.value = '   ' // empty after trim
    await editor.save()
    expect(editor.nameError.value).toBe('Tên hiển thị phải từ 2 ký tự trở lên')
  })

  it('successfully saves valid profile and synchronizes saved state', async () => {
    const user = ref({ id: 'u1', display_name: 'Lan Anh' })
    fetchMock.mockResolvedValueOnce({ success: true })

    const editor = useSettingsProfileEditor({
      user,
      fetchMe: fetchMeMock,
      showToast: showToastMock,
      authHeaders: () => ({ Authorization: 'Bearer token-1' }),
    })

    editor.displayName.value = 'Lan Anh 360'
    editor.bio.value = 'Khám phá Vĩnh Long'
    expect(editor.isDirty.value).toBe(true)

    await editor.save()

    expect(editor.nameError.value).toBe('')
    expect(fetchMock).toHaveBeenCalledWith('/auth/profile', expect.objectContaining({
      method: 'PUT',
      headers: { Authorization: 'Bearer token-1' },
      body: expect.objectContaining({
        display_name: 'Lan Anh 360',
        bio: 'Khám phá Vĩnh Long',
      }),
    }))
    expect(fetchMeMock).toHaveBeenCalled()
    expect(showToastMock).toHaveBeenCalledWith('Đã lưu hồ sơ', 'success')
    expect(editor.isDirty.value).toBe(false)
  })

  it('handles 401 session expiration gracefully during save', async () => {
    const error401 = Object.assign(new Error('Unauthorized'), { response: { status: 401 } })
    fetchMock.mockRejectedValueOnce(error401)

    const editor = useSettingsProfileEditor({
      user: ref({ id: 'u1', display_name: 'Test' }),
      handleSessionExpired: handleSessionExpiredMock,
      showToast: showToastMock,
    })

    editor.displayName.value = 'Test Modified'
    await editor.save()

    expect(handleSessionExpiredMock).toHaveBeenCalled()
    expect(showToastMock).not.toHaveBeenCalledWith('Đã lưu hồ sơ', 'success')
    expect(editor.saving.value).toBe(false)
  })

  it('rejects invalid image types and oversized files during avatar and cover change', async () => {
    const editor = useSettingsProfileEditor({ showToast: showToastMock })

    // Invalid MIME type
    const fakeGifEvent = {
      target: {
        files: [{ type: 'image/gif', size: 1024 }],
      },
    } as unknown as Event

    await editor.onAvatarChange(fakeGifEvent)
    expect(showToastMock).toHaveBeenCalledWith('Chỉ hỗ trợ JPEG, PNG hoặc WebP', 'error')

    showToastMock.mockClear()
    await editor.onCoverChange(fakeGifEvent)
    expect(showToastMock).toHaveBeenCalledWith('Chỉ hỗ trợ JPEG, PNG hoặc WebP', 'error')

    // Oversized file > 12MB
    showToastMock.mockClear()
    const fakeOversizedEvent = {
      target: {
        files: [{ type: 'image/jpeg', size: 13 * 1024 * 1024 }],
      },
    } as unknown as Event

    await editor.onAvatarChange(fakeOversizedEvent)
    expect(showToastMock).toHaveBeenCalledWith('Ảnh quá lớn (tối đa 12MB)', 'error')

    showToastMock.mockClear()
    await editor.onCoverChange(fakeOversizedEvent)
    expect(showToastMock).toHaveBeenCalledWith('Ảnh quá lớn (tối đa 12MB)', 'error')
  })

  it('cleans up image previews without throwing errors', () => {
    const editor = useSettingsProfileEditor()
    expect(() => editor.cleanupImagePreviews()).not.toThrow()
  })
})
