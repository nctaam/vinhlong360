# Hướng dẫn tạo nội dung chất lượng cao

> Ngày cập nhật: 27/06/2026 | Dành cho: người nhập liệu, quản trị nội dung
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
| AI-generated (cx/gpt-5.5-image) | **CHO PHEP** | Ảnh nhất quán, không vi phạm bản quyền, phong cách phù hợp miền Tây |
| UGC (người dùng tải lên, đã duyệt) | **CHO PHEP** | Ảnh thực tế từ cộng đồng |
| Pexels / Unsplash / stock photo | **KHONG DUNG** | Ảnh generic, không chính xác cho địa phương cụ thể |
| Wikimedia | **KHONG DUNG** | Thường không chính xác, chất lượng không đồng nhất |
| Lấy từ Google Maps / website khác | **KHONG DUNG** | Vi phạm bản quyền |

### 1.3 Yêu cầu tối thiểu mỗi entity

Mọi entity phải có:
- **Summary** > 100 ký tự (chi tiết ở mục 2)
- **Coordinates** chính xác (hoặc đánh dấu approximate)
- **Area** đúng tỉnh: `vinh-long`, `ben-tre`, hoặc `tra-vinh`
- **Type** phù hợp (xem danh sách type ở mục 3)

---

## 2. Cách viết summary entity

### 2.1 Template chuẩn

```
[Tên entity] là [loại hình] tại [địa chỉ/khu vực], nổi tiếng với [đặc trưng chính].
[Chi tiết bổ sung: lịch sử, đặc sản, trải nghiệm nổi bật].
```

### 2.2 Vi du tot

**Quán ăn:**
> Quán Bé Ba là quán ăn gia đình trên đường Phạm Hùng, TP. Vĩnh Long, chuyên các món đặc sản miền Tây như lẩu mắm, cá tai tượng chiên xù. Quán phục vụ từ 10h-21h hàng ngày, không gian thoáng mát với sân vườn rộng.

**Điểm du lịch:**
> Cồn Phụng là cù lao nổi giữa sông Tiền thuộc huyện Châu Thành, tỉnh Bến Tre. Du khách đến đây trải nghiệm đi xuồng ba lá qua rạch dừa, thưởng thức mật ong, kẹo dừa và nghe đờn ca tài tử. Thời điểm lý tưởng để tham quan là mùa khô (tháng 12-4).

**Sản phẩm OCOP:**
> Kẹo dừa Bến Tre Thanh Long là sản phẩm OCOP 4 sao của cơ sở Thanh Long, xã An Thạnh, huyện Mỏ Cày Nam. Kẹo được làm từ nước cốt dừa tươi, đường mía, có các vị: dừa nguyên chất, sầu riêng, đậu phộng. Sản xuất quanh năm.

### 2.3 Vi du xau (KHONG lam theo)

| Xau | Ly do | Sua lai |
|-----|-------|---------|
| "Nổi tiếng khắp nơi" | Generic, không kiểm chứng | Cụ thể hóa: "được biết đến trong tỉnh với..." |
| "Đẹp nhất miền Tây" | Superlative không chứng minh được | Bỏ, thay bằng đặc điểm cụ thể |
| "Giá cả phải chăng" | Không rõ ràng | Ghi khoảng giá cụ thể nếu có: "giá 50-150k/phần" |
| "Nhiều du khách yêu thích" | Sáo rỗng | Nêu lý do cụ thể tại sao |
| "SĐT: 0912345678" (bịa) | Vi phạm quy tắc §1.4 | Bỏ trống nếu chưa xác minh |

### 2.4 Độ dài target

| Loại | Tối thiểu | Lý tưởng | Tối đa |
|------|-----------|----------|--------|
| Summary (hiển thị trên card) | 100 ký tự | 150-300 ký tự | 500 ký tự |
| Description (trang chi tiết) | 200 ký tự | 500-1000 ký tự | 2000 ký tự |

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
| production_area | Nen co | Nơi sản xuất: "xã An Thạnh, huyện Mỏ Cày Nam" |
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
| name | Co | Tên chính thức: "UBND xã Tân An Hội" |
| type | Co | `facility` |
| summary | Co | > 100 ký tự |
| coordinates | Co | Tọa độ chính xác của trụ sở |
| area | Co | |
| office_kind | Nen co | Loại: ubnd_xa, ubnd_huyen, so_ban_nganh, buu_dien, v.v. |
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

Sử dụng endpoint `cx/gpt-5.5-image` qua script hoặc API.

### 5.2 Template prompt

```
A photograph of [tên entity], [vị trí cụ thể], Mekong Delta Vietnam.
[Phong cách: natural lighting, warm tones, editorial photography style]
[Chi tiết bổ sung tùy loại entity]
```

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
3. Kiểm tra: ảnh có phù hợp với entity không, có đúng phong cách miền Tây không
4. Phê duyệt hoặc từ chối (có thể yêu cầu tạo lại với prompt khác)
5. Ảnh đã duyệt tự động gắn vào entity

### 5.4 Luu y quan trong

- **KHONG** dùng ảnh stock (Pexels, Unsplash) — ảnh không chính xác cho địa phương cụ thể
- **KHONG** lấy ảnh từ Google Maps hay website khác — vi phạm bản quyền
- Mỗi ảnh AI phải được con người duyệt trước khi hiển thị public
- Ảnh entity nên có tỉ lệ 16:9 hoặc 4:3, độ phân giải tối thiểu 800x600

---

## 6. Checklist nội dung

### Checklist chung (moi entity)

- [ ] Summary > 100 ký tự, nội dung chính xác
- [ ] Coordinates chính xác (hoặc đánh dấu approximate)
- [ ] Area đúng: vinh-long / ben-tre / tra-vinh
- [ ] Type phù hợp
- [ ] Không có thông tin bịa đặt
- [ ] Không trùng lặp với entity khác
- [ ] Kiểm tra hiển thị trên frontend

### Checklist quán ăn / cafe

- [ ] Checklist chung (ở trên)
- [ ] Specialty (món đặc trưng) đã điền
- [ ] Khoảng giá đã điền (nếu có)
- [ ] SĐT đã xác minh (nếu có)
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
