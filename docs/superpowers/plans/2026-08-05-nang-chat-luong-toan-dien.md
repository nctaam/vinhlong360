# Kế hoạch nâng chất lượng vinhlong360 lên mức trần khả thi

> STATUS (2026-08-05): active — kế hoạch dài hạn, thực thi theo đợt.

## 0. Định nghĩa "10/10" cho dự án này

10/10 tuyệt đối không tồn tại. Ở đây nó được định nghĩa đo được:

| Chiều | Hôm nay | Đích | Cách đo (lệnh/truy vấn cụ thể) |
|---|---:|---:|---|
| Dữ liệu & nội dung | 3,0 | 9 | độ phủ ảnh ≥30%; mô tả <200 ký tự ≤15%; 0 lỗi kiểm chứng critical/high |
| Kiểm thử | 5,0 | 9 | test grep-source ≤5%; coverage `server.py`/`auth.py`/`social.py` ≥60% |
| Vận hành | 5,5 | 9 | 1 nhánh chính; backup offsite chạy tự động; 0 file rác >100 MB |
| Cổng chất lượng | 6,0 | 9 | scorecard chạy hàng tuần; 0 cổng chỉ kiểm sự-có-mặt-của-file |
| Sản phẩm/UX | 5,5 | 9 | 4 luồng chính đo được trên browser thật; cộng đồng mở hoặc gỡ khỏi nav |
| Bảo mật & pháp lý | 6,5 | 9 | 0 secret trong git; `.env.example` phủ 100% biến bí mật; hồ sơ NĐ147 rõ trạng thái |
| Backend | 7,0 | 9 | complexity ≤ baseline; 0 route trùng; hợp đồng API phủ ≥80% route |
| Frontend | 6,5 | 9 | CSS trong `<style scoped>` ≤40%; 0 hex cứng ngoài `variables.css` |

Tổng mục tiêu: **9/10**. Điểm 10 chỉ đạt khi có thêm thứ nằm ngoài tầm một người:
người kiểm chứng nội dung độc lập thường trực, và dữ liệu thực địa có `verifiedAt`.

---

## 1. Nguyên tắc rút ra từ đợt làm việc 2026-08-04/05

Ba bài học này quyết định cách viết kế hoạch, không phải lý thuyết:

1. **Gác cổng chuỗi không thay được người kiểm chứng.** Gác cổng báo "0 bản bị
   chặn" ba lần liên tiếp, trong khi người kiểm chứng độc lập tìm ra 15 lỗi ở 36
   bản và 53 lỗi ở 93 bản. Lỗi lọt đều là loại không có từ cấm: "mỗi lần", "đều",
   "thuộc", "nên", "nhìn thẳng ra".
2. **Ngưỡng số ép ra dối trá.** Ngưỡng cứng 200 ký tự khiến 148 bản đạt chuẩn
   bằng cách liệt kê thứ hồ sơ KHÔNG có. Bỏ ngưỡng thì tỉ lệ bỏ qua nhảy lên 90%
   — và đó mới là con số đúng.
3. **Test đông không bằng test đúng tầng.** 9.535 test backend xanh trong khi
   `/api/me/activity` khai báo hai lần và rỗng với mọi user, vì mọi test chỉ
   import router của module mình.

---

## Đợt A — Nội dung (quyết định điểm số, làm trước)

Nút thắt số một. Không đợt nào khác dịch chuyển tổng điểm bằng đợt này.

### A1. Ảnh: 3,3% → 30%
- Bật dịch vụ ảnh ở `localhost:20128` (hiện tắt, đây là chặn cứng).
- Chạy `scripts/gen_entity_images.py` theo lô 20, ưu tiên: entity có mô tả tốt
  sẵn > điểm tham quan/làng nghề > món ăn > xã/phường.
- Sau mỗi lô: xem toàn bộ ảnh, loại ảnh sai chủ thể. Prompt đã sửa nhưng vẫn phải
  nhìn — một tô bún từng nhận prompt "kiến trúc di sản".
- Đích: ~520 entity có ảnh. Ước lượng 26 lô.

### A2. Nội dung: 697 mô tả mỏng → ≤260
- **Không viết tiếp bằng LLM cho nhóm nghèo dữ kiện.** Đợt vừa rồi chứng minh:
  bản ghi chỉ có `schema_type` + `coords_approximate` thì mọi câu thêm vào đều là
  bịa. Việc cần làm là **bổ sung dữ kiện thật** trước: giờ mở cửa, giá, món, liên hệ.
- Cách rẻ nhất: form nhập nhanh trong AdminCP cho 5 trường đó, nhập dần khi đi
  thực địa hoặc gọi điện xác nhận.
- Với entity đã đủ dữ kiện: viết theo quy trình đã chuẩn hoá (viết → gác cổng →
  **người kiểm chứng độc lập** → mới ghi). Không bỏ bước kiểm chứng, kể cả khi gấp.

### A3. Kiểm chứng thực địa
- `verifiedAt` hiện 0/1751. Đặt mục tiêu 50 entity trọng điểm có `verifiedAt` thật
  (đi tới nơi, chụp, ghi ngày). Đây là điều kiện để gỡ bỏ giới hạn §1.7 và mở
  đường cho mọi tuyên bố tin cậy về sau.

---

## Đợt B — Kiểm thử đúng tầng

### B1. Thay test grep-source
- 1.754/5.253 test backend chỉ assert chuỗi trong source. Chúng đỏ khi refactor
  đúng và xanh khi hành vi sai — vừa cản vừa che.
- Cách làm: mỗi lần chạm một module, thay test grep-source của module đó bằng test
  gọi hành vi thật. Không làm một lượt; gắn vào từng lần sửa.
- Đích: ≤5% (từ 33,4%).

### B2. Coverage ba vùng mù
- `server.py` 21%, `auth.py` 25%, `social.py` 18% — đúng ba module CLAUDE.md §B3
  gọi là vùng mù. Nâng lên ≥60% bằng test hành vi, ưu tiên đường đi có tiền/có
  quyền: đăng nhập, 2FA, phân quyền, xoá tài khoản.

### B3. Test cô lập trạng thái
- Test hiện phụ thuộc DB cục bộ nên đỏ giả (đã gặp thật với
  `test_search_entities_by_area`). Mỗi test file cần fixture DB riêng.

---

## Đợt C — Vận hành

### C1. Gộp nhánh
- 18 worktree, `main` lệch 93/133 commit. Chi phí merge tăng theo ngày.
- Thứ tự: gộp nhánh đã xong QA trước, mỗi lần một nhánh, chạy full suite sau mỗi
  lần. Đích: ≤3 nhánh sống.
- **Chặn hiện tại**: complexity 26 > baseline 14, toàn bộ thuộc họ `itinerary_*`.
  Phải refactor `select_and_schedule_day()` (CC=126) trước, hoặc tách nhánh đó ra
  khỏi lần merge.

### C2. Backup offsite tự động
- Backup hiện chạy tay. Có `scripts/backup_offsite.py` nhưng chưa lịch hoá.
- Đặt cron hàng ngày + kiểm tra khôi phục thử mỗi tháng. DB là tài sản không tái
  tạo được.

### C3. Dọn rác định kỳ
- Đã dọn 1.469 MB backup và sửa log rotation trong đợt này. Thêm một script dọn
  chạy hàng tuần để không tái diễn.

---

## Đợt D — Cổng chất lượng

### D1. Scorecard sống lại
- Entry cuối 2026-07-10, ghi backend 99/100 trong khi thực đo 88. Một đồng hồ
  đứng yên nguy hiểm hơn đồng hồ sai, vì nó vẫn được dùng làm bằng chứng.
- Chạy `scorecard.py` mỗi tuần, ghi history. Chấp nhận điểm tụt — số thật quan
  trọng hơn số đẹp.

### D2. Rà soát các cổng còn lại
- R20.5 từng chỉ kiểm "file có được staged không" (đã sửa). Rà từng checker trong
  `scripts/checks/` với cùng câu hỏi: **nó có đọc nội dung không, hay chỉ kiểm sự
  có mặt?**

### D3. Cổng nội dung
- Thêm checker chạy `thin_description_writer.check_no_invention` trên toàn DB,
  báo số mô tả vi phạm. Biến kiểm chứng nội dung thành cổng thường trực thay vì
  việc làm một lần.

---

## Đợt E — Sản phẩm

### E1. Quyết định về Cộng đồng
- Trang hiện ở trạng thái "sắp mở" nhưng vẫn nằm trên thanh điều hướng chính.
  Hoặc mở thật (cần Postgres chạy), hoặc gỡ khỏi nav. Trạng thái lửng làm người
  dùng mất niềm tin.

### E2. Bốn luồng chính có bằng chứng browser
- Tìm kiếm, Khám phá, Chi tiết, Bản đồ: mỗi luồng một kiểm tra browser thật chạy
  được trong CI hoặc release gate, không phải screenshot thủ công.

### E3. Hoàn tất hệ màu
- Đã phủ 10 trang. Còn các trang admin và trang phụ. Đích: 0 trang dùng legacy
  `--primary` ngoài `catalog.css`/`detail.css`.

---

## Thứ tự thực thi

1. **A1 + A2** (nội dung) — dịch chuyển điểm mạnh nhất, và đang bị chặn bởi một
   dịch vụ chưa bật.
2. **C1** (gộp nhánh) — chi phí tăng theo ngày, càng để lâu càng đắt.
3. **B1 + B2** (test đúng tầng) — điều kiện để refactor an toàn về sau.
4. **D1 + D3** (cổng sống) — giữ cho ba đợt trên không trôi ngược.
5. **E** (sản phẩm) — sau khi nội dung đủ dày, vì trước đó UX bị trần nội dung chặn.

## Điều kiện dừng, phải hỏi chủ dự án

- Bật/không bật dịch vụ ảnh và LLM cục bộ (chặn Đợt A).
- Cách xử lý nợ complexity `itinerary_*` (chặn Đợt C1).
- Mở hay gỡ trang Cộng đồng (E1).
- Mọi thao tác xoá dữ liệu, push, deploy.
