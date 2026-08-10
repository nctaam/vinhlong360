# Adaptive Nocturne Residual Closure

> STATUS: proposed - design approved in conversation, waiting for written-spec review
> **Ngày:** 2026-08-10
> **Phạm vi:** contract hardening sau review cho public upgrade

## 1. Mục đích

Đặc tả này đóng bốn residual findings còn lại sau đợt review của Adaptive Nocturne Public Upgrade. Mục tiêu là làm cho planner đồng bộ an toàn, feature flag chịu lỗi đúng, contact funnel có đo lường nhất quán và CI không thể vô tình bỏ qua accessibility gate khi visual smoke thất bại.

Spec này là một additive closure. Nó không thay đổi route, auth, RBAC, data ownership, Nocturne Heritage, layout system hay các hành vi public đã được duyệt ngoài những hợp đồng được nêu rõ dưới đây.

## 2. Nguyên tắc bất biến

- **Backward compatible:** create/list/delete/merge/publish của `/api/my-plans` tiếp tục hoạt động như hiện tại.
- **No silent overwrite:** ghi đè plan đã tồn tại phải có optimistic concurrency token.
- **Fail-safe theo loại cờ:** capability rollout mới fail-closed; feature legacy đã tồn tại giữ registry default khi settings không đáng tin cậy.
- **Privacy-safe telemetry:** beacon chỉ ghi nhận action/outcome đã allowlist; không gửi số điện thoại, raw URL query, tọa độ hay nội dung tự do.
- **Independent quality gates:** visual evidence, preview, axe scan và accessibility gate có thể chạy/ghi artifact độc lập; lỗi trước đó không được làm mất gate sau.
- **Protected files:** không sửa hoặc stage các file dirty được bảo vệ trong primary checkout; mọi implementation diễn ra trong worktree riêng.

## 3. Phạm vi và không thuộc phạm vi

### 3.1 Trong phạm vi

1. Migration additive cho `user_plans`.
2. API `PUT /api/my-plans/{plan_id}` và response contract revision/conflict.
3. Resolver semantics cho established flags và public capability flags.
4. Contact metadata/handler contract cho ward phone CTAs.
5. CI condition graph cho visual smoke và accessibility.
6. Unit, integration, contract và workflow tests chứng minh các behavior trên.

### 3.2 Không thuộc phạm vi

- ETag, timestamp token thay cho integer revision.
- Event sourcing, conflict-free replicated data type hoặc server-side merge thông minh.
- Thay đổi merge từ create-only sang upsert; thay đổi này cần migration/identity contract riêng.
- Bổ sung telemetry provider hoặc lưu PII mới.
- Thiết kế lại UI ngoài metadata cần thiết để giữ contact CTA và trạng thái conflict dễ hiểu.
- Touched files đã được người dùng bảo vệ ở primary checkout.

## 4. Hợp đồng planner

### 4.1 Schema

Migration mới (tên kế tiếp sau `007_user_plans.sql`) phải là additive và idempotent:

```sql
ALTER TABLE user_plans
  ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

UPDATE user_plans
SET revision = 1
WHERE revision IS NULL OR revision < 1;

CREATE INDEX IF NOT EXISTS idx_user_plans_user_updated
  ON user_plans(user_id, updated_at DESC);
```

`revision` bắt đầu từ `1`, chỉ tăng khi mutation thành công. `updated_at` phản ánh lần mutation cuối; create và mọi update publish đều cập nhật timestamp. Existing rows nhận giá trị an toàn qua default/backfill.

### 4.2 Read contract

`GET /api/my-plans` tiếp tục trả `{ plans: [...] }`. Mỗi plan giữ các field hiện có và bổ sung:

```json
{
  "id": "uuid",
  "title": "Lịch trình",
  "stops": [],
  "is_public": false,
  "savedAt": "2026-08-10T10:00:00+00:00",
  "revision": 3,
  "updatedAt": "2026-08-10T10:04:00+00:00"
}
```

`savedAt` tiếp tục tương thích với client cũ và vẫn trỏ tới `created_at`; client mới dùng `updatedAt` để hiển thị freshness. `revision` là số nguyên dương, không expose database internals khác.

### 4.3 Update contract

Endpoint mới:

```text
PUT /api/my-plans/{plan_id}
```

Request body:

```json
{
  "title": "Lịch trình cuối tuần",
  "stops": [],
  "expected_revision": 3
}
```

Rules:

- `title` và `stops` dùng validation/limits hiện có (`120` ký tự, tối đa `50` stops).
- `expected_revision` bắt buộc là integer `>= 1`; không chấp nhận boolean hoặc string numeric.
- Query mutation phải ràng buộc đồng thời `id` và `user_id`, rồi `WHERE revision = expected_revision` trong cùng transaction.
- Thành công trả HTTP `200` với `{ "plan": PlanSnapshot }`, trong đó revision đã tăng đúng `+1`.
- Plan không tồn tại hoặc không thuộc user trả `404` như delete/publish hiện tại.
- Revision mismatch trả HTTP `409` với body ổn định:

```json
{
  "detail": "Lịch trình đã thay đổi trên thiết bị khác",
  "code": "plan_revision_conflict",
  "current": {
    "id": "uuid",
    "title": "Bản trên máy khác",
    "stops": [],
    "is_public": false,
    "savedAt": "2026-08-10T10:00:00+00:00",
    "revision": 4,
    "updatedAt": "2026-08-10T10:06:00+00:00"
  }
}
```

Không trả local draft trong response conflict. Client dùng `current` để hiển thị diff và cho phép chọn server/local/merge thủ công; không tự chọn im lặng.

### 4.4 Existing mutations

- `POST /api/my-plans`: insert với `revision=1`, `updated_at=NOW()` và `created_at` giữ nguyên semantics hiện có.
- `POST /api/my-plans/merge`: giữ semantics create-only. Các plan từ thiết bị chưa có server id tiếp tục được insert; không dùng `expected_revision` và không được phép giả lập upsert bằng title.
- `POST /api/my-plans/{id}/publish`: giữ request/response hiện có; mutation phải tăng `revision` và `updated_at` để update sau đó phát hiện conflict.
- `DELETE /api/my-plans/{id}`: giữ behavior/authorization hiện có; không cần revision vì thao tác xóa không merge snapshot.
- Rate-limit, CSRF, Postgres-only guard và ownership check giữ nguyên.

## 5. Feature flag resilience

### 5.1 Phân loại

Registry hiện có được chia thành:

- **Established/legacy flags:** các section đã tồn tại và có `default` ổn định, bao gồm `chat_widget`, `ai_recommendations`, `ai_tips`, `ai_best_time`, `reviews`, `nearby`, `onboarding`.
- **New rollout capability flags:** các key hậu tố `_v1` trong nhóm personalization/rollout (`public_*_v1`, `preference_ui_v1`, `recommendation_explanations_v1`, `trust_drawer_v1`).

### 5.2 Resolution rules

`resolveFeatureFlag(key, flags)` phải áp dụng thứ tự:

1. Nếu `flags` có boolean rõ ràng cho chính `key`, dùng override đó.
2. Nếu `key` là established và settings null, undefined, object rỗng hoặc value không hợp lệ, dùng registry default.
3. Nếu `key` là new rollout capability và settings thiếu/không hợp lệ, trả `false`.
4. Key ngoài registry luôn trả `false`.

Legacy-to-capability mapping không được làm established UI biến mất chỉ vì capability rollout mới chưa được publish. `ai_recommendations`, `ai_tips` và `ai_best_time` resolve độc lập theo established registry default/override; chúng không bị AND với `public_*_v1`. Chỉ các enhancement mới (ví dụ giải thích đề xuất, personalization công khai) mới cần capability flag `true` để bật.

### 5.3 Data hygiene

- `null`, array, string, number và object lồng nhau là malformed settings, không phải explicit false.
- Một key explicit `false` vẫn tắt đúng section legacy tương ứng.
- Không mutate input object; kết quả deterministic giữa SSR và client.
- `resolvePublicCapabilityMode` tiếp tục trả `enhanced | deterministic`; deterministic là fallback hữu ích, không phải blank state.

## 6. Contact CTA contract

Ward phone links trên `web-nuxt/pages/xa-phuong/[id].vue` phải dùng cùng contract với detail/directory funnel:

```html
<a
  data-contact-action="phone"
  data-contact-surface="ward-detail"
  data-contact-entity-id="ward-public-id"
  data-contact-outcome="navigation"
  href="tel:..."
>
  Gọi
</a>
```

Implementation phải gọi handler beacon hiện có trước navigation khi runtime hỗ trợ; nếu beacon lỗi, navigation vẫn tiếp tục. `data-contact-entity-id` dùng id public đã được phép trong UI, không dùng số điện thoại. Metadata phải xuất hiện trên cả primary action và fallback phone CTA nếu hai nhánh cùng render.

Contract tests phải mount/parse real ward surface để chứng minh:

- mỗi phone CTA có `data-contact-action="phone"`;
- có surface, entity id và outcome hợp lệ;
- handler không chặn `tel:` navigation;
- repeated click bị debounce/rate-limit theo contract telemetry hiện có;
- payload không chứa số điện thoại, raw query hoặc tọa độ.

## 7. CI accessibility independence

Job `frontend` giữ thứ tự logic hiện tại nhưng condition được chuẩn hóa:

1. Build và public accessibility gate là hard gates bình thường.
2. Visual smoke chạy và upload evidence với `if: always()` để luôn tạo artifact khi có preview/binary đủ điều kiện.
3. Preview-server step có `if: always()` và kiểm tra `.output`; nếu build không tạo output, step ghi marker `a11y-unavailable` rồi exit non-zero thay vì bị skip.
4. Axe scan và `check_axe` có `if: always()`; nếu preview không sẵn sàng, chúng giữ trạng thái failed/unavailable và không được chuyển thành skipped-green.
5. Stop server và upload axe report luôn `if: always()`.

GitHub Actions mặc định dùng `success()` cho step không có condition; spec này yêu cầu mọi step phụ thuộc vào visual smoke phải khai báo condition tường minh. Kết quả cuối phải giữ được cả lỗi visual smoke và lỗi/không khả dụng của a11y (không chuyển thành xanh giả).

## 8. Data flow và error handling

```text
planner draft + expected_revision
        → auth/CSRF/ownership
        → atomic UPDATE ... WHERE revision = expected_revision
        ├─ 200 full snapshot + revision+1
        └─ 409 current server snapshot → client diff/merge UI

CMS flags
        → shape validation
        → established default OR rollout fail-closed
        → deterministic/enhanced public surface

ward CTA
        → allowlisted contact beacon
        → best-effort send
        └─ tel: navigation always proceeds

visual smoke ─┐
preview/axe ──┼→ independent evidence + hard gate outcomes
artifact upload┘
```

All paths preserve existing auth, ownership, CSRF, rate limits, route semantics and privacy boundary. Errors are explicit, localized where already established, and actionable.

## 9. Testing and acceptance gates

### 9.1 Backend

- Migration applies twice on an empty Postgres and on existing `user_plans` without data loss.
- Create/list include revision/timestamps; publish increments revision.
- PUT succeeds with matching revision and rejects stale revision with exact `409` contract.
- Cross-user id access remains `404`, and CSRF/rate limits remain enforced.
- Merge remains create-only and never silently updates a server plan.
- SQLite/dev returns existing `503` behavior for planner routes.

### 9.2 Frontend

- Established flags resolve to defaults for `null`, `{}`, malformed objects and missing keys.
- Explicit booleans override defaults; rollout flags remain fail-closed.
- Ward contact contract tests pass for phone, map, website and Zalo branches.
- Conflict payload maps to a user-visible diff/recovery state without replacing local draft automatically.

### 9.3 CI/workflow

- Static workflow contract proves a failed visual smoke cannot skip axe scan/gate declaration.
- A missing preview produces an explicit failed accessibility result, not a skipped green path.
- Artifact upload is attempted on both pass and fail paths.

### 9.4 Quality gates

- Focused backend/frontend suites pass.
- Frontend typecheck passes.
- Hard release checks pass.
- No protected primary-checkout file is changed or staged.

## 10. Rollout and rollback

1. Apply migration in staging and verify idempotency/backfill counts.
2. Deploy API read fields first; old clients ignore additive fields.
3. Enable PUT client behavior behind existing planner rollout control, with conflict telemetry monitored.
4. Ship flag resolver fix; malformed settings preserve legacy UI immediately.
5. Ship ward metadata and CI changes.
6. Roll back application code independently if required; never remove `revision`/`updated_at` columns or delete plan data during rollback.

Rollback target for planner client is create/list/merge/delete/publish behavior without PUT; server remains backward compatible.

## 11. Implementation slicing

1. **Planner contract:** migration, serializers, PUT, publish revision bump, backend tests and API docs.
2. **Flag resilience:** resolver classification, malformed-input handling and frontend tests.
3. **Contact funnel:** ward CTA metadata/handler and contract tests.
4. **CI gate independence:** workflow conditions and static contract tests.
5. **Cross-slice verification:** typecheck, focused suites, hard gates and final whole-branch review.

Each slice is independently revertible and must be reviewed before the next slice. No slice touches the protected primary-checkout files.

## 12. Completion criteria

- Planner writes are revision-safe and conflicts expose a complete current snapshot.
- Legacy default-on sections remain visible under unavailable/malformed CMS settings.
- Every ward phone CTA emits privacy-safe contact metadata and best-effort telemetry.
- Accessibility checks cannot be bypassed by a preceding visual failure.
- Existing behavior and route/auth/RBAC/data ownership contracts remain intact.
- Spec is precise enough to become an implementation plan with independent subagent tasks and per-task review checkpoints.
