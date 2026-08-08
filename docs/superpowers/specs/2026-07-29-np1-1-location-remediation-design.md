# Thiết kế NP-1.1: Location Remediation và Privacy-Safe Self-Healing

> **STATUS:** `draft-for-review` - 2026-07-29.
> **Phạm vi:** remediation cycle cho hai blocker còn lại của NP-1: cách ly dữ liệu khu vực cũ không thể chứng minh an toàn và sửa precedence của lựa chọn thủ công `Toàn tỉnh`.
> **Worktree:** `C:\Code\vl360-wt\np1-identity-location-trust` trên nhánh `codex/np1-identity-location-trust`.
> **Base:** `2bca1dd7f3afce9ad47f70b51b815da62305e559`.

## 1. Kết luận điều hành

Phương án được duyệt là **A+ - Privacy-Safe Self-Healing**.

NP-1.1 không cố khôi phục hoặc đoán lại dữ liệu khu vực đã được ghi trước khi persistence boundary được siết chặt. Migration 073 và các guard runtime chỉ xóa phần location không thể chứng minh an toàn, chuyển snapshot về `default/off`, yêu cầu người dùng chọn lại khu vực và giữ nguyên sở thích, personalization state, consent history, recommendation cutoff cùng toàn bộ personal workspace.

Token xác nhận GPS/IP tiếp tục là token stateless ký HMAC. Token được gắn với user và preference revision, hết hiệu lực sau lần ghi thành công hoặc bất kỳ thay đổi preference nào. Không thêm bảng one-time token, nonce store, token cleanup job hoặc cột lưu token.

## 2. Quyết định đã được duyệt

1. Tự động cách ly dữ liệu region cũ không an toàn; không export hoặc ghi lại snapshot cũ.
2. Migration `073` chỉ reset location về `default/off`; không xóa interests, personalization consent/history, recommendation reset hoặc workspace.
3. Read guard và final-write guard dùng cùng một region invariant.
4. Manual precedence dựa vào `location_source = 'manual'`, không dựa vào `region_id` truthy; lựa chọn `Toàn tỉnh` có `region_id = NULL` vẫn thắng GPS/IP.
5. Token GPS/IP bind với preference revision. Manual change hoặc confirmation thành công làm token cũ hết hiệu lực.
6. Token stale trả `409`; token giả mạo, hết hạn, sai user hoặc sai contract trả `422`.
7. Không lưu hoặc log raw IP, tọa độ, raw region value bị cách ly hoặc token.
8. Dữ liệu đã cách ly không được phục hồi khi rollback.
9. Browser/Stitch rendered verification không thuộc scope NP-1.1 và không được tuyên bố pass.
10. Không thêm bảng one-time token hoặc bảng nonce dưới bất kỳ hình thức nào.

## 3. Blocker cần đóng

### 3.1 Snapshot cũ có thể đi xuyên qua load/export/final merge

`_snapshot_from_mapping()` hiện chuẩn hóa revision, boolean, interests và timestamp nhưng chưa kiểm tra region tuple. Vì vậy một row đã chứa IP/tọa độ hoặc tuple giả mạo trước bản fix có thể:

- được trả bởi `load_preferences()`;
- đi vào export tài khoản;
- được dùng làm current snapshot khi PATCH một field không liên quan;
- được ghi lại bởi final merge;
- được trả bởi `record_recommendation_reset()`.

NP-1.1 phải đảm bảo mọi đường đọc và mọi final snapshot đều đi qua cùng một invariant trước khi ra khỏi persistence boundary.

### 3.2 `Toàn tỉnh` có thể bị GPS ghi đè

Manual choice `Toàn tỉnh` là tuple hợp lệ:

```text
region_id = NULL
region_label = NULL
region_scope = all
location_source = manual
location_accuracy = unknown
```

Guard hiện tại chỉ chặn nguồn thấp hơn khi `current_snapshot["region_id"]` truthy. Do đó token GPS hợp lệ có thể ghi đè manual `Toàn tỉnh`. NP-1.1 thay điều kiện này bằng source precedence thực: `manual > gps > ip > default`.

## 4. Mục tiêu và phi mục tiêu

### 4.1 Mục tiêu

- Sau migration 073, không còn row location legacy nào không có provenance đáng tin cậy.
- Không có read, export, unrelated PATCH hoặc reset flow nào làm lộ hoặc tái lưu region không an toàn.
- Manual `Toàn tỉnh` có cùng quyền ưu tiên với mọi manual choice khác.
- Token GPS/IP có hiệu quả one-use bằng optimistic revision, không cần server-side token state.
- Hệ thống tự phục hồi có giới hạn nếu backup/import cũ đưa row sai trở lại.
- UI giải thích trung tính, giúp người dùng chọn lại khu vực mà không làm mất interests hoặc workspace.

### 4.2 Phi mục tiêu

- Không khôi phục hoặc suy đoán giá trị region đã cách ly.
- Không backfill GPS/IP cũ sang provenance mới.
- Không thêm marketplace, booking, payment, travel mode hoặc local mode.
- Không sửa homepage, public catalog, trust drawer hoặc recommendation composer ngoài ảnh hưởng trực tiếp của sanitized preference.
- Không tạo audit trail chứa before/after region thô.
- Không triển khai Browser/Stitch visual verification trong cycle này.

## 5. Region invariant chuẩn

Một region snapshot chỉ hợp lệ khi thỏa đồng thời shape, provenance và state consistency.

### 5.1 Tuple `manual`

Manual chỉ chấp nhận đúng registry server-owned hiện tại:

| `region_id` | `region_label` | `region_scope` | `location_accuracy` |
|---|---|---|---|
| `province-vl` | `Vĩnh Long` | `province` | `province` |
| `province-bt` | `Bến Tre` | `province` | `province` |
| `province-tv` | `Trà Vinh` | `province` | `province` |
| `NULL` | `NULL` | `all` | `unknown` |

Manual tuple không cần GPS/IP consent. `location_enabled` có thể bật hoặc tắt vì nó chỉ biểu thị quyền dùng resolver; manual region vẫn là nguồn ưu tiên.

Registry manual trong Python và PostgreSQL constraint là một contract versioned. Thêm khu vực manual mới phải cập nhật cả hai trong cùng migration/release; không được chỉ sửa frontend choices.

### 5.2 Tuple `gps/ip`

- `region_id` bắt buộc có giá trị bounded, không mang hình dạng IP/tọa độ.
- `region_label` nullable nhưng nếu có phải bounded và không mang hình dạng IP/tọa độ.
- `region_scope` thuộc `ward/district/province`.
- `location_accuracy` thuộc `ward/district/province/unknown`.
- `location_enabled = true` và `location_consent_state = granted`.
- `location_provenance_version = resolver-v2`.

`location_provenance_version` là metadata nội bộ, không xuất hiện trong public preference response, recommendation response hoặc account export. Trường này chỉ chứng minh row được tạo bởi contract resolver hậu cutover; nó không chứa IP, tọa độ, token, nonce hoặc provider payload.

### 5.3 Tuple `default`

```text
region_id = NULL
region_label = NULL
region_scope = unknown
location_source = default
location_accuracy = unknown
location_provenance_version = NULL
```

`location_consent_state` có thể là `unknown`, `denied`, `off` hoặc `expired` theo hành vi người dùng. `location_enabled` có thể tạm thời bật trong lúc chờ resolve; default tuple không được trình bày như một khu vực đã xác nhận.

### 5.4 Trạng thái cần xác nhận lại

`location_reconfirm_required = true` chỉ hợp lệ cùng tuple `default`, `location_enabled = false` và `location_consent_state = off`.

Chỉ hai hành động được xóa cờ này:

1. ghi một manual tuple hợp lệ, bao gồm `Toàn tỉnh`;
2. xác nhận một token `resolver-v2` hợp lệ.

Thay đổi interests, personalization toggle, reset recommendation hoặc chỉ bật location không được tự xóa cờ.

### 5.5 Phát hiện giá trị thô

Application validator tiếp tục chặn IPv4, IPv6, coordinate pair, DMS và hemisphere coordinate trong `region_id/region_label`. PostgreSQL bổ sung constraint cho các high-confidence pattern tương đương. Các pattern không được chặn tên địa bàn có số nguyên thông thường như `Phường 1`.

## 6. Migration 073

Tên migration dự kiến: `073_location_preference_remediation.sql`.

### 6.1 Schema additive

Thêm vào `user_preferences`:

- `location_reconfirm_required BOOLEAN NOT NULL DEFAULT FALSE`;
- `location_provenance_version VARCHAR(32)`.

Đồng thời widen `revision` từ PostgreSQL `INTEGER` sang `BIGINT` và giới hạn contract ở `Number.MAX_SAFE_INTEGER` (`9.007.199.254.740.991`). Backend/Pydantic/frontend cùng dùng giới hạn này để revision luôn round-trip chính xác qua JSON. Việc widen cho phép migration advance cả row đang ở giới hạn integer cũ mà không reset revision hoặc làm user mất khả năng chọn lại khu vực.

Readiness contract tăng lên schema version `73` và bắt buộc hai cột mới.

### 6.2 Tập row phải cách ly

Migration cách ly mọi row thuộc một trong các nhóm sau:

- `location_source IN ('gps', 'ip')` tồn tại trước cutover; các row này không có cách chứng minh đã đi qua resolver contract mới, kể cả khi text trông hợp lệ;
- manual tuple không khớp chính xác registry server-owned;
- default tuple chứa region data hoặc scope/accuracy không nhất quán;
- `region_id/region_label` có high-confidence IP/coordinate shape;
- source, consent, enabled hoặc provenance không tạo thành tuple hợp lệ.

Valid canonical manual tuple, bao gồm manual `Toàn tỉnh`, và valid default tuple được giữ nguyên.

### 6.3 Atomic quarantine update

Với mỗi row cần cách ly, migration chỉ thay location fields:

```text
region_id = NULL
region_label = NULL
region_scope = unknown
location_source = default
location_accuracy = unknown
location_consent_state = off
location_enabled = false
location_provenance_version = NULL
location_reconfirm_required = true
updated_at = NOW()
```

`explicit_interests`, `personalization_enabled`, `recommendation_reset_at`, `consent_version`, `created_at` và mọi bảng workspace không đổi. `user_preference_consents` giữ nguyên; migration không tạo consent event giả vì thao tác cách ly không phải quyết định do người dùng thực hiện.

Revision được advance đúng một đơn vị để vô hiệu hóa client snapshot cũ. Row đang ở giới hạn integer cũ vẫn advance được nhờ bước widen sang `BIGINT`; không wrap, reset hoặc tái sử dụng revision cũ.

Migration chỉ phát aggregate count nếu cần vận hành. Không ghi raw value, user ID hoặc before/after region vào notice, audit hay telemetry.

### 6.4 Constraint hậu cách ly

Sau update, migration thêm và validate ba nhóm constraint:

1. region text không có high-confidence raw IP/coordinate shape;
2. source tuple đúng manual/gps/ip/default invariant;
3. reconfirm state và provenance state nhất quán.

Constraint là fail-closed cho write mới. Dữ liệu đã bị cách ly không có down-migration phục hồi.

## 7. Runtime guard và self-healing

### 7.1 Một validator dùng chung

`agent/user_preferences.py` có một canonical validator nhận persisted mapping và trả một trong hai kết quả:

- snapshot hợp lệ đã normalize;
- invalid reason thuộc allowlist: `raw_shape`, `manual_tuple`, `resolver_tuple`, `default_tuple`, `provenance` hoặc `state_mismatch`.

Reason không chứa raw value. Read guard, final-write guard, import/restore adapter và self-healing worker đều dùng validator này. PostgreSQL constraints mirror cùng contract và có parity tests.

### 7.2 Read guard

`load_preferences()` không trả row trực tiếp. Nếu row invalid:

1. khóa/compare revision của row;
2. cập nhật riêng location fields về quarantine snapshot;
3. advance revision;
4. reload một lần nếu có concurrent conflict;
5. trả snapshot đã sanitized.

Nhờ đó account export và recommendation paths đang gọi `load_preferences()` tự nhận dữ liệu an toàn. Read guard không cache hoặc log giá trị cũ.

### 7.3 Final-write guard

Sau authorize + merge nhưng trước `_write_values()`, toàn bộ final snapshot phải qua canonical validator. Guard này áp dụng cả khi PATCH chỉ thay interests hoặc personalization state, vì current row cũ không được phép đi xuyên qua merge.

`record_recommendation_reset()` phải dùng cùng transactional mutation boundary thay vì upsert rồi trả `_row_snapshot()` trực tiếp. Mọi application-level import/restore preference cũng phải gọi validator; client không được tự cung cấp `location_provenance_version` hoặc `location_reconfirm_required`.

Nếu incoming user mutation tự tạo invalid tuple, trả `422` và không ghi. Nếu invalidity đến từ persisted legacy row và expected revision vẫn khớp, hệ thống dùng sanitized snapshot làm base, merge mutation rồi thực hiện một final write duy nhất với một lần advance revision. Raw region cũ không được ghi ở bước trung gian. Nếu mutation chứa manual/token hợp lệ thì final snapshot có thể hoàn tất reconfirm ngay; mutation không-location giữ `location_reconfirm_required = true`.

### 7.4 Bounded self-healing worker

Scheduler chạy một worker idempotent, tối đa `100` row mỗi lần, theo thứ tự ổn định `updated_at, user_id`. Worker chỉ xử lý row vi phạm canonical invariant, dùng compare-and-update theo revision và bỏ qua row vừa bị thay đổi đồng thời.

Mục đích của worker là xử lý drift từ backup/import cũ hoặc restore đã tạm vô hiệu constraint. Worker không thay migration 073 và không scan raw location sang hệ thống khác. Một lần chạy lặp lại trên database sạch phải có side effect bằng không.

## 8. Token confirmation v2 không cần bảng one-time token

### 8.1 Contract token

Purpose đổi từ `location-confirmation-v1` sang `location-confirmation-v2` để mọi token cũ tự bị từ chối.

Envelope/payload ký HMAC chứa tối thiểu:

- `purpose`;
- `user_id`;
- `issued_at`;
- `expires_at`;
- `preference_revision`;
- normalized `region_id`, `region_label`, `region_scope`, `location_source`, `location_accuracy`.

Token không chứa raw GPS, raw IP, nonce cần lưu, consent payload hoặc provider response. TTL giữ ngắn, mặc định `300` giây.

### 8.2 Issuance

`POST /api/me/location/resolve`:

1. xử lý GPS/IP tạm thời;
2. bỏ raw input sau khi tạo normalized region;
3. load sanitized preference revision hiện tại;
4. phát token v2 bind với revision đó;
5. trả normalized suggestion và token với `Cache-Control: no-store`.

Token không đi vào state persistence, response cache, audit hoặc telemetry. Frontend chỉ giữ token trong memory của interaction hiện tại.

### 8.3 Confirmation và effective one-use

`PATCH /api/me/preferences` yêu cầu body `revision = R` và token có `preference_revision = R`.

- Nếu token revision khác body/current revision, trả `409` cùng sanitized current snapshot.
- Nếu signature, purpose, expiry, user binding hoặc normalized payload sai, trả `422`.
- Final update dùng optimistic predicate `WHERE revision = R` và advance revision thành `R + 1`.

Vì lần ghi thành công làm revision thay đổi, token tự stale ngay sau lần dùng đầu tiên. Hai request đồng thời chỉ có một request thắng; request còn lại nhận `409`. Manual change hoặc bất kỳ preference mutation nào diễn ra sau issuance cũng làm token stale.

Không cần và không được thêm:

- one-time token table;
- nonce table/store;
- used-token cache;
- token revocation cron;
- token column trong `user_preferences`.

### 8.4 Precedence fix

Lower-priority guard dựa trên `current_snapshot["location_source"]`, không dựa trên sự tồn tại của `region_id`.

```text
current source = manual -> GPS/IP không thay region
current source = gps    -> IP không thay region
current source = ip     -> GPS có thể nâng cấp region
current source = default -> GPS/IP có thể đặt region
```

Manual `Toàn tỉnh` vì vậy được bảo vệ giống `Vĩnh Long`, `Bến Tre` và `Trà Vinh`.

## 9. Public API và export contract

Public `PreferenceSnapshot` bổ sung:

```text
location_reconfirm_required: boolean
```

`location_provenance_version` là internal-only và không được trả ra public API/export.

Các endpoint giữ `Cache-Control: no-store`. Export phải lấy preference qua sanitized load boundary; không đọc row raw riêng. Nếu read guard vừa quarantine row, export chỉ chứa `default/off`, cờ cần xác nhận lại và dữ liệu không-location được giữ nguyên.

## 10. UI/state flow

Khi `location_reconfirm_required = true`, `/cai-dat#khu-vuc-de-xuat` hiển thị banner có ngôn ngữ trung tính:

> Khu vực trước đây cần được chọn lại để bảo vệ quyền riêng tư. Sở thích và dữ liệu đã lưu của bạn vẫn được giữ nguyên.

Action chính: `Chọn lại khu vực`.

- Action đưa focus đến nhóm manual region choices.
- Manual choices, kể cả `Toàn tỉnh`, không yêu cầu geolocation.
- Tùy chọn GPS/IP chỉ chạy sau user gesture và consent rõ ràng.
- Không hiển thị raw value cũ hoặc lý do kỹ thuật chi tiết.
- Explicit interests vẫn hiển thị và tiếp tục có ưu tiên cao hơn inferred interests.
- Feed dùng explicit interests cùng public fallback trong thời gian chưa chọn lại region.
- Chọn manual hoặc confirm token hợp lệ làm response trả `location_reconfirm_required = false` và banner biến mất.
- `409` do token stale cập nhật snapshot server, bỏ token cũ và yêu cầu resolve lại; UI không tự retry token stale.

UI tận dụng component, token và layout hiện có của settings screen. NP-1.1 không mở một redesign Stitch mới.

## 11. Observability và privacy

Chỉ cho phép aggregate metrics/count theo nhóm reason và origin, ví dụ:

```text
location_preference_quarantine_total{origin=migration|read|worker, reason=...}
location_confirmation_rejected_total{reason=stale|invalid|expired}
```

Không metric/log label theo user, region ID, region label, IP, tọa độ hoặc token. Scheduler log tối đa số row đã xử lý theo batch và reason allowlist. Exception không được chứa serialized snapshot.

Các static checks phải xác nhận không có cột/bảng mới mang tên `latitude`, `longitude`, `ip`, `token`, `nonce`, `score` hoặc `weight` trong preference schema.

## 12. Error và recovery states

| Tình huống | Hành vi bắt buộc |
|---|---|
| Legacy row unsafe được load | Atomic quarantine, trả sanitized snapshot |
| Legacy row unsafe được export | Export sanitized snapshot, không lộ raw value |
| Unrelated PATCH trên legacy row | Quarantine trước, giữ mutation không-location nếu hợp lệ |
| Manual `Toàn tỉnh` + GPS token | Manual region không bị thay; revision vẫn bảo vệ concurrency |
| Token cũ v1 | `422`, không side effect |
| Token v2 hết hạn/sai user/tamper | `422`, không side effect |
| Token v2 stale revision | `409` cùng current sanitized snapshot |
| Hai confirmation đồng thời | Một thành công, một `409` |
| Worker chạy lại | Idempotent, không thay row sạch |
| Resolver flag tắt | Manual choice và public fallback vẫn hoạt động |
| UI flag tắt | Không làm yếu database constraint/read guard |

## 13. Rollout và rollback

Thứ tự rollout:

1. tắt tạm `preference_ui_v1`, `PREFERENCE_PROFILE_V1` và `LOCATION_RESOLVER_V1`; public fallback vẫn phục vụ bình thường;
2. chờ preference/resolver mutation đang chạy hoàn tất rồi deploy migration 073, quarantine và constraints;
3. deploy code đọc/ghi schema 73, token v2, read/final-write guard và self-healing worker;
4. readiness 73, migration smoke và focused privacy tests phải pass trước khi mở traffic mutation;
5. bật `PREFERENCE_PROFILE_V1`, sau đó `preference_ui_v1` cho manual/reconfirm flow;
6. bật `LOCATION_RESOLVER_V1` cuối cùng cho token v2 và theo dõi aggregate quarantine/reconfirm/stale rates.

Không chạy app cũ với resolver v1 sau khi constraint provenance của migration 073 đã có hiệu lực. Nếu deploy code v2 thất bại, giữ các flag mutation tắt và phục vụ public fallback thay vì nới constraint.

Rollback an toàn:

- Có thể tắt `LOCATION_RESOLVER_V1`; manual region vẫn hoạt động.
- Có thể tắt `preference_ui_v1`; backend vẫn sanitize và public fallback vẫn hoạt động.
- Không rollback PostgreSQL constraints.
- Không phục hồi region đã cách ly.
- Không bật lại token v1 khi rollback; resolver phải fail closed thay vì quay về contract không bind revision.

## 14. Test contract

### 14.1 Migration/PostgreSQL

- Seed raw IPv4, IPv6, coordinate pair, DMS, arbitrary manual tuple, plausible legacy GPS/IP, valid canonical manual, manual `Toàn tỉnh` và valid default.
- Apply migration 073 thật trên PostgreSQL disposable.
- Mọi legacy GPS/IP và invalid tuple chuyển `default/off`, `location_reconfirm_required = true`.
- Valid canonical manual, manual `Toàn tỉnh` và default không bị thay.
- Interests, personalization state, consent history, reset timestamp và workspace rows giữ nguyên.
- Direct SQL insert/update vi phạm raw-shape, tuple, provenance hoặc reconfirm constraint bị từ chối.
- Readiness từ chối schema 72 hoặc thiếu từng cột mới; schema 73 đầy đủ được chấp nhận.
- Revision ở giới hạn integer cũ được advance sau khi widen; revision vượt `Number.MAX_SAFE_INTEGER` bị từ chối.
- Migration không tạo bảng/cột token hoặc nonce.

### 14.2 Backend behavior

- `load_preferences()` quarantine row unsafe và lần load sau idempotent.
- Export không chứa raw location sau khi seed legacy row.
- PATCH interests trên legacy row giữ interests mới nhưng không tái lưu region cũ.
- Recommendation reset dùng sanitized mutation boundary.
- Manual `Toàn tỉnh` không bị GPS/IP ghi đè.
- Token v2 bind user, purpose, TTL và revision.
- Manual mutation/confirmation/recommendation reset sau issuance làm token stale.
- Hai confirmation concurrent có đúng một success.
- Worker xử lý tối đa 100 row, không log raw data và không đổi row sạch.
- Không có raw GPS/IP/token trong DB, audit, cache hoặc telemetry fixtures.

### 14.3 Frontend behavior-level

- Mount real settings surface với `location_reconfirm_required = true`; banner và CTA xuất hiện.
- CTA focus đúng manual region group; không gọi geolocation.
- Explicit interests vẫn hiển thị sau quarantine.
- Manual selection thành công xóa banner theo server snapshot.
- Stale token `409` bỏ suggestion/token cũ, hiển thị current snapshot và yêu cầu resolve lại.
- Feature flag off giữ public fallback và không gọi resolver.
- Test mount component/composable thực; cấm `readFileSync(...).toContain(...)` hoặc kiểm source text thay cho hành vi.

### 14.4 Verification gates

- Focused backend unit và PostgreSQL suites pass.
- Affected mounted frontend suites pass.
- Full frontend test, typecheck và build pass.
- Migration apply/readiness pass trên database trắng và database có fixture legacy.
- `git diff --check`, staged hard gate và privacy/static scans pass.
- Official backend runner 6.901 giây chỉ được tuyên bố pass nếu thực sự chạy lại.
- Browser/Stitch chỉ được ghi `not run/not in scope`, không tạo evidence giả.

## 15. Acceptance criteria

- Không còn đường load/export/final merge nào trả hoặc tái ghi legacy raw region.
- Mọi legacy GPS/IP không có provenance v2 đều bị cách ly.
- Manual `Toàn tỉnh` luôn giữ precedence cao hơn GPS/IP.
- Token cũ hết hiệu lực bằng revision và optimistic update, không có bảng one-time token.
- Người dùng chọn lại khu vực mà không mất interests, consent history hoặc workspace.
- PostgreSQL chặn direct invalid write và runtime self-heals imported legacy row.
- Observability chỉ có aggregate count/reason; không có raw location hoặc user-level label.
- Rollback flag không làm yếu privacy constraint hoặc phục hồi dữ liệu đã cách ly.

## 16. Self-review

- Không còn mục bỏ ngỏ hoặc quyết định bị trì hoãn sang implementation plan.
- Migration, runtime validator, token v2, API, UI và test đều dùng cùng precedence/invariant.
- `location_reconfirm_required` là public state; `location_provenance_version` là internal-only.
- Consent history được giữ nguyên; current location state chuyển `off` nhưng không tạo consent event giả.
- Token one-use dựa trên revision và atomic write; không có server-side token state.
- Scope chỉ đóng hai blocker NP-1 và các defense-in-depth trực tiếp liên quan.
- Browser/Stitch và official full backend runner không bị mô tả quá mức evidence thực tế.

## 17. Decision gate

Sau khi người dùng duyệt đặc tả này, bước tiếp theo là dùng `superpowers:writing-plans` để lập implementation plan `docs/superpowers/plans/2026-07-29-np1-1-location-remediation.md`, sau đó mở ledger SDD riêng cho NP-1.1. Không tái sử dụng ledger NP-1 cũ và không merge nhánh trước whole-branch review.
