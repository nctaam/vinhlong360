# Kế hoạch đưa vinhlong360 thành sản phẩm thực chiến

> STATUS (2026-08-05): active — kế hoạch dài hạn, thực thi theo đợt.

## 0. "Thực chiến" nghĩa là gì ở đây

Không phải "code đẹp". Thực chiến = **chịu được người dùng thật, tiền thật, và
luật thật, do một người vận hành với ngân sách dưới 1 triệu/tháng**.

Năm trụ, mỗi trụ có ngưỡng đo được. Thiếu bất kỳ trụ nào thì không được mở cho
công chúng, bất kể code tốt tới đâu.

| Trụ | Câu hỏi sống còn | Ngưỡng đạt |
|---|---|---|
| **ĐÚNG** | Thông tin có làm người ta đi sai chỗ không? | 0 lỗi nội dung critical; ≥30% entity có ảnh; ≥50 entity có `verifiedAt` thật |
| **SỐNG** | Sập lúc 2h sáng thì bao lâu biết, bao lâu dậy? | Cảnh báo ≤5 phút; RTO ≤2 giờ; RPO ≤24 giờ; đã diễn tập khôi phục ít nhất 1 lần |
| **AN TOÀN** | Một người xấu làm được gì? | 0 secret trong git; rate limit mọi endpoint ghi; 2FA có `TOTP_ENC_KEY`; đã tự rà OWASP Top 10 |
| **HỢP PHÁP** | Bị hỏi giấy tờ thì có gì? | Trạng thái NĐ147 rõ ràng; chính sách riêng tư đúng NĐ13; cơ chế gỡ nội dung ≤24 giờ |
| **TRẢ NỔI** | 10.000 lượt/tháng thì hết bao nhiêu? | Chi phí đo được và < 1 triệu/tháng ở tải mục tiêu; có ngưỡng cảnh báo chi phí |

**Điểm hiện tại: 5,5/10. Đích khả thi: 9/10.** Điểm 10 cần thứ ngoài tầm một
người — người kiểm chứng nội dung thường trực và dữ liệu thực địa diện rộng.

---

## 1. Ba bài học buộc phải tuân theo

Rút từ chính đợt làm việc 2026-08-04/05, không phải lý thuyết:

1. **Gác cổng chuỗi không thay được người kiểm chứng.** Nó báo "0 bản bị chặn"
   ba lần liên tiếp; người kiểm chứng độc lập tìm 15 lỗi ở 36 bản, 53 lỗi ở 93
   bản. Lỗi lọt không chứa từ cấm nào — chỉ là "mỗi lần", "đều", "thuộc", "nên",
   "nhìn thẳng ra". ⇒ **Mọi nội dung ra mặt người dùng phải qua một lượt kiểm
   chứng độc lập, không phải chỉ qua máy.**
2. **Ngưỡng số ép ra dối trá.** Ngưỡng cứng 200 ký tự khiến 148 bản đạt chuẩn
   bằng cách liệt kê thứ hồ sơ KHÔNG có. ⇒ **Không đặt KPI số lượng cho nội
   dung.**
3. **Test đông không bằng test đúng tầng.** 9.535 test backend xanh trong khi
   `/api/me/activity` khai báo hai lần và rỗng với mọi user. ⇒ **Mỗi tính năng
   người dùng chạm phải có ít nhất một test ở tầng người dùng thấy.**

---

## 2. Checklist mở cửa (go-live)

Tick được hết mới gỡ `NUXT_PUBLIC_SITE_NOINDEX`. Mỗi dòng phải có bằng chứng
chạy được, không phải lời khẳng định.

### Trụ ĐÚNG
- [ ] 0 lỗi nội dung mức critical/high trong đợt kiểm chứng gần nhất
- [ ] ≥30% entity có ảnh (nay 3,3%)
- [ ] ≤15% mô tả dưới 200 ký tự (nay ~40%)
- [ ] ≥50 entity có `verifiedAt` thật (nay 0) — điều kiện để bỏ giới hạn §1.7
- [ ] 0 mô tả nhắc đơn vị hành chính đã bỏ ở ngữ cảnh hiện tại — **đã đạt**

### Trụ SỐNG
- [ ] `setup_monitoring.sh` đã cài và **đang chạy**; có bằng chứng một cảnh báo
      thật đã đến tay (tự gây lỗi để thử)
- [ ] `backup_db_daily.sh` đã vào cron; kiểm tra file backup mới mỗi ngày
- [ ] **Đã khôi phục thử từ backup vào máy sạch ít nhất một lần**, ghi lại thời
      gian thật (đây là thứ phân biệt có-backup và có-khả-năng-khôi-phục)
- [ ] Backup offsite chạy tự động (VPS chết là mất cả DB lẫn backup cùng chỗ)
- [ ] `maintenance_mode.sh` đã thử bật/tắt trên prod
- [ ] Runbook cho 3 sự cố hay gặp nhất: hết đĩa, DB không lên, deploy hỏng

### Trụ AN TOÀN
- [ ] `TOTP_ENC_KEY` đã đặt trên prod **trước khi** bật 2FA (đặt sau = khoá vĩnh
      viễn người đã bật)
- [ ] Rà OWASP Top 10 tự làm, ghi kết quả từng mục
- [ ] Rate limit trên mọi endpoint ghi (đăng nhập, đăng bài, bình luận, upload)
- [ ] Quét secret toàn bộ lịch sử git, không chỉ HEAD
- [ ] Cookie session: HttpOnly + Secure + SameSite; kiểm bằng browser thật
- [ ] Giới hạn kích thước upload và kiểm loại file thật (không tin đuôi file)

### Trụ HỢP PHÁP
- [ ] Xác định rõ: có UGC ⇒ có thuộc diện NĐ147 không? **Cần luật sư — điều kiện
      dừng theo CLAUDE.md §4**
- [ ] Chính sách riêng tư đúng NĐ13: thu gì, giữ bao lâu, xoá thế nào
- [ ] Cơ chế tiếp nhận và gỡ nội dung vi phạm trong ≤24 giờ, có nhật ký
- [ ] Điều khoản sử dụng hiển thị được, có mốc thời gian
- [ ] Kiểm duyệt UGC trước khi mở cộng đồng (bắt buộc, không phải tuỳ chọn)

### Trụ TRẢ NỔI
- [ ] Đo chi phí thật ở tải mục tiêu (VPS + băng thông + lưu ảnh + LLM)
- [ ] Đặt trần chi tiêu LLM/ảnh theo ngày, có kill-switch (đã có
      `autonomous_budget.py` — kiểm tra nó thật sự chặn)
- [ ] Ước lượng chi phí khi traffic tăng 10 lần, biết trước điểm gãy

---

## 3. Các đợt thực thi

### Đợt A — Nội dung (quyết định điểm số, chặn go-live)

**A1. Ảnh: 3,3% → 30%.** Bật dịch vụ ảnh ở `localhost:20128` (đang tắt — chặn
cứng). Chạy `gen_entity_images.py` theo lô 20, ưu tiên: entity đã có mô tả tốt >
điểm tham quan/làng nghề > món ăn > xã/phường. **Xem toàn bộ ảnh mỗi lô** — prompt
đã sửa nhưng một tô bún từng nhận prompt "kiến trúc di sản". Ước ~26 lô.

**A2. Dữ kiện trước, câu chữ sau.** Với ~700 mô tả mỏng: **không viết tiếp bằng
LLM**. Hồ sơ chỉ có `schema_type` + `coords_approximate` thì mọi câu thêm vào đều
là bịa — đã chứng minh bằng 53 lỗi ở 93 bản. Việc đúng là bổ sung dữ kiện thật
(giờ mở cửa, giá, món, liên hệ) qua form nhập nhanh trong AdminCP, rồi mới viết.

**A3. Quy trình nội dung chuẩn, áp vĩnh viễn:**
viết → gác cổng máy → **người kiểm chứng độc lập** → mới ghi DB.
Không bỏ bước ba kể cả khi gấp. Đợt vừa rồi bỏ bước này hai lần và cả hai lần
đều phải sửa hậu quả.

**A4. Kiểm chứng thực địa.** 50 entity trọng điểm có `verifiedAt` thật (tới nơi,
chụp, ghi ngày). Đây là điều kiện gỡ giới hạn §1.7 và là nền cho mọi tuyên bố
tin cậy về sau.

### Đợt B — Sống sót thật

**B1. Cảnh báo có người nhận.** Cài `setup_monitoring.sh`, rồi **tự gây lỗi để
kiểm chứng cảnh báo tới tay trong ≤5 phút**. Monitoring không được kiểm chứng thì
coi như không có.

**B2. Diễn tập khôi phục.** Khôi phục DB từ backup vào máy sạch, bấm giờ. Con số
đó là RTO thật. Lặp lại mỗi quý.

**B3. Backup offsite.** Backup nằm cùng VPS thì VPS chết là mất cả hai. Đã có
`backup_offsite.py` — lịch hoá và kiểm tra tệp đến nơi.

**B4. Runbook cho ba sự cố hay gặp:** hết đĩa (đã suýt xảy ra: 1,8 GB rác + log
81 MB), DB không lên, deploy hỏng. Mỗi runbook phải có lệnh copy-paste được.

### Đợt C — Chịu đòn

**C1. Rà OWASP Top 10** tự làm, ghi từng mục: injection (đã dùng placeholder —
xác nhận lại), auth, exposure, XXE, access control, misconfig, XSS, deserialize,
component lỗi thời, logging.

**C2. Quét secret toàn lịch sử git.** Khoá bản đồ từng nằm trong payload công
khai; phải kiểm cả lịch sử chứ không chỉ HEAD.

**C3. Kiểm duyệt UGC trước khi mở cộng đồng.** Theo luật Việt Nam đây là bắt
buộc. Trang Cộng đồng hiện ở trạng thái "sắp mở" nhưng vẫn nằm trên nav — hoặc
làm đủ để mở, hoặc gỡ khỏi nav.

### Đợt D — Test đúng tầng

**D1. Thay test grep-source.** 1.754/5.253 test backend chỉ assert chuỗi trong
source — đỏ khi refactor đúng, xanh khi hành vi sai. Thay dần theo module mỗi lần
chạm vào. Đích ≤5%.

**D2. Ba vùng mù.** `server.py` 21%, `auth.py` 25%, `social.py` 18% coverage —
đúng ba module CLAUDE.md §B3 gọi là vùng mù. Nâng ≥60%, ưu tiên đường đi có tiền
và có quyền.

**D3. Test cô lập trạng thái.** Test hiện phụ thuộc DB cục bộ nên đỏ giả (đã gặp
thật). Mỗi file test cần fixture DB riêng.

**D4. Một test tầng người dùng cho mỗi luồng chính:** tìm kiếm, khám phá, chi
tiết, bản đồ. Chạy được trong release gate.

### Đợt E — Vận hành gọn

**E1. Gộp nhánh.** 18 worktree, `main` lệch 93/133 commit, chi phí tăng theo
ngày. Chặn hiện tại: complexity 26 > baseline 14, toàn bộ thuộc họ `itinerary_*`
— phải refactor `select_and_schedule_day()` (CC=126) hoặc tách nhánh đó ra.

**E2. Scorecard sống lại.** Entry cuối 2026-07-10 ghi backend 99/100 trong khi
thực đo 88. Chạy hàng tuần, chấp nhận điểm tụt — số thật quan trọng hơn số đẹp.

**E3. Rà mọi cổng bằng một câu hỏi:** *nó đọc nội dung, hay chỉ kiểm sự có mặt
của file?* R20.5 từng chỉ kiểm file có được staged không (đã sửa).

**E4. Cổng nội dung thường trực:** chạy `check_no_invention` trên toàn DB, báo số
mô tả vi phạm — biến kiểm chứng nội dung thành cổng thay vì việc làm một lần.

### Đợt F — Hiệu năng và khám phá

**F1. Ngân sách hiệu năng.** Đo trên mạng chậm mô phỏng, không phải localhost.
Trang chủ hiện 1,1 MB/84 request sau khi sửa prefetch. Đặt trần và gắn vào gate.

**F2. Ảnh đúng kích thước.** Ảnh là phần nặng nhất (754 KB/13 ảnh ở trang chủ).
Responsive sizes + lazy đúng chỗ.

**F3. Mở index có kiểm soát.** Chỉ gỡ noindex khi trụ ĐÚNG đạt ngưỡng. Mở sớm với
nội dung mỏng là tự chuốc đánh giá thấp từ máy tìm kiếm, và rất khó gỡ.

---

## 4. Vận hành sau khi mở cửa (một người)

- **SLO thực tế cho solo dev**: uptime 99% (≈7 giờ ngừng/tháng) là đủ, đừng hứa
  99,9% rồi không giữ nổi.
- **Không trực đêm.** Đặt cảnh báo theo mức: chỉ "site chết" mới báo ngay; còn
  lại gom vào bản tin sáng.
- **Nhật ký sự cố**: mỗi lần hỏng ghi 5 dòng — hỏng gì, biết lúc nào, do đâu, sửa
  sao, ngăn tái diễn thế nào.
- **Ôn tập hàng quý**: khôi phục backup, thử `maintenance_mode.sh`, xoay khoá.

## 5. Thứ tự và lý do

1. **A (nội dung)** — dịch chuyển điểm mạnh nhất, và đang bị chặn bởi một dịch vụ
   chưa bật. Rẻ nhất để mở khoá.
2. **B (sống sót)** — trước khi có người dùng thật, vì sau đó mọi sự cố đều đắt.
3. **C (chịu đòn) + phần HỢP PHÁP** — điều kiện bắt buộc để mở cửa, không phải
   tuỳ chọn.
4. **D (test đúng tầng)** — điều kiện để sửa nhanh mà không sợ vỡ.
5. **E, F** — sau khi nội dung đủ dày, vì trước đó UX và SEO bị trần nội dung chặn.

## 6. Rủi ro tồn dư sau khi làm hết

Nói trước để không ảo tưởng:

- **Một VPS = một điểm chết.** Ngân sách hiện tại không cho phép dự phòng nóng.
  Chấp nhận, nhưng phải có khôi phục đã diễn tập.
- **Không có người kiểm chứng nội dung thường trực.** Đây là lý do trần điểm là 9
  chứ không phải 10.
- **Pháp lý cần người thật.** Không agent nào thay được luật sư cho NĐ147.

## 7. Điều kiện dừng — phải hỏi chủ dự án

- Bật dịch vụ ảnh/LLM cục bộ (chặn Đợt A)
- Hướng xử lý nợ complexity `itinerary_*` (chặn Đợt E1)
- Mở hay gỡ trang Cộng đồng (chặn phần HỢP PHÁP)
- Hồ sơ pháp lý, NĐ147, pháp nhân (Track-H)
- Mọi thao tác xoá dữ liệu, push, deploy, đặt secret thật
