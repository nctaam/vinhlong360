# Đơn vị hành chính tỉnh Vĩnh Long (mới) — tham chiếu

> **Nguồn:** Cổng "Xây dựng chính sách" – chinhphu.vn, theo **Nghị quyết 1687/NQ-UBTVQH15**.
> URL: https://xaydungchinhsach.chinhphu.vn/sap-xep-dvhc-danh-sach-124-xa-phuong-cua-tinh-vinh-long-moi-119250623091001322.htm

## Tổng quan

- Hiệu lực: **mô hình 2 cấp (tỉnh → xã/phường), bỏ cấp huyện** từ 1/7/2025.
- Vĩnh Long mới = **Vĩnh Long (cũ) + Bến Tre + Trà Vinh**.
- Tổng: **124 đơn vị cấp xã = 19 phường + 105 xã** (101 sắp xếp + 4 giữ nguyên).
- Website (`web/data.js`) đã nạp đầy đủ 124 đơn vị làm thực thể `place`.

## 19 phường

### Khu vực Vĩnh Long (cũ) — 8 phường
**TP Vĩnh Long (5):** Thanh Đức · Long Châu · Phước Hậu · Tân Hạnh · Tân Ngãi
**TX Bình Minh (3):** Bình Minh · Cái Vồn · Đông Thành

### Khu vực Trà Vinh (cũ) — 6 phường
**TP Trà Vinh (4):** Trà Vinh · Long Đức · Nguyệt Hoá · Hoà Thuận
**TX Duyên Hải (2):** Duyên Hải · Trường Long Hoà

### Khu vực Bến Tre (cũ) — 5 phường
**TP Bến Tre (5):** An Hội · Phú Khương · Bến Tre · Sơn Đông · Phú Tân

## 105 xã

### Khu vực Vĩnh Long (cũ) — 27 xã
**Mang Thít:** Cái Nhum · Tân Long Hội · Nhơn Phú · Bình Phước
**Long Hồ:** An Bình · Long Hồ · Phú Quới · Quới Thiện
**Vũng Liêm:** Trung Thành · Trung Ngãi · Quới An · Trung Hiệp · Hiếu Phụng · Hiếu Thành · Lục Sĩ Thành
**Trà Ôn:** Trà Ôn · Vĩnh Xuân
**Tam Bình:** Trà Côn · Hòa Bình · Hòa Hiệp · Tam Bình · Ngãi Tứ · Song Phú · Cái Ngang
**Bình Tân:** Tân Quới · Tân Lược · Mỹ Thuận

### Khu vực Trà Vinh (cũ) — 35 xã (31 sắp xếp + 4 giữ nguyên)
**Duyên Hải:** Long Hữu · Long Thành · Đôn Châu · Ngũ Lạc
**Càng Long:** Càng Long · An Trường · Tân An · Nhị Long · Bình Phú
**Châu Thành:** Châu Thành · Song Lộc · Hưng Mỹ
**Cầu Kè:** Cầu Kè · Phong Thạnh · An Phú Tân · Tam Ngãi
**Tiểu Cần:** Tiểu Cần · Tân Hoà · Hùng Hoà · Tập Ngãi
**Cầu Ngang:** Cầu Ngang · Mỹ Long · Vinh Kim · Nhị Trường · Hiệp Mỹ
**Trà Cú:** Trà Cú · Đại An · Lưu Nghiệp Anh · Hàm Giang · Long Hiệp · Tập Sơn
**Giữ nguyên:** Long Hòa · Đông Hải · Long Vĩnh · Hòa Minh

### Khu vực Bến Tre — 43 xã
**Châu Thành:** Phú Túc · Giao Long · Tiên Thủy · Tân Phú
**Chợ Lách:** Phú Phụng · Chợ Lách · Vĩnh Thành · Hưng Khánh Trung
**Mỏ Cày Bắc:** Phước Mỹ Trung · Tân Thành Bình · Nhuận Phú Tân
**Mỏ Cày Nam:** Đồng Khởi · Mỏ Cày · Thành Thới · An Định · Hương Mỹ
**Thạnh Phú:** Đại Điền · Quới Điền · Thạnh Phú · An Qui · Thạnh Hải · Thạnh Phong
**Ba Tri:** Tân Thủy · Bảo Thạnh · Ba Tri · Tân Xuân · Mỹ Chánh Hòa · An Ngãi Trung · An Hiệp
**Giồng Trôm:** Hưng Nhượng · Giồng Trôm · Tân Hào · Phước Long · Lương Phú · Châu Hòa · Lương Hòa
**Bình Đại:** Thới Thuận · Thạnh Phước · Bình Đại · Thạnh Trị · Lộc Thuận · Châu Hưng · Phú Thuận

## Ghi chú thiết kế

- **Địa danh cũ** (Mang Thít, Tam Bình, Bình Tân, cù lao An Bình…) lưu trong `legacyArea` và `alias` của mỗi xã/phường — chỉ mang tính **tham khảo**, không dùng làm đơn vị phân cấp.
- Website xây theo **hệ thống chính quyền 2 cấp** (tỉnh → xã/phường), nhóm theo khu vực (VL/BT/TV) để tiện duyệt.
- Tên huyện cũ (Mang Thít, Long Hồ, Vũng Liêm…) ghi trong `legacyArea` để người dùng địa phương dễ nhận ra vị trí.
