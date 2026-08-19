<script setup lang="ts">
// The queue, in the grammar the work is triaged by:
// queue → promise health → owner → next action. Risk is never colour alone —
// every state carries its words, so a monochrome screen reads the same.
import type { AdminQueueItem } from '../../../composables/useAdminCases'

defineProps<{
  items: AdminQueueItem[]
  selectedCaseId?: string | null
}>()

const emit = defineEmits<{ (event: 'open', item: AdminQueueItem): void }>()

const KIND_LABEL: Record<string, string> = {
  decide: 'Cần quyết định',
  publication: 'Cần đăng',
  verify: 'Cần kiểm chứng',
}
</script>

<template>
  <section class="case-queue" aria-label="Hàng đợi yêu cầu">
    <h2>Hàng đợi</h2>
    <p v-if="!items.length" class="queue-empty">Không có việc đang chờ.</p>
    <ol v-else class="queue-list">
      <li v-for="item in items" :key="item.work_item_id">
        <button
          type="button"
          class="queue-row"
          :aria-current="item.case_id === selectedCaseId ? 'true' : undefined"
          :data-risk="item.risk_class"
          @click="emit('open', item)"
        >
          <span class="queue-kind">{{ KIND_LABEL[item.kind] ?? item.kind }}</span>
          <!-- The words carry the risk; the tint only underlines them. -->
          <span class="queue-risk">Mức rủi ro {{ item.risk_class }}</span>
          <span class="queue-status">{{ item.status === 'claimed' ? 'Đang có người giữ' : 'Chưa ai nhận' }}</span>
          <span class="queue-case">{{ item.case_id.slice(0, 8) }}…</span>
        </button>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.case-queue {
  display: grid;
  gap: 0.6rem;
  min-inline-size: 0;
}
.queue-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.35rem;
}
.queue-row {
  inline-size: 100%;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.15rem 0.6rem;
  text-align: start;
  padding: 0.5rem 0.7rem;
  border: 1px solid var(--border-soft, rgba(120, 113, 108, 0.3));
  border-radius: 8px;
  background: none;
  cursor: pointer;
}
.queue-row[aria-current='true'] {
  border-color: var(--primary, #1d4ed8);
}
.queue-kind {
  font-weight: 600;
}
.queue-risk,
.queue-status,
.queue-case {
  font-size: 0.8rem;
  color: var(--text-muted, #78716c);
}
.queue-row[data-risk='R3'] .queue-risk {
  font-weight: 700;
}
</style>
