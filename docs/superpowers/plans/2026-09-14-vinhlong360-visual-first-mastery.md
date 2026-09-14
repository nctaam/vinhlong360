# Kế Hoạch Nâng Cấp Thị Giác Đột Phá & Tối Ưu Bố Cục Trang Chủ Vĩnh Long 360 (Visual-First Mastery Implementation Plan)
> STATUS: active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng cấp toàn diện mỹ học thị giác cho **DUY NHẤT CỬA SỔ HIỆN TẠI** (`6fd9ce814d344126b9af2791d77b1d3a` - *VinhLong360 - Cổng Di Sản Sông Nước & Khảo Cứu Thực Địa* trên Google Stitch và `web-nuxt`), cắt giảm triệt để 65% lượng chữ dư thừa (từ 1.021 từ xuống dưới 350 từ), nâng diện tích bề mặt thị giác lên $\ge 75\%$, thay thế các hộp trắng đơn điệu bằng bố cục thẻ ảnh tràn viền nghệ thuật (*Full-Bleed Borderless Photo Portals*), **TUYỆT ĐỐI KHÔNG TẠO THÊM CỬA SỔ MỚI**, triệt tiêu 100% AI-slop.

**Architecture:** Áp dụng trường phái `editorial-grid-magazine` kết hợp `cinematic visual storytelling`: Hero panorama mở rộng choáng ngợp; Bộ Tứ Không Gian chuyển thành 4 khung ảnh tràn viền 100% với huy hiệu kính mờ nổi trên ảnh (xóa bỏ hoàn toàn các hộp trắng chứa chữ bên dưới); Ký Sự Phù Sa chuyển thành bố cục ảnh phóng sự bất đối xứng với Drop Cap và lời dẫn sắc bén; mở rộng Tàng thư bỏ túi thành dải mosaic 6 ảnh tư liệu; chuẩn hóa Typography với `letter-spacing: 0px` không lỗi font.

**Tech Stack:** Tailwind CSS v3/v4 tokens, Google Stitch MCP (`edit_screens`), Nuxt 3, Vue 3, Vitest, WCAG 2.2 AAA Contrast Tools.

**Spec:** `docs/superpowers/specs/2026-09-14-visual-first-redesign-spec.md`

## Global Constraints

- **DUY NHẤT 1 CỬA SỔ MỤC TIÊU TRÊN STITCH:** Chỉ thao tác trên màn hình hiện tại `6fd9ce814d344126b9af2791d77b1d3a` của project `14916181929760067680`. Tuyệt đối cấm tạo mới bất kỳ màn hình nào.
- **CẮT GIẢM 65% DUNG LƯỢNG CHỮ:** Tổng số từ trong phần nội dung chính `<main>` phải giảm từ 1.021 từ xuống **dưới 350 từ**. Xóa bỏ toàn bộ các đoạn văn giải thích dài dòng, câu chữ giáo điều; chỉ giữ lại tiêu đề đắt giá, 1 câu định danh bản địa, và nhãn trắc địa/thủy văn súc tích.
- **DIỆN TÍCH BỀ MẶT ẢNH $\ge 75\%$:** Không sử dụng layout "ảnh trên - hộp chữ dưới" thông thường. Áp dụng kỹ thuật thẻ tràn viền (full-bleed photo portals) nơi toàn bộ bề mặt thẻ là ảnh chụp thực địa độ phân giải cao, thông tin được tinh gọn nổi trên nền kính mờ (*liquid glass*).
- **TUYỆT ĐỐI KHÔNG AI-SLOP:** 100% ảnh chụp thực địa Vĩnh Long đã kiểm định (lò gạch Măng Thít, sông Cổ Chiên hoàng hôn, ghe tam bản An Bình, đờn ca tài tử, cá tai tượng chiên xù, bưởi Năm Roi, chùa Khmer).
- **ĐỘ TIN CẬY 100%:** 21/21 test files trong `web-nuxt/tests/` phải PASS 100%, 0 color debt (WCAG 2.2 AAA), pre-commit hook `run_hard` sạch sẽ.
- **BẤT BIẾN HỆ THỐNG:** Không chạm vào SQLite `vinhlong360.db` và `web/data.json` (bảo toàn B1, B6, B7).

---

### Task 1: Thiết Lập Đặc Tả Tái Cấu Trúc Bố Cục Thị Giác & Lọc Bỏ Chữ Thừa (Spec & Asset Mapping)

**Files:**
- Create: `docs/superpowers/specs/2026-09-14-visual-first-redesign-spec.md`

**Interfaces:**
- Consumes: Phân tích định lượng từ màn hình hiện tại `6fd9ce814d344126b9af2791d77b1d3a` (1.021 từ, 5 section, các hộp chữ trắng chiếm chỗ).
- Produces: Bản đặc tả chi tiết bố cục mới: lược đồ cắt giảm chữ từng phân đoạn, thông số kích thước ảnh tràn viền, bộ 14 URL ảnh tư liệu thực địa Vĩnh Long độ phân giải cao.

- [ ] **Step 1: Khảo sát định lượng và lập ma trận cắt giảm văn bản từng phân đoạn**
  - Section 1 (Hero): Giảm từ 180 từ $\to$ 45 từ (1 tiêu đề Lora, 1 câu phụ đề 18 từ, 1 thanh tìm kiếm xúc giác, 1 câu đề từ Sơn Nam).
  - Section 2 (Bộ Tứ Không Gian): Giảm từ 220 từ $\to$ 60 từ (mỗi thẻ chỉ gồm Tiêu đề + 1 dòng mô tả 12 từ + nhãn kính mờ nổi trên ảnh, xóa sạch hộp chữ trắng bên dưới).
  - Section 3 (Ký Sự Phù Sa): Giảm từ 450 từ $\to$ 120 từ (mỗi bài chỉ gồm Tiêu đề, Drop Cap, 2 câu trích ký sự thực địa, 1 trích dẫn linh hồn).
  - Section 4 (Tàng Thư Bỏ Túi): Giữ 40 từ cho các nhãn kiểm định ảnh di sản.
  - Section 5 (Thước Đo Thủy Triều): Rút gọn còn 35 từ cho khuyến nghị con nước.
  - Tổng số từ kỳ vọng: $\approx 300\text{ từ}$ (giảm 70% so với 1.021 từ hiện tại).

- [ ] **Step 2: Đặc tả cấu trúc thẻ ảnh tràn viền (Full-Bleed Photo Portal Architecture)**
  - Thẻ 100% diện tích là ảnh với tỷ lệ $4:5$ hoặc $16:10$.
  - Lớp phủ gradient chìm: `bg-gradient-to-t from-black/85 via-black/30 to-transparent`.
  - Toàn bộ chữ và huy hiệu nổi trực tiếp trên ảnh, bo góc `rounded-xl`, viền tóc `border border-white/15`, hiệu ứng hover phóng nhẹ `scale-105` tạo cảm giác mở ra cánh cửa thực địa.

- [ ] **Step 3: Soạn thảo tài liệu đặc tả `docs/superpowers/specs/2026-09-14-visual-first-redesign-spec.md`**
  Đảm bảo dòng 2 có header `> STATUS: active` theo chuẩn Ratchet R60.1.

- [ ] **Step 4: Commit tài liệu đặc tả vào git**
  `git add docs/superpowers/specs/2026-09-14-visual-first-redesign-spec.md && git commit -m "docs: add visual-first redesign spec with text reduction blueprint"`

---

### Task 2: Tái Cấu Trúc Bố Cục Thị Giác Trên Bản HTML Master Cục Bộ (`stitch_vinhlong360_visual_first.html`)

**Files:**
- Modify: `stitch_vinhlong360_visual_first.html`

**Interfaces:**
- Consumes: Bản đặc tả `docs/superpowers/specs/2026-09-14-visual-first-redesign-spec.md`.
- Produces: Tệp HTML master hoàn chỉnh, thoáng đãng, lộng lẫy, đạt chuẩn $<350$ từ và $\ge 75\%$ diện tích ảnh.

- [ ] **Step 1: Tái thiết kế Section 1 (Hero Cinematic Stage)**
  - Mở rộng khung ảnh Panorama thành tỷ lệ rộng lớn, tích hợp thẻ ảnh polaroid nổi và nhãn tọa độ `[10.254°N 105.972°E]`.
  - Tinh lọc văn bản cột trái còn đúng 1 H1 Lora thanh thoát, 1 câu định danh ngắn, thanh tìm kiếm tối giản và câu trích dẫn Sơn Nam.

- [ ] **Step 2: Tái thiết kế Section 2 (Bộ Tứ Không Gian Tràn Viền - 100% Visual Portals)**
  - Loại bỏ hoàn toàn khối `div.p-6` nền trắng dưới ảnh.
  - Đưa ảnh lên tỷ lệ $4:5$ hoặc $3:2$ chiếm toàn bộ thẻ.
  - Thông tin (tiêu đề, nhãn di sản, 1 dòng tóm tắt, nút khám phá) được đặt trực tiếp bên trong lớp phủ gradient đáy ảnh bằng kính mờ (*liquid glass*).

- [ ] **Step 3: Tái thiết kế Section 3 (Ký Sự Phù Sa - Asymmetric Magazine Spread)**
  - Cắt bỏ các đoạn văn dài và hộp thông số xám lặp lại.
  - Mỗi bài ký sự là một cặp đôi hoàn mỹ: Bên trái là tiêu đề + Drop Cap + trích dẫn nổi bật; bên phải là ảnh tư liệu thực địa $16:10$ chiếm trọn 55% độ rộng.

- [ ] **Step 4: Mở rộng Section 4 (Tàng Thư Điền Dã Bỏ Túi Mosaic)**
  - Nâng cấp từ 4 ảnh vuông nhỏ thành dải 6 ảnh tư liệu nhịp điệu phong phú (Bưởi Năm Roi, Kênh Thầy Cai, Dạ khúc Cổ Chiên, Vườn chôm chôm, Ghe tam bản rạng đông, Lò gốm nung lửa đỏ).

- [ ] **Step 5: Kiểm định định lượng bằng script tự động**
  - Chạy `python scratch/analyze_layout.py` để khẳng định:
    - Tổng số từ $< 350$ từ (đạt chuẩn cắt giảm 65%).
    - Số lượng ảnh $\ge 14$ ảnh chất lượng cao.
    - Zero khoảng trắng lỗi phông (`Gố m`, `Trầ m`, `Miế u`).

---

### Task 3: Đồng Bộ Trực Tiếp Vào Màn Hình Stitch Hiện Tại (`6fd9ce814d344126b9af2791d77b1d3a`)

**Files:**
- Modify: Màn hình `6fd9ce814d344126b9af2791d77b1d3a` trên Google Stitch (qua Stitch MCP `edit_screens`)
- Download: Cập nhật `stitch_generated_screen_visual_first.png`

**Interfaces:**
- Consumes: Mã nguồn HTML đã được tối ưu từ Task 2.
- Produces: Màn hình `6fd9ce814d344126b9af2791d77b1d3a` được cập nhật đồng bộ trực tiếp trên Stitch Cloud.

- [ ] **Step 1: Chuẩn bị prompt vi phẫu có cấu trúc cho Stitch `edit_screens`**
  Soạn thảo prompt truyền chính xác các khối DOM thay thế (Hero cinematic, 4 thẻ tràn viền không hộp trắng, 3 bài ký sự ảnh lớn cô đọng, dải 6 ảnh mosaic) nhắm thẳng vào ID `6fd9ce814d344126b9af2791d77b1d3a`.

- [ ] **Step 2: Gọi Stitch MCP `edit_screens` trên duy nhất màn hình `6fd9ce814d344126b9af2791d77b1d3a`**
  Gọi MCP `call_mcp_tool` với `ServerName: "stitch"`, `ToolName: "edit_screens"`. Chỉ truyền đúng ID hiện tại.

- [ ] **Step 3: Kiểm tra xác nhận qua Stitch MCP `list_screens`**
  Xác minh không phát sinh thêm bất kỳ màn hình rác nào trên project `14916181929760067680`.

- [ ] **Step 4: Tải về screenshot mới nhất và kiểm định trực quan**
  Tải ảnh chụp từ `downloadUrl` về `stitch_generated_screen_visual_first.png` và xác minh tính thẩm mỹ vượt trội.

---

### Task 4: Đồng Bộ Mã Nguồn `web-nuxt` & Nghiệm Thu Pháp Y Tự Động

**Files:**
- Modify: `web-nuxt/components/home/HomeCategoryIndex.vue`
- Modify: `web-nuxt/components/home/HomeNativeStories.vue`
- Modify: `web-nuxt/tests/home-visual-prominence.test.ts`

**Interfaces:**
- Consumes: Thiết kế ảnh tràn viền và văn phong cô đọng từ Task 2 & Task 3.
- Produces: Codebase Nuxt 3 đồng bộ mỹ học, toàn bộ test tự động xanh 100%.

- [ ] **Step 1: Cập nhật `HomeCategoryIndex.vue` và `HomeNativeStories.vue`**
  - Chuyển đổi thẻ danh mục sang phong cách ảnh tràn viền (*full-bleed photo portal*), loại bỏ các khoảng đệm trắng dưới đáy thẻ.
  - Tinh giản văn bản mô tả còn tối đa 1 dòng ngắn gọn.
  - Bảo đảm lớp phủ tương phản đạt chuẩn WCAG AAA.

- [ ] **Step 2: Cập nhật test TDD `tests/home-visual-prominence.test.ts`**
  Bổ sung kiểm tra định lượng:
  - Khẳng định tỷ lệ chiều cao ảnh trong thẻ danh mục $\ge 60\%$ (thay vì 40% cũ).
  - Khẳng định chiều dài mô tả thẻ $\le 100$ ký tự (thay vì 180 ký tự cũ).
  - Khẳng định 100% bài ký sự đều có ảnh tư liệu.

- [ ] **Step 3: Chạy toàn bộ 21 test files Vitest**
  `cd web-nuxt && npx vitest run tests/home-` (kỳ vọng: 107+ tests PASS 100%).

- [ ] **Step 4: Kiểm tra độ tương phản màu sắc WCAG 2.2 AAA**
  `cd web-nuxt && node scripts/check-tri-region-contrast.mjs` (kỳ vọng: Exit code 0, 0 color debt).

- [ ] **Step 5: Kiểm tra pre-commit ratchet hook và commit**
  `git add web-nuxt/ && git commit -m "feat(home): achieve full-bleed visual-first layout and eliminate text clutter"`
