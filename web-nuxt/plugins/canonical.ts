// Canonical is set PER-PAGE via useSeoHelpers' canonicalUrl() in each page's
// useHead (encoded-id form). A global route-path canonical here rendered a SECOND,
// conflicting <link rel="canonical"> on every page, so this plugin is intentionally
// a no-op. Pages that need a canonical must set their own.
export default defineNuxtPlugin(() => {})
