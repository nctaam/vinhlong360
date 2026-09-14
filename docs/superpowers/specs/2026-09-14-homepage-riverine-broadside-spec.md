# Đặc Tả Kiến Trúc Giao Diện: Kỳ Đài Sông Nước Nam Bộ (Riverine Living Broadside Spec)

> STATUS: active
> **Mã định danh:** `SPEC-2026-09-14-RIVERINE-BROADSIDE-V1`  
> **Dự án:** VinhLong360 (`web-nuxt` & Google Stitch `projects/14916181929760067680`)  
> **Quy chuẩn:** 5W1H2C5M · Zero AI-Slop · Anti-Skeuomorphic Kitsch · Living Riverine Journal

---

## 1. Khung Phân Tích & Phản Biện Toàn Diện 5W1H2C5M

### 1.1. WHY (Tại sao cần bản thiết kế mới này?)
* **Căn nguyên thất bại của các bản cũ:**
  1. *Bản 1 (Bento SaaS):* Bị "Tây hóa", giống dashboard phần mềm quản trị; các ô bo góc xám đen làm nguội lạnh toàn bộ cảm xúc về miền Tây.
  2. *Bản 2 (Cockpit 8.426px & Răng cưa):* Rơi vào bẫy "bội thực chi tiết & hoài cổ giả cầy". Răng cưa bưu chính là chi tiết rườm rà (visual noise); telemetry buồng lái hàng hải biến trang chủ thành công cụ chuyên ngành đo đạc tàu bè gây ngột ngạt.
  3. *Bản 3 (Phòng tranh cực đoan):* Quá trống trải, trắng bóc, biến không gian thành một phòng triển lãm châu Âu lạnh lùng, thiếu sức sống của dòng sông phù sa.
* **Mục tiêu tối hậu:** Tạo ra một **Ấn bản Kỳ Đài Sông Nước Nam Bộ** sống động, ấm áp, trang trọng, vừa vặn độ dài ($3.800\text{px} - 4.000\text{px}$), mang tinh thần điền dã của Sơn Nam: *chân thực, hữu ích, không màu mè giả tạo*.

### 1.2. WHAT (Bản thiết kế này chứa đựng những gì?)
* Bố cục 4 Màn (4-Act Broadside) với tỷ lệ vàng bất đối xứng $4:6$:
  * **Màn 1: Masthead Sông Tiền & Dòng Sông Khởi Điểm:** Khung tìm kiếm chìm nhẹ vào ảnh hoàng hôn Cổ Chiên; tiêu điểm độc bản hôm nay: *Vương quốc Gốm đỏ Măng Thít*.
  * **Màn 2: Bộ Tứ Không Gian Điền Dã (The 4 Terroir Pillars):** 4 cụm văn hóa nền tảng (Cù lao An Bình, Gốm nung Măng Thít, Trầm tích Khmer & Đình làng, Bến sông Chợ nổi).
  * **Màn 3: Ký Sự Thực Địa Phù Sa (Sediment Field Dispatches):** 3 bài viết thực chứng, ảnh lớn khổ ngang, trích dẫn văn học, triệt tiêu 100% văn mẫu du lịch.
  * **Màn 4: Cẩm Nang Đi Sông & Chân Trang Tri Ân (Quiet River Guide Footer):** 1 dòng tóm tắt con nước lớn/ròng thực tế trong ngày, bản đồ trạm dừng, hotline cứu hộ luồng lạch.

### 1.3. WHO (Phục vụ ai?)
* **Người dùng cốt lõi:** Lữ khách văn hóa, nhà nghiên cứu, du khách tìm kiếm chiều sâu bản địa và cư dân địa phương. Họ cần cảm xúc tự hào, sự tin cậy và thông tin thực chứng ngay lập tức.

### 1.4. WHERE (Vị trí & Không gian cảm xúc)
* Không gian kỹ thuật số mô phỏng chất liệu **giấy in báo văn hóa Nam Bộ xưa pha nét hiện đại** (Warm Newsprint Paper `#FAF8F5`), với mực than tự nhiên (`#181E28`), vệt son đất nung Măng Thít (`#B95F38`) và dải nước sông Cổ Chiên chiều buông (`#004E74`).

### 1.5. WHEN (Nhịp thời gian & Thời điểm tiếp cận)
* Thiết kế thích ứng theo chu kỳ con nước Bán nhật triều 24 giờ và Tiết khí 12 tháng của miền Tây Nam Bộ.

### 1.6. HOW (Thi công như thế nào?)
* Không dùng viền răng cưa giả cổ. Dùng đường gióng thẳng đơn giản (1px hairline `#E2D9CC`).
* Bố cục chữ: Tiêu đề dùng font có chân trang nhã (Lora / EB Garamond), thân bài dùng sans-serif rõ dấu tiếng Việt (Be Vietnam Pro / Plus Jakarta Sans).
* Khoảng thở âm (negative space) chiếm tối thiểu $40\%$, không bị chia cắt vụn vỡ.

### 1.7. 2C (Controls & Constraints)
* **Control (Kiểm soát):** Chiều cao cố định $\le 4.200\text{px}$. Tỷ lệ tương phản màu WCAG $\ge 7:1$ (AAA).
* **Constraints (Ràng buộc):** Không thêm route, không thêm package, không phát sinh media debt (0 audio/video), 100% test Vitest PASS.

### 1.8. 5M (Resources & Capabilities)
* **Manpower:** Tư duy biên tập của nhà nghiên cứu văn hóa kết hợp kỹ sư frontend.
* **Machine:** Google Stitch MCP Engine + Nuxt 3 Engine.
* **Material:** Hệ thống token màu Tam Vùng (Tri-region Design Tokens).
* **Method:** Subagent-Driven Development (SDD) kết hợp Test-Driven Development (TDD).
* **Measurement:** Thước đo trực quan (Stitch render) + Thước đo mã nguồn (104 tests pass).

---

## 2. Hệ Thống Design Tokens Chuẩn (Design Language)

```css
:root {
  /* Canvas Substrate - Đất và Giấy ngà phù sa */
  --canvas-bg: #FAF8F5;
  --canvas-surface: #FFFFFF;
  --canvas-subtle: #F3ECE2;
  --canvas-border: #E5DDD0;
  
  /* Pigments - Màu sắc Thổ nhưỡng Vĩnh Long */
  --pigment-terracotta: #B95F38; /* Đỏ gốm Măng Thít */
  --pigment-terracotta-dark: #8E3E1E;
  --pigment-river-azure: #004E74; /* Xanh thẳm Cổ Chiên */
  --pigment-river-light: #E1F0F8;
  --pigment-silt-gold: #C99446;   /* Vàng phù sa bãi bồi */
  
  /* Ink & Legibility - Mực than in chữ */
  --ink-primary: #181E28;   /* Mực đen than sâu */
  --ink-secondary: #4A5568; /* Mực khói ghi chép */
  --ink-muted: #718096;     /* Ghi chú tọa độ, số lưu trữ */
  
  /* Typography Hierarchy */
  --font-display: 'Lora', 'EB Garamond', serif;
  --font-sans: 'Be Vietnam Pro', 'Plus Jakarta Sans', sans-serif;
}
```

---

## 3. Cấu Trúc Chi Tiết 4 Phân Đoạn (Layout Architecture)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ ACT 1: RIVER HORIZON HERO & MASTHEAD (Cao ~900px)                               │
│ [Thương hiệu VINHLONG360 thanh nhã] · [Tọa độ GNSS 10.254°N · 105.972°E]        │
│ "KỲ ĐÀI SÔNG NƯỚC NAM BỘ: ĐẤT BÃI BỒI, DÒNG THỦY TRÌNH & VƯƠNG QUỐC GỐM ĐỎ"      │
│ Thanh tìm kiếm thông minh tự nhiên chìm nhẹ vào cảnh quan                       │
│ Feature Spotlight bên phải: Lò nung Măng Thít (Ảnh đứng, chú thích điền dã)     │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ACT 2: BỘ TỨ KHÔNG GIAN ĐIỀN DÃ (Cao ~1.100px)                                  │
│ Kicker: "KHẢO CỨU THỰC ĐỊA BỐN PHƯƠNG TRỜI"                                    │
│ 4 Khối tỷ lệ vàng 2x2 bất đối xứng thoáng đãng, đường cắt thẳng, KHÔNG RĂNG CƯA: │
│ 01. Miệt Vườn Cù Lao An Bình      │ 02. Vương Quốc Lò Gạch Măng Thít            │
│ 03. Trầm Tích Khmer & Đình Miếu   │ 04. Ẩm Thực Bến Sông & Chợ Nổi              │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ACT 3: ẤN BẢN KÝ SỰ PHÙ SA (Cao ~1.200px)                                       │
│ Kicker: "KÝ SỰ THỰC ĐỊA · TRÍCH LỤC SƠN NAM & GIA ĐỊNH THÀNH THÔNG CHÍ"         │
│ 3 Khối bài viết chiều sâu, ảnh lớn ngang, trích dẫn văn học thực tế:            │
│ 1. Nhịp chèo trên rạch An Bình: Nghệ thuật rẽ nước của ghe tam bản             │
│ 2. Trăm năm giữ lửa Măng Thít: Hồn đất nung bên dòng kênh Thầy Cai             │
│ 3. Vị dừa sáp Cầu Kè & tiếng đàn kìm đêm rằm bến sông                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│ ACT 4: CẨM NANG HÀNH TRÌNH BỎ TÚI & CHÂN TRANG (Cao ~600px)                     │
│ Dòng tóm lược con nước trong ngày: "Hôm nay nước lớn lúc 16:30 (+1.42m)"        │
│ Chỉ dẫn trạm đò ngang · Hotline cứu hộ luồng lạch 24/7 (1800 6836) · Bản quyền  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Prompt Chuẩn Bị Cho Google Stitch MCP

```markdown
Create a breathtaking, ultra-refined, authentic editorial homepage for "VinhLong360 - Kỳ Đài Sông Nước Nam Bộ" (Riverine Living Broadside Masterpiece). 

DESIGN PHILOSOPHY:
- Pure living riverine broadside journal, reminiscent of an esteemed cultural monograph.
- ABSOLUTELY NO SKEUOMORPHIC STAMP PERFORATIONS (no "răng cưa"), NO heavy black SaaS bento cards, NO nautical cockpit gauges, NO AI clichés.
- High negative space (>= 40% open breathing canvas).
- Clean hairlines (1px solid #E5DDD0), asymmetric 12-column grid, disciplined editorial pacing.
- Warm paper canvas (#FAF8F5), Mang Thit terracotta red (#B95F38), deep river azure (#004E74), deep charcoal ink (#181E28).
- Typography: Lora serif headlines, Be Vietnam Pro / Newsreader body copy, Plus Jakarta Sans uppercase tracked labels.

SECTIONS TO INCLUDE (Max height 3900px):
1. THE RIVER MASTHEAD & HORIZON (Desktop 1200px+):
   - Elegant minimal masthead: "VINHLONG360" in stately Lora serif, coordinates "10.254° N · 105.972° E · Sông Cổ Chiên", subtle date stamp.
   - Headline: "Đất Bãi Bồi Phù Sa, Thủy Trình Sông Lớn & Di Sản Trăm Năm".
   - Seamless floating search input with light borders and terracotta button: "Tìm theo điểm đến, món ngon, con nước..."
   - Right-side vertical editorial photo plate: The majestic red brick kilns of Mang Thit along Thay Cai canal, framed cleanly with zero shadows.

2. THE FOUR TERROIR QUADRANTS (Bộ Tứ Không Gian Văn Hóa):
   - Kicker: "KHẢO CỨU THỰC ĐỊA · 4 TIỂU VÙNG ĐẶC TRƯNG".
   - 4 asymmetric rectangular plates with generous whitespace:
     * 01 / Miệt Vườn Cù Lao An Bình (Fruit orchards, pomelo, fresh canal channels)
     * 02 / Vương Quốc Gốm Đỏ Măng Thít (Centuries-old brick kilns, red clay terroir)
     * 03 / Trầm Tích Khmer & Đình Miếu (Ancient Khmer pagodas, Van Thanh Mieu)
     * 04 / Hương Vị Bến Sông & Chợ Nổi (Tra On floating market, freshwater fish)
   - Each card has accession index, clear photo, title in Lora, short poetic field note, and minimal text link "Khám phá thực địa →".

3. SEDIMENT FIELD DISPATCHES (Ký Sự Điền Dã Thực Địa):
   - Kicker: "BÚT KÝ BẢN ĐỊA · GHI CHÉP TỪ DÒNG NƯỚC".
   - 3 generous horizontal article spreads:
     * "Nhịp chèo rạch An Bình: Nghệ thuật rẽ nước dòng Tiền Giang" (With boatman quote)
     * "Ngọn lửa nung đất Măng Thít: Kỹ nghệ tạo tác gốm đỏ phù sa" (With artisan name)
     * "Tiếng đàn kìm đêm rằm Cù Lao: Âm vang đờn ca tài tử bờ sông" (With music heritage note)
   - Layout: alternating clean image-left, text-right with ample margins.

4. QUIET FIELD GUIDE FOOTER:
   - Subtle 1-line tide summary: "Thủy triều hôm nay: Nước lớn 16:30 (+1.42m) · Nước ròng 10:15 (+0.28m) · Phù hợp chèo ghe và tham quan cồn bãi."
   - Editorial directory, emergency river hotline (1800 6836), and archival copyright note.
```
