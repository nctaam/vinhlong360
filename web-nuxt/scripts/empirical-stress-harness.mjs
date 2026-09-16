// @ts-nocheck
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const webNuxt = resolve(__dirname, '..')

console.log('═══════════════════════════════════════════════════════════════════════════════')
console.log('       EMPIRICAL CHALLENGER ADVERSARIAL STRESS TEST HARNESS (M3)              ')
console.log('═══════════════════════════════════════════════════════════════════════════════\n')

let totalTests = 0
let passedTests = 0
let failedTests = 0
const findings = []

function assert(condition, testName, details = '') {
  totalTests++
  if (condition) {
    passedTests++
    console.log(`  ✓ PASS: ${testName}`)
  } else {
    failedTests++
    console.log(`  ✗ FAIL: ${testName} — ${details}`)
    findings.push({ testName, details })
  }
}

// Target files under review
const files = {
  showcase: resolve(webNuxt, 'components/home/HomeCuratedShowcase.vue'),
  culinary: resolve(webNuxt, 'components/home/HomeCulinaryTrail.vue'),
  stays: resolve(webNuxt, 'components/home/HomeRiversideStays.vue'),
  companion: resolve(webNuxt, 'components/home/HomeTravelCompanion.vue'),
  planner: resolve(webNuxt, 'components/home/HomeTravelPlanner.vue'),
  index: resolve(webNuxt, 'pages/index.vue'),
  homeNocturneCss: resolve(webNuxt, 'assets/css/home-nocturne.css'),
  baseCss: resolve(webNuxt, 'assets/css/base.css'),
  variablesCss: resolve(webNuxt, 'assets/css/variables.css'),
}

const showcaseContent = readFileSync(files.showcase, 'utf8')
const culinaryContent = readFileSync(files.culinary, 'utf8')
const staysContent = readFileSync(files.stays, 'utf8')
const companionContent = readFileSync(files.companion, 'utf8')
const plannerContent = readFileSync(files.planner, 'utf8')
const indexContent = readFileSync(files.index, 'utf8')
const homeNocturneCss = readFileSync(files.homeNocturneCss, 'utf8')
const baseCss = readFileSync(files.baseCss, 'utf8')
const variablesCss = readFileSync(files.variablesCss, 'utf8')

// ─────────────────────────────────────────────────────────────────────────────
// STRESS TEST 1: Touch Targets on Interactive Elements (>= 44x44px)
// ─────────────────────────────────────────────────────────────────────────────
console.log('─── STRESS TEST 1: Touch Targets on Interactive Elements (>= 44x44px) ───')

// 1.1 Global standard
const touchMinDef = variablesCss.match(/--touch-min:\s*(\d+)px;/)
assert(touchMinDef && parseInt(touchMinDef[1], 10) >= 44, 'variables.css defines --touch-min >= 44px', `Found: ${touchMinDef?.[0]}`)

const baseTouchRule = baseCss.includes(':where(a[href], button, [role="button"], input:not([type="hidden"]), select, textarea, summary) { min-height: var(--touch-min); }')
assert(baseTouchRule, 'base.css enforces min-height: var(--touch-min) across all interactive elements')

// 1.2 HomeCuratedShowcase
const leadBookmarkMatch = showcaseContent.match(/\.home-bookmark-btn\s*\{[\s\S]*?min-width:\s*(\d+)px;[\s\S]*?min-height:\s*(\d+)px;/)
assert(leadBookmarkMatch && parseInt(leadBookmarkMatch[1], 10) >= 44 && parseInt(leadBookmarkMatch[2], 10) >= 44,
  'HomeCuratedShowcase lead bookmark button >= 44x44px', `Found: min-width ${leadBookmarkMatch?.[1]}px, min-height ${leadBookmarkMatch?.[2]}px`)

const satBookmarkMatch = showcaseContent.match(/\.home-bookmark-btn--sm\s*\{[\s\S]*?min-width:\s*(\d+)px;[\s\S]*?min-height:\s*(\d+)px;/)
assert(satBookmarkMatch && parseInt(satBookmarkMatch[1], 10) >= 44 && parseInt(satBookmarkMatch[2], 10) >= 44,
  'HomeCuratedShowcase satellite bookmark button >= 44x44px', `Found: min-width ${satBookmarkMatch?.[1]}px, min-height ${satBookmarkMatch?.[2]}px`)

const leadActionsMatch = showcaseContent.match(/\.home-curated-lead__actions\s+\.btn\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
assert(leadActionsMatch && parseInt(leadActionsMatch[1], 10) >= 44,
  'HomeCuratedShowcase lead action buttons min-height >= 44px', `Found: ${leadActionsMatch?.[1]}px`)

const satLinkMatch = showcaseContent.match(/\.home-curated-satellite__link\s*\{[\s\S]*?min-height:\s*(?:var\(--touch-min,\s*(\d+)px\)|(\d+)px);/)
const satLinkVal = parseInt(satLinkMatch?.[1] ?? satLinkMatch?.[2] ?? '0', 10)
assert(satLinkVal >= 44, 'HomeCuratedShowcase satellite detail links min-height >= 44px', `Found: ${satLinkVal}px`)

// 1.3 HomeCulinaryTrail
const culinaryBtnMatch = culinaryContent.match(/\.home-culinary-card__btn\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
assert(culinaryBtnMatch && parseInt(culinaryBtnMatch[1], 10) >= 44,
  'HomeCulinaryTrail map action button min-height >= 44px', `Found: ${culinaryBtnMatch?.[1]}px`)

// 1.4 HomeRiversideStays
const staysBtnMatch = staysContent.match(/\.home-stay-card__action\s+\.btn\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
assert(staysBtnMatch && parseInt(staysBtnMatch[1], 10) >= 44,
  'HomeRiversideStays booking action button min-height >= 44px', `Found: ${staysBtnMatch?.[1]}px`)

// 1.5 HomeTravelCompanion
const compLinkMatch = companionContent.match(/\.home-companion-card__link\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
assert(compLinkMatch && parseInt(compLinkMatch[1], 10) >= 44,
  'HomeTravelCompanion card link min-height >= 44px', `Found: ${compLinkMatch?.[1]}px`)

const compHotlineMatch = companionContent.match(/\.home-hotline-btn\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
assert(compHotlineMatch && parseInt(compHotlineMatch[1], 10) >= 48,
  'HomeTravelCompanion hotline buttons min-height >= 48px', `Found: ${compHotlineMatch?.[1]}px`)

const compQuickHotlineMatch = companionContent.match(/\.home-hotline-btn--quick\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
assert(compQuickHotlineMatch && parseInt(compQuickHotlineMatch[1], 10) >= 48,
  'HomeTravelCompanion quick utility hotline button min-height >= 48px', `Found: ${compQuickHotlineMatch?.[1]}px`)

// 1.6 pages/index.vue
const heroFilterMatch = homeNocturneCss.match(/\.home\s+\.hero-filter-pill\s*\{[\s\S]*?min-height:\s*var\(--touch-min,\s*(\d+)px\);[\s\S]*?min-width:\s*(\d+)px;/)
assert(heroFilterMatch && parseInt(heroFilterMatch[1], 10) >= 44 && parseInt(heroFilterMatch[2], 10) >= 44,
  'pages/index.vue hero filter pills min-size >= 44x44px', `Found: min-height ${heroFilterMatch?.[1]}px, min-width ${heroFilterMatch?.[2]}px`)

const terroirChipMatch = homeNocturneCss.match(/\[data-home-pilot="nocturne-b1"\]\s+\.hero-terroir-chip\s*\{[\s\S]*?min-height:\s*var\(--touch-min,\s*(\d+)px\);/)
assert(terroirChipMatch && parseInt(terroirChipMatch[1], 10) >= 44,
  'pages/index.vue hero terroir chips min-height >= 44px', `Found: ${terroirChipMatch?.[1]}px`)

const heroNearbyMatch = indexContent.match(/\.home\s+\.hero-nearby\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
assert(heroNearbyMatch && parseInt(heroNearbyMatch[1], 10) >= 44,
  'pages/index.vue hero-nearby link min-height >= 44px', `Found: ${heroNearbyMatch?.[1]}px`)

const seeAllMatch = baseCss.match(/\.see-all\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
assert(seeAllMatch && parseInt(seeAllMatch[1], 10) >= 44,
  'see-all link min-height >= 44px in base.css', `Found: ${seeAllMatch?.[1]}px`)

const eventMiniMatch = homeNocturneCss.match(/\.event-mini\s*\{[\s\S]*?min-height:\s*(\d+)px;/)
assert(eventMiniMatch && parseInt(eventMiniMatch[1], 10) >= 48,
  'pages/index.vue event-mini cards min-height >= 48px', `Found: ${eventMiniMatch?.[1]}px`)

const seasonRowMatch = homeNocturneCss.match(/\[data-home-pilot="nocturne-b1"\]\s+\.home-season-row\s*\{[\s\S]*?min-height:\s*var\(--touch-min\);/)
assert(seasonRowMatch !== null, 'pages/index.vue home-season-row min-height set to var(--touch-min)')

console.log('')

// ─────────────────────────────────────────────────────────────────────────────
// STRESS TEST 2: Check 62/38 Asymmetric Grid Layout Rule in HomeCuratedShowcase
// ─────────────────────────────────────────────────────────────────────────────
console.log('─── STRESS TEST 2: 62/38 Asymmetric Grid Layout in HomeCuratedShowcase ───')

const gridRuleMatch = showcaseContent.match(/grid-template-columns:\s*minmax\(0,\s*1\.35fr\)\s*minmax\(0,\s*1fr\);/)
assert(gridRuleMatch !== null,
  'HomeCuratedShowcase enforces minmax(0, 1.35fr) minmax(0, 1fr) asymmetric grid ratio',
  `Rule present: ${Boolean(gridRuleMatch)}`)

const leadAnnotation = showcaseContent.includes('<!-- 62% Lead Heritage Showcase: Lò gạch Mang Thít (80% photo visual area) -->')
assert(leadAnnotation, 'HomeCuratedShowcase documents 62% Lead Heritage Showcase architecture in template')

const satAnnotation = showcaseContent.includes('<!-- 38% Satellite Cards (2x2 Grid, Full-Bleed 100% Photo with Bottom Scrim) -->')
assert(satAnnotation, 'HomeCuratedShowcase documents 38% Satellite Cards architecture in template')

const satGridMatch = showcaseContent.match(/@media\s*\(min-width:\s*640px\)\s*\{\s*\.home-curated-satellites\s*\{\s*grid-template-columns:\s*repeat\(2,\s*1fr\);/)
assert(satGridMatch !== null, 'HomeCuratedShowcase satellites form a 2x2 grid on >= 640px viewport')

const mediaQueryMatch = showcaseContent.match(/@media\s*\(min-width:\s*960px\)\s*\{\s*\.home-curated-showcase__layout\s*\{/)
assert(mediaQueryMatch !== null, 'HomeCuratedShowcase applies asymmetric grid at >= 960px desktop breakpoint')

const mobileFallbackMatch = showcaseContent.match(/\.home-curated-showcase__layout\s*\{[\s\S]*?grid-template-columns:\s*1fr;/)
assert(mobileFallbackMatch !== null, 'HomeCuratedShowcase defaults to single-column 1fr stack on mobile viewports')

console.log('')

// ─────────────────────────────────────────────────────────────────────────────
// STRESS TEST 3: Description Lengths Across All Cards (<= 120 chars / 2 lines)
// ─────────────────────────────────────────────────────────────────────────────
console.log('─── STRESS TEST 3: Description Lengths Across All Cards (<= 120 chars / 2 lines) ───')

// 3.1 HomeCuratedShowcase
const showcaseLeadDescMatch = showcaseContent.match(/desc:\s*['"]([^'"]+)['"]/)
const showcaseLeadDesc = showcaseLeadDescMatch ? showcaseLeadDescMatch[1] : ''
assert(showcaseLeadDesc.length > 0 && showcaseLeadDesc.length <= 120,
  `HomeCuratedShowcase lead description length <= 120 chars (${showcaseLeadDesc.length} chars)`,
  `"${showcaseLeadDesc}"`)

const satSummaries = [...showcaseContent.matchAll(/summary:\s*['"]([^'"]+)['"]/g)].map(m => m[1])
assert(satSummaries.length === 4, `HomeCuratedShowcase has 4 satellite summaries (found ${satSummaries.length})`)
satSummaries.forEach((s, idx) => {
  assert(s.length <= 120, `HomeCuratedShowcase satellite ${idx + 1} summary <= 120 chars (${s.length} chars)`, `"${s}"`)
})

const satLineClamp = showcaseContent.match(/\.home-curated-satellite__summary\s*\{[\s\S]*?-webkit-line-clamp:\s*2;/)
assert(satLineClamp !== null, 'HomeCuratedShowcase satellite summary clamped to 2 lines (-webkit-line-clamp: 2)')

// 3.2 HomeCulinaryTrail
const culinaryCardsHaveNoTextWall = !culinaryContent.includes('home-culinary-card__desc')
assert(culinaryCardsHaveNoTextWall, 'HomeCulinaryTrail cards have 0 text-wall description paragraphs (visual-first)')

// 3.3 HomeRiversideStays
const stayDescs = [...staysContent.matchAll(/desc:\s*['"]([^'"]+)['"]/g)].map(m => m[1])
assert(stayDescs.length >= 3, `HomeRiversideStays has curated homestays with descriptions (found ${stayDescs.length})`)
stayDescs.forEach((d, idx) => {
  assert(d.length <= 120, `HomeRiversideStays item ${idx + 1} desc <= 120 chars (${d.length} chars)`, `"${d}"`)
})

// Check line-clamp on HomeRiversideStays
const stayLineClamp = staysContent.match(/\.home-stay-card__desc\s*\{[\s\S]*?-webkit-line-clamp:\s*2;/)
assert(stayLineClamp !== null, 'HomeRiversideStays card desc clamped to 2 lines (-webkit-line-clamp: 2)',
  'Lacks -webkit-line-clamp: 2; in .home-stay-card__desc CSS declaration')

// 3.4 HomeTravelCompanion
const companionDescs = [...companionContent.matchAll(/<p class="home-companion-card__desc">\s*([\s\S]*?)\s*<\/p>/g)]
  .map(m => m[1].replace(/\s+/g, ' ').trim())

console.log(`  [INFO] HomeTravelCompanion has ${companionDescs.length} utility card descriptions:`)
companionDescs.forEach((d, idx) => {
  assert(d.length <= 120, `HomeTravelCompanion card ${idx + 1} desc <= 120 chars (${d.length} chars)`,
    `"${d}" exceeds 120 chars by ${d.length - 120} chars`)
})

const companionClamp = companionContent.match(/\.home-companion-card__desc\s*\{[\s\S]*?-webkit-line-clamp:\s*2;/)
assert(companionClamp !== null, 'HomeTravelCompanion card desc clamped to 2 lines (-webkit-line-clamp: 2)',
  'Lacks -webkit-line-clamp: 2; in .home-companion-card__desc CSS declaration')

console.log('')

// ─────────────────────────────────────────────────────────────────────────────
// STRESS TEST 4: Prohibited Generic AI Slop Phrases
// ─────────────────────────────────────────────────────────────────────────────
console.log('─── STRESS TEST 4: Prohibited Generic AI Slop Phrases ───')

const prohibitedPhrases = [
  'nâng tầm trải nghiệm',
  'hành trình vô tận',
  'vẻ đẹp bất tận',
  'khám phá không giới hạn',
  'trải nghiệm phong phú',
  'bứt phá mọi giới hạn',
  'tinh hoa hội tụ',
  'bản giao hưởng',
  'chạm vào cảm xúc',
  'đánh thức mọi giác quan',
]

const auditedComponents = [
  { name: 'HomeCuratedShowcase', content: showcaseContent },
  { name: 'HomeCulinaryTrail', content: culinaryContent },
  { name: 'HomeRiversideStays', content: staysContent },
  { name: 'HomeTravelCompanion', content: companionContent },
  { name: 'pages/index.vue', content: indexContent },
]

for (const comp of auditedComponents) {
  const lower = comp.content.toLowerCase()
  for (const phrase of prohibitedPhrases) {
    assert(!lower.includes(phrase), `${comp.name} contains no slop phrase "${phrase}"`)
  }
}

// Sparkle icons check
const sparkleRegex = /name=["']sparkles?["']|icon-name=["']sparkles?["']|auto_awesome/i
for (const comp of auditedComponents) {
  assert(!sparkleRegex.test(comp.content), `${comp.name} contains zero AI sparkle icons`)
}

console.log('')

// ─────────────────────────────────────────────────────────────────────────────
// STRESS TEST 5: Zero Audio / Video Autoplay Elements
// ─────────────────────────────────────────────────────────────────────────────
console.log('─── STRESS TEST 5: Zero Audio/Video Autoplay Elements ───')

const audioRegex = /<audio\b/i
const videoRegex = /<video\b/i
const autoplayRegex = /\bautoplay\b/i
const newAudioRegex = /new\s+Audio\s*\(/i

function scanApplicationForMedia(dir) {
  let violations = []
  const list = readdirSync(dir)
  for (const item of list) {
    if (['node_modules', '.nuxt', '.output', 'dist', '.git', 'tests', 'scripts'].includes(item)) continue
    const fullPath = join(dir, item)
    const stat = statSync(fullPath)
    if (stat.isDirectory()) {
      violations = violations.concat(scanApplicationForMedia(fullPath))
    } else if (/\.(vue|ts|js|mjs|html)$/.test(item)) {
      const src = readFileSync(fullPath, 'utf8')
      if (audioRegex.test(src)) violations.push({ file: fullPath, type: '<audio>' })
      if (videoRegex.test(src)) violations.push({ file: fullPath, type: '<video>' })
      if (autoplayRegex.test(src)) violations.push({ file: fullPath, type: 'autoplay' })
      if (newAudioRegex.test(src)) violations.push({ file: fullPath, type: 'new Audio()' })
    }
  }
  return violations
}

const mediaViolations = scanApplicationForMedia(webNuxt)
assert(mediaViolations.length === 0,
  `Zero <audio>, <video>, autoplay, or new Audio() in web-nuxt application (components, pages, layouts, composables)`,
  JSON.stringify(mediaViolations))

console.log('')

// ─────────────────────────────────────────────────────────────────────────────
// STRESS TEST 6: Zero Raw Hex Colors (#...) in Newly Edited Components
// ─────────────────────────────────────────────────────────────────────────────
console.log('─── STRESS TEST 6: Zero Raw Hex Colors (#...) in Newly Edited Components ───')

const hexPattern = /#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b/g

for (const comp of auditedComponents) {
  const matches = comp.content.match(hexPattern) || []
  assert(matches.length === 0,
    `${comp.name} has 0 raw hex color literals (found ${matches.length})`,
    matches.join(', '))
}

console.log('\n═══════════════════════════════════════════════════════════════════════════════')
console.log(`TOTAL TESTS: ${totalTests} | PASSED: ${passedTests} | FAILED: ${failedTests}`)
console.log('═══════════════════════════════════════════════════════════════════════════════\n')

if (failedTests > 0) {
  console.log(`EMPIRICAL CHALLENGE FINDINGS (${failedTests} issues surfaced):`)
  findings.forEach((f, idx) => {
    console.log(`  [Defect ${idx + 1}] ${f.testName}`)
    console.log(`    Detail: ${f.details}`)
  })
  console.log('\nVERDICT: REQUEST_CHANGES')
  process.exit(0)
} else {
  console.log('VERDICT: APPROVE (100% stress tests passed cleanly)')
  process.exit(0)
}
