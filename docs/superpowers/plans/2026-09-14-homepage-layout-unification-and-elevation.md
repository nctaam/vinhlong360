# Kế Hoạch Nghiên Cứu & Nâng Cấp Bố Cục Trang Chủ Nguyên Khối (Homepage Layout Unification & Elevation)

> STATUS: active
> **Mục tiêu tối thượng:** Giải quyết triệt để phản hồi của Chủ dự án: **"bố cục thì sao, quá rời rạc"**, chuyển hóa trang chủ vinhlong360 từ dạng các widget/cards cắt khúc rời rạc thành một **kiến trúc số nguyên khối, liền mạch, đầm chắc (Monolithic Editorial Architecture)** theo chuẩn mực tạp chí văn hóa quốc tế (*Rijksmuseum, Monocle, Visit Oslo*), đồng thời chuẩn hóa ngữ cảnh thực địa theo [anti-ai-writing-style.md](../../claude-desktop/anti-ai-writing-style.md).

---

## 1. Phân Tích Nguyên Nhân Gốc Rễ: Tại Sao Bố Cục Bị Đánh Giá "Quá Rời Rạc"?

Qua việc soi chiếu trực tiếp mã nguồn Nuxt, hệ thống CSS và ảnh chụp thực tế trên trình duyệt Chrome headless (cả Desktop 1440×900 và Mobile 390×844), chúng tôi xác định 5 nguyên nhân cốt lõi gây ra cảm giác "rời rạc, chắp vá":

```
HIỆN TRẠNG (11 DẢI CẮT KHÚC XẾP CHỒNG - STRIP SYNDROME):
┌────────────────────────────────────────────────────────┐
│ Dải 1: Hero (Cột trái trôi tự do vs Cột phải đóng hộp)  │
├────────────────────────────────────────────────────────┤  <- Đường cắt ngang 1px thô ráp
│ Dải 2: Ký sự thổ nhưỡng (Native Stories)              │
├────────────────────────────────────────────────────────┤  <- Khoảng trống 48px + Border
│ Dải 3: Lối rẽ nhanh (H2: Bạn muốn bắt đầu thế nào?)    │
├────────────────────────────────────────────────────────┤  <- Khoảng trống 40px + Border
│ Dải 4: Mục lục (H2: Bạn muốn trải nghiệm gì hôm nay?)  │  <- XUNG ĐỘT: Hỏi 2 lần liên tiếp!
├────────────────────────────────────────────────────────┤
│ Dải 5: Cẩm nang AEO (CatalogAeoPlaque)                 │
├────────────────────────────────────────────────────────┤
│ Dải 6: Đề cử ban biên tập (HomeProductLead)            │
├────────────────────────────────────────────────────────┤
│ Dải 7: Tín hiệu địa phương (Thủy triều, phà, sự kiện)  │  <- Tiện ích thực địa bị giấu tít ở đáy!
├────────────────────────────────────────────────────────┤
│ Dải 8: Sổ vàng OCOP (HomeOcopLedger)                   │
├────────────────────────────────────────────────────────┤
│ Dải 9: Cộng đồng (HomeCommunityFeed)                   │
├────────────────────────────────────────────────────────┤
│ Dải 10: Dành cho bạn (Personalization)                 │
├────────────────────────────────────────────────────────┤
│ Dải 11: Tiếp tục hành trình (Continuation)             │
└────────────────────────────────────────────────────────┘
```

### 1.1. Hội Chứng "Xếp Chồng Dải Ngang" (Horizontal Strip Syndrome)
- Trang chủ hiện có tới **11 dải section độc lập**. Mỗi dải đều mang:
  - Một vùng đệm dọc riêng biệt (`padding-block: 40px - 120px`).
  - Một tiêu đề H2 độc lập (`.section-head` hoặc intro riêng).
  - Một đường viền kẻ ngang (`border-block-end: 1px solid var(--color-border)`).
- Người dùng khi cuộn có cảm giác đang đọc một danh sách 11 widget rời rạc được dán nối tiếp nhau (design-by-components), thiếu hẳn một cấu trúc "chương hồi" có tính liên kết không gian.

### 1.2. Mất Cân Bằng Thị Giác Vùng Hero (Hero Asymmetry & Fragmentation)
- **Cột Trái (`.hero-main`):** Gồm 5 phần tử xếp dọc (Kicker $\to$ H1 $\to$ Subtitle $\to$ Search Autocomplete $\to$ Nút Nearby $\to$ 5 Terroir chips). Tất cả trôi tự do trên nền ảnh phong cảnh mà **không có khung chứa (bounding surface)**.
- **Vết sẹo thị giác `.hero-sub`:** Đoạn mô tả phụ bị áp `background: rgba(0,0,0,0.76)` tạo thành một miếng dán đen hình chữ nhật chắp vá trên nền giấy Parchment sáng (`#F6F4EE`).
- **Cột Phải (`HomeFeatureDossier`):** Một chiếc thẻ đóng hộp cứng cáp, bo viền, có bóng đổ và ảnh lớn. Sự đối lập giữa "bên trái trôi nổi rải rác" và "bên phải đóng hộp nặng trĩu" phá vỡ hoàn toàn trọng tâm thị giác.

### 1.3. Xung Đột Nhận Thức (Cognitive Whiplash) Tại 2 Dải Khám Phá
- Ngay dưới Ký sự thổ nhưỡng, người dùng gặp:
  - **Dải 1 (`HomeDecisionLedger`):** Tiêu đề H2: *"Hôm nay bạn muốn bắt đầu thế nào?"* (4 mốc quyết định).
  - **Dải 2 (`HomeCategoryIndex`):** Tiêu đề H2: *"Bạn muốn trải nghiệm điều gì hôm nay?"* (4 thẻ danh mục + 3 chip tiện ích).
- Hai dải này đặt câu hỏi gần như giống hệt nhau, chiếm gần 900px chiều cao cuộn với 2 tiêu đề H2 tách biệt. Người dùng cảm thấy bị tra vấn liên tục và rối loạn điều hướng!

### 1.4. Tín Hiệu Thực Địa Độc Bản Bị Đẩy Xuống Đáy Trang
- Dữ liệu độc bản và hữu ích nhất của Vĩnh Long đối với du khách: **Nhịp triều sông Cổ Chiên, lịch phà An Bình, thời tiết vi khí hậu** lại bị đẩy xuống tận Dải thứ 7 (`HomeSignals`), thay vì nằm ở ngay cửa trước để hỗ trợ du khách ra quyết định tức thì.

### 1.5. Lệch Ngữ Cảnh Địa Phương Theo [anti-ai-writing-style.md](../../claude-desktop/anti-ai-writing-style.md)
- Tiêu đề Hero hiện tại: *"Trung thu miền Tây, đèn lồng và bánh dân gian"*. Từ *"miền Tây"* vi phạm trực tiếp §2 của Hiến pháp văn phong (Cấm từ chung chung, phải dùng danh từ riêng thực địa: Cổ Chiên / Măng Thít / An Bình).

---

## 2. Mô Hình Kiến Trúc Mới: "Giao Hưởng 3 Hồi" (3-Act Symphonic Architecture)

Thay vì chia làm 11 dải cắt khúc, trang chủ được quy hoạch lại thành **3 Hồi Không Gian Nguyên Khối**:

```
KIẾN TRÚC MỚI (3 HỒI NGUYÊN KHỐI - BENTO MASTER):
┌────────────────────────────────────────────────────────────────────────┐
│ HỒI 1: CỬA NGÕ THỰC ĐỊA & BUỒNG LÁI HÀNH TRÌNH (HERITAGE COCKPIT)      │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ [Măng-sét Âm/Dương] + [Tín hiệu Sông Cổ Chiên: Triều lớn 16:30]   │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────┬───────────────────────────────┐ │
│ │ BUỒNG LÁI TƯƠNG TÁC (60%)          │ TIÊU ĐIỂM THỰC ĐỊA (40%)      │ │
│ │ • H1: Trung thu Cổ Chiên…          │ Thẻ Hồ sơ Cua cốm / Điểm đến  │ │
│ │ • [CONSOLE KÍNH LỎNG TINH THỂ]:    │ Cân bằng baseline hoàn hảo     │ │
│ │   ┌──────────────────────────────┐ │ với Buồng lái bên trái.       │ │
│ │   │ [Search] + [Tìm quanh tôi]   │ │                               │ │
│ │   ├──────────────────────────────┤ │                               │ │
│ │   │ [5 Chip Thổ Nhưỡng Neo Đậu]  │ │                               │ │
│ │   └──────────────────────────────┘ │                               │ │
│ └────────────────────────────────────┴───────────────────────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Dải chuyển tiếp nhịp phù sa mềm)
┌───────────────────────────────────▼────────────────────────────────────┐
│ HỒI 2: TỔ HỢP KHÁM PHÁ BENTO NGUYÊN KHỐI (UNIFIED EXPLORATION COMPLEX) │
│ H2 Chung Duy Nhất: "ĐỊNH HƯỚNG BẢN ĐỊA · Hôm nay ở Vĩnh Long có gì?"   │
│ ┌────────────────────────────────────┬───────────────────────────────┐ │
│ │ TRỤC NHỊP SỐNG HÔM NAY (38%)       │ 4 CỔNG TRẢI NGHIỆM (62%)      │ │
│ │ (Timeline 4 mốc thời gian thực):   │ [Du lịch]       [Ẩm thực]     │ │
│ │ • Mai: Hội Thanh Trà               │ [Gốm đỏ OCOP]   [Lễ hội]      │ │
│ │ • T9: Chuột đồng nướng             ├───────────────────────────────┤ │
│ │ • 4.9★: Bánh Canh Vịt Cô Diễm      │ 3 TIỆN ÍCH HÀNH TRÌNH (CHIPS) │ │
│ │ • Gợi ý: Lộ trình xanh             │ [Lưu trú] [Lịch trình] [Bản đồ│ │
│ └────────────────────────────────────┴───────────────────────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Chảy tiếp vào chiều sâu văn hóa)
┌───────────────────────────────────▼────────────────────────────────────┐
│ HỒI 3: KÝ SỰ VĂN HÓA, THỔ NHƯỠNG & CỘNG ĐỒNG (TERROIR & SIGNALS)       │
│ • Ký sự phù sa (Stories) kết hợp Đề cử Biên tập (Editorial Pick)       │
│ • Sổ vàng OCOP làng nghề gốm đỏ & đặc sản bản địa                      │
│ • Tiếng nói người đi trước (Community Feed) & Thanh tiếp tục hành trình│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. User Review Required

> [!IMPORTANT]
> **Các quyết định thiết kế then chốt cần Chủ dự án chuẩn y:**
> 1. **Gom cụm Hero thành "Console Kính Lỏng" (Liquid Glass Console):**
>    - Bỏ vĩnh viễn khối nền đen `.hero-sub` trong light mode (xóa bỏ vết sẹo thị giác).
>    - Tích hợp thanh tìm kiếm, nút "Tìm quanh tôi" và các chip địa danh vào **một bề mặt kính lỏng (Liquid Glass Deck)** có bo góc 16px, viền mờ `var(--border-liquid-glass)` và chiều cao cân bằng với thẻ tiêu điểm bên phải.
> 2. **Hợp nhất `Decision Ledger` & `Category Index` thành "Tổ Hợp Khám Phá Bento Nguyên Khối":**
>    - Xóa bỏ 2 tiêu đề H2 độc lập đang gây tranh chấp và khoảng trống đệm 500px thừa.
>    - Dùng 1 khung Bento 2 cánh: Cánh trái 38% cho Trục Nhịp sống hôm nay, Cánh phải 62% cho Lưới trải nghiệm và Tiện ích.
> 3. **Đưa Tín Hiệu Dòng Nước Lên Cửa Trước (Masthead Real-time Pulse):**
>    - Đưa nhịp triều sông Cổ Chiên và vi khí hậu tức thì (ví dụ: `🌊 Triều lớn 16:30 · 29°C ven Cổ Chiên`) lên dải măng-sét đầu trang cạnh ngày âm lịch.
> 4. **Chuẩn Hóa Tiêu Đề Hero Theo [anti-ai-writing-style.md](../../claude-desktop/anti-ai-writing-style.md):**
>    - Đổi *"Trung thu miền Tây, đèn lồng và bánh dân gian"* thành **`"Trung thu Cổ Chiên, đèn lồng và bánh dân gian"`**.

---

## 4. Chi Tiết Kỹ Thuật & Kế Hoạch Triển Khai

### Task 1: Tái Cấu Trúc Khối Hero Thành "Console Kính Lỏng" (Unified Action Deck)
**Mục đích:** Xóa bỏ cảm giác các phần tử Hero rơi tự do, loại bỏ miếng dán đen `.hero-sub`, đưa tìm kiếm và chips vào một bề mặt thống nhất.

**Files:**
- Modify: `web-nuxt/pages/index.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-hero-dossier-polish.test.ts`

- [ ] **Step 1: Viết test kiểm tra cấu trúc `.hero-action-deck` và khử nền đen `.hero-sub`**
- [ ] **Step 2: Chạy test xác nhận FAIL**
- [ ] **Step 3: Cập nhật template `pages/index.vue`:**
  - Bọc `SearchAutocomplete`, `.hero-nearby`, và `.hero-terroir-chips` vào `<div class="hero-action-deck">`.
  - Cập nhật tiêu đề seasonalTagline sang `"Trung thu Cổ Chiên, đèn lồng và bánh dân gian"` theo `anti-ai-writing-style.md`.
- [ ] **Step 4: Cập nhật CSS trong `home-nocturne.css`:**
  - Định nghĩa `.hero-action-deck`: bề mặt kính lỏng bán trong suốt, bo góc 16px, viền `var(--border-liquid-glass)`, đổ bóng ambient nhẹ.
  - Sửa `.hero-sub`: Bỏ `background: var(--home-color-on-media-plate)` trong light mode, dùng màu chữ hòa sắc `color-mix(in srgb, var(--color-text) 88%, transparent)`.
- [ ] **Step 5: Chạy test xác nhận PASS**
- [ ] **Step 6: Commit:** `git commit -m "feat(home): unify hero interaction deck with liquid glass surface and authentic Cổ Chiên dateline"`

---

### Task 2: Hợp Nhất `Decision Ledger` & `Category Index` Thành "Tổ Hợp Khám Phá Bento"
**Mục đích:** Khắc phục tình trạng 2 section nối đuôi nhau với 2 tiêu đề h2 rời rạc, gom thành 1 tổ hợp khám phá cân xứng.

**Files:**
- Modify: `web-nuxt/pages/index.vue`
- Modify: `web-nuxt/components/home/HomeDecisionLedger.vue`
- Modify: `web-nuxt/components/home/HomeCategoryIndex.vue`
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- New Test: `web-nuxt/tests/home-unified-exploration.test.ts`

- [ ] **Step 1: Viết test mới `home-unified-exploration.test.ts`**
- [ ] **Step 2: Chạy test xác nhận FAIL**
- [ ] **Step 3: Tinh chỉnh `HomeDecisionLedger.vue` và `HomeCategoryIndex.vue`:**
  - Bổ sung prop `:compact-header="true"` để không sinh ra 2 tiêu đề h2 trùng lặp khi nằm trong cùng một tổ hợp.
  - Cho phép hiển thị tiêu đề hợp nhất: *"ĐỊNH HƯỚNG BẢN ĐỊA · Hôm nay ở Vĩnh Long có gì?"*.
- [ ] **Step 4: Cập nhật CSS trong `home-nocturne.css`:**
  - Tạo khung `.home-exploration-complex`: Một khung bề mặt lớn có viền mờ `Liquid Glass`, nền hòa sắc vi khí hậu nhẹ (`color-mix`), ôm trọn cả trục timeline lối rẽ nhanh và 4 cánh cổng danh mục.
  - Trên desktop $\ge 1024\text{px}$: Layout Bento 2 cột cân xứng (Cột trái 38% cho Timeline sự kiện/mùa vụ, Cột phải 62% cho Lưới trải nghiệm).
- [ ] **Step 5: Chạy test xác nhận PASS**
- [ ] **Step 6: Commit:** `git commit -m "refactor(home): consolidate decision ledger and category index into unified bento exploration complex"`

---

### Task 3: Kết Nối Chuyển Tiếp Nhịp Thở Phù Sa (Spatial Rhythm & Grounding)
**Mục đích:** Triệt tiêu khoảng trống đứt gãy giữa Hero $\to$ Exploration Complex $\to$ Story Spread.

**Files:**
- Modify: `web-nuxt/assets/css/home-nocturne.css`
- Test: `web-nuxt/tests/home-layout-asymmetry.test.ts`

- [ ] **Step 1: Viết test kiểm tra dải chuyển tiếp phù sa**
- [ ] **Step 2: Chạy test xác nhận**
- [ ] **Step 3: Cập nhật CSS:**
  - Tinh chỉnh `padding-block` từ khoảng cách ngẫu hứng sang tỷ lệ nhịp vàng: 48px trên desktop, 32px trên mobile.
  - Thêm hiệu ứng dải chuyển sắc mềm (alluvial river gradient) kết nối êm ái giữa Hero và Exploration Complex.
- [ ] **Step 4: Chạy test xác nhận PASS**
- [ ] **Step 5: Commit:** `git commit -m "style(home): establish organic alluvial rhythm and eliminate abrupt sectional gaps"`

---

### Task 4: Kiểm Thử Trực Quan Bằng Chrome & Nghiệm Thu Pháp Y
**Mục đích:** Mở Chrome headless qua script CDP, chụp lại bộ ảnh mới để so sánh trực quan Before / After.

- [ ] **Step 1: Chạy toàn bộ 21 suites kiểm thử trang chủ:**
  `npx vitest run tests/home-` (bảo đảm 100% PASS).
- [ ] **Step 2: Kiểm tra nợ màu sắc và kiểu dữ liệu:**
  - `node scripts/check-tri-region-color-debt.mjs` (0 nợ màu).
  - `npm run typecheck` (0 errors).
- [ ] **Step 3: Chụp ảnh trực quan Before / After qua Chrome CDP:**
  Chụp lại `01_hero_masthead_unified.png` và `02_exploration_bento.png`.
- [ ] **Step 4: Cập nhật walkthrough và báo cáo người dùng.**

---

## 5. Verification Plan

### Automated Tests
- `npx vitest run tests/home-` (Toàn bộ 21 suites trang chủ).
- `node scripts/check-tri-region-color-debt.mjs` (0 token debt).
- `npm run typecheck` (TypeScript Nuxt clean).
- `python scripts/checks/run_hard.py` (Pre-commit hook 0 hard violations).

### Visual & Manual Verification
- Chụp ảnh Chrome ở độ phân giải 1440×900 (Desktop) và 390×844 (Mobile).
- So sánh trực tiếp: Khối Hero không còn rơi rụng tự do; Exploration Complex trở thành 1 khối Bento cân đối, đẳng cấp.
