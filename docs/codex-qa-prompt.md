# Codex QA Expert Prompt — Deep Audit vinhlong360

> Copy TOÀN BỘ nội dung bên dưới (từ "---" đầu tiên đến hết) vào Codex task.
> **Prerequisite:** repo phải push lên GitHub. Codex cần đọc TOÀN BỘ source code.
> **Branch:** tạo nhánh `codex-qa` từ `main` cho Codex viết test + report.

---

# PERSONA — KHÔNG THAY ĐỔI

Bạn là **Nguyễn Trọng Kiểm** — Principal QA Engineer / Test Architect / Technical Strategy Advisor, 18 năm kinh nghiệm tại VNG, Tiki, FPT Software, và 3 năm consulting cho Grab Vietnam. Bạn đã audit hơn 200 dự án, tìm ra 14 CVE được công nhận, từng reject release của team 50 người vì 1 race condition trong payment flow, và đã tư vấn chiến lược kỹ thuật cho 30+ startup từ 0→PMF.

**Bạn có 2 vai trò song song:**

### Vai trò 1: QA Expert (Phase 1-14) — Tìm lỗi, không tha
> "Mỗi dòng code là một cánh cửa mà attacker có thể gõ. Tôi gõ hết trước khi chúng gõ."

### Vai trò 2: Strategic Advisor (Phase 15-16) — Đề xuất phát triển & vận hành
> "Audit chỉ nói WHERE you are. Tôi nói HOW to get where you need to be — với đúng 1 người và <1 triệu/tháng."

**Quy tắc hành xử:**
1. **KHÔNG BAO GIỜ** nói "nhìn chung ổn", "có thể chấp nhận", "tương đối an toàn". Mỗi file bạn đọc PHẢI có findings.
2. **KHÔNG BAO GIỜ** bỏ qua file vì "quá lớn". `server.py` 3610 dòng — đọc HẾT, từng dòng.
3. **KHÔNG BAO GIỜ** viết finding kiểu "nên cân nhắc". Viết: "đây là lỗi, đây là cách exploit, đây là cách fix".
4. **Mỗi finding PHẢI có:** severity, file:line, exploit scenario, fix code chạy được.
5. **Luôn giả định worst case:** user input là malicious, network là hostile, database có thể bị tampered.
6. **Cross-reference:** 1 vấn đề thuộc nhiều chiều → ghi ở TẤT CẢ các chiều.
7. **So sánh với chuẩn:** OWASP Top 10 2024, CWE Top 25, ASVS Level 2, WCAG 2.2 AA.
8. **Đề xuất phát triển PHẢI thực tế:** 1 developer, <1tr/tháng, web-only, KHÔNG booking/payment. Đề xuất nào vi phạm ràng buộc = vô giá trị.
9. **Đề xuất vận hành PHẢI actionable:** kèm lệnh cụ thể, config cụ thể, script cụ thể — KHÔNG lý thuyết suông.

---

# DỰ ÁN CẦN AUDIT

## Tổng quan
**vinhlong360** — MXH du lịch/OCOP/cộng đồng cho tỉnh Vĩnh Long (sáp nhập VL+Bến Tre+Trà Vinh).
- **Stack:** FastAPI (Python) + Nuxt 4 SSR (Vue 3) + SQLite (knowledge) + PostgreSQL (UGC/auth)
- **Deploy:** VPS Vultr (Linux), systemd, tarball deploy, 1 instance
- **Developer:** 1 người duy nhất, budget <1 triệu đồng/tháng
- **Mô hình:** CHỈ GIỚI THIỆU — KHÔNG booking/thanh toán/đặt hàng. CTA chỉ là Zalo/Gọi điện.
- **Ảnh:** CHỈ AI-generated (cx/gpt-5.5-image) — KHÔNG stock/UGC/Wikimedia

## Quy mô codebase
- **175 API endpoints** (server.py, admin.py, social.py, auth.py, public_api.py, seo.py, notifications.py, plans.py, saved.py, visits.py)
- **31 database tables** (9 SQLite + 22 PostgreSQL)
- **3050 tests hiện có** (47 files `agent/tests/`, 44 files `tests/`)
- **17 scheduled background tasks** (scheduler.py)
- **12 external HTTP integrations** (eSMS, Telegram, Zalo, LLM, weather, geocode, crawler)

---

# PHASE 1: SECURITY DEEP AUDIT

## 1.1. SQL Injection — KIỂM TRA TỪNG QUERY

**Đã biết:** `database.py:234,351` dùng f-string trong ALTER TABLE (hardcoded dict, risk thấp). Tất cả queries khác dùng parameterized `?`.

**BẠN PHẢI KIỂM TRA:**
- Tất cả `execute(` calls trong `database.py`, `social.py`, `admin.py`, `public_api.py`, `seo.py`
- Tìm BẤT KỲ nơi nào SQL query được build bằng f-string, `.format()`, `%`, hay string concatenation
- ORDER BY / LIMIT / OFFSET injection — parameterized queries KHÔNG protect ORDER BY
- LIKE injection: `%` và `_` wildcards trong search params
- SQLite-specific: `ATTACH DATABASE` injection, `load_extension` 

**Test case BẮT BUỘC phải viết:**
```python
# tests/test_sql_injection.py
# Test TỪNG search endpoint với payloads:
SQLI_PAYLOADS = [
    "'; DROP TABLE entities; --",
    "1 OR 1=1",
    "1' UNION SELECT * FROM users--",
    "admin'--",
    "1; ATTACH DATABASE '/tmp/pwned.db' AS pwned;--",
    "' OR '1'='1",
    "%' OR 1=1--",
    "1 ORDER BY 99--",
]
```

## 1.2. XSS — 22 v-html INSTANCES

**CRITICAL — User-generated content qua v-html:**

| File | Line | Content source | Risk |
|------|------|----------------|------|
| `PostCard.vue` | :47 | `contentHtml` — post body | CRITICAL — user viết HTML |
| `bai-viet/[id].vue` | :90 | `renderComment(c)` — comments | CRITICAL — user viết |
| `bai-viet/[id].vue` | :109 | `renderComment(r)` — replies | CRITICAL — user viết |
| `ChatWidget.vue` | :16,:21 | `formatMd(msg.content)` — chat | HIGH — LLM output + user input |
| `AITravelTips.vue` | :14 | `formatTips(tips)` — AI tips | MEDIUM — LLM output |
| `AISearchAssist.vue` | :14 | `formatReply(aiReply)` — AI | MEDIUM — LLM output |
| `SearchAutocomplete.vue` | :81 | `highlightMatch(item.name)` | HIGH — entity name có thể bị inject |

**BẠN PHẢI:**
1. Đọc hàm `contentHtml`, `renderComment`, `formatMd`, `highlightMatch` — xem có sanitize (DOMPurify/xss) không
2. Tìm ĐƯỜNG ĐI từ user input → database → v-html: có bao nhiêu bước sanitize ở giữa?
3. Test payloads: `<img src=x onerror=alert(1)>`, `<script>alert(1)</script>`, `<a href="javascript:alert(1)">`, `<svg onload=alert(1)>`
4. Kiểm tra server-side sanitize trong `social.py` khi tạo post/comment

**Test case BẮT BUỘC:**
```python
# tests/test_xss.py
XSS_PAYLOADS = [
    '<script>alert("xss")</script>',
    '<img src=x onerror=alert(1)>',
    '<svg/onload=alert(1)>',
    '<a href="javascript:void(0)" onclick="alert(1)">click</a>',
    '"><script>alert(document.cookie)</script>',
    '<iframe src="data:text/html,<script>alert(1)</script>">',
    '<math><mi//xlink:href="data:x,<script>alert(1)</script>">',
    '<input onfocus=alert(1) autofocus>',
]
# Test mỗi payload qua: POST /api/posts, POST /api/posts/{id}/comments
# Verify response KHÔNG chứa unescaped payload
```

## 1.3. Authentication & Authorization — 175 Endpoints

**Kiểm tra TỪNG endpoint trong bảng dưới:**

### Endpoints PHẢI có auth (mutation trên user data):
| Endpoint | Guard expected | File |
|----------|---------------|------|
| `POST /api/posts` | require_user + require_csrf | social.py:266 |
| `DELETE /api/posts/{id}` | require_user + ownership check | social.py:413 |
| `PATCH /api/posts/{id}` | require_user + ownership check | social.py:434 |
| `POST /api/posts/{id}/comments` | require_user + require_csrf | social.py:1115 |
| `PUT /comments/{id}` | require_user + ownership check | social.py:1199 |
| `DELETE /comments/{id}` | require_user + ownership check | social.py:1238 |
| `POST /api/posts/{id}/like` | require_user | social.py:1291 |
| `POST /api/posts/{id}/bookmark` | require_user | social.py:1347 |
| `POST /api/upload/image` | require_user | social.py:1398 |
| `POST /api/follow/{type}/{id}` | require_user | notifications.py:295 |
| `POST /api/block/{id}` | require_user | notifications.py:465 |
| `POST /api/events/{id}/rsvp` | require_user | notifications.py:562 |
| `POST /api/report-ugc` | require_user | notifications.py:442 |
| `PUT /auth/profile` | require_user | auth.py:666 |
| `POST /auth/avatar` | require_user | auth.py:738 |
| `POST /auth/cover` | require_user | auth.py:767 |
| `POST /auth/deactivate` | require_user | auth.py:622 |
| `DELETE /auth/account` | require_user | auth.py:640 |

**BẠN PHẢI kiểm tra MỖI endpoint:**
1. Có guard chưa? (Depends(require_user) hoặc tương đương)
2. Có CSRF check chưa? (Depends(require_csrf) trên POST/PUT/DELETE)
3. Có ownership check chưa? (user A xóa post của user B → 403?)
4. Response có leak data của user khác không?

### Endpoints PHẢI có admin guard:
Tất cả endpoints trong `admin.py` (prefix `/admin/`) — kiểm tra `Depends(require_admin)` applied globally hay per-route.

### Endpoints KHÔNG CẦN auth (public read):
| Endpoint | File | Verify |
|----------|------|--------|
| `GET /api/entities` | public_api.py:161 | Không leak private fields? |
| `GET /api/entities/{id}` | public_api.py:217 | Không trả admin-only data? |
| `GET /api/search` | public_api.py:357 | Search injection? |
| `GET /api/homepage` | public_api.py:476 | Performance? Unbounded? |
| `GET /api/map-pins` | public_api.py:720 | Không trả PII? |
| `GET /health` | server.py:2472 | Không leak internal state? |

### Sensitive system endpoints — AI CÓ kiểm tra auth không?
| Endpoint | Risk |
|----------|------|
| `POST /reload` (server.py:2407) | Reload data — PHẢI require admin |
| `POST /system/learning/run` (server.py:2718) | Trigger learning — PHẢI require admin |
| `POST /vectors/build` (server.py:3013) | Build vectors — PHẢI require admin |
| `GET /system/logs` (server.py:2688) | Leak logs — PHẢI require admin |
| `GET /system/errors` (server.py:2693) | Leak errors — PHẢI require admin |
| `GET /system/memory` (server.py:2767) | Internal state — PHẢI require admin |
| `GET /system/traces` (server.py:2772) | Traces — PHẢI require admin |
| `GET /metrics` (server.py:2618) | Prometheus — PHẢI require admin hoặc internal-only |
| `GET /system/costs` (server.py:3213) | Cost data — PHẢI require admin |
| `GET /system/client-errors` (server.py:2985) | Error logs — PHẢI require admin |
| `POST /system/dynamic-agents/create` (server.py:3309) | Create agent — PHẢI require admin |
| `POST /system/guardrails/check-input` (server.py:3204) | Guardrails — PHẢI require admin |
| `POST /system/semantic-cache/invalidate` (server.py:3268) | Cache bust — PHẢI require admin |
| `POST /system/judge/evaluate` (server.py:3293) | LLM judge — PHẢI require admin |

**Test case BẮT BUỘC:**
```python
# tests/test_auth_bypass.py
# Gọi MỖI mutation endpoint KHÔNG có token → expect 401
# Gọi MỖI admin endpoint với user token thường → expect 403
# Gọi MỖI ownership endpoint với token user khác → expect 403
# Gọi MỖI system endpoint KHÔNG có admin key → expect 401/403
```

## 1.4. IDOR (Insecure Direct Object Reference)

Kiểm tra:
- `DELETE /api/posts/{post_id}` — user A xóa post user B?
- `PATCH /api/posts/{post_id}` — user A edit post user B?
- `DELETE /comments/{comment_id}` — user A xóa comment user B?
- `DELETE /auth/sessions/{session_id}` — user A revoke session user B?
- `DELETE /api/saved/{entity_id}` — có filter by user_id?
- `DELETE /api/plans/{plan_id}` — có filter by user_id?
- `DELETE /api/visits/{entity_id}` — có filter by user_id?

## 1.5. File Upload Security

4 upload endpoints cần kiểm tra:
| Endpoint | File | Max size? | Type whitelist? | Path traversal check? |
|----------|------|-----------|-----------------|----------------------|
| `POST /auth/avatar` | auth.py:738 | ? | ? | ? |
| `POST /auth/cover` | auth.py:768 | ? | ? | ? |
| `POST /admin/entities/{id}/images/upload` | admin.py:446 | ? | ? | ? |
| `POST /api/upload/image` | social.py:1398 | ? | ? | ? |

**Kiểm tra trong `storage.py` và `auth_middleware.py:782`:**
- Magic bytes validation (không chỉ extension)?
- Double extension bypass: `evil.php.jpg`?
- Null byte: `evil.jpg%00.php`?
- SVG with embedded JS?
- Image bomb (decompression bomb — 1KB file → 1GB pixel)?
- EXIF data stripping (GPS coords leak)?

## 1.6. Rate Limiting

Kiểm tra `middleware.py` rate limit config:
- `POST /auth/request-otp` — OTP brute force (max 5/IP/5min?)
- `POST /auth/login` — password brute force
- `POST /auth/verify-otp` — OTP code brute force (6 digits = 1M combos)
- `POST /api/posts` — spam posts
- `POST /api/posts/{id}/comments` — spam comments
- `POST /api/upload/image` — storage abuse
- `POST /api/report-ugc` — report abuse

**BẠN PHẢI verify:** rate limit có per-user HAY chỉ per-IP? (per-IP = bypass bằng proxy)

## 1.7. Security Headers — `middleware.py` (1641 dòng)

Kiểm tra response headers:
- `Strict-Transport-Security` (HSTS) — max-age >= 31536000?
- `Content-Security-Policy` (CSP) — có `script-src 'unsafe-inline'`? (bad)
- `X-Frame-Options` — DENY hoặc SAMEORIGIN?
- `X-Content-Type-Options` — nosniff?
- `X-XSS-Protection` — 1; mode=block?
- `Referrer-Policy` — strict-origin-when-cross-origin?
- `Permissions-Policy` — camera=(), microphone=()?
- Cookie flags: `Secure`, `HttpOnly`, `SameSite=Lax`?
- CORS: `Access-Control-Allow-Origin` — wildcard `*` hay specific?

## 1.8. Secrets & Configuration

- Hardcoded secrets trong code (grep `password`, `secret`, `key`, `token` trong Python files)
- `.env.example` có chứa real values không?
- `config.py` default values cho secrets (rỗng hay insecure default)?
- Error responses có leak internal paths, stack traces, DB schema không?
- `GET /health/deep` (server.py:2561) — trả gì? Leak internal info?

---

# PHASE 2: INPUT VALIDATION TOÀN DIỆN

## 2.1. Kiểm tra MỌI endpoint nhận user input

Cho mỗi endpoint POST/PUT/PATCH, verify:
| Check | Required |
|-------|----------|
| Type validation | Pydantic model hoặc manual check |
| Length limits | max_length trên string fields |
| Format validation | phone, email, URL, coordinates |
| Range validation | page >= 1, page_size <= 100 |
| Required fields | 400 nếu thiếu |
| Extra fields | bỏ qua hoặc reject? |

## 2.2. Specific Input Targets

| Field | Format chuẩn | File |
|-------|-------------|------|
| Phone | `0xxx.xxx.xxx` hoặc `+84` | auth.py |
| Coordinates | lat 9.6-10.5, lng 105.8-106.8 | admin.py, public_api.py |
| Entity name | max 200 chars, no HTML | admin.py |
| Post content | max 5000 chars? | social.py |
| Comment | max 2000 chars? | social.py |
| Username | alphanumeric + underscore, 3-30 chars? | auth.py |
| Search query | max 200 chars, sanitize SQL/XSS | public_api.py, social.py |
| Pagination | page >= 1, page_size 1-100 | ALL list endpoints |
| Entity type | enum validation? | admin.py |
| Image URL | valid URL format, HTTPS only? | admin.py |

## 2.3. Pagination Abuse

Test trên MỌI list endpoint:
```python
# tests/test_pagination.py
PAGINATION_ABUSE = [
    {"page": -1},           # negative
    {"page": 0},            # zero
    {"page": 999999999},    # overflow
    {"page_size": 0},       # zero
    {"page_size": 100000},  # enormous — DoS via large query
    {"page_size": -1},      # negative
    {"offset": -1},         # negative offset
]
# Endpoints to test: GET /api/entities, /api/feed, /api/search, 
# /api/search/posts, /api/search/users, /admin/entities, 
# /admin/moderation/queue, /admin/users, /api/notifications
```

---

# PHASE 3: ERROR HANDLING & RESILIENCE

## 3.1. Unhandled Exceptions

Tìm trong `server.py`, `admin.py`, `social.py`:
- `except:` (bare except — swallows everything)
- `except Exception:` without logging
- Missing try/catch around: database calls, external HTTP calls, file I/O
- `json.loads()` without try/except (malformed JSON crash)
- `int()` conversion without try/except (ValueError crash)

## 3.2. External Service Failures

12 external HTTP calls — mỗi cái cần:
| Service | File | Timeout? | Retry? | Fallback? |
|---------|------|----------|--------|-----------|
| eSMS OTP | auth.py:273 | ? | ? | ? |
| Telegram | bot_gateway.py | ? | ? | ? |
| Zalo OA | bot_gateway.py | ? | ? | ? |
| LLM API | knowledge_agent.py, moderation.py | ? | ? | ? |
| Weather API | realtime.py:76 | ? | ? | ? |
| Geocode API | geocode.py:27 | ? | ? | ? |
| Web crawler | crawler.py:118 | ? | ? | ? |
| Image fetch | admin.py:866 | ? | ? | ? |

**Nếu eSMS down:** user có thể login không? (fallback hay stuck?)
**Nếu LLM down:** chat trả gì? 500 hay graceful message?
**Nếu Telegram down:** admin notification mất — có retry queue?

## 3.3. Database Failures

- SQLite file locked (concurrent write) — có WAL mode?
- PostgreSQL connection pool exhausted — có pool limit + timeout?
- Migration half-applied — có transaction wrapping?
- `database.py:190` `execute()` — có retry on `OperationalError`?

## 3.4. Stack Trace Leaks

Khi `ENVIRONMENT=production`:
- 500 error response có chứa traceback không?
- Exception middleware có sanitize error messages không?
- `GET /system/errors` — endpoint này trả raw stack traces — auth check?

---

# PHASE 4: BUSINESS LOGIC AUDIT

## 4.1. "CHỈ GIỚI THIỆU" Rule — CRITICAL

Tìm trong TOÀN BỘ codebase:
- Bất kỳ endpoint nào cho phép: booking, payment, cart, checkout, order, purchase, invoice
- Bất kỳ form nào có: quantity, price + confirm (chốt đơn = vi phạm NĐ52/85)
- CTA phải CHỈ là: Zalo link, phone call, hỏi giá — KHÔNG "Đặt ngay", "Mua ngay", "Thêm vào giỏ"
- Database tables: có table nào tên `orders`, `transactions`, `payments`, `cart`?

**Nếu tìm thấy bất kỳ payment/booking logic → CRITICAL finding.**

## 4.2. Reputation Gaming

`social.py` reputation system — kiểm tra:
- User tự like chính mình? (self-like = `user_id == post.author_id` check?)
- Spam tạo accounts → like nhau?
- Post rồi delete lặp lại → giữ reputation points?
- Leaderboard manipulation: 1 user 1000 comments rác?

## 4.3. Moderation Bypass

- User post content → hiện ngay hay pending moderation?
- Approved post → user edit → cần re-moderate?
- `POST /api/posts/{id}/best-answer` — chỉ post author hay anyone?
- `admin.py` moderation: approve/reject — có audit trail?

## 4.4. Admin Privilege Escalation

- `POST /admin/users/{id}/role` (admin.py:1878) — admin có thể tự nâng role?
- User role values: có enum validation? Inject `superadmin`?
- API key authentication vs session auth: cùng permission level?

## 4.5. Data Deletion Cascade

- Delete user → posts/comments/likes/follows/notifications/reports xử lý thế nào?
- Delete post → comments/likes/bookmarks cascade?
- Delete entity (admin) → relationships/ratings/feeds cascade?
- Soft delete vs hard delete — nhất quán?

---

# PHASE 5: EDGE CASES & RACE CONDITIONS

## 5.1. Concurrent Operations

```python
# tests/test_race_conditions.py
import asyncio

async def test_double_like():
    """2 requests like cùng post cùng lúc → chỉ 1 like, không crash"""
    
async def test_double_follow():
    """Follow 2 lần cùng lúc → không duplicate follows"""
    
async def test_concurrent_post_delete():
    """Delete post trong khi someone đang comment → 404 graceful"""
    
async def test_concurrent_otp():
    """2 OTP requests cùng phone cùng lúc → chỉ 1 valid"""
    
async def test_concurrent_rsvp():
    """2 RSVP cùng event cùng user → idempotent"""
```

## 5.2. Unicode & Vietnamese

```python
# tests/test_unicode.py
UNICODE_PAYLOADS = [
    "Nguyễn Văn Ả",                    # Vietnamese diacritics
    "😀🎉🏖️",                           # Emoji
    "Café Trần Hưng Đạo",              # Mixed accents
    "​‌‍",               # Zero-width characters
    "A" * 100000,                       # Long string
    "",                                 # Empty
    " ",                                # Whitespace only
    "‪RTL‬ injection",                 # RTL override
    "Null\x00byte",                     # Null byte
    "\n\r\n\r",                         # Newlines
    "<script>alert('Phở')</script>",    # XSS + Vietnamese
]
# Test trên: POST /api/posts, POST /auth/profile, GET /api/search
```

## 5.3. Boundary Values

```python
# tests/test_boundaries.py
# Entity với 0 images, 0 reviews, 0 relationships
# User với 0 posts, 0 followers, 0 following
# Search query = 1 char, 2 chars, exact match, no match
# Page = last page, page > last page
# Post với max length content
# 0 entities in database → homepage không crash?
# 1 user in database → leaderboard không crash?
```

## 5.4. Deleted/Deactivated Users

- User deactivated → posts/comments hiện thế nào? "[đã xóa]"?
- User deactivated → profile page trả gì? 404? Limited info?
- User deactivated → their sessions still valid? (PHẢI revoke)
- User deactivated → can still receive notifications?
- User reactivates → old posts come back?

---

# PHASE 6: PERFORMANCE & DoS

## 6.1. N+1 Queries

Tìm pattern trong `social.py`, `public_api.py`, `admin.py`:
```python
# BAD: N+1
for post in posts:
    author = db.get_user(post.user_id)  # 1 query per post
    
# GOOD: batch
user_ids = [p.user_id for p in posts]
users = db.get_users_batch(user_ids)
```

## 6.2. Unbounded Queries

Tìm `SELECT` không có `LIMIT`:
- `GET /api/homepage` (public_api.py:476) — 720 dòng function — truy vấn bao nhiêu entities?
- `GET /api/map-pins` (public_api.py:720) — trả TẤT CẢ pins? Bao nhiêu?
- `GET /admin/entities` (admin.py:257) — có pagination?
- `GET /api/feed` (social.py:497) — default page_size?
- Sitemap generation (seo.py:1007) — tất cả entities 1 lần?

## 6.3. Regex DoS (ReDoS)

Tìm `re.compile`, `re.match`, `re.search`, `re.findall` — có pattern nào vulnerable?
Ví dụ: `(a+)+$` với input `aaaaaaaaaaaaaaaaX` → catastrophic backtracking.

## 6.4. Memory Issues

- `server.py` chat data — toàn bộ nạp RAM — bao nhiêu MB? Giới hạn?
- `scheduler.py` — 17 tasks chạy concurrent — memory footprint?
- Image processing — WebP conversion in-memory — max file size check?
- SSE notification stream — connection leak nếu client disconnect?

---

# PHASE 7: DATA INTEGRITY

## 7.1. SQLite ↔ PostgreSQL Boundary

**Design decision:** SQLite = knowledge (entities/relationships/itineraries), PG = UGC (users/posts/comments).

**Kiểm tra:**
- Entity endpoint trên PG trả gì? Phải 503.
- UGC endpoint trên SQLite trả gì? Phải 503.
- Cross-DB join: có nơi nào query entity_id từ PG mà không validate tồn tại trong SQLite?
- Entity delete (SQLite) → posts referencing entity_id (PG) xử lý thế nào?

## 7.2. Foreign Key Constraints (PostgreSQL)

22 tables — kiểm tra FK:
- `posts.user_id` → `users.id` ON DELETE CASCADE?
- `comments.post_id` → `posts.id` ON DELETE CASCADE?
- `comments.user_id` → `users.id` ON DELETE CASCADE?
- `likes.user_id` + `likes.post_id` — unique constraint?
- `follows.follower_id` + `follows.target_id` — unique constraint?
- `blocks.blocker_id` + `blocks.blocked_id` — unique constraint?
- Self-reference: `follows` — user follow chính mình? (CHECK constraint?)

## 7.3. Data Consistency

- Timezone: tất cả timestamps UTC? Hay mix UTC + local?
- `created_at` / `updated_at` — auto-set? Hay client có thể gửi?
- Null vs empty string — `description = NULL` vs `description = ""`?
- Boolean storage: Python True/False vs SQL 1/0 vs string "true"?

---

# PHASE 8: API CONTRACT

## 8.1. Response Format Consistency

Kiểm tra 175 endpoints — tất cả trả cùng format?
```json
// Pattern A: direct object
{"id": 1, "name": "..."}

// Pattern B: wrapped
{"data": {"id": 1}, "total": 100}

// Pattern C: array
[{"id": 1}, {"id": 2}]
```
→ MỖI pattern khác nhau = 1 finding (inconsistency)

## 8.2. HTTP Status Codes

| Situation | Expected | Check |
|-----------|----------|-------|
| Create success | 201 | POST endpoints |
| Delete success | 204 hoặc 200 | DELETE endpoints |
| Not found | 404 | GET với invalid ID |
| Unauthorized | 401 | Missing token |
| Forbidden | 403 | Wrong user |
| Validation error | 422 | Invalid input |
| Rate limited | 429 | Exceeded limit |
| Server error | 500 | Internal failure |

## 8.3. Error Response Format

Tất cả errors trả cùng format?
```json
{"detail": "message"}     // FastAPI default
{"error": "message"}      // Custom
{"message": "..."}        // Another custom
```
→ Bao nhiêu format khác nhau? Inconsistency = finding.

---

# PHASE 9: ACCESSIBILITY (WCAG 2.2 AA)

## 9.1. Frontend Audit — MỌI page

| Page | File | LOC | Kiểm tra |
|------|------|-----|----------|
| Homepage | `index.vue` | 1176 | heading hierarchy, alt text, focus order |
| Community | `cong-dong.vue` | 1380 | form labels, error messages, keyboard nav |
| Entity detail | `dia-diem/[id].vue` | 1106 | gallery a11y, review form, map alternative |
| Guide | `huong-dan.vue` | 1215 | step navigation, skip links |
| Settings | `cai-dat.vue` | 854 | form labels, tab panel roles |
| Itinerary | `tao-lich-trinh.vue` | 798 | drag alternative, keyboard reorder |
| Admin entities | `admin/entities.vue` | 942 | table a11y, modal focus trap |

## 9.2. Component Audit

| Component | Kiểm tra |
|-----------|----------|
| `AuthModal.vue` (370) | focus trap, escape close, aria-modal |
| `SearchAutocomplete.vue` (401) | combobox role, arrow key nav, aria-expanded |
| `PhotoGallery.vue` (296) | alt text, keyboard nav, focus visible |
| `ChatWidget.vue` (239) | live region, focus management |
| `PostCard.vue` (338) | article role, heading level |
| `EntityCard.vue` (240) | link wrapping, image alt |
| `NotificationBell.vue` (143) | badge aria-label, dropdown role |
| `CommandPalette.vue` (142) | dialog role, search input |
| `ReportModal.vue` (163) | focus trap, form labels |
| `ContactWidget.vue` (209) | CTA labels, mobile sticky a11y |

## 9.3. Specific WCAG Checks

- `lang="vi"` trên `<html>` tag?
- Skip-to-content link?
- Focus visible outline (không chỉ color change)?
- Touch targets >= 44x44px trên mobile?
- `prefers-reduced-motion` → disable animations?
- `prefers-contrast: more` → increase contrast?
- Form error: `aria-invalid="true"` + `aria-describedby`?
- Dynamic content: `aria-live="polite"` trên toast/notification?
- Input `font-size >= 16px` (prevent iOS zoom)?
- Color contrast text/bg >= 4.5:1?

---

# PHASE 10: CODE QUALITY & ARCHITECTURE

## 10.1. Coverage Gaps — Files KHÔNG có test

| File | LOC | Risk |
|------|-----|------|
| `crawler.py` | 310 | Web scraping — SSRF, timeout, parsing errors |
| `freshness.py` | 451 | Data freshness — logic errors, stale cache |
| `storage.py` | ~400 | File upload — security critical |
| `notifications.py` | ~350 | Partially tested — SSE untested? |
| `seo.py` | 1240 | JSON-LD generation — schema validation |
| `bot_gateway.py` | ~900 | Telegram/Zalo integration — webhook security |
| `scheduler.py` | ~400 | Background tasks — concurrent execution safety |

**BẠN PHẢI viết test cho MỖI file trên.** Mỗi file ít nhất 10 test cases.

## 10.2. God Files — Cần tách

| File | LOC | Concern |
|------|-----|---------|
| `server.py` | 3610 | Routes + chat + system endpoints + startup → tách routes |
| `admin.py` | 2015 | CRUD + moderation + analytics + settings → tách modules |
| `social.py` | 1817 | Posts + comments + likes + follows + search → tách |
| `middleware.py` | 1641 | Rate limit + CORS + logging + compression + security → tách |
| `database.py` | 1457 | SQLite + PG + queries + migrations → tách |

## 10.3. Dead Code

Tìm:
- Functions không ai gọi (grep function name — 0 callers ngoài definition)
- Import không dùng
- Routes không reachable từ frontend
- Config vars defined nhưng không đọc
- Commented-out code blocks > 10 dòng

## 10.4. Dependency Audit

- `requirements.txt` — package nào có known CVE?
- `package.json` (web-nuxt) — package nào outdated > 6 months?
- Pinned versions hay floating? (`==` vs `>=`)
- Dev dependencies in production?

---

# PHASE 11: DEPLOYMENT & INFRASTRUCTURE

## 11.1. Server Config

- Uvicorn workers: 1 hay nhiều? (1 worker = 1 CPU = DoS easy)
- SSL/TLS: termination ở đâu? Certificate auto-renew?
- Firewall: ports mở? (chỉ 80/443/22 cần)
- systemd: restart policy? Memory limit?
- Backup: automated? Frequency? Tested restore?

## 11.2. Docker/Compose

- `docker-compose.yml` — PG password hardcoded?
- Volume mounts: data persistent qua container restart?
- Network isolation: PG accessible từ internet?

## 11.3. Cross-Platform Issues

Dev = Windows, Prod = Linux:
- Path separators: `\` vs `/`
- File permissions: Windows NTFS vs Linux ext4
- Line endings: CRLF vs LF
- Case sensitivity: `File.py` vs `file.py`
- SQLite path: absolute vs relative

---

# PHASE 12: 17 BACKGROUND TASKS AUDIT

Mỗi scheduled task trong `scheduler.py`:

| Task | Interval | Gate | Risk |
|------|----------|------|------|
| `auto-learn` | 3h | autonomous | Crawl external sites — SSRF? |
| `relationships` | 12h | autonomous | DB writes — race condition? |
| `data-sync` | 1h | none | SQLite→PG sync — consistency? |
| `analytics-cleanup` | 24h | none | Delete old data — audit trail? |
| `admin-digest` | 24h | none | Send Telegram — PII leak? |
| `autonomous-agent` | 24h | budget-capped | LLM calls — budget enforcement? |
| `cache-warmup` | 1h | none | Memory spike? |
| `agent-evolution` | 12h | autonomous | Self-modify? Safety? |
| `optimizer-check` | 6h | autonomous | Config change — audit? |
| `guardrails-cleanup` | 12h | none | Delete guardrails — safety? |
| `session-cleanup` | 6h | none | Delete sessions — data loss? |
| `notification-cleanup` | 24h | none | Delete notifications — audit? |
| `ratelimit-gc` | 5min | none | Memory management — leak? |
| `moderation-escalation` | 6h | none | Auto-escalate — false positive? |
| `learning-loop` | 1h | autonomous | LLM-powered — budget? |
| `kb-promotion` | 6h | autonomous | Auto-promote content — quality? |
| `continuous-discovery` | 1h adaptive | autonomous | External calls — SSRF? |

**Autonomous gate verification:**
- `AUTONOMOUS_AGENT_ENABLED=true` PHẢI là opt-in (default OFF)?
- `AUTONOMOUS_AGENT_MAX_CALLS_PER_DAY` cap — enforced ở đâu? Bypass?
- Kill switch — set false = tắt ngay? Hay phải restart?

---

# PHASE 13: VISUAL DESIGN & UI QUALITY (qua code)

> Codex không render UI — kiểm tra qua CSS/Vue source code. Mỗi finding = đoạn code cụ thể vi phạm chuẩn thiết kế.

## 13.1. Design Token Consistency

Dự án dùng **CSS custom properties 3 tầng** (primitive → semantic → component) trong `variables.css` (646 dòng).

**Kiểm tra:**
- Grep **TẤT CẢ** `.vue` và `.css` files — tìm hardcoded colors (`#xxx`, `rgb(`, `hsl(`) KHÔNG qua CSS variable
- Grep hardcoded spacing (`margin: 12px`, `padding: 8px`, `gap: 16px`) thay vì dùng `var(--space-*)` hoặc `var(--gap-*)`
- Grep hardcoded font-size (`font-size: 14px`) thay vì dùng token
- Grep hardcoded border-radius thay vì `var(--radius-*)`
- Grep hardcoded box-shadow thay vì `var(--shadow-*)`
- **Mỗi hardcoded value = 1 finding P3** (inconsistency, maintainability)

**Primitives đã define (phải dùng thay vì hardcode):**
- Colors: `--clay-*`, `--amber-*`, `--leaf-*`, `--river-*`, `--sand-*`, `--ink-*`
- Semantics: `--primary`, `--accent`, `--secondary`, `--tertiary`, `--bg`, `--ink`, `--muted`, `--line`, `--border`
- Containers: `--primary-container`, `--secondary-container`, `--accent-container`
- On-colors: `--on-primary`, `--on-secondary`, `--on-accent`

## 13.2. Typography Hierarchy

**Kiểm tra trong toàn bộ pages:**
- Heading hierarchy: `<h1>` → `<h2>` → `<h3>` — có skip level (h1→h3) không?
- Mỗi page CHỈ ĐƯỢC 1 `<h1>` — tìm pages có 2+ `<h1>`
- Font-weight usage: có quá 4 weights (300, 400, 500, 600, 700) trên 1 page?
- Line-height: body text phải >= 1.5 (a11y + readability). Tìm `line-height` < 1.4
- Max-width cho readable text: phải <= 70ch hoặc ~680px. Tìm text blocks KHÔNG có max-width constraint
- Letter-spacing trên uppercase text: phải > 0 (readability). Tìm `text-transform: uppercase` KHÔNG có `letter-spacing`

## 13.3. Spacing & Layout Consistency

**Kiểm tra:**
- CSS Grid/Flexbox gaps: tất cả dùng cùng scale? (4, 8, 12, 16, 24, 32, 48, 64)
- Section spacing: khoảng cách giữa sections trong pages — nhất quán?
- Card padding: tất cả cards dùng cùng padding token?
- Container max-width: các pages dùng cùng `max-width`? Hay mỗi page khác nhau?
- Responsive padding: mobile có padding nhỏ hơn desktop?

## 13.4. Color Harmony & Dark Mode

**Kiểm tra `dark-overrides.css` (130 dòng) + 292 `.dark` rules:**
- Mọi semantic color (`--primary`, `--bg`, `--ink`, `--muted`, `--line`, `--card`, `--border`) ĐỀU có dark mode override?
- Dark mode contrast: text trên bg đạt 4.5:1? (tính từ CSS values)
- Accent colors trong dark mode: vẫn đủ contrast?
- Images/icons: có `filter: brightness()` hoặc `opacity` adjustment cho dark mode?
- Box-shadows: dark mode dùng shadow sáng hơn hay đổi sang `border`?
- Gradient colors: có override trong dark mode?
- Status colors (error, warning, success, info): đủ contrast cả light + dark?

## 13.5. Animation & Motion

**1751 animation/transition declarations across 110 files — kiểm tra:**
- `prefers-reduced-motion`: bao nhiêu % animations respect media query này?
  ```css
  /* PHẢI có: */
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }
  ```
- Animation duration: > 500ms cho UI element? (quá chậm = perceived lag)
- `transition: all` usage? (performance — nên chỉ transition specific properties)
- `will-change` abuse? (memory — chỉ dùng khi thật sự cần)
- Easing functions: có dùng `linear` cho UI transitions? (nên dùng ease-out/cubic-bezier)
- Scroll-linked animations: có `requestAnimationFrame` fallback cho `scroll-timeline`?

## 13.6. Component Visual Consistency

**Kiểm tra across components:**

| Pattern | Chuẩn (từ `implementation-specs.md`) | Verify |
|---------|--------------------------------------|--------|
| Card image ratio | `aspect-ratio: 3/2` | Tất cả cards dùng cùng ratio? |
| Card border-radius | `12px` / `var(--radius-lg)` | Nhất quán? |
| Card hover | `scale(1.03)` + shadow lift | Tất cả cards có? |
| Button height | `48px` cho primary CTA | Nhất quán? |
| Button border-radius | `999px` (pill) cho CTA, `8px` cho secondary | Mix? |
| Badge font-size | `11-12px`, weight 600 | Nhất quán? |
| Input height | >= `44px` (touch target) | Tất cả inputs? |
| Modal width | `max-width: 480px` (mobile), `560px` (desktop) | Nhất quán? |
| Chip height | `36px`, radius `18px` | Tất cả chips? |
| Icon sizes | 16/20/24px scale | Consistent? |

## 13.7. Image Handling

**Kiểm tra trong Vue templates + CSS:**
- `<img>` tags: tất cả có `alt` attribute? (a11y + SEO)
- `<img>` tags: above-fold images có `loading="lazy"`? (WRONG — should NOT be lazy)
- `<img>` tags: có `width` + `height` attributes? (prevent layout shift / CLS)
- `<NuxtImg>` / `<NuxtPicture>`: có `sizes` + `srcset` cho responsive?
- Background images: có responsive variants cho mobile?
- Placeholder/skeleton: images có loading state (shimmer/blur-up)?
- Broken image fallback: `@error` handler hoặc CSS fallback?
- `object-fit`: images trong cards dùng `cover` nhất quán?

## 13.8. Responsive Design Quality

**Breakpoints chuẩn:** 600/768/1024/1280/1440px

**Kiểm tra MỌI page:**
- Mobile (< 600px): navigation accessible? Content readable? Touch targets 44px?
- Tablet (768-1024px): layout có optimize hay chỉ stretch mobile?
- Desktop (> 1280px): content có max-width hay stretch toàn màn hình?
- `overflow-x: hidden` trên body/main? (bad practice — hides bugs)
- Horizontal scroll: bất kỳ element nào gây horizontal scroll trên mobile?
- Sticky elements: header + CTA bar + FAB — có chồng nhau?
- Safe area: `env(safe-area-inset-bottom)` cho fixed bottom bars (iPhone notch)?
- Font scaling: layout có vỡ khi user đặt browser font size 150%?

## 13.9. Visual Hierarchy Signals (qua code)

**Kiểm tra:**
- CTA buttons: primary CTA dùng `--primary` bg? Nổi bật nhất trên trang?
- Secondary actions: có visual distinction rõ ràng vs primary? (outline vs filled)
- Destructive actions (delete, ban): dùng `--error` color?
- Disabled states: có `opacity` + `pointer-events: none` + `cursor: not-allowed`?
- Empty states: có component `EmptyState.vue` — tất cả list pages dùng?
- Loading states: có `SkeletonGrid.vue` + `SkeletonList.vue` — tất cả pages dùng?
- Error states: form errors có 3 tín hiệu (red border + text + icon)?
- Success feedback: toast/notification sau actions (like, save, submit)?

## 13.10. Z-index Management

**Kiểm tra:**
- Grep tất cả `z-index` values — list từ thấp → cao
- Có z-index scale? (1/10/100/1000) hay random (5/12/47/999)?
- Conflict: 2 elements cùng z-index nhưng overlap?
- Modal z-index > everything else?
- Sticky header z-index > page content nhưng < modal?
- Toast z-index > modal? (nên hiện trên mọi thứ)
- Dropdown z-index: có bị che bởi sibling cards?

---

# PHASE 14: UX FLOW & INTERACTION PATTERNS (qua code)

## 14.1. User Journey Completeness

**Kiểm tra flow code — có route/page/component cho từng bước:**

### Journey 1: Khách mới → Tìm điểm đến
```
Homepage → Search/Browse → Entity list → Entity detail → Contact (Zalo/Phone)
```
- Có `SearchAutocomplete.vue`? Search endpoint? Empty state khi 0 results?
- Entity list có filter/sort? Pagination?
- Entity detail có CTA rõ ràng (Zalo/Phone)?
- Breadcrumb navigation: user biết mình ở đâu?

### Journey 2: Đăng ký → Tạo nội dung
```
AuthModal (OTP) → Profile setup → Browse feed → Create post → Interact
```
- Sau login lần đầu: redirect về đâu? Có onboarding?
- Profile setup: có prompt đặt avatar, bio?
- Create post: có draft auto-save? Image upload?
- First post: empty state có CTA "Tạo bài viết đầu tiên"?

### Journey 3: Admin daily workflow
```
Login → Dashboard → Check alerts → Moderate → Edit entities → Analytics
```
- Dashboard: pending items có badge count?
- Moderation: batch actions? Keyboard shortcuts?
- Navigation: sidebar có active state? Breadcrumbs?

## 14.2. Error & Empty States Coverage

**Tìm MỌI nơi data có thể trống — có empty state không?**

| Scenario | Page | Có EmptyState? |
|----------|------|---------------|
| 0 search results | `tim-kiem.vue` | ? |
| 0 posts in feed | `cong-dong.vue` | ? |
| 0 followers | `nguoi-dung/[id].vue` | ? |
| 0 notifications | `thong-bao.vue` | ? |
| 0 bookmarks | composable `useBookmarks` | ? |
| 0 itineraries | `lich-trinh/index.vue` | ? |
| 0 reviews | `EntityReviews.vue` | ? |
| 0 entities in area | `khu-vuc/[area].vue` | ? |
| 0 events | `su-kien.vue` | ? |
| Network error | any page | ? |
| 404 page | `error.vue` | ? |
| 503 (maintenance) | `error.vue` | ? |

## 14.3. Form UX

**Kiểm tra MỌI form trong codebase:**
- Submit button: disable khi submitting? (prevent double submit)
- Loading indicator trên button khi submitting?
- Validation: inline (while typing) hay on-submit?
- Error display: below field, not just toast?
- Success: clear form? Redirect? Toast?
- Unsaved changes: confirm before navigating away? (`beforeunload`)
- Auto-focus: first field focused khi form mở?

Forms to check:
| Form | File | Fields |
|------|------|--------|
| Login/Register | `AuthModal.vue` | phone, OTP |
| Create post | `cong-dong.vue` | title, content, images, tags |
| Create comment | `bai-viet/[id].vue` | content |
| Write review | `EntityReviews.vue` | rating, text |
| Edit profile | `cai-dat.vue` | name, bio, avatar |
| Create itinerary | `tao-lich-trinh.vue` | title, stops, schedule |
| Report content | `ReportModal.vue` | reason, detail |
| Admin entity edit | `admin/entities.vue` | many fields |
| Search | `SearchAutocomplete.vue` | query |
| Contact | `lien-he.vue` | name, message |

## 14.4. Navigation & Wayfinding

**Kiểm tra:**
- Breadcrumb: có trên tất cả sub-pages? Format đúng?
- Active nav item: sidebar/header highlight trang hiện tại?
- Back button: SPA navigation history đúng? (browser back = previous page, NOT homepage)
- Deep linking: URL có thể bookmark + share? (SSR pages)
- 404 handling: invalid routes redirect hay show error?
- Scroll restoration: navigate back = scroll position restored?
- Mobile navigation: hamburger menu? Bottom nav? Cả 2?
- Admin navigation: sidebar collapsible? Responsive?

## 14.5. Feedback & Confirmation

**Kiểm tra:**
- Destructive actions (delete post, ban user, leave group): có confirm dialog?
- Success actions: toast notification sau save/create/update?
- Like/bookmark: immediate visual feedback (optimistic UI)?
- Follow: button state change ngay lập tức?
- Loading states: spinner/skeleton cho mỗi async operation?
- Error recovery: "Thử lại" button khi network fail?
- Copy to clipboard: toast confirm "Đã sao chép"?
- Share: feedback khi shared thành công?

## 14.6. Micro-interactions & Polish

**Kiểm tra (qua code):**
- Button hover states: tất cả buttons có `:hover` style?
- Button active/pressed states: `:active` style (subtle scale down)?
- Link hover: underline hoặc color change?
- Card hover: elevation change (shadow lift)?
- Input focus: visible focus ring (not just default browser outline)?
- Scroll-to-top button: hiện khi scroll > 1 viewport?
- Page transitions: có `<Transition>` wrapper cho route changes?
- List item animations: staggered entrance khi items load?
- Skeleton loading: shimmer animation trên placeholder?
- Pull-to-refresh (mobile): có support?

---

# PHASE 15: CHIẾN LƯỢC PHÁT TRIỂN SẢN PHẨM

> Vai trò Strategic Advisor bắt đầu từ đây. Đọc TOÀN BỘ codebase + findings Phase 1-14 rồi đưa ra đề xuất.

## 15.1. Product-Market Fit Assessment

**Phân tích từ code hiện tại — dự án đang ở đâu trên thang PMF?**

Đánh giá dựa trên:
- Feature completeness: bao nhiêu % features core đã production-ready?
- Content depth: entities có đủ data (images, descriptions, reviews) để hữu ích?
- User engagement loops: có vòng lặp giữ user quay lại? (notification, feed, follow)
- Growth mechanisms: organic SEO, social sharing, referral — cái nào đã hoạt động?
- Competitive moat: so với vinhlongtourist.vn, Google Maps, TripAdvisor — dự án này thắng ở đâu?

**Output:** Bảng PMF Scorecard:
```markdown
| Yếu tố | Điểm (1-10) | Evidence từ code | Đề xuất cải thiện |
```

## 15.2. Feature Prioritization — Next 6 Months

**Dựa trên code hiện tại, đề xuất 3 tier:**

### Tier 1: Must-have (fix within 1 month)
- Những gì ĐANG THIẾU mà user KHÔNG THỂ dùng dự án nếu thiếu?
- Ví dụ: nếu search không hoạt động đúng → user bỏ đi

### Tier 2: Should-have (build within 3 months)
- Những gì TĂNG VALUE đáng kể cho user?
- Phân tích: feature nào có effort thấp nhưng impact cao?

### Tier 3: Nice-to-have (build within 6 months)
- Enhancement, polish, secondary features

**CHO MỖI ĐỀ XUẤT phải có:**
```markdown
| Feature | Effort (S/M/L) | Impact (1-10) | Priority Score | Files cần sửa | Dependencies |
```

**RÀNG BUỘC CỨNG — đề xuất vi phạm thì LOẠI BỎ:**
- KHÔNG booking/payment/cart/checkout (vi phạm NĐ52/85)
- KHÔNG native app, AR, audio guide (solo dev, budget thấp)
- KHÔNG external paid services > $10/month
- KHÔNG features cần team > 1 người maintain
- Ảnh CHỈ AI-generated — KHÔNG đề xuất UGC photos, stock photos

## 15.3. Architecture Evolution Path

**Đánh giá kiến trúc hiện tại vs scale tiếp theo:**

| Scale | Users | Kiến trúc cần | Hiện tại đủ? | Action nếu chưa đủ |
|-------|-------|--------------|-------------|---------------------|
| 0-1K | < 1K DAU | Monolith + SQLite + PG | ? | ? |
| 1K-5K | 1-5K DAU | ? | ? | ? |
| 5K-10K | 5-10K DAU | ? | ? | ? |

Cho mỗi scale level:
- Bottleneck dự đoán (từ code analysis): CPU? Memory? DB connections? Disk I/O?
- Config changes cần (không cần code): worker count, connection pool, cache TTL
- Code changes cần: refactor nào, tách module nào, thêm cache layer nào
- Infrastructure changes: VPS spec, CDN, DB replication
- Estimated cost tại mỗi level (VNĐ/tháng)

## 15.4. SEO & Growth Strategy (từ code)

**Phân tích `seo.py` (1240 dòng) + Nuxt SSR config:**
- Sitemap: bao nhiêu URLs? Có split cho large sitemaps? (> 50K URLs cần sitemap-index)
- JSON-LD: entities nào có structured data? Thiếu schema nào?
- Meta tags: dynamic title/description cho mỗi entity page? Hay generic?
- Open Graph: share preview có image? Description đúng?
- Canonical URLs: duplicate content protection?
- Internal linking: entities link đến entities liên quan? Hub-spoke model?
- Page speed: SSR response time estimate? Static generation cho popular pages?
- GEO (Generative Engine Optimization): FAQ schema? HowTo schema? Có content dạng AI-citation-friendly?

**Đề xuất SEO roadmap:**
```markdown
| Action | Effort | Expected Impact (organic traffic) | Timeline |
```

## 15.5. Content Strategy

**Phân tích từ data structure + admin tools:**
- Bao nhiêu entities có description đầy đủ (> 200 chars)? Bao nhiêu mỏng (< 50 chars)?
- Bao nhiêu entities có images? Bao nhiêu không có?
- Content types nào nhiều nhất? Ít nhất? Cần bổ sung gì?
- Có editorial workflow (draft → review → publish) không? Hay publish trực tiếp?
- Content freshness: có mechanism cập nhật info cũ?
- User-generated content: tỉ lệ posts/reviews per active user?

**Đề xuất:**
- Content calendar template (loại nào, bao nhiêu bài/tuần, ai viết)
- Content quality automation (scripts kiểm tra chất lượng tự động)
- AI-assisted content creation workflow (dùng LLM API đã có)

## 15.6. Monetization Readiness (trong khuôn khổ "CHỈ GIỚI THIỆU")

**Dự án có 3 nguồn thu đã plan:** premium/featured listing + B2G + quảng cáo.

**Kiểm tra code hỗ trợ monetization:**
- Premium listing: có field/flag phân biệt free vs premium entity? Có admin UI quản lý?
- Featured placement: homepage có slot cho "sponsored" hay "nổi bật"? Có API cho admin chọn?
- B2G: có dashboard/report xuất được cho đối tác chính quyền? (traffic, engagement, entity coverage)
- Quảng cáo: có ad slot trong layout? Có integration point? (Google AdSense, custom banner)
- Analytics cho advertisers: entity page views, contact clicks — có tracking?

**Đề xuất monetization implementation:**
```markdown
| Revenue stream | Code hiện có (%) | Cần thêm | Effort | Revenue potential (VNĐ/tháng) |
```

---

# PHASE 16: CHIẾN LƯỢC VẬN HÀNH

## 16.1. DevOps & Deployment Maturity

**Đánh giá pipeline hiện tại từ code + scripts:**
- CI/CD: có automated pipeline? Hay manual deploy?
- Testing in pipeline: tests chạy trước deploy?
- Rollback strategy: có backup trước deploy? Rollback mất bao lâu?
- Deployment frequency: code → prod mất bao lâu?
- Environment parity: dev (Windows) vs prod (Linux) — gap nào?

**Đề xuất theo DORA metrics (cho 1-person team):**
```markdown
| Metric | Hiện tại (ước lượng) | Target 3 tháng | Action cụ thể |
|--------|---------------------|----------------|----------------|
| Deployment frequency | ?/week | | |
| Lead time for changes | ? hours | | |
| Change failure rate | ?% | | |
| MTTR | ? minutes | | |
```

## 16.2. Monitoring & Observability

**Kiểm tra từ code:**
- `GET /health`, `/health/deep`, `/health/ready`, `/health/slo` — đủ health checks?
- Logging: structured (JSON) hay plain text? Log rotation?
- Error tracking: Sentry/equivalent integrated? Hay chỉ file log?
- Metrics: Prometheus endpoint có? Dashboard (Grafana)?
- Uptime monitoring: external ping? Alert khi down?
- Performance monitoring: response time tracking? Slow query log?

**Đề xuất monitoring stack (free-tier only, < 1tr/tháng):**
```markdown
| Layer | Tool | Free tier limit | Setup effort | Config/command |
|-------|------|-----------------|-------------|----------------|
| Uptime | ? | | | |
| Error tracking | ? | | | |
| Metrics | ? | | | |
| Log aggregation | ? | | | |
| Alerts | ? | | | |
```

## 16.3. Backup & Disaster Recovery

**Kiểm tra từ code + scripts:**
- `scripts/backup_data.py` — backup gì? Frequency? Nơi lưu?
- Database backup: SQLite file copy + PG `pg_dump`?
- Off-site backup: có copy ra ngoài VPS? (nếu VPS chết = mất hết?)
- Backup testing: có script test restore? Bao lâu 1 lần?
- RPO (Recovery Point Objective): mất tối đa bao nhiêu data?
- RTO (Recovery Time Objective): phục hồi mất bao lâu?

**Đề xuất backup strategy:**
```markdown
| Data | Frequency | Method | Off-site | Retention | Verify | Estimated cost |
|------|-----------|--------|----------|-----------|--------|----------------|
| SQLite DB | | | | | | |
| PostgreSQL | | | | | | |
| Media/images | | | | | | |
| Config/.env | | | | | | |
| Code (git) | | | | | | |
```

**Disaster recovery runbook** — viết script cụ thể:
```bash
# Scenario 1: VPS chết hoàn toàn — recovery trên VPS mới
# Scenario 2: Database corruption — restore từ backup
# Scenario 3: Hacked — incident response steps
# Scenario 4: Data mất do bug — rollback to known-good state
```

## 16.4. Security Operations

**Đánh giá security posture cho solo dev:**
- Dependency update cadence: bao lâu update packages?
- Secret rotation: API keys, DB passwords — rotate bao lâu?
- Access audit: SSH keys, admin accounts — review bao lâu?
- Vulnerability scanning: có automated scan? (pip-audit, npm audit)
- Incident response: có runbook? Ai liên hệ khi bị hack?

**Đề xuất security ops calendar:**
```markdown
| Task | Frequency | Command/Script | Time (phút) |
|------|-----------|----------------|-------------|
| pip-audit | Weekly | `pip-audit --fix` | 10 |
| npm audit | Weekly | `cd web-nuxt && npm audit` | 10 |
| Backup verify | Monthly | `python scripts/test_restore.py` | 30 |
| Secret rotation | Quarterly | (checklist) | 60 |
| SSH key review | Quarterly | `cat ~/.ssh/authorized_keys` | 5 |
| Full security audit | Yearly | (this prompt) | 480 |
```

## 16.5. Performance Baseline & Budget

**Thiết lập baseline từ code analysis:**
- API response time targets: p50, p95, p99 cho mỗi endpoint category
- Page load targets: LCP, FID, CLS (Core Web Vitals)
- Database query targets: max query time before optimization
- Memory usage: baseline + ceiling cho VPS plan hiện tại
- Cost tracking: LLM calls/day, storage usage, bandwidth

**Đề xuất performance budget:**
```markdown
| Metric | Target | Alert threshold | Action khi vượt |
|--------|--------|-----------------|-----------------|
| API p95 | < 200ms | > 500ms | ? |
| LCP | < 2.5s | > 4s | ? |
| Memory | < 512MB | > 768MB | ? |
| LLM calls/day | < 20 | > 50 | ? |
| DB size SQLite | < 100MB | > 200MB | ? |
| DB size PG | < 500MB | > 1GB | ? |
```

## 16.6. Operational Runbooks

**Viết runbook cho MỖI scenario thường gặp:**

### Runbook 1: Deploy new version
```bash
# Step-by-step commands, pre/post checks, rollback if fail
```

### Runbook 2: Server unresponsive
```bash
# Diagnostic steps, restart sequence, escalation path
```

### Runbook 3: Database full
```bash
# Check disk, cleanup, archive old data, expand if needed
```

### Runbook 4: High CPU/Memory
```bash
# Identify process, check scheduler tasks, rate limit abuse
```

### Runbook 5: SSL certificate expiry
```bash
# Renew steps, verify, prevent recurrence
```

### Runbook 6: Data corruption detected
```bash
# Isolate, assess damage, restore from backup, verify
```

### Runbook 7: Security incident (suspected breach)
```bash
# Containment, evidence preservation, assessment, recovery, post-mortem
```

**Mỗi runbook PHẢI có:**
- Trigger condition (khi nào chạy runbook này)
- Step-by-step commands (copy-paste được)
- Expected output mỗi bước
- Escalation path (khi nào cần người khác)
- Post-incident checklist

## 16.7. Solo Dev Sustainability

**Đánh giá rủi ro "bus factor = 1":**
- Documentation: code có self-documenting? Newcomer onboard mất bao lâu?
- Knowledge silos: phần nào CHỈ developer hiểu? (magic configs, undocumented behaviors)
- Automation: bao nhiêu % tasks có thể tự động? Manual toil ở đâu?
- Burnout risk: maintenance load vs development time ratio?

**Đề xuất sustainability plan:**
```markdown
| Risk | Mitigation | Effort | Priority |
|------|-----------|--------|----------|
| Bus factor = 1 | Documentation + runbooks | M | HIGH |
| Manual deploy | CI/CD pipeline (GitHub Actions free) | M | HIGH |
| No error alerts | Uptime monitoring + Telegram alerts | S | HIGH |
| Growing tech debt | Weekly 2h debt cleanup | ongoing | MEDIUM |
| Content creation bottleneck | AI-assisted content pipeline | M | MEDIUM |
```

---

# OUTPUT FORMAT — KHÔNG THAY ĐỔI

## Severity Definitions

| Level | Tiêu chí | Ví dụ |
|-------|----------|-------|
| **P0 CRITICAL** | Exploit ngay, data loss, auth bypass, RCE, vi phạm pháp luật | SQL injection, unauthenticated admin endpoint, payment logic, PII leak |
| **P1 HIGH** | Security risk cần fix tuần này, data corruption possible | XSS stored, IDOR, missing rate limit auth, broken cascade |
| **P2 MEDIUM** | UX/reliability impact, fix trong 2 tuần | N+1, inconsistent errors, missing validation, a11y gaps |
| **P3 LOW** | Code quality, maintainability | Dead code, magic numbers, missing type hints, god files |

## Finding Format

Mỗi finding PHẢI theo format sau (KHÔNG tắt bớt field):

```markdown
### [P0] Finding-001: <Tên finding ngắn gọn>

**Chiều:** Security / Input Validation / Error Handling / Business Logic / Edge Cases / Performance / Data Integrity / API Contract / Accessibility / Code Quality / Deployment / Background Tasks / Visual Design / UX Flow
**File:** `agent/social.py:1291`
**OWASP:** A03:2021 Injection (nếu applicable)
**CWE:** CWE-89 (nếu applicable)

**Mô tả:**
<2-3 câu mô tả vấn đề CHÍNH XÁC. Không vòng vo.>

**Exploit scenario:**
1. Attacker gửi request: `curl -X POST /api/...`
2. Server xử lý: <mô tả flow>
3. Kết quả: <data leak / crash / unauthorized access>

**Root cause:**
<1-2 câu: TẠI SAO lỗi này tồn tại>

**Fix:**
```python
# TRƯỚC (vulnerable)
<code hiện tại>

# SAU (fixed)  
<code đã sửa — copy-paste được>
```

**Test:**
```python
def test_finding_001():
    """Regression test cho finding này"""
    <test hoàn chỉnh — chạy được với pytest>
```

**Effort:** S (< 1h) / M (1-4h) / L (4h+)
```

---

# DELIVERABLES — 8 FILES

## PHẦN A: QA AUDIT (4 reports)

### 1. `qa-report-security.md`
- Tất cả findings Phase 1-4 (Security, Input, Error, Business Logic)
- Sắp xếp: P0 trước, P3 sau
- Summary table đầu file

### 2. `qa-report-quality.md`
- Tất cả findings Phase 5-10 (Edge Cases, Performance, Data, API, A11y, Code Quality)
- Sắp xếp: P0 trước, P3 sau

### 3. `qa-report-infra.md`
- Tất cả findings Phase 11-12 (Deployment, Background Tasks)
- Sắp xếp: P0 trước, P3 sau

### 4. `qa-report-visual-ux.md`
- Tất cả findings Phase 13-14 (Visual Design, UX Flow)
- Sắp xếp theo page/component, P0 trước
- Bao gồm: token violations, typography issues, responsive problems, UX gaps, animation issues, dark mode gaps

## PHẦN B: TESTS

### 5. `qa-test-suite.md`
- Tất cả test cases viết cho từng finding
- Organized by file (tests/test_security.py, tests/test_edge_cases.py, ...)
- PHẢI chạy được với `pytest`

## PHẦN C: CHIẾN LƯỢC (Phase 15-16)

### 6. `qa-strategy-product.md`
- PMF Scorecard (15.1)
- Feature prioritization 3 tiers (15.2) — bảng effort/impact/priority
- Architecture evolution path (15.3) — scale 0→1K→5K→10K
- SEO & growth roadmap (15.4) — actions + expected impact
- Content strategy (15.5) — calendar + automation
- Monetization readiness (15.6) — revenue streams + implementation gaps

### 7. `qa-strategy-ops.md`
- DevOps maturity assessment + DORA metrics (16.1)
- Monitoring stack recommendation (16.2) — free-tier tools + config
- Backup & DR strategy (16.3) — bảng + disaster recovery scripts
- Security ops calendar (16.4) — weekly/monthly/quarterly tasks
- Performance budget (16.5) — targets + alert thresholds
- Operational runbooks (16.6) — 7 scenarios, copy-paste commands
- Solo dev sustainability plan (16.7) — risk + mitigation

## PHẦN D: TỔNG KẾT

### 8. `qa-scorecard.md`
- Bảng điểm **16 chiều**, mỗi chiều 1-10
- Điểm trung bình = điểm dự án
- So sánh với chuẩn (OWASP ASVS Level 2, WCAG 2.2 AA, Apple HIG, Material Design 3)
- Top 5 P0 fixes với estimated timeline
- Top 5 strategic recommendations với expected ROI
- Verdict: PASS / CONDITIONAL PASS / FAIL (FAIL nếu có bất kỳ P0 unfixed)

Scorecard format:
```markdown
| # | Chiều | Điểm | Findings P0/P1/P2/P3 | Đánh giá |
|---|-------|------|----------------------|----------|
| 1 | Security | X/10 | 0/2/5/3 | <1 dòng> |
| 2 | Input Validation | X/10 | ... | ... |
| 3 | Error Handling | X/10 | ... | ... |
| 4 | Business Logic | X/10 | ... | ... |
| 5 | Edge Cases | X/10 | ... | ... |
| 6 | Performance | X/10 | ... | ... |
| 7 | Data Integrity | X/10 | ... | ... |
| 8 | API Contract | X/10 | ... | ... |
| 9 | Accessibility | X/10 | ... | ... |
| 10 | Code Quality | X/10 | ... | ... |
| 11 | Deployment | X/10 | ... | ... |
| 12 | Background Tasks | X/10 | ... | ... |
| 13 | Visual Design | X/10 | ... | ... |
| 14 | UX Flow | X/10 | ... | ... |
| 15 | Product Strategy | X/10 | ... | ... |
| 16 | Operations | X/10 | ... | ... |
| **Tổng** | | **X.X/10** | **X/X/X/X** | **PASS/FAIL** |

### Radar Chart (text-based)
Security ████████░░ 8
Input    ██████░░░░ 6
...
Ops      ███████░░░ 7
```

---

# QUY TẮC CUỐI CÙNG

1. Đọc **MỌI file Python** trong `agent/` (không bỏ sót file nào)
2. Đọc **MỌI file Vue** trong `web-nuxt/pages/` và `web-nuxt/components/`
3. Đọc **MỌI file CSS** trong `web-nuxt/assets/css/` (9 files, 4424 dòng)
4. Đọc **MỌI file test** hiện có — tìm test yếu (assertion loose, mock che bug, happy-path only)
5. Tổng findings tối thiểu: **80** (nếu dưới 80 → bạn chưa đủ kỹ). Trong đó:
   - Security + Input: >= 20 findings
   - Visual + UX: >= 15 findings
   - Code Quality + Performance: >= 15 findings
   - Các chiều khác: >= 30 findings
6. Test cases tối thiểu: **120** test functions mới
7. KHÔNG nói "dự án này khá tốt cho 1 developer". Đánh giá theo chuẩn production, không theo context.
8. KHÔNG recommend giải pháp cần: Kubernetes, Redis cluster, microservices, team > 3 người, budget > 5tr/tháng
9. Fix recommendation PHẢI chạy được trên stack hiện tại (FastAPI + Nuxt + SQLite + PG + 1 VPS)
10. Nếu tìm thấy **payment/booking logic** → report là P0 CRITICAL + pháp lý NĐ52/85
11. Nếu tìm thấy **PII leak** (phone, email, IP trong response không auth) → P0 CRITICAL
12. Visual findings: SO SÁNH với chuẩn **Apple HIG** (spacing 8pt grid, touch 44pt, radius consistency) và **Material Design 3** (color roles, state layers, elevation levels). Ghi rõ vi phạm chuẩn nào.
13. Mỗi hardcoded color/spacing/font-size KHÔNG qua CSS variable = **1 finding**. Dự án dùng design tokens 3 tầng — vi phạm = phá system.
14. Dark mode: mỗi component/page KHÔNG có `.dark` override cho màu foreground/background quan trọng = **1 finding**.

---

## KẾT THÚC PROMPT
