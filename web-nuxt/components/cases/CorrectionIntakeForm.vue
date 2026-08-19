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
  proposedValue: string
}

const items = reactive<DraftItem[]>([{ fieldPath: '', reportedValue: '', proposedValue: '' }])
const reporterPrivacy = ref<'anonymous' | 'attributed'>('anonymous')
const optionalPhone = ref('')
const phoneConsent = ref(false)
const handoffConfirmed = ref(false)
const errors = ref<Array<{ anchor: string, message: string }>>([])
const errorSummary = ref<HTMLElement | null>(null)

const canAddItem = computed(() => items.length < 10)

function addItem() {
  if (canAddItem.value) items.push({ fieldPath: '', reportedValue: '', proposedValue: '' })
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
    if (!item.proposedValue.trim()) {
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

function submit() {
  if (!validate()) return
  const payload: CorrectionItemInput[] = items.map(item => ({
    entityId: props.entityId,
    fieldPath: item.fieldPath,
    reportedValue: item.reportedValue.trim(),
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
          <textarea :id="`item-${index}-proposed`" v-model="item.proposedValue" rows="2" maxlength="2000" required />
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

    <!-- A stable action region: the submit button never moves as sections
         reveal, so a thumb mid-reach is never betrayed by a reflow. -->
    <div class="intake-actions">
      <button type="submit" :disabled="busy" data-role="submit">
        {{ busy ? 'Đang gửi…' : 'Gửi yêu cầu sửa' }}
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
  background: var(--surface-muted, #f5f5f4);
}
.intake-errors {
  border: 1px solid var(--color-danger, #b91c1c);
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
  border: 1px solid var(--border-soft, rgba(120, 113, 108, 0.3));
  border-radius: 10px;
  padding: 0.9rem 1rem;
  display: grid;
  gap: 0.7rem;
  min-inline-size: 0;
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
  bottom: calc(var(--bottom-nav-height, 56px) + 0.5rem);
  display: grid;
  gap: 0.3rem;
  background: var(--surface-page, #fff);
  padding-block: 0.5rem;
}
.intake-promise-note {
  margin: 0;
  font-size: 0.85rem;
  color: var(--text-muted, #78716c);
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
