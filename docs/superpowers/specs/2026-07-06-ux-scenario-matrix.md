# Ma trận kịch bản trải nghiệm người dùng — vinhlong360.vn (2026-07-06)

Khung đánh giá cho vòng test-trực-tiếp-Chrome. Mỗi kịch bản = một người thật, một mục tiêu thật, đi qua các trang thật. Test = đi đúng luồng đó trong browser, chấm từng bước theo tiêu chí.

## Persona → Kịch bản → Luồng → Tiêu chí "tốt"

| # | Persona | Mục tiêu | Luồng trang (journey) | CTA/quyết định | Tiêu chí "tốt" (đạt/không) | Ma sát cần soi |
|---|---------|----------|----------------------|----------------|---------------------------|----------------|
| **S1** | Du khách lần đầu | Lên kế hoạch 1 chuyến 2 ngày | `/` → `/khu-vuc/[vùng]` → `/dia-diem/[id]` → `/tao-lich-trinh` → lưu | Lưu điểm / tạo lịch trình | Hero cuốn ngay; hiểu 3 vùng; điểm đến "kể chuyện"; tạo lịch trình mượt | Hero quá tải? Điều hướng vùng rõ? Teaser thẻ = chuyện hay địa chỉ? |
| **S2** | Tín đồ ẩm thực | Tìm món đặc trưng gần đây | `/` → `/kham-pha/am-thuc` (hoặc `/tim-kiem`) → `/dia-diem/[dish]` → contact | Gọi/Zalo hỏi quán | Lưới món hấp dẫn; lọc nhanh; món có hook + mùa; CTA liên hệ rõ | Teaser = địa chỉ (bug data)? Lọc mượt? |
| **S3** | Người mua đặc sản/OCOP | Chọn quà OCOP tin cậy | `/san-pham` hoặc `/ocop` → `/dia-diem/[product]` → contact | Hỏi giá qua Zalo | Sổ vàng OCOP rõ hạng sao; provenance trước giá; không giống nhau (twin) | Sao OCOP rõ? Con dấu sáp hiện? |
| **S4** | Người tìm chỗ ở | Tìm homestay ven sông | `/luu-tru` → `/dia-diem/[stay]` → contact | Gọi đặt phòng (liên hệ) | Hero "thức dậy"; hero phù-sa cho nơi chưa ảnh; tiện ích rõ | 96% chưa ảnh → hero placeholder ổn? |
| **S5** | Đi theo mùa / lễ hội | Biết lễ hội sắp diễn ra | `/theo-mua` hoặc `/le-hoi` → `/dia-diem/[event]` → `/tao-lich-trinh` | Thêm vào lịch (iCal) | Vòng-mùa "bạn đang ở đây"; dải trăng + âm lịch; countdown lễ hội | Ngày sống đúng? Nút iCal hiện mobile? |
| **S6** | Thành viên cộng đồng | Đọc/đăng bài, xem hồ sơ | `/cong-dong` → `/bai-viet/[id]` → `/nguoi-dung/[id]` → `/bang-xep-hang` | Đăng bài / theo dõi | Feed ấm; PostCard editorial; hồ sơ = record đóng góp | Composer nguyên vẹn? Hydration? |
| **S7** | Chủ cơ sở | Đăng ký quản lý trang | footer/`/dia-diem/[id]` → `/lien-he?ref=claim` | Gửi liên hệ | CTA B2G rõ; form liên hệ mượt; không "chốt đơn" | Đường claim rõ từ đâu? |
| **S8** | Tra cứu hành chính | Tìm phường/xã | `/danh-ba` → `/xa-phuong/[id]` | Xem điểm đến trong xã | Danh bạ = ngách; xã-phường có mô tả + sản phẩm | 124 đơn vị load ổn? |

## Chiều cắt-ngang (áp cho MỌI trang khi test)

| Dim | Kiểm gì | Cách đo (Chrome) |
|-----|---------|------------------|
| **D1 Render/SSR** | Trang load, không 500 | HTTP 200 + không màn trắng |
| **D2 Console** | 0 error, 0 hydration-mismatch | `preview_console_logs level:error` (fresh-server, direct-nav để cô lập) |
| **D3 Overflow ngang** | 0 tràn @1280 và @375 | `scrollWidth - clientWidth` ở cả 2 viewport (nhớ set viewport thật, tránh clientW=0) |
| **D4 Dark mode** | Parity đủ, không vỡ tương phản | toggle theme → soi màu chữ/nền, sediment gradient dark |
| **D5 Mobile @375** | Không đè, touch ≥44px, nav ẩn/hamburger | `preview_resize mobile` + snapshot |
| **D6 A11y** | Focus thấy được, heading order, alt/aria | tab-through + snapshot accessibility tree |
| **D7 Ngôn ngữ editorial** | serif masthead + sediment + teaser đúng nơi | inspect font-family + sự hiện diện dấu phù-sa |
| **D8 CWV cảm nhận** | Không nhero-clamp lỗi, ảnh có kích thước, không layout-shift lớn | inspect + logs |

## Thang chấm mỗi bước
- ✅ Tốt (đúng ý đồ, không lỗi) · ⚠️ Đáng nâng (không lỗi nhưng dưới chuẩn) · ❌ Lỗi (phải sửa)

## Trang public đầy đủ (36) — gom theo cụm để test không sót
- **Trang chủ/vùng**: `/`, `/khu-vuc/[area]`, `/xa-phuong/[id]`, `/danh-ba`
- **Điểm đến/khám phá**: `/dia-diem`, `/dia-diem/[id]`, `/kham-pha/[interest]`, `/du-lich`, `/luu-tru`, `/theo-mua`, `/tuyen-duong`, `/ban-do`
- **Đặc sản/sự kiện**: `/san-pham`, `/ocop`, `/le-hoi`, `/su-kien`
- **Lịch trình**: `/lich-trinh`, `/lich-trinh/[id]`, `/tao-lich-trinh`, `/da-luu`
- **Cộng đồng/tài khoản**: `/cong-dong`, `/bai-viet/[id]`, `/nguoi-dung/[id]`, `/bang-xep-hang`, `/tai-khoan`, `/cai-dat`, `/thong-bao`
- **Tìm kiếm/tĩnh**: `/tim-kiem`, `/gioi-thieu`, `/lien-he`, `/huong-dan`, `/huong-dan-thanh-vien`, `/chinh-sach-bao-mat`, `/dieu-khoan-su-dung`

> Test theo KỊCH BẢN (S1–S8) để bám ngữ cảnh người dùng, đồng thời tick phủ hết 36 trang qua các cụm. Ghi finding theo `trang · dim · thang-chấm · ghi-chú`.
