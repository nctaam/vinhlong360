> STATUS: active
Authority: config/release-authority.json

# Sổ hồ sơ quyết định — `docs/decisions/`

> **Không hồ sơ nào trong thư mục này đã được ký.** Trạng thái hiện tại của cả sáu là
> **CHƯA KÝ**. Máy (agent, script, CI) **không được điền §7 của bất kỳ hồ sơ nào** —
> điền chữ ký thay người là bịa ra sự đồng ý của con người, và đó là hỏng hóc nặng
> nhất có thể xảy ra ở thư mục này.

## 1. Thư mục này là gì

`config/release-authority.json:23` khai bốn khoản bắt buộc phải có quyết định trước khi
cổng nghiệm thu pilot mở: `legal`, `provider`, `residency`, `public_indexing`. Cùng file,
`:20`, đặt `owner_signoff_required: true`, và `:4` ghi chủ sở hữu là chuỗi vai trò
`"service-owner"` chứ không phải một con người cụ thể.

Trước thư mục này, bốn khoản đó chỉ tồn tại dưới dạng tên khoá trong JSON và một dòng
mô tả trong `web-nuxt/utils/legalContent.ts:63-68`. Không có chỗ nào ghi: chọn gì, đánh
đổi ra sao, ai chịu hậu quả, và cần bằng chứng nào mới được ký. Thư mục này là chỗ đó.

Sáu hồ sơ — bốn khoản của `decision_required_items`, cộng hai khoản về người
(chủ sở hữu dịch vụ, chủ sở hữu phát hành/staging) mà `docs/audit-toan-du-an-2026-08.md:834`
đòi trước khi mở pilot:

| Mã | Hồ sơ | `decision_key` | Trạng thái |
|---|---|---|---|
| QD-01 | [Chủ sở hữu dịch vụ](QD-01-chu-so-huu-dich-vu.md) | `service_owner` | CHƯA KÝ |
| QD-02 | [Pháp lý / DPO](QD-02-phap-ly-dpo.md) | `legal` | CHƯA KÝ |
| QD-03 | [Idempotency nhà cung cấp](QD-03-idempotency-nha-cung-cap.md) | `provider` | CHƯA KÝ |
| QD-04 | [Nơi lưu trữ dữ liệu](QD-04-noi-luu-tru-du-lieu.md) | `residency` | CHƯA KÝ |
| QD-05 | [Lập chỉ mục công khai](QD-05-lap-chi-muc-cong-khai.md) | `public_indexing` | CHƯA KÝ |
| QD-06 | [Chủ sở hữu staging / phát hành](QD-06-chu-so-huu-staging-phat-hanh.md) | `release_owner` | CHƯA KÝ |

Chỉ mục máy đọc được: `config/decision-records.json`. Hai nơi phải khớp nhau; nếu lệch
thì **văn bản trong `docs/decisions/` là bản gốc**, JSON là bản chiếu.

## 2. Vòng đời: CHƯA KÝ → ĐÃ KÝ

1. **Soạn (máy làm được).** Một agent dựng §1–§6: bối cảnh có trích dẫn `path:line` tự
   đọc được, ít nhất hai lựa chọn thật, đánh đổi, ai chịu, hậu quả nếu treo, và danh sách
   bằng chứng phải kèm khi ký. §7 để trống.
2. **Chủ dự án đọc và chọn.** Nếu khoản cần người ngoài (luật sư, nhà cung cấp) thì bằng
   chứng ở §6 phải có trước, không phải sau.
3. **Ký (chỉ người).** Chủ dự án điền §7: `decision_key`, `chosen_option`, `signed_by`,
   `signed_at`, `signature`. Đổi dòng "Trạng thái: CHƯA KÝ" thành trạng thái đã ký.
4. **Chiếu sang JSON.** Cập nhật mục tương ứng trong `config/decision-records.json`:
   `state` từ `"unsigned"` sang trạng thái đã ký, điền `chosen_option`, `signed_by`,
   `signed_at`, `record_sha256` (băm của chính file `.md` tại thời điểm ký) và
   `signature`.
5. **Nghiệm thu lại.** Cổng pilot đọc `config/release-authority.json`; sau khi ký thì
   chạy lại toàn bộ ma trận bằng chứng, không suy ra kết quả từ chữ ký.

Một hồ sơ đã ký **không được sửa §1–§6 tại chỗ**. Sự thật đổi thì mở hồ sơ mới, ghi
`superseded-by` ở header STATUS của hồ sơ cũ — đúng quy ước tài liệu ở `CLAUDE.md` §3.6.

## 3. Vì sao máy không được ký

`CLAUDE.md` §4 liệt các việc phải hỏi người: hồ sơ pháp lý, đặt giá trị bí mật thật,
thao tác phát sinh chi phí, deploy prod. Cả sáu hồ sơ ở đây đều rơi vào ít nhất một
trong số đó.

Ngoài ra, cổng nghiệm thu pilot đang ở **NO_GO** một cách có chủ đích: bốn khoá chứng
thực khai ở `config/release-authority.json:26-31` (vai trò `runner`, `owner`,
`countersign`, `ci`) hiện **không có giá trị**, và khoá vai trò `owner` được giữ ngoài
máy (`custody: "offline-owner:/etc/vinhlong360/pilot-owner-signing.key"`). Một agent điền §7 sẽ
không tạo ra quyền phát hành — nó chỉ tạo ra một tài liệu nói dối về việc con người đã
đồng ý. Đó là lý do §7 trống là **trạng thái đúng**, không phải việc còn dở.

## 4. Quy ước trong từng hồ sơ

- Header hai dòng: `> STATUS: ...` rồi `Authority: config/release-authority.json`.
- Bảy mục cố định, cùng tiêu đề, cùng thứ tự, ở cả sáu hồ sơ: BỐI CẢNH · LỰA CHỌN ·
  ĐÁNH ĐỔI · AI CHỊU ẢNH HƯỞNG · NẾU KHÔNG QUYẾT · BẰNG CHỨNG PHẢI KÈM KHI KÝ ·
  CHỐT CỦA CHỦ DỰ ÁN.
- §1 chỉ chứa dữ kiện có trích dẫn `path:line`. Chỗ nào chưa kiểm được thì ghi thẳng là
  chưa kiểm được, không suy đoán.
- §2 phải có ít nhất hai lựa chọn thật, khác nhau về hậu quả. Hồ sơ chỉ có một đường là
  hồ sơ đóng dấu, không phải hồ sơ quyết định.
- §7 luôn trống cho tới khi chủ dự án tự tay điền.
