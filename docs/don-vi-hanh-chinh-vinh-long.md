# Đơn vị hành chính tỉnh Vĩnh Long (mới) — tham chiếu

> **STATUS (2026-07-07): active — đã truth-sync.** Số liệu khớp `web/data.json` hiện hành (125 place = 1 tỉnh + **35 phường + 89 xã**); đã cập nhật đợt 16 xã lên phường 09/06/2026 (data migrate xong 2026-06-18, local + prod).

> **Nguồn:** Cổng "Xây dựng chính sách" – chinhphu.vn, theo **Nghị quyết 1687/NQ-UBTVQH15**.
> URL: https://xaydungchinhsach.chinhphu.vn/sap-xep-dvhc-danh-sach-124-xa-phuong-cua-tinh-vinh-long-moi-119250623091001322.htm

## Tổng quan

- Hiệu lực: **mô hình 2 cấp (tỉnh → xã/phường), bỏ cấp huyện** từ 1/7/2025.
- Vĩnh Long mới = **Vĩnh Long (cũ) + Bến Tre + Trà Vinh**.
- Tổng hiện hành: **124 đơn vị cấp xã = 35 phường + 89 xã**.
  - Theo NQ 1687 ban đầu: 19 phường + 105 xã (101 sắp xếp + 4 giữ nguyên).
  - Ngày **09/06/2026**, **16 xã được nâng lên phường** (VL 5 · BT 6 · TV 5 — đều là trung tâm huyện lỵ cũ đủ tiêu chí đô thị) → 35 phường + 89 xã. Dữ liệu hệ thống **migrate hoàn tất 2026-06-18** (SQLite local + Postgres prod, script `scripts/migrate_sap_nhap.py` — script đã xoá sau khi hoàn tất, cleanup 2026-06-27 `c8e0e74`).
- DB là nguồn sự thật; `web/data.json` (bản export/prerender) đã nạp đầy đủ 124 đơn vị làm thực thể `place`: id `p-*` (phường), `xa-*` (xã), cộng 1 entity `vinh-long` cấp tỉnh; **cả 124 đơn vị có `parentId=vinh-long`** (không cấp trung gian).

## 35 phường

### Khu vực Vĩnh Long (cũ) — 13 phường
**Từ TP Vĩnh Long cũ (5):** Thanh Đức · Long Châu · Phước Hậu · Tân Hạnh · Tân Ngãi
**Từ TX Bình Minh cũ (3):** Bình Minh · Cái Vồn · Đông Thành
**Lên phường 09/06/2026 (5):** Long Hồ · Tam Bình · Trà Ôn · Tân Quới · Vũng Liêm *(Phường Vũng Liêm gốc là xã Trung Thành)*

### Khu vực Trà Vinh (cũ) — 11 phường
**Từ TP Trà Vinh cũ (4):** Trà Vinh · Long Đức · Nguyệt Hóa · Hòa Thuận
**Từ TX Duyên Hải cũ (2):** Duyên Hải · Trường Long Hòa
**Lên phường 09/06/2026 (5):** Càng Long · Tiểu Cần · Tân Hoà · Hùng Hoà · Tập Ngãi

### Khu vực Bến Tre (cũ) — 11 phường
**Từ TP Bến Tre cũ (5):** An Hội · Phú Khương · Bến Tre · Sơn Đông · Phú Tân
**Lên phường 09/06/2026 (6):** Ba Tri · Bình Đại · Mỏ Cày · Phú Túc · Tiên Thủy · Tân Thủy

## 89 xã

> Nhóm theo `legacyArea` (tên huyện/TX cũ) — chỉ để nhận diện vị trí, **KHÔNG phải cấp hành chính**.

### Khu vực Vĩnh Long (cũ) — 22 xã
**Mang Thít:** Bình Phước · Cái Nhum · Nhơn Phú · Tân Long Hội
**Long Hồ:** An Bình · Phú Quới
**Vũng Liêm:** Hiếu Phụng · Hiếu Thành · Lục Sĩ Thành · Quới An · Quới Thiện · Trung Hiệp · Trung Ngãi
**Tam Bình:** Hòa Bình · Hòa Hiệp · Ngãi Tứ · Song Phú · Trà Côn
**Bình Tân:** Mỹ Thuận · Tân Lược
**Trà Ôn:** Vĩnh Xuân
**(chưa gắn `legacyArea` trong data):** Hậu Lộc

### Khu vực Trà Vinh (cũ) — 30 xã
**Càng Long:** An Trường · Bình Phú · Nhị Long · Tân An
**Châu Thành:** Châu Thành · Hưng Mỹ · Song Lộc
**Cầu Kè:** An Phú Tân · Cầu Kè · Phong Thạnh · Tam Ngãi
**Cầu Ngang:** Cầu Ngang · Hiệp Mỹ · Mỹ Long · Nhị Trường · Vinh Kim
**Duyên Hải:** Đôn Châu · Đông Hải · Hòa Minh · Long Hòa · Long Hữu · Long Thành · Long Vĩnh · Ngũ Lạc
**Trà Cú:** Đại An · Hàm Giang · Long Hiệp · Lưu Nghiệp Anh · Tập Sơn · Trà Cú

### Khu vực Bến Tre (cũ) — 37 xã
**Ba Tri:** An Hiệp · An Ngãi Trung · Bảo Thạnh · Mỹ Chánh Hòa · Tân Xuân
**Bình Đại:** Châu Hưng · Lộc Thuận · Phú Thuận · Thạnh Phước · Thạnh Trị · Thới Thuận
**Châu Thành:** Giao Long · Tân Phú
**Chợ Lách:** Chợ Lách · Hưng Khánh Trung · Phú Phụng · Vĩnh Thành
**Giồng Trôm:** Châu Hòa · Giồng Trôm · Hưng Nhượng · Lương Hòa · Lương Phú · Phước Long · Tân Hào
**Mỏ Cày Bắc:** Nhuận Phú Tân · Phước Mỹ Trung · Tân Thành Bình
**Mỏ Cày Nam:** An Định · Đồng Khởi · Hương Mỹ · Thành Thới
**Thạnh Phú:** An Qui · Đại Điền · Quới Điền · Thạnh Hải · Thạnh Phú
**(chưa gắn `legacyArea` trong data):** Thạnh Phong

## Ghi chú thiết kế

- **Địa danh cũ** (Mang Thít, Tam Bình, Bình Tân, cù lao An Bình…) lưu trong `legacyArea` và `alias` của mỗi xã/phường — chỉ mang tính **tham khảo**, không dùng làm đơn vị phân cấp.
- Website xây theo **hệ thống chính quyền 2 cấp** (tỉnh → xã/phường), nhóm theo khu vực (VL/BT/TV) để tiện duyệt — khu vực là slug lọc, KHÔNG còn là tỉnh riêng.
- Tên huyện cũ (Mang Thít, Long Hồ, Vũng Liêm…) ghi trong `legacyArea` để người dùng địa phương dễ nhận ra vị trí.
- Trong nội dung công khai: gọi vùng đất theo **tỉnh Vĩnh Long mới**; "tỉnh Bến Tre/Trà Vinh" hay "huyện X" chỉ xuất hiện trong văn cảnh lịch sử có chữ "cũ/trước 7-2025".
