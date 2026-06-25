<template>
  <section class="page settings-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Cài đặt hồ sơ' }]" />

    <div v-if="!isLoggedIn" class="settings-guest card">
      <h1>Cài đặt hồ sơ</h1>
      <p>Bạn cần đăng nhập để chỉnh sửa hồ sơ.</p>
      <button type="button" class="btn btn-primary" @click="openAuth">Đăng nhập</button>
    </div>

    <div v-else class="settings-card card">
      <h1>Cài đặt hồ sơ</h1>
      <form class="settings-form" @submit.prevent="save">
        <div class="sf-avatar-section">
          <div class="sf-avatar-preview" @click="($refs.avatarInput as HTMLInputElement)?.click()">
            <img v-if="avatarPreview || user?.avatar_url" :src="avatarPreview || user?.avatar_url!" alt="Avatar" class="sf-avatar-img" />
            <AvatarPlaceholder v-else :initial="user?.display_name?.[0]?.toUpperCase()" />
            <span class="sf-avatar-overlay">📷</span>
          </div>
          <div class="sf-avatar-info">
            <span class="sf-label">Ảnh đại diện</span>
            <span class="sf-hint">JPEG, PNG hoặc WebP. Tối đa 12MB.</span>
            <button type="button" class="btn btn-ghost btn-sm" :disabled="uploadingAvatar" @click="($refs.avatarInput as HTMLInputElement)?.click()">
              {{ uploadingAvatar ? 'Đang tải...' : 'Đổi ảnh' }}
            </button>
          </div>
          <input ref="avatarInput" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="onAvatarChange" />
        </div>

        <label class="sf-field">
          <span class="sf-label">Tên hiển thị</span>
          <input
            v-model="displayName"
            type="text"
            class="sf-input"
            maxlength="50"
            required
            :aria-invalid="!!nameError"
            placeholder="Tên bạn muốn hiển thị"
          />
          <span v-if="nameError" class="sf-error" role="alert">{{ nameError }}</span>
        </label>

        <label class="sf-field">
          <span class="sf-label">Giới thiệu <span class="sf-hint">({{ bio.length }}/300)</span></span>
          <textarea
            v-model="bio"
            class="sf-input sf-textarea"
            maxlength="300"
            rows="4"
            placeholder="Đôi dòng về bạn (không bắt buộc)"
          ></textarea>
        </label>

        <div class="sf-actions">
          <button type="submit" class="btn btn-primary" :disabled="saving" :aria-busy="saving">
            <span v-if="!saving">Lưu thay đổi</span>
            <span v-else class="spinner spinner-sm" aria-label="Đang lưu"></span>
          </button>
          <NuxtLink v-if="user" :to="`/nguoi-dung/${user.id}`" class="btn btn-ghost">Xem hồ sơ</NuxtLink>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
const { user, isLoggedIn, authHeaders, fetchMe } = useAuth()
const { openAuth } = useAuthModal()
const { show: showToast } = useToast()

useHead({
  title: 'Cài đặt hồ sơ',
  meta: [{ name: 'robots', content: 'noindex,nofollow' }],
  link: [{ rel: 'canonical', href: canonicalUrl('/cai-dat') }],
})

const displayName = ref(user.value?.display_name || '')
const bio = ref('')
const saving = ref(false)
const nameError = ref('')
const uploadingAvatar = ref(false)
const avatarPreview = ref('')

async function onAvatarChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  avatarPreview.value = URL.createObjectURL(file)
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
  } catch (err: any) {
    avatarPreview.value = ''
    showToast(err?.data?.detail || 'Không thể tải ảnh lên', 'error')
  } finally {
    uploadingAvatar.value = false
  }
}

// Prefill bio from the public profile (User type doesn't carry bio).
onMounted(async () => {
  if (!user.value) return
  try {
    const res = await $fetch<Record<string, any>>(`/api/users/${user.value.id}`, { headers: authHeaders() })
    const u = res?.user ?? res
    if (u?.bio) bio.value = u.bio
    if (!displayName.value && u?.display_name) displayName.value = u.display_name
  } catch { /* prefill is best-effort */ }
})

async function save() {
  nameError.value = ''
  const name = displayName.value.trim()
  if (name.length < 2) {
    nameError.value = 'Tên hiển thị phải từ 2 ký tự trở lên'
    return
  }
  saving.value = true
  try {
    await $fetch('/auth/profile', {
      method: 'PUT',
      headers: authHeaders(),
      body: { display_name: name, bio: bio.value.trim() },
    })
    await fetchMe()
    showToast('Đã lưu hồ sơ', 'success')
  } catch (e: any) {
    showToast(e?.data?.detail || 'Không thể lưu hồ sơ', 'error')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.settings-page { max-width: 640px; margin: 0 auto; }
.settings-card, .settings-guest { padding: 1.5rem; }
.settings-card h1, .settings-guest h1 { margin: 0 0 1.25rem; font-size: 1.5rem; }
.settings-guest p { color: var(--ink-700); margin-bottom: 1rem; }
.settings-form { display: flex; flex-direction: column; gap: 1.25rem; }
.sf-field { display: flex; flex-direction: column; gap: .4rem; }
.sf-label { font-weight: 600; font-size: .95rem; }
.sf-hint { font-weight: 400; color: var(--ink-700); font-size: .85rem; }
.sf-input {
  width: 100%; padding: .65rem .8rem; border: 1px solid var(--border-input);
  border-radius: var(--radius-md); background: var(--bg); color: var(--ink-900);
  font: inherit;
}
.sf-input:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.sf-textarea { resize: vertical; min-height: 90px; }
.sf-error { color: var(--danger, #c0392b); font-size: .85rem; }
.sf-actions { display: flex; gap: .75rem; align-items: center; }
.sf-avatar-section { display: flex; align-items: center; gap: 1rem; }
.sf-avatar-preview {
  width: 80px; height: 80px; border-radius: 50%; overflow: hidden; cursor: pointer;
  position: relative; flex-shrink: 0; border: 2px solid var(--border-input);
}
.sf-avatar-preview:hover .sf-avatar-overlay { opacity: 1; }
.sf-avatar-img { width: 100%; height: 100%; object-fit: cover; }
.sf-avatar-overlay {
  position: absolute; inset: 0; background: rgba(0,0,0,.45); color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 1.5rem;
  opacity: 0; transition: opacity .2s;
}
.sf-avatar-info { display: flex; flex-direction: column; gap: .25rem; }
.sf-avatar-info .sf-hint { font-size: .8rem; }
.btn-sm { padding: .3rem .7rem; font-size: .85rem; }
</style>
