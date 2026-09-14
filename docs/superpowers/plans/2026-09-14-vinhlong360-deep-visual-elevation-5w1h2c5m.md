# Kế Hoạch Nâng Cấp Chiều Sâu Kỳ Đài Di Sản Thị Giác 5W1H2C5M (Deep Visual Elevation Plan)
> STATUS: active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng cấp đột phá, toàn diện cửa sổ hiện tại **`VinhLong360 - Kỳ Đài Di Sản Thị Giác & Khảo Cứu Thực Địa (Visual Cultural Masterpiece)`** (Project Stitch `14916181929760067680`) đạt chuẩn thẩm mỹ bảo tàng thế giới (Rijksmuseum x NatGeo x Apple Ergonomics): xóa bỏ cảm giác phẳng đơn điệu, bổ sung lăng kính thời gian - tọa độ - giác quan theo quy chuẩn **5W1H2C5M**, tăng độ cuốn hút thị giác áp đảo ($\ge 92\%$ bề mặt ảnh), và **duy trì tuyệt đối đúng 3 cửa sổ trên Canvas**.

**Architecture:** Tái cấu trúc file master `stitch_vinhlong360_visual_first.html` thành một ấn bản khảo cứu sống (Living Field Broadside): đưa dữ liệu thủy văn thời gian thực lên đỉnh Hero, bổ sung chỉ số vật liệu - đo đạc thực chứng (5M) vào từng thẻ Bento, phân đoạn ký sự theo mốc thời gian thực địa (05:30 - 14:00 - 19:30), nâng cấp lưới 8 tiêu bản thành tủ mẫu vật bảo tàng số; kết xuất ảnh chụp $1.409 \times 3.600$ và đồng bộ thay thế trực tiếp vào cửa sổ thứ 3 trên Canvas.

**Tech Stack:** HTML5 Semantic, Tailwind CSS 3.4, Typography Lora + Be Vietnam Pro + JetBrains Mono, CDP Headless Chrome Screenshot Renderer, Google Stitch REST API (`BatchCreateScreens`, `updateMask=screenInstances`), Vitest.

**Spec:** [docs/superpowers/specs/2026-09-14-visual-elevation-spec.md](../specs/2026-09-14-visual-elevation-spec.md)

---

## Global Constraints

- **Canvas Invariant:** Giữ nguyên chính xác **3 cửa sổ** trên Canvas Stitch (`projects/14916181929760067680`). Tuyệt đối không tạo thêm cửa sổ thứ 4, không dịch chuyển vị trí 2 cửa sổ còn lại.
- **Target Screen:** Cập nhật thay thế trực tiếp vào Cửa sổ thứ 3 tại tọa độ `(x: 2496, y: 5003)`.
- **5W1H2C5M Strict Grounding:** Không có bất kỳ chi tiết trang trí ngẫu nhiên nào. Từng thẻ ảnh, nhãn badge, thông số đều đại diện cho một sự thật địa lý, sinh thái hoặc kỹ nghệ thủ công Vĩnh Long đã kiểm định.
- **Anti-AI Slop:** Tuyệt đối không dùng gradient tím/xanh neon SaaS, không dùng icon sparkles lấp lánh vô nghĩa, không dùng text sáo rỗng ("Khám phá ngay", "Trải nghiệm tuyệt vời"), không dùng hình ảnh stock generic.
- **Visual Dominance & Text Discipline:** Mật độ ảnh $\ge 92\%$. Văn bản cô đọng dưới $200$ từ trong toàn bộ `<main>`, mỗi ảnh chỉ mang nhãn danh xưng và thông số đo đạc thực địa.
- **Typography & Font Integrity:** Khóa `letter-spacing: 0px !important` trên toàn bộ văn bản tiếng Việt.

---

## Ma Trận Thiết Kế 5W1H2C5M Nâng Cấp Sâu (Vì Sao Cái Này Hiển Thị Ở Đây?)

| Khối giao diện | Quy chuẩn 5W1H (Who, What, Where, When, Why, How) | Quy chuẩn 2C & 5M (Context, Constraint, Manpower, Machine, Material, Method, Measurement) | Đột phá thẩm mỹ & Tính thông minh mới |
|---|---|---|---|
| **Hero Stage: Live Field Broadside (21:9)** | **What:** Toàn cảnh dòng Cổ Chiên và vương quốc lò gạch Măng Thít.<br>**Where:** $10.254^\circ\text{N}\ 105.972^\circ\text{E}$ bến Cổ Chiên.<br>**When:** Giờ vàng hoàng hôn $17:45$, con nước lớn $+1.42\text{m}$.<br>**Why:** Định danh ngay linh hồn đất và nước Vĩnh Long.<br>**How:** Floating Glass Capsule với Inline Photo Typography. | **Context:** Vùng lõi bãi bồi phù sa sông Tiền.<br>**Material:** Gốm đỏ Măng Thít, đất phù sa.<br>**Machine:** Trạm đo mực nước thủy văn bán nhật triều.<br>**Measurement:** $1.500+$ vòm lò, nhiệt độ $1.100^\circ\text{C}$, nước dâng $+1.42\text{m}$. | Đưa dải Telemetry thủy văn lên góc trên Hero thành **Live Observation Pill**: Khách khảo sát nhìn thấy ngay con nước và giờ vàng nhiếp ảnh. |
| **Bento Portals: 4 Lăng Kính Giác Quan & Địa Tầng** | **What:** 4 cực không gian bản sắc:<br>1. *An Bình:* Sinh thái miệt vườn.<br>2. *Măng Thít:* Vương quốc gốm đỏ.<br>3. *Chùa Âng:* Trầm tích Khmer 1864.<br>4. *Thủy vị:* Ẩm thực cá tai tượng bến sông.<br>**Why:** Phân bổ toàn diện 4 trụ cột văn hóa - sinh thái. | **Material:** Đất sét bãi bồi, dừa nước, cá tai tượng, gỗ sao dầu.<br>**Method:** Nghề nung thủ công, làm vườn truyền thống.<br>**Measurement:** $12^\circ\text{ Brix}$ độ ngọt bưởi, niên đại 1864, $1.500+$ lò nung. | **Gắn thông số đo đạc thực chứng (5M)** trực tiếp lên từng ảnh: Không chỉ ghi tên, mà ghi rõ chỉ số đặc trưng (Brix, niên đại, số lượng lò) giúp giao diện thông minh vượt bậc. |
| **Ký Sự Triptych: Trục Thủy Trình Theo Giờ Thực Địa** | **What:** 3 phóng sự ảnh dọc $3:4$:<br>1. Rạch An Bình ($05:30$ Sáng).<br>2. Lửa gốm Măng Thít ($14:00$ Trưa).<br>3. Đờn kìm bến sông ($19:30$ Tối).<br>**When:** 3 mốc thời gian sống động trong ngày. | **Who:** Tài công ghe tam bản, nghệ nhân lò gạch, nghệ sĩ đờn ca tài tử UNESCO.<br>**Method:** Chèo nương con nước, canh lửa trấu 28 ngày, gảy phím lõm đờn kìm. | **Bổ sung nhãn thời gian thực địa (Time-Stamped Dispatch):** Biến 3 cột ảnh thành một lộ trình nhật ký điền dã có chiều sâu thời gian và cảm xúc. |
| **Tàng Thư 8 Tiêu Bản: Digital Cabinet of Curiosities** | **What:** 8 mẫu vật đại diện cho 5 giác quan Vĩnh Long (Bưởi Năm Roi, Kênh Thầy Cai, Dạ khúc Cổ Chiên, Chôm chôm, Chợ nổi, Bàn xoay gốm, Mái chùa, Men gốm nung). | **Context:** Lưu trữ bảo tàng học thuật.<br>**Measurement:** Mã số hiện vật `[MS: VL-01 ... 08]`.<br>**Method:** Đánh số lưu trữ khoa học. | **Phong cách tủ tiêu bản bảo tàng (Cabinet of Curiosities):** Khung ảnh bo tròn tinh xảo, nhãn kính mờ liquid glass với mã lưu trữ bảo tàng tăng tối đa tính kích thích khám phá. |
| **Dynamic Telemetry Dock: La Bàn Sông Nước** | **What:** Trạm điều khiển dữ liệu khảo cứu thực địa: Mực nước triều, giờ vàng, tọa độ GPS, độ mặn $0.1‰$.<br>**Why:** Cung cấp thông tin sinh tử cho việc đi lại đường sông. | **Machine:** Vệ tinh GPS, cảm biến đo mặn, lịch bán nhật triều.<br>**Context:** Lưu vực sông Tiền - Cổ Chiên. | **Dock nổi than củi bo góc siêu êm:** Đèn xung nhịp thời gian thực, nút tương tác "Tra cứu lịch con nước" chuẩn công thái học. |

---

## Tasks

### Task 1: Tái Thiết Kế & Nâng Cấp Mỹ Học 5W1H2C5M Trên Master HTML

**Files:**
- Modify: `stitch_vinhlong360_visual_first.html`
- Test: `scratch/verify_5w1h2c5m_metrics.py`

**Interfaces:**
- Consumes: Bộ 18 ảnh thực địa đã kiểm định, mã token màu Terroir (Terracotta `#B95F38`, Alluvial `#C99446`, River `#004E74`, Charcoal `#181E28`, Papyrus `#FAF8F5`).
- Produces: Giao diện HTML đẳng cấp bảo tàng, tích hợp Live Observation Pill trên Hero, 5M measurement badges trên Bento, Time-stamped Triptych, Cabinet of Curiosities 8 mẫu vật.

- [ ] **Step 1: Tinh chỉnh Hero Stage với Live Observation Pill & Inline Photo Typography**
  * Nâng cấp tiêu đề H1 Lora với ảnh ghe tam bản inline siêu nét.
  * Tích hợp dải quan sát thực địa trực tiếp trên nóc Hero: `● BẾN CỔ CHIÊN · TRIỀU CƯỜNG +1.42M · GIỜ VÀNG 17:45`.
  * Rút gọn thanh tìm kiếm thành dock xúc giác tối giản với nút gốm nung `#B95F38`.

- [ ] **Step 2: Nâng cấp Bento Matrix với Thông Số Thực Chứng 5M**
  * Thẻ An Bình: Tích hợp badge `ĐỘ NGỌT 12° BRIX · BƯỞI NĂM ROI`.
  * Thẻ Măng Thít: Tích hợp badge `1.100°C · 1.500+ LÒ NUNG CỔ`.
  * Thẻ Chùa Âng: Tích hợp badge `NIÊN ĐẠI 1864 · RỪNG SAO 300 NĂM`.
  * Thẻ Thủy vị: Tích hợp badge `CÁ TAI TƯỢNG XÒE VÂY · CHỢ NỔI TRÀ ÔN`.
  * Giữ $100\%$ ảnh tràn viền, $0$ hộp text trắng.

- [ ] **Step 3: Bổ sung Mốc Thời Gian Điền Dã Vào Ký Sự Triptych**
  * Ký sự 01: `05:30 SÁNG` · Rạch An Bình · Mái dầm nương con nước.
  * Ký sự 02: `14:00 TRƯA` · Lò gốm Măng Thít · Lửa trấu 28 ngày đêm.
  * Ký sự 03: `19:30 TỐI` · Bến Cổ Chiên · Phím lõm đờn ca tài tử.

- [ ] **Step 4: Kiểm định định lượng với verify_5w1h2c5m_metrics.py**
  Run: `python scratch/verify_5w1h2c5m_metrics.py`
  Expected: $\ge 18$ ảnh, $< 200$ từ trong `<main>`, $100\%$ invariants pass.

- [ ] **Step 5: Commit thay đổi Task 1 vào git**
  ```bash
  git add stitch_vinhlong360_visual_first.html
  git commit -m "feat(stitch): elevate master html with 5M metrics and time-stamped triptych"
  ```

---

### Task 2: Kết Xuất Ngoại Tuyến Ảnh Chụp Toàn Cảnh Độ Nét Cao (1409x3600)

**Files:**
- Modify: `scratch/capture_stitch_screen.mjs`
- Create: `stitch_screen_visual_cultural_masterpiece.png`

**Interfaces:**
- Consumes: `stitch_vinhlong360_visual_first.html` nâng cấp.
- Produces: Tệp ảnh `stitch_screen_visual_cultural_masterpiece.png` (kích thước $1.409 \times 3.600$, dung lượng $\approx 3.7\text{ MB}$).

- [ ] **Step 1: Thực thi headless Chrome CDP render**
  Run: `node scratch/capture_stitch_screen.mjs`
  Expected: Kết xuất hoàn tất ảnh chụp toàn trang sắc nét.

- [ ] **Step 2: Kiểm tra kích thước và sao lưu vào brain artifacts**
  Run: `python -c "from PIL import Image; im=Image.open('stitch_screen_visual_cultural_masterpiece.png'); print('Size:', im.size)"`
  Expected: `Size: (1409, ~3600)`.
  Sao lưu vào thư mục brain artifacts.

---

### Task 3: Đồng Bộ Trực Tiếp Vào Cửa Sổ Thứ 3 Trên Google Stitch (Bảo Toàn 3 Cửa Sổ)

**Files:**
- Modify: `scratch/test_batch_create.py`, `scratch/reposition_and_curate_3screens.py`
- Project: `projects/14916181929760067680`

**Interfaces:**
- Consumes: Ảnh kết xuất `stitch_screen_visual_cultural_masterpiece.png`.
- Produces: Màn hình mới trên Google Stitch gắn vào vị trí Cửa sổ thứ 3 tại `(x: 2496, y: 5003)`, ẩn các bản cũ, bảo đảm Canvas có **chính xác 3 cửa sổ**.

- [ ] **Step 1: Tải ảnh chụp mới lên Stitch qua BatchCreateScreens**
  Run: `python scratch/test_batch_create.py`
  Trích xuất mã màn hình mới từ `scratch/last_batch_create_resp.json`.

- [ ] **Step 2: Cập nhật screenInstances qua Stitch REST API**
  Run: `python scratch/reposition_and_curate_3screens.py <NEW_SCREEN_ID>`
  Expected: `Visible screens count after adjustment: 3`.

- [ ] **Step 3: Xác minh trạng thái đám mây qua get_project**
  Xác nhận Project `14916181929760067680` có chính xác 3 màn hình hiển thị.

---

### Task 4: Kiểm Thử Toàn Diện & Hướng Dẫn Nghiệm Thu Thực Tế

**Files:**
- Test: `web-nuxt/tests/home-nocturne-*.test.ts`
- Audit: `python scripts/checks/run_hard.py --staged`

**Interfaces:**
- Consumes: Mã nguồn và Canvas đã đồng bộ.
- Produces: Báo cáo nghiệm thu chi tiết kèm walkthrough.

- [ ] **Step 1: Chạy toàn bộ Vitest suite Nuxt Home Nocturne**
  Run: `npx --prefix web-nuxt vitest run home-nocturne`
  Expected: $4/4$ test files passed ($31/31$ tests passed).

- [ ] **Step 2: Kiểm tra pre-commit hooks**
  Run: `python scripts/checks/run_hard.py --staged`
  Expected: 0 vi phạm.

- [ ] **Step 3: Cập nhật walkthrough và hướng dẫn người dùng nhấn F5 kiểm tra**

---

## Self-Review Checklist

1. **Spec & 5W1H2C5M Coverage:** Mọi thành phần đều có lý do tồn tại rõ ràng, có thông số 5M thực chứng (Brix, độ C, con nước, niên đại, tọa độ GPS).
2. **Anti-Slop:** 0 gradient tím/xanh SaaS, 0 sparkles, 0 text rác, 0 hộp trắng dưới chân ảnh.
3. **Canvas Invariant:** Giữ nguyên chính xác đúng 3 cửa sổ trên Canvas Stitch, không phát sinh cửa sổ thứ 4.
