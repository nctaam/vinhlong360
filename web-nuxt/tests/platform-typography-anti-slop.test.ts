import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Platform-Wide Typography Anti-Slop Discipline', () => {
  const filesToCheck = [
    '../assets/css/variables.css',
    '../assets/css/base.css',
    '../assets/css/catalog.css',
    '../assets/css/shell.css',
    '../assets/css/home-nocturne.css',
  ]

  it('bans Times New Roman fallback across every stylesheet in the project', () => {
    for (const relPath of filesToCheck) {
      const content = readFileSync(resolve(__dirname, relPath), 'utf8')
      expect(content, `File ${relPath} still contains Times New Roman fallback!`).not.toContain('Times New Roman')
    }
  })

  it('ensures Lora serif is prioritized in editorial font stacks', () => {
    const vars = readFileSync(resolve(__dirname, '../assets/css/variables.css'), 'utf8')
    expect(vars).toMatch(/--font-editorial:\s*'Lora'/)
  })
})
