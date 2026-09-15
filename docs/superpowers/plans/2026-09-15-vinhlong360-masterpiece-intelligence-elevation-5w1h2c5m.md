# Kế Hoạch Nâng Cấp Kỳ Đài Di Sản Thị Giác & Khảo Cứu Thực Địa Thông Minh 5W1H2C5M (VinhLong360 Masterpiece Intelligence Elevation Plan)
> STATUS: active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nâng cấp chuyên sâu, toàn diện cửa sổ hiện tại **`VinhLong360 - Kỳ Đài Di Sản Thị Giác & Khảo Cứu Thực Địa (Visual Cultural Masterpiece)`** (Project Stitch `14916181929760067680`) thành một kiệt tác giao diện khảo cứu văn hóa Mekong siêu hiện đại, tinh tế, thông minh vượt bậc. Tối ưu bố cục thị giác dựa trên nghiên cứu toàn diện hệ sinh thái dự án VinhLong360 (124 xã/phường, trạm thủy văn bến Cổ Chiên, cứu hộ sông nước VHF 16, sổ vàng OCOP, lộ trình theo con nước và giải đáp nhanh AEO), tuân thủ nghiêm ngặt quy tắc **5W1H2C5M**, loại bỏ hoàn toàn AI slop, và **duy trì tuyệt đối đúng 3 cửa sổ trên Canvas** (không phát sinh thêm cửa sổ mới).

**Architecture:** 
1. Tái cấu trúc file mã nguồn chuẩn `stitch_vinhlong360_visual_first.html` với 5 phân tầng giao diện thông minh mang thẩm mỹ ấn bản bảo tàng đương đại (Aldine Editorial & Spatial Bento Matrix).
2. Tích hợp thanh điều khiển đa chế độ khảo cứu (Tactile Mode Switcher), buồng lái dữ liệu thủy văn thực địa (Hydrology Signal Cockpit), lưới Bento bất đối xứng đa chiều (Multi-Dimensional Living Bento) gắn thẻ mẫu vật OCOP & làng nghề, lộ trình điền dã theo con nước 3 chặng (3-Stage Tide Expedition Journey), tàng thư tiêu bản phân nhóm theo danh mục và bàn vận hành công ích cứu hộ 24/7.
3. Kết xuất ngoại tuyến ảnh chụp độ nét cực cao $1.409 \times 3.600$ qua giao thức headless CDP và đồng bộ trực tiếp (in-place) qua Google Stitch REST API vào đúng cửa sổ thứ 3 tại tọa độ `(x: 2496, y: 5003)`, bảo toàn đúng 3 cửa sổ hiển thị trên Canvas.

**Tech Stack:** Semantic HTML5, Tailwind CSS 3.4 tokens, Typography Lora + Be Vietnam Pro + JetBrains Mono, Node.js CDP Headless Chrome Renderer, Google Stitch REST API (`BatchCreateScreens`, `updateMask=screenInstances`), Vitest test suite.

---

## 1. Kết Quả Nghiên Cứu Toàn Diện Dự Án VinhLong360

Qua khảo sát sâu rộng toàn bộ mã nguồn, cơ sở dữ liệu và tài liệu hiến pháp thiết kế của dự án (`PROJECT.md`, `web-nuxt/DESIGN.md`, `web-nuxt/pages/`, `web-nuxt/types/index.ts`), nền tảng VinhLong360 được định danh là **Mekong Signal Atlas - Local Intelligence Platform** với các giá trị bản địa cốt lõi sau:

1. **Tam Vùng Thổ Nhưỡng (Terroir Tri-Region):**
   * **Cù Lao An Bình (Long Hồ):** Vùng đất bãi bồi phù sa ngọt giữa sông Tiền và sông Cổ Chiên. Đậm đà bản sắc nông nghiệp miệt vườn, nổi tiếng với Bưởi Năm Roi Mỹ Hòa chuẩn GlobalGAP ($12^\circ\text{ Brix}$), Vườn chôm chôm Bình Hòa Phước, nghề nuôi cá bè trên sông và nhịp sống ghe tam bản luồn lách rạch dừa nước.
   * **Vương Quốc Gốm Đỏ Măng Thít (Kênh Thầy Cai):** Quần thể hơn $1.500$ lò nung gạch gốm truyền thống hình chóp nón cổ kính, kỹ thuật ủ men đất sét phù sa rực lửa suốt 28 ngày đêm ở nhiệt độ $1.100^\circ\text{C}$, tạo nên màu men đỏ au đặc trưng không nơi nào có được.
   * **Vùng Giao Thoa Văn Hóa Kinh - Khmer - Hoa (Trà Ôn, Tam Bình, TP. Vĩnh Long):** Chùa Âng (ngôi chùa Khmer cổ niên đại 1864 nép mình dưới rừng cây sao cổ thụ hơn 300 năm), Văn Thánh Miếu (1864 - biểu tượng nho học phương Nam), Chùa Ông Thất Phủ Miếu (1892), Lễ hội Ok Om Bok và nghệ thuật Đờn ca tài tử ven bến sông (Di sản UNESCO).
2. **Hệ Thống Dữ Liệu Địa Bạ 124 Xã/Phường:** Mạng lưới dữ liệu hành chính và tọa độ thực địa chuẩn xác đến 3 chữ số thập phân (`10.254°N, 105.972°E`), cắm rễ vào thực tiễn địa phương.
3. **Mạng Lưới Thủy Lộ & Cứu Hộ Sông Nước 24/7:**
   * Trạm đo mực nước bán nhật triều sông Tiền - Cổ Chiên (+1.42m Nước Lớn, nước ròng, nước rong, nước kém).
   * Tần số vô tuyến cứu hộ hàng hải duyên hải: **VHF Kênh 16**.
   * Trực ban Bến phà Đình Khao 24/24 (kết nối TP. Vĩnh Long sang Cù lao An Bình).
   * Đường dây nóng cứu hộ khẩn cấp: **`1800 6836 (Miễn phí)`**.
4. **Niên Giám OCOP Vàng & Sản Vật Thổ Nhưỡng:** Bưởi Năm Roi, Gốm nung men sa bồi Măng Thít, Khoai lang tím Bình Tân, Cam sành Tam Bình, Bánh tráng nem Lục Sĩ Thành, Cá tai tượng chiên xù xòe vây, 14 loại rau rừng ngập nước.
5. **Cẩm Nang Giải Đáp Thực Địa AEO (Answer Engine Optimization):** Trả lời trực diện, không quảng cáo, có kiểm chứng nguồn tin (`SourceMark: VinhLong360 Điền dã 2024`).

---

## 2. Ma Trận Thiết Kế 5W1H2C5M (Nguyên Tắc Hiển Thị Có Căn Cứ Thực Địa)

Mỗi phân đoạn giao diện đều được giải trình chi tiết theo chuẩn 5W1H2C5M, giải thích tường tận *"Vì sao cái này hiển thị ở đây"*:

| Phân Vùng Giao Diện | 5W1H Phân Tích | 2C (Context & Constraints) | 5M (Man, Machine, Material, Method, Measurement) | Lý Do Hiển Thị (Why & Grounding) |
| :--- | :--- | :--- | :--- | :--- |
| **1. Header & Navigation Dock** | **Who:** Lữ khách, nhà khảo cứu văn hóa.<br>**What:** Nhãn hiệu VinhLong360 + Điều hướng 4 phân hệ chính.<br>**Where:** Tỉnh Vĩnh Long.<br>**When:** Thường trực 24/7. | **Context:** Thanh điều hướng đầu trang.<br>**Constraint:** Siêu tinh gọn (chiều cao 58px), khóa viền liquid glass, không che khuất khung hình. | **Machine:** Bộ tìm kiếm thực địa, định vị GPS.<br>**Method:** Đề mục tối giản chuẩn bảo tàng số. | Xác lập danh tính nền tảng trang trọng, cho phép truy cập nhanh toàn bộ hệ thống mà không làm xao nhãng trải nghiệm thị giác. |
| **2. Hero Cinematic Stage & Telemetry Cockpit** | **What:** Đại cảnh hoàng hôn sông Cổ Chiên và vương quốc lò gạch Măng Thít.<br>**Where:** Bến Cổ Chiên $10.254^\circ\text{N}\ 105.972^\circ\text{E}$.<br>**When:** Giờ vàng nhiếp ảnh $17:15 - 17:45$, mực nước triều $+1.42\text{m}$. | **Context:** Khung hình bao quát vùng lõi di sản.<br>**Constraint:** Tỷ lệ $21:9$ điện ảnh tràn viền, $\ge 90\%$ ảnh, lớp kính mờ không che khuất đường chân trời. | **Material:** Đất phù sa, dòng nước Cổ Chiên, gạch nung.<br>**Measurement:** Chiều cao vòm lò 9m, mức triều cường $+1.42\text{m}$, giờ vàng $17:45$. | Tạo cảm xúc choáng ngợp ngay giây đầu tiên; cung cấp ngay thông số mực nước và giờ vàng - yếu tố sinh tử cho việc đi lại bằng ghe thuyền và chụp ảnh thực địa. |
| **3. Tactile Perspective Switcher (Thanh Lọc Đa Chiều)** | **What:** 3 nút chuyển chế độ khảo cứu nhanh: `[Kỳ Đài Khảo Cứu]` · `[Thủy Trình Sông Nước]` · `[Niên Giám 124 Xã/Phường]`.<br>**How:** Nút chuyển dạng tactile pill công thái học touch $\ge 44\text{px}$. | **Context:** Chuyển đổi góc nhìn của siêu ứng dụng.<br>**Constraint:** Nằm ngay dưới Hero, chuyển đổi trực quan, không reload trang. | **Method:** Phân loại góc nhìn theo nhu cầu lữ khách (Người tìm cảnh đẹp / Người đi thuyền / Người tra cứu địa phương). | Khắc phục cảm giác "trang tĩnh buồn tẻ", biến trang chủ thành một buồng lái dữ liệu thông minh, đa năng. |
| **4. Multi-Dimensional Living Bento Matrix** | **What:** 4 Cổng Không Gian Di Sản bất đối xứng: Cù Lao An Bình (60%), Gốm Đỏ Măng Thít (40%), Chùa Cổ Âng (40%), Hương Vị Bến Sông (60%).<br>**Where:** Long Hồ, Kênh Thầy Cai, Trà Ôn, Chợ nổi Trà Ôn. | **Context:** 4 trụ cột bản sắc Vĩnh Long.<br>**Constraint:** $100\%$ ảnh tràn viền, $0$ thẻ trắng chân ảnh; thẻ thông số kính mờ đa tầng. | **Man:** Nghệ nhân gốm vuốt tay, nông dân miệt vườn.<br>**Measurement:** $12^\circ\text{ Brix}$ bưởi ngọt, $1.100^\circ\text{C}$ lò nung 28 ngày, niên đại Chùa Âng $1864$, $14$ loại rau rừng. | Định lượng hóa giá trị thổ nhưỡng và làng nghề; người xem hiểu ngay đặc tính độc bản của từng tiểu vùng trong vòng 3 giây quét mắt. |
| **5. Tide-Responsive Expedition Journey (Lộ Trình 3 Chặng)** | **What:** Lộ trình điền dã theo con nước Mekong: Sớm Mai rạch An Bình ($05:30$) → Chính Ngọ lò gạch Măng Thít ($14:00$) → Dạ Nguyệt đờn ca bến sông ($19:30$).<br>**When:** Chu kỳ 1 ngày từ bình minh đến trăng lên. | **Context:** Hành trình trải nghiệm thực địa.<br>**Constraint:** 3 cột ảnh đứng $3:4$ tỷ lệ vàng, có đường nối hành trình (Journey Line), nhãn phương tiện (ghe chèo, tàu máy, đi bộ). | **Machine:** Ghe tam bản, tàu vỏ lãi composite, máy ảnh số.<br>**Method:** Điền dã theo nhịp triều (Nước Lớn xuồng đi, Nước Ròng ngắm bãi bồi). | Hướng dẫn du khách và nhà nghiên cứu cách trải nghiệm Vĩnh Long chuẩn xác nhất: không đi bừa bãi mà nương theo nhịp sống sông nước tự nhiên. |
| **6. Cabinet of Curiosities & OCOP Registry (Tàng Thư 8 Mẫu Vật)** | **What:** 8 tiêu bản hiện vật văn hóa và sản vật OCOP đặc trưng có mã bảo tàng `[MS: VL-01 ... 08]`.<br>**Where:** Bưởi Năm Roi Mỹ Hòa, Kênh Thầy Cai, Dạ khúc Cổ Chiên, Vườn chôm chôm, Chợ nổi Trà Ôn, Bàn xoay gốm, Chùa Cổ Âng, Đờn ca tài tử. | **Context:** Bộ sưu tập mẫu vật văn hóa số.<br>**Constraint:** Lưới 8 ảnh tỉ lệ $4:5$ sắc nét, $100\%$ mã trạng thái HTTP 200, vi nhãn Liquid Glass. | **Material:** Đất sét sa bồi, vỏ bưởi tinh dầu, gỗ sao cổ thụ.<br>**Measurement:** Mã lưu trữ số bảo tàng, xếp hạng OCOP 4-5 sao. | Kích thích trí tò mò khảo cứu, biến dữ liệu trừu tượng thành các mẫu vật cụ thể có thể chạm vào và sưu tầm. |
| **7. Civic & Marine Dispatch Desk (Bàn Vận Hành Công Ích Sông Nước)** | **What:** Thông tin cứu hộ đường sông khẩn cấp, trực ban phà Đình Khao, mục lục địa bạ 124 Xã/Phường, cam kết bảo tồn AEO độc lập. | **Context:** Chân trang công ích và an toàn sông ngòi.<br>**Constraint:** Bố cục 4 cột nghiêm cẩn, nền màu than củi Mekong `#181e28` ấm áp, tương phản AAA. | **Machine:** Đài duyên hải VHF Kênh 16, Phà tải trọng 100 tấn Đình Khao, đường dây nóng 1800 6836.<br>**Method:** Dịch vụ công ích phi thương mại, không quảng cáo. | Khẳng định bản chất siêu ứng dụng vì cộng đồng: an toàn giao thông đường thủy là huyết mạch sinh tồn của vùng sông nước Vĩnh Long. |

---

## 3. Danh Mục Các File Chạm Vào & Thay Đổi Cụ Thể

### File Được Nâng Cấp Trực Tiếp
- **[MODIFY] `stitch_vinhlong360_visual_first.html`:** 
  * Bổ sung **Tactile Mode Switcher** ngay dưới Hero Stage.
  * Tinh chỉnh **Hero Telemetry Cockpit** với la bàn hướng nước và trạng thái phà Đình Khao.
  * Nâng cấp **Living Bento Matrix** với các vi nhãn mẫu vật thổ nhưỡng và chỉ số đo lường 5M sắc sảo.
  * Thiết kế lại **Tide-Responsive Expedition Journey** với chỉ dẫn phương tiện, cự ly và mốc thời gian thực địa.
  * Bổ sung nhãn phân loại chuyên đề cho **Tàng Thư Điền Dã 8 Mẫu Vật**.
  * Hoàn thiện **Bàn Vận Hành Công Ích Sông Nước** tại chân trang.
  * Đảm bảo tổng số từ trong `<main>` $< 200$ từ và mật độ ảnh $\ge 90\%$.

- **[MODIFY] `scratch/capture_stitch_screen.mjs`:**
  * Tối ưu thông số kết xuất CDP: viewport width $1409\text{px}$, chiều cao tự động theo layout metric, delay tải font Lora & Be Vietnam Pro để ảnh đạt độ sắc nét quang học tuyệt đối.

- **[MODIFY] `scratch/reposition_and_curate_3screens.py`:**
  * Đồng bộ ID màn hình mới được tạo lên Stitch Canvas.
  * Khóa cứng vị trí tại `(x: 2496, y: 5003)`, chiều rộng $1.280\text{px}$.
  * Đặt `"hidden": true` cho tất cả các bản nháp khác, duy trì tuyệt đối đúng **3 cửa sổ** trên Canvas.

---

## 4. Kế Hoạch Thực Thi Từng Task (Task Breakdown)

### Task 1: Nâng Cấp Mỹ Học Thị Giác Thông Minh & Bố Cục 5W1H2C5M Trên Master HTML
- **Files:** `stitch_vinhlong360_visual_first.html`, `scratch/verify_5w1h2c5m_metrics.py`
- **Mục tiêu:** Tích hợp bộ chuyển đổi góc nhìn khảo cứu, buồng lái thủy văn, thẻ mẫu vật thổ nhưỡng và lộ trình điền dã 3 chặng; duy trì $< 200$ từ trong `<main>`.
- **Các bước thực hiện:**
  1. Viết script chèn Tactile Mode Switcher (`Khảo cứu`, `Thủy trình`, `124 Xã/Phường`).
  2. Tích hợp chỉ dẫn phương tiện & cự ly vào 3 chặng hành trình Triptych.
  3. Bổ sung nhãn chuyên khảo OCOP & bảo tàng số vào 8 mẫu vật thực địa.
  4. Chạy `python scratch/verify_5w1h2c5m_metrics.py` xác minh: $\ge 19$ ảnh, $< 200$ từ, 0 lỗi CSS vỡ chữ.
  5. Chạy `python scratch/test_urls.py` xác minh 100% ảnh đạt HTTP 200 OK.
  6. Git commit Task 1.

### Task 2: Kết Xuất Ngoại Tuyến Ảnh Chụp Toàn Cảnh Độ Nét Cực Cao (1409x3600)
- **Files:** `scratch/capture_stitch_screen.mjs`, `stitch_screen_visual_cultural_masterpiece.png`
- **Mục tiêu:** Tạo file ảnh kết xuất độ phân giải cao hoàn hảo, không răng cưa, không giật layout.
- **Các bước thực hiện:**
  1. Chạy `node scratch/capture_stitch_screen.mjs`.
  2. Kiểm tra kích thước và độ toàn vẹn của tệp ảnh `stitch_screen_visual_cultural_masterpiece.png`.
  3. Sao chép ảnh vào thư mục brain artifacts để kiểm tra trực quan qua công cụ `view_file`.

### Task 3: Đồng Bộ Trực Tiếp Vào Cửa Sổ Thứ 3 Trên Google Stitch (Bảo Toàn 3 Cửa Sổ)
- **Files:** `scratch/test_batch_create.py`, `scratch/reposition_and_curate_3screens.py`
- **Mục tiêu:** Upload ảnh mới lên Stitch Cloud và cập nhật vị trí cửa sổ thứ 3 tại `(x: 2496, y: 5003)`, bảo toàn đúng 3 cửa sổ.
- **Các bước thực hiện:**
  1. Chạy `python scratch/test_batch_create.py` để tải ảnh lên dự án Stitch `14916181929760067680`.
  2. Lấy ID màn hình mới từ `scratch/last_batch_create_resp.json`.
  3. Chạy `python scratch/reposition_and_curate_3screens.py <NEW_SCREEN_ID>`.
  4. Xác minh qua REST API số lượng cửa sổ hiển thị (`not hidden`) là CHÍNH XÁC 3.

### Task 4: Kiểm Thử Toàn Bộ Hệ Thống Nuxt & Báo Cáo Nghiệm Thu
- **Files:** `web-nuxt/tests/home-nocturne-*.test.ts`, `walkthrough.md`
- **Mục tiêu:** Đảm bảo toàn bộ 31 unit & integration tests trong Nuxt đều xanh lá và pre-commit checks không có nợ kỹ thuật.
- **Các bước thực hiện:**
  1. Chạy `npx vitest run tests/home-nocturne-*.test.ts` trong thư mục `web-nuxt`.
  2. Chạy `python scripts/checks/run_hard.py --staged`.
  3. Cập nhật `walkthrough.md` và hướng dẫn người dùng nhấn F5 trên Stitch Canvas.

---

## 5. Kế Hoạch Xác Minh (Verification Plan)

### Kiểm thử tự động
- `python scratch/verify_5w1h2c5m_metrics.py`: Kiểm tra $\ge 19$ ảnh, $< 200$ từ trong `<main>`, khóa `letter-spacing: 0px !important`.
- `python scratch/test_urls.py`: Kiểm tra 100% URL ảnh đều phản hồi HTTP 200.
- `npx vitest run tests/home-nocturne-*.test.ts`: Xác nhận 31/31 unit tests Nuxt vượt qua.
- `python scripts/checks/run_hard.py --staged`: Xác nhận 0 vi phạm pre-commit.

### Kiểm tra thủ công của người dùng
- Mở Google Stitch Canvas dự án `14916181929760067680`, nhấn **F5**:
  * Kiểm tra đúng 3 cửa sổ hiện diện trên màn hình.
  * Chiêm ngưỡng cửa sổ thứ 3 bên phải phía dưới đã được lột xác thành **Kỳ Đài Di Sản Thị Giác & Khảo Cứu Thực Địa Thông Minh**: tông màu thổ nhưỡng ấm áp, ảnh toàn cảnh Cổ Chiên bao trùm, buồng lái dữ liệu thủy văn, thẻ mẫu vật OCOP và lộ trình 3 chặng điền dã sắc nét.
