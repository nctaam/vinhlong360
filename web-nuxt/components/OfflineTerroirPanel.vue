<template>
  <div
    v-if="shouldShow"
    class="offline-terroir-panel"
    data-offline-terroir-panel
    role="region"
    aria-label="Bảng điều hướng cứu hộ thực địa ngoại tuyến"
  >
    <!-- Scrim when open as overlay/modal -->
    <div v-if="isModalOpen" class="offline-panel-scrim" aria-hidden="true" @click="dismissModal" />

    <div class="offline-panel-container" :class="{ 'as-modal': isModalOpen }">
      <!-- Status Banner -->
      <div class="offline-status-banner">
        <div class="status-left">
          <span class="offline-pulse-icon" aria-hidden="true">
            <VernacularGlyph name="three-plank-sampan" :size="20" accent="clay" />
          </span>
          <div>
            <strong class="status-title">Chế độ Thực địa Ngoại tuyến</strong>
            <p class="status-desc">
              {{ networkText }}
            </p>
          </div>
        </div>

        <div class="status-right">
          <button
            type="button"
            class="offline-toggle-btn"
            :aria-expanded="expanded"
            :aria-label="expanded ? 'Thu gọn bảng cứu hộ' : 'Mở rộng bảng cứu hộ'"
            @click="expanded = !expanded"
          >
            <IconLine :name="expanded ? 'chevron-up' : 'chevron-down'" aria-hidden="true" />
          </button>
          <button
            v-if="isModalOpen"
            type="button"
            class="offline-close-btn"
            aria-label="Đóng bảng cứu hộ"
            @click="dismissModal"
          >
            <IconLine name="x" aria-hidden="true" />
          </button>
        </div>
      </div>

      <!-- Collapsible Body Content -->
      <div v-if="expanded" class="offline-panel-body">
        <!-- Section 1: Astronomical Tide Almanac (Computed Offline) -->
        <section class="offline-section" aria-labelledby="offline-tide-heading">
          <h3 id="offline-tide-heading" class="offline-section-title">
            <VernacularGlyph name="barringtonia-flower" :size="16" accent="silt" />
            <span>Lịch Con Nước Thiên Văn (Tính Toán Cục Bộ)</span>
          </h3>

          <div class="tide-almanac-card">
            <div class="tide-state-row">
              <div class="tide-pill">
                <span class="tide-indicator-dot" aria-hidden="true" />
                <strong>{{ tide.tidePhaseLabel }}</strong>
              </div>
              <span class="tide-flow-badge">{{ tide.waterFlowLabel }} ({{ tide.waterLevelMeters }}m)</span>
            </div>
            <p class="tide-wisdom">
              <em>"{{ tide.folkWisdom }}"</em>
            </p>
            <p class="tide-desc">
              {{ tide.waterFlowDesc }}
            </p>
          </div>
        </section>

        <!-- Section 2: Terroir Field Navigation Notes -->
        <section class="offline-section" aria-labelledby="offline-nav-heading">
          <h3 id="offline-nav-heading" class="offline-section-title">
            <IconLine name="compass" aria-hidden="true" />
            <span>Chỉ Dẫn Vượt Sông &amp; Tọa Độ Thực Địa</span>
          </h3>

          <div class="offline-nav-card">
            <p class="nav-coords-row">
              <span>Tâm điểm Lò gạch Mang Thít:</span>
              <strong class="coords-value">10.254° N, 105.972° E</strong>
            </p>
            <ul class="offline-notes-list">
              <li><strong>Phà An Bình:</strong> Hoạt động 24/7 nối trung tâm TP Vĩnh Long với 4 xã cù lao An Bình, Bình Hòa Phước, Hòa Ninh, Đồng Phú.</li>
              <li><strong>Phà Đình Khao:</strong> Trục huyết mạch QL57 vượt sông Cổ Chiên sang Bến Tre.</li>
              <li><strong>Lưu ý luồng lạch:</strong> Khi nước ròng sát đáy cẩn trọng bãi bùn lạn ghe xuồng; chọn đi men luồng sâu kênh Thầy Cai.</li>
            </ul>
          </div>
        </section>

        <!-- Section 3: 24/7 Emergency Rescue Contacts -->
        <section class="offline-section" aria-labelledby="offline-emergency-heading">
          <h3 id="offline-emergency-heading" class="offline-section-title">
            <IconLine name="phone" aria-hidden="true" />
            <span>Đầu Mối Cứu Hộ Đường Thủy &amp; Khẩn Cấp (Gọi Trực Tiếp)</span>
          </h3>

          <div class="emergency-contacts-grid">
            <a
              v-for="c in EMERGENCY_CONTACTS"
              :key="c.phone"
              :href="'tel:' + c.tel"
              class="emergency-contact-btn"
              :aria-label="'Gọi ' + c.name + ': ' + c.phone"
            >
              <div class="contact-info">
                <strong class="contact-name">{{ c.name }}</strong>
                <span class="contact-role">{{ c.role }}</span>
              </div>
              <span class="contact-call-action">
                <IconLine name="phone" aria-hidden="true" />
                <span class="contact-phone-num">{{ c.phone }}</span>
              </span>
            </a>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCognitiveTerroir } from '~/composables/useCognitiveTerroir'

const props = withDefaults(defineProps<{
  isOffline?: boolean
  open?: boolean
  modelValue?: boolean
}>(), {
  isOffline: undefined,
  open: false,
  modelValue: false,
})

const emit = defineEmits<{
  (e: 'update:open', val: boolean): void
  (e: 'update:modelValue', val: boolean): void
  (e: 'close'): void
}>()

const { tide, isOffline: terroirOffline } = useCognitiveTerroir()

const effectiveOffline = computed(() => {
  if (typeof props.isOffline === 'boolean') return props.isOffline
  return terroirOffline.value
})

const isModalOpen = computed(() => props.open || props.modelValue)
const shouldShow = computed(() => effectiveOffline.value || isModalOpen.value)

const expanded = ref(true)

const networkText = computed(() => {
  if (effectiveOffline.value) {
    return 'Mất kết nối Internet · Đang hiển thị bản đồ số & danh bạ cứu hộ từ bộ nhớ đệm an toàn.'
  }
  return 'Bảng hỗ trợ khẩn cấp điền dã · Khả dụng ngoại tuyến 100% không phụ thuộc sóng di động.'
})

const EMERGENCY_CONTACTS = [
  {
    name: 'Cứu Hộ Giao Thông Thủy Vĩnh Long',
    role: 'Trực ban 24/7 sông Cổ Chiên & Bến Đình Khao',
    phone: '0270 3822 188',
    tel: '02703822188',
  },
  {
    name: 'Bến Phà An Bình',
    role: 'Phà chở khách sang cù lao thường trực ngày đêm',
    phone: '0270 3858 200',
    tel: '02703858200',
  },
  {
    name: 'Bệnh Viện Đa Khoa Tỉnh Vĩnh Long',
    role: 'Cấp cứu y tế & hỗ trợ sơ cứu vùng sông nước',
    phone: '0270 3823 520',
    tel: '02703823520',
  },
  {
    name: 'Công An Tỉnh Vĩnh Long (Trực Ban)',
    role: 'Bảo đảm an ninh trật tự & hỗ trợ du khách',
    phone: '069 370 6112',
    tel: '0693706112',
  },
  {
    name: 'Tổng Đài Cứu Nạn Khẩn Cấp (PCCC & CNCH)',
    role: 'Cứu hộ cứu nạn khẩn cấp trên sông',
    phone: '114',
    tel: '114',
  },
]

function dismissModal() {
  emit('update:open', false)
  emit('update:modelValue', false)
  emit('close')
}
</script>

<style scoped>
.offline-terroir-panel {
  position: relative;
  width: 100%;
  z-index: var(--z-sticky);
}

.offline-panel-scrim {
  position: fixed;
  inset: 0;
  background: color-mix(in srgb, var(--night-canvas) 60%, transparent);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  z-index: var(--z-modal);
}

.offline-panel-container {
  width: 100%;
  background: var(--color-surface);
  color: var(--color-text);
  border: 1.5px solid var(--alluvial-gold);
  border-radius: var(--radius-surface);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  transition: all 0.2s ease;
}

.offline-panel-container.as-modal {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  max-width: 600px;
  width: 95%;
  max-height: 85vh;
  z-index: var(--z-modal);
  box-shadow: var(--shadow-xl);
  overflow-y: auto;
  margin-bottom: var(--space-fib-3);
}

.offline-status-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-fib-2) var(--space-fib-3);
  background: color-mix(in srgb, var(--color-material-clay) 8%, var(--color-surface));
  border-bottom: 1px solid var(--color-border);
}

.status-left {
  display: flex;
  align-items: center;
  gap: var(--space-fib-2);
}

.offline-pulse-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-title {
  font-size: var(--font-size-body);
  font-weight: var(--weight-bold);
  color: var(--color-material-clay);
}

.status-desc {
  margin: 2px 0 0;
  font-size: var(--font-size-label);
  color: var(--color-text-muted);
}

.status-right {
  display: flex;
  align-items: center;
  gap: var(--space-fib-1);
}

.offline-toggle-btn,
.offline-close-btn {
  min-width: 44px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  color: var(--color-text);
  cursor: pointer;
}

.offline-panel-body {
  padding: var(--space-fib-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-fib-3);
}

.offline-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-fib-1);
}

.offline-section-title {
  display: flex;
  align-items: center;
  gap: var(--space-fib-1);
  font-size: var(--font-size-caption);
  font-weight: var(--weight-title-sm);
  color: var(--color-text-muted);
  margin: 0;
}

.tide-almanac-card,
.offline-nav-card {
  padding: var(--space-fib-2) var(--space-fib-3);
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  display: flex;
  flex-direction: column;
  gap: var(--space-fib-1);
}

.tide-state-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tide-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--font-size-body);
  color: var(--color-text);
}

.tide-indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--alluvial-gold);
}

.tide-flow-badge {
  font-size: var(--font-size-caption);
  font-family: monospace;
  font-weight: var(--weight-bold);
  color: var(--color-action);
}

.tide-wisdom {
  margin: 0;
  font-size: var(--font-size-caption);
  font-family: var(--font-editorial, 'Lora', serif);
  color: var(--color-material-clay);
}

.tide-desc {
  margin: 0;
  font-size: var(--font-size-label);
  color: var(--color-text-muted);
}

.nav-coords-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 0;
  font-size: var(--font-size-caption);
}

.coords-value {
  font-family: monospace;
  color: var(--color-action);
}

.offline-notes-list {
  margin: var(--space-fib-1) 0 0;
  padding-left: var(--space-fib-3);
  font-size: var(--font-size-label);
  color: var(--color-text-muted);
  line-height: 1.5;
}

.emergency-contacts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-fib-2);
}

.emergency-contact-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 48px;
  padding: var(--space-fib-2) var(--space-fib-3);
  background: var(--color-surface-subtle);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-control);
  color: var(--color-text);
  text-decoration: none;
  transition: all 0.15s ease;
}

.emergency-contact-btn:hover {
  background: var(--color-surface-raised);
  border-color: var(--alluvial-gold);
}

.contact-info {
  display: flex;
  flex-direction: column;
}

.contact-name {
  font-size: var(--font-size-caption);
  font-weight: var(--weight-title-sm);
  color: var(--color-text);
}

.contact-role {
  font-size: var(--font-size-label);
  color: var(--color-text-muted);
}

.contact-call-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: var(--radius-control);
  background: var(--color-action);
  color: var(--sand-50);
  font-size: var(--font-size-label);
  font-weight: var(--weight-bold);
  white-space: nowrap;
}

.contact-phone-num {
  font-family: monospace;
}
</style>
