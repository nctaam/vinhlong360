<template><span ref="el">{{ text }}</span></template>

<script setup lang="ts">
// Đếm-lên số khi cuộn vào tầm (IntersectionObserver — KHÔNG dùng scroll-driven CSS vì
// Firefox chưa hỗ trợ). SSR + no-JS + reduced-motion = hiện thẳng giá-trị cuối (không nhảy).
const props = defineProps<{ value: string | number }>()
const raw = String(props.value)
const m = raw.match(/^([\d.,]+)(.*)$/)
const target = m ? parseInt(m[1].replace(/[.,]/g, ''), 10) : NaN
const suffix = m ? m[2] : ''

const text = ref(raw)          // mặc-định = giá-trị cuối (đúng cho SSR/hydrate)
const el = ref<HTMLElement | null>(null)

onMounted(() => {
  if (Number.isNaN(target) || !el.value) return
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const io = new IntersectionObserver((entries) => {
    if (!entries[0]?.isIntersecting) return
    io.disconnect()
    const dur = 1100
    const t0 = performance.now()
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / dur)
      const eased = 1 - Math.pow(1 - p, 3)   // easeOutCubic
      text.value = Math.round(target * eased).toLocaleString('vi-VN') + suffix
      if (p < 1) requestAnimationFrame(tick)
      else text.value = raw
    }
    requestAnimationFrame(tick)
  }, { threshold: 0.4 })
  io.observe(el.value)
})
</script>
