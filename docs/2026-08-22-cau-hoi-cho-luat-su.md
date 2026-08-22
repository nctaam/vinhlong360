# Hồ sơ hỏi luật sư — vinhlong360, trước khi bật kênh đính chính

> STATUS: active
> Mục đích: gói gọn **những gì cần luật sư trả lời** thành một tài liệu chủ dự án đưa thẳng
> được, kèm sự thật về hệ thống để luật sư không phải đoán.
> **Đây không phải tư vấn pháp lý.** Mọi trích dẫn dưới đây do tôi tra từ cổng Chính phủ và
> Bộ chủ quản; giới hạn của việc tra cứu ghi ở §5.
> Nguồn chi tiết: `docs/2026-08-21-danh-gia-toan-du-an.md` §2 và §4b.

---

## 1. Dự án là gì, trong ba câu

Website giới thiệu du lịch/OCOP/cộng đồng cho tỉnh Vĩnh Long mới (sáp nhập Vĩnh Long + Bến Tre
+ Trà Vinh từ 07/2025). Một người làm, dưới 10.000 người dùng, ngân sách dưới 1 triệu đồng
mỗi tháng. **Chỉ giới thiệu**: không bán hàng, không đặt chỗ, không thanh toán trên site; CTA
là gọi điện hoặc Zalo tới chủ cơ sở.

Sắp bật thêm **kênh đính chính**: người dân báo thông tin sai về một địa điểm/sản phẩm, ban
biên tập xét, sửa hoặc từ chối, và báo lại kết quả. Kênh này **có thể thu số điện thoại** của
người báo (tuỳ chọn, có ô đồng ý riêng) để nhắn tin báo kết quả.

Hiện **toàn bộ cờ tính năng của kênh này đang TẮT**. Chưa có người dùng thật nào đi qua nó.

---

## 2. Bốn câu hỏi cần trả lời

### Câu 1 — Dự án thuộc nhóm nào theo Luật 91/2025, và vì thế được miễn gì?

**Vì sao hỏi:** Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15 (thông qua 26/06/2025, hiệu lực
**01/01/2026**) cho **doanh nghiệp nhỏ và doanh nghiệp khởi nghiệp** *"được quyền lựa chọn
thực hiện hoặc không thực hiện"* các quy định về **lập hồ sơ đánh giá tác động** và **chỉ định
bộ phận/nhân sự bảo vệ dữ liệu cá nhân**, trong **05 năm** kể từ ngày Luật có hiệu lực; và
**miễn thực hiện đối với hộ kinh doanh, doanh nghiệp siêu nhỏ**.

**Cần luật sư xác định:** vinhlong360 hiện đang vận hành dưới tư cách pháp lý nào (cá nhân? hộ
kinh doanh? chưa có pháp nhân?), và tư cách đó rơi vào nhóm nào ở trên. Câu trả lời quyết định
**có phải dựng hồ sơ đánh giá tác động trước khi bật cờ hay không** — một việc tốn nhiều công
sức với người làm một mình.

**Câu hỏi phụ:** nếu hiện chưa có pháp nhân, việc lập hộ kinh doanh có làm nhẹ hay nặng thêm
nghĩa vụ so với hiện trạng?

### Câu 2 — Nghĩa vụ nào KHÔNG được miễn, và hệ thống đã đủ chưa?

Miễn trừ ở Câu 1 chỉ chạm hai nghĩa vụ *thủ tục*. Các nghĩa vụ *nội dung* không miễn cho ai.
Bảng dưới là **hiện trạng thật của hệ thống**, để luật sư đối chiếu:

| Nghĩa vụ | Hệ thống hiện có | Ghi chú |
|---|---|---|
| Sự đồng ý trước khi thu số điện thoại | ✅ Ô đồng ý riêng, chỉ hiện khi người dùng nhập số; nhập số mà không tick thì **chặn gửi** | |
| Giới hạn mục đích | ✅ Câu chữ: *"dùng số này để báo kết quả yêu cầu, và chỉ việc đó"* | |
| **Rút lại đồng ý** | ✅ Vừa mở đường (2026-08-22) | Trang chính sách hứa **15 ngày**; trước đó API không nhận được yêu cầu rút |
| Quyền xoá | ⚠️ Có đường xoá **tài khoản** (30 ngày) | Người báo **ẩn danh không có tài khoản** — cần xác định họ dùng đường nào |
| Thông báo thời hạn lưu | ❌ Chính sách chỉ ghi *"trong thời gian cần thiết"* | Hệ thống thật dùng **90 ngày** sau khi khép hồ sơ (số điện thoại), 365 ngày (chứng cứ riêng tư), 730 ngày (liên kết thống kê) |
| Thông báo khi có vi phạm dữ liệu | ⚠️ Chính sách có mục 5 | Chưa đối chiếu thời hạn theo Luật mới |

**Cần luật sư trả lời:**
1. Thời hạn 90/365/730 ngày có phải **nêu cụ thể** trong chính sách không, hay ghi "thời gian
   cần thiết" là đủ?
2. Người báo **ẩn danh** (không tài khoản) thực hiện quyền xoá bằng cách nào cho đúng luật?
3. Cam kết "rút lại đồng ý trong 15 ngày" đang ghi trong chính sách — có phải là mốc phù hợp,
   hay Luật đòi ngắn hơn?

### Câu 3 — Mô hình doanh thu có đẩy site thành sàn giao dịch TMĐT không?

**Đây là câu tôi cho là rủi ro nhất, và nó chưa từng được đặt ra trong tài liệu dự án.**

Sự thật đã tra được:

- Sau NĐ85/2021, nghĩa vụ **thông báo** với Bộ Công Thương chỉ phát sinh với website bán hàng
  **có chức năng đặt hàng trực tuyến**. Site không có nút đặt hàng → **không phải thông báo**.
  Điểm này dự án đang làm đúng.
- Nhưng NĐ52/2013 xếp *"trưng bày giới thiệu hàng hóa, dịch vụ"* là **mắt xích đầu tiên** của
  quy trình thương mại, và website **cho phép người tham gia mở gian hàng** để trưng bày đã bị
  xếp là một **hình thức hoạt động của sàn giao dịch TMĐT**.
- Mạng xã hội bị coi là sàn khi hội đủ **HAI điều kiện đồng thời**: (a) có một trong các hình
  thức tại điểm a/b/c khoản 2 Điều 35, **VÀ** (b) người tham gia **trả phí trực tiếp hoặc gián
  tiếp** cho hoạt động đó.
- Nếu bị xếp là sàn: nghĩa vụ nhảy từ *thông báo* lên **ĐĂNG KÝ**, kèm công bố thông tin người
  sở hữu theo Điều 29 **trên trang chủ**.

**Hiện trạng:** doanh thu dự kiến là **premium/featured listing** — chủ cơ sở trả tiền để được
hiển thị nổi bật. Đó là **phí trực tiếp cho việc trưng bày**, tức đã thoả nửa điều kiện (b).
Hiện **chưa** có gian hàng tự quản: chủ cơ sở không tự sửa trang của mình, mọi thay đổi đi qua
ban biên tập.

**Cần luật sư trả lời:**
1. Với hiện trạng (có phí trưng bày, **không** có gian hàng tự quản), site có bị coi là sàn không?
2. Nếu sau này mở tính năng cho chủ cơ sở **tự sửa/tự quản lý trang của mình** — kể cả chỉ để
   sửa giờ mở cửa — thì có vượt ranh giới không? *(Kênh đính chính là hàng xóm rất gần của
   tính năng này.)*
3. Có cách cấu trúc gói premium nào **không** tính là "trả phí cho hoạt động trưng bày" không?

### Câu 4 — NĐ147/2024: site có phải xin giấy phép không?

NĐ147/2024 (hiệu lực 25/12/2024) Điều 24 miễn cấp phép cho *"trang thông tin điện tử cung cấp
dịch vụ chuyên ngành"*, và Điều 3 khoản 23 liệt kê **"văn hóa, thể thao và du lịch"** là một
lĩnh vực chuyên ngành. **Tôi chưa đọc được toàn văn Điều 24** (xem §5), nên không biết miễn
trừ này kèm điều kiện gì.

Ràng buộc đã tra được với **"trang thông tin điện tử tổng hợp"**: đăng lại tin **chậm hơn 1
giờ** so với nguồn; nguồn từ **≥3 cơ quan báo chí**; **người dùng không được bình luận** trên
bài của trang tổng hợp.

**Hiện trạng:** site tự sản xuất nội dung về địa phương; với tin báo chí thì **chỉ trích tiêu
đề + đoạn ngắn + link gốc**, không đăng lại nguyên văn. Site **có** khu vực cộng đồng cho
người dùng đăng bài và bình luận.

**Cần luật sư trả lời:**
1. Với cách dùng tin báo như trên, site có bị xếp là "trang thông tin điện tử tổng hợp" không?
2. Nếu có, quy định "người dùng không được bình luận" áp dụng thế nào với khu vực cộng đồng?
3. Điều kiện kèm theo của miễn trừ Điều 24 là gì, và site có thoả không?

---

## 3. Hai mốc thời gian luật sư nên biết

- **24 giờ**: pháp luật TMĐT đặt mốc này để gỡ thông tin hàng hoá/dịch vụ vi phạm **khi cơ quan
  quản lý nhà nước có thẩm quyền yêu cầu**. Chính sách nội bộ của kênh đính chính hiện dùng
  nhịp **3 ngày** cho cập nhật thông thường — hai việc khác nhau, nhưng cần biết mốc 24 giờ tồn
  tại để làm đường ưu tiên riêng.
- **5 năm** kể từ 01/01/2026 (tức tới **01/01/2031**): cửa sổ mà doanh nghiệp nhỏ/khởi nghiệp
  được chọn không lập hồ sơ đánh giá tác động.

## 4. Chế tài, để cân nhắc mức độ thận trọng

| Hành vi | Mức |
|---|---|
| Mua/bán dữ liệu cá nhân (**cấm tuyệt đối**) | tới **10 lần** khoản thu bất hợp pháp |
| Chuyển dữ liệu xuyên biên giới trái quy định | tối đa **5% doanh thu năm trước** |
| Vi phạm khác | tới **3 tỷ đồng** |
| Cá nhân vi phạm | **một nửa** mức của tổ chức |

Trần 3 tỷ đồng đặt cạnh ngân sách dưới 1 triệu đồng/tháng là lý do nên hỏi trước khi bật cờ,
chứ không phải sau.

## 5. Giới hạn của phần tra cứu này

- Bản ký gốc Luật 91/2025 trên `datafiles.chinhphu.vn` là **PDF ảnh scan**; máy không có công
  cụ OCR, nên **tôi không đọc được từng điều khoản**. Các con số ở §2 và §4 lấy từ Cổng TTĐT
  Chính phủ (`xaydungchinhsach.chinhphu.vn`) và Bộ Công an (`mps.gov.vn`), **khớp chéo giữa hai
  nguồn** — nhưng không phải trích trực tiếp từ luật.
- `thuvienphapluat.vn` chặn truy cập (403); `mic.gov.vn` không phân giải được DNS lúc tra.
  **Toàn văn Điều 24 NĐ147/2024 vì vậy chưa đọc được.**
- Các nghĩa vụ có mốc thời gian cụ thể của Luật 91/2025 (thời hạn đáp ứng yêu cầu của chủ thể
  dữ liệu, thời hạn thông báo vi phạm) **chưa tra được số ngày chính xác** — cần luật sư đọc
  bản chính.
- Phần EU DSA trong báo cáo đánh giá là **tham chiếu thiết kế**, không ràng buộc ở Việt Nam.

## 6. Việc chủ dự án nên chuẩn bị trước khi gặp

1. Tư cách pháp lý hiện tại (cá nhân / hộ kinh doanh / doanh nghiệp — có mã số thuế chưa).
2. Doanh thu dự kiến từ premium/featured listing: hình thức thu, ai trả, trả cho cái gì.
3. Bản in trang chính sách bảo mật hiện tại (`/chinh-sach-bao-mat`) và điều khoản sử dụng.
4. Tài liệu này, cùng `docs/2026-08-21-danh-gia-toan-du-an.md` §2 và §4b.
