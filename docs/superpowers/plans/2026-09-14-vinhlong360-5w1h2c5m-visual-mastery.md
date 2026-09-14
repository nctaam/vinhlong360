# VinhLong360 5W1H2C5M Visual-First Mastery Implementation Plan

> STATUS: complete
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng cấp toàn diện cửa sổ hiện tại `VinhLong360 - Kỳ Đài Di Sản Thị Giác & Khảo Cứu Thực Địa (Visual Cultural Masterpiece)` (Screen ID: `47e7dae92c2648dd8171a8e6f8701aa8` trên Canvas `14916181929760067680`), giải quyết triệt để vấn đề "nhiều chữ, ít ảnh, kém thu hút", chuyển đổi sang ngôn ngữ thị giác thuần khiết với $\ge 85\%$ diện tích ảnh, 18 bức ảnh tư liệu thực địa độ phân giải cao, cắt giảm chữ xuống $< 280$ từ, áp dụng ma trận 5W1H2C5M, không tạo màn hình mới và tránh 100% AI-slop.

**Architecture:** Kiến trúc thị giác phân lớp theo nguyên lý Tạp chí di sản cao cấp (National Geographic / Monocle): Hero Widescreen Panoramic Stage $\to$ Asymmetric Bento 4-Portals $\to$ 3-Column Visual Triptych Stories $\to$ 8-Photo Museum Lightbox Grid $\to$ Telemetry HUD Bar. Toàn bộ thông tin chữ được nén thành huy hiệu kính mờ (Liquid Glass) thả nổi trực tiếp trên ảnh qua lớp phủ gradient quang học.

**Tech Stack:** Vanilla HTML5/CSS3, Tailwind Utilities (Stitch-compatible), Vue 3 SFCs, Nuxt 3, Vitest, Google Stitch Cloud MCP.

**Spec:** `docs/superpowers/specs/2026-09-14-5w1h2c5m-visual-mastery-spec.md`

## Global Constraints

- Màn hình mục tiêu duy nhất: `47e7dae92c2648dd8171a8e6f8701aa8` trên Stitch Project `14916181929760067680`. Tuyệt đối KHÔNG tạo thêm màn hình mới.
- Tổng số từ trong `<main>`: Nghiêm ngặt $< 280\text{ từ}$ (cắt giảm >72% so với bản gốc 1.021 từ).
- Tỉ lệ diện tích bề mặt ảnh: $\ge 85\%$ diện tích trang.
- Số lượng ảnh thực địa đã kiểm định: Đạt 18 ảnh tư liệu bản địa Vĩnh Long, 100% Anti-AI-Slop.
- Typography: Tiêu đề `Lora`, Thân bài `Be Vietnam Pro`, khóa chết `letter-spacing: 0px !important` chống lỗi nhảy chữ tiếng Việt.
- Bất biến kiểm thử: 21/21 test files Vitest PASS 100% (107+ tests), WCAG 2.2 AAA Contrast Check pass với 0 color debt.

---

### Task 1: Tái Thiết Lập Bố Cục Thị Giác 5W1H2C5M Trên Bản Master Cục Bộ (`stitch_vinhlong360_visual_first.html`)

**Files:**
- Modify: `stitch_vinhlong360_visual_first.html`
- Create: `scratch/verify_5w1h2c5m_metrics.py`

**Interfaces:**
- Consumes: Đặc tả `docs/superpowers/specs/2026-09-14-5w1h2c5m-visual-mastery-spec.md`.
- Produces: Bản HTML master cục bộ hoàn thiện với 18 ảnh thực địa, Hero Widescreen, Bento Portals bất đối xứng, Bộ ba Triptych phóng sự, và Lưới bảo tàng 8 ảnh.

- [ ] **Step 1: Viết script kiểm tra định lượng tự động (TDD Check Script)**

```python
# scratch/verify_5w1h2c5m_metrics.py
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('stitch_vinhlong360_visual_first.html', 'r', encoding='utf8') as f:
    html = f.read()

imgs = re.findall(r'<img[^>]+>', html)
print(f'Total <img> tags: {len(imgs)}')
assert len(imgs) >= 17, f'Expected at least 17 images, got {len(imgs)}'

main_m = re.search(r'<main[^>]*>([\s\S]*?)</main>', html)
assert main_m, 'Missing <main> tag'
clean_text = re.sub(r'<[^>]+>', ' ', main_m.group(1))
words = clean_text.split()
print(f'Total words in <main>: {len(words)}')
assert len(words) < 280, f'Expected < 280 words in <main>, got {len(words)}'

# Verify Bento asymmetrical classes
assert 'lg:col-span-7' in html or 'lg:col-span-8' in html or 'col-span-3' in html, 'Missing asymmetric bento portal classes'
# Verify 8-photo mosaic
sec4_m = re.search(r'id=["\']pocket-museum["\'][\s\S]*?</section>', html)
assert sec4_m, 'Missing pocket-museum'
mosaic_imgs = re.findall(r'<img[^>]+>', sec4_m.group(0))
print(f'Pocket museum images: {len(mosaic_imgs)}')
assert len(mosaic_imgs) >= 8, f'Expected >= 8 mosaic images, got {len(mosaic_imgs)}'

# Verify font letter-spacing rule
assert 'letter-spacing: 0px !important' in html, 'Missing letter-spacing override'

print('All 5W1H2C5M visual invariants PASSED!')
```

- [ ] **Step 2: Chạy script kiểm tra để xác nhận FAIL ban đầu**

Run: `python scratch/verify_5w1h2c5m_metrics.py`
Expected: FAIL với "Expected at least 17 images, got 15" hoặc "Expected >= 8 mosaic images, got 6".

- [ ] **Step 3: Cập nhật `stitch_vinhlong360_visual_first.html` đạt chuẩn 5W1H2C5M**
  - Chuyển Section 1 (Hero) thành Cinematic Widescreen Panorama: ảnh bao trọn chiều ngang, khối thông tin Ethereal Glass Capsule nổi mờ góc dưới trái (`backdrop-blur-xl bg-black/50 border border-white/20 p-6 rounded-2xl`).
  - Chuyển Section 2 thành Asymmetric Bento Grid: Thẻ 1 (An Bình) chiếm 60% bề ngang, Thẻ 2 (Măng Thít) 40%, Thẻ 3 (Khmer) 40%, Thẻ 4 (Trà Ôn) 60%.
  - Chuyển Section 3 thành 3-Column Visual Triptych: 3 cột ảnh đứng $3:4$ đặt ngang nhau thay cho 3 khối chữ nhật xếp chồng cũ.
  - Mở rộng Section 4 thành Lưới Bảo Tàng 8 Khung Ảnh Cận Cảnh (Museum Lightbox Grid: 8 ảnh chân dung $4:5$ có mã định danh `[MS: VL-01 ... VL-08]`).
  - Tinh giản tối đa câu chữ: mỗi thẻ chỉ gồm 1 tiêu đề H3 và 1 câu linh hồn dưới 12 từ.

- [ ] **Step 4: Chạy lại script kiểm định để xác nhận PASS**

Run: `python scratch/verify_5w1h2c5m_metrics.py`
Expected: PASS ("All 5W1H2C5M visual invariants PASSED!").

- [ ] **Step 5: Commit tệp HTML master vào git**

```bash
git add stitch_vinhlong360_visual_first.html scratch/verify_5w1h2c5m_metrics.py
git commit -m "feat(stitch): elevate master HTML to 5W1H2C5M visual-first architecture"
```

---

### Task 2: Đồng Bộ Trực Tiếp Vào Màn Hình Stitch Hiện Tại (`47e7dae92c2648dd8171a8e6f8701aa8`)

**Files:**
- Modify: Màn hình `47e7dae92c2648dd8171a8e6f8701aa8` trên Google Stitch (qua Stitch MCP `edit_screens`)
- Download: `stitch_screen_visual_cultural_masterpiece.png`

**Interfaces:**
- Consumes: Mã nguồn HTML 5W1H2C5M từ Task 1.
- Produces: Màn hình Stitch `47e7dae92c2648dd8171a8e6f8701aa8` được cập nhật đồng bộ trực tiếp, 0 màn hình mới sinh ra.

- [ ] **Step 1: Soạn thảo prompt vi phẫu có cấu trúc cho Stitch `edit_screens`**
  Truyền prompt chi tiết nhắm thẳng vào ID `47e7dae92c2648dd8171a8e6f8701aa8`:
  1. Section 1: Cinematic Widescreen Panorama với Ethereal Glass Capsule nổi mờ.
  2. Section 2: Asymmetric Bento Portals (60/40 & 40/60).
  3. Section 3: 3-Column Portrait Triptych Photostories.
  4. Section 4: 8-Photo Museum Lightbox Grid.
  5. Letter-spacing 0px !important và 18 ảnh thực địa.

- [ ] **Step 2: Gọi Stitch MCP `edit_screens` trên đúng màn hình `47e7dae92c2648dd8171a8e6f8701aa8`**
  Gọi MCP `call_mcp_tool` với `ServerName: "stitch"`, `ToolName: "edit_screens"`, `projectId: "14916181929760067680"`, `selectedScreenIds: ["47e7dae92c2648dd8171a8e6f8701aa8"]`.

- [ ] **Step 3: Kiểm tra xác nhận qua Stitch MCP `list_screens`**
  Xác minh danh sách màn hình trên project `14916181929760067680` giữ nguyên vẹn 3 màn hình, không sinh ra bất kỳ màn hình rác nào.

- [ ] **Step 4: Tải về screenshot mới nhất và kiểm định trực quan**
  Tải ảnh từ `downloadUrl` về `stitch_screen_visual_cultural_masterpiece.png` và chạy kiểm tra trực quan.

---

### Task 3: Đồng Bộ Mỹ Học Vào `web-nuxt` & Nghiệm Thu Pháp Y Tự Động

**Files:**
- Modify: `web-nuxt/components/home/HomeCategoryIndex.vue`
- Modify: `web-nuxt/components/home/HomeNativeStories.vue`
- Modify: `web-nuxt/tests/home-visual-prominence.test.ts`

**Interfaces:**
- Consumes: Bố cục Asymmetric Bento và Triptych từ Task 1 & Task 2.
- Produces: Toàn bộ 21 tệp Vitest PASS 100%, WCAG 2.2 AAA pass.

- [ ] **Step 1: Cập nhật `tests/home-visual-prominence.test.ts` để kiểm định độ tinh gọn văn bản**
  Bổ sung kiểm tra:
  - Mọi đoạn văn trong `HomeNativeStories` đều $< 120$ ký tự.
  - Số lượng ảnh tư liệu trong `HomeNativeStories` $\ge 2$.
  - Mọi thẻ danh mục đều có ảnh tư liệu và mô tả $\le 80$ ký tự.

- [ ] **Step 2: Chạy test để xác nhận trạng thái xanh**

Run: `cd web-nuxt && npx vitest run tests/home-visual-prominence.test.ts`
Expected: PASS (2 tests passed).

- [ ] **Step 3: Chạy toàn bộ bộ kiểm thử trang chủ Vitest (21 files)**

Run: `cd web-nuxt && npx vitest run tests/home-`
Expected: PASS (21/21 files passed, 107+ tests passed).

- [ ] **Step 4: Kiểm tra độ tương phản màu sắc WCAG 2.2 AAA**

Run: `cd web-nuxt && node scripts/check-tri-region-contrast.mjs`
Expected: Exit code 0, 0 color debt.

- [ ] **Step 5: Commit thay đổi vào git**

```bash
git add web-nuxt/
git commit -m "feat(home): sync 5w1h2c5m visual-first layout with zero text clutter"
```
