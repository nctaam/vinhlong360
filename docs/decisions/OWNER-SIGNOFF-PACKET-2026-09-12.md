> STATUS: active (2026-09-15) — Gói lựa chọn bảo thủ cho closed pilot (CHƯA KÝ).
> Authority: config/release-authority.json

# Gói lựa chọn bảo thủ cho closed pilot

Tài liệu này là phiếu chuẩn bị cho owner và các signer. Nó **không phải chữ ký**,
không thay thế ý kiến luật sư, và không được dùng để làm verifier chuyển sang
`PASS` trước khi các điều kiện bằng chứng bên dưới tồn tại.

## Phạm vi và giả định

- Mục tiêu là một **closed pilot có kiểm soát**, không phải public launch.
- Owner/release signer hiện được xác nhận là `NCTaam`. Chưa có countersigner
  độc lập; trường này phải giữ `PENDING` và verifier phải tiếp tục fail-closed.
- Pilot không gọi nhà cung cấp SMS thật từ runner acceptance.
- Chi phí staging và tư vấn pháp lý được owner phê duyệt riêng.
- Site tiếp tục `noindex` trong giai đoạn pilot.

## Bộ lựa chọn đề xuất

| Hồ sơ | `chosen_option` đề xuất | Lý do bảo thủ | Điều kiện trước khi ký |
|---|---:|---|---|
| QD-01 `service_owner` | **1** | Ghi đúng hiện trạng một người chịu trách nhiệm thay vì khai phân tách nhiệm vụ chưa tồn tại. | Ghi `NCTaam`, kênh liên lạc, lịch trực, người dự phòng và đường escalation trong một file cấu hình nội bộ. |
| QD-02 `legal` | **4** | Hoãn phê duyệt pháp lý; giữ demo đóng và không biến sự thiếu vắng luật sư/DPO thành một phê duyệt giả. | Tắt các tính năng pháp lý còn treo, không mở cho người dùng thật, không thu số điện thoại, không premium/featured listing, không cộng đồng và không thay câu chữ “chờ phê duyệt”. |
| QD-03 `provider` | **5** | Tắt SMS trong pilot, loại bỏ tác dụng phụ bên ngoài và rủi ro gửi trùng. | UX chỉ trả biên nhận tra cứu; cờ gửi SMS phải bị tắt và có test chứng minh không phát sinh provider call. |
| QD-04 `residency` | **3** | Dùng `local` trong pilot, tránh tuyên bố sai về vùng lưu trữ/bên xử lý phụ. | Xác nhận backend thực tế là `local`; không có credential R2/S3 khiến hệ thống tự chuyển backend; có kế hoạch backup media. |
| QD-05 `public_indexing` | **1** | Giữ `noindex` toàn site trong closed pilot, không công khai dữ liệu chưa được duyệt. | Kiểm tra robots/meta/sitemap và giữ `NUXT_PUBLIC_SITE_NOINDEX`; QD-02 và QD-04 phải không mâu thuẫn. |
| QD-06 `release_owner` | **1** | Có staging thật để chạy rollout → smoke → rollback và restore drill trước production. | Chỉ định release owner; xác định prod là systemd hay docker-compose; có staging tương đồng, restore receipt, alert receipt và rollback receipt. |

## Các điểm không được hiểu nhầm

1. Bộ trên **không cấp phép public launch**. `public_launch_verdict` vẫn là
   `NO_GO` theo authority.
2. QD-02 option 4 chỉ ghi nhận quyết định **hoãn**. Nó không phải kết luận pháp
   lý và không cho phép mở pilot cho người dùng thật. Khi phạm vi thay đổi phải
   mở lại QD-02 và lấy văn bản của luật sư/DPO.
3. QD-04 option 3 là lựa chọn vận hành có điều kiện. Nếu production thật đang
   chạy R2/S3 thì phải đổi cấu hình có kiểm soát hoặc chọn lại QD-04; không được
   ghi `local` trên giấy nhưng chạy backend khác.
4. QD-06 option 1 kéo theo chi phí staging. Nếu owner không phê duyệt chi phí,
   phải chọn lại phương án và chấp nhận `NO_GO`, không tự dựng host trả phí.
5. Chữ ký trong hồ sơ phải do signer thật thực hiện. Agent chỉ có thể tính
   `record_sha256`, đối chiếu schema và chạy verifier sau khi nhận hồ sơ đã ký.

## Phiếu xác nhận offline

Owner điền hoặc đánh dấu từng dòng sau qua kênh được phê duyệt:

```text
[ ] QD-01 service_owner      = option 1
[ ] QD-02 legal              = option 4
[ ] QD-03 provider           = option 5
[ ] QD-04 residency          = option 3
[ ] QD-05 public_indexing    = option 1
[ ] QD-06 release_owner      = option 1

owner_signer_id:        NCTaam
countersigner_id:      PENDING
legal_signer_id:       NCTaam
provider_signer_id:    ____________________
residency_signer_id:   ____________________
indexing_signer_id:    ____________________
release_signer_id:     ____________________
confirmed_at_utc:      ____________________
owner_signature_ref:   ____________________
countersignature_ref:  ____________________
```

`legal_signer_id` ở đây chỉ là người ghi nhận quyết định **hoãn**. Nó không đại
diện cho luật sư/DPO và không được dùng để tuyên bố dự án đã có phê duyệt pháp lý.

## Ranh giới bắt buộc của chế độ demo

- Không mở cho người dùng thật và không quảng bá như dịch vụ đã sẵn sàng.
- Giữ `noindex` toàn site và không phát hành sitemap indexable công khai.
- Tắt SMS/provider side effect và không thu số điện thoại ở kênh đính chính.
- Tắt community/UGC, premium/featured listing và mọi luồng có thể tạo nghĩa vụ
  pháp lý chưa được duyệt.
- Chỉ dùng dữ liệu test/fixture không chứa dữ liệu cá nhân thật.
- Việc website truy cập được trên Internet không tự động biến nó thành
  “nội bộ”; nếu không có access control thì phải coi là công khai và không được
  dựa vào QD-02 option 4 để bỏ qua rà soát pháp lý.

Sau khi owner xác nhận, từng QD-01…QD-06 phải được điền mục §7 trong chính file
gốc. Sau đó mới cập nhật `config/decision-records.json` với `state: "signed"`,
`chosen_option`, `signed_by`, `signed_at`, chữ ký và `record_sha256` tương ứng.

## Custody key — không gửi trong chat

- Owner key: `/etc/vinhlong360/pilot-owner-signing.key` (ngoài checkout, quyền
  đọc giới hạn cho tiến trình verifier).
- Countersign key: cấp trong shell offline qua `PILOT_ATTEST_COUNTERSIGN_KEY`.
- Runner/CI attestation: phải có custody hợp lệ qua `PILOT_ATTEST_RUNNER_KEY` và
  `PILOT_ATTEST_CI_KEY`; thiếu một trong bốn role thì acceptance vẫn `NO_GO`.
- Không commit, paste, log hoặc đưa giá trị của bất kỳ key nào vào repository hay
  cuộc trò chuyện.

## Thứ tự sau khi nhận xác nhận

1. Cập nhật `decision_signers` trong authority theo đúng signer ID đã xác nhận.
2. Đối chiếu sáu §7, tính lại SHA-256 và cập nhật chỉ mục quyết định.
3. Chạy acceptance mới, countersign độc lập và `verify_release_bundle.py`.
4. Chỉ khi verifier trả `PASS` mới chạy installer và các kiểm tra migration,
   backup, watchdog, service health và rollback.
