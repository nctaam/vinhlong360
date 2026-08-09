import {
  PUBLIC_CAPABILITY_FLAGS,
  resolveFeatureFlag,
  resolvePublicCapabilityMode,
  type PublicCapability,
} from '~/utils/featureFlags'

/**
 * A4 — read feature flags from the CMS.
 * Existing modules keep their registry defaults. Unknown and adaptive rollout
 * flags fail closed so deterministic search/detail/planner UI remains usable.
 */
export function useFeature() {
  const { get } = useSiteSettings()
  const source = computed<{ available: boolean; flags: Record<string, unknown> }>(() => {
    try {
      const value = get('features.flags', {})
      return value && typeof value === 'object' && !Array.isArray(value)
        ? { available: true, flags: value as Record<string, unknown> }
        : { available: false, flags: {} }
    } catch {
      return { available: false, flags: {} }
    }
  })
  const flags = computed(() => source.value.flags)

  function enabled(key: string): boolean {
    if (!source.value.available) return false
    return resolveFeatureFlag(key, flags.value)
  }

  function capabilityMode(capability: PublicCapability) {
    return resolvePublicCapabilityMode(capability, flags.value)
  }

  const capabilityModes = computed(() => Object.fromEntries(
    (Object.keys(PUBLIC_CAPABILITY_FLAGS) as PublicCapability[]).map(capability => [capability, capabilityMode(capability)]),
  ) as Record<PublicCapability, ReturnType<typeof capabilityMode>>)

  return { flags, enabled, capabilityMode, capabilityModes }
}
