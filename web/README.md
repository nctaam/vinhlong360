# vinhlong360 — Web (Cổng du lịch & sản phẩm địa phương)

Website **du lịch + sản phẩm địa phương** cho Vĩnh Long — tĩnh, **không cần build**, chạy bằng cách mở file hoặc serve tĩnh.

## Chạy thử

**Cách 1 — mở trực tiếp:** double-click `index.html` (chạy được nhờ không dùng ES module import).

**Cách 2 — serve tĩnh (khuyến nghị):**

```powershell
cd C:\Code\vinhlong360\web
python -m http.server 5173    # rồi mở http://localhost:5173
# hoặc: npx serve C:\Code\vinhlong360\web
```

## Sơ đồ trang (hash routing, không cần server-side)

| Đường dẫn | Trang |
|---|---|
| `#/` | Trang chủ: hero, "đang vào mùa", trải nghiệm/đặc sản nổi bật, lịch trình, theo vùng |
| `#/du-lich` | Du lịch: trải nghiệm · tham quan · lưu trú · làng nghề · ẩm thực (lọc loại/vùng/mùa/từ khóa) |
| `#/san-pham` | Sản phẩm địa phương: đặc sản & OCOP (mặc định theo **tháng hiện tại**, lọc OCOP/mùa/vùng) |
| `#/lich-trinh` | Danh sách lịch trình gợi ý |
| `#/lich-trinh/:id` | Chi tiết lịch trình (timeline điểm dừng) |
| `#/khu-vuc/:area` | Trang khu vực: vinh-long · ben-tre · tra-vinh (danh sách xã/phường + nội dung) |
| `#/e/:id` | **Hồ sơ số** một thực thể: mùa vụ, OCOP, giá, quan hệ đồ thị, nguồn + độ tin cậy |
| `#/tim?q=...` | Kết quả tìm kiếm |

## Cấu trúc mã & vì sao không phải đồ bỏ đi

| File | Vai trò |
|---|---|
| [`data.js`](data.js) | Dữ liệu hạt giống: 124 xã/phường (mô hình 2 cấp) + `entities` + `relationships` + `itineraries` (mỗi mục có `source`/`confidence`/`updatedAt`) |
| [`store.js`](store.js) | **Lớp truy vấn** (không đụng DOM): lọc, duyệt quan hệ, tìm kiếm, mùa vụ. *Đây là phần sẽ thay bằng API PostgreSQL/GraphRAG* |
| [`ui.js`](ui.js) | Router hash + các view. Chỉ đọc dữ liệu qua `window.Store` |
| [`styles.css`](styles.css) | Giao diện đầy đủ (topbar, hero, card, trang chi tiết, timeline, responsive) |

Ranh giới `store.js` ↔ `ui.js` chính là ranh giới kiến trúc: khi lên production, chỉ cần đổi thân các hàm trong `store.js` thành lệnh gọi API — `ui.js` không phải sửa. Mô hình dữ liệu khớp [`../docs/kien-truc-va-lo-trinh.md`](../docs/kien-truc-va-lo-trinh.md).

## ⚠️ Lưu ý dữ liệu

Dữ liệu mùa vụ, giá & địa điểm là **hạt giống (seed) minh họa**, cần chủ thể địa phương xác nhận — vì vậy mỗi mục có "độ tin cậy" và nguồn. Đơn vị hành chính xây theo **hệ thống chính quyền 2 cấp** (tỉnh → 124 xã/phường, bỏ cấp huyện) từ 1/7/2025. Tên địa danh cũ (huyện, TP, TX) chỉ mang tính tham khảo.
