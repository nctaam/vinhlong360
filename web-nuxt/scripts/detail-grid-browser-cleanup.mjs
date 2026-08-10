import {
  cleanupOwnedProcessSet,
  WINDOWS_EXACT_PROCESS_CLEANUP_TIMEOUT_MS,
  terminateExactProcessIdentities,
} from './detail-grid-gate-core.mjs'

export function cleanupOwnedBrowserProcesses(browser, {
  cleanup = cleanupOwnedProcessSet,
  listOwnedProcesses,
  terminateOwnedProcesses = terminateExactProcessIdentities,
  platform = process.platform,
}) {
  return cleanup({
    listOwnedProcesses: options => listOwnedProcesses(browser, options),
    terminateOwnedProcesses: (identities, options) => terminateOwnedProcesses(identities, {
      ...options,
      marker: browser.marker,
      timeoutMs: Math.min(5000, options.timeoutMs),
    }),
    rootPid: browser.child?.pid || 0,
    timeoutMs: platform === 'win32'
      ? WINDOWS_EXACT_PROCESS_CLEANUP_TIMEOUT_MS
      : 10_000,
  })
}
