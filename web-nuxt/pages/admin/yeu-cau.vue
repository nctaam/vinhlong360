<script setup lang="ts">
// The correction workbench: queue on one side, one case on the other.
//
// Desktop holds both; a narrow screen shows the queue, then the case. Every
// mutating action goes through the composable, carries the revision the
// operator saw, and a 409 surfaces the reloaded case instead of retrying.
import { computed, onBeforeUnmount, ref } from 'vue'

import AssistedCorrectionForm from '../../components/admin/cases/AssistedCorrectionForm.vue'
import CaseQueue from '../../components/admin/cases/CaseQueue.vue'
import CaseWorkbench from '../../components/admin/cases/CaseWorkbench.vue'
import EvidencePanel from '../../components/admin/cases/EvidencePanel.vue'
import {
  RevisionConflictError,
  useAdminCases,
  type AdminQueueItem,
} from '../../composables/useAdminCases'

definePageMeta({ layout: 'admin' })

const cases = useAdminCases()
const scopes = computed<string[]>(() => {
  const state = useState<{ scopes?: string[] } | null>('admin-user', () => null)
  return state.value?.scopes ?? []
})

const conflict = ref(false)
const failure = ref('')
const busy = ref(false)
const claimedWorkItem = ref<AdminQueueItem | null>(null)
const leaseSecondsLeft = ref<number | null>(null)
let leaseTimer: ReturnType<typeof setInterval> | null = null

async function run(action: () => Promise<unknown>) {
  busy.value = true
  failure.value = ''
  conflict.value = false
  try {
    await action()
  } catch (error) {
    if (error instanceof RevisionConflictError) {
      // The composable already reloaded the case; the person re-applies
      // against what is now on screen or walks away.
      conflict.value = true
    } else {
      failure.value = 'Thao tác chưa thực hiện được. Thử lại hoặc tải lại hồ sơ.'
    }
  } finally {
    busy.value = false
  }
}

async function openWorkItem(item: AdminQueueItem) {
  await run(async () => {
    await cases.openCase(item.case_id)
  })
}

async function claimSelected(item: AdminQueueItem) {
  await run(async () => {
    await cases.claim(item.work_item_id, item.revision)
    claimedWorkItem.value = item
    leaseSecondsLeft.value = 15 * 60
    if (leaseTimer) clearInterval(leaseTimer)
    leaseTimer = setInterval(() => {
      if (leaseSecondsLeft.value != null && leaseSecondsLeft.value > 0) {
        leaseSecondsLeft.value -= 1
      }
    }, 1000)
    await cases.loadQueue()
  })
}

onBeforeUnmount(() => {
  if (leaseTimer) clearInterval(leaseTimer)
})

await useAsyncData('admin-case-queue', async () => {
  await cases.loadQueue().catch(() => {})
  return true
})
</script>

<template>
  <section class="admin-cases" aria-label="Xử lý yêu cầu sửa thông tin">
    <header class="admin-cases-head">
      <h1>Yêu cầu sửa thông tin</h1>
      <p v-if="failure" role="alert" class="admin-cases-failure">{{ failure }}</p>
    </header>

    <div class="admin-cases-split">
      <div class="admin-cases-queue">
        <CaseQueue
          :items="cases.queue.value"
          :selected-case-id="cases.current.value?.case_id"
          @open="openWorkItem"
        />
        <button
          v-if="cases.current.value && !claimedWorkItem"
          type="button"
          data-role="claim"
          :disabled="busy"
          @click="claimSelected(cases.queue.value.find(i => i.case_id === cases.current.value?.case_id)!)"
        >
          Nhận việc này
        </button>
      </div>

      <div class="admin-cases-work">
        <CaseWorkbench
          v-if="cases.current.value"
          :detail="cases.current.value"
          :scopes="scopes"
          :lease-seconds-left="leaseSecondsLeft"
          :conflict="conflict"
          :busy="busy"
          @reload="run(() => cases.openCase(cases.current.value!.case_id))"
          @decide="body => run(() => cases.decide({ case_id: cases.current.value!.case_id, risk_class: 'R1', ...body }))"
          @build-change-set="itemIds => run(() => cases.buildChangeSet({
            case_id: cases.current.value!.case_id, item_ids: itemIds,
            expected_revision: cases.current.value!.current_revision, evidence_refs: [],
          }))"
          @apply-change-set="run(() => cases.applyChangeSet({
            case_id: cases.current.value!.case_id, change_set_id: '',
            expected_case_revision: cases.current.value!.current_revision,
          }))"
          @verify-change-set="run(() => cases.verifyChangeSet({
            case_id: cases.current.value!.case_id, change_set_id: '',
          }))"
          @rollback-change-set="run(() => cases.rollbackChangeSet({
            case_id: cases.current.value!.case_id, change_set_id: '',
            expected_case_revision: cases.current.value!.current_revision,
          }))"
        />
        <p v-else class="admin-cases-empty">Chọn một việc trong hàng đợi để mở hồ sơ.</p>

        <EvidencePanel
          v-if="cases.current.value"
          :case-id="cases.current.value.case_id"
          :step-up-secret="cases.stepUpSecret.value"
          :busy="busy"
          @step-up="run(() => cases.stepUp(cases.current.value!.case_id))"
          @drop-step-up="run(() => cases.dropStepUp(cases.current.value!.case_id))"
        />

        <AssistedCorrectionForm
          v-if="scopes.includes('service.operator') || scopes.includes('*')"
          privacy-notice-revision="privacy-2026-07"
          :busy="busy"
          @submit="body => run(() => cases.createAssisted(body))"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.admin-cases {
  display: grid;
  gap: 1rem;
  padding: 1rem;
}
.admin-cases-failure {
  margin: 0;
  color: var(--color-danger, #b91c1c);
}
/* Mobile first: one stacked task view. */
.admin-cases-split {
  display: grid;
  gap: 1rem;
  grid-template-columns: minmax(0, 1fr);
}
.admin-cases-queue,
.admin-cases-work {
  display: grid;
  gap: 0.9rem;
  align-content: start;
  min-inline-size: 0;
}
.admin-cases-empty {
  margin: 0;
  color: var(--text-muted, #78716c);
}
/* Desktop: queue beside the case, queue resizable within its column. */
@media (min-width: 64rem) {
  .admin-cases-split {
    grid-template-columns: minmax(16rem, 24rem) minmax(0, 1fr);
  }
  .admin-cases-queue {
    resize: horizontal;
    overflow: auto;
  }
}
</style>
