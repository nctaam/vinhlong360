<template>
  <div :class="['modal-overlay', { show: visible }]" @click.self="close">
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title" ref="modalEl">
      <div class="modal-head">
        <h2 id="auth-modal-title">{{ modalTitle }}</h2>
        <button type="button" class="modal-close" aria-label="Đóng" @click="close">✕</button>
      </div>
      <div class="modal-body">
        <!-- Step 1: Phone -->
        <div v-if="step === 'phone'" class="otp-step">
          <h3>Nhập số điện thoại</h3>
          <p>Nhập SĐT để đăng nhập hoặc tạo tài khoản mới.</p>
          <div class="form-group">
            <input
              v-model="phone"
              class="input"
              :class="{ error: error && step === 'phone' }"
              :aria-invalid="!!(error && step === 'phone')"
              type="tel"
              inputmode="tel"
              autocomplete="tel"
              aria-label="Số điện thoại"
              placeholder="0901234567"
              maxlength="11"
              @keyup.enter="handlePhone"
            />
          </div>
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <label class="consent-row">
            <input v-model="consent" type="checkbox" class="consent-checkbox" />
            <span>Tôi đồng ý với
              <NuxtLink to="/dieu-khoan-su-dung" @click="close">Điều khoản sử dụng</NuxtLink> và
              <NuxtLink to="/chinh-sach-bao-mat" @click="close">Chính sách bảo mật</NuxtLink>.
            </span>
          </label>
          <button type="button" class="btn btn-primary btn-full" :disabled="sending || !consent" @click="handlePhone">
            {{ sending ? 'Đang kiểm tra…' : 'Tiếp tục' }}
          </button>
        </div>

        <!-- Step: Password login (returning user) -->
        <div v-else-if="step === 'password'" class="otp-step">
          <h3>Nhập mật khẩu</h3>
          <p>Đăng nhập cho {{ phone }}</p>
          <div class="form-group">
            <input
              v-model="password"
              class="input"
              :class="{ error: error && step === 'password' }"
              :aria-invalid="!!(error && step === 'password')"
              type="password"
              autocomplete="current-password"
              aria-label="Mật khẩu"
              placeholder="Mật khẩu"
              @keyup.enter="handleLogin"
            />
          </div>
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <button type="button" class="btn btn-primary btn-full" :disabled="sending" @click="handleLogin">
            {{ sending ? 'Đang đăng nhập…' : 'Đăng nhập' }}
          </button>
          <button type="button" class="otp-resend" @click="forgotPassword">Quên mật khẩu?</button>
          <button type="button" class="otp-resend" @click="step = 'phone'">Đổi số điện thoại</button>
        </div>

        <!-- Step: OTP input -->
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
              autocomplete="one-time-code"
              :aria-label="`Ô mã OTP số ${i}`"
              @input="onOtpInput(i - 1)"
              @keydown.backspace="onOtpBackspace(i - 1, $event)"
              @paste="onOtpPaste"
            />
          </div>
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <button type="button" class="btn btn-primary btn-full" :disabled="sending" @click="verifyCode">
            {{ sending ? 'Đang xác minh…' : 'Xác nhận' }}
          </button>
          <div class="otp-timer">
            <button type="button" class="otp-resend" :disabled="countdown > 0" @click="sendOtp">
              {{ countdown > 0 ? `Gửi lại sau ${countdown}s` : 'Gửi lại mã' }}
            </button>
          </div>
        </div>

        <!-- Step: Set password (after first OTP verification) -->
        <div v-else-if="step === 'set-password'" class="otp-step">
          <h3>Đặt mật khẩu</h3>
          <p>Tạo mật khẩu để lần sau đăng nhập nhanh hơn (không cần OTP).</p>
          <div class="form-group">
            <input
              v-model="newPassword"
              class="input"
              :class="{ error: error && step === 'set-password' }"
              :aria-invalid="!!(error && step === 'set-password')"
              type="password"
              autocomplete="new-password"
              aria-label="Mật khẩu mới"
              placeholder="Mật khẩu (tối thiểu 6 ký tự)"
              @keyup.enter="handleSetPassword"
            />
          </div>
          <div class="form-group">
            <input
              v-model="confirmPassword"
              class="input"
              type="password"
              autocomplete="new-password"
              aria-label="Xác nhận mật khẩu"
              placeholder="Nhập lại mật khẩu"
              @keyup.enter="handleSetPassword"
            />
          </div>
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <button type="button" class="btn btn-primary btn-full" :disabled="sending" @click="handleSetPassword">
            {{ sending ? 'Đang lưu…' : 'Đặt mật khẩu' }}
          </button>
          <button type="button" class="otp-resend" @click="step = 'done'">Bỏ qua, để sau</button>
        </div>

        <!-- Step: Done -->
        <div v-else class="otp-step otp-done">
          <h3>Đăng nhập thành công!</h3>
          <p>Chào mừng bạn đến với vinhlong360.</p>
          <button type="button" class="btn btn-primary btn-full" @click="close">Đóng</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const { requestOtp, verifyOtp, checkPhone, login, setPassword } = useAuth()

const step = ref<'phone' | 'password' | 'otp' | 'set-password' | 'done'>('phone')
const phone = ref('')
const password = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const otpDigits = ref(['', '', '', '', '', ''])
const otpRefs = ref<HTMLInputElement[]>([])
const error = ref('')
const sending = ref(false)
const consent = ref(false)
const countdown = ref(0)
const modalEl = ref<HTMLElement | null>(null)
const isResetFlow = ref(false)
let countdownTimer: ReturnType<typeof setInterval> | null = null

const modalTitle = computed(() => {
  if (step.value === 'set-password') return 'Đặt mật khẩu'
  if (step.value === 'done') return 'Thành công'
  return 'Đăng nhập'
})

function close() {
  emit('close')
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
  setTimeout(() => {
    step.value = 'phone'
    error.value = ''
    consent.value = false
    password.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    isResetFlow.value = false
    otpDigits.value = ['', '', '', '', '', '']
  }, 300)
}

// Body-scroll lock, focus trap, Escape-to-close + focus restore (SSR-safe).
const visibleRef = computed(() => props.visible)
useModalA11y(visibleRef, modalEl, { onClose: close })

onUnmounted(() => {
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
})

async function handlePhone() {
  if (!phone.value || phone.value.length < 9) {
    error.value = 'Vui lòng nhập số điện thoại hợp lệ'
    return
  }
  sending.value = true
  error.value = ''
  try {
    const res = await checkPhone(phone.value)
    if (res.has_password) {
      step.value = 'password'
    } else {
      await sendOtp()
    }
  } catch (e: unknown) {
    error.value = e.data?.detail || 'Lỗi kiểm tra số điện thoại'
  } finally {
    sending.value = false
  }
}

async function handleLogin() {
  if (!password.value) {
    error.value = 'Vui lòng nhập mật khẩu'
    return
  }
  sending.value = true
  error.value = ''
  try {
    await login(phone.value, password.value)
    step.value = 'done'
  } catch (e: unknown) {
    error.value = e.data?.detail || 'Số điện thoại hoặc mật khẩu không đúng'
  } finally {
    sending.value = false
  }
}

function forgotPassword() {
  isResetFlow.value = true
  error.value = ''
  sendOtp()
}

async function sendOtp() {
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
  } catch (e: unknown) {
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
    const res = await verifyOtp(phone.value, code, consent.value)
    if (res.error) {
      error.value = res.error
    } else {
      if (res.has_password && !isResetFlow.value) {
        step.value = 'done'
      } else {
        step.value = 'set-password'
      }
    }
  } catch (e: unknown) {
    error.value = e.data?.detail || 'Mã OTP không đúng.'
    otpDigits.value = ['', '', '', '', '', '']
    nextTick(() => otpRefs.value[0]?.focus())
  } finally {
    sending.value = false
  }
}

async function handleSetPassword() {
  if (!newPassword.value || newPassword.value.length < 6) {
    error.value = 'Mật khẩu phải từ 6 ký tự trở lên'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = 'Mật khẩu nhập lại không khớp'
    return
  }
  sending.value = true
  error.value = ''
  try {
    await setPassword(newPassword.value)
    step.value = 'done'
  } catch (e: unknown) {
    error.value = e.data?.detail || 'Lỗi đặt mật khẩu'
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

function onOtpPaste(e: ClipboardEvent) {
  const text = (e.clipboardData?.getData('text') || '').replace(/\D/g, '').slice(0, 6)
  if (!text) return
  e.preventDefault()
  const digits = text.split('')
  for (let i = 0; i < 6; i++) otpDigits.value[i] = digits[i] || ''
  const last = Math.max(0, Math.min(text.length, 6) - 1)
  nextTick(() => otpRefs.value[last]?.focus())
  if (text.length === 6) verifyCode()
}
</script>

<style scoped>
.consent-row { display: flex; gap: var(--space-3); align-items: flex-start; margin: var(--space-3) 0; font-size: var(--text-sm); line-height: var(--leading-relaxed); cursor: pointer; padding: var(--space-3); border-radius: var(--radius-md); transition: background .3s var(--ease-out); }
.consent-row:hover { background: var(--bg-alt); }
.consent-checkbox { margin-top: 3px; width: 18px; height: 18px; accent-color: var(--primary); flex-shrink: 0; }
.btn-full { width: 100%; }
.otp-done { text-align: center; }
.otp-done h3 { animation: successPop .45s var(--ease-spring-gentle); }
@keyframes successPop { 0% { transform: scale(.85); opacity: 0; } 60% { transform: scale(1.06); } 100% { transform: scale(1); opacity: 1; } }
.otp-step { animation: stepSlideIn .35s var(--ease-out-expo); }
@keyframes stepSlideIn { from { opacity: 0; transform: translateX(14px); } to { opacity: 1; transform: translateX(0); } }
@media (prefers-reduced-motion: reduce) {
  .otp-done h3 { animation: none; }
  .otp-step { animation: none; }
}
</style>
