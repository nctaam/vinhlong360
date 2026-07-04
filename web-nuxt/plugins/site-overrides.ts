import { applySiteOverrides } from '~/composables/useConstants'

/**
 * A1 — apply CMS metadata overrides (categories.*, metadata.office_kind) into
 * the shared TYPE_META / AREA_META / OFFICE_KIND maps before the app renders.
 *
 * Runs universally (server + client) and AWAITS the settings fetch so the very
 * first render already reflects overrides — no hydration mismatch. Uses the
 * same useAsyncData key as useSiteSettings() so the fetch is deduped (one call
 * per request; client reuses the SSR payload). If Postgres/API is down the
 * fetch yields {} and the maps simply keep their hardcoded defaults.
 */
export default defineNuxtPlugin(async () => {
  // Never let a settings fetch failure stall or break app init — overrides are
  // a non-essential enhancement; on any error the maps keep their defaults.
  try {
    const { data } = await useAsyncData('site-settings',
      () => apiFetch<Record<string, unknown>>('/api/site-settings'),
      { server: true, default: () => ({}) },
    )
    const s = (data.value || {}) as Record<string, unknown>
    applySiteOverrides({
      typeOverrides: s['categories.type_overrides'],
      areaOverrides: s['categories.area_overrides'],
      officeKind: s['metadata.office_kind'],
      interests: s['metadata.interests'],
    })
  } catch {
    // ignore — defaults remain in effect
  }
})
