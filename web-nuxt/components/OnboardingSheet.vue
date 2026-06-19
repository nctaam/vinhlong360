<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="visible" class="onboarding-overlay" @click.self="dismiss">
        <div class="onboarding-sheet" role="dialog" aria-modal="true" aria-label="Chào mừng đến vinhlong360" ref="sheetEl">
          <button type="button" class="sheet-close" aria-label="Đóng" @click="dismiss">&times;</button>
          <div class="sheet-header">
            <span class="sheet-emoji">🌴</span>
            <h2>Chào mừng đến vinhlong360</h2>
            <p>Khám phá Vĩnh Long, Bến Tre, Trà Vinh — theo cách của người bản địa.</p>
          </div>
          <div class="sheet-features">
            <div class="sheet-feature" v-for="(f, i) in features" :key="i">
              <span class="sf-icon">{{ f.icon }}</span>
              <div>
                <strong>{{ f.title }}</strong>
                <p>{{ f.desc }}</p>
              </div>
            </div>
          </div>
          <div class="sheet-actions">
            <NuxtLink to="/du-lich" class="btn btn-primary" @click="dismiss">Khám phá ngay</NuxtLink>
            <button type="button" class="btn btn-ghost" @click="dismiss">Để sau</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
const visible = ref(false)
const sheetEl = ref<HTMLElement | null>(null)

const features = [
  { icon: '🗺️', title: '1.400+ địa điểm & đặc sản', desc: 'Trải nghiệm miệt vườn, làng nghề, món ngon — cập nhật liên tục từ cộng đồng.' },
  { icon: '📅', title: 'Lịch trình gợi ý theo mùa', desc: 'Lộ trình chi tiết với bản đồ, đặc sản mùa nào, lễ hội sắp diễn ra.' },
  { icon: '💬', title: 'Hỏi đáp AI bản địa', desc: 'Chat trực tiếp để lên kế hoạch — nhanh hơn tìm kiếm thủ công.' },
]

function onSheetKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') { dismiss(); return }
  if (e.key !== 'Tab' || !sheetEl.value) return
  const focusable = Array.from(
    sheetEl.value.querySelectorAll<HTMLElement>('button, a[href], [tabindex]:not([tabindex="-1"])')
  ).filter(el => el.offsetParent !== null)
  if (!focusable.length) return
  const first = focusable[0], last = focusable[focusable.length - 1]
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
}

onMounted(() => {
  const key = 'vl360_onboarding_seen'
  if (!localStorage.getItem(key)) {
    setTimeout(() => { visible.value = true }, 1500)
  }
})

watch(visible, (v) => {
  if (v) {
    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', onSheetKeydown)
    nextTick(() => sheetEl.value?.querySelector<HTMLElement>('a, button')?.focus())
  } else {
    document.body.style.overflow = ''
    document.removeEventListener('keydown', onSheetKeydown)
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', onSheetKeydown)
  document.body.style.overflow = ''
})

function dismiss() {
  visible.value = false
  localStorage.setItem('vl360_onboarding_seen', '1')
}
</script>
