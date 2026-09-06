<script setup lang="ts">
// Taking a correction down the phone, with the consent the file must prove.
//
// The reporter cannot see this screen, so nothing submits until the operator
// has recorded which privacy notice was read out, what the caller consented
// to, and that every value was read back and confirmed in their hearing.
// There is nowhere to paste a recording or a transcript: the pilot keeps none.
import { reactive, ref } from 'vue'

const props = defineProps<{
  privacyNoticeRevision: string
  busy?: boolean
}>()

const emit = defineEmits<{
  (event: 'submit', body: Record<string, unknown>): void
}>()

const channel = ref<'phone' | 'zalo_human'>('phone')
const reporterPrivacy = ref<'anonymous' | 'attributed'>('anonymous')
const noticeReadOut = ref(false)
const reporterConfirmed = ref(false)
const item = reactive({
  entity_id: '',
  field_path: 'attributes.phone',
  reported_value: '',
  proposed_value: '',
  base_entity_revision: 1,
  read_back_confirmed: false,
})

function submit() {
  if (!noticeReadOut.value || !reporterConfirmed.value || !item.read_back_confirmed) return
  emit('submit', {
    channel: channel.value,
    privacy_notice_revision: props.privacyNoticeRevision,
    consent_scope: 'correction.contact',
    consent_given_at: new Date().toISOString(),
    reporter_privacy: reporterPrivacy.value,
    reporter_confirmed: reporterConfirmed.value,
    items: [{ ...item }],
  })
}
</script>

<template>
  <form class="assisted-form" data-role="assisted-form" @submit.prevent="submit">
    <h3>Ghi hộ qua điện thoại / Zalo</h3>

    <label>Kênh
      <select v-model="channel">
        <option value="phone">Điện thoại</option>
        <option value="zalo_human">Zalo (người thật)</option>
      </select>
    </label>

    <label class="assisted-consent" data-role="notice-consent">
      <input v-model="noticeReadOut" type="checkbox" required>
      Tôi đã đọc cho người gọi nghe thông báo quyền riêng tư
      <strong>{{ privacyNoticeRevision }}</strong> và họ đồng ý phạm vi
      “chỉ dùng để xử lý yêu cầu sửa”.
    </label>

    <fieldset class="assisted-item">
      <legend>Nội dung người gọi báo</legend>
      <label>Mã địa điểm
        <input v-model="item.entity_id" type="text" required>
      </label>
      <label>Trường cần sửa
        <select v-model="item.field_path">
          <option value="attributes.phone">Số điện thoại</option>
          <option value="attributes.address">Địa chỉ</option>
          <option value="attributes.opening_hours">Giờ mở cửa</option>
          <option value="name">Tên hiển thị</option>
        </select>
      </label>
      <label>Trang đang ghi
        <textarea v-model="item.reported_value" rows="2" maxlength="2000" />
      </label>
      <label>Người gọi nói đúng là
        <textarea v-model="item.proposed_value" rows="2" maxlength="2000" required />
      </label>
      <label class="assisted-consent" data-role="read-back">
        <input v-model="item.read_back_confirmed" type="checkbox" required>
        Tôi đã đọc lại giá trị này cho người gọi và họ xác nhận đúng.
      </label>
    </fieldset>

    <label class="assisted-consent" data-role="reporter-confirmed">
      <input v-model="reporterConfirmed" type="checkbox" required>
      Người gọi đồng ý gửi yêu cầu này.
    </label>

    <button type="submit" :disabled="busy || !noticeReadOut || !reporterConfirmed || !item.read_back_confirmed">
      Gửi thay người gọi
    </button>
    <p class="assisted-note">
      Người gọi sẽ nhận mã tra cứu qua kênh họ chọn. Mã một lần không hiển thị
      cho người trực.
    </p>
  </form>
</template>

<style scoped>
.assisted-form {
  display: grid;
  gap: 0.7rem;
}
.assisted-form label {
  display: grid;
  gap: 0.2rem;
}
.assisted-consent {
  display: flex !important;
  gap: 0.5rem;
  align-items: flex-start;
}
.assisted-item {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 0.8rem 1rem;
  display: grid;
  gap: 0.6rem;
}
.assisted-note {
  margin: 0;
  font-size: 0.85rem;
  color: var(--muted);
}
</style>
