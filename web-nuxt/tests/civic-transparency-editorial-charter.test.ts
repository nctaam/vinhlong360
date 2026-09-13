// @vitest-environment node
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(process.cwd())
const doc = (rel: string) => readFileSync(resolve(root, rel), 'utf8')

describe('R4: Civic Transparency, Editorial Charter & Ombudsman Governance (Moc 134)', () => {
  // ─── TIER 1: FEATURE COVERAGE (Core Requirements) ───────────────────────────
  describe('Tier 1: Feature Coverage — Editorial Charter, Fact-Checking & Ombudsman Bridge', () => {
    it('F4-1: renders independent editorial charter and non-commercial conservation manifesto on pages/gioi-thieu.vue', () => {
      const src = doc('pages/gioi-thieu.vue')
      expect(src).toContain('data-color-system="tri-region-v1"')
      expect(src).toContain('id="ban-bien-tap"')
      expect(src).toContain('editors-infobox')
      expect(src).toContain('Tôn chỉ biên tập &amp; Phương pháp thẩm định thông tin')
      expect(src).toContain('phi thương mại bảo tồn di sản và văn hóa sông nước Cửu Long')
      expect(src).toContain('không thu phí xếp hạng điểm đến')
      expect(src).toContain('không bán tour du lịch')
      expect(src).toContain('không nhận quảng cáo ẩn làm sai lệch thông tin bản địa')
    })

    it('F4-2: documents the 3-tier fact-checking methodology across official, academic, and field witnesses', () => {
      const src = doc('pages/gioi-thieu.vue')
      expect(src).toContain('Quy trình thẩm định dữ liệu 3 tầng (3-Tier Fact-Checking)')
      // Tier 1: State Authority & Legal Sources
      expect(src).toContain('Tầng 1 (Nguồn thẩm quyền Nhà nước &amp; Pháp lý)')
      expect(src).toContain('.gov.vn')
      expect(src).toContain('Cục Di sản Văn hóa')
      // Tier 2: Gazetteer Research & Academic Depth
      expect(src).toContain('Tầng 2 (Khảo cứu địa chí &amp; Học thuật chuyên sâu)')
      expect(src).toContain('Viện Khoa học Xã hội vùng Nam Bộ')
      expect(src).toContain('Địa chí Vĩnh Long')
      // Tier 3: Field Verification & Local Witnesses
      expect(src).toContain('Tầng 3 (Kiểm chứng thực địa &amp; Nhân chứng bản xứ)')
      expect(src).toContain('tọa độ vệ tinh GPS')
      expect(src).toContain('nghệ nhân lão thành')
    })

    it('F4-3: integrates SourceMark tier="official" seal in mastheads and adheres to verifiedAt transparency protocol', () => {
      const srcAbout = doc('pages/gioi-thieu.vue')
      expect(srcAbout).toContain('<SourceMark tier="official" />')
      expect(srcAbout).toContain('Minh bạch kiểm chứng thực địa &amp; Nhãn SourceMark')
      expect(srcAbout).toContain('attributes.verifiedAt')
      expect(srcAbout).toContain('Chưa kiểm chứng thực địa')
      expect(srcAbout).toContain('graceful collapse')

      const srcContact = doc('pages/lien-he.vue')
      expect(srcContact).toContain('<SourceMark tier="official" />')
    })

    it('F4-4: establishes Civic Correction Bridge Card and ombudsman accountability on pages/lien-he.vue', () => {
      const src = doc('pages/lien-he.vue')
      expect(src).toContain('card-correction')
      expect(src).toContain('card-correction--prominent')
      expect(src).toContain('Trách nhiệm giải trình · Ombudsman')
      expect(src).toContain('Sửa thông tin chưa đúng')
      expect(src).toContain('to="/yeu-cau/sua-thong-tin"')
      expect(src).toContain('to="/yeu-cau/tra-cuu"')
      expect(src).toContain('Chúng tôi không bán tour. Chúng tôi giới thiệu vùng đất.')
    })

    it('F4-5: provides two-factor receipt lookup form with masked capability key on pages/yeu-cau/tra-cuu.vue', () => {
      const src = doc('pages/yeu-cau/tra-cuu.vue')
      expect(src).toContain('id="lookup-reference"')
      expect(src).toContain('id="lookup-capability"')
      expect(src).toMatch(/id="lookup-capability"[\s\S]*?type="password"/)
      expect(src).toContain('Mã tra cứu')
      expect(src).toContain('Mã một lần')
      expect(src).toContain('Dùng hai mã trên biên nhận bạn đã lưu')
    })
  })

  // ─── TIER 2: BOUNDARY, QUALITY & ANTI-SLOP DISCIPLINE ───────────────────────
  describe('Tier 2: Boundary Invariants, Anti-Slop & Editorial Aesthetics', () => {
    it('B4-1: enforces receipt lookup validation error feedback and disabled submit guards', () => {
      const src = doc('pages/yeu-cau/tra-cuu.vue')
      expect(src).toContain('data-role="lookup-failure"')
      expect(src).toContain('role="alert"')
      expect(src).toContain(':disabled="busy || !reference.trim() || !capability.trim()"')
      expect(src).toContain("failure.value = error instanceof CaseAccessError")
    })

    it('B4-2: employs authentic editorial typography and forbids Times New Roman across civic pages', () => {
      const srcAbout = doc('pages/gioi-thieu.vue')
      expect(srcAbout).toContain('editorial-body')
      expect(srcAbout).toContain('drop-cap')
      expect(srcAbout).toContain('pull-quote')

      const srcContact = doc('pages/lien-he.vue')
      expect(srcContact).toContain('contact-quote')

      // Ensure no raw Times New Roman fonts are declared
      expect(srcAbout).not.toContain('Times New Roman')
      expect(srcContact).not.toContain('Times New Roman')
    })

    it('B4-3: strictly forbids raw emoji salad and marketing promotional slop in civic content', () => {
      const srcAbout = doc('pages/gioi-thieu.vue')
      // cleanBody strips raw emojis using unicode range regex
      expect(srcAbout).toMatch(/\/\[\\u\{1F300\}-\\u\{1FAFF\}\\u\{2600\}-\\u\{27BF\}\]\/gu/)
      // Forbid promotional buzzwords
      expect(srcAbout).not.toContain('nâng tầm trải nghiệm')
      expect(srcAbout).not.toContain('thiên đường nghỉ dưỡng')
      expect(srcAbout).not.toContain('đẳng cấp thượng lưu')

      const srcContact = doc('pages/lien-he.vue')
      expect(srcContact).not.toContain('nâng tầm trải nghiệm')
      expect(srcContact).not.toContain('thiên đường nghỉ dưỡng')
    })

    it('B4-4: strictly enforces robots noindex/nofollow privacy guards on transactional intake pages', () => {
      const srcIntake = doc('pages/yeu-cau/sua-thong-tin.vue')
      expect(srcIntake).toMatch(/robots:\s*['"]noindex,\s*nofollow['"]/)

      const srcLookup = doc('pages/yeu-cau/tra-cuu.vue')
      expect(srcLookup).toMatch(/robots:\s*['"]noindex,\s*nofollow['"]/)
    })
  })

  // ─── TIER 3: COMBINATORIAL & SERVICE LEVEL INVARIANTS ───────────────────────
  describe('Tier 3: Combinatorial & Service Level Invariants', () => {
    it('C4-1: ensures capability secrets travel exclusively in POST body and never in browser URL history', () => {
      const srcLookup = doc('pages/yeu-cau/tra-cuu.vue')
      expect(srcLookup).toContain('cases.exchangeReceipt(reference.value.trim(), capability.value.trim())')
      expect(srcLookup).toContain("router.push('/yeu-cau/trang-thai')")
      // Capability key is wiped immediately after exchange
      expect(srcLookup).toContain("capability.value = ''")
    })

    it('C4-2: documents explicit ombudsman resolution SLAs on pages/lien-he.vue', () => {
      const src = doc('pages/lien-he.vue')
      // 10 days for access/rectification, 15 days for consent withdrawal per Decree 13/2023
      expect(src).toMatch(/truy cập\/chỉnh sửa\s*\(10 ngày\)/)
      expect(src).toMatch(/rút đồng ý\s*\(15 ngày\)/)
      expect(src).toContain('accountErasureDeadlineDays')
    })

    it('C4-3: enforces input ergonomics (min-height >= 44px) and semantic control radii on civic forms', () => {
      const srcLookup = doc('pages/yeu-cau/tra-cuu.vue')
      expect(srcLookup).toMatch(/\.case-field input\s*\{[\s\S]*?min-height:\s*44px;[\s\S]*?border-radius:\s*var\(--radius-control\);/)
      
      const srcIntake = doc('pages/yeu-cau/sua-thong-tin.vue')
      expect(srcIntake).toContain('var(--radius-control)')
      expect(srcIntake).toContain('var(--radius-surface)')
    })
  })

  // ─── TIER 4: REAL-WORLD CIVIC OVERSIGHT JOURNEYS ─────────────────────────────
  describe('Tier 4: Real-World Civic Oversight & Independent Ombudsman Journeys', () => {
    it('J4-1: Journey — Heritage researcher discovers factual discrepancy, inspects methodology and files correction request', () => {
      const srcAbout = doc('pages/gioi-thieu.vue')
      // Discovers editorial charter and 3-tier fact checking
      expect(srcAbout).toContain('Tiếp nhận hiệu đính &amp; Trách nhiệm giải trình')
      expect(srcAbout).toContain('to="/yeu-cau/sua-thong-tin"')

      const srcContact = doc('pages/lien-he.vue')
      expect(srcContact).toContain('Mọi đề xuất đính chính di tích, toạ độ thực địa')

      const srcIntake = doc('pages/yeu-cau/sua-thong-tin.vue')
      // Intake form receives entity and field parameters
      expect(srcIntake).toContain('useCorrectionCases')
      expect(srcIntake).toContain('<CorrectionIntakeForm')
      expect(srcIntake).toContain('<CaseReceiptCard')
    })

    it('J4-2: Journey — Citizen checks ombudsman resolution status via two-factor receipt without credential leakage', () => {
      const srcLookup = doc('pages/yeu-cau/tra-cuu.vue')
      // Inputting reference code and one-time secret key
      expect(srcLookup).toContain('id="lookup-reference"')
      expect(srcLookup).toContain('id="lookup-capability"')
      // Executes exchange and navigates to session-secured status page
      expect(srcLookup).toContain('exchangeReceipt')
      expect(srcLookup).toContain('/yeu-cau/trang-thai')
      // Error handling gives unified opaque error to prevent oracle enumeration
      expect(srcLookup).toContain('CaseAccessError')
    })
  })
})
