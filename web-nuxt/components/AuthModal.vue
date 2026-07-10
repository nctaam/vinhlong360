<template>
  <Transition name="modal-fade">
  <div v-if="visible" class="modal-overlay show" @click.self="close">
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title" ref="modalEl">
      <div class="modal-head modal-head-editorial">
        <div class="modal-head-text">
          <span class="modal-eyebrow">Vinhlong360 · Sổ tay hành trình</span>
          <h2 id="auth-modal-title">{{ modalTitle }}</h2>
        </div>
        <button type="button" class="modal-close" aria-label="Đóng" @click="close">✕</button>
      </div>
      <span class="modal-rule" aria-hidden="true"></span>
      <div class="modal-body">
        <!-- Step 1: Phone -->
        <div v-if="step === 'phone'" class="otp-step">
          <h3 tabindex="-1" class="step-label">Nhập số điện thoại</h3>
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

        <!-- Step: Register (new user fills info before OTP) -->
        <div v-else-if="step === 'register'" class="otp-step">
          <h3 tabindex="-1" class="step-label">Tạo tài khoản</h3>
          <p>Hoàn tất thông tin để đăng ký cho {{ phone }}</p>
          <div class="form-group">
            <label class="form-label">Họ và tên <span class="required">*</span></label>
            <input
              v-model="regFullName"
              class="input"
              type="text"
              autocomplete="name"
              placeholder="Nguyễn Văn A"
              maxlength="100"
            />
          </div>
          <div class="form-group">
            <label class="form-label">Ngày sinh</label>
            <input
              v-model="regDob"
              class="input"
              type="date"
              autocomplete="bday"
              :max="maxDob"
            />
          </div>
          <div class="form-group">
            <label class="form-label">Username <span class="required">*</span></label>
            <input
              v-model="regUsername"
              class="input"
              type="text"
              autocomplete="username"
              placeholder="nguyenvana"
              maxlength="30"
              @blur="checkUsernameAvail"
            />
            <p v-if="usernameStatus === 'taken'" class="form-error">Username đã được sử dụng</p>
            <p v-else-if="usernameStatus === 'invalid'" class="form-error">Username 3–30 ký tự, bắt đầu bằng chữ, chỉ gồm chữ/số/dấu chấm/gạch ngang</p>
            <p v-else-if="usernameStatus === 'available'" class="form-success">Username khả dụng</p>
          </div>
          <div class="form-group">
            <label class="form-label">Mật khẩu <span class="required">*</span></label>
            <input
              v-model="regPassword"
              class="input"
              type="password"
              autocomplete="new-password"
              placeholder="Tối thiểu 8 ký tự, có chữ và số"
              maxlength="128"
            />
          </div>
          <div class="form-group">
            <label class="form-label">Xác nhận mật khẩu <span class="required">*</span></label>
            <input
              v-model="regPasswordConfirm"
              class="input"
              type="password"
              autocomplete="new-password"
              placeholder="Nhập lại mật khẩu"
              maxlength="128"
            />
          </div>
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <button type="button" class="btn btn-primary btn-full" :disabled="sending" @click="handleRegister">
            {{ sending ? 'Đang gửi OTP…' : 'Xác minh số điện thoại' }}
          </button>
          <button type="button" class="otp-resend" @click="error = ''; step = 'phone'">Đổi số điện thoại</button>
        </div>

        <!-- Step: Password login (returning user) -->
        <div v-else-if="step === 'password'" class="otp-step">
          <h3 tabindex="-1" class="step-label">Nhập mật khẩu</h3>
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
          <button type="button" class="otp-resend" @click="sendOtp">Đăng nhập bằng OTP</button>
          <button type="button" class="otp-resend" @click="forgotPassword">Quên mật khẩu?</button>
          <button type="button" class="otp-resend" @click="error = ''; step = 'phone'">Đổi số điện thoại</button>
        </div>

        <!-- Step: OTP input -->
        <div v-else-if="step === 'otp'" class="otp-step">
          <h3 tabindex="-1" class="step-label">Nhập mã OTP</h3>
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
              @keydown="onOtpKeydown(i - 1, $event)"
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

        <!-- Step: Set password (after first OTP login without password) -->
        <div v-else-if="step === 'set-password'" class="otp-step">
          <h3 tabindex="-1" class="step-label">Đặt mật khẩu</h3>
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
              placeholder="Mật khẩu (tối thiểu 8 ký tự)"
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

        <!-- Step: Two-factor authentication -->
        <div v-else-if="step === 'twofactor'" class="otp-step">
          <h3 tabindex="-1" class="step-label">Xác thực 2 bước</h3>
          <template v-if="!useRecovery">
            <p>Nhập mã 6 chữ số từ ứng dụng xác thực.</p>
            <div class="form-group">
              <input
                v-model="totpCode"
                class="input"
                :class="{ error: error && step === 'twofactor' }"
                :aria-invalid="!!(error && step === 'twofactor')"
                type="text"
                inputmode="numeric"
                maxlength="6"
                autocomplete="one-time-code"
                aria-label="Mã xác thực 2 bước"
                placeholder="123456"
                @keyup.enter="verifyTwoFactorCode"
              />
            </div>
          </template>
          <template v-else>
            <p>Nhập một mã khôi phục (dùng một lần).</p>
            <div class="form-group">
              <input
                v-model="recoveryCode"
                class="input"
                :class="{ error: error && step === 'twofactor' }"
                :aria-invalid="!!(error && step === 'twofactor')"
                type="text"
                autocomplete="off"
                aria-label="Mã khôi phục"
                placeholder="Mã khôi phục"
                @keyup.enter="verifyTwoFactorCode"
              />
            </div>
          </template>
          <label class="consent-row">
            <input v-model="rememberDevice" type="checkbox" class="consent-checkbox" />
            <span>Tin cậy thiết bị này trong 90 ngày</span>
          </label>
          <p v-if="error" class="form-error" role="alert">{{ error }}</p>
          <button type="button" class="btn btn-primary btn-full" :disabled="sending" @click="verifyTwoFactorCode">
            {{ sending ? 'Đang xác minh…' : 'Xác nhận' }}
          </button>
          <button type="button" class="otp-resend" @click="error = ''; useRecovery = !useRecovery">
            {{ useRecovery ? 'Dùng mã từ ứng dụng xác thực' : 'Dùng mã khôi phục' }}
          </button>
        </div>

        <!-- Step: Done -->
        <div v-else class="otp-step otp-done">
          <h3 tabindex="-1" class="step-label">{{ isNewAccount ? 'Đăng ký thành công!' : 'Đăng nhập thành công!' }}</h3>
          <p>Chào mừng bạn đến với vinhlong360.</p>
          <button type="button" class="btn btn-primary btn-full" @click="close">Đóng</button>
        </div>
      </div>
    </div>
  </div>
  </Transition>
</template>

<script setup lang="ts">
const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const { requestOtp, verifyOtp, checkPhone, login, setPassword, verifyTwoFactor } = useAuth()
const { onLoginSuccess } = useAuthModal()

const step = ref<'phone' | 'register' | 'password' | 'otp' | 'set-password' | 'twofactor' | 'done'>('phone')
watch(step, (v) => {
  if (v === 'done') onLoginSuccess()
  nextTick(() => modalEl.value?.querySelector<HTMLElement>('h3')?.focus())
})
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
const isNewAccount = ref(false)
let countdownTimer: ReturnType<typeof setInterval> | null = null

const regFullName = ref('')
const regDob = ref('')
const regUsername = ref('')
const regPassword = ref('')
const regPasswordConfirm = ref('')
const usernameStatus = ref<'idle' | 'checking' | 'available' | 'taken' | 'invalid'>('idle')

const challengeId = ref('')
const totpCode = ref('')
const recoveryCode = ref('')
const useRecovery = ref(false)
const rememberDevice = ref(false)

const maxDob = computed(() => {
  const d = new Date()
  d.setFullYear(d.getFullYear() - 13)
  return d.toISOString().split('T')[0]
})

const modalTitle = computed(() => {
  if (step.value === 'register') return 'Đăng ký'
  if (step.value === 'set-password') return 'Đặt mật khẩu'
  if (step.value === 'twofactor') return 'Xác thực 2 bước'
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
    isNewAccount.value = false
    otpDigits.value = ['', '', '', '', '', '']
    regFullName.value = ''
    regDob.value = ''
    regUsername.value = ''
    regPassword.value = ''
    regPasswordConfirm.value = ''
    usernameStatus.value = 'idle'
    challengeId.value = ''
    totpCode.value = ''
    recoveryCode.value = ''
    useRecovery.value = false
    rememberDevice.value = false
  }, 300)
}

const visibleRef = computed(() => props.visible)
useModalA11y(visibleRef, modalEl, { onClose: close })

onUnmounted(() => {
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
})

async function handlePhone() {
  const normalized = phone.value.replace(/\D/g, '')
  if (!normalized || normalized.length < 9 || normalized.length > 11 || !/^0\d{8,10}$/.test(normalized)) {
    error.value = 'Vui lòng nhập số điện thoại hợp lệ (VD: 0901234567)'
    return
  }
  phone.value = normalized
  sending.value = true
  error.value = ''
  try {
    const res = await checkPhone(phone.value)
    if (res.exists) {
      step.value = 'password'
    } else {
      isNewAccount.value = true
      step.value = 'register'
    }
  } catch (e: unknown) {
    error.value = (e as any).data?.detail || 'Lỗi kiểm tra số điện thoại'
  } finally {
    sending.value = false
  }
}

async function checkUsernameAvail() {
  const uname = regUsername.value.trim().toLowerCase()
  if (!uname) { usernameStatus.value = 'idle'; return }
  if (uname.length < 3 || uname.length > 30 || !/^[a-z][a-z0-9._-]*$/.test(uname)) {
    usernameStatus.value = 'invalid'
    return
  }
  usernameStatus.value = 'checking'
  try {
    const res = await $fetch<{ available: boolean }>(`/auth/check-username/${encodeURIComponent(uname)}`)
    usernameStatus.value = res.available ? 'available' : 'taken'
  } catch {
    usernameStatus.value = 'idle'
  }
}

async function handleRegister() {
  error.value = ''
  if (!regFullName.value.trim() || regFullName.value.trim().length < 2) {
    error.value = 'Vui lòng nhập họ và tên (ít nhất 2 ký tự)'
    return
  }
  const uname = regUsername.value.trim().toLowerCase()
  if (!uname || uname.length < 3 || !/^[a-z][a-z0-9._-]*$/.test(uname)) {
    error.value = 'Username phải từ 3 ký tự, bắt đầu bằng chữ, chỉ gồm chữ/số/dấu chấm/gạch ngang'
    return
  }
  if (usernameStatus.value === 'taken') {
    error.value = 'Username đã được sử dụng, vui lòng chọn tên khác'
    return
  }
  if (!regPassword.value || regPassword.value.length < 8) {
    error.value = 'Mật khẩu phải từ 8 ký tự trở lên'
    return
  }
  if (!/\d/.test(regPassword.value) || !/[a-zA-Z]/.test(regPassword.value)) {
    error.value = 'Mật khẩu cần có ít nhất 1 chữ cái và 1 chữ số'
    return
  }
  if (regPassword.value !== regPasswordConfirm.value) {
    error.value = 'Mật khẩu nhập lại không khớp'
    return
  }
  await sendOtp()
}

async function handleLogin() {
  if (!password.value) {
    error.value = 'Vui lòng nhập mật khẩu'
    return
  }
  sending.value = true
  error.value = ''
  try {
    const res = await login(phone.value, password.value)
    if (res.two_factor_required && res.challenge_id) {
      challengeId.value = res.challenge_id
      step.value = 'twofactor'
    } else {
      step.value = 'done'
    }
  } catch (e: unknown) {
    error.value = (e as any).data?.detail || 'Số điện thoại hoặc mật khẩu không đúng'
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
    error.value = (e as any).data?.detail || 'Lỗi gửi OTP. Thử lại sau.'
  } finally {
    sending.value = false
  }
}

let verifyLock = false
async function verifyCode() {
  if (sending.value || verifyLock) return
  verifyLock = true
  const code = otpDigits.value.join('')
  if (code.length !== 6) {
    error.value = 'Vui lòng nhập đủ 6 chữ số'
    verifyLock = false
    return
  }
  sending.value = true
  error.value = ''
  try {
    const registration = isNewAccount.value ? {
      full_name: regFullName.value.trim(),
      username: regUsername.value.trim().toLowerCase(),
      password: regPassword.value,
      date_of_birth: regDob.value || undefined,
    } : undefined
    const res = await verifyOtp(phone.value, code, consent.value, registration)
    if (res.two_factor_required && res.challenge_id) {
      challengeId.value = res.challenge_id
      step.value = 'twofactor'
    } else if (res.error) {
      error.value = res.error
    } else if (isNewAccount.value) {
      step.value = 'done'
    } else if (res.has_password && !isResetFlow.value) {
      step.value = 'done'
    } else {
      step.value = 'set-password'
    }
  } catch (e: unknown) {
    error.value = (e as any).data?.detail || 'Mã OTP không đúng.'
    otpDigits.value = ['', '', '', '', '', '']
    nextTick(() => otpRefs.value[0]?.focus())
  } finally {
    sending.value = false
    verifyLock = false
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
    error.value = (e as any).data?.detail || 'Lỗi đặt mật khẩu'
  } finally {
    sending.value = false
  }
}

async function verifyTwoFactorCode() {
  const code = useRecovery.value ? recoveryCode.value.trim() : totpCode.value.trim()
  if (!code) {
    error.value = useRecovery.value ? 'Vui lòng nhập mã khôi phục' : 'Vui lòng nhập mã 6 chữ số'
    return
  }
  sending.value = true
  error.value = ''
  try {
    const res = await verifyTwoFactor(challengeId.value, code, {
      recovery: useRecovery.value,
      remember_device: rememberDevice.value,
    })
    if (res.error) {
      error.value = res.error
    } else {
      step.value = 'done'
    }
  } catch (e: unknown) {
    error.value = (e as any).data?.detail || 'Mã không đúng'
    totpCode.value = ''
    recoveryCode.value = ''
  } finally {
    sending.value = false
  }
}

function onOtpInput(idx: number) {
  const val = (otpDigits.value[idx] ?? '').replace(/\D/g, '')
  otpDigits.value[idx] = val
  if (val && idx < 5) {
    otpRefs.value[idx + 1]?.focus()
  }
  if (otpDigits.value.join('').length === 6) {
    verifyCode()
  }
}

function onOtpKeydown(idx: number, e: KeyboardEvent) {
  if (e.key === 'Backspace' && !otpDigits.value[idx] && idx > 0) {
    otpRefs.value[idx - 1]?.focus()
  }
  if (e.key === 'ArrowLeft' && idx > 0) { e.preventDefault(); otpRefs.value[idx - 1]?.focus() }
  if (e.key === 'ArrowRight' && idx < 5) { e.preventDefault(); otpRefs.value[idx + 1]?.focus() }
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
/* ── Editorial masthead (visual reskin only — logic/focus untouched) ── */
.modal-head-editorial { align-items: flex-start; }
.modal-head-text { min-width: 0; }
.modal-eyebrow {
  display: block; margin-bottom: var(--space-1);
  font-family: var(--font-sans); font-size: var(--text-2xs); font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase; color: var(--muted);
}
.modal-head-editorial #auth-modal-title {
  font-family: var(--font-editorial); font-weight: 600; letter-spacing: -.01em;
  margin: 0;
}
/* tri-province hairline — quiet rule beneath the masthead, echoes card-rule/sediment-tick */
.modal-rule {
  display: block; height: 2px; border-radius: 2px;
  margin: 0 var(--space-6) var(--space-2);
  background: linear-gradient(90deg, var(--river-600) 0%, var(--amber-600) 52%, var(--clay-600) 100%);
}
.dark .modal-rule { background: linear-gradient(90deg, #74ABB5 0%, var(--amber-500) 52%, var(--clay-400) 100%); }
/* step eyebrow — small-caps label above each step's own heading, restrained */
.step-label {
  font-family: var(--font-editorial); font-weight: 600; letter-spacing: -.005em;
}
.consent-row { display: flex; gap: var(--space-3); align-items: flex-start; margin: var(--space-3) 0; font-size: var(--text-sm); line-height: var(--leading-relaxed); cursor: pointer; padding: var(--space-3); border-radius: var(--radius-md); transition: background .3s var(--ease-out); }
.consent-row:hover { background: var(--bg-alt); }
.consent-checkbox { margin-top: 3px; width: 18px; height: 18px; accent-color: var(--primary); flex-shrink: 0; }
.btn-full { width: 100%; }
.otp-done { text-align: center; }
.otp-done h3 { animation: successPop .45s var(--ease-spring-gentle); }
@keyframes successPop { 0% { transform: scale(.85); opacity: 0; } 60% { transform: scale(1.06); } 100% { transform: scale(1); opacity: 1; } }
.otp-step { animation: stepSlideIn .35s var(--ease-out-expo); }
@keyframes stepSlideIn { from { opacity: 0; transform: translateX(14px); } to { opacity: 1; transform: translateX(0); } }
.form-label { display: block; font-size: var(--text-sm); font-weight: 600; margin-bottom: var(--space-1); color: var(--ink-secondary); }
.form-label .required { color: var(--error); }
.form-group { margin-bottom: var(--space-3); }
.form-success { font-size: var(--text-sm); color: var(--success); margin-top: var(--space-1); }
@media (prefers-reduced-motion: reduce) {
  .otp-done h3 { animation: none; }
  .otp-step { animation: none; }
}
@media (max-width: 600px) {
  .otp-step .input { font-size: 16px; }
}
.otp-step h3 { outline: none; }
@media (forced-colors: active) {
  .consent-checkbox { outline: 1px solid ButtonText; }
}
</style>
