# Hồ sơ chờ chủ dự án quyết — sau đợt "giải quyết tất cả nợ" (2026-08-30)

> STATUS: active — mỗi mục là MỘT quyết định. Máy đã làm hết phần tự quyết được
> theo hiến pháp; những mục dưới đây dừng lại vì cần quyền của chủ dự án
> (đổi tiêu chuẩn, đổi diện mạo, pháp lý, chi phí) chứ không vì thiếu năng lực
> hay thiếu thời gian.

## 0. Bảng điểm trước → sau đợt

| Chiều | Trước (2026-08-29) | Sau | Nợ còn |
|---|---:|---:|---|
| data | 100 | **100** | 0 |
| backend | 81 | **100** | R20.4 (chỉ thiếu artifact `coverage.json`) |
| frontend | 64 | **86** | 331 = R30.2 emoji 330 + R30.7 bundle 1 |
| ui-design | 100 | **100** | 0 |
| content | 51 | **99** | R50.2 = 8 (đều là tên riêng / thuật ngữ lịch sử) |
| docs | 100 | **100** | 0 |
| ops | 100 | **100** | 0 |

Nợ R20.8 (complexity backend): **47 → 0 toàn repo**.

---

## 1. Gói JS 803/800 kB — nới trần hay xếp đợt giảm cân?

**Sự thật đo được.** Trần 800 đặt 2026-07-10 khi bundle đang 790 (biên 10 kB).
Nay 803: **tăng trưởng thật** của 18 task correction-case pilot, không phải rác.

Đã thử và ĐỀU KHÔNG ĂN (đo, không đoán):
- Gom chunk nhỏ `experimentalMinChunkSize` 6 KB → **811** (tệ hơn: chunk dùng
  chung bị nhân bản vào từng importer); hạ 2 KB → **810**. Đã hoàn nguyên.
- Soi mỡ thư viện: `ipx/yup/chart` trong chunk là **dương-tính-giả** (trùng chuỗi
  trong hash tên file). Không có provider chết để gỡ.
- 276/803 kB là `maplibre-gl` và nó **đã lazy đúng** (`await import`), chỉ bị cổng
  đếm vì cổng cộng mọi `*.js`.
- Phiên 2026-08-27 độc lập đã tới cùng kết luận (sổ `90-exceptions-log.md`), và
  việc này đã nằm ở **ROADMAP §37.3** như một task hiệu năng riêng.

**Hai đường, chọn một:**
- (a) **Nới trần lên 820** kèm giải trình trong `bundle-budget.json` — mở lại cổng
  frontend của CI ngay, đổi lại hạ một nấc tiêu chuẩn.
- (b) **Giữ trần, xếp đợt giảm cân** (thay maplibre bằng bản nhẹ hơn, hoặc tách
  route bản đồ khỏi build chính) — giữ tiêu chuẩn, đổi lại CI frontend còn đỏ.

Máy KHÔNG tự chọn: cả hai đều là hạ/giữ một tiêu chuẩn của dự án.

---

## 2. Emoji chức năng 330 chỗ (R30.2) — đại tu bộ icon?

**Sự thật.** 330 emoji trong 38 file: 157 ở trường `icon:`, 88 trong
`<span aria-hidden>`, 85 chỗ khác (nhãn option, ví dụ JSON trong trang hướng dẫn).
Chuẩn nhà đòi emoji-chức-năng dùng component `IconLine` — nhưng `IconLine` hiện
**chỉ có 18 icon**, còn 110 emoji khác nhau đang dùng.

Quy đổi đủ = vẽ/nhập ~110 SVG mới và **đổi diện mạo 38 trang**. Đây là quyết định
thị giác, không phải phép thay chuỗi — và bài học đã ghi: chủ dự án đánh giá theo
bố cục/màu sắc, đề xuất phải trình **tổng phổ toàn trang**.

**Đề nghị:** cho phép mở một đợt riêng, máy sẽ dựng mockup tổng phổ (tên trang
thật, cả sáng lẫn tối) rồi mới thay. Chi phí ước tính: 1 đợt cỡ chiến dịch F1/F2.

**Lưu ý:** R30.2 là *soft-ratchet* — 330 này là **tồn kho hợp lệ**, cổng chỉ chặn
emoji-chức-năng MỚI. Không sửa cũng không ai vi phạm gì.

---

## 3. R50.2 còn 8 — giữ nguyên (đề nghị đóng, không phải nợ)

8 chỗ chứa chữ "miền Tây" còn lại KHÔNG phải filler:
- `Trường Xây dựng miền Tây` — **tên riêng** của trường (3 chỗ).
- `nhóm đờn ca tài tử miền Tây` — **thuật ngữ âm nhạc học**: trường phái miền Tây
  (Trần Quang Quờn) đối với trường phái miền Đông (3 chỗ).
- `ba tỉnh miền Tây` 1867 (Phan Thanh Giản) — **sự kiện lịch sử** (1 chỗ).
- 1 chỗ trong `name` của chính entity trường.

Cổng là bộ so chuỗi nên không phân biệt được. **Đề nghị chủ duyệt** coi đây là mức
sàn đúng của R50.2 (giống whitelist của R10.7), hoặc cho phép thêm whitelist
per-occurrence để cổng về 0 mà không phải viết sai lịch sử.

---

## 4. 157 entity gắn cờ "cần bổ sung" — cần khảo sát thực địa

Trong 245 entity mỏng vừa viết lại, **157 cái chỉ có địa chỉ (± số điện thoại)**:
phần lớn là quán ăn/cà phê/nhà nghỉ nhập từ danh bạ. Nội dung đã viết trung thực
từ dữ liệu thật và KHÔNG bịa thêm — nên chúng ngắn và khô.

Muốn dày hơn thì cần **dữ liệu mới** (giờ mở cửa, khoảng giá, món đặc trưng, ảnh) —
tức khảo sát/gọi điện, việc của người. Danh sách đầy đủ nằm ở
`C:\tmp\apply_log.json` (khoá `owner_list`), máy có thể xuất ra CSV khi cần.

Cũng phát hiện vài dữ liệu **nghi sai** cần chủ xác nhận:
- `khach-san-khoi-hoa` có `ocop_star = 2` (khách sạn không phải sản phẩm OCOP).
- `lang-be---am-thuc-du-lich-sinh-thai` có `sub_category = lake`.
- `mandi-cafe` từng ghi "Đánh giá 7.3/5" (vượt thang) — đã bỏ khi viết lại.

---

## 5. Track-H — pháp lý (giữ nguyên, vẫn chờ luật sư)

Không đổi so với đánh giá 2026-08-21, nhắc lại vì vẫn là mục treo nghiêm trọng nhất:
- **Luật 91/2025/QH15** (Bảo vệ dữ liệu cá nhân, hiệu lực 01/01/2026) đã thay khung
  NĐ13 mà mọi ghi chú pháp lý trong repo đang dựa vào.
- **Ranh giới TMĐT** của mô hình premium/featured listing hẹp hơn giả định §1.4.

Hồ sơ câu hỏi đã soạn sẵn: `docs/2026-08-22-cau-hoi-cho-luat-su.md`.

---

## 6. Việc chờ nguồn dữ liệu chính thức (không phải nợ kỹ thuật)

- Bảng ánh xạ xã-cũ → xã-mới (124 đơn vị) — cần văn bản chính thức.
- 10 entity còn tên riêng chứa "tỉnh X" trong whitelist R10.7 — chờ chủ soát tên
  hiển thị (vd `Cửa hàng OCOP tỉnh Bến Tre` là tên đơn vị đặt trước 7-2025).
- Re-author `xa-hung-khanh-trung`; quyết `require_admin` cho `/search/enhanced`.

---

## 7. Dung lượng máy (ngoài dự án)

Đã dọn phần thuộc quyền trong đợt trước: Downloads 14 GB → 0,9 GB, vhdx Docker
32,7 → 24 GB, Temp/pytest/playwright/pnpm. Còn **chờ chủ**: `.codex/sessions`
8 GB, `Claude/vm_bundles` 9 GB, `Packages` 10,6 GB, `Documents` 37,9 GB (repo dự
án khác — muốn tỉa `node_modules` các repo ngủ thì ra lệnh). Máy hiện ~22 GB trống.
