<script setup lang="ts">
// Where the case actually is, told in order, with the promise attached.
//
// The timeline never says more than the projection does: each step is derived
// from fields the backend sent, and the one live region announces changes for
// screen readers without re-reading the whole page.
import { computed } from 'vue'

import DecisionPublicationState from './DecisionPublicationState.vue'
import type { CaseStatus } from '../../types/cases'

const props = defineProps<{ status: CaseStatus }>()
const emit = defineEmits<{ (event: 'request-review'): void }>()

const receivedOn = computed(() => new Date(props.status.receivedAt).toLocaleString('vi-VN'))
const nextUpdate = computed(() => new Date(props.status.nextUpdateAt).toLocaleString('vi-VN'))

// The date below is what we promised at the start, and it does not move. Once
// it has passed, calling it "still in effect" is the site telling somebody the
// deadline it already missed is fine. Say the true thing instead.
const promiseNote = computed(() => {
  switch (props.status.promiseHealth) {
    case 'recovery':
      return 'Có trục trặc khi hoàn tất; chúng tôi đang khắc phục và sẽ báo lại.'
    case 'breached':
      return 'Chúng tôi đã trễ hạn dưới đây. Hồ sơ đã được chuyển lên mức ưu tiên cao hơn'
        + ' và chúng tôi sẽ cập nhật sớm nhất có thể.'
    case 'at_risk':
      return 'Việc xử lý đang chậm hơn dự kiến; hạn cập nhật bên dưới vẫn có hiệu lực.'
    default:
      return null
  }
})

// A review is an act on an answer. While items are still undecided there is no
// answer to contest, so the action simply is not offered.
const terminal = computed(() =>
  props.status.itemDecisions.length > 0
  && props.status.itemDecisions.every(decision => decision.dispositionFamily !== 'undetermined'),
)

const publicationByItem = computed(() => new Map(
  props.status.itemPublicationStates.map(entry => [entry.itemId, entry.state] as const),
))
</script>

<template>
  <section class="case-timeline" aria-labelledby="timeline-heading">
    <h2 id="timeline-heading">Trạng thái yêu cầu {{ status.publicReference }}</h2>

    <!-- Announce progress without re-reading the page. -->
    <p class="timeline-live" aria-live="polite" data-role="live-step">
      {{ status.currentStep }}
    </p>

    <ol class="timeline-steps">
      <li>
        <h3>Đã tiếp nhận</h3>
        <p>{{ receivedOn }}</p>
      </li>
      <li>
        <h3>Bước hiện tại</h3>
        <p data-role="current-step">{{ status.currentStep }}</p>
        <p v-if="status.waitingFor" data-role="waiting-for">Đang chờ: {{ status.waitingFor }}</p>
      </li>
      <li>
        <h3>Việc kế tiếp</h3>
        <p data-role="next-action">{{ status.nextAction }}</p>
        <p data-role="next-update">
          {{ status.promiseHealth === 'breached' ? 'Hạn đã hứa' : 'Cập nhật trước' }}:
          {{ nextUpdate }}
        </p>
        <p v-if="promiseNote" class="timeline-promise" data-role="promise-note">{{ promiseNote }}</p>
      </li>
    </ol>

    <section v-if="status.itemDecisions.length" aria-labelledby="items-heading">
      <h3 id="items-heading">Từng nội dung đã báo</h3>
      <div class="timeline-items">
        <DecisionPublicationState
          v-for="decision in status.itemDecisions"
          :key="decision.itemId"
          field-label="Nội dung đã báo"
          :outcome="decision.outcome"
          :disposition-family="decision.dispositionFamily"
          :publication-state="publicationByItem.get(decision.itemId) ?? 'not_required'"
        />
      </div>
    </section>

    <div class="timeline-actions">
      <!-- Only on a terminal answer: contesting nothing helps nobody. -->
      <button
        v-if="terminal"
        type="button"
        data-role="request-review"
        @click="emit('request-review')"
      >
        Yêu cầu xem xét lại
      </button>
      <p v-else class="timeline-review-note" data-role="review-unavailable">
        Có thể yêu cầu xem xét lại sau khi có kết quả.
      </p>
    </div>
  </section>
</template>

<style scoped>
.case-timeline {
  display: grid;
  gap: 1rem;
}
.timeline-steps {
  display: grid;
  gap: 0.9rem;
  margin: 0;
  padding-left: 1.25rem;
}
.timeline-steps h3 {
  margin: 0 0 0.2rem;
  font-size: 1rem;
}
.timeline-steps p {
  margin: 0;
}
.timeline-promise {
  color: var(--color-warning);
}
.timeline-items {
  display: grid;
  gap: 0.6rem;
}
.timeline-actions {
  margin-top: 0.25rem;
}

/* Status progression is the only motion, and it bows out entirely when the
   reader asked for stillness. */
@media (prefers-reduced-motion: no-preference) {
  .timeline-steps li {
    animation: step-reveal 240ms ease-out both;
  }
  @keyframes step-reveal {
    from {
      opacity: 0;
      transform: translateY(4px);
    }
    to {
      opacity: 1;
      transform: none;
    }
  }
}
</style>
