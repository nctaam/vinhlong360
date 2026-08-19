<script setup lang="ts">
// The queue, in the grammar the work is triaged by:
// queue → promise health → owner → next action. Risk is never colour alone —
// every state carries its words, so a monochrome screen reads the same.
import type { AdminQueueItem } from '../../../composables/useAdminCases'

import {
  CASE_HEALTH_LABEL as HEALTH_LABEL,
  CASE_KIND_LABEL as KIND_LABEL,
} from '../../../utils/caseLabels'

defineProps<{
  items: AdminQueueItem[]
  selectedCaseId?: string | null
}>()

const emit = defineEmits<{ (event: 'open', item: AdminQueueItem): void }>()

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
          <!-- The grammar, in reading order: next action, promise health,
               owner, then the identifiers. All words, no colour-only state. -->
          <span class="queue-kind">{{ KIND_LABEL[item.kind] ?? item.kind }}</span>
          <span class="queue-health" :data-health="item.promise_health">
            {{ HEALTH_LABEL[item.promise_health ?? 'on_track'] ?? item.promise_health }}
          </span>
          <span class="queue-owner">
            {{ item.owner_ref ? `Người giữ: ${item.owner_ref}` : 'Chưa ai nhận' }}
          </span>
          <span class="queue-risk">Mức rủi ro {{ item.risk_class }}</span>
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
  border: 1px solid var(--border);
  border-radius: 8px;
  background: none;
  cursor: pointer;
}
.queue-row[aria-current='true'] {
  border-color: var(--primary);
}
.queue-kind {
  font-weight: 600;
}
.queue-health[data-health='breached'],
.queue-health[data-health='at_risk'] {
  font-weight: 700;
}
.queue-risk,
.queue-health,
.queue-owner,
.queue-case {
  font-size: 0.8rem;
  color: var(--muted);
}
.queue-row[data-risk='R3'] .queue-risk {
  font-weight: 700;
}
</style>
