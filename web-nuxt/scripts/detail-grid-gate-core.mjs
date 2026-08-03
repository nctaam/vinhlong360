import { spawn } from 'node:child_process'
import { basename } from 'node:path'

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
    const tripHits = geometry.actions?.trip_hits || []
    if (geometry.actions?.trip_control_count !== 3 || tripHits.length !== 3) {
      failures.push({ code: 'trip-controls-missing', message: 'Detail route must expose exactly three trip actions' })
    }
    if (tripHits.some(hit => !hit?.belongs)) {
      failures.push({ code: 'trip-hit-owner', message: 'one or more trip actions do not own their center hit target' })
    }
    if (!(geometry.contact?.controls || []).length || geometry.contact.controls.some(control => !control?.hit?.belongs)) {
      failures.push({ code: 'contact-hit-owner', message: 'one or more contact actions do not own their center hit target' })
    }
    const sticky = geometry.sticky
    const stickyPresent = sticky?.present ?? Boolean(sticky)
    if (!stickyPresent) {
      failures.push({ code: 'sticky-contract-missing', message: 'legacy sticky CTA contract is missing from the Detail route' })
    } else if (sticky.display !== 'none' && sticky.visibility !== 'hidden' && sticky.rect?.width > 0 && sticky.rect?.height > 0) {
      failures.push({ code: 'sticky-visible', message: 'legacy sticky CTA is visible alongside ContactWidget' })
    }
  }

  const lightbox = state?.lightbox
  if (lightbox) {
    if (!lightbox.opened || !lightbox.aria_modal || !lightbox.surface_visible || !lightbox.media_visible) {
      failures.push({ code: 'lightbox-open-failed', message: 'photo action did not open a visible modal lightbox' })
    }
    if (!lightbox.close_hit?.belongs || lightbox.close_hit?.stable === false) {
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

export function ownedBrowserProcessIds(processes, ownership) {
  return (processes || [])
    .filter(processInfo => isOwnedBrowserProcess(processInfo, ownership))
    .map(processInfo => Number(processInfo.pid || 0))
    .filter(pid => Number.isInteger(pid) && pid > 0)
}

export function hasStableOwnedHit(samples, requiredConsecutive) {
  const required = Number(requiredConsecutive)
  if (!Number.isInteger(required) || required <= 0) return false
  let consecutive = 0
  for (let index = (samples || []).length - 1; index >= 0; index -= 1) {
    const sample = samples[index]
    if (!sample?.present || !sample?.visible || !sample?.belongs) break
    consecutive += 1
    if (consecutive >= required) return true
  }
  return false
}

function terminateCapturedProcess(child) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return
  if (process.platform === 'win32' && child.pid) {
    const killer = spawn('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], {
      stdio: 'ignore',
      windowsHide: true,
    })
    killer.once('error', () => child.kill())
    return
  }
  child.kill('SIGTERM')
}

export function runCaptured(command, args, options = {}) {
  const { timeoutMs = 10000, ...spawnOptions } = options
  return new Promise((resolveRun, reject) => {
    const child = spawn(command, args, { ...spawnOptions, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true })
    let stdout = ''
    let stderr = ''
    let timedOut = false
    let settled = false
    let timer
    let forceTimer
    let abandonTimer
    const append = (current, chunk) => (current + String(chunk)).slice(-512 * 1024)
    const finish = (handler, value) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      clearTimeout(forceTimer)
      clearTimeout(abandonTimer)
      child.off('error', onError)
      child.off('exit', onExit)
      handler(value)
    }
    const timeoutError = () => new Error(basename(command) + ' timed out after ' + timeoutMs + 'ms')
    const onError = error => finish(reject, timedOut ? timeoutError() : error)
    const onExit = code => {
      if (timedOut) {
        finish(reject, timeoutError())
      } else if (code === 0) {
        finish(resolveRun, { stdout, stderr })
      } else {
        finish(reject, new Error(basename(command) + ' exited with code ' + code + (stderr.trim() ? ': ' + stderr.trim() : '')))
      }
    }
    child.stdout?.on('data', chunk => { stdout = append(stdout, chunk) })
    child.stderr?.on('data', chunk => { stderr = append(stderr, chunk) })
    child.once('error', onError)
    child.once('exit', onExit)
    timer = setTimeout(() => {
      timedOut = true
      terminateCapturedProcess(child)
      forceTimer = setTimeout(() => {
        if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL')
      }, 1000)
      abandonTimer = setTimeout(() => {
        finish(reject, timeoutError())
      }, 3000)
    }, timeoutMs)
  })
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
  const reasons = evidence.reasons || []
  const blockerReasons = reasons.filter(reason => !/^(?:mobile|desktop):/u.test(String(reason?.code || '')))
  const retainedBlockers = blockerReasons.slice(0, 12)
  const retainedStateReasons = reasons
    .filter(reason => !retainedBlockers.includes(reason))
    .slice(0, Math.max(0, 12 - retainedBlockers.length))
  const retained = new Set([...retainedStateReasons, ...retainedBlockers])
  evidence.reasons = reasons.filter(reason => retained.has(reason)).slice(0, 12)
  evidence.reason_summary = {
    total_count: reasons.length,
    retained_count: evidence.reasons.length,
    truncated_count: Math.max(0, reasons.length - evidence.reasons.length),
    truncated: reasons.length > evidence.reasons.length,
    blocker_codes: blockerReasons.map(reason => String(reason?.code || '')).filter(Boolean),
  }
  return evidence
}
