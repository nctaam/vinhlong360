> STATUS: active — Ca A (lệch cấp) ĐÃ CHỐT 2026-08-07; Ca B (đổi tên) và Ca C (quy ước dấu) còn chờ chủ dự án quyết

# Đối chiếu mã hành chính: file chính thức ↔ `web/data.json`

**Ngày lập:** 2026-08-07 · **Loại:** báo cáo CHỈ-ĐỌC, không ghi dữ liệu · **Phạm vi:** 124 đơn vị xã/phường

**Nguồn A (chính thức):** `C:\Users\Administrator\Desktop\Danh sách phường xã thuộc Tỉnh Vĩnh Long_07_08_2026.xls`, Sheet1, 125 dòng × 8 cột (1 header + 124 dữ liệu).
Cột: `Tỉnh Thành Phố | Mã TP | Phường Xã | Mã PX | Cấp | Tên Tiếng Anh | Ghi chú | Nghị định`.

**Nguồn B (dự án):** `web/data.json` — 125 entity `type=place` = 124 xã/phường + 1 `vinh-long` (`level=tinh`, không đối chiếu).

**Cách ghép:** chuẩn hoá tên = NFC → bỏ tiền tố (`Phường `/`Xã `/`P. `/`TT. `/`Thị trấn `) → hạ chữ thường → gộp khoảng trắng. **GIỮ NGUYÊN DẤU tiếng Việt.** Khoá ghép = (tên chuẩn hoá, cấp).

---

## 1. Kiểm tính toàn vẹn (số thật, không làm tròn)

| Kiểm tra | Kết quả |
|---|---|
| Dòng dữ liệu trong file (trừ header) | **124** |
| Dòng lỗi / trống / thiếu Mã PX / cấp lạ | **0** — không có dòng nào bị bỏ qua |
| `Mã PX` trùng nhau | **KHÔNG** — 124 mã đều duy nhất (khoảng 28756 → 29857) |
| Cột `Tỉnh Thành Phố` | 124/124 = `Tỉnh Vĩnh Long` |
| Cột `Mã TP` | 124/124 = `86` |
| Cột `Nghị định` | 124/124 = `Số: 1687/NQ-UBTVQH15; Ngày: 16/06/2025` (chỉ MỘT nghị quyết) |
| Cột `Tên Tiếng Anh` | **rỗng 124/124** — không dùng được |
| Cột `Ghi chú` | có đủ 124/124 (mô tả hợp nhất / đổi tên / đổi loại hình) |
| Tên trùng nhau trong file (cùng tên + cùng cấp) | **KHÔNG** |
| Tên trùng nhau sau khi BỎ DẤU | **KHÔNG** (124 tên bỏ dấu vẫn phân biệt được) |
| Trùng tên trong `data.json` (cùng tên + cấp) | **KHÔNG** |

### 1.1 Số Phường / Xã — **LỆCH LỚN, phải chú ý**

| Nguồn | Phường | Xã | Tổng |
|---|---|---|---|
| File danh mục (.xls, chưa cập nhật cấp) | **19** | **105** | 124 |
| `web/data.json` (và CLAUDE.md §0) | **35** | **89** | 124 |
| Lệch | **−16** | **+16** | 0 |

Tổng vẫn đúng **124**, nhưng **16 đơn vị mà dự án đang ghi là "Phường" thì file danh mục ghi là "Xã".**
Đây không phải lỗi ghép tên — 16/16 ca đều truy được là **cùng một đơn vị** (danh sách `attributes.merged_from` trong data.json khớp với cột `Ghi chú` của file).
Nhiều dòng trong file còn nói ngược hẳn lại, ví dụ:

- `Xã Ba Tri` (29110): *"Đổi loại hình từ thị trấn Ba Tri thành **xã** Ba Tri…"*
- `Xã Long Hồ` (29602): *"Đổi loại hình từ thị trấn Long Hồ thành **xã** Long Hồ…"*
- `Xã Trung Thành` (29659): *"Đổi loại hình, đổi tên từ thị trấn Vũng Liêm thành **xã** Trung Thành…"*

File chỉ dẫn **một** nghị quyết là 1687/NQ-UBTVQH15 ngày 16/06/2025. Ghi chép nội bộ của dự án (`memory/project-16-phuong-moi.md`) nói **ngày 09/06/2026 có 16 xã được nâng lên phường** và đã migrate 2026-06-18 lên cả local + Postgres prod.
**→ Hai nguồn nói về hai thời điểm khác nhau. Chủ dự án đã chốt (2026-08-07): 16 đơn vị đó ĐANG là phường; file .xls dừng ở mốc 1687/2025 nên cột `Cấp` của nó lạc hậu, còn `data.json` (35 phường + 89 xã) là trạng thái hiện hành.** Chi tiết ở §5, Ca A.

### 1.2 Place trong data.json không tìm được mã

Sau khi ghép: **0/124 place bị mất dấu hoàn toàn.** 2 place không khớp bằng tên nhưng truy được mã qua `merged_from` ↔ `Ghi chú` (xem §4). Nghĩa là **cả 124 đơn vị đều có mã ứng viên**. Trong 17 ca từng cần chủ dự án xác nhận: 16 ca lệch CẤP (Ca A) nay đã chốt — xem §5; còn treo là TÊN của 2 ca Ca B và quy ước dấu của 2 ca Ca C, cả hai nhóm đều không đụng tới mã.

---

## 2. KHỚP CHẮC — 107 đơn vị

Điều kiện: tên chuẩn hoá **bằng nhau tuyệt đối (còn dấu)** VÀ cấp khớp (`Phường`↔`phuong`, `Xã`↔`xa`). Không ca nào mơ hồ.

Quy ước slug đề xuất: `<tên-không-dấu>-<maPX>`. Bỏ dấu ở slug là an toàn vì mã số đã bảo đảm duy nhất — **đã kiểm: 107/107 slug đề xuất không trùng nhau.**

| # | id hiện tại | name | cấp | Mã PX | slug đề xuất |
|---:|---|---|---|---:|---|
| 1 | `p-an-hoi` | Phường An Hội | Phường | 28777 | `an-hoi-28777` |
| 2 | `p-binh-minh` | Phường Bình Minh | Phường | 29771 | `binh-minh-29771` |
| 3 | `p-ben-tre` | Phường Bến Tre | Phường | 28789 | `ben-tre-28789` |
| 4 | `p-cai-von` | Phường Cái Vồn | Phường | 29770 | `cai-von-29770` |
| 5 | `p-duyen-hai` | Phường Duyên Hải | Phường | 29512 | `duyen-hai-29512` |
| 6 | `p-hoa-thuan` | Phường Hòa Thuận | Phường | 29398 | `hoa-thuan-29398` |
| 7 | `p-long-chau` | Phường Long Châu | Phường | 29551 | `long-chau-29551` |
| 8 | `p-long-duc` | Phường Long Đức | Phường | 29263 | `long-duc-29263` |
| 9 | `p-nguyet-hoa` | Phường Nguyệt Hóa | Phường | 29254 | `nguyet-hoa-29254` |
| 10 | `p-phu-khuong` | Phường Phú Khương | Phường | 28756 | `phu-khuong-28756` |
| 11 | `p-phu-tan` | Phường Phú Tân | Phường | 28858 | `phu-tan-28858` |
| 12 | `p-phuoc-hau` | Phường Phước Hậu | Phường | 29557 | `phuoc-hau-29557` |
| 13 | `p-son-dong` | Phường Sơn Đông | Phường | 28783 | `son-dong-28783` |
| 14 | `p-thanh-duc` | Phường Thanh Đức | Phường | 29590 | `thanh-duc-29590` |
| 15 | `p-tra-vinh` | Phường Trà Vinh | Phường | 29242 | `tra-vinh-29242` |
| 16 | `p-truong-long-hoa` | Phường Trường Long Hòa | Phường | 29516 | `truong-long-hoa-29516` |
| 17 | `p-tan-hanh` | Phường Tân Hạnh | Phường | 29593 | `tan-hanh-29593` |
| 18 | `p-tan-ngai` | Phường Tân Ngãi | Phường | 29566 | `tan-ngai-29566` |
| 19 | `p-dong-thanh` | Phường Đông Thành | Phường | 29812 | `dong-thanh-29812` |
| 20 | `xa-an-binh` | Xã An Bình | Xã | 29584 | `an-binh-29584` |
| 21 | `xa-an-hiep` | Xã An Hiệp | Xã | 29158 | `an-hiep-29158` |
| 22 | `xa-an-ngai-trung` | Xã An Ngãi Trung | Xã | 29143 | `an-ngai-trung-29143` |
| 23 | `xa-an-phu-tan` | Xã An Phú Tân | Xã | 29317 | `an-phu-tan-29317` |
| 24 | `xa-an-qui` | Xã An Qui | Xã | 29224 | `an-qui-29224` |
| 25 | `xa-an-truong` | Xã An Trường | Xã | 29275 | `an-truong-29275` |
| 26 | `xa-an-dinh` | Xã An Định | Xã | 28957 | `an-dinh-28957` |
| 27 | `xa-binh-phu` | Xã Bình Phú | Xã | 29287 | `binh-phu-29287` |
| 28 | `xa-binh-phuoc` | Xã Bình Phước | Xã | 29638 | `binh-phuoc-29638` |
| 29 | `xa-bao-thanh` | Xã Bảo Thạnh | Xã | 29125 | `bao-thanh-29125` |
| 30 | `xa-chau-hoa` | Xã Châu Hòa | Xã | 28996 | `chau-hoa-28996` |
| 31 | `xa-chau-hung` | Xã Châu Hưng | Xã | 29083 | `chau-hung-29083` |
| 32 | `xa-chau-thanh` | Xã Châu Thành | Xã | 29374 | `chau-thanh-29374` |
| 33 | `xa-cho-lach` | Xã Chợ Lách | Xã | 28870 | `cho-lach-28870` |
| 34 | `xa-cai-nhum` | Xã Cái Nhum | Xã | 29641 | `cai-nhum-29641` |
| 35 | `xa-cau-ke` | Xã Cầu Kè | Xã | 29308 | `cau-ke-29308` |
| 36 | `xa-cau-ngang` | Xã Cầu Ngang | Xã | 29416 | `cau-ngang-29416` |
| 37 | `xa-giao-long` | Xã Giao Long | Xã | 28807 | `giao-long-28807` |
| 38 | `xa-giong-trom` | Xã Giồng Trôm | Xã | 28984 | `giong-trom-28984` |
| 39 | `xa-hieu-phung` | Xã Hiếu Phụng | Xã | 29701 | `hieu-phung-29701` |
| 40 | `xa-hieu-thanh` | Xã Hiếu Thành | Xã | 29713 | `hieu-thanh-29713` |
| 41 | `xa-hiep-my` | Xã Hiệp Mỹ | Xã | 29455 | `hiep-my-29455` |
| 42 | `xa-ham-giang` | Xã Hàm Giang | Xã | 29489 | `ham-giang-29489` |
| 43 | `xa-hoa-binh` | Xã Hòa Bình | Xã | 29830 | `hoa-binh-29830` |
| 44 | `xa-hoa-hiep` | Xã Hòa Hiệp | Xã | 29734 | `hoa-hiep-29734` |
| 45 | `xa-hoa-minh` | Xã Hòa Minh | Xã | 29410 | `hoa-minh-29410` |
| 46 | `xa-hung-khanh-trung` | Xã Hưng Khánh Trung | Xã | 28901 | `hung-khanh-trung-28901` |
| 47 | `xa-hung-my` | Xã Hưng Mỹ | Xã | 29407 | `hung-my-29407` |
| 48 | `xa-hung-nhuong` | Xã Hưng Nhượng | Xã | 29044 | `hung-nhuong-29044` |
| 49 | `xa-huong-my` | Xã Hương Mỹ | Xã | 28981 | `huong-my-28981` |
| 50 | `xa-long-hiep` | Xã Long Hiệp | Xã | 29506 | `long-hiep-29506` |
| 51 | `xa-long-hoa` | Xã Long Hòa | Xã | 29413 | `long-hoa-29413` |
| 52 | `xa-long-huu` | Xã Long Hữu | Xã | 29518 | `long-huu-29518` |
| 53 | `xa-long-thanh` | Xã Long Thành | Xã | 29513 | `long-thanh-29513` |
| 54 | `xa-long-vinh` | Xã Long Vĩnh | Xã | 29533 | `long-vinh-29533` |
| 55 | `xa-luu-nghiep-anh` | Xã Lưu Nghiệp Anh | Xã | 29476 | `luu-nghiep-anh-29476` |
| 56 | `xa-luong-hoa` | Xã Lương Hòa | Xã | 28987 | `luong-hoa-28987` |
| 57 | `xa-luong-phu` | Xã Lương Phú | Xã | 28993 | `luong-phu-28993` |
| 58 | `xa-loc-thuan` | Xã Lộc Thuận | Xã | 29077 | `loc-thuan-29077` |
| 59 | `xa-luc-si-thanh` | Xã Lục Sĩ Thành | Xã | 29857 | `luc-si-thanh-29857` |
| 60 | `xa-my-chanh-hoa` | Xã Mỹ Chánh Hòa | Xã | 29122 | `my-chanh-hoa-29122` |
| 61 | `xa-my-long` | Xã Mỹ Long | Xã | 29419 | `my-long-29419` |
| 62 | `xa-my-thuan` | Xã Mỹ Thuận | Xã | 29788 | `my-thuan-29788` |
| 63 | `xa-ngai-tu` | Xã Ngãi Tứ | Xã | 29767 | `ngai-tu-29767` |
| 64 | `xa-ngu-lac` | Xã Ngũ Lạc | Xã | 29530 | `ngu-lac-29530` |
| 65 | `xa-nhuan-phu-tan` | Xã Nhuận Phú Tân | Xã | 28948 | `nhuan-phu-tan-28948` |
| 66 | `xa-nhon-phu` | Xã Nhơn Phú | Xã | 29623 | `nhon-phu-29623` |
| 67 | `xa-nhi-long` | Xã Nhị Long | Xã | 29302 | `nhi-long-29302` |
| 68 | `xa-nhi-truong` | Xã Nhị Trường | Xã | 29446 | `nhi-truong-29446` |
| 69 | `xa-phong-thanh` | Xã Phong Thạnh | Xã | 29329 | `phong-thanh-29329` |
| 70 | `xa-phu-phung` | Xã Phú Phụng | Xã | 28879 | `phu-phung-28879` |
| 71 | `xa-phu-quoi` | Xã Phú Quới | Xã | 29611 | `phu-quoi-29611` |
| 72 | `xa-phu-thuan` | Xã Phú Thuận | Xã | 29062 | `phu-thuan-29062` |
| 73 | `xa-phuoc-long` | Xã Phước Long | Xã | 29020 | `phuoc-long-29020` |
| 74 | `xa-phuoc-my-trung` | Xã Phước Mỹ Trung | Xã | 28915 | `phuoc-my-trung-28915` |
| 75 | `xa-quoi-an` | Xã Quới An | Xã | 29668 | `quoi-an-29668` |
| 76 | `xa-quoi-thien` | Xã Quới Thiện | Xã | 29677 | `quoi-thien-29677` |
| 77 | `xa-quoi-dien` | Xã Quới Điền | Xã | 29191 | `quoi-dien-29191` |
| 78 | `xa-song-loc` | Xã Song Lộc | Xã | 29386 | `song-loc-29386` |
| 79 | `xa-song-phu` | Xã Song Phú | Xã | 29740 | `song-phu-29740` |
| 80 | `xa-tam-ngai` | Xã Tam Ngãi | Xã | 29335 | `tam-ngai-29335` |
| 81 | `xa-thanh-thoi` | Xã Thành Thới | Xã | 28969 | `thanh-thoi-28969` |
| 82 | `xa-thanh-hai` | Xã Thạnh Hải | Xã | 29221 | `thanh-hai-29221` |
| 83 | `xa-thanh-phong` | Xã Thạnh Phong | Xã | 29227 | `thanh-phong-29227` |
| 84 | `xa-thanh-phu` | Xã Thạnh Phú | Xã | 29182 | `thanh-phu-29182` |
| 85 | `xa-thanh-phuoc` | Xã Thạnh Phước | Xã | 29104 | `thanh-phuoc-29104` |
| 86 | `xa-thanh-tri` | Xã Thạnh Trị | Xã | 29089 | `thanh-tri-29089` |
| 87 | `xa-thoi-thuan` | Xã Thới Thuận | Xã | 29107 | `thoi-thuan-29107` |
| 88 | `xa-trung-hiep` | Xã Trung Hiệp | Xã | 29683 | `trung-hiep-29683` |
| 89 | `xa-trung-ngai` | Xã Trung Ngãi | Xã | 29698 | `trung-ngai-29698` |
| 90 | `xa-tra-con` | Xã Trà Côn | Xã | 29836 | `tra-con-29836` |
| 91 | `xa-tra-cu` | Xã Trà Cú | Xã | 29461 | `tra-cu-29461` |
| 92 | `xa-tan-an` | Xã Tân An | Xã | 29278 | `tan-an-29278` |
| 93 | `xa-tan-hao` | Xã Tân Hào | Xã | 29029 | `tan-hao-29029` |
| 94 | `xa-tan-long-hoi` | Xã Tân Long Hội | Xã | 29653 | `tan-long-hoi-29653` |
| 95 | `xa-tan-luoc` | Xã Tân Lược | Xã | 29785 | `tan-luoc-29785` |
| 96 | `xa-tan-phu` | Xã Tân Phú | Xã | 28840 | `tan-phu-28840` |
| 97 | `xa-tan-thanh-binh` | Xã Tân Thành Bình | Xã | 28921 | `tan-thanh-binh-28921` |
| 98 | `xa-tan-xuan` | Xã Tân Xuân | Xã | 29137 | `tan-xuan-29137` |
| 99 | `xa-tap-son` | Xã Tập Sơn | Xã | 29467 | `tap-son-29467` |
| 100 | `xa-vinh-kim` | Xã Vinh Kim | Xã | 29431 | `vinh-kim-29431` |
| 101 | `xa-vinh-thanh` | Xã Vĩnh Thành | Xã | 28894 | `vinh-thanh-28894` |
| 102 | `xa-vinh-xuan` | Xã Vĩnh Xuân | Xã | 29845 | `vinh-xuan-29845` |
| 103 | `xa-don-chau` | Xã Đôn Châu | Xã | 29497 | `don-chau-29497` |
| 104 | `xa-dong-hai` | Xã Đông Hải | Xã | 29536 | `dong-hai-29536` |
| 105 | `xa-dai-an` | Xã Đại An | Xã | 29491 | `dai-an-29491` |
| 106 | `xa-dai-dien` | Xã Đại Điền | Xã | 29194 | `dai-dien-29194` |
| 107 | `xa-dong-khoi` | Xã Đồng Khởi | Xã | 28945 | `dong-khoi-28945` |

---

## 3. KHỚP MỜ — 15 đơn vị (lệch cấp; Ca A đã chốt ở §5)

Toàn bộ 15 ca đều là **lệch cấp theo cùng một hướng**: `data.json` = Phường, file = Xã. Tên khớp (2 ca chỉ khác quy ước đặt dấu `oà`/`òa`). Cột "Bằng chứng cùng đơn vị" = số phần tử `attributes.merged_from` xuất hiện trong `Ghi chú` của file. Cột "VÌ SAO KHÔNG CHẮC" ghi lại tình trạng **lúc lập báo cáo**; hướng lệch nay đã được giải thích ở §5 Ca A (file lạc hậu về cấp).

| id hiện tại | name (data.json) | cấp data.json | Tên trong file | Cấp file | Mã PX | Bằng chứng cùng đơn vị | VÌ SAO KHÔNG CHẮC |
|---|---|---|---|---|---:|---|---|
| `p-ba-tri` | Phường Ba Tri | phuong | Xã Ba Tri | Xã | 29110 | 5/5 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** |
| `p-binh-dai` | Phường Bình Đại | phuong | Xã Bình Đại | Xã | 29050 | 3/3 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** |
| `p-cang-long` | Phường Càng Long | phuong | Xã Càng Long | Xã | 29266 | 3/3 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** |
| `p-hung-hoa` | Phường Hùng Hoà | phuong | Xã Hùng Hòa | Xã | 29362 | 3/3 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** + tên khác quy ước đặt dấu (`Hùng Hoà` vs `Hùng Hòa` — cùng một chữ, khác vị trí dấu huyền) |
| `p-long-ho` | Phường Long Hồ | phuong | Xã Long Hồ | Xã | 29602 | 2/3 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** |
| `p-mo-cay` | Phường Mỏ Cày | phuong | Xã Mỏ Cày | Xã | 28903 | 4/4 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** |
| `p-phu-tuc` | Phường Phú Túc | phuong | Xã Phú Túc | Xã | 28810 | 4/4 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** |
| `p-tam-binh` | Phường Tam Bình | phuong | Xã Tam Bình | Xã | 29719 | 1/2 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** |
| `p-tien-thuy` | Phường Tiên Thủy | phuong | Xã Tiên Thủy | Xã | 28861 | 3/3 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** |
| `p-tieu-can` | Phường Tiểu Cần | phuong | Xã Tiểu Cần | Xã | 29341 | 3/3 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** |
| `p-tra-on` | Phường Trà Ôn | phuong | Xã Trà Ôn | Xã | 29821 | 1/2 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** |
| `p-tan-hoa` | Phường Tân Hoà | phuong | Xã Tân Hòa | Xã | 29371 | 3/3 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** + tên khác quy ước đặt dấu (`Tân Hoà` vs `Tân Hòa` — cùng một chữ, khác vị trí dấu huyền) |
| `p-tan-quoi` | Phường Tân Quới | phuong | Xã Tân Quới | Xã | 29800 | 3/3 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** |
| `p-tan-thuy` | Phường Tân Thủy | phuong | Xã Tân Thủy | Xã | 29167 | 3/3 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** |
| `p-tap-ngai` | Phường Tập Ngãi | phuong | Xã Tập Ngãi | Xã | 29365 | 2/2 | Lệch cấp: dự án ghi **Phường**, file ghi **Xã** |

> Ghi chú `p-long-ho` (2/3), `p-tam-binh` (1/2), `p-tra-on` (1/2): số bằng chứng thấp hơn vì `merged_from` trong data.json dùng cụm rút gọn ("một phần TT Tam Bình", "phần còn lại") nên so chuỗi không bắt được — không phải dấu hiệu sai đơn vị.

---

## 4. KHÔNG KHỚP — 2 + 2

### 4.1 Có trong `data.json`, không có tên tương ứng trong file (2)

| id hiện tại | name | cấp | `merged_from` | VÌ SAO KHÔNG KHỚP |
|---|---|---|---|---|
| `p-vung-liem` | Phường Vũng Liêm | phuong | TT Vũng Liêm, xã Trung Hiếu, xã Trung Thành | Trong file **không có đơn vị nào tên "Vũng Liêm"**. Dòng 103 `Xã Trung Thành` (29659) ghi: *"Đổi loại hình, đổi tên từ thị trấn Vũng Liêm thành xã Trung Thành, hợp nhất thị trấn Vũng Liêm, xã Trung Hiếu và xã Trung Thành"* → **cùng một đơn vị nhưng khác cả TÊN lẫn CẤP** |
| `xa-hau-loc` | Xã Hậu Lộc | xa | xã Mỹ Lộc, xã Tân Lộc, xã Hậu Lộc, xã Phú Lộc | Trong file **không có đơn vị nào tên "Hậu Lộc"**. Dòng 111 `Xã Cái Ngang` (29728) ghi: *"Đổi tên từ xã Hậu Lộc thành xã Cái Ngang, hợp nhất xã Mỹ Lộc, Tân Lộc, Hậu Lộc và Phú Lộc"* → **cùng một đơn vị, cấp khớp, chỉ khác TÊN** |

### 4.2 Có trong file, không có tên tương ứng trong `data.json` (2)

| Dòng | Tên trong file | Cấp | Mã PX | VÌ SAO KHÔNG KHỚP |
|---:|---|---|---:|---|
| 103 | Xã Trung Thành | Xã | 29659 | `data.json` không có place nào tên "Trung Thành". Ứng viên duy nhất là `p-vung-liem` (xem 4.1) |
| 111 | Xã Cái Ngang | Xã | 29728 | `data.json` không có place nào tên "Cái Ngang". Ứng viên duy nhất là `xa-hau-loc` (xem 4.1) |

> 2 dòng ở §4.2 chính là 2 dòng bị "bỏ trống" tương ứng với 2 place ở §4.1 — **không phải 4 đơn vị mất tích, mà là 2 cặp đổi tên.**

---

## 5. Quyết định của chủ dự án

### Ca A — ĐÃ CHỐT (2026-08-07): giữ dữ liệu dự án, file .xls lạc hậu về CẤP

**Kết luận:** 16 đơn vị dưới đây **ĐANG là phường** — đây là trạng thái hành chính hiện hành, không phải phương án. `data.json` (35 phường + 89 xã) đúng và **giữ nguyên**: không hạ cấp, không đổi `name`, không đổi `id`.

**Lý do:** file `.xls` ngày 07/08/2026 chỉ dẫn **một** văn bản là NQ 1687/NQ-UBTVQH15 (16/06/2025), tức nó dừng ở mốc 19 phường + 105 xã và **chưa cập nhật đợt 16 xã lên phường**. Lệch ở đây là do danh mục chậm, không phải do dữ liệu dự án sai.

**Cách dùng file từ nay:** `.xls` là nguồn **MÃ** hành chính, **KHÔNG** phải nguồn **CẤP**. Mã không đổi khi đơn vị đổi loại hình — chính file tự chứng minh: `Xã Ba Tri` 29110 ghi *"Đổi loại hình từ thị trấn Ba Tri thành xã Ba Tri…"*. Vì vậy 16 đơn vị này vẫn mượn `Mã PX` của file mà không phải theo cột `Cấp` của file.

**Khoá bằng test:** `tests/test_place_admin_code.py` giữ hằng `PHUONG_UPGRADE_IDS` đúng 16 id này và tính lại tập lệch TỪ DỮ LIỆU — thừa hoặc thiếu một ca đều đỏ. Khi có danh mục mới đã cập nhật cấp thì sửa cột cấp trong `OFFICIAL_ADMIN_CODES` và thu hằng số này lại trong cùng commit.

Gồm 15 ca ở §3 cộng `p-vung-liem` ở §4.1. Đúng bằng **16 đơn vị của đợt migrate "16 xã lên phường" (2026-06-18)** đã chạy trên cả local và Postgres prod.

| # | id hiện tại | Dự án ghi (đúng, giữ nguyên) | File .xls ghi (lạc hậu về cấp) | Mã PX |
|---:|---|---|---|---:|
| 1 | `p-ba-tri` | Phường Ba Tri | Xã Ba Tri | 29110 |
| 2 | `p-binh-dai` | Phường Bình Đại | Xã Bình Đại | 29050 |
| 3 | `p-cang-long` | Phường Càng Long | Xã Càng Long | 29266 |
| 4 | `p-hung-hoa` | Phường Hùng Hoà | Xã Hùng Hòa | 29362 |
| 5 | `p-long-ho` | Phường Long Hồ | Xã Long Hồ | 29602 |
| 6 | `p-mo-cay` | Phường Mỏ Cày | Xã Mỏ Cày | 28903 |
| 7 | `p-phu-tuc` | Phường Phú Túc | Xã Phú Túc | 28810 |
| 8 | `p-tam-binh` | Phường Tam Bình | Xã Tam Bình | 29719 |
| 9 | `p-tan-hoa` | Phường Tân Hoà | Xã Tân Hòa | 29371 |
| 10 | `p-tan-quoi` | Phường Tân Quới | Xã Tân Quới | 29800 |
| 11 | `p-tan-thuy` | Phường Tân Thủy | Xã Tân Thủy | 29167 |
| 12 | `p-tap-ngai` | Phường Tập Ngãi | Xã Tập Ngãi | 29365 |
| 13 | `p-tien-thuy` | Phường Tiên Thủy | Xã Tiên Thủy | 28861 |
| 14 | `p-tieu-can` | Phường Tiểu Cần | Xã Tiểu Cần | 29341 |
| 15 | `p-tra-on` | Phường Trà Ôn | Xã Trà Ôn | 29821 |
| 16 | `p-vung-liem` | Phường Vũng Liêm | Xã Trung Thành | 29659 |

**Phương án đã chọn — giữ dữ liệu dự án:** giữ `level=phuong` cho cả 16, mượn `Mã PX` từ file làm khoá định danh. Số liệu toàn site tiếp tục là **35 phường + 89 xã**; CLAUDE.md §0 và `memory/project-16-phuong-moi.md` giữ nguyên; đợt migrate 2026-06-18 vẫn đứng.

**Phương án đã loại — hạ 16 đơn vị về `level=xa`** cho khớp cột `Cấp` của file (kèm đổi `name` "Phường X" → "Xã X" và id `p-*` → `xa-*`). Loại vì nó lấy một danh mục chậm cập nhật làm chuẩn cho trạng thái hiện hành, và cái giá là toàn site quay về 19 phường + 105 xã cộng ~16 URL đổi thêm lần nữa.

> **Việc còn lại (không chặn):** khi tra được số hiệu văn bản 2026 của đợt nâng cấp, ghi bổ sung vào `docs/don-vi-hanh-chinh-vinh-long.md` để danh mục vận hành có dẫn nguồn cấp một. Điều này KHÔNG làm thay đổi kết luận trên.

## 5b. Còn chờ chủ dự án quyết

### Ca B — 2 đơn vị đổi tên

| id hiện tại | Tên dự án | Tên chính thức | Mã PX | Cấp lệch? |
|---|---|---|---:|---|
| `p-vung-liem` | Phường Vũng Liêm | Xã Trung Thành | 29659 | Cấp đã chốt ở Ca A (giữ `phuong`); còn treo là TÊN |
| `xa-hau-loc` | Xã Hậu Lộc | Xã Cái Ngang | 29728 | Không lệch cấp; chỉ treo TÊN |

**Phương án B1 — Theo tên chính thức:** đổi hiển thị thành "Xã Trung Thành" / "Xã Cái Ngang", slug `trung-thanh-29659` / `cai-ngang-29728`, giữ tên cũ trong `attributes.aliases` để search vẫn ra. Đúng văn bản, nhưng **"Vũng Liêm" là tên có sức nhận diện du lịch mạnh** — mất tên này là mất lưu lượng tìm kiếm.

**Phương án B2 — Giữ tên đang dùng, gắn mã chính thức:** hiển thị "Vũng Liêm"/"Hậu Lộc" nhưng gắn `maPX` 29659/29728 và ghi chú tên chính thức trong trang. Giữ được SEO, nhưng **site đang nói sai tên hành chính hiện hành** — vi phạm tinh thần §1.7 (không khai khống) nếu không nêu rõ.

*(Gợi ý trung dung để chủ dự án cân nhắc, không tự áp: tiêu đề dùng tên chính thức, phụ đề "trước đây là …" — nhưng vẫn cần chủ dự án chốt.)*

### Ca C — 2 đơn vị khác quy ước đặt dấu

| id | data.json | File | Bản chất |
|---|---|---|---|
| `p-hung-hoa` | Hùng **Hoà** | Hùng **Hòa** | Cùng một chữ, khác vị trí dấu huyền (kiểu cũ `oà` vs kiểu mới `òa`) |
| `p-tan-hoa` | Tân **Hoà** | Tân **Hòa** | Như trên |

**Phương án C1:** chuẩn hoá toàn site theo file (`òa`, `òe`, `ùy`) — nhất quán với văn bản nhà nước, nhưng phải rà cả những chỗ khác trong nội dung.
**Phương án C2:** giữ nguyên `Hoà`, coi đây là biến thể chính tả chấp nhận được. Không ảnh hưởng slug (bỏ dấu thì `hoa` = `hoa`), chỉ ảnh hưởng chữ hiển thị.

> Hai ca này cũng nằm trong 16 đơn vị của Ca A, nhưng phần cấp đã chốt rồi — thứ còn treo ở đây chỉ là **chữ hiển thị**, không ảnh hưởng mã lẫn slug.

---

## 6. Ảnh hưởng nếu đổi slug

URL trang xã/phường hiện là `/xa-phuong/<entity id>` (`web-nuxt/pages/xa-phuong/[id].vue`, `web-nuxt/utils/adminUnit.ts:89`). **`place` không có trường `slug` riêng — `id` CHÍNH LÀ slug.** Đổi slug = đổi id = đổi mọi tham chiếu.

### 6.1 URL

| Nhóm | Số URL `/xa-phuong/…` đổi |
|---|---:|
| Khớp chắc (§2) — đổi được ngay sau khi duyệt | **107** |
| Khớp mờ + không khớp (§3, §4) — chỉ đổi sau khi chốt Ca A/B | **17** |
| **Tổng nếu làm hết** | **124** |

Chưa tính các URL *chứa* id xã/phường ở dạng tham số (`/danh-ba?place=…`, `/ban-do`, filter, sitemap). Sitemap có mục `/xa-phuong/{ward_id}` (`config/launch-indexing-policy.json:74`) → **sitemap phải sinh lại toàn bộ**.

### 6.2 Tham chiếu bên trong `web/data.json`

| Loại tham chiếu | Khớp chắc | Khớp mờ + chưa khớp | Tổng |
|---|---:|---:|---:|
| `entity.placeId` (entity KHÔNG phải place trỏ về xã/phường) | 1428 | 190 | **1618** |
| `relationships.from` / `.to` | 2021 | 255 | **2276** |
| `itineraries` (chuỗi trùng id) | — | — | **2** |
| **Tổng chỗ phải cập nhật trong data.json** | **3449** | **445** | **3896** |

Thêm: **86 place tự trỏ chính mình** (`place.placeId == place.id`) cũng phải đổi theo.

107/124 xã-phường đang có ít nhất 1 entity trỏ tới; **17 xã-phường chưa có entity nào** (đổi id không ảnh hưởng tham chiếu, nhưng vẫn đổi URL).
Tập trung cao nhất: `p-long-chau` 213 entity, `p-tra-vinh` 116, `p-phuoc-hau` 90, `p-phu-khuong` 87, `xa-an-binh` 76.

### 6.3 Id ghi cứng ngoài `data.json`

Quét toàn worktree (bỏ `.git`, `.nuxt`, `node_modules`, `__pycache__`, `data.json`): **5.739 lần xuất hiện id xã/phường trong 51 file**.

| File | Số lần |
|---|---:|
| `web/data.js` | 4413 |
| `docs/data-verification-web-log.csv` | 188 |
| `docs/data-verification-claims.csv` | 169 |
| `docs/data-verification-sources.csv` | 142 |
| `docs/data-verification-matrix.csv` | 140 |
| `agent/geocode_results.json` | 112 |
| `agent/crawled/_govsite_proposed.json` | 76 |
| `agent/crawled/_deep_crawl_proposed.json` | 40 |
| `agent/auto_learn.py` | 38 |
| `agent/crawler.py` | 26 |
| `tests/test_runtime_place_mappings.py` | 26 |
| `web-nuxt/tests/detail-admin-unit-breadcrumb.test.ts` | 18 |
| `web-nuxt/public/data/entity-index.json` | 16 |

Đáng lưu ý:

- **`web/data.js` (5,4 MB, ĐANG ĐƯỢC GIT THEO DÕI)** là **bản sao thứ hai của toàn bộ roster**, chạm lần cuối ở commit `6c8c95c4`. Không có cơ chế nào bảo đảm nó được sinh lại cùng lúc với `data.json` → đổi slug mà quên file này thì nó thành **nguồn cũ âm thầm**.
- **`agent/auto_learn.py` (38) và `agent/crawler.py` (26) là code chạy thật**, không phải dữ liệu — id ghi cứng ở đó sẽ **âm thầm sai** sau khi đổi slug, không có test nào bắt được nếu chỉ đổi dữ liệu.

### 6.4 Chỗ báo cáo này CHƯA đo được

- **Postgres prod** — chưa truy vấn (không có chỉ đạo). Bảng `entities`/`relationships` prod đã phân kỳ với `data.json` (CLAUDE.md §1.1) nên các con số trên **là cận dưới**, không phải con số prod.
- **UGC do người dùng tạo** (post/comment/saved/itinerary chia sẻ) có thể chứa id hoặc URL cũ.
- **Backlink & chỉ mục Google** — site đang `noindex` toàn bộ, nên rủi ro SEO thấp *ở thời điểm này*; nếu đổi sau khi mở index thì phải có 301.

---

## 7. Việc cần làm tiếp (đề xuất, chưa thực hiện)

1. ~~Chủ dự án chốt Ca A~~ — **XONG 2026-08-07** (§5: giữ dữ liệu dự án, file lạc hậu về cấp).
2. Chốt Ca B, Ca C (§5b) — chỉ đụng chữ hiển thị, không đụng mã.
3. `python scripts/backup_data.py` (bắt buộc, CLAUDE.md §B1) trước bất kỳ thao tác ghi nào.
4. Chuẩn bị bảng redirect 301 cũ→mới cho đủ 124 URL trước khi đổi (kể cả khi đang noindex).
5. Bổ sung test khoá `id ↔ maPX` để lần sau lệch là đỏ ngay.

---

*Báo cáo do phiên đối chiếu tự động lập, CHỈ ĐỌC hai nguồn. Không ghi `web/data.json`, không đụng DB, không commit.*
