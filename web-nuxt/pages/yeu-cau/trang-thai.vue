<script setup lang="ts">
// The case as the reporter sees it, running entirely on the session cookie.
//
// No credential appears on this page. If the cookie has expired the reader gets
// one neutral message and the way back to the lookup form — never a hint about
// which part of their session went stale.
import { onMounted, ref } from 'vue'

import CaseReceiptCard from '../../components/cases/CaseReceiptCard.vue'
import CaseStatusTimeline from '../../components/cases/CaseStatusTimeline.vue'
import { CaseAccessError, CaseReviewConflictError, useCorrectionCases } from '../../composables/useCorrectionCases'
import type { CaseReceipt } from '../../types/cases'

const cases = useCorrectionCases()
const router = useRouter()

const loading = ref(true)
const failure = ref('')
const rotated = ref<CaseReceipt | null>(null)
const reviewRequested = ref(false)

async function refresh() {
  loading.value = true
  failure.value = ''
  try {
    await cases.loadStatus()
  } catch (error) {
    failure.value = error instanceof CaseAccessError
      ? error.message
      : 'Chưa tải được trạng thái. Vui lòng thử lại sau ít phút.'
  } finally {
    loading.value = false
  }
}

async function requestReview() {
  try {
    await cases.requestReview('reporter_requested')
    reviewRequested.value = true
    await refresh()
  } catch (error) {
    // CaseReviewConflictError mang lý do THẬT (hồ sơ chưa khép / vừa đổi) và
    // người bấm nút này đã mở được hồ sơ nên mã của họ không hỏng — đừng gộp nó
    // vào câu "kiểm tra lại mã tra cứu".
    failure.value = error instanceof CaseAccessError || error instanceof CaseReviewConflictError
      ? error.message
      : 'Chưa gửi được yêu cầu xem xét lại. Vui lòng thử lại.'
  }
}

async function rotate() {
  try {
    // A fresh receipt invalidates the old key: this is the reader's recourse
    // when they suspect the saved code has been seen by somebody else.
    rotated.value = await cases.rotateReceipt()
  } catch (error) {
    failure.value = error instanceof CaseAccessError
      ? error.message
      : 'Chưa đổi được mã. Vui lòng thử lại.'
  }
}

async function signOut() {
  await cases.clearAccess().catch(() => {})
  await router.push('/yeu-cau/tra-cuu')
}

onMounted(refresh)

useSeoMeta({
  title: 'Trạng thái yêu cầu — vinhlong360',
  description: 'Theo dõi tiến trình xử lý yêu cầu sửa thông tin trên vinhlong360.',
  robots: 'noindex, nofollow',
  ogTitle: 'Trạng thái yêu cầu — vinhlong360',
  ogUrl: () => canonicalUrl('/yeu-cau/trang-thai'),
  twitterCard: 'summary_large_image',
})

useHead(() => ({
  link: [{ rel: 'canonical', href: canonicalUrl('/yeu-cau/trang-thai') }],
}))
</script>

<template>
  <section class="case-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Trạng thái yêu cầu' }]" :json-ld="true" />

    <p v-if="loading" aria-live="polite">Đang tải trạng thái…</p>

    <template v-else-if="cases.status.value">
      <p v-if="failure" class="case-failure" role="alert">{{ failure }}</p>
      <p v-if="reviewRequested" class="case-note" aria-live="polite" data-role="review-sent">
        Đã ghi nhận yêu cầu xem xét lại. Kết quả sẽ có trong lần cập nhật kế tiếp.
      </p>

      <!-- Rotation mints a new one-time key, shown through the same one-time
           card as the original receipt, with the same warning. -->
      <CaseReceiptCard v-if="rotated" :receipt="rotated" @forget="rotated = null" />

      <CaseStatusTimeline :status="cases.status.value" @request-review="requestReview" />

      <div class="case-session-actions">
        <button type="button" class="btn btn-outline" data-role="rotate" @click="rotate">Đổi mã tra cứu mới</button>
        <button type="button" class="btn btn-ghost" data-role="sign-out" @click="signOut">Đóng phiên tra cứu</button>
      </div>
    </template>

    <div v-else class="case-missing">
      <p class="case-failure" role="alert">
        {{ failure || 'Phiên tra cứu chưa mở hoặc đã kết thúc.' }}
      </p>
      <NuxtLink to="/yeu-cau/tra-cuu" class="btn btn-outline">Mở lại bằng mã trên biên nhận</NuxtLink>
    </div>
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
.case-failure {
  padding: 0.75rem 1rem;
  border-radius: var(--radius-control);
  border: 1px solid var(--color-error);
  background: color-mix(in srgb, var(--color-error) 8%, transparent);
  color: var(--ink);
  font-size: var(--text-sm);
}
.case-note {
  margin: 0;
  color: var(--color-source-verified);
}
.case-session-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.case-missing {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-5);
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius-surface);
}
</style>
