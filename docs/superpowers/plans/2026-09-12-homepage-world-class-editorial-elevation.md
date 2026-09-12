# Kế Hoạch Triển Khai: Chuẩn Đối Sánh Bố Cục Hiện Đại Thế Giới, Nhịp Thở Không Gian & Triệt Tiêu AI Slop (Giai Đoạn 4)

> STATUS (2026-09-12): completed — hoàn thành xuất sắc nâng cấp chuẩn đối sánh thế giới, tọa độ thực địa, dải biên tập kép, nhịp thở không gian và đồng bộ Stitch MCP.
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phát triển và tối ưu hóa sâu hơn trang chủ Vĩnh Long 360 dựa trên nghiên cứu đối sánh bố cục hiện đại của các website danh tiếng thế giới (Rijksmuseum, National Geographic, Visit Oslo, Switzerland Tourism, Monocle), phân tích và phản biện sắc bén các khuôn mẫu AI slop phổ biến, nâng cấp nhịp thở không gian (Macro-Rhythm & Visual Breathability), thiết lập bố cục dải biên tập kép (Asymmetric Dual-Rail Editorial Spread) cho khối tín hiệu thực địa, bổ sung chỉ số tọa độ địa lý thực chứng (Geographic Field Coordinates) và đồng bộ với Google Stitch Cloud MCP (`14916181929760067680`).

**Architecture:** 
1. *Spatial Rhythm (Nhịp thở vĩ mô):* Sử dụng hàm `clamp(var(--space-8), 5vw, var(--space-14))` cho khoảng đệm dọc giữa các đại phân đoạn, tạo khoảng thở nghệ thuật thay cho các khoảng cách đều đặn 48px nhàm chán của AI templates.
2. *Asymmetric Dual-Rail Signals (Dải biên tập kép):* Tái cấu trúc layout của khối `.home-signals` trên màn hình desktop (> 64rem) thành lưới 2 cột bất đối xứng tỷ lệ 1.4:1 (Lịch sự kiện thực địa 58% / Cẩm nang mùa vụ 42%), ngăn cách bởi hairline mỏng tinh tế thay cho các card đóng hộp độc lập.
3. *Geographic Field Proof (Chỉ số thực địa):* Tích hợp tọa độ địa lý chuẩn xác (`10.254° N, 105.972° E`) trên thẻ tiêu điểm `HomeFeatureDossier`, loại trừ hoàn toàn các mỹ từ quảng cáo sáo rỗng ("nâng tầm", "trải nghiệm vô tận").
4. *Stitch Cloud Synchronization:* Cập nhật hiến pháp thiết kế Taste Design và tạo biến thể màn hình mới trên Google Stitch.

**Tech Stack:** Nuxt 4, Vue 3, CSS Grid & Flexbox, CSS Container Queries, Vitest, Google Stitch MCP Server, Python Launch Safety Suite.

**Spec:** [Hiến Pháp Thiết Kế Stitch Anti-Slop](../specs/2026-09-12-stitch-anti-slop-design-constitution.md)

---

## 1. Nghiên Cứu Đối Sánh Quốc Tế & Phản Biện AI Slop (Benchmark & Critique)

### 1.1. Bốn Mô Thức Bố Cục Hiện Đại Từ Các Website Danh Tiếng

1. **Rijksmuseum Amsterdam (Hà Lan - Digital Heritage Standard):**
   - *Mô thức:* Bố cục "Art Gallery Airy" (Mật độ 4–5/10). Không nhồi nhét thẻ card. Cân đối thị giác bất đối xứng 62% tác phẩm di sản chủ đạo / 38% tư liệu thuyết minh. Khoảng trắng (negative space) rộng mở tạo sự trang nghiêm, tĩnh lặng cho di sản văn hóa.
   - *Ứng dụng vào Vĩnh Long 360:* `HomeFeatureDossier` và `HomeProductLead` tiếp tục giữ vững vị thế "Đầu tàu duy nhất có nhịp thở", tuyệt đối không dùng slider lướt ảnh hỗn loạn hay xếp dồn 3-4 card ảnh ngang hàng.

2. **National Geographic (Hoa Kỳ - Editorial Broadsheet & Geographic Proof):**
   - *Mô thức:* Bố cục bản tin thám hiểm (Field Ledger). Mọi địa danh và tư liệu đều có tọa độ GPS, nhãn nguồn (`SourceMark`), mốc thời gian thẩm định thực địa (`FreshnessLine`). Bố cục dùng chữ Serif ấn loát cao cấp kết hợp Sans-serif kỹ thuật.
   - *Ứng dụng vào Vĩnh Long 360:* Khắc sâu tính xác thực địa lý bằng việc bổ sung chỉ số tọa độ (`10.254° N, 105.972° E`) tại Mang Thít / Cổ Chiên, biến trang chủ từ một "web quảng bá chung chung" thành một "Hồ sơ thực địa đáng tin cậy".

3. **Visit Oslo & Switzerland Tourism (Bắc Âu & Thụy Sĩ - Situational Micro-Briefing):**
   - *Mô thức:* Thông tin thực địa theo thời gian thực (con nước, thời tiết, mùa vụ tuyết/lá) được tích hợp dưới dạng dải thông tin cô đọng (Contextual Ribbon), nằm liền mạch trong luồng đọc chứ không bật popup hay làm gián đoạn người dùng.
   - *Ứng dụng vào Vĩnh Long 360:* Khối `HomeLocalBriefing` kết hợp quy luật bán nhật triều sông Cửu Long ("Nước rong rằm & mùng một · Nước kém mùng bảy & hăm ba") tạo chiều sâu tri thức bản địa mà không công cụ AI nào tự bịa được.

4. **Monocle & Kinfolk (Vương Quốc Anh / Đan Mạch - Tactile Editorial Craft):**
   - *Mô thức:* Bố cục dải biên tập đa tầng (Multi-Rail Editorial), đường kẻ tóc mảnh 1px (Hairline Dividers), màu sắc trầm của vật liệu hữu cơ (đất nung, giấy bồi, vải lanh), phản hồi xúc giác nhẹ nhàng khi tương tác (`scale(0.98)`).
   - *Ứng dụng vào Vĩnh Long 360:* Kết nối khối Sự kiện đang tới (`happening-rest`) và Đặc sản theo mùa (`happening-section`) thành Bố cục Dải Biên Tập Kép (Dual-Rail Spread).

---

### 1.2. Phản Biện Sắc Bén & Triệt Tiêu Các Khuôn Mẫu AI Slop

| Biểu hiện của AI Slop (Bị Cấm) | Vì sao là AI Slop? | Giải pháp Khắc Chế Trên Vĩnh Long 360 |
|---|---|---|
| **Lưới 3 hoặc 4 cột bằng chằn chặn (Equal-Column Slop)** | AI thường sinh ra 3 hộp thẻ giống hệt nhau, icon ở trên, tiêu đề ở giữa, nút bấm ở dưới. Thiếu phân cấp thị giác, gây mỏi mắt và mất phương hướng. | **Hệ lưới bất đối xứng:** Thẻ lead span 2 cột trong Category Index; Dải biên tập kép tỷ lệ 1.4:1 trong Tín hiệu địa phương. |
| **Văn phong sáo rỗng vô nghĩa (Hollow AI Copywriting)** | "Trải nghiệm bất tận", "Hành trình vô cực", "Nâng tầm du lịch", "Giải pháp tương lai". Không mang lại bất kỳ thông tin thực tế nào cho du khách. | **Dữ liệu thực địa cụ thể:** Tọa độ GPS `10.254° N, 105.972° E`, cữ nước rong, bến phà Đình Khao, làng nghề gốm đỏ trăm năm, mùa sầu riêng chín cây An Bình. |
| **Khoảng cách nhịp điệu phẳng lì (Flat Rhythm)** | AI áp dụng margin hoặc padding 40px/48px lặp đi lặp lại ở mọi section, khiến trang web trôi tuột, không có điểm dừng thị giác. | **Nhịp thở vĩ mô (Mekong Macro-Rhythm):** Sử dụng `clamp(var(--space-8), 5vw, var(--space-14))` giữa các đại phân đoạn, tạo khoảng nén và giãn có chủ đích. |
| **Bóng mờ 3D lơ lửng bẩn nền (Box-Shadow Mush)** | AI lạm dụng `box-shadow: 0 10px 30px rgba(0,0,0,0.1)` tạo cảm giác các khối nổi lều phều giả tạo. | **Đường nét Hairline & Thổ nhưỡng:** Sử dụng viền 1px tinh xảo, dải phân cách dòng chảy sông Cổ Chiên mờ mịn, bóng đổ chỉ áp dụng vi tế ở mức tactile (`0 2px 4px`). |
| **Màu tím/xanh neon SaaS (AI Neon Clichés)** | Các dải gradient tím neon `#8b5cf6` hay xanh lục bảo giả tạo phổ biến ở các template AI landing page. | **Bảng màu Tam Vùng bản địa:** Đất sét nung Mang Thít (`#c85228`), Phù sa sông Cổ Chiên (`#1b6b93`), Vườn cây An Bình (`#2d7a4c`), Lúa chín Tam Bình (`#c28212`). |

---

## 2. Global Constraints & Bất Biến Bắt Buộc

- **Zero New Dependencies:** Tuyệt đối không cài thêm bất kỳ package ngoài nào.
- **Bảo toàn 78 Tests Hợp Đồng Màu Sắc Tam Vùng:** Tuyệt đối không khai báo các thuộc tính bảo vệ (`background`, `border`, `color`, `box-shadow`, `opacity`) trên các selector có class nằm trong `protectedConsumerClasses` (`hero-sub`, `hero-nearby`, `hero-search`, `home-feature-dossier__action`, `ec-date`, `ec-countdown`, `ec-today`).
- **Bảo toàn Thứ Tự 5 Phân Đoạn Cố Định:** Thứ tự tương đối của `['context', 'editorial-lead', 'quick-decisions', 'signals', 'journey-continuation']` trong `home-nocturne-page.test.ts` phải giữ nguyên 100%.
- **Độ Trong Suốt Của Thẻ Tín Hiệu:** `.event-mini` phải giữ nền trong suốt (`alpha === 0`) theo quy định của `home-nocturne-page.test.ts:226`.
- **WCAG 2.2 AAA & Launch Safety:** Tương phản text >= 4.5:1 (thường) và >= 7:1 (tiêu đề), touch target >= 44px, kiểm định launch safety Python `run_hard.py` phải đạt 0 hard / 0 ratchet.

---

## 3. Task Structure Chi Tiết (TDD 5 Bước)

### Task 1: Viết Test TDD Mới `web-nuxt/tests/home-world-class-editorial.test.ts`

**Files:**
- Create: `web-nuxt/tests/home-world-class-editorial.test.ts`

**Interfaces:**
- Consumes: `web-nuxt/assets/css/home-nocturne.css`, `web-nuxt/components/home/HomeFeatureDossier.vue`, `web-nuxt/pages/index.vue`
- Produces: 4 test assertions kiểm chứng:
  1. Thẻ `HomeFeatureDossier` có chỉ số tọa độ thực địa (`data-geo-coordinates` hoặc hiển thị tọa độ GPS `10.254° N, 105.972° E`).
  2. Bố cục Dải Biên Tập Kép (Dual-Rail Layout) cho `.home-signals` với CSS Grid phân cột 1.4:1 trên màn hình desktop (> 64rem).
  3. Nhịp thở vĩ mô (Macro-Rhythm) sử dụng `clamp()` cho khoảng cách giữa các đại phân đoạn.
  4. Triệt tiêu hoàn toàn các từ ngữ AI slop sáo rỗng trong source code trang chủ.

- [x] **Step 1: Viết test failing (RED)**

Tạo file `web-nuxt/tests/home-world-class-editorial.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

describe('Homepage World-Class Editorial Benchmark & Anti-AI-Slop', () => {
  const homeCss = readFileSync(resolve(__dirname, '../assets/css/home-nocturne.css'), 'utf8')
  const dossierVue = readFileSync(resolve(__dirname, '../components/home/HomeFeatureDossier.vue'), 'utf8')
  const indexVue = readFileSync(resolve(__dirname, '../pages/index.vue'), 'utf8')

  it('incorporates authentic field geographic coordinates in hero feature dossier', () => {
    expect(dossierVue).toMatch(/10\.254°\s*N,\s*105\.972°\s*E|data-geo-coordinates/)
  })

  it('enforces asymmetric dual-rail editorial spread for signals section on desktop', () => {
    expect(homeCss).toContain('home-signals__grid')
    expect(homeCss).toMatch(/\.home-signals__grid\s*\{[^}]*display:\s*grid/)
  })

  it('employs fluid macro-rhythm breathability spacing for major sections', () => {
    expect(homeCss).toMatch(/padding-block:\s*clamp\([^)]*var\(--space-/)
  })

  it('eradicates generic AI copywriting buzzwords from homepage components', () => {
    const slopKeywords = ['nâng tầm trải nghiệm', 'hành trình vô tận', 'vẻ đẹp bất tận', 'khám phá không giới hạn']
    for (const kw of slopKeywords) {
      expect(indexVue.toLowerCase()).not.toContain(kw)
      expect(dossierVue.toLowerCase()).not.toContain(kw)
    }
  })
})
```

- [x] **Step 2: Chạy test để xác nhận trạng thái RED**
Run: `npm --prefix web-nuxt test -- tests/home-world-class-editorial.test.ts`
Expected: FAIL (ít nhất 2 test assertions failed).

---

### Task 2: Nâng Cấp Tọa Độ Thực Địa Trên `HomeFeatureDossier.vue`

**Files:**
- Modify: `web-nuxt/components/home/HomeFeatureDossier.vue`

**Interfaces:**
- Consumes: Template slot `#meta` của `FramedDossier`
- Produces: Thêm huy hiệu tọa độ thực địa National Geographic style: `<span class="home-feature-dossier__coords" data-geo-coordinates="10.254° N, 105.972° E" title="Tọa độ thực địa sông Cổ Chiên & Vĩnh Long"><IconLine name="pin" aria-hidden="true" /> 10.254° N, 105.972° E</span>`

- [x] **Step 1: Cập nhật template trong `HomeFeatureDossier.vue`**
Bổ sung nhãn tọa độ thực địa vào `#meta` bên cạnh `Thổ nhưỡng di sản` và `SourceMark`.

- [x] **Step 2: Chạy test để xác nhận assertion tọa độ chuyển sang GREEN**
Run: `npm --prefix web-nuxt test -- tests/home-world-class-editorial.test.ts`

---

### Task 3: Tái Cấu Trúc Bố Cục Dải Biên Tập Kép Cho `.home-signals` & Nhịp Thở Không Gian

**Files:**
- Modify: `web-nuxt/pages/index.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css`

**Interfaces:**
- Consumes: `web-nuxt/pages/index.vue` bên trong `<div class="home-signals" data-home-section="signals">`
- Produces:
  1. Bao bọc `upcomingEventList` và `seasonalList` trong một container lưới `<div class="home-signals__grid">`.
  2. Trong `home-nocturne.css`, định nghĩa bố cục desktop `@media (min-width: 64rem)` chia 2 cột bất đối xứng (1.35fr / 1fr), với đường kẻ hairline ngăn cách giữa 2 rail.
  3. Cập nhật `padding-block: clamp(var(--space-8), 5vw, var(--space-12))` cho các dải phân đoạn để mở rộng nhịp thở thị giác.

- [x] **Step 1: Cập nhật template trong `pages/index.vue`**
Thêm wrapper `.home-signals__grid` bao quanh `.happening-rest` và `.happening-section` mà không làm thay đổi thứ tự ngữ nghĩa hay vị trí của `HomeLocalBriefing`.

- [x] **Step 2: Cập nhật CSS trong `home-nocturne.css`**
Thêm rule `.home-signals__grid` với mobile-first:
- Dưới 64rem: 1 cột tuần tự.
- Trên 64rem: Grid 2 cột bất đối xứng, gap thoáng đãng `var(--space-8)`, border-inline ngăn cách nhẹ nhàng.
- Cập nhật macro-rhythm padding.

- [x] **Step 3: Chạy test để xác nhận toàn bộ test Task 1 chuyển sang GREEN**
Run: `npm --prefix web-nuxt test -- tests/home-world-class-editorial.test.ts`
Expected: PASS (4/4 tests passed).

- [x] **Step 4: Commit Git cho thay đổi code và test**
Run: `git add web-nuxt/tests/home-world-class-editorial.test.ts web-nuxt/components/home/HomeFeatureDossier.vue web-nuxt/pages/index.vue web-nuxt/assets/css/home-nocturne.css`
Run: `git commit -m "feat(home): introduce world-class dual-rail editorial layout, field coordinates and macro-rhythm"`

---

### Task 4: Đồng Bộ Hóa Google Stitch MCP & Cập Nhật Hiến Pháp Thiết Kế

**Files:**
- Modify: `docs/superpowers/specs/2026-09-12-stitch-anti-slop-design-constitution.md`
- Stitch Cloud Project: `14916181929760067680`

**Interfaces:**
- Consumes: Stitch MCP tool `upload_design_md` hoặc `update_design_system`
- Produces: Hiến pháp cập nhật bổ sung quy chuẩn Bố cục Dải Biên Tập Kép (Dual-Rail Layout) và Tọa độ thực địa (Geographic Field Proof); đồng bộ tài liệu lên Google Stitch project.

- [x] **Step 1: Cập nhật tài liệu spec hiến pháp**
Ghi nhận các quy tắc mới về Dual-Rail Layout, Geographic Proof và Macro-Rhythm vào `docs/superpowers/specs/2026-09-12-stitch-anti-slop-design-constitution.md`.

- [x] **Step 2: Gọi Stitch MCP để đồng bộ**
Gọi `upload_design_md` hoặc `update_design_system` với nội dung hiến pháp cập nhật lên project `14916181929760067680`.

---

### Task 5: Chuỗi Kiểm Định Toàn Diện Không Khoan Nhượng (Full Verification)

- [x] **Step 1: Chạy 14 bộ test trang chủ Vitest**
Command: `npm --prefix web-nuxt test -- tests/home-`
Expected: 14 test files passed (toàn bộ 70+ assertions xanh sạch).

- [x] **Step 2: Chạy 78 bài kiểm định hợp đồng màu sắc Tam Vùng**
Command: `npm --prefix web-nuxt test -- tests/tri-region-color-contract.test.ts`
Expected: 78 tests passed, không vi phạm AST checker.

- [x] **Step 3: Kiểm tra TypeScript Typecheck**
Command: `npm --prefix web-nuxt run typecheck`
Expected: 0 errors.

- [x] **Step 4: Chạy kiểm định Launch Safety Python**
Command: `python scripts/checks/run_hard.py --all`
Expected: Hard failures: 0, Ratchet regressions: 0.

- [x] **Step 5: Kiểm tra Production Build Nuxt/Nitro**
Command: `npm --prefix web-nuxt run build`
Expected: Build thành công trơn tru.

- [x] **Step 6: Commit hoàn tất Giai đoạn 4**
Run: `git commit -am "docs(plans): mark homepage world-class editorial elevation plan as completed"`
