<template>
  <details v-if="kindGroups.length" class="ent-kinds-panel">
    <summary class="ent-kinds-summary">
      <IconLine name="chart" /> Tổng quan theo danh mục
      <span class="ent-kinds-total">{{ kindGrandTotal.toLocaleString('vi-VN') }} entity</span>
    </summary>
    <div class="ent-kinds-grid">
      <div v-for="k in kindGroups" :key="k.kind" class="ent-kind-card">
        <div class="ent-kind-head">
          <span class="ent-kind-emoji" aria-hidden="true"><IconLine :name="kindIcon(k.kind)" /></span>
          <span class="ent-kind-label">{{ k.label }}</span>
          <span class="ent-kind-count">{{ k.total }}</span>
        </div>
        <div class="ent-kind-types">
          <button v-for="t in k.types" :key="t.type" type="button"
            class="ent-kind-chip" :class="{ active: typeFilter === t.type }"
            :title="`Lọc: ${t.label} (${t.count})`" @click="$emit('filter', t.type)">
            <IconLine :name="typeIcon(t.type)" aria-hidden="true" /> {{ t.label }} <span class="ent-kind-chip-n">{{ t.count }}</span>
          </button>
        </div>
      </div>
    </div>
  </details>
</template>

<script setup lang="ts">
import { TYPE_META } from '~/composables/useConstants'
import { ADMIN_KINDS } from '~/utils/adminKinds'

interface KindTypeItem {
  type: string
  label: string
  count: number
}

interface KindGroupItem {
  kind: string
  label: string
  total: number
  types: KindTypeItem[]
}

defineProps<{
  kindGroups: KindGroupItem[]
  kindGrandTotal: number
  typeFilter: string
}>()

defineEmits<{
  (e: 'filter', type: string): void
}>()

function kindIcon(kind: string): string {
  return ADMIN_KINDS.find(k => k.kind === kind)?.icon || 'tag'
}

function typeIcon(type: string): string {
  return TYPE_META[type]?.icon || 'tag'
}
</script>
