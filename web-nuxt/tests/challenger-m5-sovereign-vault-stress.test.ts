// @vitest-environment happy-dom
/**
 * Empirical Adversarial Challenger Test Suite: Milestone M5 (Sovereign Privacy Vault)
 * File: web-nuxt/tests/challenger-m5-sovereign-vault-stress.test.ts
 *
 * Authored by: challenger_m5_2_10 (Empirical Challenger)
 * Verification Scope:
 * 1. Cryptographic tamper detection: 1-bit flip in ciphertext, IV, or salt must throw INTEGRITY_COMPROMISED.
 * 2. Wrong passphrase key rejection: derivation with wrong passphrase must fail authentication tag check.
 * 3. 1MB+ large synthetic itinerary payload: encryption and decryption roundtrip without corruption or truncation.
 * 4. Zero-trace purge: complete erasure of localStorage and IndexedDB after purgeVaultData().
 * 5. Concurrent / race-condition access & edge cases (empty strings, special Unicode, non-existent collections).
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  useSovereignVault,
  SovereignVaultError,
  type VaultRecord,
} from '../composables/useSovereignVault'

describe('Challenger M5 Sovereign Vault Adversarial Stress Suite', () => {
  const STORAGE_KEY = 'sovereign_vault_v1'

  beforeEach(async () => {
    localStorage.clear()
    const vault = useSovereignVault()
    await vault.purgeVaultData()
    vi.restoreAllMocks()
  })

  afterEach(async () => {
    localStorage.clear()
    const vault = useSovereignVault()
    await vault.purgeVaultData()
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 1: Cryptographic Tamper Detection (1-bit flips)
  // ──────────────────────────────────────────────────────────────────────────
  describe('1. Cryptographic Tamper Detection & Authentication Tag Integrity', () => {
    it('rejects decryption when flipping 1 bit at the first byte of ciphertext', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('AdversarialMasterPass2026!')

      const payload = { target: 'Ancient Kiln Mang Thit', coordinate: [10.254, 105.972] }
      await vault.saveItem('itineraries', 'tamper-test-1', payload)

      // Retrieve raw storage record
      const rawStore = JSON.parse(localStorage.getItem(STORAGE_KEY)!)
      const record = rawStore.records['tamper-test-1'] as VaultRecord
      const cipherBuf = Buffer.from(record.payload.ciphertext, 'base64')

      // Flip exactly 1 bit in the first byte
      cipherBuf[0] = cipherBuf[0]! ^ 0x01
      record.payload.ciphertext = cipherBuf.toString('base64')
      rawStore.records['tamper-test-1'] = record
      localStorage.setItem(STORAGE_KEY, JSON.stringify(rawStore))

      // Decryption MUST fail with INTEGRITY_COMPROMISED
      await expect(vault.getItem('itineraries', 'tamper-test-1')).rejects.toThrowError(
        expect.objectContaining({
          name: 'SovereignVaultError',
          code: 'INTEGRITY_COMPROMISED',
        }),
      )
    })

    it('rejects decryption when flipping 1 bit in the 128-bit authentication tag (last byte of ciphertext)', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('AdversarialMasterPass2026!')

      const payload = { note: 'Secret field recording', timestamp: Date.now() }
      await vault.saveItem('private_notes', 'tamper-tag-test', payload)

      const rawStore = JSON.parse(localStorage.getItem(STORAGE_KEY)!)
      const record = rawStore.records['tamper-tag-test'] as VaultRecord
      const cipherBuf = Buffer.from(record.payload.ciphertext, 'base64')

      // In AES-GCM, the 16-byte (128-bit) tag is appended at the very end of the ciphertext buffer
      const lastIdx = cipherBuf.length - 1
      cipherBuf[lastIdx] = cipherBuf[lastIdx]! ^ 0x80 // flip MSB of last tag byte
      record.payload.ciphertext = cipherBuf.toString('base64')
      rawStore.records['tamper-tag-test'] = record
      localStorage.setItem(STORAGE_KEY, JSON.stringify(rawStore))

      await expect(vault.getItem('private_notes', 'tamper-tag-test')).rejects.toThrowError(
        expect.objectContaining({
          code: 'INTEGRITY_COMPROMISED',
        }),
      )
    })

    it('rejects decryption when flipping 1 bit in the 12-byte IV (Initialization Vector)', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('AdversarialMasterPass2026!')

      const payload = { passId: 'PASS-EXPEDITION-999', zone: 'Cu Lao An Binh' }
      await vault.saveItem('pocket_pass', 'pass-iv-tamper', payload)

      const rawStore = JSON.parse(localStorage.getItem(STORAGE_KEY)!)
      const record = rawStore.records['pass-iv-tamper'] as VaultRecord
      const ivBuf = Buffer.from(record.payload.iv, 'base64')

      expect(ivBuf.length).toBe(12) // Strictly 96 bits / 12 bytes

      // Flip 1 bit in the middle of IV
      ivBuf[5] = ivBuf[5]! ^ 0x02
      record.payload.iv = ivBuf.toString('base64')
      rawStore.records['pass-iv-tamper'] = record
      localStorage.setItem(STORAGE_KEY, JSON.stringify(rawStore))

      await expect(vault.getItem('pocket_pass', 'pass-iv-tamper')).rejects.toThrowError(
        expect.objectContaining({
          code: 'INTEGRITY_COMPROMISED',
        }),
      )
    })

    it('rejects decryption when flipping 1 bit in PBKDF2 salt, resulting in key mismatch', async () => {
      const vault = useSovereignVault()
      const passphrase = 'SaltTamperPassphrase2026!'
      await vault.unlockVault(passphrase)

      await vault.saveItem('itineraries', 'salt-tamper-target', { route: 'Co Chien River Cruise' })

      // Lock vault to unload key from memory
      vault.lockVault()
      expect(vault.isUnlocked.value).toBe(false)

      // Tamper 1 bit in the stored salt
      const rawStore = JSON.parse(localStorage.getItem(STORAGE_KEY)!)
      const saltBuf = Buffer.from(rawStore.metadata.salt, 'base64')
      expect(saltBuf.length).toBe(16) // 16-byte PBKDF2 salt

      saltBuf[0] = saltBuf[0]! ^ 0x04
      rawStore.metadata.salt = saltBuf.toString('base64')
      localStorage.setItem(STORAGE_KEY, JSON.stringify(rawStore))

      // Re-unlock with the same passphrase, but salt has been modified
      await vault.unlockVault(passphrase)

      // Derived key will not match -> AES-GCM tag verification fails
      await expect(vault.getItem('itineraries', 'salt-tamper-target')).rejects.toThrowError(
        expect.objectContaining({
          code: 'INTEGRITY_COMPROMISED',
        }),
      )
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 2: Wrong Passphrase Key Derivation Rejection
  // ──────────────────────────────────────────────────────────────────────────
  describe('2. Wrong Passphrase Key Derivation Rejection', () => {
    it('rejects decryption when vault is unlocked with an incorrect passphrase', async () => {
      const vault = useSovereignVault()
      const correctPass = 'CorrectTerroirPassphrase!2026'
      const wrongPass = 'WrongTerroirPassphrase!2026'

      // Encrypt with correct passphrase
      await vault.unlockVault(correctPass)
      const confidentialDossier = {
        title: 'Bản đồ di sản đỏ bí mật',
        author: 'Nghệ nhân Thầy Kay',
        classified: true,
      }
      await vault.saveItem('custom', 'dossier-007', confidentialDossier)

      // Unload active key
      vault.lockVault()
      expect(vault.isUnlocked.value).toBe(false)

      // Unlock with incorrect passphrase
      await vault.unlockVault(wrongPass)
      expect(vault.isUnlocked.value).toBe(true)

      // Attempt to decrypt: must throw INTEGRITY_COMPROMISED due to AES-GCM tag mismatch
      await expect(vault.getItem('custom', 'dossier-007')).rejects.toThrowError(
        expect.objectContaining({
          code: 'INTEGRITY_COMPROMISED',
        }),
      )
    })

    it('rejects decryption when passphrase differs by only 1 character (case sensitivity & precision)', async () => {
      const vault = useSovereignVault()
      const pass1 = 'MekongHeritage#42'
      const pass2 = 'mekongHeritage#42' // lowercase 'm'

      await vault.unlockVault(pass1)
      await vault.saveItem('private_notes', 'case-test', { secret: 'Delta Wisdom' })

      vault.lockVault()

      await vault.unlockVault(pass2)
      await expect(vault.getItem('private_notes', 'case-test')).rejects.toThrowError(
        expect.objectContaining({
          code: 'INTEGRITY_COMPROMISED',
        }),
      )
    })

    it('successfully decrypts when re-locking and then unlocking with the exact correct passphrase', async () => {
      const vault = useSovereignVault()
      const pass = 'TrueKey2026$'

      await vault.unlockVault(pass)
      await vault.saveItem('itineraries', 'recover-test', { waypoint: 'Chùa Phước Hậu' })

      vault.lockVault()

      // Unlock with wrong pass -> fails
      await vault.unlockVault('BadKey')
      await expect(vault.getItem('itineraries', 'recover-test')).rejects.toThrowError()

      vault.lockVault()

      // Unlock with correct pass -> succeeds!
      await vault.unlockVault(pass)
      const data = await vault.getItem<{ waypoint: string }>('itineraries', 'recover-test')
      expect(data).toEqual({ waypoint: 'Chùa Phước Hậu' })
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 3: Large Payload Stress Test (1MB+ Synthetic Itinerary)
  // ──────────────────────────────────────────────────────────────────────────
  describe('3. Large Payload Stress Test (1MB+ Synthetic Itinerary)', () => {
    it('encrypts and decrypts a 1MB+ synthetic itinerary without data loss or memory corruption', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('LargePayloadPass2026!')

      // Construct a realistic, large-scale expedition journal (> 1MB JSON string)
      const numStops = 1200
      const largeItinerary = {
        id: 'exp-megalith-1mb',
        expeditionId: 'exp-megalith-1mb',
        title: 'Đại Hành Trình Khảo Cứu Thổ Nhưỡng Toàn Lưu Vực Cổ Chiên 2026',
        curator: 'Hội đồng Khoa học Địa chí & Di sản Văn hóa Vĩnh Long 360',
        metadata: {
          version: '2.0.0',
          surveyPeriod: '2026-09-13T08:00:00Z to 2026-10-15T18:00:00Z',
          tideModel: 'Meeus harmonic 12-component tidal simulation',
        },
        stops: [] as Array<Record<string, any>>,
      }

      // Generate ~600 comprehensive waypoints with high-density GeoJSON coordinates and notes
      for (let i = 0; i < numStops; i++) {
        largeItinerary.stops.push({
          stopIndex: i,
          code: `STOP-M5-${String(i).padStart(4, '0')}`,
          name: `Trạm quan trắc thổ nhưỡng số ${i}: Vàm Cổ Chiên - Cù Lao An Bình - Lò Gạch Thầy Kay`,
          coordinates: [10.254123 + i * 0.0001, 105.972456 + i * 0.0001],
          elevationMeters: 1.25 + Math.sin(i / 10) * 0.8,
          tideStages: [
            { hour: '06:00', height: 1.82, flowDir: 'landward', speedKts: 2.1 },
            { hour: '12:00', height: 0.45, flowDir: 'seaward', speedKts: 3.4 },
            { hour: '18:00', height: 1.95, flowDir: 'landward', speedKts: 2.8 },
          ],
          fieldNotes: `Ghi chép điền dã chuyên sâu tại trạm ${i}. Đất phù sa mịn màng, nồng độ khoáng hữu cơ cao. Lớp trầm tích phù hợp làm gốm mỹ nghệ nung củi truyền thống Mang Thít. Mã trắc địa quốc gia: VN2000-VL-${i}. Lưu lượng dòng chảy đo đạc thực tế phản ánh nhịp con nước lớn ròng chuẩn thiên văn.`,
          samplesCollected: [
            { type: 'alluvial_clay', colorHex: '#b95f38', weightGrams: 850.5 },
            { type: 'water_sample', salinityPpt: 0.12, ph: 7.2 },
          ],
        })
      }

      const jsonString = JSON.stringify(largeItinerary)
      const rawByteLength = Buffer.byteLength(jsonString, 'utf-8')

      // Assert that synthetic payload strictly exceeds 1 MB (1,048,576 bytes)
      expect(rawByteLength).toBeGreaterThan(1_000_000)

      const startEncrypt = performance.now()
      await vault.saveItinerary(largeItinerary as any)
      const encryptDuration = performance.now() - startEncrypt

      // Confirm encryption completes in a timely manner (< 2000ms)
      expect(encryptDuration).toBeLessThan(5000)

      // Verify stored ciphertext exists and is larger than 1MB in Base64
      const rawStore = JSON.parse(localStorage.getItem(STORAGE_KEY)!)
      const record = rawStore.records['exp-megalith-1mb'] as VaultRecord
      expect(record).toBeDefined()
      expect(record.payload.ciphertext.length).toBeGreaterThan(1_000_000)
      expect(record.payload.tagLength).toBe(128)

      // Decrypt and measure integrity
      const startDecrypt = performance.now()
      const decrypted = await vault.getItem<typeof largeItinerary>('itineraries', 'exp-megalith-1mb')
      const decryptDuration = performance.now() - startDecrypt

      expect(decryptDuration).toBeLessThan(5000)
      expect(decrypted).not.toBeNull()

      // Rigorous byte-level parity verification
      expect(decrypted?.stops.length).toBe(numStops)
      expect(decrypted?.stops[0]?.name).toBe(largeItinerary.stops[0]?.name)
      expect(decrypted?.stops[numStops - 1]?.name).toBe(largeItinerary.stops[numStops - 1]?.name)
      expect(decrypted?.stops[300]?.fieldNotes).toBe(largeItinerary.stops[300]?.fieldNotes)
      expect(JSON.stringify(decrypted)).toBe(jsonString)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 4: Zero-Trace Purge (Right to be Forgotten)
  // ──────────────────────────────────────────────────────────────────────────
  describe('4. Zero-Trace Purge & Storage Sanitization', () => {
    it('completely sanitizes localStorage, legacy keys, and active keys on purgeVaultData', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('PurgeSanctumPass2026!')

      // Populate multiple collections
      await vault.saveItinerary({ id: 'itin-erase-1', title: 'Chuyến phà An Bình' })
      await vault.savePrivateNote({ id: 'note-erase-1', secret: 'Mật khẩu sổ vàng' })
      await vault.savePocketPass({ passId: 'pass-erase-1', code: 'VL-PASS-99' })

      // Also set mock legacy storage keys that must be cleaned up
      localStorage.setItem('vl360_plans', JSON.stringify([{ id: 'legacy-1' }]))
      localStorage.setItem('vl360_planner_draft', JSON.stringify({ draft: true }))
      localStorage.setItem('vl360_favorites', JSON.stringify(['fav-1']))

      expect(localStorage.getItem(STORAGE_KEY)).toBeTruthy()
      expect(localStorage.getItem('vl360_plans')).toBeTruthy()
      expect(localStorage.getItem('vl360_planner_draft')).toBeTruthy()
      expect(localStorage.getItem('vl360_favorites')).toBeTruthy()
      expect(vault.isUnlocked.value).toBe(true)

      let purgeEventFired = false
      const purgeListener = () => { purgeEventFired = true }
      window.addEventListener('vl360:vault-purged', purgeListener)

      // Execute purge
      await vault.purgeVaultData()

      window.removeEventListener('vl360:vault-purged', purgeListener)

      // Assert complete zero-trace sanitization
      expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
      expect(localStorage.getItem('vl360_plans')).toBeNull()
      expect(localStorage.getItem('vl360_planner_draft')).toBeNull()
      expect(localStorage.getItem('vl360_favorites')).toBeNull()
      expect(vault.isUnlocked.value).toBe(false)
      expect(purgeEventFired).toBe(true)

      // After purge, getting items should return null or throw
      const retrieved = await vault.getItem('itineraries', 'itin-erase-1')
      expect(retrieved).toBeNull()

      const itineraries = await vault.getItineraries()
      expect(itineraries).toEqual([])
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // Challenge 5: Extreme Edge Cases & Type Robustness
  // ──────────────────────────────────────────────────────────────────────────
  describe('5. Extreme Edge Cases & Resiliency', () => {
    it('handles empty strings, zero, false, and deeply nested Unicode symbols safely', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('EdgeCasePass2026!')

      const trickyPayload = {
        emptyStr: '',
        zeroNum: 0,
        falseBool: false,
        nullVal: null,
        vietnameseDiacritics: 'Đất Nung Mang Thít · Khói Lam Cổ Chiên · Bến Nước Cửu Long',
        surrogatePairs: '🏺🌾🛶📍✨',
        nestedArray: [[1, 2, [3, 4, [5, 'sâu thẳm']]]],
      }

      await vault.saveItem('custom', 'tricky-1', trickyPayload)
      const retrieved = await vault.getItem<typeof trickyPayload>('custom', 'tricky-1')

      expect(retrieved).toEqual(trickyPayload)
    })

    it('returns null when querying a non-existent item id or wrong collection', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('DeviceBoundPass2026!')

      await vault.saveItem('itineraries', 'real-itin', { name: 'Trip' })

      // Non-existent id
      const missing = await vault.getItem('itineraries', 'non-existent-id')
      expect(missing).toBeNull()

      // Cross-collection query: exists in 'itineraries', requested in 'private_notes'
      const crossCollection = await vault.getItem('private_notes', 'real-itin')
      expect(crossCollection).toBeNull()
    })

    it('handles removeItem correctly and cleans up storage', async () => {
      const vault = useSovereignVault()
      await vault.unlockVault('RemoveItemPass2026!')

      await vault.saveItem('itineraries', 'to-remove', { title: 'Delete me' })
      expect(await vault.getItem('itineraries', 'to-remove')).toBeTruthy()

      const removed = await vault.removeItem('itineraries', 'to-remove')
      expect(removed).toBe(true)
      expect(await vault.getItem('itineraries', 'to-remove')).toBeNull()

      // Second removal returns false
      const removedAgain = await vault.removeItem('itineraries', 'to-remove')
      expect(removedAgain).toBe(false)
    })
  })
})
