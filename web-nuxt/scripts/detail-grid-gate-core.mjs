import { spawn } from 'node:child_process'
import { readdir, readFile, readlink } from 'node:fs/promises'
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
    || !asset.theme_binding?.opposite_mode_seeded_before_navigation
    || !asset.theme_binding?.opposite_mode_confirmed_before_click
    || !asset.theme_binding?.target_control_hit_owned
    || !asset.theme_binding?.physical_transition_observed
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

export function isOwnedBrowserProcess(processInfo, { profile, browserPath, marker = '' }) {
  if (!processInfo?.executablePath || !processInfo?.commandLine || !profile || !browserPath) return false
  if (processInfo.executablePath.toLowerCase() !== browserPath.toLowerCase()) return false
  if (marker && !commandHasMarker(processInfo, marker)) return false
  if (Array.isArray(processInfo.argv)) {
    return processInfo.argv.includes('--user-data-dir=' + profile)
  }
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
  assertOppositeTheme,
  applyRequestedTheme,
  waitForStableReadiness,
}) {
  capture.start()
  try {
    await navigate()
    const oppositeThemeState = await assertOppositeTheme()
    const themeState = await applyRequestedTheme()
    await waitForStableReadiness()
    const previewAssets = await capture.verify()
    return { oppositeThemeState, themeState, previewAssets }
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
  if (Array.isArray(expected.argv) && JSON.stringify(current.argv || []) !== JSON.stringify(expected.argv)) return false
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
    let settled = false
    let timeoutTimer
    const append = (current, chunk) => (current + String(chunk)).slice(-512 * 1024)
    const onStdout = chunk => { stdout = append(stdout, chunk) }
    const onStderr = chunk => { stderr = append(stderr, chunk) }
    const finish = (handler, value) => {
      if (settled) return
      settled = true
      clearTimeout(timeoutTimer)
      child.stdout?.off('data', onStdout)
      child.stderr?.off('data', onStderr)
      child.off('error', onError)
      child.off('exit', onExit)
      handler(value)
    }
    const onError = error => {
      finish(reject, error)
    }
    const onExit = code => {
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
    timeoutTimer = setTimeout(() => {
      child.stdout?.destroy()
      child.stderr?.destroy()
      child.unref()
      finish(reject, new Error(basename(command) + ' timed out after ' + timeoutMs
        + 'ms; helper identity was not verified, so no bare-PID termination was attempted'))
    }, timeoutMs)
  })
}

const windowsStartIdentityFunction = [
  'function Get-Vl360StartIdentity([object]$ProcessItem) {',
  '  if ($null -eq $ProcessItem -or $null -eq $ProcessItem.CreationDate) { return "" }',
  '  $ticks = $ProcessItem.CreationDate.ToUniversalTime().Ticks.ToString([Globalization.CultureInfo]::InvariantCulture)',
  '  return "win:utc-ticks:" + $ticks',
  '}',
]

export function assertHighConfidenceProcessIdentityPlatform(platform = process.platform) {
  if (platform !== 'win32' && platform !== 'linux') {
    throw new Error('high-confidence process identity is unsupported on ' + platform)
  }
}

export function parseLinuxProcStat(source) {
  const match = /^(\d+)\s+\((.*)\)\s+\S\s+(.+)$/su.exec(String(source || '').trim())
  if (!match) return null
  const remainingFields = match[3].trim().split(/\s+/u)
  const parentPid = Number(remainingFields[0] || 0)
  const startTicks = remainingFields[18] || ''
  if (!Number.isInteger(parentPid) || parentPid < 0 || !/^\d+$/u.test(startTicks)) return null
  return { pid: Number(match[1]), parentPid, startTicks }
}

function isMissingProcessError(error) {
  return ['ENOENT', 'ESRCH'].includes(error?.code)
}

export async function readLinuxProcessIdentity(pid, io = {}) {
  if (!Number.isInteger(pid) || pid <= 0) return null
  const readFileOperation = io.readFile || readFile
  const readlinkOperation = io.readlink || readlink
  try {
    const procRoot = '/proc/' + pid
    const [statSource, executablePath, commandLineBuffer] = await Promise.all([
      readFileOperation(procRoot + '/stat', 'utf8'),
      readlinkOperation(procRoot + '/exe'),
      readFileOperation(procRoot + '/cmdline'),
    ])
    const stat = parseLinuxProcStat(statSource)
    if (!stat || stat.pid !== pid) return null
    const commandLine = Buffer.isBuffer(commandLineBuffer)
      ? commandLineBuffer.toString('utf8')
      : String(commandLineBuffer || '')
    const argv = commandLine.split('\0').filter(Boolean)
    if (!executablePath || argv.length === 0) return null
    return {
      pid,
      parentPid: stat.parentPid,
      startIdentity: 'linux:proc-start-ticks:' + stat.startTicks,
      executablePath: String(executablePath),
      commandLine,
      argv,
    }
  } catch (error) {
    if (isMissingProcessError(error)) return null
    throw error
  }
}

async function captureProcessSnapshot(timeoutMs) {
  assertHighConfidenceProcessIdentityPlatform()
  if (process.platform === 'win32') {
    const source = [
      "$ErrorActionPreference = 'Stop'",
      ...windowsStartIdentityFunction,
      '$items = @(Get-CimInstance Win32_Process | ForEach-Object { [PSCustomObject]@{ ProcessId = [int]$_.ProcessId; ParentProcessId = [int]$_.ParentProcessId; StartIdentity = Get-Vl360StartIdentity $_; ExecutablePath = [string]$_.ExecutablePath; CommandLine = [string]$_.CommandLine } })',
      'ConvertTo-Json -InputObject $items -Compress',
    ].join('; ')
    const result = await runBoundedHelper(
      'powershell.exe',
      ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', source],
      { timeoutMs },
    )
    const parsed = JSON.parse(result.stdout.trim() || '[]')
    return (Array.isArray(parsed) ? parsed : [parsed]).map(processInfo => ({
      pid: Number(processInfo.ProcessId || 0),
      parentPid: Number(processInfo.ParentProcessId || 0),
      startIdentity: String(processInfo.StartIdentity || ''),
      executablePath: String(processInfo.ExecutablePath || ''),
      commandLine: String(processInfo.CommandLine || ''),
    })).filter(processInfo => processInfo.pid > 0 && processInfo.startIdentity)
  }

  const entries = await readdir('/proc', { withFileTypes: true })
  const identities = await Promise.all(entries
    .filter(entry => entry.isDirectory() && /^\d+$/u.test(entry.name))
    .map(entry => readLinuxProcessIdentity(Number(entry.name)).catch(error => {
      if (isMissingProcessError(error) || error?.code === 'EACCES') return null
      throw error
    })))
  return identities.filter(Boolean)
}

async function captureProcessIdentity(pid, timeoutMs) {
  if (!Number.isInteger(pid) || pid <= 0) return null
  assertHighConfidenceProcessIdentityPlatform()
  if (process.platform === 'win32') {
    const source = [
      "$ErrorActionPreference = 'Stop'",
      ...windowsStartIdentityFunction,
      '$item = Get-CimInstance Win32_Process -Filter "ProcessId=' + pid + '"',
      'if ($null -eq $item) { exit 0 }',
      '$result = [PSCustomObject]@{ ProcessId = [int]$item.ProcessId; ParentProcessId = [int]$item.ParentProcessId; StartIdentity = Get-Vl360StartIdentity $item; ExecutablePath = [string]$item.ExecutablePath; CommandLine = [string]$item.CommandLine }',
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
  return readLinuxProcessIdentity(pid)
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

async function signalOwnedIdentityLinux(identity, marker, signal, timeoutMs) {
  const source = [
    "const fs = require('node:fs')",
    'const expected = JSON.parse(process.env.VL360_GATE_PROCESS_IDENTITY)',
    "const marker = process.env.VL360_GATE_PROCESS_MARKER || ''",
    'const pid = Number(expected.pid)',
    'const result = status => process.stdout.write(JSON.stringify({ pid, status }))',
    'const missing = error => error && (error.code === "ENOENT" || error.code === "ESRCH")',
    'let statSource, executablePath, commandLine',
    'try { statSource = fs.readFileSync(`/proc/${pid}/stat`, "utf8"); executablePath = fs.readlinkSync(`/proc/${pid}/exe`); commandLine = fs.readFileSync(`/proc/${pid}/cmdline`, "utf8") } catch (error) { if (missing(error)) { result("already-exited"); process.exit(0) } throw error }',
    'const match = /^(\\d+)\\s+\\((.*)\\)\\s+\\S\\s+(.+)$/s.exec(statSource.trim())',
    'const fields = match ? match[3].trim().split(/\\s+/) : []',
    'const current = match ? { pid: Number(match[1]), startIdentity: `linux:proc-start-ticks:${fields[18] || ""}`, executablePath, commandLine, argv: commandLine.split("\\0").filter(Boolean) } : null',
    'const same = current && current.pid === expected.pid && current.startIdentity === expected.startIdentity && current.executablePath === expected.executablePath && current.commandLine === expected.commandLine && JSON.stringify(current.argv) === JSON.stringify(expected.argv || []) && (!marker || current.commandLine.includes(marker))',
    'if (!same) { result("identity-mismatch"); process.exit(0) }',
    'try { process.kill(pid, process.env.VL360_GATE_PROCESS_SIGNAL); result("signalled") } catch (error) { if (missing(error)) result("already-exited"); else throw error }',
  ].join('; ')
  const result = await runBoundedHelper(process.execPath, ['-e', source], {
    env: {
      ...process.env,
      VL360_GATE_PROCESS_IDENTITY: JSON.stringify(identity),
      VL360_GATE_PROCESS_MARKER: marker,
      VL360_GATE_PROCESS_SIGNAL: signal,
    },
    timeoutMs,
  })
  return JSON.parse(result.stdout.trim() || '{"pid":0,"status":"helper-empty"}')
}

async function terminateOwnedIdentityLinux(identity, marker, deadline, helperTimeoutMs) {
  const remainingMs = () => Math.max(0, deadline - Date.now())
  const termStatus = await signalOwnedIdentityLinux(
    identity,
    marker,
    'SIGTERM',
    Math.min(helperTimeoutMs, Math.max(500, remainingMs())),
  )
  if (termStatus.status !== 'signalled') return termStatus
  let remaining = await waitForIdentityExit(identity, Math.min(1500, remainingMs()), helperTimeoutMs)
  if (!remaining) return termStatus
  const killStatus = await signalOwnedIdentityLinux(
    identity,
    marker,
    'SIGKILL',
    Math.min(helperTimeoutMs, Math.max(500, remainingMs())),
  )
  if (killStatus.status === 'signalled') {
    remaining = await waitForIdentityExit(identity, Math.min(1500, remainingMs()), helperTimeoutMs)
  }
  if (remaining && killStatus.status === 'signalled') {
    throw new Error('owned process identity did not exit: ' + identity.pid)
  }
  return killStatus
}

async function terminateOwnedIdentitiesWindows(identities, marker, timeoutMs) {
  if (identities.length === 0) return []
  const source = [
    "$ErrorActionPreference = 'Stop'",
    ...windowsStartIdentityFunction,
    '$parsedExpected = $env:VL360_GATE_PROCESS_IDENTITIES | ConvertFrom-Json',
    '$expected = if ($parsedExpected -is [System.Array]) { $parsedExpected } else { @($parsedExpected) }',
    '$marker = [string]$env:VL360_GATE_PROCESS_MARKER',
    '$results = @()',
    'foreach ($identity in $expected) {',
    '  $pidValue = [int]$identity.pid',
    '  $current = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $pidValue)',
    '  if ($null -eq $current) { $results += [PSCustomObject]@{ pid = $pidValue; status = "already-exited" }; continue }',
    '  $sameStart = (Get-Vl360StartIdentity $current) -ceq ([string]$identity.startIdentity)',
    '  $sameExecutable = [StringComparer]::OrdinalIgnoreCase.Equals([string]$current.ExecutablePath, [string]$identity.executablePath)',
    '  $sameCommand = ([string]$current.CommandLine) -ceq ([string]$identity.commandLine)',
    '  $sameMarker = [string]::IsNullOrEmpty($marker) -or ([string]$current.CommandLine).Contains($marker)',
    '  if (-not ($sameStart -and $sameExecutable -and $sameCommand -and $sameMarker)) { $results += [PSCustomObject]@{ pid = $pidValue; status = "identity-mismatch" }; continue }',
    '  try {',
    '    Stop-Process -Id $pidValue -Force -ErrorAction Stop',
    '    $results += [PSCustomObject]@{ pid = $pidValue; status = "terminated" }',
    '  } catch {',
    '    $after = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $pidValue)',
    '    if ($null -eq $after) { $results += [PSCustomObject]@{ pid = $pidValue; status = "already-exited-after-validation" }; continue }',
    '    $afterMatches = ((Get-Vl360StartIdentity $after) -ceq ([string]$identity.startIdentity)) -and [StringComparer]::OrdinalIgnoreCase.Equals([string]$after.ExecutablePath, [string]$identity.executablePath) -and (([string]$after.CommandLine) -ceq ([string]$identity.commandLine)) -and ([string]::IsNullOrEmpty($marker) -or ([string]$after.CommandLine).Contains($marker))',
    '    if (-not $afterMatches) { $results += [PSCustomObject]@{ pid = $pidValue; status = "identity-mismatch-after-validation" }; continue }',
    '    throw',
    '  }',
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
  return Array.isArray(parsed) ? parsed : [parsed]
}

export async function terminateExactProcessIdentities(identities, {
  marker = '',
  timeoutMs = 5000,
  deadline = Date.now() + timeoutMs,
} = {}) {
  assertHighConfidenceProcessIdentityPlatform()
  const valid = (identities || []).filter(identity => (
    Number.isInteger(identity?.pid)
    && identity.pid > 0
    && identity.startIdentity
    && identity.executablePath
    && identity.commandLine
  ))
  if (valid.length !== (identities || []).length) {
    throw new Error('one or more process identities are incomplete; no unverified PID was killed')
  }
  if (process.platform === 'win32') {
    return terminateOwnedIdentitiesWindows(valid, marker, timeoutMs)
  }
  const statuses = []
  for (const identity of valid) {
    statuses.push(await terminateOwnedIdentityLinux(identity, marker, deadline, timeoutMs))
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
    await terminateExactProcessIdentities(terminationOrder, {
      marker: ownershipMarker,
      timeoutMs: Math.min(helperTimeoutMs, Math.max(1000, deadline - Date.now())),
      deadline,
    })

    if (ownershipMarker) {
      for (let round = 0; round < 2 && Date.now() < deadline; round += 1) {
        const snapshot = await captureProcessSnapshot(Math.min(helperTimeoutMs, Math.max(250, deadline - Date.now())))
        const lateOwned = snapshot.filter(processInfo => commandHasMarker(processInfo, ownershipMarker))
        if (lateOwned.length === 0) break
        for (const identity of lateOwned) {
          captured.set(identity.pid + ':' + identity.startIdentity, identity)
        }
        await terminateExactProcessIdentities(lateOwned, {
          marker: ownershipMarker,
          timeoutMs: Math.min(helperTimeoutMs, Math.max(1000, deadline - Date.now())),
          deadline,
        })
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
