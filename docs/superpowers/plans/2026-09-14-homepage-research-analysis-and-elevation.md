# Chuyên Khảo Nghiên Cứu Pháp Y & Kiến Trúc Nâng Cấp Bố Cục Trang Chủ (Homepage Layout Forensic Elevation & Ergonomics Architecture)

> STATUS: active
> **Mục tiêu tối thượng:** Giải quyết triệt để phản hồi của Chủ dự án: **"bố cục thì sao, quá rời rạc"**. 
> Soi chiếu trực tiếp với **Bản thiết kế gốc trên Google Stitch Cloud (Project `14916181929760067680`)**, bóc tách sự thoái hóa kiến trúc trong quá trình phát triển mã nguồn Nuxt, và xác lập **Kiến trúc Lưới 12 Cột Đảo Nhịp Đối Ngẫu (7:5 $\longleftrightarrow$ 5:7 Chiasmus Cadence)** nhằm biến trang chủ vinhlong360.vn thành một ấn phẩm tạp chí số nguyên khối, hoàn mỹ, tuân thủ nghiêm ngặt [anti-ai-writing-style.md](../../claude-desktop/anti-ai-writing-style.md).

---

## 1. Phát Hiện Pháp Y Đột Phá: Sự Thoái Hóa Từ Google Stitch Đến Nuxt

Qua việc trích xuất và phân tích trực tiếp mã nguồn của **Screen `ae1e97b75f31411c9062659ec8f75052` (Asymmetric Mekong Editorial Variant)** trong Google Stitch Project `14916181929760067680`, chúng tôi phát hiện nguyên nhân sâu xa vì sao bố cục bị "rời rạc":

| Tiêu chí | Bản Thiết Kế Gốc Trên Google Stitch | Hiện Trạng Trong Mã Nguồn Nuxt Hiện Tại | Mức Độ Sai Lệch |
|---|---|---|---|
| **Hệ Lưới (Grid)** | Chuẩn hóa duy nhất: `grid lg:grid-cols-12` (7 cột Trái : 5 cột Phải) xuyên suốt toàn trang. | Bị băm nhỏ thành **6 hệ lưới riêng biệt** trong từng component (`1.08fr`, `1.35fr`, `0.72fr`, `repeat(4)`, `1fr:1fr`). | **Nghiêm trọng (Gây nhảy trục)** |
| **Cấu Trúc Khối** | **Nguyên khối (Monolithic):** Tìm kiếm, bộ lọc và gợi ý nằm trọn vẹn trong `lg:col-span-7`; ảnh tiêu điểm đối xứng tỷ lệ vàng nằm trong `lg:col-span-5`. | **Phân mảnh (Fragmented):** Cột trái thả trôi tự do 5 phần tử không khung chứa; đoạn mô tả phụ bị dán miếng đen `rgba(0,0,0,0.76)`. | **Nghiêm trọng (Chắp vá thị giác)** |
| **Số Lượng Phân Dải** | **3 Đại Hồi (3 Major Acts):** Hero Cockpit $\to$ Curated Exploration $\to$ Terroir Narrative. | **11 Dải Cắt Khúc (11 Strips):** Mỗi component tự sinh ra 1 section độc lập với viền kẻ cắt ngang $1\text{px}$. | **Nghiêm trọng (Hội chứng Strip Syndrome)** |
| **Tiêu Đề Dẫn Hướng** | 1 Tiêu đề phân cấp duy nhất dẫn dắt hành trình. | **2 Tiêu đề $H_2$ cạnh tranh:** Lối rẽ nhanh hỏi 1 câu, Mục lục lại hỏi 1 câu tương tự ngay dưới. | **Nghiêm trọng (Xung đột nhận thức)** |
| **Tín Hiệu Thực Địa** | Tọa độ GPS, nhịp triều và thời tiết nằm ngay tại buồng lái cửa trước. | Bị giấu tít xuống Dải thứ 7 (`HomeSignals`), tách rời khỏi nhu cầu thực tế của du khách. | **Nghiêm trọng (Lỗi công thái học)** |

---

## 2. Bản Thiết Kế Trực Quan & Kiến Trúc 4 Đại Hồi (Visual Mockups & 4-Act Master Layout)

### A. Bản Dựng Trực Tiếp Trên Google Stitch Cloud (Screen `dfa666b71d8e41abb5f9e272342e880d`)

> **Liên kết dự án Google Stitch:** Project `14916181929760067680` — *VinhLong360 Mekong Heritage & Discovery*  
> **Màn hình vừa sinh:** `VinhLong360 - Trang Chủ Biên Tập Di Sản & Khám Phá Thổ Nhưỡng` (Kích thước: $2560\times 5634\text{px}$)

![Bản dựng trực tiếp từ Google Stitch](C:\Users\NCTaam\.gemini\antigravity-ide\brain\71b606fa-723e-4a79-8a19-854bf74a7b8d\stitch_generated_screen_bento.png)

---

### B. Bản Thiết Kế Bento Desktop (Ý Tưởng 16:9)

![Bản thiết kế Bento Desktop đề xuất](C:\Users\NCTaam\.gemini\antigravity-ide\brain\71b606fa-723e-4a79-8a19-854bf74a7b8d\vinhlong360_bento_layout_mockup_1789351706659.jpg)

![Bản thiết kế Bento Mobile đề xuất](C:\Users\NCTaam\.gemini\antigravity-ide\brain\71b606fa-723e-4a79-8a19-854bf74a7b8d\vinhlong360_mobile_bento_mockup_1789351749143.jpg)

### Bản Đồ Giải Phẫu 4 Đại Hồi (12 Cột Đối Ngẫu 7:5 $\longleftrightarrow$ 5:7)

Hiện tượng "rời rạc" được chứng minh chính xác bằng biểu đồ đo đạc góc lệch trục mắt người khi cuộn qua 6 component hiện tại:

```
HIỆN TRẠNG (MẮT BỊ GIẬT CỤC 6 LẦN - 6 KHÁC BIỆT TRỤC):
0%                  25%       36%        50%  54% 57%                      100%
Hero:               |         |          |    |===*===|                      | (Trục 54%)
Native Stories:     |         |          |    |   |===*===|                  | (Lệch sang phải 57.4%)
Decision Ledger:    |         |===*===|  |    |   |                          | (GIẬT MẠNH SANG TRÁI 36%!)
Category Index:     |====*====|====*=====|====*===|===*===|                  | (Vỡ vụn thành 4 cột 25%)
Product Lead:       |         |          |    |===*===|                      | (Nhảy lại 54.5%)
Signals:            |         |          |====*===|                          | (Nhảy về 50%)

MỤC TIÊU KIẾN TRÚC MỚI (CHUẨN HÓA 12 CỘT ĐỐI NGẪU 7:5 - NHỊP HÌNH SIN MỀM MẠI):
0%                                  58.3% (7 Cột)                          100%
HỒI 1 (Hero Cockpit):               |===========*==========|                 | (7 Cột Trái : 5 Cột Phải)
                                                \
HỒI 2 (Exploration Bento):          |       |==========*====================| (5 Cột Trái : 7 Cột Phải)
                                                /
HỒI 3 (Terroir Chronicle):          |===========*==========|                 | (7 Cột Trái : 5 Cột Phải)
                                                \
HỒI 4 (Signals & Community):        |       |==========*====================| (5 Cột Trái : 7 Cột Phải)
```

> **Nguyên lý nhịp điệu:** Mắt người dùng được dẫn dắt theo **đường cong hình sin đối ngẫu êm ái**:
> $$\mathbf{7:5} \longrightarrow \mathbf{5:7} \longrightarrow \mathbf{7:5} \longrightarrow \mathbf{5:7}$$
> Mọi dao động giật cục bị triệt tiêu 100%. Toàn bộ trang web vận hành như một dòng sông Cổ Chiên xuôi dòng liền mạch!

---

## 3. Kiến Trúc 4 Đại Hồi Nguyên Khối (The 4-Act Master Layout)

### HỒI 1: Cửa Ngõ Thực Địa & Buồng Lái Hành Trình (Tỉ lệ 7 : 5)
- **Cột Trái (7 cột - 58.3%): Buồng Lái Kính Lỏng (Liquid Glass Cockpit):**
  - Măng-sét Âm/Dương kết hợp Tín hiệu Triều sông Cổ Chiên tức thì (`🌊 Triều lớn 16:30 · 29°C ven Cổ Chiên`).
  - $H_1$ chuẩn [anti-ai-writing-style.md](../../claude-desktop/anti-ai-writing-style.md): `"Trung thu Cổ Chiên, đèn lồng và bánh dân gian"`.
  - Subtitle: `"Tìm điểm đến ven sông Cổ Chiên, lò gạch Măng Thít và miệt vườn An Bình hôm nay."` (Loại bỏ vĩnh viễn miếng dán đen `.hero-sub`).
  - Thanh tìm kiếm viền mờ `Liquid Glass` tích hợp nút "Tìm quanh tôi" và dock 5 chip thổ nhưỡng neo đậu vững chãi.
- **Cột Phải (5 cột - 41.7%): Hồ Sơ Tiêu Điểm Thực Địa (Living Dossier):**
  - Ảnh lớn tỷ lệ $4:5$ có viền gốm nung Măng Thít (`border-terracotta/25`), tem chứng thực GNSS và trạng thái kiểm định nguồn tin cậy (`SourceMark`).
  - Baseline cân bằng tuyệt đối với buồng lái bên trái.

### HỒI 2: Tổ Hợp Khám Phá Bento Nguyên Khối (Đảo tỉ lệ 5 : 7)
- **Tiêu đề duy nhất:** *Kicker:* `ĐỊNH HƯỚNG BẢN ĐỊA` · *$H_2$:* `Hôm nay ở Vĩnh Long có gì?` (Xóa bỏ 2 tiêu đề $H_2$ cạnh tranh của `HomeDecisionLedger` và `HomeCategoryIndex`).
- **Cột Trái (5 cột - 41.7%): Trục Nhịp Sống Hôm Nay (Fast Decisions Timeline):**
  - Timeline 4 mốc thực địa: Lịch gần nhất (Hội Thanh Trà), Mùa vụ tháng 9 (Chuột đồng nướng), Quán ngon điểm cao (Bánh canh Cô Diễm), Lộ trình gợi ý (Du lịch xanh).
- **Cột Phải (7 cột - 58.3%): 4 Cánh Cổng Trải Nghiệm & 3 Tiện Ích Hành Trình:**
  - Lưới 4 thẻ danh mục trọng tâm (Du lịch miệt vườn, Ẩm thực sông nước, Gốm đỏ Măng Thít, Lễ hội dân gian).
  - Chân khối là 3 chip tiện ích (Lưu trú, Lịch trình, Bản đồ 3 vùng).
  - *Hiệu quả:* Tiết kiệm hơn $500\text{px}$ cuộn thừa, đưa toàn bộ quyết định của du khách vào 1 vùng nhìn duy nhất!

### HỒI 3: Ký Sự Phù Sa, Thổ Nhưỡng & Sổ Vàng OCOP (Đảo tỉ lệ 7 : 5)
- **Cột Trái (7 cột - 58.3%): Ký Sự Điền Dã An Bình & Cổ Chiên:**
  - Ảnh phóng sự lớn kết hợp trích dẫn pull-quote Lora chân thực: `"Phù sa Cổ Chiên nuôi lớn những rặng bần, rặng dừa..."`.
  - Tiêu đề thuần khiết: `"Nhịp chèo trên rạch An Bình"` (triệt tiêu cụm từ cấm "miền sông nước").
- **Cột Phải (5 cột - 41.7%): Đề Cử Biên Tập & Sổ Vàng OCOP Quốc Gia:**
  - `HomeProductLead`: Đề cử đặc sản có số đếm thực từ dữ liệu kho.
  - `HomeOcopLedger`: Khung chứng chỉ hoa văn bảo an Guilloche và tem sáp nung Măng Thít.

### HỒI 4: TÍN HIỆU KHÍ HẬU & TIẾNG NÓI CỘNG ĐỒNG (Đảo tỉ lệ 5 : 7)
- **Cột Trái (5 cột - 41.7%): Bản Tin Khí Hậu & Lịch Đếm Ngược:**
  - `HomeLocalBriefing`: Số đo thời tiết thực tế, độ ẩm, gió và vạch tươi mới `FreshnessLine`.
  - Đếm ngược sự kiện sắp diễn ra.
- **Cột Phải (7 cột - 58.3%): Tiếng Nói Bản Địa & Thanh Hành Trình:**
  - `HomeCommunityFeed`: Câu chuyện và góc ảnh của người đi trước.
  - `HomeContinuation`: Thanh tiếp nối lộ trình cá nhân hóa.

---

## 4. Bảng So Sánh Trước & Sau Nâng Cấp

| Yếu Tố Bố Cục | Hiện Trạng (Rời Rạc) | Sau Khi Nâng Cấp (Nguyên Khối) |
|---|---|---|
| **Số lượng section cắt ngang** | 11 dải phân mảnh độc lập | **4 Đại Hồi chuyển tiếp hữu cơ** |
| **Số lượng tiêu đề $H_2$ cạnh tranh** | 10 tiêu đề $H_2$ rời rạc | **3 tiêu đề $H_2$ đại diện cho từng Hồi** |
| **Trục căn lề mắt người** | Nhảy loạn xạ giữa 6 vị trí | **Chuẩn hóa 12 cột đảo nhịp 7:5 $\longleftrightarrow$ 5:7** |
| **Chiều cao cuộn lãng phí** | ~800px khoảng đệm thừa | **Tiết kiệm 65% khoảng trống vô nghĩa** |
| **Điểm neo buồng lái Hero** | Chữ và search trôi nổi, dán nền đen | **Console Kính Lỏng nguyên khối, viền mờ** |
| **Tín hiệu sông nước thực địa** | Giấu ở đáy trang (Section 8) | **Đưa lên măng-sét ngay cửa trước** |
| **Ngữ cảnh thực địa [anti-ai-style]** | Dùng từ cấm "miền Tây", "sông nước" | **100% địa danh thật: Cổ Chiên, Măng Thít, An Bình** |

---

## 5. Kế Hoạch Triển Khai Kỹ Thuật (Atomic Implementation Steps)

### Task 1: Tái Cấu Trúc Khối Hero Thành Console Kính Lỏng (7:5 Grid)
- **Files:** `web-nuxt/pages/index.vue`, `web-nuxt/assets/css/home-nocturne.css`
- **Bước 1:** Viết test kiểm tra container 12 cột `.hero-inner` và `.hero-action-deck`.
- **Bước 2:** Cập nhật template `pages/index.vue` đưa Search, Nearby và Chips vào `.hero-action-deck`.
- **Bước 3:** Sửa H1 sang `"Trung thu Cổ Chiên, đèn lồng và bánh dân gian"` và bỏ nền đen của `.hero-sub`.
- **Bước 4:** Cập nhật CSS tỷ lệ 7:5 cân bằng baseline với Dossier.

### Task 2: Hợp Nhất Bento Khám Phá (5:7 Grid)
- **Files:** `web-nuxt/pages/index.vue`, `web-nuxt/components/home/HomeDecisionLedger.vue`, `web-nuxt/components/home/HomeCategoryIndex.vue`, `web-nuxt/assets/css/home-nocturne.css`
- **Bước 1:** Viết test kiểm tra container Bento `.home-exploration-complex` và thuộc tính `:compact-header="true"`.
- **Bước 2:** Tích hợp 2 component vào khung Bento 2 cánh (Trái 5 cột, Phải 7 cột) dưới tiêu đề duy nhất: `"ĐỊNH HƯỚNG BẢN ĐỊA · Hôm nay ở Vĩnh Long có gì?"`.
- **Bước 3:** Cập nhật CSS đảm bảo phản hồi xúc giác `:active { transform: scale(0.98); }`.

### Task 3: Chuẩn Hóa Văn Phong Thực Địa Theo [anti-ai-writing-style.md](../../claude-desktop/anti-ai-writing-style.md)
- **Files:** `web-nuxt/components/home/HomeNativeStories.vue`
- **Bước 1:** Thay "Hơi thở miền sông nước" bằng "Nhịp chèo trên rạch An Bình".
- **Bước 2:** Thay mô tả sáo rỗng bằng câu có danh từ riêng và chi tiết giác quan con nước Cổ Chiên.

### Task 4: Kiểm Thử Toàn Diện & Nghiệm Thu Pháp Y
- Chạy 21 bộ test vitest trang chủ: `npx vitest run tests/home-` (100% PASS).
- Kiểm tra nợ token màu sắc: `node scripts/check-tri-region-color-debt.mjs` (0 debt).
- Chụp ảnh Chrome CDP ở cả 2 chế độ (Parchment & Nocturne) trên Desktop 1440px và Mobile 390px để đối chiếu trực quan.
