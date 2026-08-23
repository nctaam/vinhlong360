export function useReveal(options: { threshold?: number; rootMargin?: string } = {}) {
  if (!import.meta.client) return

  const threshold = options.threshold ?? 0.1
  const rootMargin = options.rootMargin ?? '0px 0px -30px 0px'
  let observer: IntersectionObserver | null = null
  let mutations: MutationObserver | null = null
  const timers: ReturnType<typeof setTimeout>[] = []

  const revealAll = () =>
    document.querySelectorAll('.reveal:not(.revealed)').forEach(el => el.classList.add('revealed'))
  const observeAll = () =>
    observer && document.querySelectorAll('.reveal:not(.revealed)').forEach(el => observer!.observe(el))

  onMounted(() => {
    nextTick(() => {
      if (!('IntersectionObserver' in window)) { revealAll(); return }

      observer = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            ;(entry.target as HTMLElement).classList.add('revealed')
            observer!.unobserve(entry.target)
          }
        }
      }, { threshold, rootMargin })

      observeAll()

      // A hydration mismatch can swap the observed nodes for fresh ones the observer
      // never saw → those sections stay stuck at opacity:0. Re-scan shortly after
      // hydration settles to observe the new nodes (keeps the scroll-reveal effect).
      timers.push(setTimeout(observeAll, 400))

      // Hard safety net: if anything at/above the fold is still unrevealed after a beat,
      // the observer is broken for it — reveal EVERYTHING so content is never invisible.
      timers.push(setTimeout(() => {
        const vh = window.innerHeight || 0
        const stuck = [...document.querySelectorAll('.reveal:not(.revealed)')]
          .some(el => el.getBoundingClientRect().top < vh)
        if (stuck) revealAll()
      }, 2000))

      // Hai mốc 400ms/2000ms ở trên là một CUỘC ĐUA, và nới hằng số chỉ dời cuộc
      // đua chứ không kết thúc nó: phần tử .reveal vào DOM sau lần quét cuối sẽ
      // không bao giờ được observe, không bao giờ nhận .revealed, và
      // `html.js .reveal { opacity: 0 }` (base.css:314) giữ nó TÀNG HÌNH VĨNH
      // VIỄN — kể cả khi người dùng cuộn thẳng tới nó. Đây là mất nội dung, không
      // phải mất hiệu ứng. Nội dung nạp trễ (danh sách theo bộ lọc, kết quả tìm,
      // trang phân trang) rơi đúng vào đó.
      //
      // MutationObserver là API gốc, không thêm phụ thuộc nào (§B8). Nó xoá hẳn
      // cuộc đua thay vì dời nó.
      mutations = new MutationObserver((records) => {
        for (const record of records) {
          for (const node of record.addedNodes) {
            if (!(node instanceof HTMLElement)) continue
            if (node.classList.contains('reveal') && !node.classList.contains('revealed')) {
              observer!.observe(node)
            }
            node.querySelectorAll?.('.reveal:not(.revealed)').forEach(el => observer!.observe(el))
          }
        }
      })
      mutations.observe(document.body, { childList: true, subtree: true })
    })
  })

  onUnmounted(() => {
    observer?.disconnect()
    observer = null
    mutations?.disconnect()
    mutations = null
    timers.forEach(clearTimeout)
  })
}
