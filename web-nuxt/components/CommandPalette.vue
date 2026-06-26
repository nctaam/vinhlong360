<template>
  <Transition name="cmd-fade">
  <div v-if="open" class="cmd-overlay" @click.self="open = false">
    <div ref="paletteRef" class="cmd-palette" role="dialog" aria-modal="true" aria-label="Tìm nhanh">
      <input
        ref="inputEl"
        v-model="query"
        class="cmd-input"
        placeholder="Tìm trang, entity, thao tác…"
        @keydown.escape="open = false"
        @keydown.down.prevent="move(1)"
        @keydown.up.prevent="move(-1)"
        @keydown.enter.prevent="go"
      />
      <div class="cmd-results">
        <button
          v-for="(item, i) in results"
          :key="item.to"
          type="button"
          :class="['cmd-item', { active: i === active }]"
          @click="navigate(item)"
          @mouseenter="active = i"
        >
          <span class="cmd-icon">{{ item.icon }}</span>
          <span class="cmd-label">{{ item.label }}</span>
          <span class="cmd-hint">{{ item.hint }}</span>
        </button>
        <div v-if="!results.length && query" class="cmd-empty">
          <span>Không tìm thấy "{{ query }}"</span>
          <span class="cmd-empty-hint">Thử: Entities, Kiểm duyệt, Users, Báo cáo…</span>
        </div>
      </div>
      <div class="cmd-footer">
        <kbd>↑↓</kbd> di chuyển <kbd>Enter</kbd> chọn <kbd>Esc</kbd> đóng
      </div>
    </div>
  </div>
  </Transition>
</template>

<script setup lang="ts">
const open = ref(false)
const query = ref('')
const active = ref(0)
const inputEl = ref<HTMLInputElement>()
const paletteRef = ref<HTMLElement | null>(null)
useModalA11y(open, paletteRef, { onClose: () => { open.value = false } })

const PAGES = [
  { icon: '📊', label: 'Dashboard', to: '/admin', hint: 'Tổng quan' },
  { icon: '📈', label: 'Thống kê', to: '/admin/thong-ke', hint: 'Analytics' },
  { icon: '📋', label: 'Entities', to: '/admin/entities', hint: 'Quản lý nội dung' },
  { icon: '📍', label: 'Chưa phân loại', to: '/admin/chua-phan-loai', hint: 'Entity chưa gắn xã' },
  { icon: '🏛', label: 'Danh bạ HC', to: '/admin/danh-ba', hint: 'Hành chính' },
  { icon: '🗺', label: 'Lịch trình', to: '/admin/lich-trinh', hint: 'Tuyến đường' },
  { icon: '🔍', label: 'Chất lượng DL', to: '/admin/data-quality', hint: 'Data quality' },
  { icon: '🛡', label: 'Kiểm duyệt', to: '/admin/kiem-duyet', hint: 'Moderation' },
  { icon: '📷', label: 'Duyệt ảnh', to: '/admin/duyet-anh', hint: 'Image review' },
  { icon: '👥', label: 'Users', to: '/admin/users', hint: 'Quản lý tài khoản' },
  { icon: '🚩', label: 'Báo cáo', to: '/admin/bao-cao', hint: 'Reports' },
  { icon: '🧪', label: 'Duyệt & Tools', to: '/admin/duyet-tu-hoc', hint: 'KB curation' },
  { icon: '🤖', label: 'Knowledge Agent', to: '/admin/ai', hint: 'AI chat' },
  { icon: '⚙', label: 'Cài đặt', to: '/admin/cai-dat', hint: 'Site settings' },
  { icon: '🏠', label: 'Về trang chủ', to: '/', hint: 'Public site' },
]

const results = computed(() => {
  if (!query.value) return PAGES
  const q = query.value.toLowerCase()
  return PAGES.filter(p => p.label.toLowerCase().includes(q) || p.hint.toLowerCase().includes(q))
})

watch(query, () => { active.value = 0 })

function move(d: number) {
  active.value = Math.max(0, Math.min(results.value.length - 1, active.value + d))
}

function go() {
  const item = results.value[active.value]
  if (item) navigate(item)
}

function navigate(item: { to: string }) {
  open.value = false
  query.value = ''
  navigateTo(item.to)
}

function onKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    open.value = !open.value
  }
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))

defineExpose({ open })
</script>

<style scoped>
.cmd-overlay { position: fixed; inset: 0; z-index: 9999; background: rgba(0,0,0,.4); display: flex; align-items: flex-start; justify-content: center; padding-top: 15vh; }
.cmd-palette { width: min(540px, 90vw); background: var(--bg, #fff); border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,.2); overflow: hidden; }
.cmd-input { width: 100%; padding: 14px 20px; border: none; outline: none; font-size: 1rem; background: transparent; color: var(--ink); }
.cmd-input::placeholder { color: var(--muted); }
.cmd-results { max-height: 360px; overflow-y: auto; border-top: .5px solid var(--line); }
.cmd-item { display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px 20px; border: none; background: none; cursor: pointer; text-align: left; font: inherit; color: var(--ink); }
.cmd-item.active { background: rgba(52,120,246,.08); }
.cmd-icon { font-size: 1.1rem; flex-shrink: 0; width: 24px; text-align: center; }
.cmd-label { font-weight: 500; flex: 1; }
.cmd-hint { font-size: .78rem; color: var(--muted); }
.cmd-empty { padding: 20px; text-align: center; color: var(--muted); font-size: .9rem; display: flex; flex-direction: column; gap: 6px; }
.cmd-empty-hint { font-size: .75rem; opacity: .6; }
.cmd-footer { padding: 8px 20px; border-top: .5px solid var(--line); font-size: .72rem; color: var(--muted); }
.cmd-footer kbd { background: rgba(0,0,0,.06); padding: 1px 5px; border-radius: 3px; font-family: inherit; }
.cmd-fade-enter-active, .cmd-fade-leave-active { transition: opacity .15s; }
.cmd-fade-enter-from, .cmd-fade-leave-to { opacity: 0; }
:global(.dark) .cmd-palette { background: var(--card, #2c2c2e); }
:global(.dark) .cmd-item.active { background: rgba(52,120,246,.15); }
:global(.dark) .cmd-footer kbd { background: rgba(255,255,255,.12); color: rgba(255,255,255,.7); }
@media (max-width: 600px) {
  .cmd-overlay { padding-top: 0; align-items: flex-end; }
  .cmd-palette { width: 100%; border-radius: 16px 16px 0 0; max-height: 85vh; }
  .cmd-results { max-height: 50vh; }
  .cmd-footer { display: none; }
}
@media (forced-colors: active) {
  .cmd-palette { border: 2px solid CanvasText; background: Canvas; }
  .cmd-input { border-bottom: 1px solid CanvasText; }
  .cmd-item.active { border-left: 3px solid Highlight; }
  .cmd-footer kbd { border: 1px solid GrayText; background: Canvas; }
}
</style>
