<script setup lang="ts">
// The one screen that ever shows the reporter's key.
//
// The reference is theirs to keep and print. The capability is shown once, with
// the warning beside it rather than behind a link, and the component asks to be
// forgotten the moment the person says they have saved it. It never touches
// storage; the parent holds it in a ref that dies with the page.
import { computed, ref } from 'vue'

import type { CaseReceipt } from '../../types/cases'

const props = defineProps<{ receipt: CaseReceipt }>()
const emit = defineEmits<{ (event: 'forget'): void }>()

const acknowledged = ref(false)
const copied = ref(false)

const receivedOn = computed(() => new Date(props.receipt.receivedAt).toLocaleString('vi-VN'))
const nextUpdate = computed(() => new Date(props.receipt.nextUpdateAt).toLocaleString('vi-VN'))

async function copyCapability() {
  try {
    await navigator.clipboard.writeText(props.receipt.capability)
    copied.value = true
  } catch {
    // Selection stays possible; the value is on screen precisely once.
    copied.value = false
  }
}

function confirmSaved() {
  acknowledged.value = true
  // Their acknowledgement is the signal the key may leave memory.
  emit('forget')
}
</script>

<template>
  <section class="receipt-card" aria-labelledby="receipt-heading">
    <h2 id="receipt-heading">Biên nhận yêu cầu</h2>

    <div class="receipt-reference">
      <p class="receipt-label">Mã tra cứu (giữ lại, in được)</p>
      <p class="receipt-value" data-role="public-reference">{{ receipt.publicReference }}</p>
    </div>

    <p v-if="receipt.replayed" class="receipt-replayed">
      Yêu cầu này đã được ghi nhận trước đó; đây là biên nhận ban đầu của bạn.
    </p>

    <div v-if="!acknowledged" class="receipt-secret print-hidden">
      <p class="receipt-label">Mã một lần</p>
      <p class="receipt-value receipt-capability" data-role="capability">{{ receipt.capability }}</p>
      <!-- The warning sits beside the value, not behind a link: the reader must
           meet it before the value is gone. -->
      <p class="receipt-warning" role="alert">
        Mã này chỉ hiển thị <strong>một lần duy nhất</strong>. Hãy lưu lại trước khi rời trang —
        chúng tôi không lưu bản gốc và không thể cấp lại mã cũ.
      </p>
      <div class="receipt-actions">
        <button type="button" class="btn btn-primary btn-sm" @click="copyCapability">Sao chép mã</button>
        <button type="button" class="btn btn-outline btn-sm" data-role="confirm-saved" @click="confirmSaved">
          Tôi đã lưu mã
        </button>
      </div>
      <p v-if="copied" class="receipt-copied" aria-live="polite">Đã sao chép.</p>
    </div>
    <p v-else class="receipt-secret-gone" data-role="capability-gone">
      Mã một lần đã được ẩn. Dùng mã tra cứu cùng mã đã lưu để xem trạng thái.
    </p>

    <dl class="receipt-meta">
      <div><dt>Tiếp nhận lúc</dt><dd>{{ receivedOn }}</dd></div>
      <div><dt>Cập nhật kế tiếp trước</dt><dd>{{ nextUpdate }}</dd></div>
    </dl>
  </section>
</template>

<style scoped>
.receipt-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-surface);
  padding: 1.25rem;
  display: grid;
  gap: 0.9rem;
}
.receipt-label {
  margin: 0;
  font-size: 0.8rem;
  color: var(--muted);
}
.receipt-value {
  margin: 0.15rem 0 0;
  font-family: var(--font-mono);
  font-size: 1.05rem;
  overflow-wrap: anywhere;
}
.receipt-warning {
  margin: 0.5rem 0 0;
  padding: 0.6rem 0.8rem;
  border-radius: var(--radius-control);
  background: var(--bg-warm);
  color: var(--color-warning);
}
.receipt-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.receipt-meta {
  display: grid;
  gap: 0.4rem;
  margin: 0;
}
.receipt-meta dt {
  font-size: 0.8rem;
  color: var(--muted);
}
.receipt-meta dd {
  margin: 0;
}

/* The paper copy carries the reference and the meta. The one-time secret is
   deliberately excluded: paper outlives screens, and a printed key is a key
   left on a desk. */
@media print {
  .print-hidden {
    display: none !important;
  }
  .receipt-card {
    border: 1px solid rgb(var(--black-rgb));
  }
}
</style>
