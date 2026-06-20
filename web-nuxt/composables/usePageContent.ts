import { pageFieldDefault } from '~/utils/pageManifest'

/**
 * A2 — read per-page content overrides from the CMS.
 *
 * Returns `f(field, explicitFallback?)`:
 *   1. CMS override under `page.<slug>.<field>` if present & non-empty, else
 *   2. `explicitFallback` if provided (for dynamic/templated fields), else
 *   3. the manifest default for that field (the canonical content).
 *
 * Pages call `f('hero_title')` and render identically to before until an admin
 * sets an override — the manifest holds the single copy of the default text.
 */
export function usePageContent(slug: string) {
  const { get } = useSiteSettings()
  const page = computed<Record<string, unknown>>(
    () => (get(`page.${slug}`, {}) as Record<string, unknown>) || {},
  )

  function f<T = string>(field: string, explicitFallback?: T): T {
    const v = page.value?.[field]
    if (v !== undefined && v !== null && v !== '') return v as T
    if (explicitFallback !== undefined) return explicitFallback
    return pageFieldDefault(slug, field) as unknown as T
  }

  return { page, f }
}
