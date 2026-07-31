# Đặc tả bổ sung cho `/dia-diem/[id]`

> Kế thừa `../MASTER.md`. Trạng thái `approved-design`.

**Ánh xạ Adaptive Nocturne:** thuộc family **Dossier / Detail**, dùng Framed
Dossier với tỷ lệ định hướng 56% Nocturne / 44% Parchment. Controlled Serif chỉ
dùng cho H1/tên địa danh hoặc narrative highlight; source, freshness, facts và
action dùng Be Vietnam Pro. Skeleton, trust tier và primary action giữ cùng
anatomy ở desktop/mobile.

## 1. Nhiệm vụ

Giúp người dùng xác minh đây có đúng nơi/dịch vụ họ cần không, sau đó gọi, nhắn Zalo hoặc chỉ đường một cách tự tin.

## 2. Hành động chính

- Có tọa độ: `Chỉ đường`.
- Không có tọa độ nhưng có số điện thoại: `Gọi`.
- Không có hai dữ liệu trên: `Thêm vào lịch trình` hoặc `Xem nội dung liên quan`, tùy loại entity.

Zalo, lưu, chia sẻ, theo dõi và báo sai là secondary action.

## 3. Composition desktop

```text
Breadcrumb
SourceMark · freshness · area
┌ Title + concise summary 7c ──────────┬ Action dock 5c ──────────────┐
│ Media plate / honest placeholder     │ Primary action               │
│ key factual meta                     │ Gọi · Zalo · Lưu · Chia sẻ   │
└──────────────────────────────────────┴ Trust/freshness ─────────────┘
┌ Story / description 8c ──────────────┬ Facts rail 4c ───────────────┐
│ practical sections                   │ địa chỉ, giờ, giá tham khảo   │
│ source-backed recommendations        │ nguồn, cập nhật, báo sai      │
└──────────────────────────────────────┴──────────────────────────────┘
Map / relationships / nearby
Community review and posts, clearly separated from official data
```

## 4. Mobile

- SourceMark và title xuất hiện trước media.
- Facts dùng definition list, không là 17 hàng emoji.
- Sticky action bar tối đa ba action nhìn thấy: primary, gọi/Zalo phù hợp, lưu; phần còn lại vào More sheet.
- Sticky bar chừa safe-area; content có bottom padding tương ứng.

## 5. Mô hình độ tin cậy

- `SourceMark` luôn nằm trong vùng đầu trang.
- Official/verified facts và community review tách bằng heading/label, không trộn vào một stream.
- `FreshnessLine` nói rõ lần cập nhật và stale state.
- Chỉ một affordance `Báo sai hoặc bổ sung nguồn` chính.
- Nội dung AI có disclosure riêng và không đứng cao hơn dữ liệu nguồn.

## 6. Chữ ký

Dòng địa bàn đi từ `Nguồn` -> `Cập nhật` -> `Vị trí` -> `Hành động`. Nếu thiếu một nút, đường vẫn giữ trật tự nhưng hiển thị `Chưa có dữ liệu`, không giả lập.

## 7. Media

- Ảnh thật có credit/provenance, kích thước cố định tránh CLS.
- Thiếu ảnh dùng bản đồ/motif category có nhãn `Chưa có ảnh xác minh`.
- Không dùng AI image để minh họa mặt tiền dịch vụ như ảnh thực tế.
- Lightbox và gallery giữ keyboard, focus trap, caption và disclosure.

## 8. Trạng thái

- 404, private/unpublished, missing coords, missing contact, stale source.
- Contact action unavailable phải giải thích, không chỉ biến mất.
- Map fail có địa chỉ copyable và link mở map ngoài.
- Save/follow/visit auth gate giữ context sau đăng nhập.
- Report success có undo/edit nếu phù hợp.

## 9. Acceptance

- Trong viewport đầu thấy title, source, area và ít nhất một hành động hợp lệ.
- Không structural emoji; không CTA trùng.
- Official facts và community content không thể bị hiểu nhầm là cùng nguồn.
- Mobile action bar không có hơn ba action trực tiếp.
