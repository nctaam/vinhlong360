<template>
  <div>
    <div class="admin-head-row">
      <div>
        <NuxtLink to="/admin/cai-dat" class="cs-back">← Cài đặt</NuxtLink>
        <h1>Điều hướng</h1>
        <p class="cs-subtitle">Thêm, xoá, sắp xếp menu điều hướng chính</p>
      </div>
    </div>

    <div v-if="loading" class="cs-skeleton">
      <div class="cs-skel-item" v-for="n in 4" :key="n"></div>
    </div>
    <Transition name="cs-fade">
      <div v-if="!loading" class="cs-form-wrap">
        <p class="cs-hint">Bấm ✎ để sửa tên nhóm và các mục con. Dùng ▲▼ để sắp xếp.</p>

        <AdminSortableList
          :items="navGroups"
          label-field="label"
          :editable-fields="['label', 'to']"
          add-label="Thêm nhóm menu"
          :new-item-template="{ label: 'Nhóm mới', children: [{ label: 'Mục mới', to: '/' }] }"
          @update:items="navGroups = $event"
        />

        <div class="cs-save-row">
          <button type="button" class="btn-primary sf-save" :disabled="saving" @click="onSave">
            {{ saving ? 'Đang lưu...' : 'Lưu điều hướng' }}
          </button>
          <button type="button" class="btn-outline sf-reset" :disabled="saving" @click="onReset">
            Đặt lại mặc định
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'admin', middleware: 'admin' })
useHead({ title: 'Điều hướng — Admin' })
const { authHeaders } = useAuth()
const { show: showToast } = useToast()
const { confirmDialog } = useConfirm()

const navGroups = ref<any[]>([])
const loading = ref(true)
const saving = ref(false)

async function reload() {
  loading.value = true
  try {
    const r = await $fetch<any>('/admin-api/site-settings/navigation', { headers: authHeaders() })
    const setting = (r.settings || []).find((s: any) => s.key === 'navigation.nav_groups')
    navGroups.value = setting?.value || []
  } catch { showToast('Không thể tải cài đặt', 'error') }
  loading.value = false
}

function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); if (!saving.value) onSave() }
}
onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))

async function onSave() {
  if (saving.value) return
  saving.value = true
  try {
    await $fetch('/admin-api/site-settings/navigation.nav_groups', {
      method: 'PUT',
      headers: authHeaders(),
      body: { value: navGroups.value },
    })
    showToast('Đã lưu điều hướng', 'success')
  } catch (e: unknown) { showToast(extractErrorMessage(e, 'Lỗi khi lưu'), 'error') }
  saving.value = false
}

async function onReset() {
  if (saving.value) return
  if (!await confirmDialog('Đặt lại menu điều hướng về mặc định?', { danger: true })) return
  saving.value = true
  try {
    await $fetch('/admin-api/site-settings/reset/navigation', { method: 'POST', headers: authHeaders() })
    showToast('Đã đặt lại', 'success')
    await reload()
  } catch (e: unknown) { showToast(extractErrorMessage(e, 'Lỗi'), 'error') }
  saving.value = false
}

onMounted(reload)
</script>

<style scoped>
.cs-back { font-size: .82rem; color: var(--muted); text-decoration: none; transition: color .15s; }
.cs-back:hover { color: var(--primary, #219653); }
.cs-subtitle { font-size: .82rem; color: var(--muted); margin-top: 4px; }
.cs-form-wrap { max-width: 640px; }
.cs-hint { font-size: .82rem; color: var(--muted); margin-bottom: var(--space-4); line-height: 1.4; }

/* ── Skeleton ── */
.cs-skeleton { max-width: 640px; display: flex; flex-direction: column; gap: 2px; }
.cs-skel-item { height: 58px; border-radius: 12px; background: var(--line); opacity: .4; animation: cs-pulse 1.5s ease-in-out infinite; }
.cs-skel-item:nth-child(2) { animation-delay: .1s; }
.cs-skel-item:nth-child(3) { animation-delay: .2s; }
.cs-skel-item:nth-child(4) { animation-delay: .3s; }
@keyframes cs-pulse { 0%, 100% { opacity: .3; } 50% { opacity: .6; } }

/* ── Fade transition ── */
.cs-fade-enter-active { transition: opacity .3s cubic-bezier(.2,1,.4,1), transform .3s cubic-bezier(.2,1,.4,1); }
.cs-fade-enter-from { opacity: 0; transform: translateY(6px); }

.cs-save-row {
  display: flex; gap: var(--space-3); padding-top: var(--space-5);
  margin-top: var(--space-4); border-top: .5px solid var(--line);
}
.sf-save {
  padding: 12px 28px; border-radius: 12px; font-weight: 600; font-size: .88rem;
  background: var(--primary, #219653); color: var(--on-primary); border: none; cursor: pointer;
  min-height: 44px;
  transition: transform .2s cubic-bezier(.2,1,.4,1), box-shadow .2s;
}
.sf-save:hover:not(:disabled) { transform: scale(1.02); box-shadow: 0 4px 12px rgba(var(--primary-rgb),.2); }
.sf-save:active:not(:disabled) { transform: scale(.97); }
.sf-save:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }
.sf-save:disabled { opacity: var(--opacity-disabled); cursor: not-allowed; }
.sf-reset {
  padding: 12px 20px; border-radius: 12px; font-size: .85rem; font-weight: 500;
  background: transparent; border: .5px solid var(--line); color: var(--muted); cursor: pointer;
  min-height: 44px;
  transition: border-color .2s, color .2s, transform .15s cubic-bezier(.2,1,.4,1);
}
.sf-reset:hover:not(:disabled) { border-color: var(--error); color: var(--error); }
.sf-reset:active:not(:disabled) { transform: scale(.97); }
.sf-reset:focus-visible { outline: 2px solid var(--error); outline-offset: 2px; }

@media (prefers-reduced-motion: reduce) {
  .cs-skel-item { animation: none; }
  .cs-fade-enter-active { transition: none; }
  .sf-save:hover:not(:disabled), .sf-save:active:not(:disabled),
  .sf-reset:active:not(:disabled) { transform: none; }
}
</style>
