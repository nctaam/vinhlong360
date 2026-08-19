# Runbook sự cố — Correction Case Pilot

> STATUS: active
> Nguyên tắc xuyên suốt: **fail-closed, không bịa trạng thái, không xoá bằng chứng.** Mọi lệnh phá dữ liệu bị cấm theo CLAUDE.md §B7.

## 1. Kiểm chứng projection thất bại hàng loạt (case kẹt `applied`, promise `recovery`)

Triệu chứng: `projection_verification_failed` dồn trong `case_audit_events`; trang người dân báo "đang kiểm tra trang công khai".
1. Tự mở `/api/entities/{id}` — so `revision` với `base_entity_revision + 1` của change set. Lệch = cache/prerender cũ.
2. Invalidate cache entity (AdminCP) rồi chạy lại `Kiểm chứng trang công khai` trên workbench.
3. Vẫn lệch → KHÔNG đánh dấu tay. Case cứ ở fulfillment; đó là hành vi đúng. Báo chủ dự án nếu quá 24h.

## 2. Cần gỡ một correction đã đăng (rollback)

1. Workbench → `Hoàn tác thay đổi` (cần `publication.apply` + đang giữ việc publication).
2. Bị từ chối `entity_drifted_after_apply` = có người sửa entry SAU khi đăng. **Không ép.** Hệ thống đã ghi `rollback_refused_entity_drift` + escalation; sửa tay qua AdminCP editor (đi qua boundary, có audit `admin-editor`) rồi xử lý case như một quyết định mới.
3. Case tự mở lại (fulfillment, outcome xoá) — đúng thiết kế: lời hứa không được tính là giữ bằng một thay đổi không còn tồn tại.

## 3. Nghi lộ capability / truy cập chéo

1. Với case cụ thể: rotate (nếu người dân còn phiên) hoặc `revoke_access`; mọi mã cũ chết theo.
2. Diện rộng: tắt `CASE_KERNEL_ENABLED` → mọi route case trả 404 `capability_unavailable`. Intake tạm dừng — chấp nhận, an toàn hơn rò rỉ.
3. Đối chiếu `case_audit_events` (correlation_id) + `case_admin_access_sessions`. Digest không đảo ngược được — đó là lý do ta chỉ lưu digest.

## 4. Kernel báo not-ready (`required_schema_version`)

1. `SELECT version, migration FROM schema_version WHERE component='agent'` — cần ≥ 81 (`081_change_set_lifecycle.sql`).
2. Thiếu → chạy `scripts/apply_migrations.py` theo runbook deploy hiện hành. KHÔNG hạ `PG_REQUIRED_SCHEMA_VERSION` để "cho chạy".

## 5. Scheduler cleanup hỏng (`CASE_LIFECYCLE_CLEANUP_FAILED` trong log)

- Task nuốt lỗi có chủ đích (không được giết scheduler). Chạy tay để xem lỗi thật:
  `python -c "import sys;sys.path.insert(0,'agent');from scheduler import task_case_lifecycle_cleanup as t;print(t())"`
- Hold pháp lý: truyền `audited_holds` qua đường gọi tay `cleanup_case_data`, kèm ghi chú ai quyết — KHÔNG thêm cờ môi trường cho hold.

## 6. Chế độ suy giảm (degraded)

| Mất gì | Còn gì | Làm gì |
|---|---|---|
| SMS provider | Toàn bộ xử lý; chỉ thông báo chậm | Đợi backoff; không hứa mốc mới |
| Publication (cờ tắt) | Intake, biên nhận, quyết định, audit | Nói thật trên workbench: "chờ đăng" |
| PostgreSQL | Không gì của kernel | Tắt `CASE_KERNEL_ENABLED`; route công khai 404 sạch |
| Metrics (observe drop) | Mọi nghiệp vụ (đo lường không được phép chặn hành động) | Xem log `capacity event dropped`; lỗ ngày = mất eligibility 28 ngày — chấp nhận, không backfill bịa |
