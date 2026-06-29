<template>
  <div>
    <div class="admin-head-row">
      <div>
        <NuxtLink to="/admin/cai-dat" class="cs-back">← Cài đặt</NuxtLink>
        <h1>Footer</h1>
        <p class="cs-subtitle">Cột footer, copyright, disclaimer</p>
      </div>
    </div>

    <div v-if="loading" class="cs-skeleton">
      <div class="cs-skel-row" v-for="n in 3" :key="n"><div class="cs-skel-label"></div><div class="cs-skel-input"></div></div>
      <div class="cs-skel-item" v-for="n in 3" :key="'c'+n"></div>
    </div>
    <Transition name="cs-fade">
      <div v-if="!loading" class="cs-form-wrap">
        <AdminSettingsForm :category="'footer'" :fields="textFields" @saved="reload" />

        <div class="cs-section" v-if="footerColumns.length || !loading">
          <h2 class="cs-section-title">Cột footer</h2>
          <p class="cs-hint">Mỗi cột có tiêu đề và danh sách liên kết. Bấm ✎ để sửa.</p>

          <AdminSortableList
            :items="footerColumns"
            label-field="title"
            :editable-fields="['title']"
            add-label="Thêm cột footer"
            :new-item-template="{ title: 'Cột mới', links: [{ label: 'Liên kết mới', to: '/' }] }"
            @update:items="footerColumns = $event"
          >
            <template #display="{ item }">
              <span class="sl-item-label">{{ item.title }}</span>
              <span class="sl-item-sub">{{ (item.links || []).length }} liên kết</span>
            </template>
          </AdminSortableList>

          <div class="cs-save-row">
            <button type="button" class="btn-primary sf-save" :disabled="saving" @click="saveColumns">
              {{ saving ? 'Đang lưu...' : 'Lưu cột footer' }}
            </button>
          </div>
        </div>

        <div class="cs-section">
          <h2 class="cs-section-title">Liên kết pháp lý (đáy trang)</h2>
          <p class="cs-hint">Hàng liên kết nhỏ ở đáy footer (Bảo mật, Điều khoản, Liên hệ…).</p>
          <AdminSortableList
            :items="legalLinks"
            label-field="label"
            :editable-fields="['label', 'to']"
            add-label="Thêm liên kết"
            :new-item-template="{ label: 'Liên kết mới', to: '/' }"
            @update:items="legalLinks = $event"
          >
            <template #display="{ item }">
              <span class="sl-item-label">{{ item.label }}</span>
              <span class="sl-item-sub">{{ item.to }}</span>
            </template>
          </AdminSortableList>
          <div class="cs-save-row">
            <button type="button" class="btn-primary sf-save" :disabled="saving" @click="saveLegalLinks">
              {{ saving ? 'Đang lưu...' : 'Lưu liên kết pháp lý' }}
            </button>
          </div>
        </div>

        <div class="cs-section">
          <h2 class="cs-section-title">Mạng xã hội</h2>
          <p class="cs-hint">Hiện ở footer dưới slogan. Mỗi liên kết có emoji + tên + URL. Để trống = không hiện.</p>
          <AdminSortableList
            :items="socialLinks"
            label-field="label"
            :editable-fields="['icon', 'label', 'url']"
            add-label="Thêm mạng xã hội"
            :new-item-template="{ icon: '🔗', label: 'Mạng xã hội', url: 'https://' }"
            @update:items="socialLinks = $event"
          >
            <template #display="{ item }">
              <span class="sl-item-label">{{ item.icon }} {{ item.label }}</span>
              <span class="sl-item-sub">{{ item.url }}</span>
            </template>
          </AdminSortableList>
          <div class="cs-save-row">
            <button type="button" class="btn-primary sf-save" :disabled="saving" @click="saveSocial">
              {{ saving ? 'Đang lưu...' : 'Lưu mạng xã hội' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Footer — Admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()

const textFields = ref<any[]>([])
const footerColumns = ref<any[]>([])
const legalLinks = ref<any[]>([])
const socialLinks = ref<any[]>([])
const loading = ref(true)
const saving = ref(false)

async function reload() {
  loading.value = true
  try {
    const r = await $fetch<any>('/admin-api/site-settings/footer', { headers: authHeaders() })
    const settings = r.settings || []
    textFields.value = settings.filter((s: any) => s.input_type !== 'json')
    footerColumns.value = settings.find((s: any) => s.key === 'footer.columns')?.value || []
    legalLinks.value = settings.find((s: any) => s.key === 'footer.legal_links')?.value || []
    socialLinks.value = settings.find((s: any) => s.key === 'social.links')?.value || []
  } catch { showToast('Không thể tải cài đặt', 'error') }
  loading.value = false
}

async function saveSocial() {
  saving.value = true
  try {
    await $fetch('/admin-api/site-settings/social.links', {
      method: 'PUT',
      headers: authHeaders(),
      body: { value: socialLinks.value },
    })
    showToast('Đã lưu mạng xã hội', 'success')
  } catch (e: unknown) { showToast(extractErrorMessage(e, 'Lỗi khi lưu'), 'error') }
  saving.value = false
}

async function saveLegalLinks() {
  saving.value = true
  try {
    await $fetch('/admin-api/site-settings/footer.legal_links', {
      method: 'PUT',
      headers: authHeaders(),
      body: { value: legalLinks.value },
    })
    showToast('Đã lưu liên kết pháp lý', 'success')
  } catch (e: unknown) { showToast(extractErrorMessage(e, 'Lỗi khi lưu'), 'error') }
  saving.value = false
}

async function saveColumns() {
  saving.value = true
  try {
    await $fetch('/admin-api/site-settings/footer.columns', {
      method: 'PUT',
      headers: authHeaders(),
      body: { value: footerColumns.value },
    })
    showToast('Đã lưu cột footer', 'success')
  } catch (e: unknown) { showToast(extractErrorMessage(e, 'Lỗi khi lưu'), 'error') }
  saving.value = false
}

onMounted(() => { reload(); window.addEventListener('keydown', onFooterKeydown) })
onUnmounted(() => window.removeEventListener('keydown', onFooterKeydown))

function onFooterKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    if (!saving.value) { saveColumns(); saveLegalLinks(); saveSocial() }
  }
}
</script>

<style scoped>
.cs-back { font-size: .82rem; color: var(--muted); text-decoration: none; transition: color .15s; }
.cs-back:hover { color: var(--primary, #219653); }
.cs-subtitle { font-size: .82rem; color: var(--muted); margin-top: var(--space-1); }
.cs-form-wrap { max-width: 640px; }
.cs-section { margin-top: var(--space-6); }
.cs-section-title { font-size: 1rem; font-weight: 600; margin-bottom: var(--space-3); }
.cs-hint { font-size: .82rem; color: var(--muted); margin-bottom: var(--space-4); line-height: 1.4; }
.sl-item-label { font-size: .88rem; font-weight: 500; }
.sl-item-sub { display: block; font-size: .75rem; color: var(--muted); margin-top: 2px; }

/* ── Skeleton ── */
.cs-skeleton { max-width: 640px; display: flex; flex-direction: column; gap: var(--space-5); }
.cs-skel-row { display: flex; flex-direction: column; gap: var(--space-2); }
.cs-skel-label { width: 120px; height: 14px; border-radius: 6px; background: var(--line); animation: cs-pulse 1.5s ease-in-out infinite; }
.cs-skel-input { width: 100%; height: 44px; border-radius: 10px; background: var(--line); opacity: .5; animation: cs-pulse 1.5s ease-in-out .15s infinite; }
.cs-skel-item { height: 58px; border-radius: 12px; background: var(--line); opacity: .35; animation: cs-pulse 1.5s ease-in-out .2s infinite; }
@keyframes cs-pulse { 0%, 100% { opacity: .3; } 50% { opacity: .6; } }

/* ── Fade transition ── */
.cs-fade-enter-active { transition: opacity .3s cubic-bezier(.2,1,.4,1), transform .3s cubic-bezier(.2,1,.4,1); }
.cs-fade-enter-from { opacity: 0; transform: translateY(6px); }

.cs-save-row {
  display: flex; gap: var(--space-3); padding-top: var(--space-5);
  margin-top: var(--space-4); border-top: .5px solid var(--line);
}
.sf-save {
  padding: var(--space-3) var(--space-7); border-radius: 12px; font-weight: 600; font-size: .88rem;
  background: var(--primary, #219653); color: var(--on-primary); border: none; cursor: pointer;
  min-height: 44px;
  transition: transform .2s cubic-bezier(.2,1,.4,1), box-shadow .2s;
}
.sf-save:hover:not(:disabled) { transform: scale(1.02); box-shadow: 0 4px 12px rgba(var(--primary-rgb),.2); }
.sf-save:active:not(:disabled) { transform: scale(.97); }
.sf-save:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.sf-save:disabled { opacity: var(--opacity-disabled); cursor: not-allowed; }

@media (prefers-reduced-motion: reduce) {
  .cs-skel-label, .cs-skel-input, .cs-skel-item { animation: none; }
  .cs-fade-enter-active { transition: none; }
  .sf-save:hover:not(:disabled), .sf-save:active:not(:disabled) { transform: none; }
}
</style>
