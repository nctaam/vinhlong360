<template>
  <div class="img-mgr">
    <strong class="admin-label">Quan hệ ({{ rels.length }})</strong>
    <div v-for="(r, i) in rels" :key="i" class="img-row">
      <span class="img-url">{{ r.type }} → {{ r.target_name || r.source_name || r.to_id }}</span>
      <button type="button" class="btn-danger btn-sm" @click="$emit('remove-rel', r)">Xóa</button>
    </div>
    <div class="admin-inline-add">
      <select v-model="newRel.type" class="input" aria-label="Loại quan hệ" style="flex:0 0 130px">
        <option v-for="t in relTypes" :key="t" :value="t">{{ t }}</option>
      </select>
      <input v-model="newRel.to_id" class="input" placeholder="ID entity đích" aria-label="ID entity đích" @keyup.enter="$emit('add-rel')" />
      <button type="button" class="btn btn-secondary btn-sm" :disabled="!newRel.to_id.trim()" @click="$emit('add-rel')">Thêm</button>
    </div>
    <details class="bulk-rel-details">
      <summary class="btn btn-ghost btn-sm">Thêm hàng loạt…</summary>
      <div class="bulk-rel-inner">
        <select v-model="bulkModel.type" class="input" aria-label="Loại quan hệ hàng loạt" style="max-width:160px">
          <option v-for="t in relTypes" :key="t" :value="t">{{ t }}</option>
        </select>
        <textarea v-model="bulkModel.ids" class="input" placeholder="Mỗi dòng 1 entity ID đích" rows="3" aria-label="Danh sách entity ID đích"></textarea>
        <button type="button" class="btn btn-secondary btn-sm" :disabled="!bulkModel.ids.trim() || bulkRelSaving" @click="$emit('add-bulk-rels')">
          {{ bulkRelSaving ? 'Đang thêm…' : 'Thêm tất cả' }}
        </button>
      </div>
    </details>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface RelItem {
  from_id?: string
  type: string
  to_id: string
  target_name?: string
  source_name?: string
}

const props = defineProps<{
  rels: RelItem[]
  relTypes: string[]
  newRel: { to_id: string; type: string }
  bulkRelType: string
  bulkRelIds: string
  bulkRelSaving: boolean
}>()

const emit = defineEmits<{
  (e: 'update:bulkRelType', val: string): void
  (e: 'update:bulkRelIds', val: string): void
  (e: 'add-rel'): void
  (e: 'remove-rel', rel: RelItem): void
  (e: 'add-bulk-rels'): void
}>()

const bulkModel = computed({
  get: () => ({ type: props.bulkRelType, ids: props.bulkRelIds }),
  set: (val) => {
    emit('update:bulkRelType', val.type)
    emit('update:bulkRelIds', val.ids)
  },
})
</script>
