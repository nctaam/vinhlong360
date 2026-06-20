/**
 * reveal-enhance — belt-and-suspenders for the JS-gated `.reveal` pattern.
 *
 * The inline head script in nuxt.config.ts adds `js` to <html> before first
 * paint (so .reveal content is never hidden when JS is absent/slow). This
 * client plugin re-asserts the class on the client as a fallback in case the
 * inline script was stripped (e.g. strict CSP, ad-blocker injecting late, or a
 * static-export edge case). It is intentionally tiny and idempotent.
 *
 * The actual reveal-on-scroll behaviour (adding `.revealed`) lives in
 * composables/useReveal.ts and is left untouched.
 */
export default defineNuxtPlugin(() => {
  if (typeof document !== 'undefined') {
    document.documentElement.classList.add('js')
  }
})
