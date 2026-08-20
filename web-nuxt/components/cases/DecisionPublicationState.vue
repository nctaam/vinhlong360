<script setup lang="ts">
// One item's answer: what was decided, and separately, how far the public
// change has got. Two facts, two lines — collapsing them is how "accepted"
// quietly gets read as "already on the page".
import { computed } from 'vue'

import {
  CASE_DECISION_COPY,
  CASE_OUTCOME_COPY,
  CASE_PUBLICATION_COPY,
  type CaseDispositionFamily,
  type CasePublicationState,
} from '../../types/cases'

const props = defineProps<{
  fieldLabel: string
  dispositionFamily: CaseDispositionFamily
  publicationState: CasePublicationState
  outcome?: string | null
}>()

// The specific ruling when there is one, the family when there is not. Three
// different refusals reading as one "Không thay đổi" leaves the reporter with
// no idea whether sending another source would help.
const decisionText = computed(() =>
  (props.outcome ? CASE_OUTCOME_COPY[props.outcome] : null)
  ?? CASE_DECISION_COPY[props.dispositionFamily],
)
const publicationText = computed(() => CASE_PUBLICATION_COPY[props.publicationState])
// The waiting states carry the promise; the settled ones carry the answer.
const settled = computed(() => ['verified', 'not_required'].includes(props.publicationState))
</script>

<template>
  <div class="dps-item" :data-publication-state="publicationState">
    <p class="dps-field">{{ fieldLabel }}</p>
    <dl class="dps-facts">
      <div class="dps-fact">
        <dt>Quyết định</dt>
        <dd data-role="decision">{{ decisionText }}</dd>
      </div>
      <div class="dps-fact">
        <dt>Trên trang công khai</dt>
        <dd data-role="publication" :class="{ 'dps-settled': settled }">{{ publicationText }}</dd>
      </div>
    </dl>
  </div>
</template>

<style scoped>
.dps-item {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.75rem 1rem;
}
.dps-field {
  margin: 0 0 0.5rem;
  font-weight: 600;
}
.dps-facts {
  display: grid;
  gap: 0.4rem;
  margin: 0;
}
.dps-fact dt {
  font-size: 0.8rem;
  color: var(--muted);
}
.dps-fact dd {
  margin: 0;
}
.dps-settled {
  color: var(--color-source-verified);
}
</style>
