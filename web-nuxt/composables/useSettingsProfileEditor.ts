import { ref, computed, type Ref } from 'vue'
import { getStatusCode, extractErrorMessage } from '~/composables/useFetchError'

export const ALLOWED_PROFILE_IMG = ['image/jpeg', 'image/png', 'image/webp']
export const MAX_PROFILE_IMG_SIZE = 12 * 1024 * 1024

export interface UseSettingsProfileEditorOptions {
  user?: Ref<any>
  authHeaders?: () => Record<string, string>
  fetchMe?: () => Promise<unknown>
  handleSessionExpired?: () => void
  showToast?: (message: string, type?: 'info' | 'success' | 'warning' | 'error') => void
}

export function useSettingsProfileEditor(options: UseSettingsProfileEditorOptions = {}) {
  const user = options.user
  const authHeaders = options.authHeaders ?? (() => ({}))
  const fetchMe = options.fetchMe ?? (() => Promise.resolve())
  const handleSessionExpired = options.handleSessionExpired ?? (() => {})
  const showToast = options.showToast ?? (() => {})

  const displayName = ref(user?.value?.display_name || '')
  const fullName = ref(user?.value?.full_name || '')
  const bio = ref('')
  const email = ref(user?.value?.email || '')
  const contactInfo = ref(user?.value?.contact_info || '')

  const savedName = ref(displayName.value)
  const savedFullName = ref(fullName.value)
  const savedBio = ref('')
  const savedEmail = ref(email.value)
  const savedContactInfo = ref(contactInfo.value)

  const saving = ref(false)
  const nameError = ref('')

  const uploadingAvatar = ref(false)
  const avatarPreview = ref('')
  const avatarBroken = ref(false)

  const uploadingCover = ref(false)
  const coverPreview = ref('')

  async function onAvatarChange(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return
    if (!ALLOWED_PROFILE_IMG.includes(file.type)) {
      showToast('Chỉ hỗ trợ JPEG, PNG hoặc WebP', 'error')
      return
    }
    if (file.size > MAX_PROFILE_IMG_SIZE) {
      showToast('Ảnh quá lớn (tối đa 12MB)', 'error')
      return
    }
    if (avatarPreview.value?.startsWith('blob:')) {
      URL.revokeObjectURL(avatarPreview.value)
    }
    avatarPreview.value = URL.createObjectURL(file)
    avatarBroken.value = false
    uploadingAvatar.value = true
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await $fetch<{ avatar_url: string }>('/auth/avatar', {
        method: 'POST',
        headers: authHeaders(),
        body: form,
      })
      if (res.avatar_url) {
        await fetchMe()
        showToast('Đã cập nhật ảnh đại diện', 'success')
      }
    } catch (err: unknown) {
      avatarPreview.value = ''
      if (getStatusCode(err) === 401) {
        handleSessionExpired()
        return
      }
      showToast(extractErrorMessage(err, 'Không thể tải ảnh lên'), 'error')
    } finally {
      uploadingAvatar.value = false
    }
  }

  async function onCoverChange(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return
    if (!ALLOWED_PROFILE_IMG.includes(file.type)) {
      showToast('Chỉ hỗ trợ JPEG, PNG hoặc WebP', 'error')
      return
    }
    if (file.size > MAX_PROFILE_IMG_SIZE) {
      showToast('Ảnh quá lớn (tối đa 12MB)', 'error')
      return
    }
    if (coverPreview.value?.startsWith('blob:')) {
      URL.revokeObjectURL(coverPreview.value)
    }
    coverPreview.value = URL.createObjectURL(file)
    uploadingCover.value = true
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await $fetch<{ cover_url: string }>('/auth/cover', {
        method: 'POST',
        headers: authHeaders(),
        body: form,
      })
      if (res.cover_url) {
        await fetchMe()
        showToast('Đã cập nhật ảnh bìa', 'success')
      }
    } catch (err: unknown) {
      coverPreview.value = ''
      if (getStatusCode(err) === 401) {
        handleSessionExpired()
        return
      }
      showToast(extractErrorMessage(err, 'Không thể tải ảnh bìa lên'), 'error')
    } finally {
      uploadingCover.value = false
    }
  }

  async function save() {
    nameError.value = ''
    const name = displayName.value.trim()
    if (name.length < 2) {
      nameError.value = 'Tên hiển thị phải từ 2 ký tự trở lên'
      return
    }
    saving.value = true
    try {
      const body: Record<string, any> = {
        display_name: name,
        full_name: fullName.value.trim() || null,
        bio: bio.value.trim(),
        email: email.value.trim() || null,
        contact_info: contactInfo.value.trim() || null,
      }
      await $fetch('/auth/profile', {
        method: 'PUT',
        headers: authHeaders(),
        body,
      })
      await fetchMe()
      savedName.value = displayName.value
      savedFullName.value = fullName.value
      savedBio.value = bio.value
      savedEmail.value = email.value
      savedContactInfo.value = contactInfo.value
      showToast('Đã lưu hồ sơ', 'success')
    } catch (e: unknown) {
      if (getStatusCode(e) === 401) {
        handleSessionExpired()
        return
      }
      showToast(extractErrorMessage(e, 'Không thể lưu hồ sơ'), 'error')
    } finally {
      saving.value = false
    }
  }

  const isDirty = computed(() =>
    displayName.value !== savedName.value ||
    bio.value !== savedBio.value ||
    fullName.value !== savedFullName.value ||
    email.value !== savedEmail.value ||
    contactInfo.value !== savedContactInfo.value
  )

  async function loadProfile(userId?: string) {
    const id = userId || user?.value?.id
    if (!id) return
    try {
      const res = await $fetch<Record<string, any>>(`/api/users/${id}`, { headers: authHeaders() })
      const u = res?.user ?? res
      if (u?.bio) { bio.value = u.bio; savedBio.value = u.bio }
      if (!displayName.value && u?.display_name) { displayName.value = u.display_name; savedName.value = u.display_name }
      if (u?.full_name) { fullName.value = u.full_name; savedFullName.value = u.full_name }
      if (u?.email) { email.value = u.email; savedEmail.value = u.email }
      if (u?.contact_info) { contactInfo.value = u.contact_info; savedContactInfo.value = u.contact_info }
    } catch {
      /* prefill is best-effort */
    }
  }

  function cleanupImagePreviews() {
    if (typeof URL !== 'undefined' && typeof URL.revokeObjectURL === 'function') {
      if (avatarPreview.value?.startsWith('blob:')) URL.revokeObjectURL(avatarPreview.value)
      if (coverPreview.value?.startsWith('blob:')) URL.revokeObjectURL(coverPreview.value)
    }
  }

  return {
    displayName,
    fullName,
    bio,
    email,
    contactInfo,
    savedName,
    savedFullName,
    savedBio,
    savedEmail,
    savedContactInfo,
    saving,
    nameError,
    isDirty,
    uploadingAvatar,
    avatarPreview,
    avatarBroken,
    onAvatarChange,
    uploadingCover,
    coverPreview,
    onCoverChange,
    save,
    loadProfile,
    cleanupImagePreviews,
  }
}
