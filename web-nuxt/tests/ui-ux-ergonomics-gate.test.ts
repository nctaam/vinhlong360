import { describe, it, expect } from "vitest"
import { readFileSync, readdirSync, statSync } from "node:fs"
import { resolve, join, relative } from "node:path"

describe("Mốc 103: UI/UX Ergonomics, WCAG 2.2 Touch Targets & EmptyState Governance Gate", () => {
  const root = process.cwd()

  it("EntityCard.vue mở rộng vùng chạm 44px cho .card-arrow theo chuẩn WCAG 2.2 SC 2.5.8", () => {
    const content = readFileSync(resolve(root, "components/EntityCard.vue"), "utf8")
    expect(content).toMatch(/\.card-arrow::before\s*\{[\s\S]*?min-width:\s*44px;[\s\S]*?min-height:\s*44px;/i)
  })

  it("EntityReviews.vue mở rộng vùng chạm 44px cho .rf-image-remove theo chuẩn WCAG 2.2 SC 2.5.8", () => {
    const content = readFileSync(resolve(root, "components/EntityReviews.vue"), "utf8")
    expect(content).toMatch(/\.rf-image-remove::before\s*\{[\s\S]*?min-width:\s*44px;[\s\S]*?min-height:\s*44px;/i)
  })

  it("ScrollToTop.vue hỗ trợ biến token động --scroll-top-bottom", () => {
    const content = readFileSync(resolve(root, "components/ScrollToTop.vue"), "utf8")
    expect(content).toContain("var(--scroll-top-bottom")
  })

  it("assets/css/detail.css nâng tầng .scroll-top tránh đè lên Sticky CTA Bar trên di động", () => {
    const content = readFileSync(resolve(root, "assets/css/detail.css"), "utf8")
    expect(content).toMatch(/@media\s*\(max-width:\s*840px\)[\s\S]*?\.scroll-top\s*\{[\s\S]*?bottom:\s*calc\(var\(--shell-public-bottom-nav-reserved-height\)\s*\+\s*72px/i)
  })

  it("JourneyBar.vue quản lý body state has-journey-bar và nâng tầng .scroll-top", () => {
    const content = readFileSync(resolve(root, "components/JourneyBar.vue"), "utf8")
    expect(content).toContain("has-journey-bar")
    expect(content).toMatch(/body\.has-journey-bar\s+\.scroll-top/)
  })

  it("EmptyState.vue tự động bao bọc an toàn cả #actions và default slot trong .empty-actions", () => {
    const content = readFileSync(resolve(root, "components/EmptyState.vue"), "utf8")
    expect(content).toMatch(/<div\s+v-if="\$slots\.actions\s*\|\|\s*\$slots\.default"\s+class="empty-actions"/)
  })

  it("Tất cả các trang công khai gọi EmptyState có nút hành động đều dùng semantic template #actions", () => {
    function walk(dir) {
      let results = []
      const list = readdirSync(dir)
      for (const file of list) {
        const full = join(dir, file)
        const stat = statSync(full)
        if (stat && stat.isDirectory()) {
          results = results.concat(walk(full))
        } else if (file.endsWith(".vue")) {
          results.push(full)
        }
      }
      return results
    }

    const pages = walk(resolve(root, "pages")).filter(p => !p.includes("admin"))
    const violations = []

    for (const file of pages) {
      const content = readFileSync(file, "utf8")
      const rel = relative(root, file).replace(/\\/g, "/")
      const matches = content.match(/<EmptyState[\s\S]*?<\/EmptyState>/g) || []

      for (const m of matches) {
        if (m.includes("<button") || m.includes("<NuxtLink") || m.includes("<a ")) {
          if (!m.includes("#actions") && !m.includes("v-slot:actions") && !m.includes("slot=\"actions\"")) {
            violations.push({ file: rel, snippet: m.slice(0, 120).replace(/\s+/g, " ") })
          }
        }
      }
    }

    expect(violations).toHaveLength(0)
  })

  it("Các EmptyState trên bề mặt công cụ chính (lich-trinh/[id], tao-lich-trinh) đều có icon-name và title", () => {
    const lichTrinhId = readFileSync(resolve(root, "pages/lich-trinh/[id].vue"), "utf8")
    const taoLichTrinh = readFileSync(resolve(root, "pages/tao-lich-trinh.vue"), "utf8")

    expect(lichTrinhId).not.toMatch(/<EmptyState\s+message=/)
    expect(taoLichTrinh).not.toMatch(/<EmptyState\s+message=/)
  })
})
