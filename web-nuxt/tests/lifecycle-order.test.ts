import { describe, expect, it } from 'vitest'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'

function collectVueFiles(dir: string): string[] {
  const entries = readdirSync(dir)
  const files: string[] = []
  for (const entry of entries) {
    const full = join(dir, entry)
    const st = statSync(full)
    if (st.isDirectory()) {
      files.push(...collectVueFiles(full))
    } else if (entry.endsWith('.vue')) {
      files.push(full)
    }
  }
  return files
}

function extractScriptSetup(content: string): string | null {
  const match = content.match(/<script\s+[^>]*\bsetup\b[^>]*>([\s\S]*?)<\/script>/i)
  return match && typeof match[1] === 'string' ? match[1] : null
}

describe('Vue 3 Lifecycle Order Contract', () => {
  const root = resolve(__dirname, '..')
  const pagesDir = resolve(root, 'pages')
  const componentsDir = resolve(root, 'components')
  const vueFiles = [...collectVueFiles(pagesDir), ...collectVueFiles(componentsDir)]

  function findViolations(): Array<{ file: string; hook: string; line: number }> {
    const violations: Array<{ file: string; hook: string; line: number }> = []
    const lifecycleHooks = ['onMounted', 'onBeforeMount', 'onBeforeUnmount', 'onUnmounted', 'onActivated', 'onDeactivated']

    for (const file of vueFiles) {
      const content = readFileSync(file, 'utf8')
      const script = extractScriptSetup(content)
      if (!script) continue

      const lines = script.split('\n')
      let seenTopLevelAwait = false
      let braceDepth = 0

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i] ?? ''
        const openBraces = (line.match(/{/g) || []).length
        const closeBraces = (line.match(/}/g) || []).length

        // Top level await: await at depth 0
        if (braceDepth === 0 && /\bawait\s+/.test(line)) {
          seenTopLevelAwait = true
        }

        braceDepth += openBraces - closeBraces
        if (braceDepth < 0) braceDepth = 0

        if (seenTopLevelAwait) {
          for (const hook of lifecycleHooks) {
            const hookPattern = new RegExp(`\\b${hook}\\s*\\(`, 'u')
            if (hookPattern.test(line)) {
              violations.push({
                file: file.replace(root, '').replace(/\\/g, '/'),
                hook,
                line: i + 1,
              })
            }
          }
        }
      }
    }
    return violations
  }

  it('guarantees remediated core pages have zero lifecycle order violations', () => {
    const violations = findViolations()
    const remediatedFiles = [
      '/pages/bai-viet/[id].vue',
      '/pages/nguoi-dung/[id].vue',
      '/pages/dia-diem/[id].vue',
      '/pages/cong-dong.vue',
    ]

    const targetViolations = violations.filter(v => remediatedFiles.includes(v.file))
    expect(targetViolations).toEqual([])
  })

  // Hard ratchet on legacy backlog: baseline established at 19 violations across 12 legacy files.
  // No new violations may ever be added; ratchets downward as Phase 2 refactoring proceeds.
  it('enforces hard ratchet on legacy lifecycle order violations (must not exceed baseline 19)', () => {
    const violations = findViolations()
    const MAX_ALLOWED_LEGACY_VIOLATIONS = 19
    expect(violations.length).toBeLessThanOrEqual(MAX_ALLOWED_LEGACY_VIOLATIONS)
  })
})
