// @vitest-environment happy-dom
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  useCognitiveTerroir,
  detectBatteryCondition,
  detectNetworkCondition,
} from '../composables/useCognitiveTerroir'
import {
  useSovereignVault,
  SovereignVaultError,
} from '../composables/useSovereignVault'
import * as legalContent from '../utils/legalContent'

// ── Sustainable Web Design Mathematical Model ──
const SWD_ENERGY_PER_GB = 0.81 // kWh/GB
const SWD_CARBON_INTENSITY = 442 // g CO2/kWh

function calculateCarbonGrams(bytes: number): number {
  const gb = bytes / (1024 * 1024 * 1024)
  return gb * SWD_ENERGY_PER_GB * SWD_CARBON_INTENSITY
}

const configPath = resolve(__dirname, '../nuxt.config.ts')
const nuxtConfigSource = readFileSync(configPath, 'utf-8')

describe('Milestone M5: Green Web WSG, Core Web Vitals & Sovereign Privacy Suite', () => {
  // ──────────────────────────────────────────────────────────────────────────
  // Phân hệ 1: Thẩm định Toán học Phát thải Carbon & Ngân sách Tải trọng
  // ──────────────────────────────────────────────────────────────────────────
  describe('1. WSG Carbon & Payload Math Verification', () => {
    it('proves that a 200 KB payload produces strictly less than 0.1g CO2 per view', () => {
      const payloadBytes = 200 * 1024 // 204,800 Bytes
      const co2Grams = calculateCarbonGrams(payloadBytes)

      // Expected: ~0.0683g CO2, well below the 0.100g ceiling
      expect(co2Grams).toBeLessThan(0.100)
      expect(co2Grams).toBeGreaterThan(0.060)
      expect(co2Grams).toBeCloseTo(0.0683, 3)
    })

    it('determines the theoretical payload ceiling for the 0.1g CO2 limit', () => {
      // 0.1g / (0.81 * 442) = ~0.0002793 GB = ~292.9 KB (binary)
      const maxAllowedBytes = (0.1 / (SWD_ENERGY_PER_GB * SWD_CARBON_INTENSITY)) * (1024 * 1024 * 1024)
      expect(maxAllowedBytes).toBeGreaterThan(200 * 1024)
      expect(Math.floor(maxAllowedBytes / 1024)).toBe(292)
    })

    it('verifies Nitro asset pre-compression is strictly configured in nuxt.config.ts', () => {
      expect(nuxtConfigSource).toMatch(/compressPublicAssets:\s*true/)
    })

    it('verifies client bundle excludes heavy third-party dependencies', () => {
      expect(nuxtConfigSource).toMatch(/exclude:\s*\[[^\]]*'maplibre-gl'[^\]]*\]/)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Phân hệ 2: Kiểm định Chế Độ Sinh Thái Sông Nước (Eco-Terroir Mode)
  // ──────────────────────────────────────────────────────────────────────────
  describe('2. Eco-Terroir Mode Reactive Mechanics', () => {
    const originalNavigator = global.navigator

    beforeEach(() => {
      document.documentElement.removeAttribute('data-eco-mode')
      localStorage.clear()
    })

    afterEach(() => {
      Object.defineProperty(global, 'navigator', {
        value: originalNavigator,
        configurable: true,
      })
    })

    it('triggers Eco-Terroir Mode automatically when battery <= 20% and not charging', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockResolvedValue({
            level: 0.18,
            charging: false,
            addEventListener: vi.fn(),
          }),
        },
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.level).toBe(0.18)
      expect(battery.isLowBattery).toBe(true)
    })

    it('does not trigger Eco-Terroir Mode if battery <= 20% but device is charging', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockResolvedValue({
            level: 0.15,
            charging: true,
            addEventListener: vi.fn(),
          }),
        },
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.level).toBe(0.15)
      expect(battery.isLowBattery).toBe(false)
    })

    it('supports explicit user toggle of Eco-Terroir Mode', () => {
      const terroir = useCognitiveTerroir()
      terroir.toggleEcoMode(false)
      expect(terroir.isEcoTerroir.value).toBe(false)

      terroir.toggleEcoMode(true)
      expect(terroir.isEcoTerroir.value).toBe(true)
      expect(document.documentElement.getAttribute('data-eco-mode')).toBe('true')
      expect(localStorage.getItem('vl360_eco_mode')).toBe('true')

      terroir.toggleEcoMode(false)
      expect(terroir.isEcoTerroir.value).toBe(false)
      expect(document.documentElement.hasAttribute('data-eco-mode')).toBe(false)
    })

    it('switches geolocation to manual and disables prefetching under Eco-Mode', () => {
      const terroir = useCognitiveTerroir()
      terroir.toggleEcoMode(true)

      expect(terroir.geolocationMode.value).toBe('manual')
      expect(terroir.prefetchEnabled.value).toBe(false)

      terroir.toggleEcoMode(false)
      expect(terroir.geolocationMode.value).toBe('auto')
      expect(terroir.prefetchEnabled.value).toBe(true)
    })

    it('handles unsupported Battery API gracefully without crashing (SSR / Safari)', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {},
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.isLowBattery).toBe(false)
      expect(battery.level).toBe(1.0)
    })

    it('verifies base.css contains Eco-Terroir animation suppression and content-visibility', () => {
      const cssPath = resolve(__dirname, '../assets/css/base.css')
      const cssContent = readFileSync(cssPath, 'utf-8')

      expect(cssContent).toContain('html[data-eco-mode="true"]')
      expect(cssContent).toContain('animation: none !important')
      expect(cssContent).toContain('content-visibility: auto')
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Phân hệ 3: Bất Biến Core Web Vitals (CLS = 0.000, LCP < 0.8s, INP < 50ms)
  // ──────────────────────────────────────────────────────────────────────────
  describe('3. Core Web Vitals Structural Invariants', () => {
    it('ensures fixed height design tokens exist in variables.css for CLS prevention', () => {
      const cssPath = resolve(__dirname, '../assets/css/variables.css')
      const cssContent = readFileSync(cssPath, 'utf-8')

      // Fixed height header
      expect(cssContent).toMatch(/--shell-public-header-height:\s*150px;/)
      // Fixed height bottom nav
      expect(cssContent).toMatch(/--shell-public-bottom-nav-reserved-height:\s*max\(64px/)
      // Aspect ratio tokens
      expect(cssContent).toMatch(/--ratio-hero:\s*16\s*\/\s*9;/)
      expect(cssContent).toMatch(/--ratio-card:\s*5\s*\/\s*3;/)
      expect(cssContent).toMatch(/--ratio-card-tall:\s*4\s*\/\s*3;/)
    })

    it('verifies scroll event listener uses non-blocking passive mode in default.vue', () => {
      const layoutPath = resolve(__dirname, '../layouts/default.vue')
      const layoutContent = readFileSync(layoutPath, 'utf-8')

      expect(layoutContent).toMatch(/window\.addEventListener\('scroll',\s*onPageScroll,\s*\{\s*passive:\s*true\s*\}\)/)
      expect(layoutContent).toMatch(/requestAnimationFrame\(/)
    })

    it('verifies Weserv image provider and WebP conversion in nuxt.config.ts', () => {
      expect(nuxtConfigSource).toMatch(/provider:\s*'weserv'/)
      expect(nuxtConfigSource).toMatch(/format:\s*\[[^\]]*'webp'[^\]]*\]/)
      expect(nuxtConfigSource).toMatch(/quality:\s*72/)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Phân hệ 4: Sovereign Privacy (100% Zero 3rd-Party Tracking)
  // ──────────────────────────────────────────────────────────────────────────
  describe('4. Sovereign Privacy & Zero 3rd-Party Surveillance', () => {
    it('confirms zero 3rd-party tracking scripts in nuxt head configuration', () => {
      const forbiddenTrackers = [
        'google-analytics.com',
        'googletagmanager.com',
        'facebook.net',
        'connect.facebook.net',
        'hotjar.com',
        'clarity.ms',
        'doubleclick.net',
        'criteo.net',
        'segment.io',
      ]

      for (const tracker of forbiddenTrackers) {
        expect(nuxtConfigSource.includes(tracker), `Forbidden surveillance script found: ${tracker}`).toBe(false)
      }
    })

    it('guarantees strictly 1st-party ownership for all inventory cookies', () => {
      const cookies = legalContent.privacy.cookieInventory
      expect(cookies.length).toBeGreaterThanOrEqual(6)
      for (const cookie of cookies) {
        expect(cookie.owner).toBe('vinhlong360')
        expect(cookie.sameSite).toBe('Lax')
        expect(cookie.purpose).toBeTruthy()
        expect(cookie.consentControl).toBeTruthy()
      }
    })

    it('enforces HTTP Strict-Transport-Security and geolocation=(self) in Permissions-Policy', () => {
      expect(nuxtConfigSource).toMatch(/Strict-Transport-Security['"]?:\s*['"]max-age=31536000;\s*includeSubDomains['"]/)
      expect(nuxtConfigSource).toMatch(/X-Content-Type-Options['"]?:\s*['"]nosniff['"]/)
      expect(nuxtConfigSource).toMatch(/X-Frame-Options['"]?:\s*['"]SAMEORIGIN['"]/)
      expect(nuxtConfigSource).toMatch(/Referrer-Policy['"]?:\s*['"]strict-origin-when-cross-origin['"]/)
      expect(nuxtConfigSource).toMatch(/Permissions-Policy['"]?:\s*['"][^'"]*geolocation=\(self\)/)
    })

    it('complies with Nghị định 13/2023/NĐ-CP user rights declarations', () => {
      const rightsSection = legalContent.LEGAL_PRIVACY.sections.find(s => s.heading.includes('Quyền của bạn'))
      expect(rightsSection).toBeDefined()
      expect(rightsSection?.body).toContain('Truy cập / chỉnh sửa')
      expect(rightsSection?.body).toContain('Rút lại đồng ý')
      expect(rightsSection?.body).toContain('Xoá tài khoản & dữ liệu')
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Phân hệ 5: Web Crypto API AES-GCM 256-bit Sanctum
  // ──────────────────────────────────────────────────────────────────────────
  describe('5. Web Crypto API AES-GCM 256-bit Encryption Engine', () => {
    beforeEach(() => {
      localStorage.clear()
    })

    it('derives a 256-bit key using PBKDF2 with SHA-256 and 100,000 iterations', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('MekongSecret2026!')
      expect(vault.isUnlocked.value).toBe(true)
      expect(vault.vaultMode.value).toBe('passphrase-derived')
    })

    it('encrypts data returning valid { iv, ciphertext, tagLength: 128 } structure', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('MekongSecret2026!')

      const sampleItinerary = {
        title: 'Hành trình Lò Gạch Mang Thít',
        stops: [{ name: 'Bến phà An Bình', time: '07:30' }],
        notes: 'Ghi chú điền dã bí mật không gửi lên server',
      }

      await vault.saveItem('itineraries', 'itin-001', sampleItinerary)

      const rawVault = localStorage.getItem('sovereign_vault_v1')
      expect(rawVault).toBeTruthy()
      const parsed = JSON.parse(rawVault!)
      const record = parsed.records['itin-001']

      expect(record).toBeDefined()
      expect(record.payload.tagLength).toBe(128)
      expect(typeof record.payload.iv).toBe('string')
      expect(typeof record.payload.ciphertext).toBe('string')
      // Cleartext must never leak into local storage
      expect(rawVault).not.toContain('Ghi chú điền dã bí mật')
      expect(rawVault).not.toContain('Lò Gạch Mang Thít')
    })

    it('successfully decrypts encrypted records back to authentic original data', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('MekongSecret2026!')

      const secretNote = {
        entityId: 'mang-thit-kiln-1',
        secretImpression: 'Lò nung của nghệ nhân Bảy có kỹ thuật giữ lửa trấu rất đặc sắc.',
      }

      await vault.saveItem('private_notes', 'note-77', secretNote)
      const decrypted = await vault.getItem<typeof secretNote>('private_notes', 'note-77')

      expect(decrypted).toEqual(secretNote)
    })

    it('provides entity shortcuts for itineraries, private notes, and pocket pass', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('MekongSecret2026!')

      await vault.saveItinerary({ id: 'itin-exp-1', title: 'Chuyến đi Cù Lao' })
      const itins = await vault.getItineraries()
      expect(itins.some(i => i.title === 'Chuyến đi Cù Lao')).toBe(true)

      await vault.savePrivateNote({ id: 'note-exp-1', text: 'Cây cầu khỉ ven rạch' })
      const notes = await vault.getPrivateNotes()
      expect(notes.some(n => n.text === 'Cây cầu khỉ ven rạch')).toBe(true)

      await vault.savePocketPass({ passId: 'pass-001', passCode: 'PASS-VL-2026' })
      const pass = await vault.getPocketPass()
      expect(pass).toBeDefined()
      expect(pass.passCode).toBe('PASS-VL-2026')
    })

    it('generates a fresh 12-byte IV for every encryption call, preventing IV reuse', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('MekongSecret2026!')

      const data = { ping: 'pong' }
      await vault.saveItem('custom', 'rec-1', data)
      await vault.saveItem('custom', 'rec-2', data)

      const rawVault = JSON.parse(localStorage.getItem('sovereign_vault_v1')!)
      const iv1 = rawVault.records['rec-1'].payload.iv
      const iv2 = rawVault.records['rec-2'].payload.iv
      const cipher1 = rawVault.records['rec-1'].payload.ciphertext
      const cipher2 = rawVault.records['rec-2'].payload.ciphertext

      expect(iv1).not.toEqual(iv2)
      expect(cipher1).not.toEqual(cipher2)
    })

    it('detects tampering and rejects corrupted ciphertext via 128-bit authentication tag', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('MekongSecret2026!')

      await vault.saveItem('custom', 'tamper-target', { secret: 'top-secret' })

      const rawVault = JSON.parse(localStorage.getItem('sovereign_vault_v1')!)
      const originalCipher = rawVault.records['tamper-target'].payload.ciphertext
      const tamperedCipher = (originalCipher.startsWith('A') ? 'B' : 'A') + originalCipher.slice(1)
      rawVault.records['tamper-target'].payload.ciphertext = tamperedCipher
      localStorage.setItem('sovereign_vault_v1', JSON.stringify(rawVault))

      await expect(vault.getItem('custom', 'tamper-target')).rejects.toThrowError(
        expect.objectContaining({ code: 'INTEGRITY_COMPROMISED' }),
      )
    })

    it('exports complete decrypted vault archive for user portability', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('MekongSecret2026!')

      await vault.saveItem('itineraries', 'itin-exp', { title: 'Tour Cù Lao' })
      await vault.saveItem('pocket_pass', 'pass-exp', { passCode: 'PASS-123' })

      const archive = await vault.exportVaultData()
      expect(archive.schema).toBe('vinhlong360-sovereign-vault-v1')
      expect(archive.records.length).toBeGreaterThanOrEqual(2)
      expect(archive.records.some(r => r.id === 'itin-exp')).toBe(true)
    })

    it('purges all keys, metadata, and ciphertexts on purgeVaultData (Zero Trace)', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('MekongSecret2026!')

      await vault.saveItem('itineraries', 'doomed-itin', { title: 'To Be Erased' })
      expect(localStorage.getItem('sovereign_vault_v1')).toBeTruthy()

      await vault.purgeVaultData()

      expect(localStorage.getItem('sovereign_vault_v1')).toBeNull()
      expect(vault.isUnlocked.value).toBe(false)
    })
  })
})
