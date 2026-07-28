# Đặc tả bổ sung cho trang chủ `/`

> Kế thừa `../MASTER.md`. Trạng thái `draft-for-review`.

## 1. Nhiệm vụ

Trong 10 giây đầu, người dùng phải biết:

1. Hệ thống đang hiểu họ ở khu vực nào.
2. Có thông tin chính thức nào cần chú ý ngay không.
3. Hôm nay có gì gần họ và họ có thể làm gì tiếp theo.

Trang chủ không còn là landing page du lịch. Đây là **Bảng tin địa phương thích ứng** của super app.

## 2. Primary action

`Tìm kiếm địa điểm, dịch vụ hoặc thông tin khu vực`.

Action phụ theo context: `Xem gần tôi`, `Mở cảnh báo`, `Chỉ đường`, `Lưu`, `Tham gia cộng đồng`.

## 3. Bố cục desktop

```text
┌ Context: Vĩnh Long · vị trí đang dùng/tắt · đổi khu vực ─────────────┐
│ Brand        Universal search                         User / alerts  │
├──────────────────────────────────────────────────────────────────────┤
│ OFFICIAL SIGNAL                                                     │
│ cảnh báo/khuyến cáo chính thức; ẩn hoàn toàn khi không có dữ liệu    │
├───────────────────────────────────────┬──────────────────────────────┤
│ Bản tin địa phương                  8c│ Việc có thể làm ngay       4c│
│ thời tiết/sự kiện/giao thông/dịch vụ   │ chỉ đường, gọi, lưu, theo dõi│
├───────────────────────────────────────┴──────────────────────────────┤
│ Gần bạn · list/map preview · có “Vì sao bạn thấy nội dung này”       │
├──────────────────────────────────────────────────────────────────────┤
│ Một editorial feature có ảnh thật, không lặp thành nhiều hero         │
├───────────────────────────────┬──────────────────────────────────────┤
│ Cộng đồng có moderation       │ Khám phá theo sở thích               │
└───────────────────────────────┴──────────────────────────────────────┘
```

## 4. Bố cục mobile

```text
Context location + privacy status
Search full-width
Official signal
Local briefing list
Near-you map/list toggle
Actions relevant to current items
One editorial feature
Community
Interest discovery
Bottom navigation
```

- Không dùng nhiều horizontal carousel liên tiếp.
- Module quan trọng là vertical list; carousel chỉ dùng cho ảnh/collection có nhu cầu so sánh ngang.
- Sticky chrome phải chừa safe-area và không che content cuối trang.

## 5. Quy tắc nội dung

- `Chính thức` luôn đứng trước `Đã xác minh`, sau đó mới tới `Cộng đồng`.
- Module không có dữ liệu thật thì ẩn hoặc dùng empty state có hành động; không tạo số liệu mẫu.
- Personalization chỉ thay thứ tự và gợi ý, không thay navigation cốt lõi.
- Mọi module cá nhân hóa có menu `Vì sao bạn thấy nội dung này`.
- Context control gồm: đổi khu vực, chỉnh sở thích, tắt vị trí, đặt lại đề xuất.

## 6. Chữ ký

`Dòng địa bàn` nối context khu vực với các signal chính trong Local Briefing. Trên mobile, nó trở thành một rail dọc bên trái danh sách, không trở thành progress giả.

## 7. Quy tắc thị giác

- Không dùng hero full-viewport, Ken Burns hoặc ảnh vàng hoàng hôn ở viewport đầu.
- Search và official signal tạo hierarchy, không dùng gradient để gây chú ý.
- Editorial image chỉ xuất hiện sau phần utility đầu tiên.
- Section dùng divider, index và khoảng trắng; không bọc mọi section vào card.

## 8. Trạng thái bắt buộc

- Guest cold start: yêu cầu chọn khu vực, không tự nhận vị trí chính xác.
- Có IP gần đúng nhưng chưa consent: ghi `Khu vực ước tính`, cho sửa ngay.
- Location denied/off: vẫn dùng khu vực người dùng đã chọn.
- Official alert active/expired/stale.
- Partial API failure: module lỗi riêng, không chặn toàn trang.
- Returning user: khôi phục scroll/state hợp lý, không nhảy module khi hydration.
- No personalization signal: dùng editorial/default ranking và không gọi là `Dành cho bạn`.

## 9. Acceptance

- Người dùng nhận ra đây là super app địa phương, không phải site du lịch thuần.
- Cảnh báo chính thức nhìn thấy trước community/discovery khi có dữ liệu.
- Không entity nào lặp quá một lần trong vùng đầu trang.
- Viewport đầu có tối đa một surface elevated.
- CLS dưới 0.1; skeleton mô phỏng đúng module.
