# Runbook vận hành — Correction Case Pilot

> STATUS: active
> Chủ sở hữu dịch vụ: **Ban biên tập vinhlong360** (owner_ref đặt qua `CASE_SERVICE_OWNER_REF`).
> Phạm vi: tiếp nhận – xử lý – đăng – kiểm chứng yêu cầu sửa thông tin. KHÔNG gồm khiếu nại nội dung, khôi phục tài khoản, an toàn (các kênh đó vẫn qua email, nói rõ trên `/lien-he`).

## Cờ điều khiển (tất cả mặc định FALSE — bật là quyết định phát hành riêng của chủ dự án)

Thứ tự bật khi được duyệt (mỗi bước quan sát ≥1 ngày trước bước sau):
1. `CASE_KERNEL_ENABLED` — mở đường ống, chưa nhận đơn.
2. `CORRECTION_INTAKE_ENABLED` — nhận đơn công khai + chuyển làn `/api/report`, `report-stale` sang kernel.
3. `CORRECTION_ADMIN_ENABLED` / `CORRECTION_ASSISTED_ENABLED` — workbench + ghi hộ.
4. `CORRECTION_PUBLICATION_ENABLED` — CHO PHÉP sửa entry sống. Bật cuối cùng, tắt đầu tiên.

Tắt `CORRECTION_PUBLICATION_ENABLED` KHÔNG dừng tiếp nhận/biên nhận/audit — đó là chủ đích: dừng thay đổi trang, không dừng lời hứa.

Ràng buộc kèm: PostgreSQL bắt buộc (`case_postgresql_required` nếu lệch), schema ≥ 81, `CASE_KERNEL_ENCRYPTION_KEY` 43 ký tự.

## Hàng đợi & lease

- Grammar hàng đợi: **việc kế tiếp → sức khoẻ lời hứa → người giữ → rủi ro**. Sắp theo priority, health, risk, tuổi.
- Lease 15 phút, heartbeat gia hạn; hết lease thì scan escalation tạo việc giám sát và ghi sự kiện `lease_expired`.
- Takeover chỉ `case.supervisor`, phải ghi lý do; guard R2/R3 KHÔNG bị takeover bỏ qua.
- R3: cần reviewer ≠ maker trên change set **và** work item `truth_review` đã completed bởi người ≠ maker; người áp dụng ≠ maker.

## Sự cố nhà cung cấp SMS

- Outbox at-least-once, backoff, tối đa 5 lần; hỏng hẳn → `failed` + sự kiện `provider_failure`.
- Số lượng `provider_failure` tăng bất thường → kiểm tra eSMS trước, KHÔNG retry tay từng dòng (đợi scheduler); tuyệt đối không đọc số điện thoại từ DB ra log.

## Mất biên nhận

- Mã một lần KHÔNG cấp lại được (chỉ lưu digest). Người dân còn phiên cookie → `Đổi mã tra cứu mới` (rotate) tự phục vụ.
- Mất cả hai: không có đường tra cứu tự động. Hồ sơ vẫn được xử lý và (nếu có consent SĐT) vẫn được báo kết quả. Không tạo cơ chế "xác minh danh tính qua chat" tuỳ tiện.

## Riêng tư / an ninh — leo thang

- Nghi lộ dữ liệu case: tắt `CASE_KERNEL_ENABLED` (fail-closed toàn bộ), giữ nguyên DB làm bằng chứng, báo chủ dự án. KHÔNG xoá dữ liệu.
- Step-up 15 phút, chỉ digest trong DB; nghi lạm dụng quyền đọc chứng cứ → xem `case_audit_events` + `case_admin_access_sessions`.
- Retention tự động (scheduler `case-lifecycle-cleanup`, 24h/lần): hết hạn ngay (access/idempotency/challenge), 90 ngày (SĐT sau đóng), 365 ngày (payload mã hoá, trừ hold truyền vào tường minh), 730 ngày (bỏ liên kết capacity). KHÔNG bao giờ xoá sớm audit/quyết định.

## Bằng chứng năng lực & SLA công khai

- Cửa sổ 28 ngày UTC trọn vẹn tính từ DB (`capacity_window`); đủ điều kiện chỉ khi 28/28 ngày có dữ liệu, đến/xong > 0, có tên người trực. `public_sla_eligible` chỉ trả **object bằng chứng nội bộ** — treo SLA công khai là quyết định của chủ dự án cầm bằng chứng đó, không phải của code.

## Vị trí bằng chứng

- Kết quả pilot: `docs/superpowers/results/2026-08-12-correction-case-pilot.md`
- Đối chứng schema/hành vi: các suite `agent/tests/test_case_*`, `test_correction_*` (chạy với `VL360_TEST_DATABASE_URL` loopback disposable).
- Sự cố: `docs/runbooks/correction-case-incident.md`. Cutover legacy: `docs/runbooks/correction-case-cutover.md`.
