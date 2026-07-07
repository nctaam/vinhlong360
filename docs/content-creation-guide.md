# Hướng dẫn tạo nội dung chất lượng cao

> **STATUS (2026-07-07): active — đã truth-sync.** Ảnh CHỈ AI-generated qua `scripts/gen_image.py` (UGC/stock/Wikimedia đều CẤM); template + ví dụ đã align nguyên tắc viết của `docs/toi-uu-chong-ai-va-google-spam-playbook.md` (§4); chuẩn độ dài align cổng index `is_index_worthy` (agent/seo.py); địa danh theo mô hình 2 cấp (124 xã/phường, không huyện).

> Ngày cập nhật: 07/07/2026 | Dành cho: người nhập liệu, quản trị nội dung
> Tài liệu này hướng dẫn cách tạo và chỉnh sửa nội dung entity trên vinhlong360.vn

---

## 1. Nguyên tắc nội dung

### 1.1 Chính xác tuyệt đối (Quy tắc vàng)

- **KHÔNG** bịa địa chỉ, số điện thoại, giá cả, mùa vụ
- **KHÔNG** suy đoán giờ mở cửa, giá vé, dịch vụ khi chưa xác minh
- Nếu không có thông tin chính xác, **bỏ trống** thay vì điền sai
- Entity chưa xác định được phân loại thì để `placeId=None` (hệ thống hiển thị "Chưa phân loại")
- Tọa độ ước tính phải đánh dấu `coords_approximate=true` (hệ thống hiển thị huy hiệu "Gần đúng")

### 1.2 Nguồn ảnh

| Nguồn | Cho phép | Lý do |
|-------|----------|-------|
| AI-generated (cx/gpt-5.5-image, qua `scripts/gen_image.py`) | **NGUỒN DUY NHẤT** | Chốt chủ dự án: CHỈ ảnh AI-gen. Sạch bản quyền, phong cách nhất quán; luôn kèm nhãn "minh hoạ AI", không giả làm ảnh chụp thật |
| UGC (người dùng tải lên) | **KHONG DUNG** | Chốt chủ dự án 2026 (override hướng dẫn cũ): không gắn ảnh người dùng vào entity |
| Pexels / Unsplash / stock photo | **KHONG DUNG** | Bị cấm theo chốt ảnh; ảnh generic, không chính xác cho địa phương cụ thể |
| Wikimedia | **KHONG DUNG** | Bị cấm theo chốt ảnh |
| Lấy từ Google Maps / website khác | **KHONG DUNG** | Vi phạm bản quyền |

### 1.3 Yêu cầu tối thiểu mỗi entity

Mọi entity phải có:
- **Summary** > 100 ký tự (chi tiết ở mục 2)
- **Coordinates** chính xác (hoặc đánh dấu approximate)
- **Area** đúng khu vực (slug hệ thống): `vinh-long`, `ben-tre`, hoặc `tra-vinh` — đây là slug **khu vực cũ** dùng để lọc, KHÔNG còn là tỉnh riêng (tất cả thuộc tỉnh Vĩnh Long mới)
- **Địa danh 2 cấp**: địa chỉ/mô tả chỉ dùng xã/phường CÓ THẬT trong 124 đơn vị (35 phường + 89 xã — xem `docs/don-vi-hanh-chinh-vinh-long.md`); KHÔNG ghi "huyện X" hay "tỉnh Bến Tre/Trà Vinh" trừ văn cảnh lịch sử có chữ "cũ/trước 7-2025"
- **Type** phù hợp (xem danh sách type ở mục 3)

---

## 2. Cách viết summary entity

### 2.1 Nguyên tắc viết (KHÔNG dùng công thức mở bài)

> KHÔNG dùng khuôn "[Tên entity] là [loại hình] tại [địa chỉ], nổi tiếng với [đặc trưng]" — đây chính là formula opening + từ "nổi tiếng" trơ mà playbook chống-AI/spam CẤM (`docs/toi-uu-chong-ai-va-google-spam-playbook.md` §4). Khuôn câu lặp qua hàng trăm trang là hồ sơ "scaled content" Google phạt.

Thay vào đó, viết theo 5 nguyên tắc (rút từ playbook §4):

1. **Mở bằng chi tiết đặc thù** (món signature, mùa vụ, cách đi, âm thanh/mùi) — KHÔNG "Tọa lạc tại / Nằm ở / Là một trong những / X là...".
2. **Mỗi câu ≥1 danh từ riêng hoặc con số** chỉ đúng entity này (năm, giá, tên HTX, quãng đường, tháng âm/dương).
3. **≥1 khiếm khuyết trung thực** ("chỉ nhận tiền mặt", "đường ổ gà mùa mưa") — đáng giá hơn 10 tính từ khen.
4. **Test "thay tên":** dán tên entity khác vào câu — nếu câu vẫn "đúng" thì câu đó vô giá trị, viết lại.
5. **Cấm filler:** "nổi tiếng" (trơ), "đặc sản miền Tây", "điểm đến lý tưởng", "đậm đà bản sắc", kết "Hãy đến và cảm nhận". Mỗi khi định viết "miền Tây" → hỏi "chỗ NÀY khác chỗ khác ở ĐBSCL chỗ nào?" và viết cái khác biệt.

### 2.2 Vi du tot

**Quán ăn** *(ví dụ MINH HOẠ cấu trúc câu — món/giờ/tiện ích dưới đây là fact GIẢ ĐỊNH, KHÔNG phải dữ liệu đã xác minh của entity `nha-hang-sau-tu`; đừng copy vào entity. Khi viết thật: chỉ ghi fact ĐÚNG, chưa xác minh thì bỏ trống, KHÔNG bịa)*:
> Quán Sáu Tú ở 284 Phạm Hùng nổi món cá tai tượng chiên xù cuốn bánh tráng và lẩu mắm cá linh (mùa nước nổi tháng 9-11). Bàn đặt trước cuối tuần vì kín chỗ trưa. Có sân đậu ô tô, nhận tiền mặt và chuyển khoản.

**Điểm du lịch** *(chuẩn vàng có sẵn trong corpus — Cồn Bửng, xã Thạnh Hải)*:
> Khi thủy triều rút, bãi cồn lộ ra ba hồ nước dân địa phương gọi là "hủng", nước phẳng tắm được không lo sóng. Người ta ra cào nghêu, bắt sò cùng ngư dân. Rằm tháng Giêng có Lễ hội Nghinh Ông.

**Sản phẩm OCOP** *(nguyên văn từ entity `tep-kho-my-long` trong data — mẫu chuẩn)*:
> Sáng sớm trên sân phơi xi măng ở thị trấn Mỹ Long, tép biển vừa cập bến được ướp muối rồi phơi nắng 2–3 ngày cho đến khi vỏ đỏ hồng, thịt khô giòn, vị ngọt đậm tự nhiên. Mỹ Long (Cầu Ngang, Trà Vinh) là một trong hai làng nghề chế biến hải sản lớn nhất tỉnh, được công nhận năm 2011, hơn 500 lao động sản xuất hàng nghìn tấn hàng khô mỗi năm.

> Lưu ý địa danh: các mốc chưa chắc chắn để dạng placeholder `[xã]/[năm]` và **verify trước khi publish**; xã/phường phải có thật trong 124 đơn vị hiện hành.

### 2.3 Vi du xau (KHONG lam theo)

| Xau | Ly do | Sua lai |
|-----|-------|---------|
| "Nổi tiếng khắp nơi" | Generic, không kiểm chứng | Cụ thể hóa: "được biết đến trong tỉnh với..." |
| "Đẹp nhất miền Tây" | Superlative không chứng minh được | Bỏ, thay bằng đặc điểm cụ thể |
| "Giá cả phải chăng" | Không rõ ràng | Ghi khoảng giá cụ thể nếu có: "giá 50-150k/phần" |
| "Nhiều du khách yêu thích" | Sáo rỗng | Nêu lý do cụ thể tại sao |
| "X là quán ăn tại [địa chỉ], nổi tiếng với..." | Formula opening — khuôn lặp hàng trăm trang = hồ sơ scaled-content | Mở bằng món/mùa/cách đi cụ thể |
| "chuyên các món đặc sản miền Tây" | Filler phủ-toàn-vùng, test đổi-tên-tỉnh fail | Gọi tên món thật: "lẩu mắm cá linh mùa nước nổi" |
| "Tọa lạc tại... / Nằm ở... / Là một trong những..." | Mở bài formula bị playbook cấm | Mở bằng chi tiết giác quan/hành động |
| "SĐT: 0912345678" (bịa) | Vi phạm quy tắc §1.4 | Bỏ trống nếu chưa xác minh |

### 2.4 Độ dài target

> **Ngưỡng index (cổng chất lượng `is_index_worthy` — agent/seo.py, chạy thật từ 2026-07-06):** summary + description **gộp** phải ≥ **130 từ** (hoặc ≥ **100 từ** nếu entity có ảnh thật) thì trang mới vào sitemap; dưới ngưỡng → bị loại khỏi sitemap. (Robots `noindex,follow` per-page cho entity mỏng là phần P0-1 **CHƯA ship** — hiện toàn site đang noindex chủ động qua `NUXT_PUBLIC_SITE_NOINDEX`, chỉ mở khi chủ dự án quyết.) Vì vậy chuẩn "lý tưởng" dưới đây đặt TRÊN ngưỡng này.

| Loại | Tối thiểu | Lý tưởng | Tối đa |
|------|-----------|----------|--------|
| Summary (hiển thị trên card) | 100 ký tự (~20 từ) | 40-60 từ | 500 ký tự |
| Description (trang chi tiết) | — | 120-200 từ ĐẶC THÙ (gộp với summary ≥130 từ để được index) | 2000 ký tự |

- **KHÔNG độn chữ cho đủ số từ** — Google phủ nhận "preferred word count". Entity chưa đủ chất thì để noindex (mặc định của hệ thống), đừng bịa.
- Body KHÔNG in lại verbatim câu summary (template đã có guard tự cắt, nhưng đừng dựa vào nó).

---

## 3. Enrichment theo entity type

### 3.1 Restaurant / Cafe (Quán ăn / Quán cà phê)

| Trường | Bắt buộc | Ghi chú |
|--------|----------|---------|
| name | Co | Tên quán chính thức |
| type | Co | `restaurant` hoặc `cafe` |
| summary | Co | > 100 ký tự, nêu đặc sản |
| coordinates | Co | Chính xác đến cấp đường |
| area | Co | `vinh-long` / `ben-tre` / `tra-vinh` |
| specialty | Nen co | Món đặc trưng: "cá tai tượng chiên xù, lẩu mắm" |
| price_range | Nen co | Khoảng giá: "50-150k/người" |
| phone | Nen co | Đã xác minh, format 10 chữ số |
| hours | Nen co | "10:00-21:00" hoặc "Hàng ngày 8h-22h" |
| address | Nen co | Địa chỉ đầy đủ: số nhà, đường, phường/xã |

### 3.2 Attraction (Điểm du lịch / Tham quan)

| Trường | Bắt buộc | Ghi chú |
|--------|----------|---------|
| name | Co | Tên chính thức |
| type | Co | `attraction` |
| summary | Co | > 100 ký tự, nêu trải nghiệm chính |
| coordinates | Co | Tọa độ chính xác |
| area | Co | |
| admission | Nen co | Giá vé: "Miễn phí" hoặc "50k/người lớn, 25k/trẻ em" |
| hours | Nen co | Giờ mở cửa |
| best_season | Nen co | "Mùa khô (tháng 12-4)" — CHỈ khi xác minh |
| how_to_get_there | Nen co | Hướng dẫn di chuyển thực tế |

### 3.3 Product / OCOP (Sản phẩm / Đặc sản)

| Trường | Bắt buộc | Ghi chú |
|--------|----------|---------|
| name | Co | Tên sản phẩm + thương hiệu (nếu có) |
| type | Co | `product` |
| summary | Co | > 100 ký tự, mô tả nguyên liệu + đặc trưng |
| area | Co | |
| price | Nen co | Giá bán lẻ: "35k/gói 200g" |
| ocop_stars | Nen co | Số sao OCOP (3, 4, hoặc 5) — CHỈ khi có chứng nhận |
| production_area | Nen co | Nơi sản xuất — CHỈ xã/phường có thật trong 124 đơn vị, KHÔNG ghi huyện: "xã Đồng Khởi (khu vực Mỏ Cày Nam cũ)" |
| season | Nen co | Mùa thu hoạch/sản xuất — CHỈ khi xác minh |

### 3.4 Craft Village (Làng nghề)

| Trường | Bắt buộc | Ghi chú |
|--------|----------|---------|
| name | Co | Tên làng nghề |
| type | Co | `craft_village` |
| summary | Co | > 100 ký tự, mô tả nghề truyền thống |
| coordinates | Co | Tọa độ trung tâm làng |
| area | Co | |
| specialty | Nen co | Sản phẩm đặc trưng: "gốm đỏ, lò gạch" |
| phone | Nen co | SĐT liên hệ (hộ sản xuất chính hoặc HTX) |
| production_method | Nen co | Mô tả ngắn quy trình: "thủ công truyền thống 100%" |

### 3.5 Facility (Cơ sở hành chính / Dịch vụ)

| Trường | Bắt buộc | Ghi chú |
|--------|----------|---------|
| name | Co | Tên chính thức: "UBND xã Tân Long Hội" (xã/phường phải có thật trong 124 đơn vị) |
| type | Co | `facility` |
| summary | Co | > 100 ký tự |
| coordinates | Co | Tọa độ chính xác của trụ sở |
| area | Co | |
| office_kind | Nen co | Giá trị đang dùng trong data: `buu_dien`, `cong_an`, `y_te`, `khac` — KHÔNG dùng `ubnd_huyen` (cấp huyện đã bãi bỏ từ 1/7/2025) |
| phone | Nen co | SĐT chính thức — xác minh qua cổng DVCTT |
| hours | Nen co | "Thứ 2-6, 7:30-11:30, 13:30-17:00" |
| services | Nen co | Danh sách dịch vụ chính |

---

## 4. Quy trình nhập liệu

### 4.1 Tạo entity mới

1. **Kiểm tra trùng lặp** trước khi tạo:
   - Tìm kiếm tên entity trên trang chủ
   - Kiểm tra trong admin: `/admin/entities?q=tên-entity`
   - Nếu đã tồn tại, **sửa** thay vì tạo mới

2. **Đăng nhập admin** tại `/admin`

3. **Thêm entity mới**: Admin > Entities > Thêm mới
   - Điền tất cả trường bắt buộc
   - Điền trường "Nên có" nếu có thông tin xác minh
   - Bỏ trống các trường chưa xác minh

4. **Lưu** và kiểm tra hiển thị trên frontend

### 4.2 Sửa entity hiện có

1. Admin > Entities > Tìm entity > Sửa
2. Chỉ sửa trường cần thay đổi
3. Lưu — hệ thống tự cập nhật `updatedAt`

### 4.3 Nhập liệu hàng loạt (batch)

Khi nhập nhiều entity (>10):

1. Chuẩn bị danh sách trong file CSV/Excel trước
2. Nhập từng entity qua admin UI
3. Sau khi nhập xong batch, chạy kiểm tra:

```powershell
# Windows
python scripts/validate_data.py

# Linux
python3 scripts/validate_data.py
```

4. Xử lý các warning/error mà script báo

### 4.4 Nguồn dữ liệu đáng tin cậy

| Loại thông tin | Nguồn ưu tiên |
|---------------|----------------|
| SĐT cơ quan hành chính | Cổng dịch vụ công trực tuyến (DVCTT) tỉnh |
| Giờ làm việc UBND | Quy định chung: T2-T6, 7:30-11:30, 13:30-17:00 |
| Sao OCOP | Danh sách OCOP trên website Sở Công Thương |
| SĐT quán ăn/cafe | Gọi trực tiếp xác minh, Google Maps (kiểm chéo) |
| Giá vé tham quan | Website chính thức, gọi trực tiếp |
| Mùa thu hoạch | Nông dân, HTX, niên giám nông nghiệp |

---

## 5. Ảnh AI-generated

### 5.1 Cách tạo ảnh

Đường tạo ảnh **DUY NHẤT**: `python scripts/gen_image.py --prompt "..." --out web-nuxt/public/img/x.webp` (endpoint cx/gpt-5.5-image, cần `IMAGE_API_KEY` trong env). Không dùng nguồn ảnh nào khác (xem §1.2).

### 5.2 Template prompt

```
A photograph of [tên entity], [vị trí cụ thể — xã/phường thật], Vinh Long province (Mekong Delta), Vietnam.
[Phong cách: natural lighting, warm tones, editorial photography style]
[Chi tiết bổ sung tùy loại entity]
```

- **Đặt tên file theo địa danh thật** (vd `mang-thit-lo-gach.webp`, `cu-lao-an-binh.webp`) — KHÔNG tên generic kiểu `song-nuoc.webp` (playbook P1-7).
- Prompt phải neo địa danh/đặc thù Vĩnh Long cụ thể, không tả cảnh "sông nước ĐBSCL" nào cũng giống nào.

**Vi du prompt theo loai:**

| Loại | Prompt |
|------|--------|
| Quán ăn | "A photograph of a riverside Vietnamese restaurant in Vinh Long, Mekong Delta. Wooden tables under thatched roof, steaming hotpot, tropical greenery. Natural daylight, editorial food photography." |
| Cù lao | "Aerial photograph of a small river island (cu lao) in the Mekong Delta, Vietnam. Coconut palms, narrow waterways, small boats, lush green vegetation. Golden hour lighting." |
| Sản phẩm OCOP | "Product photography of Vietnamese coconut candy (keo dua) from Ben Tre. Wrapped candies arranged on banana leaf, rustic wooden table. Studio lighting, clean background." |
| Làng nghề | "Documentary photograph of traditional pottery making in Vinh Long, Mekong Delta. Artisan shaping clay on wheel, kiln in background. Natural ambient light." |

### 5.3 Quy trình duyệt ảnh

1. Ảnh AI-generated được tải lên hệ thống
2. Admin vào `/admin/duyet-anh` để duyệt
3. Kiểm tra: ảnh có phù hợp với entity không, có đúng đặc thù cảnh quan Vĩnh Long không (người bản địa nhận ra ngay cảnh "không có thật ở đây" — lỗi tay/chữ biển hiệu/hoạ tiết Khmer-gốm phải loại)
4. Phê duyệt hoặc từ chối (có thể yêu cầu tạo lại với prompt khác)
5. Ảnh đã duyệt tự động gắn vào entity

### 5.4 Luu y quan trong

- **KHONG** dùng ảnh stock (Pexels, Unsplash), Wikimedia, hay ảnh UGC người dùng tải lên — chốt chủ dự án: CHỈ AI-generated
- **KHONG** lấy ảnh từ Google Maps hay website khác — vi phạm bản quyền
- Ảnh AI **không được giả làm ảnh chụp thật**: giữ nhãn minh hoạ, KHÔNG giả EXIF/credit/tác giả
- Mỗi ảnh AI phải được con người duyệt trước khi hiển thị public
- Ảnh entity nên có tỉ lệ 16:9 hoặc 4:3, độ phân giải tối thiểu 800x600

---

## 6. Checklist nội dung

### Checklist chung (moi entity)

- [ ] Summary > 100 ký tự, nội dung chính xác
- [ ] Coordinates chính xác (hoặc đánh dấu approximate)
- [ ] Area đúng slug khu vực: vinh-long / ben-tre / tra-vinh
- [ ] Địa danh 2 cấp: chỉ xã/phường có thật trong 124 đơn vị; KHÔNG "huyện X", KHÔNG "tỉnh Bến Tre/Trà Vinh" (trừ văn cảnh lịch sử "cũ")
- [ ] Không mở bài formula ("X là... tại...", "Tọa lạc tại..."); không filler "miền Tây" generic
- [ ] Muốn trang được index: summary + description gộp ≥130 từ đặc thù (hoặc ≥100 từ + ảnh) — không độn chữ
- [ ] Type phù hợp
- [ ] Không có thông tin bịa đặt
- [ ] Không trùng lặp với entity khác
- [ ] Kiểm tra hiển thị trên frontend

### Checklist quán ăn / cafe

- [ ] Checklist chung (ở trên)
- [ ] Specialty (món đặc trưng) đã điền
- [ ] Khoảng giá đã điền (nếu có)
- [ ] SĐT đối chiếu nguồn chính thống (nếu có)
- [ ] Giờ mở cửa (nếu có)
- [ ] Địa chỉ đầy đủ

### Checklist điểm du lịch

- [ ] Checklist chung
- [ ] Giá vé / admission (nếu có)
- [ ] Giờ mở cửa (nếu có)
- [ ] Mùa phù hợp (nếu biết chắc)
- [ ] Hướng dẫn di chuyển

### Checklist sản phẩm OCOP

- [ ] Checklist chung
- [ ] Giá bán (nếu có)
- [ ] Số sao OCOP (nếu đã chứng nhận)
- [ ] Vùng sản xuất
- [ ] Mùa vụ (nếu biết chắc)

### Checklist cơ sở hành chính

- [ ] Checklist chung
- [ ] office_kind đúng
- [ ] SĐT chính thức (xác minh qua DVCTT)
- [ ] Giờ làm việc
- [ ] Danh sách dịch vụ chính

---

## Lien he ho tro

Nếu gặp vấn đề khi nhập liệu hoặc cần hỗ trợ:
- Kiểm tra `docs/developer-setup.md` cho hướng dẫn cài đặt
- Chạy `python scripts/validate_data.py` để phát hiện lỗi dữ liệu
- Xem `docs/data-quality-report.md` cho tình trạng chất lượng dữ liệu hiện tại
