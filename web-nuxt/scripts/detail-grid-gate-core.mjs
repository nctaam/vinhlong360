export function hasExactZeroMinWidth(declarations) {
  return /(?:^|;)\s*min-width\s*:\s*(?:0|0px)\s*(?:;|$)/iu.test(String(declarations || ''))
}

export function collectStateFailures(state) {
  const failures = []
  const relevantErrors = (state?.console_errors || []).filter(entry => !entry?.allowed_reason)
  if (relevantErrors.length > 0) {
    failures.push({ code: 'console-errors', message: `${relevantErrors.length} relevant browser error(s) observed` })
  }

  const geometry = state?.geometry
  if (geometry) {
    if (geometry.viewport?.width !== state.viewport?.width || geometry.viewport?.height !== state.viewport?.height) {
      failures.push({ code: 'viewport-mismatch', message: 'rendered viewport differs from the requested viewport' })
    }
    const hero = geometry.hero
    if (
      !hero?.cover_rect?.width
      || !hero?.cover_rect?.height
      || !hero?.image_rect?.width
      || !hero?.image_rect?.height
      || !hero?.image_loaded_class
      || !hero?.image_complete
      || !(hero?.image_natural_width > 0)
      || !(hero?.image_natural_height > 0)
      || !hero?.image_in_cover
    ) {
      failures.push({ code: 'hero-regression', message: 'Detail hero is not visibly loaded inside its cover' })
    }
    if ((geometry.actions?.trip_photo_intersection?.area || 0) > 1) {
      failures.push({ code: 'trip-photo-overlap', message: 'trip and photo actions overlap' })
    }
    if (!geometry.actions?.photo_hit?.belongs) {
      failures.push({ code: 'photo-hit-owner', message: 'photo action does not own its center hit target' })
    }
    if ((geometry.actions?.trip_hits || []).some(hit => !hit?.belongs)) {
      failures.push({ code: 'trip-hit-owner', message: 'one or more trip actions do not own their center hit target' })
    }
    if (!(geometry.contact?.controls || []).length || geometry.contact.controls.some(control => !control?.hit?.belongs)) {
      failures.push({ code: 'contact-hit-owner', message: 'one or more contact actions do not own their center hit target' })
    }
    const sticky = geometry.sticky
    if (sticky && sticky.display !== 'none' && sticky.visibility !== 'hidden' && sticky.rect?.width > 0 && sticky.rect?.height > 0) {
      failures.push({ code: 'sticky-visible', message: 'legacy sticky CTA is visible alongside ContactWidget' })
    }
  }

  const lightbox = state?.lightbox
  if (lightbox) {
    if (!lightbox.opened || !lightbox.aria_modal || !lightbox.surface_visible || !lightbox.media_visible) {
      failures.push({ code: 'lightbox-open-failed', message: 'photo action did not open a visible modal lightbox' })
    }
    if (!lightbox.close_hit?.belongs) {
      failures.push({ code: 'lightbox-close-hit-owner', message: 'lightbox close action does not own its center hit target' })
    }
    if (!lightbox.closed) failures.push({ code: 'lightbox-close-failed', message: 'lightbox did not close after activation' })
  }

  return failures
}

export function isFreshNavigationState({ expectedUrl, previousDocumentToken, href, readyState, documentToken }) {
  return href === expectedUrl
    && readyState === 'complete'
    && Boolean(documentToken)
    && documentToken !== previousDocumentToken
}

export function collectAssetSetFailures(states) {
  const failures = []
  const assets = states.map(state => state?.preview_assets || {})
  if (assets.some(asset => (
    !(asset.asset_paths || []).length
    || !(asset.css_paths || []).length
    || !(asset.js_paths || []).length
    || !asset.detail_css_path
    || !/^[a-f0-9]{64}$/u.test(asset.fingerprint_sha256 || '')
  ))) {
    failures.push({ code: 'asset-binding-incomplete', message: 'one or more states lack bound CSS or JavaScript assets' })
  }
  const viewportGroups = new Map()
  states.forEach((state, index) => {
    const group = state?.viewport_name || 'unknown'
    if (!viewportGroups.has(group)) viewportGroups.set(group, [])
    viewportGroups.get(group).push(assets[index])
  })
  const mismatchedGroup = [...viewportGroups.values()].some(groupAssets => {
    const signatures = groupAssets.map(asset => JSON.stringify(asset.asset_paths || []))
    const fingerprints = groupAssets.map(asset => asset.fingerprint_sha256 || '')
    return new Set(signatures).size > 1 || new Set(fingerprints).size > 1
  })
  if (mismatchedGroup) {
    failures.push({ code: 'asset-set-state-mismatch', message: 'themes within a viewport did not bind the same exact asset set and fingerprint' })
  }
  return failures
}

export function isOwnedBrowserProcess(processInfo, { profile, browserPath }) {
  if (!processInfo?.executablePath || !processInfo?.commandLine || !profile || !browserPath) return false
  if (processInfo.executablePath.toLowerCase() !== browserPath.toLowerCase()) return false
  const escapedProfile = profile.replace(/[.*+?^${}()|[\]\\]/gu, '\\$&')
  const profileArgument = new RegExp(
    '(?:^|\\s)"?--user-data-dir=(?:"' + escapedProfile + '"|' + escapedProfile + ')"?(?=\\s|$)',
    'iu',
  )
  return profileArgument.test(processInfo.commandLine)
}

export function compactGateEvidence(evidence) {
  for (const state of evidence.states || []) {
    state.console_errors = (state.console_errors || []).slice(0, 2)
    state.relevant_console_errors = (state.relevant_console_errors || []).slice(0, 2)
    if (state.preview_assets) {
      state.preview_assets.asset_paths = []
      state.preview_assets.css_paths = []
      state.preview_assets.js_paths = []
      state.preview_assets.asset_set_recorded_globally = true
    }
    if (state.geometry?.contact) state.geometry.contact.controls = (state.geometry.contact.controls || []).slice(0, 2)
  }
  evidence.reasons = (evidence.reasons || []).slice(0, 12)
  return evidence
}
