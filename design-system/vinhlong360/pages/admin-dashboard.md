# Đặc tả bổ sung cho `/admin`

> Kế thừa `../MASTER.md`. Trạng thái `draft-for-review`.

## 1. Nhiệm vụ

Admin dashboard là **Bàn điều phối vận hành**, không phải trang trình diễn KPI. Nó phải trả lời:

1. Có việc gì cần xử lý ngay?
2. Hệ thống hoặc dữ liệu nào đang suy giảm?
3. Người dùng hiện tại có quyền thực hiện hành động nào?

## 2. Hành động chính

`Mở công việc ưu tiên cao nhất` theo scope và dữ liệu thật.

Không đặt một CTA chung như `Thêm mới` nếu dashboard không biết loại công việc.

## 3. Composition desktop

```text
Role/scope context · last refresh · command palette
Priority queue: severity · age/SLA · owner · next action
Health ledger: API · data · moderation · release · backup
┌ Queue volume 7c ─────────────────────┬ Exceptions 5c ───────────────┐
│ trend + table, không KPI card grid   │ cảnh báo có link xử lý       │
└──────────────────────────────────────┴──────────────────────────────┘
Recent changes / audit relevant to current role
Secondary analytics, collapsed or linked to dedicated pages
```

## 4. Navigation

- Sidebar group theo công việc: Vận hành, Nội dung & dữ liệu, Tin cậy, Người dùng & bảo mật, Cài đặt.
- Menu render theo scope; route không đủ quyền có 403 state rõ.
- Icon SVG cùng family, không emoji/numeric entity.
- Count chỉ xuất hiện với queue có hành động; không dùng badge trang trí.
- Sidebar collapsed vẫn giữ accessible name và tooltip keyboard-reachable.

## 5. Trình bày dữ liệu

- Thay 6 `dash-stat-card` bằng một `HealthLedger` hoặc metric strip có baseline và trend.
- Alert sắp xếp theo severity -> SLA -> age, không theo loại widget.
- Chart phải có insight title, bảng dữ liệu thay thế và trạng thái no-data/error.
- Không tạo donut chỉ để lấp chỗ; nếu phân bổ loại không dẫn tới hành động, chuyển sang dedicated stats page.
- Số liệu dùng tabular figures và format locale `vi-VN`.

## 6. Mobile/tablet

- Queue list đứng trước metric.
- Sidebar trở thành drawer/task switcher, không phải dải navigation cuộn ngang hàng chục mục.
- Table quan trọng có sticky primary column + detail sheet; bulk action bar sticky khi có selection.
- Action destructive không nằm sát navigation/back.

## 7. Partial failure

- Mỗi panel có loading/error/stale riêng.
- Dữ liệu cũ phải có timestamp và nhãn `Dữ liệu chưa cập nhật`.
- Refresh không xóa dashboard hiện có; dùng stale-while-refresh.
- Permission failure tách khỏi network failure.

## 8. Chữ ký

Dòng địa bàn trở thành `Workstream Line`: nguồn sự cố/hàng đợi -> trạng thái -> owner -> next action. Nó dùng cùng visual DNA public nhưng mang nghĩa vận hành.

## 9. Acceptance

- Không structural emoji hoặc HTML numeric icon.
- Không hero/gradient trang trí.
- Người dùng có thể mở việc ưu tiên cao nhất trong một thao tác.
- Moderator chỉ thấy moderation surface hợp lệ; admin/superadmin thấy đúng scope.
- Dashboard vẫn hữu ích khi một trong các API con bị lỗi.
