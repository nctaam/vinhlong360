import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

const BASE_DIR = path.resolve(__dirname, '..')

function getFiles(dir: string, match: (file: string) => boolean): string[] {
  let results: string[] = []
  const list = fs.readdirSync(dir)
  list.forEach(file => {
    const full = path.join(dir, file)
    const stat = fs.statSync(full)
    if (stat && stat.isDirectory()) {
      results = results.concat(getFiles(full, match))
    } else if (match(file)) {
      results.push(full)
    }
  })
  return results
}

function readFile(relPath: string): string {
  return fs.readFileSync(path.join(BASE_DIR, relPath), 'utf-8')
}

describe('Mốc 109: Form Error Association & Programmatic Feedback Standards (WCAG 2.2 SC 3.3.1 & SC 1.3.1)', () => {
  describe('Explicit Form Error Links', () => {
    it('bảo đảm displayName trong pages/cai-dat.vue liên kết với cd-err-name', () => {
      const content = readFile('pages/cai-dat.vue')
      expect(content).toMatch(/:aria-describedby="nameError \? 'cd-err-name' : undefined"/)
      expect(content).toMatch(/id="cd-err-name"[^>]*role="alert"/)
    })

    it('bảo đảm search input trong pages/tim-kiem.vue liên kết với search-error-state', () => {
      const content = readFile('pages/tim-kiem.vue')
      expect(content).toMatch(/:aria-describedby="hasError && !totalSearchResults \? 'search-error-state' : undefined"/)
      expect(content).toMatch(/id="search-error-state"/)
    })

    it('bảo đảm các bước xác thực trong components/AuthModal.vue đều liên kết với thông báo lỗi tương ứng', () => {
      const content = readFile('components/AuthModal.vue')
      expect(content).toMatch(/:aria-describedby="error && step === 'phone' \? 'auth-err-phone' : undefined"/)
      expect(content).toMatch(/id="auth-err-phone"[^>]*class="form-error"/)

      expect(content).toMatch(/:aria-describedby="error && step === 'password' \? 'auth-err-password' : undefined"/)
      expect(content).toMatch(/id="auth-err-password"[^>]*class="form-error"/)

      expect(content).toMatch(/:aria-describedby="error && step === 'set-password' \? 'auth-err-setpw' : undefined"/)
      expect(content).toMatch(/id="auth-err-setpw"[^>]*class="form-error"/)

      expect(content).toMatch(/:aria-describedby="error && step === 'twofactor' \? 'auth-err-2fa' : undefined"/)
      expect(content).toMatch(/id="auth-err-2fa"[^>]*class="form-error"/)
    })
  })

  describe('Zero Unassociated Invalid Inputs Across All Pages & Components', () => {
    const allFiles = [
      ...getFiles(path.join(BASE_DIR, 'pages'), f => f.endsWith('.vue')),
      ...getFiles(path.join(BASE_DIR, 'components'), f => f.endsWith('.vue'))
    ]

    it('bảo đảm mọi input có aria-invalid đều có aria-describedby', () => {
      const unassociated: string[] = []

      allFiles.forEach(file => {
        const code = fs.readFileSync(file, 'utf-8')
        const rel = path.relative(BASE_DIR, file).replace(/\\/g, '/')
        const inputRegex = /<(?:input|textarea|select)\b([^>]*)>/gi
        let match: RegExpExecArray | null
        while ((match = inputRegex.exec(code)) !== null) {
          const attrs = match[1] ?? ''
          if (/aria-invalid/i.test(attrs) && !/aria-describedby/i.test(attrs)) {
            unassociated.push(`${rel}: ${attrs.slice(0, 60)}`)
          }
        }
      })

      expect(unassociated).toEqual([])
    })
  })
})
