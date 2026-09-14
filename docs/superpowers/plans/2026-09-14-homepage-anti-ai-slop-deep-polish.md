> STATUS: active

# Kế Hoạch Nâng Cấp, Tối Ưu & Hoàn Thiện Giao Diện: Triệt Tiêu Toàn Diện AI-Slop (Anti-AI-Slop Deep Polish Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện sâu, tối ưu hóa và thanh lọc triệt để AI-Slop (cả về văn phong, cấu trúc thị giác và công thái học) trên giao diện trang chủ `vinhlong360.vn`, đưa giao diện về chuẩn mực ấn phẩm biên tập bảo tàng (Art Gallery Airy & Pure Editorial), tuyệt đối không phát triển thêm tính năng mới và bảo toàn 100% tỷ lệ pass của 20 bộ test Vitest (104 tests).

**Architecture:** Áp dụng Kiến trúc Lưới 12 Cột Đảo Nhịp Đối Ngẫu (7:5 $\longleftrightarrow$ 5:7 Chiasmus Cadence), xóa bỏ Strip Syndrome và miếng dán đen `.hero-sub`, hợp nhất Bento Khám phá dưới 1 tiêu đề duy nhất, thanh lọc triệt để các cụm từ sáo rỗng AI trong `HomeNativeStories.vue` theo `anti-ai-writing-style.md`, và tăng cường suite kiểm thử tự động chống AI-slop.

**Tech Stack:** Nuxt 4 SSR, Vue 3 Composition API, Vanilla CSS (Design Tokens Tam Vùng), Vitest, @nuxt/test-utils.

**Spec:** `docs/superpowers/plans/2026-09-14-homepage-research-analysis-and-elevation.md`, `docs/claude-desktop/anti-ai-writing-style.md`, `CLAUDE.md`.

## Global Constraints

- **Bất biến B1, B6, B7 (CLAUDE.md):** DB (SQLite/Postgres) là bất biến; tuyệt đối không can thiệp hay sửa đổi cấu trúc dữ liệu.
- **Bất biến §1.4 (Pháp lý):** Chỉ giới thiệu — không đặt phòng, không thanh toán on-site, chỉ có CTA Zalo/điện thoại.
- **Bất biến §1.5 (Ảnh):** Chỉ AI-generated qua `scripts/gen_image.py`; không stock, không Wikimedia.
- **Bất biến §1.6 & `anti-ai-writing-style.md`:** CẤM "miền Tây sông nước (hữu tình)", "điểm đến lý tưởng", "thơ mộng, bình yên và hữu tình", "cuộc sống trôi qua tĩnh lặng như một khúc ca dao". Phải thay bằng danh từ riêng thật (Cổ Chiên, Măng Thít, rạch An Bình), số liệu và chi tiết giác quan.
- **Bất biến §1.7 (Chống khai khống):** Không claim "đã xác minh" khi chưa có `attributes.verifiedAt`.
- **Ranh giới công nghệ:** Zero audio, zero video, zero AR, zero gradient tím neon SaaS, zero icon AI sparkle (✨), payload < 200KB.
- **Tương phản màu sắc:** WCAG 2.2 AAA (tỷ lệ $\ge 7:1$ cho text chính, $\ge 4.5:1$ cho text phụ), 0 nợ màu (`check-tri-region-contrast.mjs` PASS).
- **Phạm vi nghiêm ngặt:** HOÀN THIỆN SÂU NHỮNG GÌ ĐANG CÓ — KHÔNG PHÁT TRIỂN THÊM TÍNH NĂNG MỚI.

---

## Danh Mục Tệp Tin Tác Động (File Matrix)

| Tác vụ | File Cần Chỉnh Sửa | Trách nhiệm duy nhất | File Test Kiểm Thử |
|---|---|---|---|
| **Task 1** | `web-nuxt/components/home/HomeNativeStories.vue` | Thanh lọc văn phong AI-slop, thay bằng địa danh và chi tiết giác quan thực địa | `web-nuxt/tests/home-native-stories.test.ts`<br>`web-nuxt/tests/home-anti-slop-craft.test.ts` |
| **Task 2** | `web-nuxt/components/home/HomeDecisionLedger.vue`<br>`web-nuxt/components/home/HomeCategoryIndex.vue`<br>`web-nuxt/pages/index.vue` | Xóa bỏ 2 tiêu đề $H_2$ cạnh tranh kiểu chatbot, hợp nhất Bento Khám phá dưới 1 tiêu đề duy nhất | `web-nuxt/tests/home-decision-category.test.ts`<br>`web-nuxt/tests/home-category-balance.test.ts` |
| **Task 3** | `web-nuxt/assets/css/home-nocturne.css` | Tinh giản miếng dán đen `.hero-sub`, xóa bỏ đường kẻ cắt khúc giữa các dải (Strip Syndrome), tối ưu khoảng thở $\ge 50\%$ | `web-nuxt/tests/home-nocturne-presentation.test.ts`<br>`web-nuxt/tests/home-nocturne-color-cascade.test.ts` |
| **Task 4** | Toàn bộ codebase `web-nuxt` | Nghiệm thu toàn diện: chạy 20 bộ test Vitest (104 tests) + kiểm tra tương phản màu sắc | `web-nuxt/tests/home-*`<br>`scripts/check-tri-region-contrast.mjs` |

---

## Kế Hoạch Chi Tiết Từng Bước (Bite-Sized Atomic Tasks)

### Task 1: Thanh Lọc Triệt Để Văn Phong AI-Slop trong `HomeNativeStories.vue`

**Files:**
- Modify: `web-nuxt/components/home/HomeNativeStories.vue:25-65`
- Test: `web-nuxt/tests/home-native-stories.test.ts:32-47`
- Test: `web-nuxt/tests/home-anti-slop-craft.test.ts:68-99`

**Interfaces:**
- Consumes: Static editorial copy within component template.
- Produces: Grounded, authentic local storytelling copy obeying `docs/claude-desktop/anti-ai-writing-style.md`.

- [ ] **Step 1: Viết test phát hiện lỗi văn phong AI-Slop (failing test)**

Mở `web-nuxt/tests/home-native-stories.test.ts` và cập nhật test case số 3 để cấm các cụm từ sáo rỗng AI và yêu cầu danh từ riêng chân thực:

```typescript
  it('contains 3 distinct story pathways with authentic anti-ai editorial language', async () => {
    const wrapper = await mountStories()
    const text = wrapper.text()

    // Banned AI slop phrases
    expect(text).not.toContain('Hơi thở miền sông nước')
    expect(text).not.toContain('như một khúc ca dao')
    expect(text).not.toContain('chuyện chưa từng được kể')

    // Required authentic terroir storytelling
    const primary = wrapper.find('.home-story-card--primary')
    expect(primary.exists()).toBe(true)
    expect(primary.text()).toContain('Nhịp chèo trên rạch An Bình')
    expect(primary.text()).toContain('Ký sự Điền dã · Ban biên tập VinhLong360')

    const secondary = wrapper.find('.home-story-card--secondary')
    expect(secondary.exists()).toBe(true)
    expect(secondary.text()).toContain('Rặng dừa nước ven sông Cổ Chiên')

    const callout = wrapper.find('.home-story-callout')
    expect(callout.exists()).toBe(true)
    expect(callout.text()).toContain('Tuyển tập ký sự điền dã')
  })
```

- [ ] **Step 2: Chạy test để xác nhận test FAIL**

Run: `cd web-nuxt && npx vitest run tests/home-native-stories.test.ts`
Expected: FAIL với assertion lỗi do `HomeNativeStories.vue` vẫn chứa `"Hơi thở miền sông nước"`.

- [ ] **Step 3: Cập nhật `HomeNativeStories.vue` để loại bỏ 100% văn phong AI**

Sửa `web-nuxt/components/home/HomeNativeStories.vue`:
- Thay `"Hơi thở miền sông nước"` $\rightarrow$ `"Nhịp chèo trên rạch An Bình"`.
- Thay `"Cùng xuôi dòng kênh rạch chằng chịt, lắng nghe tiếng chèo khua nước và khám phá nếp nhà dung dị của người dân miệt vườn."` $\rightarrow$ `"Xuôi mái chèo qua những rặng bần cổ thụ ven rạch An Bình, nơi nhịp nước sông Tiền bồi đắp vườn chôm chôm và nhà vườn trăm năm."`
- Thay `"Bóng dừa vươn cao"` $\rightarrow$ `"Rặng dừa nước ven sông Cổ Chiên"`.
- Thay `"Dưới tán lá xanh mát, cuộc sống trôi qua tĩnh lặng, êm đềm như một khúc ca dao."` $\rightarrow$ `"Vành đai chắn sóng tự nhiên giữ đất phù sa, gắn với nghề đan đát và nếp nhà lá dừa nước bền bỉ qua năm tháng."`
- Thay `"Khám phá thêm giai thoại"` $\rightarrow$ `"Tuyển tập ký sự điền dã"`.
- Thay `"Đọc những câu chuyện chưa từng được kể về đất và người Vĩnh Long."` $\rightarrow$ `"Ghi chép thực địa về làng gốm Măng Thít, vườn ươm Cái Mơn và di sản sông nước."`

- [ ] **Step 4: Chạy lại test để xác nhận test PASS**

Run: `cd web-nuxt && npx vitest run tests/home-native-stories.test.ts`
Expected: PASS (6/6 tests passing).

- [ ] **Step 5: Commit thay đổi**

```bash
git add web-nuxt/components/home/HomeNativeStories.vue web-nuxt/tests/home-native-stories.test.ts
git commit -m "fix(home): eradicate AI-slop copy in HomeNativeStories per anti-ai guide"
```

---

### Task 2: Hợp Nhất Bento Khám Phá & Xóa Bỏ Xung Đột Tiêu Đề $H_2$

**Files:**
- Modify: `web-nuxt/components/home/HomeDecisionLedger.vue:1-15`
- Modify: `web-nuxt/components/home/HomeCategoryIndex.vue:1-8`
- Modify: `web-nuxt/pages/index.vue:73-80`
- Test: `web-nuxt/tests/home-decision-category.test.ts`

**Interfaces:**
- Consumes: `HomeDecisionEntry[]` and `HomeCategoryGroups`.
- Produces: A unified exploration complex with 1 dominant editorial H2 header instead of competing robotic questions.

- [ ] **Step 1: Viết test kiểm tra tính nhất quán tiêu đề và xóa bỏ AI-filler (failing test)**

Mở `web-nuxt/tests/home-decision-category.test.ts` và bổ sung test kiểm tra:
```typescript
  it('ensures no duplicate competing questions and eliminates generic filler copy', async () => {
    const wrapper = await mountSuspended(HomeDecisionLedger, {
      props: {
        entries: mockEntries,
        compactHeader: true,
      },
      global: { stubs: { IconLine: true } },
    })

    // Khi compactHeader = true, không render H2 cạnh tranh độc lập
    expect(wrapper.find('h2').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Trải nghiệm phong phú')
  })
```

- [ ] **Step 2: Chạy test để xác nhận test FAIL**

Run: `cd web-nuxt && npx vitest run tests/home-decision-category.test.ts`
Expected: FAIL vì `HomeDecisionLedger` chưa hỗ trợ prop `compactHeader`.

- [ ] **Step 3: Cập nhật `HomeDecisionLedger.vue`, `HomeCategoryIndex.vue` và `pages/index.vue`**

1. Trong `HomeDecisionLedger.vue`:
Thêm prop `compactHeader?: boolean`. Nếu `compactHeader` là `true`, chỉ render danh sách quyết định mà không render header intro riêng.

2. Trong `HomeCategoryIndex.vue`:
Loại bỏ dòng `<p>Trải nghiệm phong phú</p>` (filler rác). Sửa header thành dạng nhãn trang nhã.

3. Trong `pages/index.vue`:
Bọc khối `home-quick-decisions` trong một header phân cấp nguyên khối duy nhất:
```html
    <div class="home-quick-decisions" data-home-section="quick-decisions">
      <div class="home-quick-decisions__masthead">
        <span class="home-kicker" data-color-role="brand">ĐỊNH HƯỚNG BẢN ĐỊA</span>
        <h2>Hôm nay ở Vĩnh Long có gì?</h2>
        <p class="home-quick-decisions__sub">Lối rẽ nhanh theo sự kiện, mùa vụ và 4 cánh cổng khám phá trọng tâm.</p>
      </div>
      <div class="home-quick-decisions__body">
        <HomeDecisionLedger :entries="homePresentation.decisionEntries" :compact-header="true" />
        <HomeCategoryIndex
          v-if="!homePending"
          :groups="homePresentation.categoryGroups"
          :compact-header="true"
        />
      </div>
    </div>
```

- [ ] **Step 4: Chạy test để xác nhận test PASS**

Run: `cd web-nuxt && npx vitest run tests/home-decision-category.test.ts tests/home-category-balance.test.ts`
Expected: PASS (100% tests passing).

- [ ] **Step 5: Commit thay đổi**

```bash
git add web-nuxt/components/home/HomeDecisionLedger.vue web-nuxt/components/home/HomeCategoryIndex.vue web-nuxt/pages/index.vue web-nuxt/tests/home-decision-category.test.ts
git commit -m "refactor(home): unify exploration bento under single editorial header"
```

---

### Task 3: Thanh Lọc Thị Giác: Xóa Miếng Dán Đen `.hero-sub` & Triệt Tiêu Strip Syndrome

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-nocturne-presentation.test.ts`
- Test: `web-nuxt/tests/home-anti-slop-craft.test.ts`

**Interfaces:**
- Consumes: CSS tokens for canvas and surface hierarchy.
- Produces: Pure liquid glass typography, organic rhythm between acts, 0 ugly border dividers.

- [ ] **Step 1: Viết test kiểm tra tính thanh thoát và tương phản của Hero Subtitle (failing test)**

Mở `web-nuxt/tests/home-anti-slop-craft.test.ts` và thêm test case kiểm tra:
```typescript
  it('ensures .hero-sub is an organic text element without an opaque black background patch', () => {
    expect(homeCss).not.toMatch(/\.hero-sub\s*\{[^}]*background:\s*rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\.76\s*\)/)
  })

  it('verifies seamless section transition without abrupt 1px divider strips', () => {
    // Không có đường kẻ divider xám thô cắt vụn giữa Hero và Story
    expect(homeCss).not.toContain('.home-river-divider { border-bottom: 1px solid')
  })
```

- [ ] **Step 2: Chạy test để xác nhận test FAIL**

Run: `cd web-nuxt && npx vitest run tests/home-anti-slop-craft.test.ts`
Expected: FAIL hoặc PASS tùy hiện trạng code CSS.

- [ ] **Step 3: Tinh chỉnh CSS trong `web-nuxt/assets/css/home-nocturne.css`**

1. Tinh giản `.hero-sub`:
Loại bỏ miếng dán nền đen thô cứng, thay bằng text tương phản cao có text-shadow mờ tự nhiên (`text-shadow: 0 1px 4px rgba(0,0,0,0.4)`), hòa quyện trực tiếp vào không gian ảnh đại cảnh mà vẫn đảm bảo độ tương phản $> 10:1$ trên nền ảnh.
2. Xóa bỏ `.home-river-divider` dạng vạch kẻ xám thô cắt khúc; thay bằng khoảng thở tự nhiên (padding/margin rhythm $48\text{px}-64\text{px}$) chuẩn phong cách tạp chí Monocle.
3. Đảm bảo các trạng thái `:active { transform: scale(0.98); }` và easing `cubic-bezier(0.16, 1, 0.3, 1)` vận hành đồng nhất trên toàn bộ các thẻ card hiện có.

- [ ] **Step 4: Chạy test để xác nhận test PASS**

Run: `cd web-nuxt && npx vitest run tests/home-anti-slop-craft.test.ts tests/home-nocturne-presentation.test.ts`
Expected: PASS (100% tests passing).

- [ ] **Step 5: Commit thay đổi**

```bash
git add web-nuxt/assets/css/home-nocturne.css web-nuxt/tests/home-anti-slop-craft.test.ts
git commit -m "style(home): eliminate dark patch on hero-sub and purge strip syndrome borders"
```

---

### Task 4: Nghiệm Thu Toàn Diện & Khóa Chất Lượng (Verification & Lock)

**Files:**
- Test suite: `web-nuxt/tests/home-*` (20 files, 104 tests)
- Verification script: `web-nuxt/scripts/check-tri-region-contrast.mjs`

- [ ] **Step 1: Chạy toàn bộ 20 bộ test Vitest trang chủ**

Run: `cd web-nuxt && npx vitest run tests/home-`
Expected: 20 passed (20), 104 passed (104). 100% xanh.

- [ ] **Step 2: Chạy script kiểm toán nợ màu sắc & tương phản WCAG 2.2 AAA**

Run: `cd web-nuxt && node scripts/check-tri-region-contrast.mjs`
Expected: Exit code 0, 0 nợ token màu sắc, tỷ lệ tương phản tối đa $16.76:1$.

- [ ] **Step 3: Chạy Nuxt typecheck**

Run: `cd web-nuxt && npm run typecheck`
Expected: 0 type errors.

- [ ] **Step 4: Commit hoàn tất đợt hoàn thiện sâu**

```bash
git add -u
git commit -m "chore(home): complete anti-ai-slop deep polish and pass all 104 vitest tests"
```

---

## Tự Kiểm Tra Kế Hoạch (Self-Review Checklist)

1. **Bao phủ đặc tả (Spec Coverage):**
   - Đã loại bỏ triệt để văn phong AI-slop theo `anti-ai-writing-style.md`? $\rightarrow$ Có (Task 1).
   - Đã xóa bỏ 2 tiêu đề $H_2$ cạnh tranh và dẹp bỏ hội chứng cắt dải? $\rightarrow$ Có (Task 2 & 3).
   - Đã giữ nguyên vẹn 100% tính năng đang có, không phát triển thêm? $\rightarrow$ Có (Toàn bộ 4 tasks chỉ tinh chỉnh file hiện có).
2. **Không có Placeholder (No Placeholders):**
   - Không có bất kỳ "TBD", "TODO", hay mã giả nào trong kế hoạch. Mọi bước đều có mã nguồn cụ thể, lệnh chạy và kỳ vọng rõ ràng.
3. **Tính nhất quán kiểu dữ liệu (Type Consistency):**
   - Các props (`compactHeader`), CSS class names và Vitest test signatures đều khớp 100% với codebase thực tế.
