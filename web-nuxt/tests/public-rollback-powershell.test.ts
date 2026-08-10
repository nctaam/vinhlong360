import { spawnSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const repoRoot = resolve(process.cwd(), '..')
const rollbackScript = resolve(repoRoot, 'scripts/ops/disable_public_feature_flags.ps1')
const reportPath = resolve(repoRoot, 'docs/superpowers/reports/2026-08-09-adaptive-nocturne-public-upgrade-verification.md')

function psLiteral(value: string) {
  return `'${value.replaceAll("'", "''")}'`
}

describe('public capability rollback PowerShell', () => {
  it('preserves unrelated PSCustomObject flags and disables all five public capabilities', () => {
    const settingsJson = JSON.stringify({
      settings: [
        { key: 'features.flags', value: { existing_unrelated_flag: true, public_personalization_v1: true } },
      ],
    })
    const command = process.platform === 'win32' ? 'powershell.exe' : 'pwsh'
    const script = [
      "$ErrorActionPreference = 'Stop'",
      `$settings = ${psLiteral(settingsJson)} | ConvertFrom-Json`,
      `$result = & ${psLiteral(rollbackScript)} -Settings $settings`,
      '$result',
    ].join('; ')
    const completed = spawnSync(command, ['-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script], {
      cwd: repoRoot,
      encoding: 'utf8',
    })

    expect(completed.status, completed.stderr || completed.stdout).toBe(0)
    const result = JSON.parse(completed.stdout.trim()) as { value: Record<string, boolean> }
    expect(result.value.existing_unrelated_flag).toBe(true)
    expect(result.value).toMatchObject({
      public_personalization_v1: false,
      public_recommendation_v1: false,
      public_search_expansion_v1: false,
      public_optimizer_v1: false,
      public_proactive_notices_v1: false,
    })
  })

  it('keeps the operator snippet on the executable PSCustomObject conversion path', () => {
    const report = readFileSync(reportPath, 'utf8')
    expect(report).toContain('.value).PSObject.Properties |')
    expect(report).not.toContain('$flags = @{} +')
  })
})
