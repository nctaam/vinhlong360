# Kế Hoạch Nâng Cấp Thị Giác & Tối Ưu Hóa Tỷ Lệ Ảnh/Chữ Trang Chủ Vĩnh Long 360 (Visual-First Mastery Implementation Plan)
> STATUS: active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng cấp toàn diện mỹ học thị giác cho **DUY NHẤT CỬA SỔ HIỆN TẠI** (`113af35ecf1846e8b4dd7425c432f425` trên Google Stitch và `pages/index.vue` trong `web-nuxt`), đảo ngược tỷ lệ Ảnh/Chữ từ 25/75 (nhiều chữ, thiếu ảnh, khô khan) thành 65/35 (giàu hình ảnh, cuốn hút, sang trọng chuẩn tạp chí di sản quốc tế), loại bỏ triệt để AI-slop, **TUYỆT ĐỐI KHÔNG TẠO THÊM CỬA SỔ/MÀN HÌNH MỚI**.

**Architecture:** Áp dụng trường phái `editorial-grid-magazine` kết hợp `visual storytelling photo gallery layout` từ `ui-ux-pro-max`: Hero composition ảnh kép, lưới bộ tứ không gian văn hóa bất đối xứng giàu hình ảnh, 100% bài ký sự đều có ảnh tư liệu thực địa bảo tàng, bổ sung dải thị giác di sản bỏ túi (Pocket Visual Vignette Strip), cô đọng câu chữ thành văn phong khảo cứu sắc bén.

**Tech Stack:** Tailwind CSS v3/v4 tokens, Google Stitch MCP (`edit_screens`), Nuxt 3, Vue 3, Vitest, WCAG 2.2 AAA Contrast Tools.

**Spec:** `docs/superpowers/specs/2026-09-14-visual-elevation-spec.md`

## Global Constraints

- **DUY NHẤT 1 CỬA SỔ TRÊN STITCH:** Chỉ chỉnh sửa in-place trên màn hình `113af35ecf1846e8b4dd7425c432f425` của project `14916181929760067680`. Tuyệt đối cấm tạo mới bất kỳ màn hình nào.
- **TUYỆT ĐỐI KHÔNG AI-SLOP:** Không dùng ảnh stock vô danh, không dùng đồ họa vector giả tạo; sử dụng 100% tư liệu ảnh chụp thực địa độ phân giải cao về Vĩnh Long (lò gạch Măng Thít, sông Cổ Chiên hoàng hôn, cù lao An Bình, đờn ca tài tử, ẩm thực cá tai tượng, bưởi Năm Roi, chùa Khmer).
- **CÔ ĐỌNG CÂU CHỮ:** Cắt giảm 40% dung lượng chữ thừa, dẹp bỏ các đoạn văn giải thích dài dòng mang tính giáo điều, giữ lại tiêu đề đắt giá, phụ đề ngắn gọn, danh ngôn văn hóa và nhãn tọa độ khảo nghiệm.
- **ĐỘ TIN CẬY 100%:** 20/20 test files (105+ tests) trong `web-nuxt/tests/` phải PASS 100%, 0 color debt, WCAG 2.2 AAA contrast pass.
- **BẤT BIẾN HỆ THỐNG:** Không chạm vào SQLite `vinhlong360.db` và `web/data.json` (bảo toàn B1, B6, B7).

---

### Task 1: Phân Tích Pháp Y Khiếm Khuyết Thị Giác & Lập Đặc Tả Tái Cân Bằng Mỹ Học (Visual Elevation Spec)

**Files:**
- Create: `docs/superpowers/specs/2026-09-14-visual-elevation-spec.md`

**Interfaces:**
- Consumes: Hiện trạng màn hình `113af35ecf1846e8b4dd7425c432f425` và phản hồi của người dùng về tình trạng "nhiều chữ, ít hình ảnh, kém thu hút".
- Produces: Bản đặc tả phân bổ hình ảnh chi tiết, danh mục 12 URL ảnh tư liệu thực địa, thông số tỷ lệ khung hình (aspect ratio) và phân bổ lưới bất đối xứng.

- [ ] **Step 1: Khảo sát định lượng tỷ lệ diện tích Ảnh/Chữ trên màn hình hiện tại**
  Xác định tỷ lệ diện tích hiện tại: chữ chiếm ~75% diện tích màn hình, chỉ có 6 ảnh đơn điệu. Mục tiêu: tăng lên ít nhất 10-12 hình ảnh tư liệu di sản, nâng diện tích thị giác lên $\ge 65\%$.

- [ ] **Step 2: Tuyển chọn bộ ảnh tư liệu thực địa độ phân giải cao đã qua kiểm định**
  Khớp 12 hình ảnh tư liệu thực địa Vĩnh Long từ tàng thư ảnh bảo tàng Google Stitch:
  1. *Hero Primary:* Hoàng hôn sông Tiền & Vòm lò gạch Măng Thít (`AEtjO1WL80s...`)
  2. *Hero Inset:* Ghe tam bản rẽ nước sớm mai rạch Cù lao An Bình (`AB6AXuCyCb...`)
  3. *Territory 1:* Cù lao An Bình mướt xanh & vườn chôm chôm (`AEtjO1W5b2...`)
  4. *Territory 2:* Vương quốc lò gạch Măng Thít rực rỡ hoàng hôn kênh Thầy Cai (`AEtjO1Xk3D...`)
  5. *Territory 3:* Trầm tích Khmer, Chùa Âng & Ao Bà Om cổ thụ (`AEtjO1XLye...`)
  6. *Territory 4:* Cá tai tượng chiên xù cuốn bánh tráng & rau rừng (`AEtjO1Xvwi...`)
  7. *Chronicle 1:* Ghe tam bản len lỏi rạch dừa nước sương sớm (`AB6AXuAksv...`)
  8. *Chronicle 2:* Kết cấu vòm lò gạch nung trấu rực lửa đỏ (`AB6AXuCglv...`)
  9. *Chronicle 3:* Đờn ca tài tử bên hiên nhà gỗ ngắm trăng bến sông (`AEtjO1UoAy...`)
  10. *Vignette Strip 1:* Bưởi Năm Roi trĩu cành Mỹ Hòa (`AEtjO1Vdka...`)
  11. *Vignette Strip 2:* Nghệ nhân tạo tác gốm đất sét đỏ trên bàn xoay (`AEtjO1UR3T...`)
  12. *Vignette Strip 3:* Dạ khúc Cổ Chiên & Lửa lò gạch nung đêm rằm (`AEtjO1Vy41...`)

- [ ] **Step 3: Soạn thảo tài liệu đặc tả mỹ học `docs/superpowers/specs/2026-09-14-visual-elevation-spec.md`**
  Đảm bảo dòng 2 có header `> STATUS: active` theo chuẩn Ratchet R60.1.

- [ ] **Step 4: Commit tài liệu đặc tả**
  `git add docs/superpowers/specs/2026-09-14-visual-elevation-spec.md && git commit -m "docs: add visual elevation and photo-rich layout spec"`

---

### Task 2: Thực Thi Vi Phẫu Thị Giác In-Place Trên Màn Hình Stitch Hiện Tại

**Files:**
- Modify: Screen `113af35ecf1846e8b4dd7425c432f425` trên Google Stitch (qua MCP `edit_screens`)
- Download: `stitch_screen_riverine_masterpiece.html` và `stitch_screen_riverine_masterpiece.png`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-09-14-visual-elevation-spec.md`
- Produces: Màn hình `113af35ecf1846e8b4dd7425c432f425` được nâng cấp sâu về thị giác trực tiếp trên Stitch Cloud.

- [ ] **Step 1: Chuẩn bị payload prompt chỉnh sửa cho `edit_screens`**
  Soạn thảo prompt chỉnh sửa vi phẫu thuật có cấu trúc nghiêm ngặt:
  - **Tái cấu trúc Hero Section:** Chuyển từ cột chữ đơn điệu sang bố cục *Asymmetric Visual Panorama*. Đặt ảnh lớn toàn cảnh hoàng hôn sông Cổ Chiên và vòm lò gạch (aspect 16:9), lồng ghép khung ảnh nhỏ nghệ thuật (inset polaroid/archival frame) cận cảnh nhịp chèo xuồng ba lá. Rút gọn đoạn văn mô tả còn 2 câu đắt giá.
  - **Tái cấu trúc Section 2 (Bộ Tứ Không Gian Văn Hóa):** Tăng diện tích hiển thị ảnh từ 16:10 lên tỉ lệ vàng 3:2 với hiệu ứng hover zoom mượt mà, đưa các thông số di sản (mã bảo tồn, cự ly km, thời gian) thành các huy hiệu viền liquid glass trong suốt nổi trên góc ảnh thay vì chôn dưới chân thẻ. Rút gọn văn bản thẻ còn 1-2 câu súc tích.
  - **Tái cấu trúc Section 3 (Ký Sự Phù Sa):** Đưa ảnh tư liệu thực địa vào CẢ 3 BÀI KÝ SỰ. Mỗi bài là một bố cục Magazine Spread 2 cột kinh điển: Một bên là ảnh tư liệu lớn (aspect 4:3), một bên là tiêu đề Lora, Drop Cap cổ điển và khối trích dẫn văn hóa nổi bật.
  - **Bổ sung Section Dải Thị Giác Di Sản (Pocket Heritage Photo Vignette Strip):** 4 khung ảnh vuông bo nhẹ góc kèm nhãn kiểm định `[MS: VL-01]` đến `[MS: VL-04]` tạo nhịp điệu thị giác choáng ngợp trước khi xuống footer.

- [ ] **Step 2: Thực thi lệnh MCP `edit_screens` trên duy nhất màn hình `113af35ecf1846e8b4dd7425c432f425`**
  Gọi MCP `call_mcp_tool` với `ServerName: "stitch"`, `ToolName: "edit_screens"`. Chỉ truyền đúng ID màn hình hiện tại.

- [ ] **Step 3: Tải về và kiểm tra ảnh chụp render mới nhất**
  Tải file screenshot và HTML từ downloadUrl mới về `stitch_screen_riverine_masterpiece.png` và `stitch_screen_riverine_masterpiece.html`.

- [ ] **Step 4: Kiểm tra xác nhận qua Stitch MCP `list_screens`**
  Xác minh trong project `14916181929760067680` vẫn chỉ có đúng 1 màn hình duy nhất.

---

### Task 3: Đồng Bộ Mỹ Học Hình Ảnh & Tinh Giản Chữ Vào Codebase `web-nuxt`

**Files:**
- Create: `web-nuxt/tests/home-visual-prominence.test.ts`
- Modify: `web-nuxt/components/home/HomeCategoryIndex.vue`
- Modify: `web-nuxt/components/home/HomeNativeStories.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css`

**Interfaces:**
- Consumes: Chuẩn mỹ học hình ảnh từ Stitch màn hình đã nâng cấp.
- Produces: Giao diện web Nuxt đồng bộ tỷ lệ ảnh/chữ thoáng đãng, lôi cuốn, không bị ngợp chữ.

- [ ] **Step 1: Viết test TDD kiểm tra tính nổi trội thị giác (Visual Prominence Test)**
  Tạo `web-nuxt/tests/home-visual-prominence.test.ts` khẳng định:
  - Mỗi thẻ danh mục văn hóa có tỷ lệ khung ảnh ưu tiên $\ge 40\%$ chiều cao thẻ.
  - Mỗi mục ký sự bản địa bắt buộc gắn liền với tư liệu hình ảnh trực quan (không được có bài ký sự không ảnh).
  - Không có đoạn văn mô tả nào vượt quá 180 ký tự gây ngợp chữ.

- [ ] **Step 2: Chạy test để xác nhận trạng thái RED**
  `cd web-nuxt && npx vitest run tests/home-visual-prominence.test.ts`

- [ ] **Step 3: Cập nhật `HomeCategoryIndex.vue` và `HomeNativeStories.vue`**
  - Tinh giản văn bản mô tả, làm nổi bật ảnh đại diện và thẻ huy hiệu di sản.
  - Bảo đảm lớp phủ tương phản (media plate) đạt chuẩn WCAG AAA.

- [ ] **Step 4: Chạy test để xác nhận trạng thái GREEN**
  `cd web-nuxt && npx vitest run tests/home-visual-prominence.test.ts`

- [ ] **Step 5: Commit mã nguồn**
  `git add web-nuxt/ && git commit -m "feat(home): elevate visual prominence and balance photo-to-text ratio"`

---

### Task 4: Cổng Nghiệm Thu Pháp Y Tự Động & Lập Báo Cáo Hoàn Thành

**Files:**
- Modify: `C:\Users\NCTaam\.gemini\antigravity-ide\brain\71b606fa-723e-4a79-8a19-854bf74a7b8d\implementation_plan.md`
- Modify: `C:\Users\NCTaam\.gemini\antigravity-ide\brain\71b606fa-723e-4a79-8a19-854bf74a7b8d\walkthrough.md`

**Interfaces:**
- Consumes: Toàn bộ kết quả thực thi từ Task 1 đến Task 3.
- Produces: Báo cáo nghiệm thu hoàn chỉnh kèm minh chứng hình ảnh render trên Stitch và tỷ lệ kiểm thử.

- [ ] **Step 1: Chạy toàn bộ 21 test files Vitest trang chủ**
  `cd web-nuxt && npx vitest run tests/home-` (kỳ vọng: 108+ tests PASS 100%).

- [ ] **Step 2: Chạy kiểm định độ tương phản màu sắc**
  `cd web-nuxt && node scripts/check-tri-region-contrast.mjs` (kỳ vọng: Exit code 0, WCAG AAA).

- [ ] **Step 3: Cập nhật artifact `walkthrough.md` và `implementation_plan.md`**
  Ghi nhận bảng đối chiếu trước/sau, ảnh chụp màn hình render mới trên Stitch và link truy cập trực tiếp.

- [ ] **Step 4: Kiểm tra trạng thái git repository**
  Đảm bảo working tree sạch sẽ, các file được phân bổ rõ ràng.
