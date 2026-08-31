<script setup lang="ts">
// Reporting a mistake, one field at a time.
//
// The form asks for exactly what the kernel records: which entry, which field,
// what the page says now, what it should say. Nothing here is a secret, and the
// submit event carries structured fields only — transport, keys and cookies are
// the composable's problem, never this component's.
//
// A phone number is optional and consent-gated: it is a reply address, not an
// identity, and the checkbox says so in the reporter's language.
import { computed, reactive, ref } from 'vue'

import type { CorrectionItemInput, CorrectionSubmission } from '../../types/cases'

const props = defineProps<{
  entityId: string
  entityName: string
  baseEntityRevision: number
  /** Present only when a Zalo AI conversation handed this form its context. */
  handoffDigest?: string | null
  /** Configured support hours, shown only when the deployment provides them. */
  assistedHours?: string | null
  /** A convenience hint from the entry link; anything unrecognised is ignored. */
  initialFieldPath?: string | null
  busy?: boolean
}>()

const emit = defineEmits<{
  (event: 'submit', submission: CorrectionSubmission): void
  (event: 'request-phone-verification', phone: string): void
}>()

// The fields the kernel accepts, in the reporter's words.
const FIELD_CHOICES = [
  { path: 'attributes.phone', label: 'Số điện thoại' },
  { path: 'attributes.address', label: 'Địa chỉ' },
  { path: 'attributes.opening_hours', label: 'Giờ mở cửa' },
  { path: 'attributes.website', label: 'Trang web' },
  { path: 'attributes.price_range', label: 'Khoảng giá' },
  { path: 'name', label: 'Tên hiển thị' },
  { path: 'summary', label: 'Đoạn giới thiệu ngắn' },
  { path: 'description', label: 'Bài mô tả' },
] as const

interface DraftItem {
  fieldPath: string
  reportedValue: string
  reportedValueKnown: boolean
  proposedValue: string
}

const initialField = FIELD_CHOICES.some(choice => choice.path === props.initialFieldPath)
  ? String(props.initialFieldPath)
  : ''
const items = reactive<DraftItem[]>([
  { fieldPath: initialField, reportedValue: '', reportedValueKnown: true, proposedValue: '' },
])
const reporterPrivacy = ref<'anonymous' | 'attributed'>('anonymous')
const optionalPhone = ref('')
const phoneConsent = ref(false)
const handoffConfirmed = ref(false)
const errors = ref<Array<{ anchor: string, message: string }>>([])
// Tra lỗi theo neo, để chính ô nhập nói được nó sai gì thay vì bắt người dùng
// quay lại bảng tóm tắt.
function errorFor(anchor: string): string | undefined {
  return errors.value.find(e => e.anchor === anchor)?.message
}
function hasError(anchor: string): boolean {
  return errors.value.some(e => e.anchor === anchor)
}
const errorSummary = ref<HTMLElement | null>(null)

const canAddItem = computed(() => items.length < 10)

function addItem() {
  if (canAddItem.value) items.push({ fieldPath: '', reportedValue: '', reportedValueKnown: true, proposedValue: '' })
}

function removeItem(index: number) {
  if (items.length > 1) items.splice(index, 1)
}

function validate(): boolean {
  const found: Array<{ anchor: string, message: string }> = []
  items.forEach((item, index) => {
    if (!item.fieldPath) {
      found.push({ anchor: `item-${index}-field`, message: `Mục ${index + 1}: chọn thông tin cần sửa.` })
    }
    // Điều kiện item.fieldPath là BẮT BUỘC: hai textarea nằm trong
    // `<template v-if="item.fieldPath">`, nên với mục chưa chọn loại thông tin,
    // id `item-N-proposed` KHÔNG có trong DOM — link trong bảng tóm tắt lỗi bấm
    // vào không đi đâu cả. Khi chưa chọn thì lỗi "chọn thông tin cần sửa" ở trên
    // đã đủ và trỏ đúng chỗ.
    if (item.fieldPath && !item.proposedValue.trim()) {
      found.push({ anchor: `item-${index}-proposed`, message: `Mục ${index + 1}: ghi nội dung đúng.` })
    }
  })
  if (optionalPhone.value.trim() && !phoneConsent.value) {
    found.push({
      anchor: 'phone-consent',
      message: 'Đánh dấu đồng ý để chúng tôi được dùng số điện thoại này báo kết quả.',
    })
  }
  if (props.handoffDigest && !handoffConfirmed.value) {
    found.push({
      anchor: 'handoff-confirm',
      message: 'Xác nhận nội dung chuyển từ trợ lý Zalo trước khi gửi.',
    })
  }
  errors.value = found
  if (found.length) {
    // The summary receives focus so a keyboard or screen-reader user lands on
    // the list of what to fix, with links into the fields themselves.
    requestAnimationFrame(() => errorSummary.value?.focus())
  }
  return found.length === 0
}

// WCAG 2.2 SC 3.3.4 Error Prevention (Legal, Financial, Data), Level AA. It is
// triggered here not because money changes hands but because this submission
// modifies user-controllable data in a storage system. The criterion is
// disjunctive — reversible, checked, or confirmed — and a review-and-confirm
// step alone satisfies it. Claiming AA without one would be claiming wrongly.
const reviewing = ref(false)

function requestReview() {
  if (!validate()) return
  reviewing.value = true
}

function submit() {
  if (!validate()) return
  const payload: CorrectionItemInput[] = items.map(item => ({
    entityId: props.entityId,
    fieldPath: item.fieldPath,
    reportedValue: item.reportedValue.trim(),
    reportedValueKnown: item.reportedValueKnown,
    proposedValue: item.proposedValue.trim(),
    baseEntityRevision: props.baseEntityRevision,
  }))
  emit('submit', {
    reporterPrivacy: reporterPrivacy.value,
    items: payload,
    optionalPhone: phoneConsent.value && optionalPhone.value.trim()
      ? optionalPhone.value.trim()
      : null,
    notificationConsent: phoneConsent.value && Boolean(optionalPhone.value.trim()),
    handoffDigest: props.handoffDigest ?? null,
    handoffConfirmed: props.handoffDigest ? handoffConfirmed.value : false,
  })
}
</script>

<template>
  <form class="intake-form" novalidate @submit.prevent="submit">
    <!-- Safety routing first, in plain words. We are editors, not responders:
         the copy sends danger to the people who answer it, and claims nothing. -->
    <p class="intake-safety" data-role="urgent-routing">
      Nếu có tình huống nguy hiểm hoặc khẩn cấp, hãy gọi cơ quan chức năng
      (113/114/115). Trang này chỉ tiếp nhận sửa thông tin hiển thị trên vinhlong360.
    </p>

    <p v-if="assistedHours" class="intake-assisted" data-role="assisted-hours">
      Cần người hỗ trợ điền thay? Gọi trong giờ hỗ trợ: {{ assistedHours }}.
    </p>

    <div
      v-if="errors.length"
      ref="errorSummary"
      class="intake-errors"
      role="alert"
      tabindex="-1"
      data-role="error-summary"
    >
      <h3>Cần bổ sung trước khi gửi</h3>
      <ul>
        <li v-for="error in errors" :key="error.anchor">
          <a :href="`#${error.anchor}`">{{ error.message }}</a>
        </li>
      </ul>
    </div>

    <fieldset
      v-for="(item, index) in items"
      :key="index"
      class="intake-item"
      :data-role="`item-card-${index}`"
    >
      <legend>Nội dung cần sửa {{ items.length > 1 ? index + 1 : '' }} — {{ entityName }}</legend>

      <div class="intake-field">
        <label :for="`item-${index}-field`">Thông tin nào chưa đúng?</label>
        <select :id="`item-${index}-field`" v-model="item.fieldPath" required>
          <option value="" disabled>Chọn thông tin</option>
          <option v-for="choice in FIELD_CHOICES" :key="choice.path" :value="choice.path">
            {{ choice.label }}
          </option>
        </select>
      </div>

      <!-- Progressive: the value fields appear once the reader has said which
           field is wrong, so the empty form asks one question, not six. -->
      <template v-if="item.fieldPath">
        <div class="intake-field">
          <label :for="`item-${index}-reported`">Trang đang ghi (chép lại giúp chúng tôi)</label>
          <textarea :id="`item-${index}-reported`" v-model="item.reportedValue" rows="2" maxlength="2000" />
        </div>
        <div class="intake-field">
          <label :for="`item-${index}-proposed`">Thông tin đúng là</label>
          <textarea
            :id="`item-${index}-proposed`"
            v-model="item.proposedValue"
            rows="2"
            maxlength="2000"
            required
            :aria-invalid="hasError(`item-${index}-proposed`) || undefined"
            :aria-describedby="hasError(`item-${index}-proposed`) ? `item-${index}-proposed-error` : undefined"
          />
          <!-- Nhảy tới đúng ô mà bản thân ô không nói nó sai gì thì người dùng
               trình đọc màn hình vẫn phải quay lại bảng tóm tắt để biết lý do. -->
          <p
            v-if="hasError(`item-${index}-proposed`)"
            :id="`item-${index}-proposed-error`"
            class="intake-field-error"
          >{{ errorFor(`item-${index}-proposed`) }}</p>
        </div>
      </template>

      <button v-if="items.length > 1" type="button" class="intake-remove" @click="removeItem(index)">
        Bỏ mục này
      </button>
    </fieldset>

    <button v-if="canAddItem" type="button" class="intake-add" @click="addItem">
      Thêm nội dung khác của cùng địa điểm
    </button>

    <fieldset class="intake-privacy">
      <legend>Hiển thị người gửi</legend>
      <label>
        <input v-model="reporterPrivacy" type="radio" value="anonymous" name="reporter-privacy">
        Ẩn danh
      </label>
      <label>
        <input v-model="reporterPrivacy" type="radio" value="attributed" name="reporter-privacy">
        Ghi nhận tôi là người gửi
      </label>
    </fieldset>

    <fieldset class="intake-contact">
      <legend>Nhận kết quả (không bắt buộc)</legend>
      <div class="intake-field">
        <label for="optional-phone">Số điện thoại (chỉ để báo kết quả)</label>
        <input id="optional-phone" v-model="optionalPhone" type="tel" inputmode="tel" maxlength="32">
      </div>
      <label v-if="optionalPhone.trim()" id="phone-consent" class="intake-consent">
        <input v-model="phoneConsent" type="checkbox">
        Tôi đồng ý cho vinhlong360 dùng số này để báo kết quả yêu cầu, và chỉ việc đó.
      </label>
      <button
        v-if="optionalPhone.trim() && phoneConsent"
        type="button"
        data-role="verify-phone"
        @click="emit('request-phone-verification', optionalPhone.trim())"
      >
        Gửi mã xác nhận số điện thoại
      </button>
    </fieldset>

    <fieldset v-if="handoffDigest" class="intake-handoff" data-role="handoff">
      <legend>Nội dung từ trợ lý Zalo</legend>
      <label id="handoff-confirm" class="intake-consent">
        <input v-model="handoffConfirmed" type="checkbox">
        Tôi xác nhận nội dung trợ lý ghi lại đúng ý tôi. Chưa xác nhận thì chưa gửi.
      </label>
    </fieldset>

    <section
      v-if="reviewing"
      class="intake-review"
      role="group"
      aria-labelledby="review-heading"
      data-role="review-panel"
    >
      <h2 id="review-heading">Xem lại trước khi gửi</h2>
      <ul class="intake-review-list">
        <li v-for="(item, index) in items" :key="`review-${index}`">
          <strong>{{ FIELD_CHOICES.find(f => f.path === item.fieldPath)?.label ?? item.fieldPath }}</strong>
          <span data-role="review-reported">Hiện tại: {{ item.reportedValue.trim() || '—' }}</span>
          <span data-role="review-proposed">Sửa thành: {{ item.proposedValue.trim() }}</span>
        </li>
      </ul>
      <p v-if="optionalPhone.trim() && phoneConsent" data-role="review-phone">
        Báo kết quả về số {{ optionalPhone.trim() }} — và chỉ việc đó.
      </p>
      <p v-else data-role="review-no-phone">Không để lại số điện thoại.</p>
      <button type="button" data-role="review-back" @click="reviewing = false">
        Quay lại sửa
      </button>
    </section>

    <!-- A stable action region: the submit button never moves as sections
         reveal, so a thumb mid-reach is never betrayed by a reflow. -->
    <div class="intake-actions">
      <button
        v-if="!reviewing"
        type="button"
        :disabled="busy"
        data-role="review"
        @click="requestReview"
      >
        Xem lại trước khi gửi
      </button>
      <button v-else type="submit" :disabled="busy" data-role="submit">
        {{ busy ? 'Đang gửi…' : 'Xác nhận gửi yêu cầu' }}
      </button>
      <p class="intake-promise-note">
        Sau khi gửi, bạn nhận mã tra cứu và mốc cập nhật kế tiếp.
      </p>
    </div>
  </form>
</template>

<style scoped>
.intake-form {
  display: grid;
  gap: 1rem;
  /* One column always: at 320px and 200% text there is nothing to collapse. */
  grid-template-columns: minmax(0, 1fr);
}
.intake-safety {
  margin: 0;
  padding: 0.6rem 0.8rem;
  border-radius: 8px;
  background: var(--bg-alt);
}
.intake-errors {
  border: 1px solid var(--color-error);
  border-radius: 8px;
  padding: 0.75rem 1rem;
}
.intake-errors h3 {
  margin: 0 0 0.4rem;
}
.intake-errors ul {
  margin: 0;
  padding-left: 1.1rem;
}
fieldset {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.9rem 1rem;
  display: grid;
  gap: 0.7rem;
  min-inline-size: 0;
}
.intake-field-error {
  margin: var(--space-1) 0 0;
  font-size: var(--text-xs);
  color: var(--color-error);
}
.intake-field textarea[aria-invalid="true"] {
  border-color: var(--color-error);
}
.intake-field {
  display: grid;
  gap: 0.25rem;
}
.intake-field select,
.intake-field textarea,
.intake-field input {
  max-inline-size: 100%;
}
.intake-consent {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
}
.intake-actions {
  position: sticky;
  bottom: calc(var(--shell-public-bottom-nav-reserved-height) + 0.5rem);
  display: grid;
  gap: 0.3rem;
  background: var(--bg);
  padding-block: 0.5rem;
}
.intake-promise-note {
  margin: 0;
  font-size: 0.85rem;
  color: var(--muted);
}

@media (prefers-reduced-motion: no-preference) {
  .intake-item {
    animation: card-reveal 200ms ease-out both;
  }
  @keyframes card-reveal {
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
