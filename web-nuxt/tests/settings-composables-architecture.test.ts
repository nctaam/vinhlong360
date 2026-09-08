import { describe, it, expect, vi } from 'vitest'
import { ref } from 'vue'
import {
  useSettingsSecurity,
  COMMON_PASSWORDS,
  isInternalUA,
  shortUA,
} from '../composables/useSettingsSecurity'
import {
  useSettingsModeration,
  NOTIF_TYPES,
} from '../composables/useSettingsModeration'
import {
  useSettingsAccountLifecycle,
  formatConsentDate,
} from '../composables/useSettingsAccountLifecycle'

describe('Moc 163: Settings Composables Architecture & Security Hygiene', () => {
  describe('useSettingsSecurity', () => {
    it('correctly identifies internal system user agents to hide noisy telemetry sessions', () => {
      expect(isInternalUA('python-requests/2.31.0')).toBe(true)
      expect(isInternalUA('curl/8.1.2')).toBe(true)
      expect(isInternalUA('undici')).toBe(true)
      expect(isInternalUA('uptime-kuma/1.23.0')).toBe(true)
      expect(isInternalUA('healthcheck-runner')).toBe(true)
      expect(isInternalUA('Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X)')).toBe(false)
      expect(isInternalUA('Mozilla/5.0 (Windows NT 10.0; Win64; x64)')).toBe(false)
    })

    it('formats user agent strings into clear human-readable device labels', () => {
      expect(shortUA('')).toBe('Không rõ')
      expect(shortUA('curl/7.68.0')).toBe('Phiên hệ thống')
      expect(shortUA('Mozilla/5.0 (iPhone; CPU iPhone OS...) Mobile/15E148')).toBe('Di động')
      expect(shortUA('Mozilla/5.0 (Windows NT 10.0; Win64; x64)')).toBe('Windows')
      expect(shortUA('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)')).toBe('macOS')
      expect(shortUA('Mozilla/5.0 (X11; Linux x86_64)')).toBe('Linux')
      expect(shortUA('CustomClientAppVersion123456789012345678901234567890Extra')).toHaveLength(30)
    })

    it('evaluates password strength according to length, complexity, and common leaked sets', () => {
      const { newPw, pwStrength } = useSettingsSecurity()

      expect(pwStrength.value.score).toBe(0)
      expect(pwStrength.value.label).toBe('')

      // Common leaked password
      newPw.value = '123456'
      expect(pwStrength.value.score).toBe(1)
      expect(pwStrength.value.label).toBe('Rất yếu')

      // Short simple password
      newPw.value = 'abcdef'
      expect(pwStrength.value.score).toBe(1)
      expect(pwStrength.value.label).toBe('Yếu')

      // Moderate password
      newPw.value = 'VinhLong360'
      expect(pwStrength.value.score).toBeGreaterThanOrEqual(2)

      // Complex strong password
      newPw.value = 'Mekong#Delta*2026!VinhLong'
      expect(pwStrength.value.score).toBe(4)
      expect(pwStrength.value.label).toBe('Rất mạnh')
    })

    it('prevents concurrent execution using withBusy async guard', async () => {
      const { securityBusy, withBusy } = useSettingsSecurity()
      let callCount = 0

      expect(securityBusy.value).toBe(false)

      const slowOp = () => withBusy(async () => {
        callCount++
        await new Promise(resolve => setTimeout(resolve, 50))
      })

      const p1 = slowOp()
      expect(securityBusy.value).toBe(true)
      const p2 = slowOp() // should be dropped by guard

      await Promise.all([p1, p2])
      expect(callCount).toBe(1)
      expect(securityBusy.value).toBe(false)
    })

    it('validates password requirement flags against authenticated user object', () => {
      const userWithPw = ref({ id: 'u1', has_password: true })
      const security1 = useSettingsSecurity({ user: userWithPw })
      expect(security1.hasPassword.value).toBe(true)
      expect(security1.hasPasswordKnown.value).toBe(true)

      const userOauthOnly = ref({ id: 'u2', has_password: false })
      const security2 = useSettingsSecurity({ user: userOauthOnly })
      expect(security2.hasPassword.value).toBe(false)
      expect(security2.hasPasswordKnown.value).toBe(true)
    })
  })

  describe('useSettingsModeration', () => {
    it('defines 5 canonical notification categories with distinct preference keys', () => {
      expect(NOTIF_TYPES).toHaveLength(5)
      const keys = NOTIF_TYPES.map(t => t.key)
      expect(keys).toEqual(['like', 'comment', 'follow', 'mention', 'system'])
      const prefs = NOTIF_TYPES.map(t => t.pref)
      expect(new Set(prefs).size).toBe(5)
    })

    it('initializes default privacy and notification settings optimistically', () => {
      const { privacy, notifPrefs } = useSettingsModeration()
      expect(privacy.value).toEqual({
        profile_visibility: 'public',
        show_activity: true,
        show_saved: true,
      })
      expect(notifPrefs.value.pref_like).toBe(true)
      expect(notifPrefs.value.pref_system).toBe(true)
    })
  })

  describe('useSettingsAccountLifecycle', () => {
    it('formats consent timestamps reliably with fallback for invalid dates', () => {
      expect(formatConsentDate('invalid-date')).toBe('Không rõ thời điểm')
      const formatted = formatConsentDate('2026-03-29T10:00:00Z')
      expect(formatted).toContain('2026')
      expect(formatted).toContain('tháng')
    })

    it('initializes lifecycle status flags safely', () => {
      const { exportLoading, deleteConfirmVisible, deleteBusy, accountStatus } = useSettingsAccountLifecycle()
      expect(exportLoading.value).toBe(false)
      expect(deleteConfirmVisible.value).toBe(false)
      expect(deleteBusy.value).toBe(false)
      expect(accountStatus.value).toBe('')
    })
  })
})
