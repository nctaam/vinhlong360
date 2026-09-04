> STATUS: active
Authority: config/release-authority.json

# QD-01 — Chủ sở hữu dịch vụ (`service_owner`)

> **Hồ sơ này CHƯA KÝ.** Không một agent, script hay job CI nào được điền §7. §7 chỉ do
> chủ dự án tự tay điền. Máy điền vào đó là bịa ra sự đồng ý của con người.

`decision_key`: `service_owner` · Hồ sơ liên quan: `docs/decisions/QD-06-chu-so-huu-staging-phat-hanh.md`

---

## 1. BỐI CẢNH

**Hệ thống đang trỏ vào một vai trò, không phải một người.**

- `config/release-authority.json:4` — `"owner": "service-owner"`. Đây là một chuỗi vai
  trò. Không có tên, không có kênh liên lạc, không có khung giờ trực.
- `config/release-authority.json:17` — khối `pilot_acceptance` lặp lại đúng chuỗi đó
  (`"owner": "service-owner"`).
- `config/release-authority.json:20` — `"owner_signoff_required": true`. Cổng nghiệm thu
  đòi một chữ ký của chủ sở hữu, trong khi không nơi nào trong repo nói chủ sở hữu là ai.
- `config/release-authority.json:26-31` — bộ chứng thực bốn vai trò
  (`runner`, `owner`, `countersign`, `ci`). Vai trò `owner` có custody
  `"offline-owner:/etc/vinhlong360/pilot-owner-signing.key"`, tức khoá cố ý nằm ngoài máy này.
  Các khoá hiện **không có giá trị**, nên cổng đứng ở NO_GO. Đây là lựa chọn có chủ
  đích của chủ dự án, không phải sự cố.

**Đợt rà soát đòi có người, không đòi có vai trò.**

- `docs/audit-toan-du-an-2026-08.md:834` — điều kiện thứ 4 để mở closed pilot:
  *"Có owner/on-call, support route, correction SLA clock và incident escalation."*
- `docs/audit-toan-du-an-2026-08.md:831` — 28 P1 phải có fix kèm bằng chứng; trong đó
  F-53 đòi **risk acceptance được ký** nếu không bật được idempotency phía nhà cung cấp
  (xem `QD-03`). "Được ký" đòi một người có thẩm quyền ký.

**Phía sản phẩm cũng đang ở mức tổ chức, không mức cá nhân.**

- `web-nuxt/utils/legalContent.ts:70` — `LEGAL_OWNER = 'Chủ quản trị vinhlong360'`.
- `web-nuxt/utils/legalContent.ts:71` — `LEGAL_CONTACT = '/lien-he (mục "Dữ liệu cá nhân & pháp lý")'`.
- `CLAUDE.md` §1.7 chốt byline ở cấp tổ chức ("Ban biên tập vinhlong360"), không tên cá
  nhân. Nên câu hỏi ở đây **không phải** "có công khai tên người không" mà là "nội bộ,
  ai là người ký và người trực".

**Chưa kiểm được (ghi thẳng, không suy đoán):** repo không chứa bất kỳ file nào khai
danh tính, số điện thoại hay khung giờ trực của người chịu trách nhiệm vận hành. Không có
cách nào để máy suy ra thông tin đó.

## 2. LỰA CHỌN

1. **Chỉ định đích danh một người làm chủ sở hữu dịch vụ.** Ghi tên, kênh liên lạc và
   khung giờ trực vào một nơi duy nhất (đề nghị: mở rộng khối `pilot_acceptance` trong
   `config/release-authority.json`, hoặc một file `config/service-owner.json` mới). Người
   đó giữ `secrets/pilot-owner-signing.key` và là người ký mọi attestation vai trò
   `owner`.
2. **Giữ nhãn cấp tổ chức, chỉ định một người ký uỷ quyền.** `"service-owner"` ở lại như
   tên vai trò; bên cạnh đó có một người duy nhất được nêu tên trong tài liệu nội bộ, có
   nhiệm vụ hẹp: giữ khoá và ký. Vận hành hằng ngày vẫn nói bằng giọng tổ chức.
3. **Chưa chỉ định.** Cổng giữ NO_GO, pilot không mở, và mọi hồ sơ khác trong thư mục này
   không có ai ký được.
4. **Chỉ định hai người: một ký, một đối ký.** Tách vai trò `owner` khỏi vai trò
   `countersign` (`config/release-authority.json:27,29`) sang hai con người khác nhau,
   để một người không tự chứng minh cho chính mình.

## 3. ĐÁNH ĐỔI

- **(1)** rõ ràng nhất và mở khoá được mọi hồ sơ còn lại. Đổi lại: một người gánh toàn
  bộ trách nhiệm pháp lý và vận hành, kể cả khi nghỉ ốm hay đi vắng. Với dự án một
  người thì đây là mô tả đúng hiện trạng chứ không phải rủi ro mới — nhưng viết ra thành
  văn bản làm nó thành cam kết chứ không còn là mặc định.
- **(2)** giữ được nguyên tắc byline tổ chức của `CLAUDE.md` §1.7 và tách "ai nói với
  công chúng" khỏi "ai ký". Đổi lại thêm một lớp gián tiếp: khi có sự cố, người bên ngoài
  vẫn không biết gọi ai, chỉ có `/lien-he`.
- **(3)** không tốn gì hôm nay. Đổi lại: `owner_signoff_required: true`
  (`config/release-authority.json:20`) trở thành một điều kiện vĩnh viễn không ai thoả
  được, và mọi công việc kỹ thuật đã làm xong nằm chờ sau một ô trống.
- **(4)** đúng nguyên tắc phân tách trách nhiệm nhất, và khớp với thiết kế bốn vai trò
  đã khai. Đổi lại cần **hai người thật**; nếu dự án chỉ có một người thì lựa chọn này
  không thực hiện được mà chỉ tạo ra hai cái tên trỏ về cùng một người — tệ hơn (1) vì
  nó trông như có kiểm soát chéo trong khi không có.

## 4. AI CHỊU ẢNH HƯỞNG

- **Người báo tin qua kênh đính chính**: nếu không ai trực, hồ sơ của họ nằm chờ mà
  không có ai chịu trách nhiệm cho việc chờ đó.
- **Chủ dự án**: trách nhiệm pháp lý và vận hành thuộc về con người, không thuộc về sản
  phẩm — điều này đã ghi ở `docs/QUYET-DINH-DANG-CHO.md` mục B6.
- **Mọi hồ sơ còn lại trong `docs/decisions/`**: cả năm hồ sơ kia đều cần một người ký.
  Không có QD-01 thì không có QD-02…QD-06.
- **Cổng nghiệm thu pilot**: đứng NO_GO cho tới khi có chữ ký vai trò `owner`.

## 5. NẾU KHÔNG QUYẾT

Cổng ở lại NO_GO — đó là kết quả đúng, không phải sự cố. Nhưng cái giá thật nằm chỗ
khác: điều kiện thứ 4 của `docs/audit-toan-du-an-2026-08.md:834` (owner/on-call,
support route, SLA clock, escalation) không bao giờ tick được, nên toàn bộ công việc kỹ
thuật đã hoàn thành cho pilot không đổi thành giá trị sử dụng nào. Và mỗi khoản trong
`docs/decisions/` sẽ tích luỹ thêm bối cảnh phải đọc lại từ đầu mỗi lần có người quay
lại hồ sơ.

## 6. BẰNG CHỨNG PHẢI KÈM KHI KÝ

1. Tên người chịu trách nhiệm, kênh liên lạc, và khung giờ trực (on-call window) — ghi
   vào một file cấu hình duy nhất, nêu rõ đường dẫn trong `chosen_option`.
2. Xác nhận custody của `secrets/pilot-owner-signing.key`: ai giữ, giữ ở đâu, và ai lấy
   lại được nếu người đó không liên lạc được. **Máy không được tạo, đặt hay đọc giá trị
   khoá này** — `CLAUDE.md` §4.
3. Đường xử lý sự cố (escalation) cho kênh đính chính: bước 1 gửi cho ai, bao lâu thì
   leo thang, leo lên đâu.
4. Mục `service_owner` trong `config/decision-records.json` được cập nhật cùng lúc, với
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
