// @vitest-environment node
import { describe, it, expect } from "vitest"
import { readFileSync, existsSync } from "node:fs"
import { resolve } from "node:path"

describe("Adversarial Empirical Challenger: Mobile Ergonomics & Micro-Typography Gate", () => {
  const root = process.cwd()

  describe("1. 320px–414px Mobile Viewport Behavior & Zero Overflow", () => {
    it("assets/css/shell.css hides display settings on <=400px viewports to eliminate ~30px header overflow", () => {
      const shellCss = readFileSync(resolve(root, "assets/css/shell.css"), "utf8")
      const mediaIdx = shellCss.indexOf("@media (max-width: 400px)")
      expect(mediaIdx).toBeGreaterThan(0)
      const mediaChunk = shellCss.slice(mediaIdx, mediaIdx + 300)
      expect(mediaChunk).toContain(".display-settings-wrapper")
      expect(mediaChunk).toMatch(/display:\s*none/)
    })

    it("HomeRiversideStays.vue protects grid columns against 320px blowout using min(100%, 260px)", () => {
      const staysVue = readFileSync(resolve(root, "components/home/HomeRiversideStays.vue"), "utf8")
      expect(staysVue).toContain("grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));")
    })

    it("assets/css/base.css eliminates double-gutter padding trap between .page and .block on mobile", () => {
      const baseCss = readFileSync(resolve(root, "assets/css/base.css"), "utf8")
      expect(baseCss).toMatch(/@media\s*\(max-width:\s*640px\)\s*\{\s*\.page\s*>\s*\.block\s*\{\s*padding-inline:\s*0;\s*\}\s*\}/)
    })

    it("pages/danh-ba.vue prevents tab blowout at <=640px via overflow-x horizontal scroll", () => {
      const danhBaVue = readFileSync(resolve(root, "pages/danh-ba.vue"), "utf8")
      const mediaIdx = danhBaVue.indexOf("@media (max-width: 640px)")
      expect(mediaIdx).toBeGreaterThan(0)
      const mediaChunk = danhBaVue.slice(mediaIdx, mediaIdx + 350)
      expect(mediaChunk).toMatch(/overflow-x:\s*auto/)
      expect(mediaChunk).toMatch(/flex-wrap:\s*nowrap/)
      expect(mediaChunk).toMatch(/\.gazetteer-tab\s*\{[\s\S]*?flex-shrink:\s*0/)
    })

    it("pages/ban-do.vue hides floating thumb dock in list view to preserve viewport space", () => {
      const banDoVue = readFileSync(resolve(root, "pages/ban-do.vue"), "utf8")
      expect(banDoVue).toContain(':data-panel="searchView.state.value.panel"')
      expect(banDoVue).toContain('[data-panel="list"] .map-floating-thumb-dock')
      expect(banDoVue).toMatch(/\[data-panel="list"\]\s+\.map-floating-thumb-dock\s*\{[\s\S]*?display:\s*none\s*!important;/)
    })

    it("assets/css/cards.css enforces single-column 1fr grid on mobile viewports <=480px", () => {
      const cardsCss = readFileSync(resolve(root, "assets/css/cards.css"), "utf8")
      expect(cardsCss).toMatch(/@container\s*\(max-width:\s*480px\)\s*\{[\s\S]*?\.grid\s*\{[\s\S]*?grid-template-columns:\s*1fr;/)
    })

    it("assets/css/catalog.css provides horizontal momentum scrolling on .scroll-row with zero viewport bleed", () => {
      const catalogCss = readFileSync(resolve(root, "assets/css/catalog.css"), "utf8")
      expect(catalogCss).toMatch(/\.scroll-row\s*\{[\s\S]*?overflow-x:\s*auto;[\s\S]*?-webkit-overflow-scrolling:\s*touch;/)
      expect(catalogCss).toMatch(/@media\s*\(max-width:\s*640px\)\s*\{[\s\S]*?\.scroll-row\s*>\s*\*\s*\{[\s\S]*?flex:\s*0\s*0\s*220px;/)
    })
  })

  describe("2. Touch Targets (>= 44px x 44px WCAG 2.2 SC 2.5.8)", () => {
    it("SaveButton.vue: small variant (.save-btn-sm) satisfies minimum 44px x 44px bounds", () => {
      const saveBtnVue = readFileSync(resolve(root, "components/SaveButton.vue"), "utf8")
      expect(saveBtnVue).toMatch(/\.save-btn-sm\s*\{[\s\S]*?min-height:\s*44px;[\s\S]*?min-width:\s*44px;/)
    })

    it("FilterChips.vue: chip element (.fc-chip) maintains minimum 44px height and padded tap width", () => {
      const fcVue = readFileSync(resolve(root, "components/FilterChips.vue"), "utf8")
      expect(fcVue).toMatch(/\.fc-chip\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(fcVue).toMatch(/\.fc-chip\s*\{[\s\S]*?padding:\s*0\s+var\(--space-4\);/)
    })

    it("assets/css/catalog.css: .chip maintains min-height: 44px and phone min-width: 80px", () => {
      const catalogCss = readFileSync(resolve(root, "assets/css/catalog.css"), "utf8")
      expect(catalogCss).toMatch(/\.chip\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(catalogCss).toMatch(/@media\s*\(max-width:\s*640px\)\s*\{[\s\S]*?\.chip\s*\{[\s\S]*?min-width:\s*80px;/)
    })

    it("pages/ban-do.vue: all field action buttons have >= 44px touch targets", () => {
      const banDoVue = readFileSync(resolve(root, "pages/ban-do.vue"), "utf8")
      expect(banDoVue).toMatch(/\.map-zoom-btn\s*\{[\s\S]*?min-width:\s*46px;[\s\S]*?min-height:\s*46px;/)
      expect(banDoVue).toMatch(/\.map-terroir-gps-btn\s*\{[\s\S]*?min-height:\s*46px;/)
      expect(banDoVue).toMatch(/\.map-quick-preset-btn\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(banDoVue).toMatch(/\.map-contrast-toggle\s*\{[\s\S]*?min-height:\s*44px;/)
      expect(banDoVue).toMatch(/\.map-fullbleed-toggle\s*\{[\s\S]*?min-height:\s*44px;/)
    })

    it("assets/css/base.css: .see-all link button maintains min-height: 44px", () => {
      const baseCss = readFileSync(resolve(root, "assets/css/base.css"), "utf8")
      expect(baseCss).toMatch(/\.see-all\s*\{[\s\S]*?min-height:\s*44px;/)
    })

    it("pages/danh-ba.vue: .gazetteer-tab buttons maintain min-height: 44px", () => {
      const danhBaVue = readFileSync(resolve(root, "pages/danh-ba.vue"), "utf8")
      expect(danhBaVue).toMatch(/\.gazetteer-tab\s*\{[\s\S]*?min-height:\s*44px;/)
    })
  })

  describe("3. Vietnamese Micro-Typography & Syllabic Word Wrapping", () => {
    it("EntityCard.vue eliminates hyphens: auto and uses overflow-wrap: break-word & text-wrap: pretty", () => {
      const cardVue = readFileSync(resolve(root, "components/EntityCard.vue"), "utf8")
      const cardNameMatches = [...cardVue.matchAll(/\.card-name\s*\{([^}]+)\}/g)]
      const activeCardNameRule = cardNameMatches[cardNameMatches.length - 1][1]
      expect(activeCardNameRule).not.toContain("hyphens: auto")
      expect(activeCardNameRule).not.toContain("overflow-wrap: anywhere")
      expect(activeCardNameRule).toContain("overflow-wrap: break-word")
      expect(activeCardNameRule).toContain("text-wrap: pretty")
    })

    it("assets/css/base.css: .section-head h2 restores natural block context and enables text-wrap: balance", () => {
      const baseCss = readFileSync(resolve(root, "assets/css/base.css"), "utf8")
      const h2Match = baseCss.match(/\.section-head\s+h2\s*\{([^}]+)\}/)
      expect(h2Match).toBeTruthy()
      expect(h2Match![1]).not.toContain("display: flex")
      expect(h2Match![1]).toContain("text-wrap: balance")
    })

    it("Zero hyphens: auto across all production styles to safeguard Vietnamese syllabic integrity", () => {
      const globalCssFiles = [
        "assets/css/variables.css",
        "assets/css/base.css",
        "assets/css/shell.css",
        "assets/css/cards.css",
        "assets/css/catalog.css",
        "assets/css/home-nocturne.css",
        "assets/css/detail.css",
        "assets/css/components.css"
      ]
      for (const rel of globalCssFiles) {
        const full = resolve(root, rel)
        if (existsSync(full)) {
          const content = readFileSync(full, "utf8")
          expect(content).not.toMatch(/hyphens:\s*auto/i)
        }
      }
    })

    it("HomeRiversideStays.vue enables text-wrap: pretty for card title and description", () => {
      const staysVue = readFileSync(resolve(root, "components/home/HomeRiversideStays.vue"), "utf8")
      expect(staysVue).toMatch(/\.home-stay-card__title\s*\{[\s\S]*?text-wrap:\s*pretty;/)
      expect(staysVue).toMatch(/\.home-stay-card__desc\s*\{[\s\S]*?text-wrap:\s*pretty;/)
    })
  })
})
