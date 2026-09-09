<template>
  <div class="ent-history">
    <strong class="admin-label">Lịch sử thay đổi ({{ history.length }})</strong>
    <div v-for="h in history" :key="h.id" class="ent-history-item">
      <span class="ent-history-field">{{ h.field }}</span>
      <span class="ent-history-diff">
        <del v-if="h.old_value" :title="h.old_value">{{ truncVal(h.old_value) }}</del>
        <span class="ent-history-arrow"><IconLine name="arrow-right" /></span>
        <ins :title="h.new_value ?? undefined">{{ truncVal(h.new_value) }}</ins>
      </span>
      <span class="ent-history-time">{{ timeAgo(h.created_at) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
interface EntityHistoryRecord {
  id: string | number
  field: string
  old_value?: string | null
  new_value?: string | null
  created_at: string
}

defineProps<{
  history: EntityHistoryRecord[]
}>()

const { timeAgo } = useTimeAgo()

function truncVal(val: unknown): string {
  const s = String(val ?? '')
  return s.length > 60 ? s.slice(0, 57) + '…' : s
}
</script>
