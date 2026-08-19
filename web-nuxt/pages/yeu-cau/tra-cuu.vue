<script setup lang="ts">
// Opening a case with the receipt: reference plus one-time key, once.
//
// Both values travel in a POST body. The page never puts either into the URL,
// so neither reaches history or logs, and a success navigates on to a status
// page that runs entirely on the cookie the exchange set.
import { ref } from 'vue'

import { CaseAccessError, useCorrectionCases } from '../../composables/useCorrectionCases'

const cases = useCorrectionCases()
const router = useRouter()

const reference = ref('')
const capability = ref('')
const busy = ref(false)
const failure = ref('')

async function open() {
  busy.value = true
  failure.value = ''
  try {
    await cases.exchangeReceipt(reference.value.trim(), capability.value.trim())
    // The key has done its one job; nothing downstream needs it.
    capability.value = ''
    await router.push('/yeu-cau/trang-thai')
  } catch (error) {
    // One message for every way the pair can fail: which half was wrong is
    // exactly what a guesser wants confirmed.
    failure.value = error instanceof CaseAccessError
      ? error.message
      : 'Chưa tra cứu được. Vui lòng thử lại sau ít phút.'
  } finally {
    busy.value = false
  }
}

useSeoMeta({
  title: 'Tra cứu yêu cầu — vinhlong360',
  description: 'Tra cứu tiến trình xử lý yêu cầu sửa thông tin bằng mã trên biên nhận.',
})
</script>

<template>
  <section class="case-page">
    <Breadcrumb :items="[{ label: 'Trang chủ', to: '/' }, { label: 'Tra cứu yêu cầu' }]" />

    <header class="case-header">
      <h1>Tra cứu yêu cầu</h1>
      <p class="case-trust-note">Dùng hai mã trên biên nhận bạn đã lưu khi gửi yêu cầu.</p>
    </header>

    <form class="case-lookup" novalidate @submit.prevent="open">
      <p v-if="failure" class="case-failure" role="alert" data-role="lookup-failure">
        {{ failure }}
      </p>

      <div class="case-field">
        <label for="lookup-reference">Mã tra cứu</label>
        <input
          id="lookup-reference"
          v-model="reference"
          type="text"
          autocomplete="off"
          spellcheck="false"
          required
        >
      </div>
      <div class="case-field">
        <label for="lookup-capability">Mã một lần</label>
        <!-- A password field in behaviour, not in meaning: hidden from
             shoulders, excluded from autofill and password managers. -->
        <input
          id="lookup-capability"
          v-model="capability"
          type="password"
          autocomplete="off"
          spellcheck="false"
          required
        >
      </div>

      <div class="case-actions">
        <button type="submit" :disabled="busy || !reference.trim() || !capability.trim()">
          {{ busy ? 'Đang mở…' : 'Mở yêu cầu' }}
        </button>
      </div>
    </form>
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
.case-lookup {
  display: grid;
  gap: 0.9rem;
}
.case-field {
  display: grid;
  gap: 0.25rem;
}
.case-failure {
  padding: 0.6rem 0.8rem;
  border-radius: 8px;
  border: 1px solid var(--color-danger, #b91c1c);
}
</style>
