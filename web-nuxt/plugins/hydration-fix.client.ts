// Workaround for @unhead/vue v2.1.15 bug: during hydration of async components,
// the head entry's watcher may not fire before onUnmounted, leaving the entry
// object undefined — causing "Cannot read properties of undefined (reading 'dispose')".
// This intercepts Vue's error handler to suppress that specific non-fatal error.
export default defineNuxtPlugin((nuxtApp) => {
  const original = nuxtApp.vueApp.config.errorHandler
  nuxtApp.vueApp.config.errorHandler = (err, instance, info) => {
    const msg = err instanceof Error ? err.message : String(err)
    if (msg.includes("reading 'dispose'")) {
      return
    }
    if (original) {
      return original(err, instance, info)
    }
    throw err
  }
})
