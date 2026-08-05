> STATUS: active — rà soát OWASP Top 10 (2021) trên code thật, ngày 2026-08-05.
> Người rà: agent trong worktree `.worktrees/tri-region-color`. Không sửa code, chỉ đọc + chạy kiểm chứng.
> Mọi kết luận đều kèm `path:line`. Chỗ nào không có bằng chứng thì ghi thẳng "chưa kiểm được".

# Rà OWASP Top 10 — vinhlong360, 2026-08-05

## 0. Cách rà và những gì đã chạy thật

Rà trên **app đã merge** (`server.app`), không rà từng router rời — đúng bài học từ vụ `GET /api/me/activity`
khai báo hai lần mà 9.535 test vẫn xanh. Bốn việc đã chạy:

1. **Liệt kê route trên app merge**: 403 route. Kiểm trùng `(method, path)` → **0 trùng**
   (tức lỗi khai báo hai lần của `/api/me/activity` đã được vá; route hiện sống ở `agent/social.py:1601`,
   `agent/public_api.py:2175` có ghi chú xác nhận).
2. **Probe hành vi bằng `TestClient` trên app merge** — gửi request thật không kèm chứng thực,
   xem status code trả về (không assert chuỗi trong source).
3. **Quét AST toàn bộ f-string chứa từ khoá SQL** trong `agent/` + `scripts/`: 650 f-string SQL,
   161 chỗ nội suy không phải placeholder → đọc tay từng nhóm.
4. **Probe hành vi che-log**: nạp `middleware` cho gắn bridge, gọi `logging.getLogger(<tên>).error()`
   với một chuỗi chứa email + số điện thoại + `api_key=…`, rồi **bắt chính stream của handler** để xem
   cái gì thực sự được in ra. Không đoán từ code.

Test đã chạy (chỉ tập con liên quan bảo mật, không chạy full suite):

```
python -m pytest -q agent/tests/test_p0_security.py agent/tests/test_security_advanced.py \
  agent/tests/test_auth_security_hardening.py agent/tests/test_writepaths_auth.py \
  tests/test_crawler_ssrf.py tests/test_pinned_http_consumers.py -p no:randomly
→ 220 passed, 3 skipped, 1 warning in 15.01s
```

**Cảnh báo về giá trị của con số 220 đó**: `agent/tests/test_auth_security_hardening.py` có **24 lần**
dùng `inspect.getsource()` để assert chuỗi trong source. Loại test này đỏ khi refactor đúng và xanh khi
hành vi sai — đừng coi nó là bảo chứng. Toàn repo có 79/250 file test chạm `getsource`.

---

## 1. Bảng tổng kết

| Mục | Kết luận | Mức nghiêm trọng của phần thiếu |
|---|---|---|
| A01 Broken Access Control | **ĐẠT** (có 1 điểm nợ thiết kế) | Thấp |
| A02 Cryptographic Failures | **THIẾU** | **Cao** (khoá TOTP) |
| A03 Injection | **ĐẠT** | — |
| A04 Insecure Design | **THIẾU** | Trung bình |
| A05 Security Misconfiguration | **THIẾU** | Trung bình |
| A06 Vulnerable Components | **THIẾU** | Trung bình |
| A07 Auth Failures | **ĐẠT** (có 1 oracle liệt kê tài khoản) | Thấp–Trung bình |
| A08 Data Integrity | **ĐẠT** (upload) / **THIẾU** (chuỗi cung ứng) | Trung bình |
| A09 Logging Failures | **THIẾU** | Trung bình |
| A10 SSRF | **ĐẠT** | Thấp (nợ egress còn lại) |

Xuyên suốt 10 mục có **một vấn đề chung nghiêm trọng hơn từng mục riêng lẻ**: 34/52 hàm bảo mật public
trong `agent/auth_middleware.py` **không được gọi ở bất kỳ đâu trong code sản xuất** — chỉ tồn tại để test.
Chi tiết ở mục A04.

---

## 2. Chi tiết từng mục

### A01 — Broken Access Control → **ĐẠT**

**Ba lớp guard, đã xác nhận trên app merge:**

- Router admin gắn dependency ở cấp router, không phải từng hàm:
  `agent/admin.py:531` — `APIRouter(prefix="/admin", dependencies=[Depends(require_admin), Depends(require_csrf)])`.
  `require_admin` ở `agent/admin.py:478` làm 4 việc: rate-limit theo IP (`agent/admin.py:462`),
  xác thực bằng `X-Admin-Key` (`agent/middleware.py:481`, so sánh `hmac.compare_digest`, fail-closed khi
  chưa cấu hình key) **hoặc** phiên admin đăng nhập, kiểm scope RBAC, rồi ghi audit mọi mutation.
- **Default-deny cho scope**: `agent/admin.py:497-503` — path admin mutating **không** có rule trong
  `ADMIN_SCOPE_RULES` (`agent/admin.py:180`) thì chỉ master (`*`/admin-key/superadmin) qua được.
  Đây là chống-fail-open đúng cách: thêm endpoint mutating mới mà quên khai scope thì nó siết, không mở.
- **Lớp chặn thứ ba, độc lập với router**: `agent/server.py:1310-1329` — middleware `gate_internal_endpoints`
  trả **404** cho `/system/*`, `/checkpoints`, `/confirmations`, `/confirm/`, `/reject/`, `/metrics`,
  `/vectors/stats`, `/analytics`, `/ab-testing`, `/prompt-cache`, `/freshness` nếu không có `X-Admin-Key` hợp lệ.

**Bằng chứng hành vi (probe trên app merge, không kèm chứng thực):**

```
GET    /admin/entities                                    401
POST   /admin/entities                                    401
DELETE /admin/entities/abc                                401
POST   /admin/users/{uuid}/role                           401
PUT    /admin/site-settings/foo                           401
POST   /reload                                            401
POST   /vectors/build                                     401
POST   /system/learning/run                               404  (bị gate_internal_endpoints chặn trước)
POST   /checkpoints                                       404  (nt)
POST   /image/recognize                                   401
GET    /api/me/activity                                   503  (require_pg — SQLite local, đúng thiết kế)
POST   /api/posts                                         503  (nt)
```

**Route mutating không có guard ở tầng dependency**: quét ra 25/403. Đọc tay từng cái:

- Một nhóm có guard **trong thân hàm**. Đính chính bản rà đầu: đo bằng
  `grep -c "await require_admin_scope" agent/server.py` cho **7** chỗ, không phải 12 — phần còn
  lại được chặn bởi `gate_internal_endpoints` (`agent/server.py:1310-1329`, trả 404) chứ không
  phải bởi guard trong thân hàm. Các vị trí đã đối chiếu:
  `agent/server.py:3922` `/reload`, `agent/server.py:4737` `/vectors/build`,
  `agent/server.py:4316` `/system/learning/run`, `agent/server.py:5075` `/system/dynamic-agents/create`,
  `agent/server.py:4864` `/image/recognize`, `agent/server.py:4946` `/system/guardrails/check-input`,
  `agent/server.py:5026` `/system/semantic-cache/invalidate`, `agent/server.py:5055` `/system/judge/evaluate`,
  `agent/server.py:4435` `/checkpoints`, `agent/server.py:4452` `/checkpoints/{id}/resume`,
  `agent/server.py:4479` `/confirm/{id}`, `agent/server.py:4492` `/reject/{id}`.
  → An toàn, **nhưng** guard trong thân hàm không hiện ra trong OpenAPI và không bắt được bằng
  bất kỳ cổng tĩnh nào soi `route.dependant`. Ai đọc `/openapi.json` sẽ tưởng chúng là public.
- 5 cái là endpoint auth công khai theo thiết kế (`/auth/login`, `/auth/request-otp`, `/auth/verify-otp`,
  `/auth/2fa/verify`, `/auth/check-phone`) — đều có `_require_pg` + rate-limit.
- 8 cái công khai thật sự: `/chat`, `/chat/stream`, `/feedback`, `/api/client-error`, `/api/report`,
  `/api/entities/{id}/report-stale`, `/api/entities/{id}/view-contact`, `/api/itineraries/optimize-order`.
  7/8 có rate-limit; cái thứ 8 xem A04.

**Phân quyền cấp đối tượng (chống IDOR)** — có kiểm quyền sở hữu thật:
`agent/social.py:844` (xoá bài: chủ bài hoặc admin/moderator), `agent/social.py:906-913`
(`_post_check_owner` cho sửa bài). Không phải chỉ dựa vào ID khó đoán.

**Điểm nợ (Thấp)**: `agent/database.py:1815` — allowlist của `update_user` chứa `role`, `is_active`,
`password_hash`, `deleted_at`. Hiện chỉ có **một** caller (`agent/auth.py:1275`) và caller đó dựng dict
`fields` tường minh từ `ProfileUpdate` (`agent/auth.py:425-430`, chỉ 5 trường hồ sơ) nên **chưa** có lỗ
mass-assignment. Nhưng nếu sau này ai đó viết `db.update_user(uid, **body.model_dump())` thì đó là leo
quyền tức thì, không cần thêm bug nào khác.

**Điểm chết vô hại**: `agent/admin.py:240-241` — `admin_scopes_for_user` đọc thêm scope từ các trường
`admin_scopes` / `scopes` / `permissions` của user. Bảng `users` trong `init.sql` **không có** cột nào
trong ba cái đó (chỉ `admin_audit_events.actor_scopes` ở `init.sql:481`), nên nhánh này luôn rỗng.
Không phải lỗ hổng, nhưng là ba tên trường đang chờ ai đó vô tình tạo cột trùng tên.

### A02 — Cryptographic Failures → **THIẾU**

**Phần ĐẠT:**

- Mật khẩu: PBKDF2-HMAC-SHA256, salt 16 byte ngẫu nhiên mỗi mật khẩu, **310.000 vòng**
  (`agent/auth.py:463-466`, `agent/config.py:118`) — đúng ngưỡng OWASP khuyến nghị cho PBKDF2-SHA256.
  So sánh bằng `hmac.compare_digest` (`agent/auth.py:476`). Có đường nâng cấp hash cũ 200.000 vòng
  (`agent/auth.py:478-480`) và tự rehash khi đăng nhập (`agent/auth.py:921-931`).
- Chống timing oracle khi tài khoản không tồn tại: vẫn chạy PBKDF2 trên `_DUMMY_HASH`
  (`agent/auth.py:469`, `agent/auth.py:891`).
- Session token: `secrets.token_urlsafe(48)` (`agent/auth.py:451`), **lưu DB dưới dạng SHA-256**
  (`agent/auth.py:454-458`) — lộ DB không dùng lại token được. Entropy đủ nên SHA-256 là lựa chọn đúng.
- TOTP: bí mật **mã hoá Fernet** khi lưu, khoá dẫn xuất HKDF-SHA256 (`agent/twofactor.py:56-60`);
  mã khôi phục thì hash SHA-256 dùng-một-lần.
- Cookie: `httponly=True`, `samesite=lax`, `path=/` mặc định; production thêm `secure=True` +
  `domain=.vinhlong360.vn` (`agent/auth_middleware.py:1132-1148`). Nhận diện production không chỉ
  dựa vào biến môi trường mà còn theo `x-forwarded-proto` + host (`agent/auth.py:147-157`), và
  chủ động **bỏ** `secure` khi chạy localhost (`agent/auth.py:165-167`) để dev không tự bắn chân.
- `CSRF_SECRET` fail-closed ở production: `agent/auth_middleware.py:104-107` ném `RuntimeError`.

**Phần THIẾU (Cao) — khoá mã hoá TOTP không có ai canh:**

`agent/twofactor.py:36-53` chọn khoá theo thứ tự `TOTP_ENC_KEY` → `JWT_SECRET` → `ADMIN_API_KEY` →
fallback dev cố định `b"vl360-dev-totp-fallback-do-not-use-in-prod"`.
Nhưng `agent/config.py:151-168` (`validate_production_keys`) **không kiểm `TOTP_ENC_KEY`**, và
`JWT_SECRET` bị bỏ qua có chủ ý (`agent/config.py:160`, mặc định rỗng). Hệ quả cụ thể:

- Prod hoàn toàn có thể khởi động với khoá TOTP **dẫn xuất từ `ADMIN_API_KEY`**.
- Khi đó **xoay `ADMIN_API_KEY` = mất vĩnh viễn toàn bộ bí mật TOTP đã lưu** → mọi user bật 2FA bị khoá
  ngoài tài khoản, không có đường tự phục hồi ngoài mã khôi phục.
- Đính chính bản rà đầu: `.env.example:163-164` **có** cảnh báo đầy đủ ngay trên dòng
  `# TOTP_ENC_KEY=` — "Bật 2FA khi CHƯA đặt khoá này = khoá vĩnh viễn người dùng đã bật 2FA".

**Hạ mức từ Cao xuống Trung bình.** Kịch bản mất khoá hiện **chưa thể xảy ra**:
`agent/config.py:82` đặt `TWO_FACTOR_ENABLED: bool = False` và nó được cưỡng chế ở
`agent/auth.py:1774`, `:1788`, `:1825` — không user nào enroll được 2FA, nên không có bí mật
TOTP nào để mất. Rủi ro chỉ hiện thực hoá **đúng lúc bật cờ đó trên prod**, và đó chính là
lúc phải đặt `TOTP_ENC_KEY` trước.

Việc cần làm vẫn giữ nguyên nhưng đúng thời điểm: đưa `TOTP_ENC_KEY` vào
`validate_production_keys` (`config.py:151-168`) **trước khi** bật `TWO_FACTOR_ENABLED`,
để prod không thể khởi động với khoá dẫn xuất từ `ADMIN_API_KEY`.

**Phần THIẾU (Thấp):** `agent/auth.py:446-447` — OTP 6 chữ số hash bằng SHA-256 trần, không salt,
không KDF. Không gian chỉ 10^6 → lộ bảng `otp_sessions` là dò ngược tức thì. Giảm nhẹ: TTL 5 phút
(`agent/config.py:120`) và bị xoá sau khi dùng, nên tác động thực tế thấp.

### A03 — Injection → **ĐẠT**

Quét AST toàn bộ `agent/` + `scripts/` (bỏ test): **650 f-string chứa từ khoá SQL**, trong đó **161 chỗ**
nội suy một biểu thức không phải placeholder. Đọc tay theo nhóm biểu thức, kết quả:

- **Không tìm thấy chỗ nào nối trực tiếp giá trị người dùng vào chuỗi SQL.**
- Thứ nội suy vào SQL luôn thuộc một trong bốn loại, tất cả đều do code kiểm soát:
  1. Placeholder: `{db._ph}` / `{ph}` / `",".join(ph for _ in ids)` — ví dụ `agent/admin.py:4483`.
  2. Mảnh `WHERE` ghép từ **các chuỗi hằng** trong code, còn tham số đi qua placeholder — ví dụ
     `agent/database.py:1093`, `agent/admin.py:3988-3997`.
  3. **Tên bảng/cột từ danh sách hằng**: `agent/admin.py:2392` (`tables = [...]` ở dòng 2386),
     `agent/admin.py:5511` (`tables = ["saved_entities", "user_visits", "event_rsvp"]` ở dòng 5508),
     `agent/notifications.py:414` (`pref_col` lấy từ dict `_NOTIF_TYPE_TO_PREF`),
     `agent/social.py:89` và `agent/social.py:102` (`column` là tham số mặc định `"u.id"` / `"p.user_id"`).
  4. `ORDER BY` chọn qua `if/elif` với chuỗi cứng, **không** nội suy giá trị `sort` của client:
     `agent/database.py:1136-1148` (client gửi `sort` bất kỳ thì rơi vào nhánh `else` mặc định).
- LIKE có escape wildcard riêng + `ESCAPE '\'`: `agent/database.py:138-140` (`escape_like`),
  dùng ở `agent/database.py:341-351` và `agent/admin.py:3973`. Nghĩa là `%`/`_` của người dùng
  không biến thành wildcard (không phải injection, nhưng là DoS/lệch kết quả — đã chặn).
- Không có `eval` / `exec` / `pickle.loads` / `yaml.load` trên dữ liệu ngoài (quét toàn `agent/`,
  các match đều là tên hàm nội bộ như `_exec`, `run_eval`).

Ghi chú phạm vi: các chỗ nội suy tên bảng/cột trong `scripts/` (`scripts/sp2_reconcile.py:47,122,127`,
`scripts/migrate_entity_status.py:1649,1662`) nhận giá trị từ tham số CLI của người vận hành, không
từ HTTP. Không phải bề mặt tấn công web.

### A04 — Insecure Design → **THIẾU**

**Rate-limit đang có (ĐẠT):**

- Tầng ứng dụng: `agent/ratelimit.py` — cửa sổ trượt in-memory, **kèm lớp chia sẻ qua Postgres**
  (`agent/ratelimit.py:66-80`, bảng `shared_rate_limits`, dùng `pg_advisory_xact_lock`) nên nhiều
  worker không cộng dồn sai. Đếm số điểm gọi: `agent/social.py` 35 chỗ, `agent/auth.py` 19,
  `agent/plans.py` 4, `agent/saved.py` 3, `agent/visits.py` 2.
- Chat/stream/report/feedback có limiter riêng: `agent/server.py:2516`, `agent/server.py:3099`,
  `agent/public_api.py:2793`, `agent/server.py:4590`.
- Admin: `agent/admin.py:462` — mọi route `/admin/*` đi qua `admin_limiter` (đó là lý do 57 route admin
  bị máy quét đánh dấu "không thấy marker rate-limit" nhưng thực tế đã bị chặn ở cấp router).
- Tầng biên: `nginx-ssl.conf:8-9` — zone `api` 30r/m, zone `chat` 10r/m theo `$binary_remote_addr`.

**THIẾU 1 (Trung bình) — `TRUSTED_PROXIES` không được cấu hình ở đâu cả:**

`agent/middleware.py:521` mặc định `TRUSTED_PROXIES = "127.0.0.1,::1"`, và `get_client_ip`
(`agent/middleware.py:523-538`) chỉ tin `X-Forwarded-For` khi IP kết nối trực tiếp nằm trong danh sách đó.
Thiết kế này đúng. Vấn đề là:

- `.env.example` **không có** dòng `TRUSTED_PROXIES` nào (đã grep toàn file).
- `docker-compose.prod.yml` **không set** biến này, mà nginx chạy trong container riêng
  (`docker-compose.prod.yml:80-83`) → IP nguồn tới agent sẽ là IP bridge (172.x), **không** khớp
  `127.0.0.1` → `X-Forwarded-For` bị bỏ → **mọi request trả về cùng một IP**.

Hệ quả nếu chạy nhánh docker: toàn bộ rate-limit theo IP (đăng nhập, OTP, báo cáo, chat, feedback) gộp
chung một rổ — một người dùng bình thường có thể tự đẩy cả site vào 429, và kẻ tấn công thì được
"che" trong đám đông. Log bảo mật theo IP (`agent/middleware.py:494-501`) cũng thành vô nghĩa.
*Chưa kiểm được* prod thật đang chạy nhánh nào (systemd trên host hay docker-compose) — cần người xác nhận.

**THIẾU 2 (Thấp–Trung bình) — endpoint tính toán công khai không có rate-limit tầng app:**

`POST /api/itineraries/optimize-order` (`agent/public_api.py:2001-2008`) là POST công khai duy nhất
không auth **và** không rate-limit trong code. Nó nhận 2–20 điểm dừng (`agent/public_api.py:1827`) và
chạy quy hoạch động Held-Karp khi phần giữa ≤ 10 điểm (`agent/itinerary_optimizer.py:579`,
`exact_limit=10` ở `agent/itinerary_optimizer.py:42`), nghĩa là tối đa ~2^10 × 10 × 10 phép cạnh mỗi
request; trên 10 thì rơi về beam-search width 64 nên có trần. Chạy trong `asyncio.to_thread`
(`agent/public_api.py:1968`) → flood sẽ bào threadpool, mà threadpool cũng chính là nơi mọi truy vấn DB
chạy. Giảm nhẹ duy nhất hiện có là nginx 30r/m (`nginx-ssl.conf:143`).

**THIẾU 3 (Trung bình) — "bảo mật giấy": 34/52 hàm bảo mật không được nối dây.**

Quét toàn bộ hàm public của `agent/auth_middleware.py` rồi tìm lời gọi trong code sản xuất
(bỏ `agent/tests/`, `tests/`): **12** hàm được dùng thật, **6** chỉ được gọi nội bộ trong chính module,
**34** không được gọi ở đâu ngoài test. Danh sách 34 (kèm dòng khai báo):

`add_ip_rule:1545`, `build_rate_limit_headers:1155`, `check_password_strength:716`,
`check_path_traversal:647`, `check_permission_boundary:1658`, `check_privilege_escalation:1713`,
`check_session_count:401`, `check_sqli_patterns:315`, `clear_login_failures:1075`, `detect_bot_ua:471`,
`detect_pii:773`, `generate_nonce:1605`, `is_account_locked:1064`, `is_safe_content:285`, `mask_pii:790`,
`record_login_failure:1017`, `remove_ip_rule:1556`, `sanitize_error_message:816`, `sanitize_filename:938`,
`sanitize_html:263`, `sanitize_log_param:241`, `validate_api_key_format:1500`, `validate_content_type:1100`,
`validate_cors_origin:1191`, `validate_file_upload:898`, `validate_int_param:227`, `validate_redirect_url:593`,
`validate_referrer:1462`, `validate_token_structure:1256`, `validate_url_safe:541`, `validate_uuid_param:217`,
`verify_nonce:1610`, `verify_request_signature:972`, `verify_webhook_signature:1680`.

Ba cái đáng nói nhất:

- **Khoá tài khoản (`record_login_failure` / `is_account_locked` / `clear_login_failures`,
  `agent/auth_middleware.py:1017-1079`) hoàn toàn không được gọi.** `agent/tests/test_security_advanced.py:38-82`
  test rất kỹ 3 hàm này. Chống brute-force thực tế **không** đến từ đây mà từ throttle theo IP + theo
  số điện thoại trong `agent/auth.py:878-911` (xem A07). Nghĩa là các biến `LOCKOUT_THRESHOLD` /
  `LOCKOUT_DURATION` / `LOCKOUT_WINDOW` được ghi trong `.env.example:114-116` **không có tác dụng gì**.
- `validate_file_upload` (`agent/auth_middleware.py:898`) không được gọi — nhưng may là các endpoint upload
  dùng đường khác và tốt hơn (xem A08).
- `check_privilege_escalation` / `check_permission_boundary` không được gọi — phân quyền thực tế
  đến từ `_ensure_admin_scope` (`agent/admin.py:246`) và `_assert_actor_can_manage_target`
  (`agent/admin.py:168`).

Đây chính xác là mô hình bài học số 2: một khối test xanh đang bảo chứng cho code **không chạy trong sản xuất**.
Nó không tạo lỗ hổng mới, nhưng nó tạo **niềm tin sai** — người đọc scorecard sẽ tưởng đã có khoá tài khoản.

### A05 — Security Misconfiguration → **THIẾU**

**Phần ĐẠT:**

- CORS whitelist, không dùng `*`, có `allow_credentials=True` nhưng danh sách origin là hằng
  (`agent/server.py:1092-1108`); production tự loại origin localhost (`agent/server.py:1095-1099`).
- Tài liệu API tắt ở production: `agent/server.py:1079-1081` (`docs_url`/`redoc_url`/`openapi_url` = None).
- Header bảo mật gắn ở middleware cho mọi response: `agent/server.py:1156-1170` →
  `agent/auth_middleware.py:413-426` (`X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`,
  `Permissions-Policy`, `X-Permitted-Cross-Domain-Policies`, COOP, CORP; production thêm HSTS preload).
- CSP của backend có **nonce**, không có `unsafe-inline` cho script: `agent/auth_middleware.py:433-443`.
- Lỗi không rò rỉ nội bộ: `agent/server.py:1188-1200` trả "Lỗi hệ thống." / 503 cho lỗi DB, traceback
  chỉ vào log.
- `replace_from_json` bị khoá mặc định: `agent/database.py:1624` (`DESTRUCTIVE_OPS_LOCKED=1`).

**THIẾU 1 (Trung bình) — CSP ở tầng phục vụ người dùng gần như vô hiệu:**

`nginx.conf:33` và `nginx-ssl.conf:70` đặt:
`script-src 'self' 'unsafe-inline'` và `connect-src 'self' http: https: ws: wss:`.
Với `'unsafe-inline'`, CSP không còn chặn XSS phản chiếu/lưu trữ; với `connect-src http: https:`,
nó cũng không chặn rút dữ liệu ra ngoài. CSP có nonce (bản tốt) chỉ áp cho response **từ agent**,
mà agent chủ yếu trả JSON — HTML người dùng thấy là do Nuxt phục vụ.

**THIẾU 2 (Trung bình) — Nuxt không đặt CSP:**

`web-nuxt/nuxt.config.ts:217-226` đặt `X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN`,
`Referrer-Policy`, `Permissions-Policy`, `Strict-Transport-Security` — **không có** `Content-Security-Policy`.
Nghĩa là trang HTML chính không tự bảo vệ; nó phụ thuộc hoàn toàn vào CSP yếu của nginx ở trên.

**THIẾU 3 (Thấp) — nginx đẩy thẳng bề mặt nội bộ ra Internet:**

`nginx-ssl.conf:180` proxy các prefix `health|analytics|feedback|welcome|reload|system|seo|weather|recommend|freshness`
lên agent. `/system` và `/reload` là bề mặt quản trị; hiện chúng an toàn nhờ lớp app
(`agent/server.py:1322-1329` + `agent/server.py:3926-3939`), nhưng chặn ngay ở biên sẽ rẻ hơn và
bớt phụ thuộc vào việc lớp app không bao giờ hồi quy.

**Ghi chú (không phải lỗi):** `X-XSS-Protection: 1; mode=block` (`nginx-ssl.conf:68`) đã lỗi thời và
bị mọi trình duyệt hiện đại bỏ qua; giữ lại không hại nhưng cũng không bảo vệ gì.

*Chưa kiểm được*: cấu hình nginx **đang chạy thật** trên VPS. Hai file trong repo có thể đã lệch với
`/etc/nginx` trên máy prod — cần đọc trực tiếp trên VPS mới kết luận được.

### A06 — Vulnerable and Outdated Components → **THIẾU**

Phiên bản đang cài trong môi trường này (đọc bằng `importlib.metadata`, không phải đoán từ requirements):

```
fastapi 0.136.3    starlette 1.3.1    uvicorn 0.49.0     httpx 0.28.1
httpcore 1.0.9     requests 2.34.2    pydantic 2.13.4    cryptography 48.0.0
Pillow 12.2.0      psycopg2-binary 2.9.12                pyotp 2.10.0
redis 8.0.1        boto3 1.43.46      python-multipart 0.0.32
openai 2.41.0      qrcode 8.2         ddgs 9.14.4        mcp 1.27.2
```

Không có gói nào ở phiên bản cổ đáng báo động. Ba vấn đề về **quy trình**, không phải về một gói cụ thể:

1. **(Trung bình) Pin trần `fastapi>=0.115,<0.137`** (`requirements.txt:4`, lý do ghi rõ ở dòng 1-3:
   regression làm `include_router` chỉ copy 1/N route). Trần này là **đúng** về mặt kỹ thuật — nhưng nó
   cũng có nghĩa dự án **không thể nhận bản vá bảo mật nào của dòng ≥0.137** cho tới khi gỡ trần.
   Đây là món nợ có hạn dùng, cần đặt lịch kiểm lại, không phải để mãi.
2. **(Trung bình) Không có lockfile / hash pinning cho Python.** Toàn bộ `requirements.txt` dùng `>=`
   không trần (trừ fastapi, httpx, httpcore). Không có `requirements.lock`, không có `constraints.txt`,
   không có `--require-hashes`. Một bản phát hành bị chiếm dụng của bất kỳ gói nào ở trên sẽ tự vào
   máy build ở lần cài kế tiếp. (Frontend thì ổn: `web-nuxt/package-lock.json` có tồn tại.)
3. **(Thấp) Quét CVE đã có, phần thiếu là quét mã tĩnh và cập nhật tự động.**
   Đính chính bản rà đầu: `.github/workflows/ci.yml:395` **có** job `deps-audit` chạy
   `pip-audit -r requirements.txt` (`ci.yml:408-411`) và `npm audit`. Vậy CVE của
   phụ thuộc **có** được báo.
   Phần còn thiếu là: không có quét mã tĩnh (`bandit`, CodeQL, Trivy) và không có
   `dependabot.yml` để tự mở PR nâng phiên bản — nên CVE được *báo* nhưng việc vá
   vẫn hoàn toàn thủ công.

### A07 — Identification and Authentication Failures → **ĐẠT**

**Chống brute-force (ĐẠT)** — nằm ở `agent/auth.py`, không phải ở `auth_middleware` (xem A04):

- Theo IP: `agent/auth.py:878-879` — hai lớp, một in-memory (`_enforce_local_rate`) và một chia sẻ qua
  Postgres (`_check_shared_auth_rate` → `agent/ratelimit.py`).
- Theo số điện thoại: `agent/auth.py:883-886` — vượt `LOGIN_PHONE_LIMIT` trong `LOGIN_PHONE_WINDOW`
  thì trả 429 "tạm khoá 15 phút", đếm cả trước và sau khi kiểm mật khẩu (`agent/auth.py:892-895`,
  `agent/auth.py:907-910`). Đếm được reset khi đăng nhập thành công (`agent/auth.py:934`).
- OTP: giới hạn theo số điện thoại và theo IP (`agent/auth.py:532-548`).

**Chống liệt kê tài khoản (phần lớn ĐẠT):** kiểm `is_active` được đặt **sau** khi verify mật khẩu
(`agent/auth.py:915-918`, có comment giải thích đúng lý do), và luôn chạy PBKDF2 giả khi user không tồn tại.

**THIẾU (Thấp–Trung bình) — nhưng có một oracle liệt kê cố ý:** `POST /auth/check-phone`
(`agent/auth.py:865-867`) trả thẳng `{"exists": true|false}`. Có rate-limit theo IP
(`agent/auth.py:855-863`) nhưng vẫn là một API cho biết số điện thoại nào đã đăng ký. Với site du lịch
địa phương thì đây là rủi ro riêng tư ở mức thấp, không phải lỗ hổng chiếm tài khoản — nhưng nên
biết là mình đang cố ý mở nó.

**Session (ĐẠT):**

- Không có session fixation: token sinh mới hoàn toàn tại thời điểm đăng nhập (`agent/auth.py:450-451`),
  không tái dùng giá trị client gửi lên.
- Đăng xuất **xoá hàng ở server**, không chỉ xoá cookie: `agent/auth.py:1073-1077`.
- Xoay token: `POST /auth/refresh` (`agent/auth.py:1084`) cấp token mới và thu hồi token cũ
  (`agent/auth.py:1094-1104`).
- Đổi mật khẩu **thu hồi mọi phiên khác** nhưng giữ phiên hiện tại: `agent/auth.py:983-993`.
- Tra phiên luôn kiểm hạn + `is_active` + `deleted_at` trong **cùng một câu truy vấn**:
  `agent/auth.py:2122-2128` — không thể dùng token cũ sau khi bị vô hiệu hoá.
- Có ràng buộc phiên theo dấu vân tay UA + dải IP (`agent/auth_middleware.py:333-390`), áp ở đúng ba
  thao tác nhạy cảm: đặt mật khẩu (`agent/auth.py:970`), vô hiệu hoá (`agent/auth.py:1213`),
  xoá tài khoản (`agent/auth.py:1235`). Không áp toàn cục — hợp lý, tránh đá người dùng di động ra ngoài.
- 2FA TOTP + thiết bị tin cậy (`agent/auth.py:640-690`), mã khôi phục hash một chiều.

**Chính sách mật khẩu (ĐẠT, tối thiểu):** `agent/auth.py:374-382` — tối thiểu 8 ký tự, ít nhất 1 chữ số
và 1 chữ cái, trần 128 ký tự. Không kiểm danh sách mật khẩu đã rò rỉ, không tính entropy.
(Hàm `check_password_strength` ở `agent/auth_middleware.py:716` làm cả hai việc đó nhưng **không được gọi** —
lại là A04.)

**CSRF (ĐẠT):** `agent/auth_middleware.py:132-167` — HMAC-SHA256 gắn với session token, so bằng
`hmac.compare_digest`, bỏ qua method an toàn, bỏ qua request không đăng nhập (đúng — không có ambient
auth thì không có CSRF). Token lấy qua `GET /auth/csrf` (`agent/auth.py:1188-1200`) mà endpoint đó
yêu cầu cookie phiên; kẻ tấn công khác origin không đọc được response nhờ whitelist CORS.
Thất bại CSRF được ghi log bảo mật (`agent/auth_middleware.py:158-167`).

### A08 — Software and Data Integrity Failures → **ĐẠT (upload) / THIẾU (chuỗi cung ứng)**

**Upload — kiểm loại thật, không kiểm đuôi (ĐẠT rõ ràng):**

Cả 4 endpoint upload đều **không** tin `Content-Type` client gửi, mà đọc magic byte:

- `agent/storage.py:92-108` — `sniff_image_type` khớp magic byte cho JPEG/PNG/GIF/WebP(+RIFF…WEBP)/AVIF,
  trả `None` cho mọi thứ khác (SVG, HTML, polyglot).
- `POST /api/upload/image` — `agent/social.py:3534-3537`.
- `POST /auth/avatar` — `agent/auth.py:1395-1396`; `POST /auth/cover` — `agent/auth.py:1432-1433`.
- `POST /admin/entities/{id}/images/upload` — `agent/admin.py:1123-1124`.

Ngoài ra:

- **Re-encode toàn bộ sang WebP** thay vì lưu file gốc (`agent/storage.py:115-117`) → phá polyglot,
  xoá EXIF (gồm toạ độ GPS của người đăng).
- **Trần điểm ảnh chống decompression bomb**: `agent/storage.py:111-112`, `MAX_IMAGE_PIXELS = 40_000_000`.
- **Tên file do server sinh**, không dùng tên client: `agent/storage.py:192` (`uuid4().hex[:12] + ".webp"`),
  `agent/storage.py:172`. Không có đường path-traversal qua filename.
- Chặn traversal ở tham số folder (`agent/storage.py:185-186`) và ở đường xoá
  (`agent/storage.py:204-206`, kiểm `is_relative_to`).
- Trần dung lượng đọc theo stream `read(MAX+1)` chứ không đọc hết rồi mới kiểm (`agent/auth.py:1392`,
  `agent/social.py:3529`) — không cho phép làm cạn RAM bằng file khổng lồ.
- Trên hết: chính sách ảnh AI-only đang **chặn cứng** upload ảnh UGC — `agent/social.py:73-74`
  `_reject_non_ai_media()` luôn ném 400, gọi ngay dòng đầu của `upload_image` (`agent/social.py:3525`).

**THIẾU (Trung bình) — chuỗi cung ứng:** xem A06 mục 2 và 3 (không lockfile, không hash, không quét CVE).
Deserialize không an toàn: **không có** (không dùng pickle/marshal/yaml.load trên dữ liệu ngoài).

### A09 — Security Logging and Monitoring Failures → **THIẾU**

**Phần ĐẠT:**

- `redact_log_value` (`agent/middleware.py:42-43` → `agent/privacy_boundary.py:143-164`) đệ quy qua
  str/dict/list/tuple, và **fail-closed**: kiểu không nhận diện được thì trả `[REDACTION_FAILED]`
  chứ không ghi nguyên trạng (`agent/privacy_boundary.py:163-164`, `agent/middleware.py:46-50`).
- Bộ nhận diện phủ 6 loại (`agent/guardrails.py:185-192`): `secret` (khớp `api_key|secret|access_token|auth_token|password` theo sau `:`/`=`, và `sk-…`), `email`, `passport`, `id_number` (CCCD/CMND có từ khoá đứng trước), `bank_account` (có từ khoá đứng trước), `phone` (định dạng VN). Có thêm bộ "overflow" bắt giá trị dài tràn ngoài mẫu chính (`agent/guardrails.py:333-358`).
- Audit admin có bảng riêng, ghi mọi mutation kèm actor/scope/request-id: `agent/admin.py:282-295`,
  gọi ở `agent/admin.py:470-475`.
- Lịch sử đăng nhập (thành/bại) ghi vào `login_history`, dọn sau 90 ngày (`agent/auth.py:196-199`).
- `SecurityLogger` ghi sự kiện chuyên biệt: sai admin key (`agent/middleware.py:618`), CSRF fail
  (`agent/middleware.py:624`), bất thường phiên (`agent/middleware.py:621`).
- Số điện thoại được che tay trước khi log ở đường SMS/OTP: `agent/auth.py:219-222`, dùng ở
  `agent/auth.py:511`, `agent/auth.py:571`, `agent/auth.py:1499`.

**Cơ chế thực tế (quan trọng — đừng đọc nhầm như tôi đã đọc nhầm lần đầu):**
Việc redact nằm trong `StructuredLogger.log()` (`agent/middleware.py:77-92`), và các module lớn
(`agent/admin.py:39`, `agent/social.py:38`, `agent/auth.py:30`, `agent/database.py:29`) dùng `logging`
chuẩn chứ không dùng instance đó. **Nhưng** `agent/middleware.py:204-221` có `_StructuredLogBridge`
— một `logging.Handler` gắn vào **root logger** (`agent/middleware.py:241-242`) — nên record của mọi
logger stdlib vẫn chảy qua `StructuredLogger.log()` và **được che**.

Đã kiểm bằng hành vi, không bằng đọc code (bắt chính stream của handler):

```
admin        -> da che        social       -> da che
auth         -> da che        database     -> da che
scheduler    -> RO RI: email,phone,api_key
learn_loop   -> RO RI: email,phone,api_key
bot_gateway  -> RO RI: email,phone,api_key
```

> Đính chính bản rà đầu: dòng `bot_gateway` ban đầu ghi rò rỉ **chỉ** email. Chạy lại
> đúng probe đó (import middleware rồi bắt stream của handler riêng từng logger) cho
> thấy nó rò cả **email, phone và api_key**, y hệt `scheduler` và `learn_loop`. Mức độ
> nặng hơn bản rà đầu mô tả — và `bot_gateway` chính là module xử lý tin nhắn
> Telegram/Zalo của người thật.

**THIẾU (Trung bình) — ba module tự gắn `StreamHandler` riêng nên bản THÔ lọt ra console/journald:**

- `agent/scheduler.py:41-46`
- `agent/learn_loop.py:56-61`
- `agent/bot_gateway.py:54-58`

Cả ba đều làm cùng một việc: `logging.getLogger(<tên>)` rồi `addHandler(StreamHandler())`, mà
`propagate` vẫn để `True`. Kết quả đo được: **một dòng thô** đi ra stderr qua handler riêng, **và**
một dòng đã che đi ra qua bridge. Trên VPS chạy systemd, dòng thô đó nằm trong journald — đúng chỗ
người vận hành hay `grep`.

Console thật quan sát được trong probe (`scheduler`):

```
[ERROR] lien he test@example.com hoac 0912345678, api_key=SK12345678ABCDEF   ← handler riêng, THÔ
[ERROR] lien he [EMAIL] hoac [PHONE], ...                                     ← qua bridge, đã che
```

Ba module này đều là nơi dễ log nội dung ngoài: `scheduler` chạy tác vụ nền chạm dữ liệu người dùng,
`bot_gateway` xử lý tin nhắn Telegram/Zalo của người thật.

**THIẾU (Thấp) — hai điểm mù của bridge:**

- `_StructuredLogBridge.__init__` đặt `level=logging.INFO` (`agent/middleware.py:210`) → record mức
  `DEBUG` không bao giờ đi qua đường che. Hiện vô hại vì level hiệu lực của root là WARNING, nhưng
  ai bật `LOG_LEVEL=DEBUG` sẽ vô tình mở đường.
- `uvicorn.access` có handler riêng của uvicorn và không propagate về root → dòng access log
  (gồm query string) **không** đi qua redact. Filter duy nhất gắn vào nó là `_SSEAccessLogFilter`
  (`agent/middleware.py:224-234`, `agent/middleware.py:243`), chỉ để bớt ồn SSE, không liên quan PII.
  Hiện chấp nhận được vì thiết kế không đặt PII trên query string, nhưng đó là một giả định chưa có cổng nào canh.

**THIẾU (Thấp) — phạm vi nhận diện:** `redact_log_value` không nhận diện session token trần
(chuỗi `token_urlsafe(48)` không có từ khoá đứng trước), giá trị `X-Admin-Key`, hay chuỗi cookie thô.
Mẫu `secret` chỉ khớp khi có `api_key|secret|token|password` + `:`/`=` ngay trước
(`agent/guardrails.py:283-287`).

### A10 — Server-Side Request Forgery → **ĐẠT**

Dự án có một biên egress viết riêng và khá nghiêm túc: `agent/pinned_http.py`.

- Ghim DNS: phân giải trước, chỉ quay số tới địa chỉ đã duyệt, rồi **kiểm lại peer đã kết nối**
  (`agent/pinned_http.py:677+` `_PinnedNetworkStream`, `agent/pinned_http.py:664-674` `validate_public_url`).
- **Mỗi hop redirect được phân giải lại và kiểm lại** theo cùng chính sách (mô tả ở docstring
  `agent/pinned_http.py:1-27`, vòng lặp redirect thủ công) — chặn được đòn "redirect sang 169.254.169.254".
- Từ chối các dạng chuyển tiếp IPv6 và dải dành riêng mà `ipaddress.is_global` vẫn báo là global.
- Trần dung lượng, trần thời gian, trần số redirect qua `EgressPolicy` (ví dụ cấu hình cho ảnh admin:
  `agent/admin.py:57-66`).
- Danh sách consumer được **khoá bằng test**: `tests/test_pinned_http_consumers.py` (đã chạy, pass).
  Consumer: `admin._approve_fetch_image_data` (`agent/admin.py:2227-2237`), `auto_learn.fetch_url`,
  `crawler.fetch_page` (`agent/crawler.py:160-169`), `geocode._query_nominatim`,
  `gpt55_quality_burst.fetch_url_text`, `realtime.get_weather`.
- `tests/test_crawler_ssrf.py` cũng pass.

**Nợ egress còn lại (Thấp, đã được khai báo công khai ở `agent/pinned_http.py:22-26`):**
`agent/bot_gateway.py:344,534,823,878`, `agent/moderation.py:229,290`, `agent/scheduler.py:565,612`,
`agent/auth.py:502` vẫn gọi `httpx` trực tiếp. Đã đọc từng chỗ: **tất cả đều tới host cố định**
(`api.telegram.org`, `openapi.zalo.me`, `vision.googleapis.com`, `rest.esms.vn`, `OPENAI_BASE_URL`,
`self.agent_url` từ env) — **không có URL nào do người dùng cuối điều khiển**, nên không phải SSRF.
Điểm cần để mắt: `agent/moderation.py:290` gửi `image_urls` của người dùng cho Google Vision dưới dạng
`imageUri` — Google là bên đi lấy, không phải mạng nội bộ của mình, nên không phải SSRF; nhưng đó là
một kênh rò rỉ URL ra bên thứ ba.

---

## 3. Việc cần làm, xếp theo mức nghiêm trọng

**Cao**

1. **Bắt buộc `TOTP_ENC_KEY` ở production.** Thêm nó vào `validate_production_keys`
   (`agent/config.py:151`) đúng như `ADMIN_API_KEY`, và bỏ nhánh fallback dẫn xuất từ `ADMIN_API_KEY`
   ở `agent/twofactor.py:44-50` khi `is_production`. Kèm một test **hành vi**: dựng settings production
   thiếu `TOTP_ENC_KEY` → phải ném; đừng viết test assert chuỗi trong source.
   Lưu ý thứ tự thi hành: đặt khoá **trước**, không được xoay `ADMIN_API_KEY` giữa chừng, nếu không
   mọi bí mật TOTP hiện có thành rác. Đây là việc chạm secret thật → **phải hỏi chủ dự án** (CLAUDE.md §4).

**Trung bình**

2. **Bịt ba đường log thô ra console.** Ở `agent/scheduler.py:41-46`, `agent/learn_loop.py:56-61`,
   `agent/bot_gateway.py:54-58`: hoặc bỏ hẳn `StreamHandler` riêng (để bridge lo, y như `admin`/`social`/
   `auth`/`database` đang làm và đã đo là sạch), hoặc gắn thêm một `logging.Filter` gọi
   `privacy_boundary.redact_log_value` vào chính handler đó. Kiểm chứng phải là **test hành vi**:
   bắt stream của handler, log một chuỗi có email, assert thấy `[EMAIL]` và **không** thấy chuỗi gốc.
   Đừng viết test `getsource` — nó sẽ xanh kể cả khi handler vẫn in thô.

3. **Cấu hình `TRUSTED_PROXIES` cho đúng cách deploy thật.** Tối thiểu: thêm dòng có giải thích vào
   `.env.example`, và set biến trong `docker-compose.prod.yml` cho service agent. Trước đó cần
   **hỏi chủ dự án** prod đang chạy systemd-trên-host hay docker-compose — hai đáp án cho hai giá trị
   khác nhau, đoán sai thì hoặc mất rate-limit hoặc mở đường giả mạo XFF.
4. **Dọn 34 hàm bảo mật không được nối dây trong `agent/auth_middleware.py`.** Mỗi hàm chọn một
   trong hai: (a) nối vào đường thật rồi viết test hành vi qua HTTP, hoặc (b) xoá cùng test của nó.
   Ưu tiên quyết định trước cho nhóm khoá tài khoản (`agent/auth_middleware.py:1017-1079`) — vì
   `.env.example:114-116` đang quảng cáo ba biến `LOCKOUT_*` không có tác dụng; hoặc nối dây, hoặc
   xoá ba dòng đó khỏi `.env.example`.
5. **Thêm quét lỗ hổng phụ thuộc vào CI.** `pip-audit` + `npm audit --omit=dev` là hai bước, không
   tốn phí, hợp §B8. Kèm `dependabot.yml` hoặc lịch chạy hằng tuần.
6. **Sinh lockfile Python** (`pip-compile` → `requirements.lock` với hash) và dùng nó ở CI + deploy.
7. **Siết CSP.** Bỏ `'unsafe-inline'` khỏi `script-src` ở `nginx.conf:33` / `nginx-ssl.conf:70`
   (Nuxt build ra script có file riêng, không cần inline; nếu còn inline thì chuyển sang nonce/hash),
   và thu hẹp `connect-src` về đúng origin cần. Đồng thời thêm `Content-Security-Policy` vào
   `web-nuxt/nuxt.config.ts:217-226`.
8. **Đặt lịch kiểm lại trần `fastapi<0.137`** (`requirements.txt:4`) — kiểm xem upstream đã vá
   regression `include_router` chưa; đừng để trần này thành vĩnh viễn.

**Thấp**

9. Thêm rate-limit tầng app cho `POST /api/itineraries/optimize-order` (`agent/public_api.py:2001`) —
   một dòng `check_rate(f"optimize:{ip}", …)` là đủ, đừng để chỉ dựa vào nginx.
10. Thu hẹp allowlist của `db.update_user` (`agent/database.py:1815`): tách `role` / `is_active` /
    `deleted_at` / `password_hash` sang hàm riêng chỉ admin gọi, để một `**body` bất cẩn trong tương lai
    không thành leo quyền.
11. Chặn `/system` và `/reload` ngay ở nginx (`nginx-ssl.conf:180`) thay vì để tới tầng app mới 404.
12. Cân nhắc lại `POST /auth/check-phone` (`agent/auth.py:865`): hoặc chấp nhận có ý thức, hoặc đổi
    thành luồng "gửi OTP rồi mới biết" để bỏ oracle liệt kê.
13. Thay `_hash_otp` SHA-256 trần (`agent/auth.py:446`) bằng HMAC có khoá — rẻ, và loại bỏ khả năng
    dò ngược tức thì nếu bảng `otp_sessions` bị lộ.

---

## 4. Những gì chưa kiểm được

- **Cấu hình nginx đang chạy thật trên VPS.** Kết luận A05 dựa trên `nginx.conf` / `nginx-ssl.conf`
  trong repo. Hai file này có thể đã lệch với `/etc/nginx` trên máy prod.
- **Đường deploy prod là systemd hay docker-compose.** Kết luận về `TRUSTED_PROXIES` (A04) đổi hoàn
  toàn theo đáp án. Cần chủ dự án xác nhận.
- **Giá trị biến môi trường thật ở prod** (`TOTP_ENC_KEY`, `CSRF_SECRET`, `CORS_ORIGINS`,
  `MAX_SESSIONS_PER_USER`). Chỉ đọc được `.env.example`, không đọc `.env` prod — và không nên đọc.
- **Hành vi các endpoint UGC/auth dưới Postgres thật.** Probe chạy trên SQLite nên phần lớn route
  UGC trả 503 ở cổng `require_pg`. Phân quyền cấp đối tượng (A01) vì thế được xác nhận **bằng đọc code**
  (`agent/social.py:844`, `agent/social.py:906-913`), không phải bằng request thật với hai user khác nhau.
  Muốn chắc thì cần một vòng probe nữa với `docker compose up postgres` và hai phiên user thật.
- **Cấu hình logging của uvicorn ở prod.** Probe che-log chạy trong tiến trình Python trần. Các
  handler ở `agent/scheduler.py:41-46`, `agent/learn_loop.py:56-61`, `agent/bot_gateway.py:54-58` được
  gắn ở cấp module nên hành vi giống nhau, nhưng nếu prod khởi động uvicorn với `--log-config` riêng
  thì cấu hình root có thể khác. Cần xem lệnh khởi động thật trong unit systemd.
- **Kiểm thâm nhập động** (fuzz, quét tự động, thử vượt CSRF/CORS thực tế). Bản rà này là rà code +
  probe có mục tiêu, không phải pentest.
