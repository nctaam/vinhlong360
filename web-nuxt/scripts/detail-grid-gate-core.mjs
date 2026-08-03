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

function childExited(child) {
  return !child || child.exitCode !== null || child.signalCode !== null
}

function processIsRunning(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false
  try {
    process.kill(pid, 0)
    return true
  } catch {
    return false
  }
}

function runBoundedHelper(command, args, { timeoutMs, env } = {}) {
  return new Promise((resolveRun, reject) => {
    const child = spawn(command, args, {
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    })
    let stdout = ''
    let stderr = ''
    let timedOut = false
    let settled = false
    let timeoutTimer
    let exitTimer
    const append = (current, chunk) => (current + String(chunk)).slice(-512 * 1024)
    const onStdout = chunk => { stdout = append(stdout, chunk) }
    const onStderr = chunk => { stderr = append(stderr, chunk) }
    const finish = (handler, value) => {
      if (settled) return
      settled = true
      clearTimeout(timeoutTimer)
      clearTimeout(exitTimer)
      child.stdout?.off('data', onStdout)
      child.stderr?.off('data', onStderr)
      child.off('error', onError)
      child.off('exit', onExit)
      handler(value)
    }
    const onError = error => {
      if (!timedOut) finish(reject, error)
    }
    const onExit = code => {
      if (timedOut) {
        finish(reject, new Error(basename(command) + ' timed out after ' + timeoutMs + 'ms'))
      } else if (code === 0) {
        finish(resolveRun, { stdout, stderr })
      } else {
        finish(reject, new Error(basename(command) + ' exited with code ' + code + (stderr.trim() ? ': ' + stderr.trim() : '')))
      }
    }
    child.stdout?.on('data', onStdout)
    child.stderr?.on('data', onStderr)
    child.once('error', onError)
    child.once('exit', onExit)
    timeoutTimer = setTimeout(() => {
      timedOut = true
      if (!childExited(child)) child.kill('SIGKILL')
      exitTimer = setTimeout(() => {
        finish(reject, new Error(basename(command) + ' cleanup helper did not exit after timeout'))
      }, 1000)
    }, timeoutMs)
  })
}

function buildProcessTree(rootPid, processes) {
  const tree = new Set([rootPid])
  let changed = true
  while (changed) {
    changed = false
    for (const processInfo of processes) {
      if (!tree.has(processInfo.pid) && tree.has(processInfo.parentPid)) {
        tree.add(processInfo.pid)
        changed = true
      }
    }
  }
  return [...tree]
}

async function captureProcessTree(rootPid, timeoutMs) {
  let processes
  if (process.platform === 'win32') {
    const source = [
      "$ErrorActionPreference = 'Stop'",
      '$items = @(Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId)',
      'ConvertTo-Json -InputObject $items -Compress',
    ].join('; ')
    const result = await runBoundedHelper(
      'powershell.exe',
      ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', source],
      { timeoutMs },
    )
    const parsed = JSON.parse(result.stdout.trim() || '[]')
    processes = (Array.isArray(parsed) ? parsed : [parsed]).map(processInfo => ({
      pid: Number(processInfo.ProcessId || 0),
      parentPid: Number(processInfo.ParentProcessId || 0),
    }))
  } else {
    const result = await runBoundedHelper('ps', ['-axo', 'pid=,ppid='], { timeoutMs })
    processes = result.stdout.split(/\r?\n/u).map(line => {
      const match = /^\s*(\d+)\s+(\d+)\s*$/u.exec(line)
      return match ? { pid: Number(match[1]), parentPid: Number(match[2]) } : null
    }).filter(Boolean)
  }
  return buildProcessTree(rootPid, processes)
}

async function waitForProcessTreeExit(pids, timeoutMs) {
  const deadline = Date.now() + timeoutMs
  let remaining = pids.filter(processIsRunning)
  while (remaining.length > 0 && Date.now() < deadline) {
    await new Promise(resolveWait => setTimeout(resolveWait, 50))
    remaining = pids.filter(processIsRunning)
  }
  return remaining
}

async function terminateCapturedProcessTree(child, cleanupTimeoutMs) {
  if (!child?.pid) throw new Error('captured process has no PID for cleanup verification')
  const rootPid = child.pid
  const helperTimeoutMs = Math.max(1000, Math.min(5000, cleanupTimeoutMs - 1000))
  let treePids = [rootPid]
  let discoveryError
  try {
    treePids = await captureProcessTree(rootPid, helperTimeoutMs)
  } catch (error) {
    discoveryError = error
  }
  let terminationError

  if (process.platform === 'win32') {
    try {
      await runBoundedHelper('taskkill.exe', ['/PID', String(rootPid), '/T', '/F'], { timeoutMs: helperTimeoutMs })
    } catch (error) {
      terminationError = error
    }
  } else if (!childExited(child)) {
    try {
      process.kill(-rootPid, 'SIGTERM')
    } catch (error) {
      terminationError = error
    }
  }

  const remaining = await waitForProcessTreeExit(treePids, Math.max(500, cleanupTimeoutMs - helperTimeoutMs))
  if (remaining.length > 0) {
    throw new Error('captured process tree cleanup failed for PID(s): ' + remaining.join(','))
  }
  if (discoveryError) {
    throw new Error('captured process tree was terminated but descendant verification failed: ' + discoveryError.message)
  }
  if (terminationError && processIsRunning(rootPid)) throw terminationError
  return treePids
}

export function runCaptured(command, args, options = {}) {
  const { timeoutMs = 10000, cleanupTimeoutMs = 7000, ...spawnOptions } = options
  return new Promise((resolveRun, reject) => {
    const child = spawn(command, args, {
      ...spawnOptions,
      detached: process.platform === 'win32' ? Boolean(spawnOptions.detached) : true,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    })
    let stdout = ''
    let stderr = ''
    let timedOut = false
    let settled = false
    let timer
    const append = (current, chunk) => (current + String(chunk)).slice(-512 * 1024)
    const onStdout = chunk => { stdout = append(stdout, chunk) }
    const onStderr = chunk => { stderr = append(stderr, chunk) }
    const finish = (handler, value) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      child.stdout?.off('data', onStdout)
      child.stderr?.off('data', onStderr)
      child.off('error', onError)
      child.off('exit', onExit)
      handler(value)
    }
    const timeoutError = cleanup => {
      const error = new Error(basename(command) + ' timed out after ' + timeoutMs + 'ms')
      error.cleanupVerified = true
      error.terminatedPids = cleanup
      return error
    }
    const onError = error => {
      if (!timedOut) finish(reject, error)
    }
    const onExit = code => {
      if (timedOut) return
      if (code === 0) {
        finish(resolveRun, { stdout, stderr })
      } else {
        finish(reject, new Error(basename(command) + ' exited with code ' + code + (stderr.trim() ? ': ' + stderr.trim() : '')))
      }
    }
    child.stdout?.on('data', onStdout)
    child.stderr?.on('data', onStderr)
    child.once('error', onError)
    child.once('exit', onExit)
    timer = setTimeout(() => {
      timedOut = true
      terminateCapturedProcessTree(child, cleanupTimeoutMs).then(
        cleanup => finish(reject, timeoutError(cleanup)),
        cleanupError => {
          const error = new Error(
            basename(command) + ' timed out after ' + timeoutMs + 'ms; cleanup failed: ' + cleanupError.message,
          )
          error.cleanupVerified = false
          error.cause = cleanupError
          finish(reject, error)
        },
      )
    }, timeoutMs)
  })
}

export function recordGateReason(evidence, code, message) {
  if (!Array.isArray(evidence.reasons)) evidence.reasons = []
  evidence.reasons.push({ code: String(code).slice(0, 100), message: String(message).slice(0, 300) })
}

export function finalizeGateEvidence(evidence, { blocked = false } = {}) {
  if ((evidence.cleanup_errors || []).length > 0 && !(evidence.reasons || []).some(reason => reason?.code === 'cleanup-failed')) {
    recordGateReason(evidence, 'cleanup-failed', 'owned Chrome resources were not fully cleaned up')
  }
  evidence.verdict = blocked
    ? 'blocked'
    : (evidence.reasons || []).length === 0 && (evidence.cleanup_errors || []).length === 0 ? 'pass' : 'fail'
  return evidence
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
