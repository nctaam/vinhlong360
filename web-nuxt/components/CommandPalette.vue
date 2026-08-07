<template>
  <Transition name="cmd-fade">
  <div v-if="open" class="cmd-overlay" @click.self="open = false">
    <div ref="paletteRef" class="cmd-palette" role="dialog" aria-modal="true" aria-label="Tìm nhanh">
      <input
        ref="inputEl"
        v-model="query"
        class="cmd-input"
        enterkeyhint="search"
        placeholder="Tìm trang, entity, thao tác…"
        aria-label="Tìm trang, entity, thao tác"
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
          <span class="cmd-icon-chip" aria-hidden="true">
            <span class="cmd-icon"><IconLine :name="item.icon" /></span>
          </span>
          <span class="cmd-label">{{ item.label }}</span>
          <span class="cmd-hint">{{ item.hint }}</span>
        </button>
        <div v-if="!results.length && query" class="cmd-empty">
          <span class="cmd-empty-query">Không tìm thấy "{{ query }}"</span>
          <span class="cmd-empty-hint">Thử: {{ emptySuggestions }}…</span>
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
import { resolveAdminScopes } from '~/utils/adminAccess'
import {
  ADMIN_NAV_GROUPS,
  filterAdminNavGroups,
  type AdminNavItem,
} from '~/utils/adminNavigation'

interface PaletteItem {
  icon: string
  label: string
  to: string
  hint: string
  search: string
}

const open = ref(false)
const query = ref('')
const active = ref(0)
const inputEl = ref<HTMLInputElement>()
const paletteRef = ref<HTMLElement | null>(null)
const { user } = useAuth()
useModalA11y(open, paletteRef, { onClose: () => { open.value = false } })

function removeDiacritics(s: string): string {
  return s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D')
}

function targetToUrl(target: AdminNavItem['to']): string {
  if (typeof target === 'string') return target
  const queryString = new URLSearchParams(target.query || {}).toString()
  return queryString ? `${target.path}?${queryString}` : target.path
}

function toPaletteItem(item: AdminNavItem, hint: string): PaletteItem {
  return {
    icon: item.icon,
    label: item.label,
    to: targetToUrl(item.to),
    hint,
    search: removeDiacritics(`${item.label} ${hint}`).toLowerCase(),
  }
}

const pages = computed<PaletteItem[]>(() => {
  const scopes = resolveAdminScopes(user.value)
  const adminItems = filterAdminNavGroups(ADMIN_NAV_GROUPS, scopes).flatMap(group => (
    group.items.flatMap(item => [
      toPaletteItem(item, group.label),
      ...(item.children || []).map(child => toPaletteItem(child, item.label)),
    ])
  ))

  return [
    ...adminItems,
    toPaletteItem({ id: 'public-home', label: 'Về trang chủ', to: '/', icon: 'home' }, 'Trang công khai'),
  ]
})

const results = computed(() => {
  if (!query.value) return pages.value
  const q = removeDiacritics(query.value).toLowerCase()
  return pages.value.filter(p => p.search.includes(q))
})
const emptySuggestions = computed(() => pages.value.slice(0, 4).map(page => page.label).join(', '))

watch(query, () => { active.value = 0 })

watch(active, () => {
  const items = paletteRef.value?.querySelectorAll('.cmd-item')
  items?.[active.value]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
})

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
.cmd-overlay { position: fixed; inset: 0; z-index: var(--z-lightbox); background: rgba(var(--black-rgb),.4); display: flex; align-items: flex-start; justify-content: center; padding-top: 15vh; }
.cmd-palette {
  width: min(540px, 90vw);
  background: var(--bg, var(--white));
  border: .5px solid var(--line);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(var(--black-rgb),.2);
  overflow: hidden;
}
.cmd-input { width: 100%; padding: 14px var(--space-5); border: none; outline: none; font-size: 1rem; background: transparent; color: var(--ink); }
.cmd-input:focus-visible { outline: 2px solid var(--primary); outline-offset: -2px; }
.cmd-input::placeholder { color: var(--muted); }
.cmd-results { max-height: 360px; overflow-y: auto; border-top: .5px solid var(--line); }
.cmd-item {
  position: relative;
  display: flex; align-items: center; gap: 10px; width: 100%; padding: 10px var(--space-5); border: none; background: none; cursor: pointer; text-align: left; font: inherit; color: var(--ink); transition: background .15s var(--ease-out);
}
/* Active row: tri-province hairline accent instead of a flat colour wash — museum-label
   register consistent with the Story Card rule, not an app-selection tint. */
.cmd-item.active { background: rgba(var(--blue-rgb),.06); }
.cmd-item.active::before {
  content: ""; position: absolute; left: 0; top: 8px; bottom: 8px; width: 2px; border-radius: 2px;
  background: linear-gradient(180deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .cmd-item.active::before { background: linear-gradient(180deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }
.cmd-item:focus-visible { outline: 2px solid var(--primary); outline-offset: -2px; }
.cmd-icon-chip {
  flex-shrink: 0; width: 26px; height: 26px; border-radius: var(--radius-full, 999px);
  display: flex; align-items: center; justify-content: center;
  background: var(--surface-container, rgba(var(--black-rgb),.04));
}
.dark .cmd-icon-chip { background: rgba(var(--white-rgb),.06); }
.cmd-icon { font-size: .95rem; line-height: 1; }
.cmd-label { font-weight: 500; flex: 1; }
.cmd-hint { font-size: .72rem; text-transform: uppercase; letter-spacing: var(--tracking-caps, .06em); color: var(--muted); }
.cmd-empty { padding: var(--space-5); text-align: center; color: var(--muted); font-size: .9rem; display: flex; flex-direction: column; gap: 6px; }
.cmd-empty-query { font-family: var(--font-editorial); }
.cmd-empty-hint { font-size: .75rem; opacity: .6; }
.cmd-footer { padding: var(--space-2) var(--space-5); border-top: .5px solid var(--line); font-size: .8rem; color: var(--muted); }
.cmd-footer kbd { background: rgba(var(--black-rgb),.06); padding: 2px 6px; border-radius: 4px; font-family: inherit; font-size: .75rem; }
.dark .cmd-footer kbd { background: rgba(var(--white-rgb),.08); }
.cmd-fade-enter-active, .cmd-fade-leave-active { transition: opacity .15s; }
.cmd-fade-enter-from, .cmd-fade-leave-to { opacity: 0; }
/* dark overrides for .cmd-palette in dark-overrides.css */
@media (max-width: 600px) {
  .cmd-overlay { padding-top: 0; align-items: flex-end; }
  .cmd-palette { width: 100%; border-radius: 16px 16px 0 0; max-height: 85vh; }
  .cmd-results { max-height: 50vh; }
  .cmd-footer { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .cmd-item { transition: none; }
  .cmd-fade-enter-active, .cmd-fade-leave-active { transition: none; }
}
@media (forced-colors: active) {
  .cmd-palette { border: 2px solid CanvasText; background: Canvas; }
  .cmd-input { border-bottom: 1px solid CanvasText; }
  .cmd-item.active { border-left: 3px solid Highlight; }
  .cmd-footer kbd { border: 1px solid GrayText; background: Canvas; }
}
</style>
