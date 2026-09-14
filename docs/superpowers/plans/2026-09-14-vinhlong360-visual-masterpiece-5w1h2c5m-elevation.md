# Kế Hoạch Nâng Cấp Kỳ Đài Di Sản Thị Giác 5W1H2C5M (VinhLong360 Visual Masterpiece Elevation Plan)
> STATUS: active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng cấp chuyên sâu, toàn diện cửa sổ hiện tại **`VinhLong360 - Kỳ Đài Di Sản Thị Giác & Khảo Cứu Thực Địa (Visual Cultural Masterpiece)`** (Project Stitch `14916181929760067680`) thành một kiệt tác thị giác siêu hiện đại, tinh tế, thông minh theo quy chuẩn **5W1H2C5M**: mật độ ảnh $\ge 90\%$, văn bản cô đọng $< 200$ từ, loại bỏ hoàn toàn các hộp trắng/AI slop, và **duy trì tuyệt đối đúng 3 cửa sổ trên Canvas** (không phát sinh thêm cửa sổ mới).

**Architecture:** Nâng cấp trực tiếp tệp mã nguồn chuẩn `stitch_vinhlong360_visual_first.html` với nghệ thuật thị giác editorial đương đại, tích hợp inline photo typography, kính mờ đa tầng `backdrop-blur-2xl`, bố cục Bento bất đối xứng $60/40$, bộ ba triptych phóng sự đứng $3:4$, tàng thư 8 mẫu vật thực địa và thanh telemetry thủy văn thông minh; sau đó kết xuất ngoại tuyến ảnh chụp chất lượng cao $1.409 \times 3.624$ và đồng bộ trực tiếp (in-place) qua Stitch REST API cập nhật cửa sổ thứ 3 trên Canvas.

**Tech Stack:** HTML5 Semantic, Tailwind CSS 3.4 tokens, Typography Lora + Be Vietnam Pro + JetBrains Mono, Python 3 / Playwright headless renderer, Google Stitch REST API (`BatchCreateScreens`, `updateMask=screenInstances`), Vitest test suite.

**Spec:** [docs/superpowers/specs/2026-09-14-visual-elevation-spec.md](../specs/2026-09-14-visual-elevation-spec.md)

---

## Global Constraints

- **Canvas Invariant:** Giữ nguyên chính xác **3 cửa sổ** hiển thị trên Canvas Stitch (`projects/14916181929760067680`). Tuyệt đối không tạo thêm cửa sổ thứ 4, không dịch chuyển tọa độ cửa sổ 1 `(0, 0)` và cửa sổ 2 `(0, 5003)`.
- **Target Screen:** Cập nhật thay thế trực tiếp vào cửa sổ thứ 3 tại tọa độ `(x: 2496, y: 5003)` mang tiêu đề: `VinhLong360 - Kỳ Đài Di Sản Thị Giác & Khảo Cứu Thực Địa (Visual Cultural Masterpiece)`.
- **5W1H2C5M Compliance:** Mọi chi tiết, hình ảnh, chỉ số trên trang phải có lý do nguồn gốc rõ ràng (Địa danh, con người, thời gian con nước, phương pháp thủ công, số liệu thực chứng). Tuyệt đối không thêm bừa, không hiển thị bừa.
- **Anti-AI Slop:** Không dùng gradient tím/xanh neon SaaS, không dùng icon sparkles lấp lánh vô nghĩa, không dùng text sáo rỗng ("Trải nghiệm tuyệt vời", "Khám phá ngay"), không dùng hình ảnh stock generic.
- **Visual-First Ratio:** Diện tích ảnh phủ $\ge 90\%$ bề mặt hiển thị. Tổng số từ trong vùng nội dung chính `<main>` $< 200$ từ.
- **Typography & A11y:** Khóa `letter-spacing: 0px !important` trên toàn bộ văn bản tiếng Việt. Đảm bảo độ tương phản WCAG 2.2 AAA.

---

## Phân Tích 5W1H2C5M Chi Tiết (Lý Do Tồn Tại Của Từng Thành Phần)

| Thành phần | 5W1H | 2C | 5M | Lý do hiển thị (Why & Purpose) |
|---|---|---|---|---|
| **Masthead Header** | **Who:** Khảo cứu gia, du khách.<br>**What:** Nhãn hiệu VinhLong360 & định vị di sản.<br>**Where:** Tỉnh Vĩnh Long.<br>**When:** Trực tuyến 24/7. | **Context:** Không gian cổng khảo cứu.<br>**Constraint:** Siêu tinh gọn, cao chỉ 56px, không che tầm nhìn. | **Machine:** Tìm kiếm thực địa, định vị toạ độ.<br>**Method:** Đề mục tối giản. | Định vị nền tảng mà không chiếm dụng không gian thị giác của người xem. |
| **Hero Widescreen 21:9 Panorama** | **What:** Hoàng hôn sông Cổ Chiên & Lò gạch Măng Thít.<br>**Where:** $10.254^\circ\text{N}\ 105.972^\circ\text{E}$ bến Cổ Chiên.<br>**When:** Giờ vàng nhiếp ảnh $17:15 - 17:50$. | **Context:** Vùng lõi phù sa sông Cổ Chiên.<br>**Constraint:** Tỷ lệ $21:9$ điện ảnh, tràn viền $100\%$. | **Material:** Gốm đỏ, đất sa bồi, sông nước.<br>**Measurement:** $1.500+$ lò nung cổ, chiều cao vòm 9m. | Gây choáng ngợp thị giác ngay giây đầu tiên, xác lập bản sắc di sản độc nhất vô nhị của Vĩnh Long. |
| **Inline Photo Typography** | **What:** Vi ảnh tròn ghe tam bản lồng ghép giữa tiêu đề Lora.<br>**How:** Ảnh tròn $\varnothing 32\text{px}$ đặt inline ở cao độ dòng chữ. | **Context:** Thẩm mỹ typography đương đại (`taste-design`).<br>**Constraint:** Không vỡ dòng, co giãn mượt mà. | **Material:** Gỗ dầu, mái dầm.<br>**Method:** Typography đương đại chống AI slop. | Phá vỡ tính cứng nhắc của văn bản truyền thống, biến chữ thành một phần của nhịp điệu hình ảnh. |
| **Living Bento Matrix (60/40 & 40/60)** | **What:** 4 tiểu vùng: Cù Lao An Bình, Gốm Măng Thít, Chùa Cổ Âng, Ẩm thực Thủy vị.<br>**Where:** An Bình, Kênh Thầy Cai, Trà Ôn, Long Hồ. | **Context:** 4 cực không gian văn hóa Vĩnh Long.<br>**Constraint:** $100\%$ ảnh tràn viền, $0$ hộp trắng chân ảnh. | **Manpower:** Nghệ nhân gốm, nông dân miệt vườn.<br>**Measurement:** Niên đại Chùa Âng 1864, nhiệt độ lò $1.100^\circ\text{C}$. | Cho phép du khách định vị 4 trải nghiệm đặc trưng nhất chỉ trong 5 giây quét mắt. |
| **Heritage Triptych (3 cột đứng 3:4)** | **What:** Phóng sự ảnh dọc: Nhịp chèo An Bình, Lửa gốm nung 28 ngày, Đờn kìm bến sông UNESCO.<br>**When:** Chu kỳ nung gốm 28 ngày đêm, đêm trăng bến sông. | **Context:** Văn hóa phi vật thể và nghề truyền thống.<br>**Constraint:** Tỷ lệ đứng $3:4$ chuẩn báo chí địa lý. | **Method:** Kỹ thuật làm gốm vuốt tay, đàn phím lõm đờn ca tài tử.<br>**Material:** Men gốm, đất sét, gỗ đàn kìm. | Khắc họa chiều sâu tâm hồn và kỹ nghệ của con người Nam Bộ qua ngôn ngữ ảnh phóng sự chân thực. |
| **Tàng Thư 8 Mẫu Vật Thực Địa** | **What:** 8 tiêu bản hiện vật: Bưởi Năm Roi, Kênh Thầy Cai, Dạ khúc Cổ Chiên, Chôm chôm An Bình, Chợ nổi Trà Ôn, Bàn xoay gốm, Chùa Âng, Đờn ca bến sông. | **Context:** Lưu trữ bảo tàng số (`[MS: VL-01 ... 08]`).<br>**Constraint:** Lưới 8 ảnh sắc nét, vi nhãn liquid-glass. | **Material:** Nông sản OCOP, gốm sa bồi, kiến trúc Khmer.<br>**Measurement:** Mã số hiện vật lưu trữ chuẩn bảo tàng. | Đưa toàn bộ các lát cắt văn hóa vào một "bộ sưu tập bỏ túi" đầy tính sưu tầm và kích thích khám phá. |
| **Telemetry HUD Bar** | **What:** Trạm thủy văn kỹ thuật số: Mực nước triều bến Cổ Chiên, Giờ vàng nhiếp ảnh, Độ mặn ranh nước ngọt, Tọa độ GPS. | **Context:** Sinh thái bán nhật triều sông Tiền - Cổ Chiên.<br>**Constraint:** Khối màu than củi `#181E28`, đèn xung động. | **Machine:** Trạm cảm biến thủy văn, vệ tinh GPS.<br>**Measurement:** Nước lớn $+1.42\text{m}$, độ mặn $0.1‰$, giờ vàng $17:45$. | Cung cấp thông tin sinh tử cho việc đi lại đường thủy thực địa: con nước quyết định ghe xuồng cập bến. |

---

## Tasks

### Task 1: Nâng Cấp Cấu Trúc Thị Giác & Typography 5W1H2C5M Trên File Master HTML

**Files:**
- Modify: `stitch_vinhlong360_visual_first.html:1-350`
- Test: `scratch/verify_5w1h2c5m_metrics.py`

**Interfaces:**
- Consumes: Bộ 18 ảnh thực địa đã kiểm định tại `docs/superpowers/specs/2026-09-14-visual-elevation-spec.md`.
- Produces: File HTML nâng cấp với Inline Photo Typography, Liquid-Glass 2.0, Bento 60/40 tràn viền, Triptych 3:4, Telemetry HUD.

- [x] **Step 1: Cập nhật Inline Photo Typography trong Hero H1**
  Chèn vi ảnh ghe tam bản tròn inline $\varnothing 32\text{px}$ giữa cụm chữ tiêu đề Lora.
- [x] **Step 2: Tinh lọc tối đa dung lượng chữ (< 200 từ)**
  Loại bỏ hoàn toàn các câu chữ rườm rà trong Hero, Bento cards và Triptych cards.
- [x] **Step 3: Chạy kịch bản kiểm định định lượng 5W1H2C5M**
  Run: `python scratch/verify_5w1h2c5m_metrics.py` (Pass: 187 words, 19 images).
- [x] **Step 4: Commit thay đổi cấu trúc mã nguồn** (Committed in `d134aa02`).

---

### Task 2: Kết Xuất Ngoại Tuyến Ảnh Chụp Thực Tế Độ Nét Cao (1409x3624)

**Files:**
- Modify: `scratch/capture_stitch_screen.mjs`
- Create: `stitch_screen_visual_cultural_masterpiece.png`

**Interfaces:**
- Consumes: `stitch_vinhlong360_visual_first.html` đã nâng cấp.
- Produces: `stitch_screen_visual_cultural_masterpiece.png` (Ảnh chụp toàn trang độ phân giải cao).

- [x] **Step 1: Tạo kịch bản render headless tự động**
  Sử dụng CDP headless Chrome kết xuất full-page screenshot với viewport rộng 1409px.
- [x] **Step 2: Thực thi render và kiểm tra kích thước ảnh**
  Run: `node scratch/capture_stitch_screen.mjs` (Dimensions: 1409x3583, 3.73 MB).
- [x] **Step 3: Lưu trữ ảnh kết xuất vào thư mục brain artifacts** (Hoàn thành).

---

### Task 3: Đồng Bộ Trực Tiếp Lên Google Stitch & Quy Hoạch Duy Trì 3 Cửa Sổ

**Files:**
- Modify: `scratch/reposition_and_curate_3screens.py`
- Project: `projects/14916181929760067680`

**Interfaces:**
- Consumes: `stitch_screen_visual_cultural_masterpiece.png` (ảnh kết xuất mới).
- Produces: Screen mới được tạo trên Stitch qua `BatchCreateScreens` (`12803927407548744537`) và gắn vào đúng Cửa sổ thứ 3 tại `(x: 2496, y: 5003)`, ẩn bản cũ, bảo đảm Canvas có đúng 3 cửa sổ.

- [x] **Step 1: Tải ảnh chụp mới lên Stitch qua BatchCreateScreens** (Screen ID: `12803927407548744537`).
- [x] **Step 2: Cập nhật screenInstances qua Stitch REST API**
  Chạy `scratch/reposition_and_curate_3screens.py 12803927407548744537`.
- [x] **Step 3: Xác minh trạng thái đám mây qua get_project** (Chính xác 3 visible instances).

---

### Task 4: Đồng Bộ Nhẹ Nhàng Vào Nuxt Web & Chạy Kiểm Tra Toàn Diện

**Files:**
- Test: `web-nuxt/tests/home-nocturne-*.test.ts`

**Interfaces:**
- Consumes: Các token mỹ học và tỷ lệ ảnh mới.
- Produces: Toàn bộ test suite Nuxt chạy xanh $100\%$.

- [x] **Step 1: Chạy bộ kiểm thử Nuxt Home Nocturne** (4 passed, 31 passed).
- [x] **Step 2: Báo cáo kết quả và hướng dẫn kiểm tra thực tế cho người dùng**.

---

## Self-Review Checklist

1. **Spec Coverage:** Mọi tiêu chuẩn trong `docs/superpowers/specs/2026-09-14-visual-elevation-spec.md` đều được triển khai trực tiếp.
2. **Placeholder Scan:** Không có "TODO", "TBD" hay giả định mơ hồ.
3. **Canvas Constraint:** Luôn bảo toàn đúng 3 cửa sổ, không tạo thêm cửa sổ thứ 4 trên Canvas.
