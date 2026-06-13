<template>
  <div :class="['modal-overlay', { show: visible }]" @click.self="close">
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title" ref="modalEl">
      <div class="modal-head">
        <h2 id="auth-modal-title">Đăng nhập</h2>
        <button class="modal-close" aria-label="Đóng" @click="close">✕</button>
      </div>
      <div class="modal-body">
        <!-- Step 1: Phone -->
        <div v-if="step === 'phone'" class="otp-step">
          <h3>Nhập số điện thoại</h3>
          <p>Chúng tôi sẽ gửi mã OTP 6 chữ số qua SMS.</p>
          <div class="form-group">
            <input
              v-model="phone"
              class="input"
              type="tel"
              aria-label="Số điện thoại"
              placeholder="0901234567"
              maxlength="11"
              @keyup.enter="sendOtp"
            />
          </div>
          <p v-if="error" class="form-error">{{ error }}</p>
          <label class="consent-row" style="display:flex; gap:8px; align-items:flex-start; margin:12px 0; font-size:.85rem; line-height:1.4;">
            <input v-model="consent" type="checkbox" style="margin-top:3px;" />
            <span>Tôi đồng ý với
              <NuxtLink to="/dieu-khoan-su-dung" target="_blank" @click="close">Điều khoản sử dụng</NuxtLink> và
              <NuxtLink to="/chinh-sach-bao-mat" target="_blank" @click="close">Chính sách bảo mật</NuxtLink>.
            </span>
          </label>
          <button class="btn btn-primary" style="width: 100%" :disabled="sending || !consent" @click="sendOtp">
            {{ sending ? 'Đang gửi…' : 'Gửi mã OTP' }}
          </button>
        </div>

        <!-- Step 2: OTP -->
        <div v-else-if="step === 'otp'" class="otp-step">
          <h3>Nhập mã OTP</h3>
          <p>Đã gửi mã tới {{ phone }}</p>
          <div class="otp-input">
            <input
              v-for="i in 6"
              :key="i"
              :ref="el => { if (el) otpRefs[i - 1] = el as HTMLInputElement }"
              v-model="otpDigits[i - 1]"
              type="text"
              maxlength="1"
              inputmode="numeric"
              :aria-label="`Ô mã OTP số ${i}`"
              @input="onOtpInput(i - 1)"
              @keydown.backspace="onOtpBackspace(i - 1, $event)"
            />
          </div>
          <p v-if="error" class="form-error">{{ error }}</p>
          <button class="btn btn-primary" style="width: 100%" :disabled="sending" @click="verifyCode">
            {{ sending ? 'Đang xác minh…' : 'Xác nhận' }}
          </button>
          <div class="otp-timer">
            <button class="otp-resend" :disabled="countdown > 0" @click="sendOtp">
              {{ countdown > 0 ? `Gửi lại sau ${countdown}s` : 'Gửi lại mã' }}
            </button>
          </div>
        </div>

        <!-- Step 3: Done -->
        <div v-else class="otp-step" style="text-align: center">
          <h3>Đăng nhập thành công!</h3>
          <p>Chào mừng bạn đến với vinhlong360.</p>
          <button class="btn btn-primary" style="width: 100%" @click="close">Đóng</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const { requestOtp, verifyOtp } = useAuth()

const step = ref<'phone' | 'otp' | 'done'>('phone')
const phone = ref('')
const otpDigits = ref(['', '', '', '', '', ''])
const otpRefs = ref<HTMLInputElement[]>([])
const error = ref('')
const sending = ref(false)
const consent = ref(false)  // GĐ5.2: consent bắt buộc (không tick sẵn) trước khi gửi OTP
const countdown = ref(0)
const modalEl = ref<HTMLElement | null>(null)  // GĐ10.3: focus-trap dialog
let countdownTimer: ReturnType<typeof setInterval> | null = null

function close() {
  emit('close')
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
  setTimeout(() => {
    step.value = 'phone'
    error.value = ''
    consent.value = false
    otpDigits.value = ['', '', '', '', '', '']
  }, 300)
}

// GĐ10.3: a11y dialog — Esc đóng + focus-trap + auto-focus khi mở.
function onModalKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') { close(); return }
  if (e.key !== 'Tab' || !modalEl.value) return
  const list = Array.from(
    modalEl.value.querySelectorAll<HTMLElement>('button, [href], input, [tabindex]:not([tabindex="-1"])')
  ).filter(el => !el.hasAttribute('disabled') && el.offsetParent !== null)
  if (!list.length) return
  const first = list[0], last = list[list.length - 1]
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
}

watch(() => props.visible, (v) => {
  if (v) {
    document.addEventListener('keydown', onModalKeydown)
    nextTick(() => modalEl.value?.querySelector<HTMLElement>('input, button')?.focus())
  } else {
    document.removeEventListener('keydown', onModalKeydown)
  }
})

onUnmounted(() => {
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
  document.removeEventListener('keydown', onModalKeydown)
})

async function sendOtp() {
  if (!phone.value || phone.value.length < 9) {
    error.value = 'Vui lòng nhập số điện thoại hợp lệ'
    return
  }
  sending.value = true
  error.value = ''
  try {
    await requestOtp(phone.value)
    step.value = 'otp'
    countdown.value = 60
    if (countdownTimer) clearInterval(countdownTimer)
    countdownTimer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0 && countdownTimer) clearInterval(countdownTimer)
    }, 1000)
    nextTick(() => otpRefs.value[0]?.focus())
  } catch (e: any) {
    error.value = e.data?.detail || 'Lỗi gửi OTP. Thử lại sau.'
  } finally {
    sending.value = false
  }
}

async function verifyCode() {
  const code = otpDigits.value.join('')
  if (code.length !== 6) {
    error.value = 'Vui lòng nhập đủ 6 chữ số'
    return
  }
  sending.value = true
  error.value = ''
  try {
    const res = await verifyOtp(phone.value, code)
    if (res.error) {
      error.value = res.error
    } else {
      step.value = 'done'
    }
  } catch (e: any) {
    error.value = e.data?.detail || 'Mã OTP không đúng.'
  } finally {
    sending.value = false
  }
}

function onOtpInput(idx: number) {
  const val = otpDigits.value[idx]
  if (val && idx < 5) {
    otpRefs.value[idx + 1]?.focus()
  }
  if (otpDigits.value.join('').length === 6) {
    verifyCode()
  }
}

function onOtpBackspace(idx: number, e: KeyboardEvent) {
  if (!otpDigits.value[idx] && idx > 0) {
    otpRefs.value[idx - 1]?.focus()
  }
}
</script>
