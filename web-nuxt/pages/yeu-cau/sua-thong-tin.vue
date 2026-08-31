<script setup lang="ts">
// Reporting a mistake on an entry, and walking away with a receipt.
//
// The page holds the receipt only while it is on screen. The moment the reader
// confirms they saved the one-time key — or navigates away — it is forgotten;
// everything afterwards runs on the HttpOnly cookie the backend set.
import { computed, ref } from 'vue'

import CaseReceiptCard from '../../components/cases/CaseReceiptCard.vue'
import CorrectionIntakeForm from '../../components/cases/CorrectionIntakeForm.vue'
import {
  CaseAccessError,
  CorrectionProblemError,
  useCorrectionCases,
} from '../../composables/useCorrectionCases'
import type { CaseReceipt, CorrectionProblemDetail, CorrectionSubmission } from '../../types/cases'
import { apiFetch } from '../../utils/apiFetch'
import { CORRECTION_FIELD_HINTS } from '../../utils/correctionLink'

const route = useRoute()
const cases = useCorrectionCases()
// Deployment-provided; an empty value hides the phone lane entirely.
const assistedHours = String(useRuntimeConfig().public.caseAssistedHours || '')

const entityId = computed(() => {
  const raw = String(route.query.entity ?? '').slice(0, 200)
  return /^[a-z0-9][a-z0-9-]*$/i.test(raw) ? raw : ''
})

// A hint, never data: the form only preselects a field it already offers, and
// the values themselves are typed by the reporter against the live entry.
const fieldHint = computed(() => {
  const raw = String(route.query.field ?? '')
  return CORRECTION_FIELD_HINTS.has(raw) ? raw : null
})

// Name and revision come from the live projection, never from the URL: the
// revision pins which wording the correction was written against.
const { data: entity, error: entityError, refresh: refreshEntity } = await useAsyncData(
  () => entityId.value ? `case-entity:${entityId.value}` : 'case-entity:none',
  async () => {
    if (!entityId.value) return null
    // KHÔNG nuốt lỗi ở đây. `catch { return null }` trước đây gộp hai trạng thái
    // khác hẳn nhau vào một: "chưa chọn địa điểm" và "tải hỏng" cùng rơi vào
    // nhánh .case-missing, nên người đến ĐÚNG đường vẫn bị bảo đi mở trang địa
    // điểm rồi bấm nút — tức bảo họ làm lại đúng việc vừa làm, không nút thử
    // lại, không lời giải thích. Để useAsyncData giữ lỗi thì trang mới phân biệt
    // được hai đường.
    return await apiFetch<{ id: string, name: string, revision: number }>(
      `/api/entities/${encodeURIComponent(entityId.value)}`,
    )
  },
)

const busy = ref(false)
const receipt = ref<CaseReceipt | null>(null)
const failure = ref('')
const problem = ref<CorrectionProblemDetail | null>(null)

async function submit(submission: CorrectionSubmission) {
  busy.value = true
  failure.value = ''
  problem.value = null
  try {
    receipt.value = await cases.createCorrection(submission)
  } catch (error) {
    if (error instanceof CorrectionProblemError) {
      problem.value = error.problem
      failure.value = error.problem.detail
    } else {
      failure.value = error instanceof CaseAccessError
        ? error.message
        : 'Chưa gửi được yêu cầu. Vui lòng thử lại sau ít phút.'
    }
  } finally {
    busy.value = false
  }
}

async function verifyPhone(phone: string) {
  try {
    await cases.requestContactVerification(phone)
  } catch {
    // The number is optional; a failed verification never blocks the report.
  }
}

useSeoMeta({
  title: 'Yêu cầu sửa thông tin — vinhlong360',
  description: 'Báo thông tin chưa đúng trên vinhlong360 và nhận mã tra cứu tiến trình xử lý.',
})
</script>

<template>
  <section class="case-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Yêu cầu sửa thông tin' }]" />

    <header class="case-header">
      <h1>Yêu cầu sửa thông tin</h1>
      <p class="case-trust-note">
        Yêu cầu được ghi nhận có mã tra cứu, có hạn phản hồi, và bạn có thể kiểm tra
        tiến trình bất kỳ lúc nào. Chúng tôi chỉ hỏi những gì cần cho việc sửa.
      </p>
    </header>

    <PageState
      v-if="entityId && entityError"
      :state="{ kind: 'error', retry: { label: 'Thử lại' } }"
      title="Không tải được thông tin địa điểm"
      :retry="refreshEntity"
    />

    <div v-else-if="!entityId || !entity" class="case-missing" aria-live="polite">
      <p>
        Hãy mở trang của địa điểm cần sửa và bấm «Báo thông tin chưa đúng» để bắt đầu —
        như vậy yêu cầu gắn đúng vào trang đó.
      </p>
      <NuxtLink to="/danh-ba">Tìm địa điểm trong danh bạ</NuxtLink>
    </div>

    <template v-else>
      <p v-if="failure" class="case-failure" role="alert">{{ failure }}</p>
      <div v-if="problem" class="case-problem" data-role="correction-problem" role="status">
        <span v-if="problem.field">Trường cần kiểm tra: {{ problem.field }}</span>
        <span v-if="problem.correlation_id">Mã đối soát: {{ problem.correlation_id }}</span>
      </div>

      <CaseReceiptCard
        v-if="receipt"
        :receipt="receipt"
        @forget="cases.forgetCapability()"
      />
      <CorrectionIntakeForm
        v-else
        :entity-id="entity.id"
        :entity-name="entity.name"
        :base-entity-revision="entity.revision"
        :initial-field-path="fieldHint"
        :assisted-hours="assistedHours || null"
        :busy="busy"
        :server-problem="problem"
        @submit="submit"
        @request-phone-verification="verifyPhone"
      />
    </template>
  </section>
</template>

<style scoped>
.case-page {
  display: grid;
  gap: 1.25rem;
  grid-template-columns: minmax(0, 1fr);
  max-inline-size: 42rem;
  margin-inline: auto;
  padding: 1rem;
}
.case-header h1 {
  margin: 0 0 0.4rem;
}
.case-trust-note {
  margin: 0;
  color: var(--muted);
}
.case-failure {
  padding: 0.6rem 0.8rem;
  border-radius: 8px;
  border: 1px solid var(--color-error);
}
.case-missing {
  display: grid;
  gap: 0.5rem;
}
</style>
