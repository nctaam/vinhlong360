import { mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, it } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'

import { useModalA11y } from '../composables/useModalA11y'

/**
 * useModalA11y KHÔNG có test nào trước đợt này — ba file test hiện có chỉ
 * `mockNuxtImport('useModalA11y', () => () => undefined)`, tức mock nó đi.
 * Đó là vùng mù đúng nghĩa (CLAUDE.md B3), và nó đang khoá cuộn TOÀN TRANG cho
 * cả những thứ không phải modal — ChatWidget là panel 400×520 ở góc, không
 * backdrop, không chặn chuột, nhưng vẫn khoá cuộn cả trang.
 *
 * Test này phủ hành vi khoá cuộn TRƯỚC khi thêm option `lockScroll`, để bản mặc
 * định không đổi được mà không ai biết.
 */
function harness(open: ReturnType<typeof ref<boolean>>, options?: Parameters<typeof useModalA11y>[2]) {
  return defineComponent({
    setup() {
      const el = ref<HTMLElement | null>(null)
      useModalA11y(open as never, el, options)
      return () => h('div', { ref: el }, [h('button', 'x')])
    },
  })
}

describe('useModalA11y — khoá cuộn', () => {
  it('mặc định VẪN khoá cuộn khi mở và trả lại khi đóng', async () => {
    document.body.style.overflow = ''
    const open = ref(false)
    await mountSuspended(harness(open))
    await nextTick()

    open.value = true
    await nextTick()
    expect(document.body.style.overflow).toBe('hidden')

    open.value = false
    await nextTick()
    expect(document.body.style.overflow).toBe('')
  })

  it('lockScroll: false thì KHÔNG đụng tới cuộn trang, cả lúc mở lẫn lúc đóng', async () => {
    // Vế "lúc đóng" quan trọng ngang vế "lúc mở": deactivate() ghi
    // body.style.overflow = '' VÔ ĐIỀU KIỆN và watch chạy với immediate:true,
    // nên một panel mount trễ có thể xoá trắng khoá cuộn mà thứ khác vừa đặt.
    document.body.style.overflow = 'hidden'
    const open = ref(false)
    await mountSuspended(harness(open, { lockScroll: false }))
    await nextTick()
    expect(document.body.style.overflow).toBe('hidden')

    open.value = true
    await nextTick()
    expect(document.body.style.overflow).toBe('hidden')

    open.value = false
    await nextTick()
    expect(document.body.style.overflow).toBe('hidden')
  })
})

describe('useModalA11y — option dạng hàm', () => {
  it('đọc lại hàm ở MỖI lần mở, không chốt giá trị lúc mount', async () => {
    // Đây là bẫy thật: options được destructure đúng một lần, nên nếu bên gọi
    // truyền boolean lấy từ ref thì giá trị bị đóng băng ở trạng thái lúc mount.
    // ChatWidget cần khoá cuộn ở ≤480px và KHÔNG khoá ở trên đó, mà nó chỉ biết
    // được viewport sau onMounted — tức luôn sau lúc destructure.
    document.body.style.overflow = ''
    const open = ref(false)
    const mobile = ref(false)
    await mountSuspended(harness(open, { lockScroll: () => mobile.value }))
    await nextTick()

    open.value = true
    await nextTick()
    expect(document.body.style.overflow).toBe('')   // desktop: không khoá

    open.value = false
    await nextTick()
    mobile.value = true
    open.value = true
    await nextTick()
    expect(document.body.style.overflow).toBe('hidden')  // mobile: khoá

    open.value = false
    await nextTick()
    expect(document.body.style.overflow).toBe('')
  })
})
