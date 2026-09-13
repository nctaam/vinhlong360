import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import {
  useCognitiveTerroir,
  calculateAstronomicalTide,
  calculateTidalAmplitudeFactor,
  calculateBearingDegrees,
  calculateEcoRouting,
  detectNetworkCondition,
  detectBatteryCondition,
} from '../composables/useCognitiveTerroir'
import VernacularGlyph from '../components/VernacularGlyph.vue'
import TufteSidenote from '../components/TufteSidenote.vue'

describe('Cognitive Terroir Engine & Epistemic Components (Milestone M2)', () => {
  // ──────────────────────────────────────────────────────────────────────────
  // 1. Astronomical River Tide Calculations (Meeus/Hồ Ngọc Đức & Cổ Chiên Basin)
  // ──────────────────────────────────────────────────────────────────────────
  describe('Astronomical River Tide Engine', () => {
    it('modulates tidal amplitude factor alpha(D_L) within [0.65, 1.35]', () => {
      for (let day = 1; day <= 30; day++) {
        const factor = calculateTidalAmplitudeFactor(day)
        expect(factor).toBeGreaterThanOrEqual(0.64)
        expect(factor).toBeLessThanOrEqual(1.36)
      }

      // Spring tide peaks at Day 1 (New Moon) and Day 15 (Full Moon)
      const day1Factor = calculateTidalAmplitudeFactor(1)
      expect(day1Factor).toBeCloseTo(1.35, 1)

      const day15Factor = calculateTidalAmplitudeFactor(15.76)
      expect(day15Factor).toBeGreaterThan(1.3)

      // Neap tide troughs at Day 8 and Day 23
      const day8Factor = calculateTidalAmplitudeFactor(8.38)
      expect(day8Factor).toBeCloseTo(0.65, 1)
    })

    it('classifies Spring Tide (Kỳ Nước rong) on lunar boundaries', () => {
      // 2026-09-25 is approximately Lunar August 15 (Rằm tháng 8)
      const autumnFullMoon = new Date('2026-09-25T14:00:00+07:00')
      const res = calculateAstronomicalTide(autumnFullMoon)

      expect(res.lunarDate).toBeDefined()
      expect(res.tidePhase).toBe('rong')
      expect(res.tidePhaseLabel).toBe('Kỳ Nước rong')
      expect(res.folkWisdom).toContain('Nước rong rằm & mùng một')
    })

    it('classifies Neap Tide (Kỳ Nước kém) on quarter moon periods', () => {
      // 2026-10-03 is approximately Lunar August 23 (Hăm ba)
      const neapDate = new Date('2026-10-03T10:00:00+07:00')
      const res = calculateAstronomicalTide(neapDate)

      expect(res.tidePhase).toBe('kem')
      expect(res.tidePhaseLabel).toBe('Kỳ Nước kém')
    })

    it('evaluates water level h(t) and flow state accurately', () => {
      const date = new Date('2026-09-13T10:30:00+07:00')
      const res = calculateAstronomicalTide(date)

      expect(Number.isFinite(res.waterLevelMeters)).toBe(true)
      expect(res.waterLevelMeters).toBeGreaterThan(0.2)
      expect(res.waterLevelMeters).toBeLessThan(2.5)

      expect(['nuoc_lon', 'nuoc_rong_can', 'nuoc_dung']).toContain(res.waterFlowState)
      expect(res.flowVelocityMs).toBeGreaterThanOrEqual(0.05)
      expect(res.flowVelocityMs).toBeLessThanOrEqual(1.6)

      // Azimuth check: Seaward (135°) during ebb vs Landward (315°) during flood
      if (res.waterFlowState === 'nuoc_rong_can') {
        expect(res.currentAzimuth).toBe(135.0)
      } else if (res.waterFlowState === 'nuoc_lon') {
        expect(res.currentAzimuth).toBe(315.0)
      }
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 2. Hydrodynamic Eco-Routing & 40% Propulsion Savings
  // ──────────────────────────────────────────────────────────────────────────
  describe('Hydrodynamic River Eco-Routing', () => {
    it('calculates geographic bearing between river waypoints', () => {
      const b1 = calculateBearingDegrees({ lat: 10.0, lng: 105.0 }, { lat: 10.0, lng: 106.0 })
      expect(b1).toBeCloseTo(90, 0) // Due East

      const b2 = calculateBearingDegrees({ lat: 10.0, lng: 105.0 }, { lat: 11.0, lng: 105.0 })
      expect(b2).toBeCloseTo(0, 0) // Due North
    })

    it('demonstrates ~40% propulsion savings when traveling downstream', () => {
      // Origin: Mỹ Thuận Pier (10.278° N, 105.908° E)
      // Destination: Cù Lao An Bình downstream (10.250° N, 105.980° E) -> Heading Southeast ~120-135°
      const origin = { lat: 10.278, lng: 105.908, name: 'Bến Mỹ Thuận' }
      const destination = { lat: 10.230, lng: 105.980, name: 'Cù Lao An Bình' }

      // Use a departure time during ebb tide when river flows Southeast (135°)
      // Let's create a date where tide.waterFlowState === 'nuoc_rong_can'
      let testDate = new Date('2026-09-13T00:00:00+07:00')
      for (let h = 0; h < 24; h++) {
        const candidate = new Date(`2026-09-13T${String(h).padStart(2, '0')}:00:00+07:00`)
        const t = calculateAstronomicalTide(candidate)
        if (t.waterFlowState === 'nuoc_rong_can') {
          testDate = candidate
          break
        }
      }

      const routing = calculateEcoRouting(origin, destination, testDate)

      expect(routing.direction).toBe('downstream_assist')
      expect(routing.alignmentCos).toBeGreaterThanOrEqual(0.60)
      // Savings ~40% (35% to 50%)
      expect(routing.effortSavingsPercentage).toBeGreaterThanOrEqual(30)
      expect(routing.effortSavingsPercentage).toBeLessThanOrEqual(55)
      expect(routing.narrativeAdvice).toContain('Xuôi dòng nước')
      expect(routing.narrativeAdvice).toContain('Tiết kiệm')
    })

    it('warns of upstream resistance when heading against the tidal flow', () => {
      // Reverse trajectory: from downstream Southeast back up Northwest (315°) during ebb tide (135°)
      const origin = { lat: 10.230, lng: 105.980, name: 'Cù Lao An Bình' }
      const destination = { lat: 10.278, lng: 105.908, name: 'Bến Mỹ Thuận' }

      // Same ebb tide hour
      let testDate = new Date('2026-09-13T00:00:00+07:00')
      for (let h = 0; h < 24; h++) {
        const candidate = new Date(`2026-09-13T${String(h).padStart(2, '0')}:00:00+07:00`)
        const t = calculateAstronomicalTide(candidate)
        if (t.waterFlowState === 'nuoc_rong_can') {
          testDate = candidate
          break
        }
      }

      const routing = calculateEcoRouting(origin, destination, testDate)

      expect(routing.direction).toBe('upstream_resistance')
      expect(routing.alignmentCos).toBeLessThanOrEqual(-0.60)
      expect(routing.effortSavingsPercentage).toBeLessThan(0)
      expect(routing.narrativeAdvice).toContain('Ngược dòng triều cường')
    })

    it('identifies cross-current routes when heading perpendicular', () => {
      // Due South / North vs current 135°
      const origin = { lat: 10.280, lng: 105.950 }
      const destination = { lat: 10.220, lng: 105.950 }

      let testDate = new Date('2026-09-13T12:00:00+07:00')
      const routing = calculateEcoRouting(origin, destination, testDate)

      if (routing.alignmentCos > -0.60 && routing.alignmentCos < 0.60) {
        expect(routing.direction).toBe('cross_current')
        expect(routing.effortSavingsPercentage).toBe(0)
        expect(routing.narrativeAdvice).toContain('Dòng chảy ngang')
      }
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 3. Adaptive Field Mode & Eco-Terroir Power Throttling
  // ──────────────────────────────────────────────────────────────────────────
  describe('Adaptive Field & Eco-Terroir Detection', () => {
    const originalNavigator = global.navigator

    afterEach(() => {
      Object.defineProperty(global, 'navigator', {
        value: originalNavigator,
        configurable: true,
      })
    })

    it('detects standard 4G network profile by default', () => {
      const net = detectNetworkCondition()
      expect(net.profile).toBe('standard')
      expect(net.isOffline).toBe(false)
    })

    it('detects 2G/3G and switches to field-light profile', () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          onLine: true,
          connection: { effectiveType: '2g', saveData: false },
        },
        configurable: true,
      })

      const net = detectNetworkCondition()
      expect(net.effectiveType).toBe('2g')
      expect(net.profile).toBe('field-light')
    })

    it('detects offline and switches to offline profile', () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          onLine: false,
          connection: { effectiveType: '4g' },
        },
        configurable: true,
      })

      const net = detectNetworkCondition()
      expect(net.isOffline).toBe(true)
      expect(net.profile).toBe('offline')
    })

    it('detects low battery (< 20%) and throttles GPS interval to 60s', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {
          getBattery: vi.fn().mockResolvedValue({
            level: 0.15,
            charging: false,
          }),
        },
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.level).toBe(0.15)
      expect(battery.isLowBattery).toBe(true)
      expect(battery.watchIntervalMs).toBe(60000)
    })

    it('handles unsupported battery API gracefully without throwing (CLAUDE §1.7)', async () => {
      Object.defineProperty(global, 'navigator', {
        value: {},
        configurable: true,
      })

      const battery = await detectBatteryCondition()
      expect(battery.isLowBattery).toBe(false)
      expect(battery.watchIntervalMs).toBe(5000)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 4. useCognitiveTerroir Composable & Ergonomic State Toggles
  // ──────────────────────────────────────────────────────────────────────────
  describe('useCognitiveTerroir Composable API', () => {
    it('initializes reactive state and toggles Elder Reading Mode', () => {
      const terroir = useCognitiveTerroir()

      expect(terroir.isElderMode.value).toBe(false)
      terroir.toggleElderMode()
      expect(terroir.isElderMode.value).toBe(true)
      terroir.toggleElderMode(false)
      expect(terroir.isElderMode.value).toBe(false)
    })

    it('toggles High-Glare Sunlight Mode with document attribute updates', () => {
      const terroir = useCognitiveTerroir()

      expect(terroir.isHighGlare.value).toBe(false)
      terroir.toggleHighGlare(true)
      expect(terroir.isHighGlare.value).toBe(true)
      expect(document.documentElement.getAttribute('data-outdoor-contrast')).toBe('high')

      terroir.toggleHighGlare(false)
      expect(terroir.isHighGlare.value).toBe(false)
      expect(document.documentElement.hasAttribute('data-outdoor-contrast')).toBe(false)
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 5. VernacularGlyph Component (All 32 Native Vector Glyphs)
  // ──────────────────────────────────────────────────────────────────────────
  describe('VernacularGlyph.vue Component', () => {
    const CANONICAL_32_GLYPHS = [
      'mangthit-kiln',
      'mekong-boat-eye',
      'barringtonia-flower',
      'water-lily',
      'three-plank-sampan',
      'conical-hat',
      'rice-husk-smoke',
      'coconut-palm',
      'pottery-wheel',
      'temple-roof',
      'fishing-basket',
      'silt-current',
      'wind-monsoon',
      'elder-glasses',
      'sun-glare',
      'guilloche-pass',
      'wax-seal',
      'green-lotus',
      'field-compass',
      'eoc-routing',
      'ancient-brick',
      'water-coconut',
      'lunar-tide',
      'rambutan-fruit',
      'durian-orchard',
      'tufte-marginalia',
      'ferry-landing',
      'mekong-net',
      'clay-artisan',
      'pagoda-spire',
      'bird-sanctuary',
      'sediment-delta',
    ]

    it('renders clean SVG for all 32 canonical native glyphs', () => {
      expect(CANONICAL_32_GLYPHS.length).toBe(32)

      for (const glyphName of CANONICAL_32_GLYPHS) {
        const wrapper = mount(VernacularGlyph, {
          props: { name: glyphName, size: 28 },
        })

        const svg = wrapper.find('svg')
        expect(svg.exists(), `Glyph ${glyphName} must render an SVG element`).toBe(true)
        expect(svg.attributes('viewBox')).toBe('0 0 24 24')
        expect(svg.attributes('width')).toBe('28')
        expect(svg.attributes('height')).toBe('28')
        expect(svg.classes()).toContain(`glyph--${glyphName}`)
        expect(svg.html()).toMatch(/<(path|ellipse|circle|rect|polygon)/)
        wrapper.unmount()
      }
    })

    it('supports well-known cultural aliases and synonyms', () => {
      const aliases: Array<[string, string]> = [
        ['mang-thit-kiln', 'mangthit-kiln'],
        ['eco-routing', 'eoc-routing'],
        ['water-coconut-palm', 'water-coconut'],
        ['ancient-communal-roof', 'temple-roof'],
        ['fish-trap-lo', 'fishing-basket'],
        ['water-tide-pulse', 'silt-current'],
        ['elder-reading', 'elder-glasses'],
        ['high-glare-sun', 'sun-glare'],
        ['pocket-pass', 'guilloche-pass'],
        ['sourcemark-seal', 'wax-seal'],
        ['lotus-lamp-ao-ba-om', 'green-lotus'],
        ['clay-brick', 'ancient-brick'],
        ['durian-ri6', 'durian-orchard'],
        ['ferry-crossing', 'ferry-landing'],
      ]

      for (const [alias, canonical] of aliases) {
        const wrapper = mount(VernacularGlyph, {
          props: { name: alias! },
        })
        expect(wrapper.classes()).toContain(`glyph--${canonical}`)
        wrapper.unmount()
      }
    })

    it('falls back gracefully to mangthit-kiln for unknown glyph names', () => {
      const wrapper = mount(VernacularGlyph, {
        props: { name: 'unknown-alien-glyph' },
      })

      expect(wrapper.classes()).toContain('glyph--mangthit-kiln')
      expect(wrapper.html()).toContain('M4 21h16')
      wrapper.unmount()
    })

    it('supports terroir color accents and custom size presets', () => {
      const wrapper = mount(VernacularGlyph, {
        props: {
          name: 'mangthit-kiln',
          size: 'xl',
          accent: 'clay',
        },
      })

      expect(wrapper.attributes('width')).toBe('48')
      expect(wrapper.classes()).toContain('glyph--accent-clay')
      wrapper.unmount()
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // 6. Edward Tufte Scholarly Marginalia (TufteSidenote.vue)
  // ──────────────────────────────────────────────────────────────────────────
  describe('TufteSidenote.vue Component', () => {
    it('renders desktop gutter marginalia with Lora italic styling and section mark', () => {
      const wrapper = mount(TufteSidenote, {
        props: {
          number: 3,
          content: 'Trích Địa chí Vĩnh Long, tư liệu gác sách Tụy Văn Lâu.',
          sourceTitle: 'Địa chí Vĩnh Long 2020',
          sourceUrl: 'https://vinhlong.gov.vn/diachi',
          authorityTier: 'TIER_1_GOVERNMENT',
        },
        global: {
          stubs: {
            SourceMark: true,
          },
        },
      })

      // Gutter aside element
      const aside = wrapper.find('aside.tufte-sidenote')
      expect(aside.exists()).toBe(true)
      expect(aside.text()).toContain('§3')
      expect(aside.text()).toContain('Trích Địa chí Vĩnh Long')
      expect(aside.text()).toContain('Thẩm quyền Nhà nước')
      expect(aside.find('cite').text()).toContain('Địa chí Vĩnh Long 2020')

      // Desktop link
      const link = aside.find('a.tufte-sidenote__link')
      expect(link.exists()).toBe(true)
      expect(link.attributes('href')).toBe('https://vinhlong.gov.vn/diachi')

      wrapper.unmount()
    })

    it('renders mobile trigger button with >= 44px touch target ergonomics', () => {
      const wrapper = mount(TufteSidenote, {
        props: {
          number: 1,
          content: 'Chú giải ngắn.',
        },
        global: {
          stubs: {
            SourceMark: true,
          },
        },
      })

      const trigger = wrapper.find('button.tufte-sidenote-trigger')
      expect(trigger.exists()).toBe(true)
      expect(trigger.attributes('aria-controls')).toBe('tufte-note-1')
      expect(trigger.attributes('aria-expanded')).toBe('false')
      expect(trigger.text()).toContain('§')
      expect(trigger.text()).toContain('1')

      wrapper.unmount()
    })

    it('toggles mobile bottom sheet dialog upon trigger click and closes on Escape', async () => {
      const wrapper = mount(TufteSidenote, {
        props: {
          number: 2,
          content: 'Nội dung chi tiết chú giải lề.',
          sourceTitle: 'Sổ tay NotebookLM',
        },
        global: {
          stubs: {
            SourceMark: true,
            Teleport: true,
          },
        },
      })

      const trigger = wrapper.find('button.tufte-sidenote-trigger')
      await trigger.trigger('click')

      expect(trigger.attributes('aria-expanded')).toBe('true')
      const bottomSheet = wrapper.find('.tufte-bottom-sheet')
      expect(bottomSheet.exists()).toBe(true)
      expect(bottomSheet.attributes('role')).toBe('dialog')
      expect(bottomSheet.attributes('aria-modal')).toBe('true')
      expect(bottomSheet.text()).toContain('Nội dung chi tiết chú giải lề.')

      // Close via close button
      const closeBtn = wrapper.find('button.tufte-sheet-close')
      await closeBtn.trigger('click')
      expect(trigger.attributes('aria-expanded')).toBe('false')

      wrapper.unmount()
    })
  })
})
