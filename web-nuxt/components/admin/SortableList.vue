<template>
  <div class="sl">
    <TransitionGroup name="sl-list" tag="div" class="sl-items">
      <div v-for="(item, i) in localItems" :key="itemKey(item, i)" class="sl-item" :class="{ 'sl-item-editing': editingIndex === i }">
        <div class="sl-item-head">
          <span class="sl-handle" aria-hidden="true">☰</span>
          <div class="sl-item-content">
            <template v-if="editingIndex === i">
              <div class="sl-edit-fields">
                <slot name="edit-fields" :item="item" :index="i" :update="(field: string, val: string) => updateField(i, field, val)">
                  <div v-for="field in editableFields" :key="field" class="sl-edit-group">
                    <label class="sl-edit-label">{{ field }}</label>
                    <input :value="item[field]" :placeholder="field"
                      class="sl-edit-input"
                      @input="updateField(i, field, ($event.target as HTMLInputElement).value)" />
                  </div>
                </slot>
              </div>
            </template>
            <template v-else>
              <slot name="display" :item="item" :index="i">
                <span class="sl-item-label">{{ item[labelField] || item.label || item.title || '(không có tên)' }}</span>
                <span v-if="item.to" class="sl-item-sub">{{ item.to }}</span>
              </slot>
            </template>
          </div>
          <div class="sl-actions">
            <button type="button" class="sl-btn" :disabled="i === 0" @click="moveUp(i)" title="Lên" aria-label="Di chuyển lên">▲</button>
            <button type="button" class="sl-btn" :disabled="i === localItems.length - 1" @click="moveDown(i)" title="Xuống" aria-label="Di chuyển xuống">▼</button>
            <button type="button" class="sl-btn sl-btn-edit" @click="toggleEdit(i)" :title="editingIndex === i ? 'Đóng' : 'Sửa'" :aria-label="editingIndex === i ? 'Đóng chỉnh sửa' : 'Sửa mục'">
              {{ editingIndex === i ? '✓' : '✎' }}
            </button>
            <button type="button" class="sl-btn sl-btn-remove" @click="removeItem(i)" title="Xoá" aria-label="Xoá mục">✕</button>
          </div>
        </div>
        <Transition name="sl-expand">
          <div v-if="item.children && editingIndex === i" class="sl-children">
            <TransitionGroup name="sl-list" tag="div" class="sl-children-list">
              <div v-for="(child, ci) in item.children" :key="`child-${ci}-${child.label}`" class="sl-child-item">
                <span class="sl-child-bullet" aria-hidden="true">›</span>
                <input :value="child.label" placeholder="Label" class="sl-edit-input sl-child-input"
                  @input="updateChild(i, ci, 'label', ($event.target as HTMLInputElement).value)" />
                <input :value="child.to" placeholder="/path" class="sl-edit-input sl-child-input"
                  @input="updateChild(i, ci, 'to', ($event.target as HTMLInputElement).value)" />
                <button type="button" class="sl-btn sl-btn-remove" @click="removeChild(i, ci)" aria-label="Xoá mục con">✕</button>
              </div>
            </TransitionGroup>
            <button type="button" class="sl-add-child" @click="addChild(i)">+ Thêm mục con</button>
          </div>
        </Transition>
      </div>
    </TransitionGroup>

    <button type="button" class="sl-add" @click="addItem">+ {{ addLabel }}</button>
  </div>
</template>

<script setup lang="ts">
const props = withDefaults(defineProps<{
  items: any[]
  labelField?: string
  editableFields?: string[]
  addLabel?: string
  newItemTemplate?: Record<string, unknown>
}>(), {
  labelField: 'label',
  editableFields: () => ['label', 'to'],
  addLabel: 'Thêm mục',
  newItemTemplate: () => ({ label: '', to: '' }),
})

const emit = defineEmits<{
  'update:items': [items: any[]]
}>()

const localItems = ref<any[]>([])
const editingIndex = ref<number | null>(null)

function itemKey(item: any, i: number): string {
  return `${item[props.labelField] || item.label || item.title || ''}-${i}`
}

watch(() => props.items, (val) => {
  localItems.value = JSON.parse(JSON.stringify(val || []))
}, { immediate: true, deep: true })

function emitUpdate() {
  emit('update:items', JSON.parse(JSON.stringify(localItems.value)))
}

function moveUp(i: number) {
  if (i <= 0) return
  const arr = [...localItems.value]
  ;[arr[i - 1], arr[i]] = [arr[i], arr[i - 1]]
  localItems.value = arr
  if (editingIndex.value === i) editingIndex.value = i - 1
  emitUpdate()
}

function moveDown(i: number) {
  if (i >= localItems.value.length - 1) return
  const arr = [...localItems.value]
  ;[arr[i], arr[i + 1]] = [arr[i + 1], arr[i]]
  localItems.value = arr
  if (editingIndex.value === i) editingIndex.value = i + 1
  emitUpdate()
}

function removeItem(i: number) {
  if (!confirm('Xoá mục này?')) return
  localItems.value.splice(i, 1)
  editingIndex.value = null
  emitUpdate()
}

function addItem() {
  localItems.value.push(JSON.parse(JSON.stringify(props.newItemTemplate)))
  editingIndex.value = localItems.value.length - 1
  emitUpdate()
}

function toggleEdit(i: number) {
  editingIndex.value = editingIndex.value === i ? null : i
}

function updateField(i: number, field: string, val: string) {
  localItems.value[i][field] = val
  emitUpdate()
}

function updateChild(parentIdx: number, childIdx: number, field: string, val: string) {
  localItems.value[parentIdx].children[childIdx][field] = val
  emitUpdate()
}

function removeChild(parentIdx: number, childIdx: number) {
  localItems.value[parentIdx].children.splice(childIdx, 1)
  emitUpdate()
}

function addChild(parentIdx: number) {
  if (!localItems.value[parentIdx].children) {
    localItems.value[parentIdx].children = []
  }
  localItems.value[parentIdx].children.push({ label: '', to: '' })
  emitUpdate()
}
</script>

<style scoped>
.sl { display: flex; flex-direction: column; gap: var(--space-3); }
.sl-items { display: flex; flex-direction: column; gap: 2px; }

.sl-item {
  background: var(--bg); border: .5px solid var(--line); border-radius: 12px;
  transition: box-shadow .3s cubic-bezier(.2,1,.4,1), border-color .3s;
}
.sl-item:hover { box-shadow: 0 2px 12px rgba(0,0,0,.05); }
.sl-item-editing { border-color: var(--primary, #219653); box-shadow: 0 0 0 3px rgba(33,150,83,.08); }

.sl-item-head {
  display: flex; align-items: center; gap: var(--space-3);
  padding: 12px 14px; min-height: 44px;
}
.sl-handle {
  color: var(--muted); font-size: .85rem; cursor: grab; user-select: none;
  width: 20px; text-align: center; opacity: .5;
  transition: opacity .2s;
}
.sl-item:hover .sl-handle { opacity: 1; }

.sl-item-content { flex: 1; min-width: 0; }
.sl-item-label { font-size: .88rem; font-weight: 500; }
.sl-item-sub { display: block; font-size: .75rem; color: var(--muted); margin-top: 2px; }

.sl-actions { display: flex; gap: 4px; flex-shrink: 0; }
.sl-btn {
  width: 34px; height: 34px; border-radius: 8px;
  border: .5px solid var(--line); background: var(--bg);
  font-size: .72rem; cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: background .2s cubic-bezier(.2,1,.4,1), color .2s, transform .15s cubic-bezier(.2,1,.4,1);
}
.sl-btn:hover:not(:disabled) { background: rgba(52,120,246,.06); color: #3478F6; }
.sl-btn:active:not(:disabled) { transform: scale(.9); }
.sl-btn:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 1px; }
.sl-btn:disabled { opacity: .25; cursor: not-allowed; }
.sl-btn-edit:hover:not(:disabled) { background: rgba(33,150,83,.06); color: #219653; }
.sl-btn-remove:hover:not(:disabled) { background: rgba(217,79,61,.06); color: #D94F3D; }

.sl-edit-fields { display: flex; flex-direction: column; gap: var(--space-3); }
.sl-edit-group { display: flex; flex-direction: column; gap: 4px; }
.sl-edit-label { font-size: .72rem; font-weight: 500; color: var(--muted); text-transform: capitalize; }
.sl-edit-input {
  padding: 8px 12px; border: .5px solid var(--line); border-radius: 10px;
  font-size: .85rem; background: var(--bg); color: var(--ink);
  min-height: 38px;
  transition: border-color .2s, box-shadow .2s;
}
.sl-edit-input:focus {
  outline: none; border-color: var(--primary, #219653);
  box-shadow: 0 0 0 3px rgba(33,150,83,.1);
}

.sl-children {
  padding: 0 14px 14px 44px;
  display: flex; flex-direction: column; gap: var(--space-2);
}
.sl-children-list { display: flex; flex-direction: column; gap: var(--space-2); }
.sl-child-item { display: flex; gap: var(--space-2); align-items: center; }
.sl-child-bullet { color: var(--muted); font-size: 1.1rem; font-weight: 600; width: 12px; text-align: center; flex-shrink: 0; }
.sl-child-input { flex: 1; }
.sl-add-child {
  align-self: flex-start; padding: 8px 14px; border-radius: 10px;
  font-size: .8rem; font-weight: 500; color: var(--primary, #219653);
  background: rgba(33,150,83,.06); border: none; cursor: pointer;
  min-height: 36px;
  transition: background .2s, transform .15s cubic-bezier(.2,1,.4,1);
}
.sl-add-child:hover { background: rgba(33,150,83,.1); }
.sl-add-child:active { transform: scale(.97); }

.sl-add {
  padding: 14px; border-radius: 12px;
  border: 1.5px dashed var(--line); background: transparent;
  font-size: .88rem; font-weight: 500; color: var(--primary, #219653);
  cursor: pointer; min-height: 44px;
  transition: background .2s cubic-bezier(.2,1,.4,1), border-color .2s, transform .15s;
}
.sl-add:hover { background: rgba(33,150,83,.04); border-color: var(--primary, #219653); }
.sl-add:active { transform: scale(.98); }
.sl-add:focus-visible { outline: 2px solid var(--primary, #219653); outline-offset: 2px; }

/* ── List transitions ── */
.sl-list-enter-active { transition: all .3s cubic-bezier(.2,1,.4,1); }
.sl-list-leave-active { transition: all .2s ease-in; }
.sl-list-enter-from { opacity: 0; transform: translateY(-8px); }
.sl-list-leave-to { opacity: 0; transform: scale(.96); }
.sl-list-move { transition: transform .3s cubic-bezier(.2,1,.4,1); }

/* ── Expand transition ── */
.sl-expand-enter-active { transition: all .3s cubic-bezier(.2,1,.4,1); }
.sl-expand-leave-active { transition: all .15s ease-in; }
.sl-expand-enter-from { opacity: 0; transform: translateY(-6px); }
.sl-expand-leave-to { opacity: 0; }

/* ── Dark ── */
.dark .sl-item { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .sl-item-editing { border-color: var(--primary, #219653); box-shadow: 0 0 0 3px rgba(33,150,83,.15); }
.dark .sl-btn { background: var(--card, #2c2c2e); border-color: rgba(255,255,255,.06); }
.dark .sl-edit-input { background: rgba(255,255,255,.04); border-color: rgba(255,255,255,.08); }
.dark .sl-add { border-color: rgba(255,255,255,.1); }

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .sl-item, .sl-btn, .sl-add, .sl-add-child { transition: none; }
  .sl-list-enter-active, .sl-list-leave-active, .sl-list-move,
  .sl-expand-enter-active, .sl-expand-leave-active { transition: none; }
  .sl-btn:active:not(:disabled), .sl-add:active, .sl-add-child:active { transform: none; }
}
</style>
