> STATUS: active
Authority: config/release-authority.json

# QD-02 — Pháp lý / DPO (`legal`)

> **Hồ sơ này CHƯA KÝ.** Máy **không được** điền §7. Đây là khoản duy nhất trong thư mục
> mà không một agent nào và không một tài liệu nội bộ nào trả lời thay được — nó cần
> người có tư cách pháp lý. Một agent điền §7 ở đây là bịa ra ý kiến pháp lý.

`decision_key`: `legal` · Nguồn hỏi: `docs/2026-08-22-cau-hoi-cho-luat-su.md`

---

## 1. BỐI CẢNH

**Chính sản phẩm đang tự khai là chưa có quyết định pháp lý.**

`web-nuxt/utils/legalContent.ts:63-68` khai một khối `decisionRequired` gồm đúng bốn
khoản, và bốn khoản đó trùng với `config/release-authority.json:23`:

- `:64` `sla_24h_48h` — *"Quy trình 24/48 giờ là mục tiêu đang chờ DPO/luật sư phê duyệt,
  không phải cam kết dịch vụ."*
- `:65` `residency` — nơi lưu trữ cần kiểm theo hạ tầng thực tế trước khi công bố
  (hồ sơ riêng: `docs/decisions/QD-04-noi-luu-tru-du-lieu.md`).
- `:66` `processors_subprocessors` — danh sách bên xử lý / bên xử lý phụ cần phê duyệt.
- `:67` `public_indexing` — phạm vi lập chỉ mục cần quyết riêng
  (hồ sơ riêng: `docs/decisions/QD-05-lap-chi-muc-cong-khai.md`).

Câu chữ hiển thị cho người dùng cũng nói y như vậy:
`web-nuxt/utils/legalContent.ts:162` ghi mọi mốc 24/48 giờ là **decisionRequired**, *"mục
tiêu dự kiến đang chờ DPO/luật sư phê duyệt, không phải cam kết dịch vụ"*. Đây là trạng
thái trung thực — sản phẩm không hứa cái nó chưa được duyệt.

**Chủ sở hữu pháp lý hiện là một nhãn tổ chức, không phải DPO.**
`web-nuxt/utils/legalContent.ts:70-71`: `LEGAL_OWNER = 'Chủ quản trị vinhlong360'`,
`LEGAL_CONTACT = '/lien-he (mục "Dữ liệu cá nhân & pháp lý")'`.

**Bốn câu hỏi đã được soạn sẵn, chưa ai trả lời.** `docs/2026-08-22-cau-hoi-cho-luat-su.md`
§2 gói gọn: (1) dự án thuộc nhóm nào theo Luật 91/2025 và vì thế được miễn gì; (2) nghĩa
vụ nội dung nào không được miễn và hệ thống đã đủ chưa; (3) mô hình premium/featured
listing có đẩy site thành sàn TMĐT không; (4) NĐ147/2024 có đòi giấy phép không.

**Giới hạn của phần tra cứu nội bộ, ghi ở §5 của chính tài liệu đó:** bản ký gốc Luật
91/2025 là PDF ảnh scan không đọc được bằng máy; `thuvienphapluat.vn` chặn truy cập
(403); **toàn văn Điều 24 NĐ147/2024 chưa đọc được**. Nghĩa là kể cả phần "đã tra" cũng
không phải trích trực tiếp từ luật.

**Đợt rà soát để lại hai dòng chưa đóng.**

- `docs/audit-toan-du-an-2026-08.md:239` (F-16) — câu chữ pháp lý hứa xử lý 48h/24h
  nhưng chưa có assignee, SLA clock, escalation, audit hay storage residency tương ứng;
  trạng thái ghi rõ **Decision required**, chủ thể **Owner + legal/DPO**.
- `docs/audit-toan-du-an-2026-08.md:302` (F-73) — thiếu cookie policy và lịch sử thay
  đổi chính sách. Phần sản phẩm đã có phản hồi: `web-nuxt/utils/legalContent.ts` nay có
  `COOKIE_INVENTORY` (`:72` trở đi) và `CHANGE_HISTORY` (`:81-84`); phiên bản chính sách
  `'2026.09'` khai ở `:87`.
  Phần chưa đóng là **câu chữ và nghĩa vụ**, tức phần cần luật sư.

**Đã có sổ chờ từ trước.** `docs/QUYET-DINH-DANG-CHO.md` mục B6 đặt đúng câu hỏi NĐ147
và xếp nó vào điều kiện dừng `CLAUDE.md` §4 (Track-H, cần luật sư).

**Chưa kiểm được:** tư cách pháp lý hiện tại của dự án (cá nhân / hộ kinh doanh / doanh
nghiệp) không nằm ở bất kỳ file nào trong repo. Chỉ chủ dự án biết.

## 2. LỰA CHỌN

1. **Thuê tư vấn pháp lý một lần, lấy kết luận bằng văn bản** cho đủ bốn câu ở
   `docs/2026-08-22-cau-hoi-cho-luat-su.md` §2, cộng ba khoản còn treo của F-16 (SLA
   thật, người nhận, escalation) và câu chữ cookie/changelog của F-73. Sau đó mới bật cờ
   kênh đính chính.
2. **Thu hẹp pilot để tránh phần lớn câu hỏi.** Mở kênh đính chính ở dạng **không thu số
   điện thoại** (bỏ hẳn `optionalPhone`), **không premium/featured listing**, **không mở
   khu cộng đồng** — ba nguồn phát sinh nghĩa vụ nặng nhất. Chỉ hỏi luật sư phần còn lại.
3. **Chỉ định một người làm đầu mối DPO nội bộ trước, thuê luật sư sau.** Có người chịu
   trách nhiệm và có SLA clock thật chạy, còn câu chữ giữ nguyên trạng thái
   "chờ phê duyệt" như hiện tại.
4. **Hoãn.** Giữ toàn bộ cờ tính năng ở trạng thái tắt, giữ câu chữ ở mức "mục tiêu, không
   phải cam kết", không mở pilot cho người thật.

## 3. ĐÁNH ĐỔI

- **(1)** là đường duy nhất đóng được cả bốn câu hỏi cùng lúc, và là đường duy nhất cho
  ra một văn bản mà chủ dự án cầm được khi có tranh chấp. Đổi lại: tốn tiền, và chi phí
  pháp lý nằm ngoài trần ngân sách kỹ thuật ở `CLAUDE.md` §B8 nên vẫn phải chủ dự án
  duyệt riêng. Thời gian chờ luật sư đọc cũng là thời gian pilot đứng yên.
- **(2)** mở được sớm và cắt đúng ba nguồn rủi ro nặng. Đổi lại bỏ mất chính thứ mà kênh
  đính chính sinh ra để làm: báo lại kết quả cho người đã báo tin. Không có số điện thoại
  thì người báo phải tự quay lại tra biên nhận — trải nghiệm kém hẳn, và tỷ lệ người quay
  lại là thứ chưa ai đo được.
- **(3)** rẻ nhất trong ba đường có hành động, và nó đóng đúng phần F-16 phàn nàn (thiếu
  người, thiếu đồng hồ, thiếu escalation) mà không cần luật sư. Đổi lại: một đầu mối nội
  bộ **không** thay được kết luận pháp lý; bốn câu hỏi vẫn treo, và mốc 24/48 giờ vẫn
  không được phép gọi là cam kết.
- **(4)** không tốn gì và không sai gì hôm nay — câu chữ hiện tại đã trung thực. Đổi lại
  cả kênh đính chính nằm im vô thời hạn; và rủi ro thật của việc hoãn không phải "không
  làm" mà là **có người sẽ mở cờ mà quên rằng chưa có kết luận nào**, vì trạng thái
  "đang chờ" không tự nhắc ai cả.

## 4. AI CHỊU ẢNH HƯỞNG

- **Người báo tin qua kênh đính chính**, đặc biệt người báo ẩn danh: quyền rút lại đồng ý
  và quyền xoá của họ hiện đi tới đâu là một trong bốn câu hỏi chưa có đáp án
  (`docs/2026-08-22-cau-hoi-cho-luat-su.md` §2 Câu 2).
- **Chủ dự án**: trách nhiệm pháp lý thuộc về người, không thuộc sản phẩm. Bảng chế tài ở
  §4 của tài liệu hỏi luật sư đặt trần tới 3 tỷ đồng cạnh ngân sách dưới 1 triệu
  đồng/tháng.
- **Mọi câu chữ pháp lý đang hiển thị**: `web-nuxt/utils/legalContent.ts:162` và trang
  chính sách/điều khoản.
- **Ba hồ sơ khác trong thư mục này**: `QD-04` (residency) và `QD-05` (public indexing)
  là hai trong bốn khoản `decisionRequired` do chính khối pháp lý khai; `QD-03` cần một
  chữ ký chấp nhận rủi ro mà chỉ có ý nghĩa nếu người ký hiểu hệ quả pháp lý.

## 5. NẾU KHÔNG QUYẾT

`config/release-authority.json:23` giữ `legal` trong `decision_required_items`, nên cổng
pilot ở lại NO_GO. Điều đó đúng. Cái giá nằm ở chỗ khác: câu chữ "đang chờ DPO/luật sư
phê duyệt" là trạng thái đúng **hôm nay**, nhưng để lâu nó biến thành nền — và một dòng
cảnh báo quen mắt là dòng không ai đọc nữa. Đó chính là lớp lỗi mà
`docs/2026-08-22-cau-hoi-cho-luat-su.md` §2 đã dính một lần: hai dòng trong bảng hiện
trạng khai quá so với hệ thống thật, phải đính chính tại chỗ.

## 6. BẰNG CHỨNG PHẢI KÈM KHI KÝ

1. Văn bản trả lời của luật sư cho bốn câu ở `docs/2026-08-22-cau-hoi-cho-luat-su.md` §2
   — hoặc, nếu chọn phương án (2)/(3), văn bản ghi rõ **phạm vi nào được loại trừ và vì
   sao**, để lần sau không ai phải đoán lại.
2. Tư cách pháp lý hiện tại của dự án (cá nhân / hộ kinh doanh / doanh nghiệp, có mã số
   thuế chưa) — mục 1 trong danh sách chuẩn bị ở §6 của tài liệu đó.
3. Kết luận về mốc 24/48 giờ: là cam kết dịch vụ hay là mục tiêu. Nếu là cam kết thì phải
   kèm người nhận, đồng hồ SLA thật và đường escalation (F-16,
   `docs/audit-toan-du-an-2026-08.md:239`). Chỉ khi đó mới được sửa
   `web-nuxt/utils/legalContent.ts:64` và `:162`.
4. Kết luận về câu chữ cookie và lịch sử thay đổi chính sách (F-73,
   `docs/audit-toan-du-an-2026-08.md:302`), đối chiếu với `COOKIE_INVENTORY` và
   `CHANGE_HISTORY` hiện có trong `web-nuxt/utils/legalContent.ts`.
5. Mục `legal` trong `config/decision-records.json` được cập nhật cùng lúc, kèm
   `record_sha256` băm từ chính file này tại thời điểm ký.

## 7. CHỐT CỦA CHỦ DỰ ÁN

Trạng thái: CHƯA KÝ

| Trường | Giá trị (chỉ chủ dự án điền) |
|---|---|
| decision_key | |
| chosen_option | |
| signed_by | |
| signed_at | |
| signature | |
