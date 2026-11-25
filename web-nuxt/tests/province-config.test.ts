// @vitest-environment node

import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

import dongThapExample from '../../config/province.dongthap.example.json'
import {
  PROVINCE_AREA_META,
  PROVINCE_CONFIG,
  PROVINCE_CURRENT_ALIASES,
  buildProvinceAreaMeta,
  validateProvinceConfig,
} from '../utils/provinceConfig'
import { PROVINCE_TEST_FILES } from './testSuites.mjs'

describe('province configuration layer & test boundary', () => {
  it('loads canonical Vĩnh Long configuration cleanly', () => {
    expect(PROVINCE_CONFIG.schemaVersion).toBe(1)
    expect(PROVINCE_CONFIG.identity.slug).toBe('vinhlong360')
    expect(PROVINCE_CONFIG.identity.domain).toBe('vinhlong360.vn')
    expect(PROVINCE_CONFIG.identity.siteUrl).toBe('https://vinhlong360.vn')
    expect(PROVINCE_CONFIG.areas.items).toHaveLength(3)
    expect(PROVINCE_CURRENT_ALIASES.has('vinh-long')).toBe(true)
    expect(PROVINCE_CURRENT_ALIASES.has('ben-tre')).toBe(true)
    expect(PROVINCE_AREA_META['lien-vung']?.name).toBe('Liên vùng')
  })

  it('validates the 2-region Đồng Tháp clone template cleanly', () => {
    const validated = validateProvinceConfig(dongThapExample)
    expect(validated.identity.slug).toBe('dongthap360')
    expect(validated.identity.siteUrl).toBe('https://dongthap360.vn')
    expect(validated.areas.items).toHaveLength(2)
    expect(validated.areas.items.map(a => a.slug)).toEqual(['dong-thap', 'tien-giang'])

    const areaMeta = buildProvinceAreaMeta(validated)
    expect(Object.keys(areaMeta)).toEqual(['dong-thap', 'tien-giang', 'lien-vung'])
    expect(validated.contentGuards.outOfProvincePatterns).not.toContain('Cái Bè')
    expect(validated.contentGuards.outOfProvincePatterns).toContain('Mang Thít')
  })

  it('rejects malformed or non-HTTPS province configurations', () => {
    expect(() => validateProvinceConfig(null)).toThrow(/schemaVersion=1/)
    const badUrl = structuredClone(dongThapExample)
    badUrl.identity.siteUrl = 'http://dongthap360.vn'
    expect(() => validateProvinceConfig(badUrl)).toThrow(/https:\/\//)
  })

  it('keeps PROVINCE_TEST_FILES unique and backed by existing files', () => {
    const unique = new Set(PROVINCE_TEST_FILES)
    expect(unique.size).toBe(PROVINCE_TEST_FILES.length)
    for (const file of PROVINCE_TEST_FILES) {
      expect(existsSync(resolve(__dirname, file)), `missing ${file}`).toBe(true)
    }
  })
})
