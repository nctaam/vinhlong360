import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

const BASE_DIR = path.resolve(__dirname, '..')

function readFile(relPath: string): string {
  return fs.readFileSync(path.join(BASE_DIR, relPath), 'utf-8')
}

describe('Mốc 106: Micro-Typography Gate & WCAG 2.2 SC 1.4.4 Compliance', () => {
  describe('CSS Stylesheets Micro-Typography', () => {
    it('bảo đảm admin-entities.css không chứa font-size: 9px và sử dụng token var(--text-2xs)', () => {
      const content = readFile('assets/css/admin-entities.css')
      expect(content).not.toMatch(/font-size:\s*9px/)
      expect(content).toContain('var(--text-2xs)')
    })

    it('bảo đảm events.css không chứa font-size 8px, 9px, 10px vi mô', () => {
      const content = readFile('assets/css/events.css')
      expect(content).not.toMatch(/font-size:\s*8px/)
      expect(content).not.toMatch(/font-size:\s*9px/)
      expect(content).not.toMatch(/font-size:\s*10px/)
    })

    it('bảo đảm base.css .caret sử dụng token var(--text-2xs)', () => {
      const content = readFile('assets/css/base.css')
      expect(content).not.toMatch(/\.caret\s*\{[^}]*font-size:\s*\.65rem/)
      expect(content).toMatch(/\.caret\s*\{[^}]*font-size:\s*var\(--text-2xs/)
    })

    it('bảo đảm components.css .notif-badge sử dụng token var(--text-2xs)', () => {
      const content = readFile('assets/css/components.css')
      expect(content).not.toMatch(/\.notif-badge\s*\{[^}]*font-size:\s*\.65rem/)
      expect(content).toMatch(/\.notif-badge\s*\{[^}]*font-size:\s*var\(--text-2xs/)
    })
  })

  describe('Vue Components & Pages Micro-Typography', () => {
    it('bảo đảm lien-he.vue không chứa font-size: .55rem', () => {
      const content = readFile('pages/lien-he.vue')
      expect(content).not.toMatch(/font-size:\s*\.55rem/)
      expect(content).toMatch(/\.bm-sla\s+span\s*\{[^}]*font-size:\s*var\(--text-2xs/)
    })

    it('bảo đảm index.vue không chứa font-size: .6rem trong fy-disclosure', () => {
      const content = readFile('pages/index.vue')
      expect(content).not.toMatch(/font-size:\s*\.6rem/)
      expect(content).toMatch(/\[data-short-label\]\)\s*\{[^}]*font-size:\s*var\(--text-2xs/)
    })

    it('bảo đảm danh-ba.vue .fac-verified sử dụng var(--text-2xs)', () => {
      const content = readFile('pages/danh-ba.vue')
      expect(content).not.toMatch(/\.fac-verified\s*\{[^}]*font-size:\s*\.65rem/)
      expect(content).toMatch(/\.fac-verified\s*\{[^}]*font-size:\s*var\(--text-2xs/)
    })

    it('bảo đảm EntityCard.vue .ca-more sử dụng var(--text-2xs)', () => {
      const content = readFile('components/EntityCard.vue')
      expect(content).not.toMatch(/\.ca-more\s*\{[^}]*font-size:\s*\.65rem/)
      expect(content).toMatch(/\.ca-more\s*\{[^}]*font-size:\s*var\(--text-2xs/)
    })

    it('bảo đảm theo-mua.vue .season-badge sử dụng var(--text-2xs)', () => {
      const content = readFile('pages/theo-mua.vue')
      expect(content).not.toMatch(/\.season-badge\s*\{[^}]*font-size:\s*\.65rem/)
      expect(content).toMatch(/\.season-badge\s*\{[^}]*font-size:\s*var\(--text-2xs/)
    })

    it('bảo đảm layouts/admin.vue không chứa font-size .65rem hoặc .6rem', () => {
      const content = readFile('layouts/admin.vue')
      expect(content).not.toMatch(/\.admin-brand\s+small\s*\{[^}]*font-size:\s*\.65rem/)
      expect(content).not.toMatch(/\.admin-nav-group-label\s*\{[^}]*font-size:\s*\.65rem/)
      expect(content).not.toMatch(/\.nav-badge\s*\{[^}]*font-size:\s*\.65rem/)
      expect(content).not.toMatch(/\.collapsed\s+\.nav-badge\s*\{[^}]*font-size:\s*\.6rem/)
      expect(content).not.toMatch(/\.admin-user-role\s*\{[^}]*font-size:\s*\.68rem/)
    })

    it('bảo đảm settings và personalization sheets tuân thủ token var(--text-2xs)', () => {
      const prefsContent = readFile('components/settings/SettingsPreferencesTab.vue')
      const sheetContent = readFile('components/PersonalizeSetupSheet.vue')
      expect(prefsContent).not.toMatch(/font-size:\s*\.65rem/)
      expect(sheetContent).not.toMatch(/font-size:\s*\.68rem/)
      expect(prefsContent).toContain('var(--text-2xs)')
      expect(sheetContent).toContain('var(--text-2xs)')
    })

    it('bảo đảm các trang quản trị chuyên sâu (ai, bao-cao, data-quality, duyet-anh, index, thong-ke) không dùng font-size vi mô', () => {
      const aiContent = readFile('pages/admin/ai.vue')
      const rptContent = readFile('pages/admin/bao-cao.vue')
      const dqContent = readFile('pages/admin/data-quality.vue')
      const imgContent = readFile('pages/admin/duyet-anh.vue')
      const idxContent = readFile('pages/admin/index.vue')
      const tkContent = readFile('pages/admin/thong-ke.vue')

      expect(aiContent).not.toMatch(/font-size:\s*\.58rem/)
      expect(aiContent).not.toMatch(/font-size:\s*\.68rem/)
      expect(rptContent).not.toMatch(/font-size:\s*\.68rem/)
      expect(dqContent).not.toMatch(/font-size:\s*\.68rem/)
      expect(imgContent).not.toMatch(/font-size:\s*\.68rem/)
      expect(idxContent).not.toMatch(/font-size:\s*\.68rem/)
      expect(idxContent).not.toMatch(/font-size:\s*\.65rem/)
      expect(tkContent).not.toMatch(/font-size:\s*\.62rem/)
    })
  })
})
