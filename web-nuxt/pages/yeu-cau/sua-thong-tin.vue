<script setup lang="ts">
// Reporting a mistake on an entry, and walking away with a receipt.
//
// The page holds the receipt only while it is on screen. The moment the reader
// confirms they saved the one-time key — or navigates away — it is forgotten;
// everything afterwards runs on the HttpOnly cookie the backend set.
import { computed, ref } from 'vue'

import CaseReceiptCard from '../../components/cases/CaseReceiptCard.vue'
import CorrectionIntakeForm from '../../components/cases/CorrectionIntakeForm.vue'
import { CaseAccessError, useCorrectionCases } from '../../composables/useCorrectionCases'
import type { CaseReceipt, CorrectionSubmission } from '../../types/cases'
import { apiFetch } from '../../utils/apiFetch'

const route = useRoute()
const cases = useCorrectionCases()

const entityId = computed(() => {
  const raw = String(route.query.entity ?? '').slice(0, 200)
  return /^[a-z0-9][a-z0-9-]*$/i.test(raw) ? raw : ''
})

// Name and revision come from the live projection, never from the URL: the
// revision pins which wording the correction was written against.
const { data: entity } = await useAsyncData(
  () => entityId.value ? `case-entity:${entityId.value}` : 'case-entity:none',
  async () => {
    if (!entityId.value) return null
    try {
      return await apiFetch<{ id: string, name: string, revision: number }>(
        `/api/entities/${encodeURIComponent(entityId.value)}`,
      )
    } catch {
      return null
    }
  },
)

const busy = ref(false)
const receipt = ref<CaseReceipt | null>(null)
const failure = ref('')

async function submit(submission: CorrectionSubmission) {
  busy.value = true
  failure.value = ''
  try {
    receipt.value = await cases.createCorrection(submission)
  } catch (error) {
    failure.value = error instanceof CaseAccessError
      ? error.message
      : 'Chưa gửi được yêu cầu. Vui lòng thử lại sau ít phút.'
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

    <div v-if="!entityId || !entity" class="case-missing" aria-live="polite">
      <p>
        Hãy mở trang của địa điểm cần sửa và bấm «Báo thông tin chưa đúng» để bắt đầu —
        như vậy yêu cầu gắn đúng vào trang đó.
      </p>
      <NuxtLink to="/danh-ba">Tìm địa điểm trong danh bạ</NuxtLink>
    </div>

    <template v-else>
      <p v-if="failure" class="case-failure" role="alert">{{ failure }}</p>

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
        :busy="busy"
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
  color: var(--text-muted, #78716c);
}
.case-failure {
  padding: 0.6rem 0.8rem;
  border-radius: 8px;
  border: 1px solid var(--color-danger, #b91c1c);
}
.case-missing {
  display: grid;
  gap: 0.5rem;
}
</style>
