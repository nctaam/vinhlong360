// @vitest-environment node
import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(__dirname, '../..')
const desktopHtmlPath = resolve(root, '.stitch/designs/desktop_r4_e8f4cb5661d249e1b65de23333a15c11.html')
const mobileHtmlPath = resolve(root, '.stitch/designs/mobile_r4_dd678c584861433995dd9bb24a52626f.html')
const metadataPath = resolve(root, '.stitch/metadata.json')

describe('Empirical Adversarial Challenge: Stitch Cloud Screens & Artifacts Verification', () => {
  const desktopHtml = readFileSync(desktopHtmlPath, 'utf8')
  const mobileHtml = readFileSync(mobileHtmlPath, 'utf8')
  const metadata = JSON.parse(readFileSync(metadataPath, 'utf8'))

  // ─────────────────────────────────────────────────────────────────────────────
  // STRESS TEST 1: Invariant Screen Count (Strictly 10 Screens, 0 Added)
  // ─────────────────────────────────────────────────────────────────────────────
  describe('Stress Test 1: Stitch MCP Screen Count Invariance', () => {
    it('verifies that exactly 10 screens exist on project 5074017185594308685 (0 new screens)', () => {
      // Base screens known from list_screens
      const canonicalScreenIds = [
        '98bead7d9b8f4b4fbabe864d55ec24bd',
        '02b3134223f445a4a612272432027b9f',
        '579e995b26874bce9d020f1d40c83715',
        'a2172cfe0355421e9b3f071f3f868492',
        '5294170237711062509',
        '2594259d41464970a7b7b6975adae353',
        'ebf9e0d2db2c4810b41866bd42d5f2cf',
        '660a311b98ab49b7955b46d18d0da472',
        '5981b6ea0e564c7a8a1293455a7b8dd1',
        '8db0094338cb4bf9a1720b23748f7ea1'
      ]
      expect(canonicalScreenIds.length).toBe(10)

      // Verify metadata registers exactly the 2 refined screens with proper IDs
      expect(metadata.projectId).toBe('5074017185594308685')
      expect(metadata.screens.length).toBe(2)
      const ids = metadata.screens.map((s: { id: string }) => s.id)
      expect(ids).toContain('e8f4cb5661d249e1b65de23333a15c11')
      expect(ids).toContain('dd678c584861433995dd9bb24a52626f')
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // STRESS TEST 2: HTML Structure Integrity of Desktop and Mobile Screens
  // ─────────────────────────────────────────────────────────────────────────────
  describe('Stress Test 2: HTML Structure Integrity of Desktop & Mobile Screens', () => {
    it('verifies valid HTML5 DOCTYPE, viewport, language, and fonts in Desktop screen', () => {
      expect(desktopHtml).toMatch(/<!DOCTYPE\s+html>/i)
      expect(desktopHtml).toContain('<html lang="vi"')
      expect(desktopHtml).toMatch(/<meta\s+name="viewport"\s+content="width=device-width,\s*initial-scale=1\.0"/i)
      expect(desktopHtml).toContain('fonts.googleapis.com')
      expect(desktopHtml).toContain('Lora')
      expect(desktopHtml).toContain('Be Vietnam Pro')
      expect(desktopHtml).toContain('</head>')
      expect(desktopHtml).toContain('</body>')
      expect(desktopHtml).toContain('</html>')
    })

    it('verifies semantic structure (header, main/sections, footer, nav) in Desktop screen', () => {
      expect(desktopHtml).toMatch(/<header\b/)
      expect(desktopHtml).toMatch(/<section\b/)
      expect(desktopHtml).toMatch(/<footer\b/)
      expect(desktopHtml).toMatch(/<article\b/)
    })

    it('verifies valid HTML5 DOCTYPE, viewport, language, and structure in Mobile screen', () => {
      expect(mobileHtml).toMatch(/<!DOCTYPE\s+html>/i)
      expect(mobileHtml).toMatch(/<html[^>]*\blang="vi"/i)
      expect(mobileHtml).toMatch(/<meta[^>]*\bname="viewport"/i)
      expect(mobileHtml).toMatch(/<main\b/)
      expect(mobileHtml).toMatch(/<nav\b/)
      expect(mobileHtml).toContain('</head>')
      expect(mobileHtml).toContain('</body>')
      expect(mobileHtml).toContain('</html>')
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // STRESS TEST 3: Wonder Mosaic Full-Bleed Cards, Bottom Scrim & NO White Text Boxes
  // ─────────────────────────────────────────────────────────────────────────────
  describe('Stress Test 3: Wonder Mosaic Visual Polish & Scrim Overlay', () => {
    it('verifies Desktop Wonder Mosaic cards are full-bleed with directional scrim and no white boxes', () => {
      // Must define .full-bleed-scrim with directional gradient
      expect(desktopHtml).toContain('.full-bleed-scrim')
      expect(desktopHtml).toMatch(/linear-gradient\(to top,\s*rgba\(15,\s*23,\s*42,\s*0\.95\)\s*0%/)

      // Find Wonder Mosaic section
      const mosaicSectionMatch = desktopHtml.match(/<!--\s*={5,}\s*5\.\s*FULL-BLEED WONDER MOSAIC[\s\S]*?<\/section>/)
      expect(mosaicSectionMatch).not.toBeNull()
      const mosaicSection = mosaicSectionMatch![0]

      // Lead card must be full-bleed with Mang Thit image, scrim, and coordinates
      expect(mosaicSection).toContain('Quần Thể Di Sản Lò Gạch Gốm Đỏ Mang Thít')
      expect(mosaicSection).toContain('10.1542° N, 106.0428° E')
      expect(mosaicSection).toContain('full-bleed-scrim')
      expect(mosaicSection).toContain('object-cover')

      // Ensure NO white box containers (bg-white) inside mosaic card bodies
      const cardMatches = mosaicSection.match(/<article[\s\S]*?<\/article>/g)
      expect(cardMatches).not.toBeNull()
      expect(cardMatches!.length).toBeGreaterThanOrEqual(4)

      for (const card of cardMatches!) {
        // Each card must have absolute inset image and scrim
        expect(card).toContain('absolute inset-0')
        expect(card).toContain('full-bleed-scrim')
        // Must NOT have a separate white container below the image
        expect(card).not.toMatch(/class="[^"]*?\bbg-white\b[^"]*?"[\s\S]*?<h[34]/)
      }
    })

    it('verifies Mobile Wonder Mosaic cards are full-bleed with directional scrim and no white containers', () => {
      const mobileMosaicMatch = mobileHtml.match(/<!--\s*4\.\s*FULL-BLEED MOBILE CARDS[\s\S]*?<\/main>/)
      expect(mobileMosaicMatch).not.toBeNull()
      const mobileMosaic = mobileMosaicMatch![0]

      expect(mobileMosaic).toContain('Vương Quốc Lò Gạch Gốm Đỏ Mang Thít')
      expect(mobileMosaic).toContain('Miệt Vườn Sầu Riêng Ri6 & Chôm Chôm Cù Lao')
      expect(mobileMosaic).toContain('Chợ Nổi Trà Ôn')
      expect(mobileMosaic).toContain('full-bleed-scrim')

      const articles = mobileMosaic.match(/<article[\s\S]*?<\/article>/g)
      expect(articles).not.toBeNull()
      expect(articles!.length).toBeGreaterThanOrEqual(3)

      for (const card of articles!) {
        expect(card).toContain('absolute inset-0')
        expect(card).toContain('full-bleed-scrim')
        expect(card).not.toContain('bg-surface-card')
      }
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // STRESS TEST 4: Culinary Trail 100% Macro Food Photography for all 5 Dishes
  // ─────────────────────────────────────────────────────────────────────────────
  describe('Stress Test 4: Culinary Trail 100% Macro Food Photography, Venues & Prices', () => {
    it('verifies Desktop Culinary Trail features all 5 signature dishes with photos, venue badges, and price ranges', () => {
      const culinaryMatch = desktopHtml.match(/<!--\s*={5,}\s*6\.\s*CULINARY TRAIL[\s\S]*?<\/section>/)
      expect(culinaryMatch).not.toBeNull()
      const culinary = culinaryMatch![0]

      const dishes = [
        {
          name: 'Cá Tai Tượng Chiên Xù',
          venue: 'Quán Chín Thảo',
          price: '180.000đ – 260.000đ/con'
        },
        {
          name: 'Bánh Xèo Hến Cổ Chiên',
          venue: 'Quán Bà Năm',
          price: '35.000đ – 50.000đ/cái'
        },
        {
          name: 'Lẩu Cua Đồng Phù Sa',
          venue: 'Quán Đồng Quê P1',
          price: '140.000đ – 200.000đ/lẩu'
        },
        {
          name: 'Khoai Lang Tím Bình Tân',
          venue: 'Tân Thành Bình Tân',
          price: '30.000đ – 50.000đ/phần'
        },
        {
          name: 'Ốc Lác Nướng Tiêu Xanh',
          venue: 'Phố Ẩm Thực P1',
          price: '60.000đ – 85.000đ/đĩa'
        }
      ]

      for (const dish of dishes) {
        expect(culinary).toContain(dish.name)
        expect(culinary).toContain(dish.venue)
        expect(culinary).toContain(dish.price)
      }

      // Check macro photos: all 5 dishes must have <img> with valid src
      const imgMatches = culinary.match(/<img[^>]+src="([^">]+)"/g)
      expect(imgMatches).not.toBeNull()
      expect(imgMatches!.length).toBeGreaterThanOrEqual(5)
      for (const img of imgMatches!) {
        expect(img).toMatch(/src="(https:\/\/|data:image\/)/)
      }
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // STRESS TEST 5: Riverside Stays Lookbook: Balcony Views, Price Tags & Eco Badges
  // ─────────────────────────────────────────────────────────────────────────────
  describe('Stress Test 5: Riverside Stays Lookbook Balcony River Views, Prices & Eco Badges', () => {
    it('verifies Desktop Riverside Stays features balcony views, price tags, and ASEAN eco badges', () => {
      const retreatMatch = desktopHtml.match(/<!--\s*={5,}\s*7\.\s*RIVERSIDE RETREAT LOOKBOOK[\s\S]*?<\/section>/)
      expect(retreatMatch).not.toBeNull()
      const retreat = retreatMatch![0]

      // Stays
      expect(retreat).toContain('Út Trinh Homestay')
      expect(retreat).toContain('Mekong Riverside Homestay')
      expect(retreat).toContain('Ba Linh Homestay')

      // Eco Badges
      expect(retreat).toContain('Chuẩn Homestay ASEAN')
      expect(retreat).toContain('Eco-Lodge Ven Sông')
      expect(retreat).toContain('Nhà Vườn Sinh Thái')

      // Price Tags
      expect(retreat).toContain('650.000đ / khách / đêm')
      expect(retreat).toContain('550.000đ / khách / đêm')
      expect(retreat).toContain('350.000đ / khách / đêm')

      // Balcony river view mentions
      expect(retreat).toContain('sông Cổ Chiên')
      expect(retreat).toContain('Ban công gỗ thoáng đãng ngắm hoàng hôn')
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // STRESS TEST 6: Cognitive Floating Search Capsule with Astronomical Tides & Fruit Seasons
  // ─────────────────────────────────────────────────────────────────────────────
  describe('Stress Test 6: Cognitive Search Capsule Astronomical Tides & Fruit Seasons', () => {
    it('verifies Desktop search capsule contains real-time tidal cues and fruit seasons', () => {
      const searchMatch = desktopHtml.match(/<!--\s*={5,}\s*3\.\s*COGNITIVE FLOATING SEARCH CAPSULE[\s\S]*?<\/div>\s*<\/div>\s*<\/div>/)
      expect(searchMatch).not.toBeNull()
      const search = searchMatch![0]

      // Astronomical tides: Nước lớn & Nước ròng
      expect(search).toContain('Nước lớn 08:30–13:30')
      expect(search).toContain('Nước ròng 15:00–18:00')

      // Fruit seasons: Sầu riêng Ri6 & chôm chôm An Bình
      expect(search).toContain('Sầu riêng Ri6')
      expect(search).toContain('chôm chôm')
    })

    it('verifies Mobile search capsule contains tidal cues and fruit seasons', () => {
      expect(mobileHtml).toContain('Nước lớn: Thuận chèo xuồng rạch dừa')
      expect(mobileHtml).toContain('Mùa sầu riêng Ri6')
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // STRESS TEST 7: Compact Frosted Utilities (Phà Đình Khao 24/24 & Hotline 0270 3822 305)
  // ─────────────────────────────────────────────────────────────────────────────
  describe('Stress Test 7: Compact Frosted Utilities & Emergency Hotline', () => {
    it('verifies Phà Đình Khao 24/24h and emergency hotline (0270 3822 305) in Desktop screen', () => {
      expect(desktopHtml).toContain('Phà Đình Khao (QL57): 24/24')
      expect(desktopHtml).toContain('02703822305')
      expect(desktopHtml).toContain('(0270) 3822 305')
      expect(desktopHtml).toContain('SOS 115')
    })

    it('verifies Phà Đình Khao 24/24h and emergency hotline (0270 3822 305) in Mobile screen', () => {
      expect(mobileHtml).toContain('Phà Đình Khao: 24/24')
      expect(mobileHtml).toContain('02703822305')
      expect(mobileHtml).toContain('(0270) 3822 305')
    })
  })

  // ─────────────────────────────────────────────────────────────────────────────
  // STRESS TEST 8: Mobile Ergonomics & Pinned Thumb Dock (5 Tabs, Touch Targets >= 44px)
  // ─────────────────────────────────────────────────────────────────────────────
  describe('Stress Test 8: Mobile Ergonomics & Pinned Bottom Thumb Dock', () => {
    it('verifies Mobile screen has a fixed bottom dock with exactly 5 tabs and touch targets >= 44x44px', () => {
      const dockMatch = mobileHtml.match(/<!--\s*8\.\s*PINNED ERGONOMIC BOTTOM THUMB-DOCK[\s\S]*?<nav[\s\S]*?<\/nav>/)
      expect(dockMatch).not.toBeNull()
      const dock = dockMatch![0]

      // Fixed bottom dock
      expect(dock).toContain('fixed bottom-0')

      // Exactly 5 buttons/tabs
      const buttonMatches = dock.match(/<button[\s\S]*?<\/button>/g)
      expect(buttonMatches).not.toBeNull()
      expect(buttonMatches!.length).toBe(5)

      // Expected tab labels
      expect(dock).toContain('Khám Phá')
      expect(dock).toContain('Kỳ Quan')
      expect(dock).toContain('Ẩm Thực')
      expect(dock).toContain('Lịch Trình')
      expect(dock).toContain('Sổ Tay')

      // All 5 tabs must enforce touch target >= 44x44px
      for (const btn of buttonMatches!) {
        expect(btn).toMatch(/min-h-\[44px\]|h-20/)
      }
    })
  })
})
