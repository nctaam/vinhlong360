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
  if (assets.some(asset => (
    !asset.theme_binding?.capture_started_before_navigation
    || !asset.theme_binding?.requested_mode_seeded_before_navigation
    || !asset.theme_binding?.requested_mode_selected_before_finalize
    || !asset.theme_binding?.stable_readiness_before_finalize
  ))) {
    failures.push({ code: 'asset-theme-binding-incomplete', message: 'one or more asset fingerprints were finalized before requested theme readiness' })
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

export async function captureThemeBoundAssets({
  capture,
  navigate,
  applyRequestedTheme,
  waitForStableReadiness,
}) {
  capture.start()
  try {
    await navigate()
    const themeState = await applyRequestedTheme()
    await waitForStableReadiness()
    const previewAssets = await capture.verify()
    return { themeState, previewAssets }
  } finally {
    capture.stop()
  }
}

function childExited(child) {
  return !child || child.exitCode !== null || child.signalCode !== null
}

function normalizedExecutable(value) {
  const executable = String(value || '').replace(/\//gu, process.platform === 'win32' ? '\\' : '/')
  return process.platform === 'win32' ? executable.toLowerCase() : executable
}

export function matchesProcessIdentity(expected, current) {
  if (!expected || !current) return false
  if (!Number.isInteger(expected.pid) || expected.pid <= 0 || current.pid !== expected.pid) return false
  if (!expected.startIdentity || current.startIdentity !== expected.startIdentity) return false
  if (
    expected.executablePath
    && normalizedExecutable(current.executablePath) !== normalizedExecutable(expected.executablePath)
  ) return false
  if (expected.commandLine && current.commandLine !== expected.commandLine) return false
  return true
}

function commandHasMarker(processInfo, marker) {
  return Boolean(marker) && String(processInfo?.commandLine || '').includes(marker)
}

export function classifyOwnedProcessTree(rootIdentity, processes, marker = '') {
  const snapshot = (processes || []).filter(processInfo => Number.isInteger(processInfo?.pid) && processInfo.pid > 0)
  const currentRoot = snapshot.find(processInfo => matchesProcessIdentity(rootIdentity, processInfo))
  if (!currentRoot || (marker && !commandHasMarker(currentRoot, marker))) return { owned: [], unverified: [] }

  const treePids = new Set([currentRoot.pid])
  let changed = true
  while (changed) {
    changed = false
    for (const processInfo of snapshot) {
      if (!treePids.has(processInfo.pid) && treePids.has(processInfo.parentPid)) {
        treePids.add(processInfo.pid)
        changed = true
      }
    }
  }

  const owned = [currentRoot]
  const unverified = []
  for (const processInfo of snapshot) {
    if (processInfo.pid === currentRoot.pid) continue
    if (treePids.has(processInfo.pid)) {
      if (marker && commandHasMarker(processInfo, marker)) owned.push(processInfo)
      else unverified.push(processInfo)
    } else if (marker && commandHasMarker(processInfo, marker)) {
      // A unique caller marker keeps late or reparented descendants attributable.
      owned.push(processInfo)
    }
  }
  return { owned, unverified }
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

async function captureProcessSnapshot(timeoutMs) {
  let processes
  if (process.platform === 'win32') {
    const source = [
      "$ErrorActionPreference = 'Stop'",
      '$items = @(Get-CimInstance Win32_Process | ForEach-Object { [PSCustomObject]@{ ProcessId = [int]$_.ProcessId; ParentProcessId = [int]$_.ParentProcessId; StartIdentity = [string]$_.CreationDate; ExecutablePath = [string]$_.ExecutablePath; CommandLine = [string]$_.CommandLine } })',
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
      startIdentity: String(processInfo.StartIdentity || ''),
      executablePath: String(processInfo.ExecutablePath || ''),
      commandLine: String(processInfo.CommandLine || ''),
    }))
  } else {
    const result = await runBoundedHelper('ps', ['-axo', 'pid=,ppid=,lstart=,command='], { timeoutMs })
    processes = result.stdout.split(/\r?\n/u).map(line => {
      const match = /^\s*(\d+)\s+(\d+)\s+(\S+\s+\S+\s+\d+\s+\d{2}:\d{2}:\d{2}\s+\d{4})\s+(.+)$/u.exec(line)
      return match ? {
        pid: Number(match[1]),
        parentPid: Number(match[2]),
        startIdentity: match[3],
        executablePath: '',
        commandLine: match[4],
      } : null
    }).filter(Boolean)
  }
  return processes.filter(processInfo => processInfo.pid > 0 && processInfo.startIdentity)
}

async function captureProcessIdentity(pid, timeoutMs) {
  if (!Number.isInteger(pid) || pid <= 0) return null
  if (process.platform === 'win32') {
    const source = [
      "$ErrorActionPreference = 'Stop'",
      '$item = Get-CimInstance Win32_Process -Filter "ProcessId=' + pid + '"',
      'if ($null -eq $item) { exit 0 }',
      '$result = [PSCustomObject]@{ ProcessId = [int]$item.ProcessId; ParentProcessId = [int]$item.ParentProcessId; StartIdentity = [string]$item.CreationDate; ExecutablePath = [string]$item.ExecutablePath; CommandLine = [string]$item.CommandLine }',
      'ConvertTo-Json -InputObject $result -Compress',
    ].join('; ')
    const result = await runBoundedHelper(
      'powershell.exe',
      ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', source],
      { timeoutMs },
    )
    if (!result.stdout.trim()) return null
    const processInfo = JSON.parse(result.stdout)
    return {
      pid: Number(processInfo.ProcessId || 0),
      parentPid: Number(processInfo.ParentProcessId || 0),
      startIdentity: String(processInfo.StartIdentity || ''),
      executablePath: String(processInfo.ExecutablePath || ''),
      commandLine: String(processInfo.CommandLine || ''),
    }
  }
  const result = await runBoundedHelper('ps', ['-p', String(pid), '-o', 'pid=,ppid=,lstart=,command='], { timeoutMs })
  const match = /^\s*(\d+)\s+(\d+)\s+(\S+\s+\S+\s+\d+\s+\d{2}:\d{2}:\d{2}\s+\d{4})\s+(.+)$/u.exec(result.stdout.trim())
  return match ? {
    pid: Number(match[1]),
    parentPid: Number(match[2]),
    startIdentity: match[3],
    executablePath: '',
    commandLine: match[4],
  } : null
}

async function waitForIdentityExit(identity, timeoutMs, helperTimeoutMs) {
  const deadline = Date.now() + timeoutMs
  let current
  while (Date.now() < deadline) {
    current = await captureProcessIdentity(identity.pid, Math.min(helperTimeoutMs, Math.max(500, deadline - Date.now())))
    if (!matchesProcessIdentity(identity, current)) return null
    await new Promise(resolveWait => setTimeout(resolveWait, 50))
  }
  return current
}

async function terminateOwnedIdentityPosix(identity, deadline, helperTimeoutMs) {
  const remainingMs = () => Math.max(0, deadline - Date.now())
  const before = await captureProcessIdentity(identity.pid, Math.min(helperTimeoutMs, Math.max(500, remainingMs())))
  if (!matchesProcessIdentity(identity, before)) return false

  let terminationError
  try {
    process.kill(identity.pid, 'SIGTERM')
  } catch (error) {
    terminationError = error
  }

  let remaining = await waitForIdentityExit(identity, Math.min(1500, remainingMs()), helperTimeoutMs)
  if (remaining) {
    const immediatelyBeforeKill = await captureProcessIdentity(identity.pid, Math.min(helperTimeoutMs, Math.max(500, remainingMs())))
    if (!matchesProcessIdentity(identity, immediatelyBeforeKill)) return true
    try {
      process.kill(identity.pid, 'SIGKILL')
    } catch (error) {
      terminationError ||= error
    }
    remaining = await waitForIdentityExit(identity, Math.min(1500, remainingMs()), helperTimeoutMs)
  }
  if (remaining) {
    throw terminationError || new Error('owned process identity did not exit: ' + identity.pid)
  }
  return true
}

async function terminateOwnedIdentitiesWindows(identities, marker, timeoutMs) {
  if (identities.length === 0) return []
  const source = [
    "$ErrorActionPreference = 'Stop'",
    '$parsedExpected = $env:VL360_GATE_PROCESS_IDENTITIES | ConvertFrom-Json',
    '$expected = if ($parsedExpected -is [System.Array]) { $parsedExpected } else { @($parsedExpected) }',
    '$marker = [string]$env:VL360_GATE_PROCESS_MARKER',
    '$results = @()',
    'foreach ($identity in $expected) {',
    '  $pidValue = [int]$identity.pid',
    '  $current = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $pidValue)',
    '  if ($null -eq $current) { $results += [PSCustomObject]@{ pid = $pidValue; status = "already-exited" }; continue }',
    '  $sameStart = ([string]$current.CreationDate) -ceq ([string]$identity.startIdentity)',
    '  $sameExecutable = [StringComparer]::OrdinalIgnoreCase.Equals([string]$current.ExecutablePath, [string]$identity.executablePath)',
    '  $sameCommand = ([string]$current.CommandLine) -ceq ([string]$identity.commandLine)',
    '  $sameMarker = [string]::IsNullOrEmpty($marker) -or ([string]$current.CommandLine).Contains($marker)',
    '  if (-not ($sameStart -and $sameExecutable -and $sameCommand -and $sameMarker)) { $results += [PSCustomObject]@{ pid = $pidValue; status = "identity-mismatch" }; continue }',
    '  Stop-Process -Id $pidValue -Force -ErrorAction Stop',
    '  $results += [PSCustomObject]@{ pid = $pidValue; status = "terminated" }',
    '}',
    'ConvertTo-Json -InputObject $results -Compress',
  ].join('; ')
  const result = await runBoundedHelper(
    'powershell.exe',
    ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', source],
    {
      env: {
        ...process.env,
        VL360_GATE_PROCESS_IDENTITIES: JSON.stringify(identities),
        VL360_GATE_PROCESS_MARKER: marker,
      },
      timeoutMs,
    },
  )
  const parsed = JSON.parse(result.stdout.trim() || '[]')
  const statuses = Array.isArray(parsed) ? parsed : [parsed]
  const mismatched = statuses.filter(status => status.status === 'identity-mismatch')
  if (mismatched.length > 0) {
    throw new Error('owned process identity changed immediately before termination; no mismatched PID was killed: '
      + mismatched.map(status => status.pid).join(','))
  }
  return statuses
}

async function terminateCapturedProcessTree(child, cleanupTimeoutMs, initialIdentityPromise, ownershipMarker) {
  if (!child?.pid) throw new Error('captured process has no PID for cleanup verification')
  const rootPid = child.pid
  const deadline = Date.now() + cleanupTimeoutMs
  const helperTimeoutMs = Math.max(1000, Math.min(4000, cleanupTimeoutMs - 1000))
  const initialIdentity = await initialIdentityPromise
  if (!initialIdentity) throw new Error('captured process identity was unavailable before timeout; cleanup is unverified')
  if (initialIdentity.pid !== rootPid) throw new Error('captured process identity PID changed before timeout')

  const beforeTermination = await captureProcessSnapshot(Math.min(helperTimeoutMs, Math.max(250, deadline - Date.now())))
  const classification = classifyOwnedProcessTree(initialIdentity, beforeTermination, ownershipMarker)
  if (classification.owned.length === 0) {
    throw new Error('captured process identity no longer matched immediately before termination; no PID was killed')
  }

  const captured = new Map(classification.owned.map(identity => [identity.pid + ':' + identity.startIdentity, identity]))
  try {
    const terminationOrder = [...classification.owned].sort((left, right) => (left.pid === rootPid ? 1 : 0) - (right.pid === rootPid ? 1 : 0))
    if (process.platform === 'win32') {
      await terminateOwnedIdentitiesWindows(
        terminationOrder,
        ownershipMarker,
        Math.min(helperTimeoutMs, Math.max(1000, deadline - Date.now())),
      )
    } else {
      for (const identity of terminationOrder) {
        await terminateOwnedIdentityPosix(identity, deadline, helperTimeoutMs)
      }
    }

    if (ownershipMarker) {
      for (let round = 0; round < 2 && Date.now() < deadline; round += 1) {
        const snapshot = await captureProcessSnapshot(Math.min(helperTimeoutMs, Math.max(250, deadline - Date.now())))
        const lateOwned = snapshot.filter(processInfo => commandHasMarker(processInfo, ownershipMarker))
        if (lateOwned.length === 0) break
        for (const identity of lateOwned) {
          captured.set(identity.pid + ':' + identity.startIdentity, identity)
        }
        if (process.platform === 'win32') {
          await terminateOwnedIdentitiesWindows(
            lateOwned,
            ownershipMarker,
            Math.min(helperTimeoutMs, Math.max(1000, deadline - Date.now())),
          )
        } else {
          for (const identity of lateOwned) await terminateOwnedIdentityPosix(identity, deadline, helperTimeoutMs)
        }
      }
    }

    const verification = await captureProcessSnapshot(Math.min(helperTimeoutMs, Math.max(250, deadline - Date.now())))
    const remainingOwned = [...captured.values()].filter(identity => verification.some(processInfo => matchesProcessIdentity(identity, processInfo)))
    const lateMarkerOwned = ownershipMarker ? verification.filter(processInfo => commandHasMarker(processInfo, ownershipMarker)) : []
    const remainingUnverified = classification.unverified.filter(identity => (
      verification.some(processInfo => matchesProcessIdentity(identity, processInfo))
    ))
    if (remainingOwned.length > 0 || lateMarkerOwned.length > 0 || remainingUnverified.length > 0) {
      throw new Error('owned process cleanup remained unverified for PID(s): ' + [...new Set([
        ...remainingOwned.map(identity => identity.pid),
        ...lateMarkerOwned.map(identity => identity.pid),
        ...remainingUnverified.map(identity => identity.pid),
      ])].join(','))
    }
  } catch (error) {
    error.capturedProcessIdentities = [...captured.values()]
    throw error
  }
  return [...captured.values()]
}

export function runCaptured(command, args, options = {}) {
  const {
    timeoutMs = 10000,
    cleanupTimeoutMs = 12000,
    ownershipMarker = '',
    ...spawnOptions
  } = options
  return new Promise((resolveRun, reject) => {
    const child = spawn(command, args, {
      ...spawnOptions,
      detached: process.platform === 'win32' ? Boolean(spawnOptions.detached) : true,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    })
    const identityTimeoutMs = Math.max(1000, Math.min(4000, cleanupTimeoutMs - 1000))
    const initialIdentityPromise = child.pid
      ? captureProcessIdentity(child.pid, identityTimeoutMs)
          .catch(() => null)
      : Promise.resolve(null)
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
      error.capturedProcessIdentities = cleanup
      error.terminatedPids = cleanup.map(identity => identity.pid)
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
      terminateCapturedProcessTree(child, cleanupTimeoutMs, initialIdentityPromise, ownershipMarker).then(
        cleanup => finish(reject, timeoutError(cleanup)),
        cleanupError => {
          const error = new Error(
            basename(command) + ' timed out after ' + timeoutMs + 'ms; cleanup failed: ' + cleanupError.message,
          )
          error.cleanupVerified = false
          error.cause = cleanupError
          error.capturedProcessIdentities = cleanupError.capturedProcessIdentities || []
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
