// Route focus + announcement for SPA navigations (a11y / VoiceOver parity).
//
// On client-side route changes the browser does NOT reset focus the way a full
// page load does: keyboard users keep focus on the link they just activated
// (which Vue has since removed), and screen readers stay silent about the new
// page. Apple's own apps move VoiceOver focus to the new screen's content on
// navigation — we mirror that here by focusing the <main> landmark and
// announcing the new title through a polite live region.
//
// Scroll-to-top is already handled by Nuxt's scrollBehavior, so we focus with
// { preventScroll: true } to avoid fighting it. The initial load is skipped —
// the browser/SR already announce the document on first paint.
export default defineNuxtPlugin((nuxtApp) => {
  let announcer: HTMLElement | null = null
  function ensureAnnouncer(): HTMLElement {
    if (announcer && document.body.contains(announcer)) return announcer
    announcer = document.createElement('div')
    announcer.id = 'route-announcer'
    announcer.className = 'sr-only'
    announcer.setAttribute('aria-live', 'polite')
    announcer.setAttribute('aria-atomic', 'true')
    document.body.appendChild(announcer)
    return announcer
  }

  let first = true
  nuxtApp.hook('page:finish', () => {
    if (first) { first = false; return } // initial load — already announced by the browser

    // Defer a frame so useHead has flushed the new document.title.
    requestAnimationFrame(() => {
      const main = document.getElementById('main-content')
      if (main) {
        if (!main.hasAttribute('tabindex')) main.setAttribute('tabindex', '-1')
        try { main.focus({ preventScroll: true }) } catch { main.focus() }
      }

      const title = (document.title || '').split('|')[0].trim() || document.title
      if (title) {
        const a = ensureAnnouncer()
        // Clear then set on the next frame so the SR re-announces even when the
        // title text is unchanged between routes.
        a.textContent = ''
        requestAnimationFrame(() => { a.textContent = `Đã mở: ${title}` })
      }
    })
  })
})
