# Kế Hoạch Nghiên Cứu, Phản Biện & Tạo Màn Hình Trang Chủ Mới Trên Google Stitch

> STATUS: active
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thiết lập một bản thiết kế trang chủ duy nhất, hoàn mỹ, loại bỏ triệt để cả 3 căn bệnh của các phiên bản cũ (Bento SaaS công nghiệp, Bảng điều khiển viền răng cưa cồng kềnh 8.400px, và Phòng tranh tối giản rỗng tuếch); tạo ra một màn hình trang chủ độc bản "Kỳ Đài Sông Nước Nam Bộ" (Riverine Living Broadside) trên Google Stitch (`projects/14916181929760067680`).

**Architecture:** Sử dụng kiến trúc tạp chí văn hóa điền dã (Editorial Broadside) 4 phân đoạn chắt lọc với tỷ lệ vàng $4:6$, tích hợp hình ảnh phù sa sống động, độ dài tối ưu ($3.800\text{px} - 4.000\text{px}$), triệt tiêu hoàn toàn viền răng cưa và chi tiết rác, neo giữ trực tiếp vào mã nguồn `web-nuxt/pages/index.vue`.

**Tech Stack:** Google Stitch MCP (Gemini 2.5 Flash / HTML5 Canvas / Tailwind CSS / Vanilla CSS Tokens), Nuxt 3, Vitest, Tri-region CSS Palette.

**Spec:** `docs/superpowers/plans/2026-09-14-new-homepage-stitch-ground-truth.md`

## Global Constraints

- **Scope:** Tạo duy nhất 1 màn hình Desktop Masterpiece chuẩn trên Stitch (`projects/14916181929760067680`).
- **Chiều dài trang:** Không vượt quá $4.200\text{px}$ (loại bỏ bẫy quá tải 8.400px của bản cũ).
- **Hình thức:** Cấm hoàn toàn viền răng cưa bưu chính (perforated kitsch), cấm các khối bento đen dày đặc, cấm thanh công cụ buồng lái hàng hải dày đặc.
- **Văn phong:** Tuân thủ 100% `docs/claude-desktop/anti-ai-writing-style.md` (cấm "hơi thở miền sông nước", "như một khúc ca dao", v.v.).
- **Màu sắc:** Tuân thủ Tri-region contrast palette (Mang Thít Terracotta `#B95F38`, Cổ Chiên Deep Azure `#004E74`, Ấm phù sa `#FAF8F5`, Mực than `#181E28`).
- **Codebase Invariant:** Zero DB changes, Zero new external packages, 100% Vitest pass.

---

### Task 1: Nghiên cứu Thổ nhưỡng & Phản biện Đóng khung 5W1H2C5M

**Files:**
- Create: `docs/superpowers/specs/2026-09-14-homepage-riverine-broadside-spec.md`
- Test: None (Tài liệu kiến trúc đặc tả chuẩn bị cho việc sinh tạo Stitch)

**Interfaces:**
- Consumes: Báo cáo khảo sát thực địa Vĩnh Long, các chỉ trích về lỗi răng cưa và gánh nặng thị giác.
- Produces: Bản đặc tả thiết kế 4 phân đoạn vàng (Golden 4-Act Riverine Broadside Spec) làm prompt nguồn chuẩn mực cho Stitch.

- [ ] **Step 1: Viết tài liệu đặc tả thiết kế phản biện 5W1H2C5M**

Viết tài liệu `docs/superpowers/specs/2026-09-14-homepage-riverine-broadside-spec.md` mổ xẻ vì sao bản cũ thất bại và xác lập 4 phân đoạn:
1. *Masthead Điền Dã & Dòng Sông Khởi Điểm (The River Horizon Hero)*: Header thanh mảnh, thanh tìm kiếm hòa vào cảnh quan, 1 tiêu điểm duy nhất.
2. *Bộ Tứ Không Gian Văn Hóa (The Four Terroir Quadrants)*: Cù lao An Bình, Lò gạch Măng Thít, Trầm tích Khmer & Đình làng, Văn hóa ẩm thực & Chợ nổi.
3. *Ấn Bản Phù Sa Thực Địa (Sediment Field Dispatches)*: 3 câu chuyện văn hóa có chiều sâu văn học thực tế.
4. *Chỉ Dẫn Hành Trình Bỏ Túi & Chân Trang Tri Ân (Quiet River Guide Footer)*: Thông tin con nước 1 dòng thanh nhã, hotline văn hóa.

- [ ] **Step 2: Kiểm soát chất lượng nội dung (Anti-AI-Slop Audit)**

Đối soát toàn bộ thuật ngữ trong bản spec để đảm bảo 0% văn sáo rỗng.

- [ ] **Step 3: Commit tài liệu đặc tả**

```bash
git add docs/superpowers/specs/2026-09-14-homepage-riverine-broadside-spec.md
git commit -m "docs: add riverine broadside homepage spec with 5W1H2C5M analysis"
```

---

### Task 2: Sinh tạo và Thiết lập Màn hình Duy Nhất trên Google Stitch

**Files:**
- Modify: Project Stitch `projects/14916181929760067680` qua Stitch MCP (`generate_screen_from_text`)
- Create: `C:\Users\NCTaam\.gemini\antigravity-ide\brain\71b606fa-723e-4a79-8a19-854bf74a7b8d\stitch_screen_riverine_masterpiece.html`
- Create: `C:\Users\NCTaam\.gemini\antigravity-ide\brain\71b606fa-723e-4a79-8a19-854bf74a7b8d\stitch_screen_riverine_masterpiece.png`

**Interfaces:**
- Consumes: Prompt từ `docs/superpowers/specs/2026-09-14-homepage-riverine-broadside-spec.md`
- Produces: 1 màn hình chuẩn duy nhất trên `projects/14916181929760067680` với ID xác định, tải về file cục bộ để kiểm tra.

- [ ] **Step 1: Soạn prompt tối ưu hóa cho Stitch MCP**

Prompt tích hợp đầy đủ hệ thống Design System: Lora Serif + Be Vietnam Pro, bảng màu Terracotta `#B95F38` + Deep Azure `#004E74` + Raw Warm Canvas `#FAF8F5`, loại bỏ triệt để viền răng cưa, loại bỏ thẻ bento đen, đảm bảo 40% negative space và nhịp điệu báo chí thanh nhã.

- [ ] **Step 2: Gửi lệnh `generate_screen_from_text` đến dự án `14916181929760067680`**

Gửi lệnh tạo màn hình Desktop với tiêu đề:
`VinhLong360 - Kỳ Đài Sông Nước Nam Bộ (Riverine Living Broadside Masterpiece)`.

- [ ] **Step 3: Tải mã nguồn HTML và ảnh Render độ nét cao về thư mục Artifacts**

Tải file `stitch_screen_riverine_masterpiece.html` và `stitch_screen_riverine_masterpiece.png`.

- [ ] **Step 4: Thẩm định trực quan (Visual & Ergonomic Verification)**

Kiểm tra trực tiếp ảnh render:
- Chiều cao có nằm trong ngưỡng $3.600\text{px} - 4.200\text{px}$?
- Có biến mất hoàn toàn viền răng cưa và các chi tiết rườm rà?
- Có giữ được sự ấm áp, sống động của dòng sông Vĩnh Long thay vì khoảng trắng vô hồn?

---

### Task 3: Đồng bộ và Thanh lọc Mã Nguồn Nuxt (`web-nuxt`)

**Files:**
- Modify: `web-nuxt/components/home/HomeNativeStories.vue`
- Modify: `web-nuxt/components/home/HomeDecisionLedger.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-native-stories.test.ts`
- Test: `web-nuxt/tests/home-decision-ledger.test.ts`

**Interfaces:**
- Consumes: Bản thiết kế chuẩn đã được phê duyệt trên Stitch
- Produces: Mã nguồn Vue/CSS sạch bóng AI-slop, khớp 100% với giao diện mới.

- [ ] **Step 1: Viết test kiểm tra chống AI-slop (TDD)**

Cập nhật `web-nuxt/tests/home-native-stories.test.ts` để kiểm tra cấm các từ ngữ sáo rỗng và kiểm tra tiêu đề mới "Nhịp chèo trên rạch An Bình".

- [ ] **Step 2: Chạy test để xác nhận FAIL đỏ**

```bash
cd web-nuxt && npx vitest run tests/home-native-stories.test.ts
```

- [ ] **Step 3: Cập nhật nội dung văn hóa trong `HomeNativeStories.vue`**

Thay thế các đoạn văn mẫu du lịch bằng bút pháp điền dã thực tế (nhịp chèo, lò nung, phù sa).

- [ ] **Step 4: Chạy test để xác nhận PASS xanh**

```bash
cd web-nuxt && npx vitest run tests/home-native-stories.test.ts
```

- [ ] **Step 5: Tinh chỉnh CSS trong `home-nocturne.css`**

Loại bỏ background đen nặng nề của `.hero-sub`, xóa bỏ đường kẻ chia cắt vụn vặt, thiết lập padding mở rộng tạo độ thoáng tự nhiên $\ge 40\%$.

- [ ] **Step 6: Commit các thay đổi mã nguồn**

```bash
git add web-nuxt/components/home/ web-nuxt/assets/css/ web-nuxt/tests/
git commit -m "feat(home): align homepage with riverine living broadside design, purge ai-slop"
```

---

### Task 4: Kiểm Chứng Toàn Diện & Nghiệm Thu (Verification)

**Files:**
- Modify: `visual_inspection_report.md`

**Interfaces:**
- Consumes: Toàn bộ test suite và script kiểm tra độ tương phản màu
- Produces: Báo cáo nghiệm thu đạt 100% tiêu chuẩn.

- [ ] **Step 1: Chạy toàn bộ 20 file test Vitest**

```bash
cd web-nuxt && npx vitest run tests/home-
```
Kỳ vọng: 20/20 test files, 104+ tests PASS 100%.

- [ ] **Step 2: Kiểm tra tương phản màu sắc WCAG AAA**

```bash
node scripts/check-tri-region-contrast.mjs
```
Kỳ vọng: Exit code 0, không có nợ màu sắc (color debt).

- [ ] **Step 3: Cập nhật báo cáo nghiệm thu và trình diễn trực quan**

Cập nhật `visual_inspection_report.md` và cung cấp link xem trực tiếp trên Stitch.
