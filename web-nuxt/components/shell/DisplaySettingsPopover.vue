<template>
  <div ref="popoverRoot" class="display-settings-wrapper">
    <button
      type="button"
      class="display-settings-trigger theme-mode-btn"
      :class="{ 'has-active': hasActiveMode, 'is-open': isOpen }"
      :aria-expanded="isOpen"
      aria-haspopup="dialog"
      aria-label="Tùy chọn hiển thị và trợ năng (Alt+E, Alt+S)"
      :title="triggerTooltip"
      @click="toggleOpen"
    >
      <VernacularGlyph name="field-compass" :size="16" aria-hidden="true" />
      <span class="display-settings-trigger-text sr-only-md-down">Trợ năng</span>
      <span v-if="hasActiveMode" class="display-settings-counter" aria-label="Số chế độ đang bật">
        {{ activeCount }}
      </span>
      <IconLine name="chevron-down" class="display-settings-caret" :class="{ 'is-rotated': isOpen }" aria-hidden="true" />
    </button>

    <Transition name="popover-fade">
      <div
        v-if="isOpen"
        class="display-settings-card"
        role="dialog"
        aria-modal="false"
        aria-label="Bảng điều khiển hiển thị và trợ năng"
        @keydown.esc="closePopover"
      >
        <div class="display-settings-header">
          <div class="display-settings-titles">
            <span class="display-settings-title">Hiển thị & Trợ năng</span>
            <span class="display-settings-subtitle">Tùy chỉnh cỡ chữ và độ tương phản</span>
          </div>
          <button
            type="button"
            class="display-settings-close-btn"
            aria-label="Đóng bảng tùy chọn"
            @click="closePopover"
          >
            <IconLine name="chevron-up" aria-hidden="true" />
          </button>
        </div>

        <div class="display-settings-list" role="group" aria-label="Danh sách tính năng trợ năng">
          <!-- 1. Kính Lão Điền Dã -->
          <div class="display-settings-item" :class="{ 'is-active': isElderMode }">
            <div class="display-settings-icon-box">
              <VernacularGlyph name="elder-glasses" :size="20" aria-hidden="true" />
            </div>
            <div class="display-settings-info">
              <div class="display-settings-name-row">
                <span class="display-settings-item-name">Chữ lớn dễ đọc</span>
                <kbd class="display-settings-badge-kbd">Alt+E</kbd>
              </div>
              <p class="display-settings-item-desc">Phóng to cỡ chữ 125%, giãn dòng 2.0 dễ đọc hơn</p>
            </div>
            <button
              type="button"
              class="display-settings-toggle-btn"
              :class="{ 'is-checked': isElderMode }"
              :aria-pressed="isElderMode"
              aria-label="Bật hoặc tắt chế độ chữ lớn 125% (Alt+E)"
              @click="toggleElderMode()"
            >
              <span class="toggle-rail">
                <span class="toggle-knob"></span>
              </span>
            </button>
          </div>

          <!-- 2. Nắng Gắt Sông Nước -->
          <div class="display-settings-item" :class="{ 'is-active': isHighGlare }">
            <div class="display-settings-icon-box">
              <VernacularGlyph name="sun-glare" :size="20" aria-hidden="true" />
            </div>
            <div class="display-settings-info">
              <div class="display-settings-name-row">
                <span class="display-settings-item-name">Tương phản ngoài trời</span>
                <kbd class="display-settings-badge-kbd">Alt+S</kbd>
              </div>
              <p class="display-settings-item-desc">Tăng độ tương phản &ge; 14:1 khi xem dưới nắng gắt</p>
            </div>
            <button
              type="button"
              class="display-settings-toggle-btn"
              :class="{ 'is-checked': isHighGlare }"
              :aria-pressed="isHighGlare"
              aria-label="Bật hoặc tắt chế độ tương phản ngoài trời (Alt+S)"
              @click="toggleHighGlare()"
            >
              <span class="toggle-rail">
                <span class="toggle-knob"></span>
              </span>
            </button>
          </div>

          <!-- 3. Sinh Thái Sông Nước -->
          <div class="display-settings-item" :class="{ 'is-active': isEcoTerroir }">
            <div class="display-settings-icon-box">
              <VernacularGlyph name="eco-routing" :size="20" aria-hidden="true" />
            </div>
            <div class="display-settings-info">
              <div class="display-settings-name-row">
                <span class="display-settings-item-name">Tiết kiệm dữ liệu</span>
                <span class="display-settings-badge-tag">Nhẹ tải</span>
              </div>
              <p class="display-settings-item-desc">Giảm hiệu ứng và tải dữ liệu nền khi sóng yếu</p>
            </div>
            <button
              type="button"
              class="display-settings-toggle-btn eco-mode-toggle"
              :class="{ 'is-checked': isEcoTerroir }"
              :aria-pressed="isEcoTerroir"
              aria-label="Bật hoặc tắt chế độ tiết kiệm dữ liệu"
              @click="toggleEcoMode()"
            >
              <span class="toggle-rail">
                <span class="toggle-knob"></span>
              </span>
            </button>
          </div>
        </div>

        <div class="display-settings-footer">
          <IconLine name="info" class="display-settings-footer-icon" aria-hidden="true" />
          <span class="display-settings-footer-text">
            Nhấn Esc để đóng · Phím tắt Alt+E / Alt+S có hiệu lực toàn trang
          </span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useCognitiveTerroir } from '~/composables/useCognitiveTerroir'

const {
  isElderMode,
  isHighGlare,
  isEcoTerroir,
  toggleElderMode,
  toggleHighGlare,
  toggleEcoMode,
} = useCognitiveTerroir()

const popoverRoot = ref<HTMLElement | null>(null)
const isOpen = ref(false)

const activeCount = computed(() => {
  let count = 0
  if (isElderMode.value) count++
  if (isHighGlare.value) count++
  if (isEcoTerroir.value) count++
  return count
})

const hasActiveMode = computed(() => activeCount.value > 0)

const triggerTooltip = computed(() => {
  if (hasActiveMode.value) {
    return `Đang bật ${activeCount.value} chế độ hỗ trợ (Alt+E, Alt+S)`
  }
  return 'Tùy chọn hiển thị và trợ năng (Alt+E, Alt+S)'
})

function toggleOpen() {
  isOpen.value = !isOpen.value
}

function closePopover() {
  isOpen.value = false
}

function handleClickOutside(event: MouseEvent) {
  if (!isOpen.value) return
  if (popoverRoot.value && !popoverRoot.value.contains(event.target as Node)) {
    closePopover()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
