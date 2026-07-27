# Đặc tả bổ sung cho `/du-lich`

> Kế thừa `../MASTER.md`. Trạng thái `draft-for-review`.

## 1. Nhiệm vụ

Giúp người dùng chọn một hướng khám phá phù hợp với thời gian, khu vực và sở thích mà không phải quét qua hàng chục card giống nhau.

## 2. Hành động chính

`Chọn cách khám phá` -> áp filter có URL/deep link rõ.

Action phụ: xem bản đồ, thêm vào lịch trình, lưu, đổi khu vực/mùa.

## 3. Bố cục desktop

```text
Breadcrumb + context source
┌ Atlas statement 7c ─────────────────┬ Atlas index 5c ───────────────┐
│ H1 ngắn, mô tả, một ảnh/motif thật   │ Theo nhịp / vùng / mùa        │
│ Không stats trang trí                │ label + icon SVG, không emoji │
└──────────────────────────────────────┴──────────────────────────────┘
Filter ledger: vùng · loại · mùa · sắp xếp · view map/list
Curated route hoặc spotlight duy nhất
Entity results: row/tile tùy density
One editorial field note
Related paths dạng link index, không 4 cross-card giống nhau
```

## 4. Mobile

- H1 + mô tả gọn, không ép hero cao.
- `Chọn cách khám phá` dùng segmented control hoặc list button 44px; không dùng emoji pill.
- Filter mở bottom sheet, chip hàng đầu chỉ hiển thị facet đang active.
- List là mặc định; grid hai cột chỉ dùng khi ảnh đủ chất lượng.
- Map là destination riêng hoặc full-screen state, không split-map chật.

## 5. Chữ ký

`Atlas index` là mục lục có tọa độ nội dung thật: khu vực, mùa, thời lượng và loại. Dòng địa bàn cập nhật khi filter thay đổi và đưa người dùng tới kết quả tương ứng.

## 6. Thứ bậc nội dung

1. Context và cách khám phá.
2. Filter đang áp dụng.
3. Nội dung tuyển chọn có lý do.
4. Toàn bộ kết quả.
5. Gợi ý sang bản đồ/lịch trình.

Không hiển thị 5-7 shelf trước lưới chính. Tối đa một shelf tuyển chọn trước results.

## 7. Cách trình bày entity

- Có ảnh tốt: `EntityTile` với tỷ lệ ảnh cố định, title, khu vực, source, một signal chính.
- Thiếu ảnh: chuyển sang `EntityRow` hoặc placeholder cartographic, không dùng gradient cover lớn.
- Không nhét rating, mùa, OCOP, amenity, CTA, badge vào cùng một card. Chỉ giữ thông tin phục vụ quyết định ở ngữ cảnh hiện tại.

## 8. Trạng thái

- Filter no-result có gợi ý nới facet cụ thể.
- Loading giữ nguyên filter/result geometry.
- API partial failure không xóa filter người dùng.
- Invalid query được chuẩn hóa và giải thích.
- Sort/view mode được giữ khi quay lại từ detail.

## 9. Acceptance

- Không structural emoji.
- Không số liệu hero nếu số liệu không giúp ra quyết định.
- Một người có thể lọc tới kết quả trong tối đa hai thao tác sau khi vào trang.
- Kết quả đầu tiên xuất hiện sớm hơn hiện trạng; không bị nhiều editorial block đẩy xuống.
