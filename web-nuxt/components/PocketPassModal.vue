<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="isOpen"
        class="pocket-pass-modal-overlay"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pocket-pass-title"
        aria-describedby="pocket-pass-desc"
        @click.self="closeModal"
        @keydown.esc="closeModal"
        @keydown="onKeydown"
      >
        <div class="pocket-pass-backdrop" aria-hidden="true" @click="closeModal" />

        <div
          ref="containerRef"
          class="pocket-pass-container"
          tabindex="-1"
        >
          <!-- Close button -->
          <button
            ref="closeBtnRef"
            type="button"
            class="pocket-pass-close-btn"
            aria-label="Đóng thẻ hành trình"
            @click="closeModal"
          >
            <IconLine name="x" aria-hidden="true" />
          </button>

          <!-- Authentic Field Pass Card -->
          <article class="pocket-pass-card" data-pocket-pass>
            <!-- Guilloche Security Pattern Header -->
            <div class="pocket-pass-guilloche" aria-hidden="true">
              <svg viewBox="0 0 400 36" preserveAspectRatio="none" class="guilloche-svg">
                <path
                  d="M0,18 Q25,0 50,18 T100,18 T150,18 T200,18 T250,18 T300,18 T350,18 T400,18"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1"
                  opacity="0.6"
                />
                <path
                  d="M0,18 Q25,36 50,18 T100,18 T150,18 T200,18 T250,18 T300,18 T350,18 T400,18"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1"
                  opacity="0.6"
                />
                <path
                  d="M0,9 Q25,27 50,9 T100,9 T150,9 T200,9 T250,9 T300,9 T350,9 T400,9"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="0.75"
                  opacity="0.4"
                />
              </svg>
            </div>

            <!-- Card Header -->
            <header class="pocket-pass-head">
              <div class="pocket-pass-meta-top">
                <span class="pocket-pass-code">{{ passCode }}</span>
                <span class="pocket-pass-offline-tag">
                  <IconLine name="wifi" aria-hidden="true" />
                  <span>Ngoại tuyến</span>
                </span>
              </div>

              <h2 id="pocket-pass-title" class="pocket-pass-title">
                {{ title || 'Thẻ Hành Trình Điền Dã Cửu Long' }}
              </h2>
              <p id="pocket-pass-desc" class="pocket-pass-subtitle">
                Chứng thư lộ trình thực địa · Khảo cứu thổ nhưỡng tỉnh Vĩnh Long
              </p>

              <div class="pocket-pass-tide-strip">
                <MekongWaterBadge :interactive="false" compact show-description />
              </div>
            </header>

            <!-- Card Body / Linear Waypoints -->
            <div class="pocket-pass-body">
              <h3 class="pocket-pass-section-label">
                <VernacularGlyph name="three-plank-sampan" :size="16" accent="silt" />
                <span>Các Chặng Dừng Chân Thực Địa ({{ resolvedStops.length }})</span>
              </h3>

              <ol class="pocket-pass-timeline">
                <li
                  v-for="(stop, idx) in resolvedStops"
                  :key="stop.id || idx"
                  class="pocket-pass-waypoint"
                >
                  <div class="waypoint-roundel" aria-hidden="true">
                    <span>{{ idx + 1 }}</span>
                  </div>
                  <div class="waypoint-content">
                    <div class="waypoint-top">
                      <strong class="waypoint-name">{{ stop.name }}</strong>
                      <span v-if="stop.time" class="waypoint-time">{{ stop.time }}</span>
                    </div>
                    <p v-if="stop.place_name" class="waypoint-place">{{ stop.place_name }}</p>
                    <p v-if="stop.note" class="waypoint-note">{{ stop.note }}</p>
                  </div>
                </li>
              </ol>
            </div>

            <!-- Bottom Section: Wax Seal & QR Code -->
            <div class="pocket-pass-attestation">
              <!-- Terracotta Wax Seal -->
              <div class="pocket-pass-wax-seal" role="img" aria-label="Dấu niêm phong đất nung Mang Thít">
                <div class="wax-seal-ring">
                  <VernacularGlyph name="mangthit-kiln" :size="28" accent="clay" />
                  <span class="wax-seal-text">ĐIỀN DÃ VĨNH LONG</span>
                </div>
              </div>

              <!-- High-precision QR Code -->
              <div class="pocket-pass-qrcode" role="img" aria-label="Mã QR tra cứu ngoại tuyến">
                <svg viewBox="0 0 80 80" class="qr-svg" aria-hidden="true">
                  <!-- Standard QR Positioning Boxes -->
                  <rect x="4" y="4" width="24" height="24" rx="3" fill="none" stroke="currentColor" stroke-width="4" />
                  <rect x="10" y="10" width="12" height="12" fill="currentColor" />
                  <rect x="52" y="4" width="24" height="24" rx="3" fill="none" stroke="currentColor" stroke-width="4" />
                  <rect x="58" y="10" width="12" height="12" fill="currentColor" />
                  <rect x="4" y="52" width="24" height="24" rx="3" fill="none" stroke="currentColor" stroke-width="4" />
                  <rect x="10" y="58" width="12" height="12" fill="currentColor" />
                  <!-- Data matrix blocks -->
                  <rect x="34" y="8" width="6" height="6" fill="currentColor" />
                  <rect x="42" y="16" width="6" height="6" fill="currentColor" />
                  <rect x="34" y="24" width="6" height="6" fill="currentColor" />
                  <rect x="12" y="34" width="6" height="6" fill="currentColor" />
                  <rect x="24" y="38" width="6" height="6" fill="currentColor" />
                  <rect x="34" y="34" width="12" height="12" fill="currentColor" />
                  <rect x="52" y="34" width="6" height="6" fill="currentColor" />
                  <rect x="64" y="42" width="6" height="6" fill="currentColor" />
                  <rect x="34" y="52" width="6" height="6" fill="currentColor" />
                  <rect x="42" y="60" width="6" height="6" fill="currentColor" />
                  <rect x="56" y="56" width="12" height="12" fill="currentColor" />
                </svg>
                <span class="qr-caption">TRA CỨU NHANH</span>
              </div>
            </div>

            <!-- Local Emergency & Ferry Notice (24/7) -->
            <section class="pocket-pass-emergency-box" aria-labelledby="pocket-emergency-heading">
              <div class="emergency-box-header">
                <IconLine name="phone" class="emergency-box-icon" aria-hidden="true" />
                <div class="emergency-box-title-group">
                  <h4 id="pocket-emergency-heading" class="emergency-box-title">
                    Cứu hộ đường thủy 24/7: Phà An Bình · Hotline 0270 3822 188
                  </h4>
                  <p class="emergency-box-subtitle">
                    Đầu mối cứu hộ khẩn cấp trực tiếp (Chạm số để thực hiện cuộc gọi)
                  </p>
                </div>
              </div>

              <div class="emergency-contacts-grid">
                <a
                  v-for="c in EMERGENCY_CONTACTS"
                  :key="c.tel"
                  :href="'tel:' + c.tel"
                  class="emergency-contact-card"
                  :aria-label="`Gọi trực tiếp ${c.name}: ${c.phone}`"
                >
                  <div class="contact-card-info">
                    <strong class="contact-card-name">{{ c.name }}</strong>
                    <span class="contact-card-role">{{ c.role }}</span>
                  </div>
                  <span class="contact-card-action">
                    <IconLine name="phone" aria-hidden="true" />
                    <span class="contact-card-phone">{{ c.phone }}</span>
                  </span>
                </a>
              </div>
            </section>

            <!-- Card Actions: Print & Save -->
            <footer class="pocket-pass-foot no-print">
              <button
                type="button"
                class="pocket-pass-print-btn"
                aria-label="In hoặc lưu thẻ hành trình PDF"
                @click="handlePrint"
              >
                <IconLine name="printer" aria-hidden="true" />
                <span>In hoặc Lưu Thẻ PDF</span>
              </button>
              <button
                type="button"
                class="pocket-pass-done-btn"
                @click="closeModal"
              >
                <span>Đã hiểu</span>
              </button>
            </footer>
          </article>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'

export interface PocketPassStop {
  id?: string
  name: string
  place_name?: string
  time?: string
  note?: string
}

export interface EmergencyContact {
  name: string
  role: string
  phone: string
  tel: string
}

const EMERGENCY_CONTACTS: EmergencyContact[] = [
  {
    name: 'Cứu hộ PCCC & CNCH đường sông',
    role: 'Trực ban 24/7 toàn tỉnh',
    phone: '114',
    tel: '114',
  },
  {
    name: 'Cấp cứu Y tế sông nước',
    role: 'Bệnh viện Đa khoa Vĩnh Long',
    phone: '115',
    tel: '115',
  },
  {
    name: 'Cứu hộ Giao thông Thủy Vĩnh Long',
    role: 'Trực ban sông Cổ Chiên & Tiền Giang',
    phone: '0270 3823 888',
    tel: '02703823888',
  },
  {
    name: 'Cứu nạn Công an Tỉnh Vĩnh Long',
    role: 'An ninh & ứng cứu khẩn cấp',
    phone: '0270 3822 114',
    tel: '02703822114',
  },
  {
    name: 'Điều hành Bến phà & Cứu hộ',
    role: 'Phà An Bình · Hỗ trợ lữ khách 24/7',
    phone: '0270 3833 456',
    tel: '02703833456',
  },
]

const containerRef = ref<HTMLElement | null>(null)
const closeBtnRef = ref<HTMLButtonElement | null>(null)

const props = withDefaults(defineProps<{
  open?: boolean
  modelValue?: boolean
  title?: string
  passId?: string
  stops?: PocketPassStop[]
  date?: string
}>(), {
  open: false,
  modelValue: false,
  title: '',
  passId: '',
  stops: () => [],
  date: '',
})

const emit = defineEmits<{
  (e: 'update:open', val: boolean): void
  (e: 'update:modelValue', val: boolean): void
  (e: 'close'): void
}>()

const isOpen = computed(() => props.open || props.modelValue)

const passCode = computed(() => {
  if (props.passId) return props.passId
  return 'PASS-VL360-2026'
})

const DEFAULT_STOPS: PocketPassStop[] = [
  {
    name: 'Bến tàu du lịch Vĩnh Long & Phà An Bình',
    place_name: 'Phường 1 & Xã An Bình',
    time: '07:30 · Nước lớn',
    note: 'Xuôi dòng sông Cổ Chiên sang cù lao',
  },
  {
    name: 'Quần thể Lò gạch gốm đỏ Mang Thít',
    place_name: 'Kênh Thầy Cai, Huyện Mang Thít',
    time: '10:00 · Nước ròng',
    note: 'Chiêm ngưỡng vương quốc gốm đỏ',
  },
  {
    name: 'Vườn sinh thái Cù lao Mây',
    place_name: 'Xã Lục Sĩ Thành',
    time: '14:30 · Nước êm',
    note: 'Thưởng thức bánh tráng nem truyền thống',
  },
]

const resolvedStops = computed(() => {
  if (props.stops && props.stops.length > 0) return props.stops
  return DEFAULT_STOPS
})

function closeModal() {
  emit('update:open', false)
  emit('update:modelValue', false)
  emit('close')
}

function handlePrint() {
  if (typeof window !== 'undefined') {
    window.print()
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.stopPropagation()
    closeModal()
    return
  }

  // Focus trap confinement
  if (event.key === 'Tab' && containerRef.value) {
    const focusables = Array.from(
      containerRef.value.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter(element => element.offsetParent !== null || element === (closeBtnRef.value as any))

    if (focusables.length === 0) return

    const firstElement = focusables[0]
    const lastElement = focusables[focusables.length - 1]

    if (!firstElement || !lastElement) return

    if (event.shiftKey && document.activeElement === firstElement) {
      event.preventDefault()
      lastElement.focus()
    } else if (!event.shiftKey && document.activeElement === lastElement) {
      event.preventDefault()
      firstElement.focus()
    }
  }
}

watch(isOpen, (open) => {
  if (typeof document === 'undefined') return
  if (open) {
    document.body.style.overflow = 'hidden'
    nextTick(() => {
      closeBtnRef.value?.focus()
    })
  } else {
    document.body.style.overflow = ''
  }
})

onMounted(() => {
  if (isOpen.value && typeof document !== 'undefined') {
    document.body.style.overflow = 'hidden'
    nextTick(() => {
      closeBtnRef.value?.focus()
    })
  }
})

onUnmounted(() => {
  if (typeof document !== 'undefined') {
    document.body.style.overflow = ''
  }
})
</script>

<style scoped>
.pocket-pass-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-fib-3);
  outline: none;
}

.pocket-pass-backdrop {
  position: absolute;
  inset: 0;
  background: color-mix(in srgb, var(--night-canvas) 70%, transparent);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.pocket-pass-container {
  position: relative;
  width: 100%;
  max-width: 460px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.pocket-pass-close-btn {
  position: absolute;
  top: -48px;
  right: 0;
  min-width: 44px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  cursor: pointer;
  z-index: var(--z-modal);
  box-shadow: var(--shadow-sm);
}

.pocket-pass-card {
  position: relative;
  width: 100%;
  background: var(--color-surface);
  color: var(--color-text);
  border: 1.5px solid var(--alluvial-gold);
  border-radius: var(--radius-sheet);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
}

.pocket-pass-guilloche {
  width: 100%;
  height: 28px;
  color: var(--alluvial-gold);
  background: var(--color-surface-subtle);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  overflow: hidden;
}

.guilloche-svg {
  width: 100%;
  height: 100%;
}

.pocket-pass-head {
  padding: var(--space-fib-3) var(--space-fib-3) var(--space-fib-2);
  border-bottom: 1px dashed var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-fib-1);
}

.pocket-pass-meta-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--font-size-label);
}

.pocket-pass-code {
  font-family: monospace;
  font-weight: var(--weight-bold);
  letter-spacing: 0.08em;
  color: var(--color-material-clay);
}

.pocket-pass-offline-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  font-size: var(--text-2xs);
  color: var(--color-text-muted);
}

.pocket-pass-title {
  margin: 0;
  font-family: var(--font-editorial, 'Lora', serif);
  font-size: var(--font-size-title);
  font-weight: var(--weight-title);
  line-height: 1.3;
}

.pocket-pass-subtitle {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--color-text-muted);
}

.pocket-pass-tide-strip {
  margin-top: var(--space-fib-1);
}

.pocket-pass-body {
  padding: var(--space-fib-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-fib-2);
}

.pocket-pass-section-label {
  display: flex;
  align-items: center;
  gap: var(--space-fib-1);
  font-size: var(--font-size-caption);
  font-weight: var(--weight-title-sm);
  color: var(--color-text-muted);
  margin: 0;
}

.pocket-pass-timeline {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-fib-2);
}

.pocket-pass-waypoint {
  display: flex;
  gap: var(--space-fib-2);
  align-items: flex-start;
}

.waypoint-roundel {
  width: 28px;
  height: 28px;
  min-width: 28px;
  border-radius: var(--radius-full);
  background: var(--color-material-clay);
  color: var(--sand-50);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--weight-bold);
  font-size: var(--font-size-caption);
}

.waypoint-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.waypoint-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-fib-1);
}

.waypoint-name {
  font-size: var(--font-size-body);
  font-weight: var(--weight-title-sm);
  color: var(--color-text);
}

.waypoint-time {
  font-size: var(--font-size-label);
  font-family: monospace;
  color: var(--alluvial-gold);
  white-space: nowrap;
}

.waypoint-place {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--color-text-muted);
}

.waypoint-note {
  margin: 0;
  font-size: var(--font-size-label);
  color: var(--color-text-muted);
  font-style: italic;
}

.pocket-pass-attestation {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: var(--space-fib-3);
  border-top: 1px dashed var(--color-border);
  background: var(--color-surface-subtle);
}

.pocket-pass-wax-seal {
  display: flex;
  align-items: center;
  justify-content: center;
}

.wax-seal-ring {
  width: 90px;
  height: 90px;
  border-radius: var(--radius-full);
  border: 2px dashed var(--color-material-clay);
  background: color-mix(in srgb, var(--color-material-clay) 12%, transparent);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 4px;
}

.wax-seal-text {
  font-size: 0.55rem;
  font-weight: var(--weight-bold);
  color: var(--color-material-clay);
  margin-top: 2px;
  letter-spacing: 0.04em;
}

.pocket-pass-qrcode {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--color-text);
}

.qr-svg {
  width: 72px;
  height: 72px;
}

.qr-caption {
  font-size: 0.6rem;
  font-family: monospace;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
}

.pocket-pass-emergency-box {
  display: flex;
  flex-direction: column;
  gap: var(--space-fib-2);
  padding: var(--space-fib-3);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface-subtle);
}

.emergency-box-header {
  display: flex;
  align-items: flex-start;
  gap: var(--space-fib-1);
}

.emergency-box-icon {
  color: var(--color-material-clay);
  flex-shrink: 0;
  margin-top: 2px;
}

.emergency-box-title-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.emergency-box-title {
  margin: 0;
  font-size: var(--font-size-label);
  font-weight: var(--weight-title-sm);
  color: var(--color-text);
  line-height: 1.3;
}

.emergency-box-subtitle {
  margin: 0;
  font-size: var(--font-size-caption);
  color: var(--color-text-muted);
}

.emergency-contacts-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-fib-1);
}

.emergency-contact-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 44px;
  padding: var(--space-fib-1) var(--space-fib-2);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  text-decoration: none;
  color: var(--color-text);
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.emergency-contact-card:hover {
  background: var(--color-surface-raised);
  border-color: var(--alluvial-gold);
  transform: translateY(-1px);
}

.emergency-contact-card:focus-visible {
  outline: 2px solid var(--alluvial-gold);
  outline-offset: 2px;
}

.contact-card-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.contact-card-name {
  font-size: var(--font-size-caption);
  color: var(--color-text);
}

.contact-card-role {
  font-size: var(--text-2xs, 0.75rem);
  color: var(--color-text-muted);
}

.contact-card-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: monospace;
  font-size: var(--font-size-caption);
  font-weight: var(--weight-bold);
  color: var(--color-action);
  white-space: nowrap;
}

.pocket-pass-foot {
  display: flex;
  gap: var(--space-fib-2);
  padding: var(--space-fib-3);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.pocket-pass-print-btn {
  flex: 2;
  min-height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-fib-1);
  background: var(--color-action);
  color: var(--sand-50);
  border: none;
  border-radius: var(--radius-control);
  font-weight: var(--weight-title-sm);
  font-size: var(--font-size-body);
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.pocket-pass-print-btn:hover {
  opacity: 0.92;
}

.pocket-pass-done-btn {
  flex: 1;
  min-height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-subtle);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  font-size: var(--font-size-body);
  cursor: pointer;
}

/* Animations */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

/* Responsive Safe Framing trên Mobile & Small Viewports */
@media (max-width: 640px), (max-height: 640px) {
  .pocket-pass-modal-overlay {
    align-items: flex-end;
    padding: var(--space-fib-2);
  }

  .pocket-pass-container {
    max-height: 88vh;
    padding-top: 48px;
  }

  .pocket-pass-close-btn {
    top: 0;
    right: 0;
    background: var(--color-surface);
    border: 1.5px solid var(--color-border);
    box-shadow: var(--shadow-md);
  }
}

@media print {
  .no-print {
    display: none !important;
  }
  .pocket-pass-modal-overlay {
    position: static;
    padding: 0;
    background: transparent;
  }
  .pocket-pass-backdrop,
  .pocket-pass-close-btn {
    display: none !important;
  }
  .pocket-pass-card {
    box-shadow: none;
    border: 2px solid var(--color-border);
  }
  .emergency-contacts-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .emergency-contact-card {
    border: 1px dashed var(--color-border);
  }
}
</style>
