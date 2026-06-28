# SESSION SCOPE: Backend API — branch `session-be`

> **Session song song 2/3.** CHỈ sửa file trong `agent/`. KHÔNG sửa `web-nuxt/`, `scripts/`, `docs/`, `web/`.
> Sau khi xong, session gốc sẽ merge + deploy. KHÔNG tự push/merge.

---

## 0. Bối cảnh

MXH du lịch/OCOP/cộng đồng cho Vĩnh Long mới (VL+BT+TV). Solo dev, budget <1tr/th.
Backend FastAPI (`agent/`), DB SQLite (knowledge) + Postgres (UGC/auth).
Kiến trúc: `docs/architecture-decisions.md`, `docs/stabilization-plan.md`.

## 1. Giới hạn file (TUYỆT ĐỐI — vi phạm = hỏng merge)

**ĐƯỢC sửa:**
- `agent/*.py` (server.py, admin.py, auth.py, social.py, database.py, public_api.py, knowledge.py, seo.py, notifications.py, guardrails.py, etc.)
- `agent/tests/**`
- `agent/data/eval/**` (eval test cases)
- `agent/prompts/**`

**KHÔNG ĐƯỢC sửa:**
- `web-nuxt/**` — session frontend phụ trách
- `scripts/**`, `docs/**`, `tests/**` — session khác
- `web/data.json` — KHÔNG SỬA (nếu cần thao tác data → chạy backup trước, §B1)
- `agent/data/*.db`, `agent/data/embeddings.json` — file binary/gitignored
- File root: `CLAUDE.md` gốc, `.env.example`, `docker-compose.yml`

## 2. Bất biến

- **B1.** `python scripts/backup_data.py` trước MỌI thao tác dữ liệu
- **B3.** Module 0% test phải có test TRƯỚC khi refactor
- **B4.** Thay đổi schema = phải có test
- **B5.** Mỗi commit: `python -m pytest -q` PHẢI xanh
- **B7.** Không chạy `database.py --replace`, `/reload`, `/admin/data-quality/apply` ngoài roadmap
- **B8.** Không thêm dịch vụ trả phí, không nới cap LLM
- UGC/auth = Postgres-only. SQLite endpoint UGC → 503.
- KHÔNG tự sinh dữ liệu (địa chỉ/SĐT/mùa vụ) — chỉ dùng nguồn thật

## 3. Commit

- Branch: `session-be` (đã checkout)
- Format: `[BE] <mô tả ngắn>`
- Commit nhỏ, 1 feature/fix = 1 commit
- **KHÔNG push, KHÔNG merge vào main**

## 4. Verify mỗi commit

```powershell
cd C:\Code\vinhlong360\vl360-session-be
python -m pytest -q
# Smoke test server (không gọi LLM):
$env:BUILD_SEARCH_INDEXES='false'; $env:BACKGROUND_INDEX_BUILD='false'; $env:SCHEDULER_ENABLED='false'; python agent/server.py
```

## 5. Danh sách task (làm theo thứ tự)

### Nhóm 1: Security & Auth hardening (ưu tiên cao nhất)
- [ ] **BE-1** Password change yêu cầu password cũ — `auth.py` hiện cho đổi password mà không verify password cũ. Fix: check `current_password` trước khi SET.
- [ ] **BE-2** Session management API — `GET /auth/sessions` (list device/IP/time), `DELETE /auth/sessions/{id}` (revoke). Badge "current session".
- [ ] **BE-3** Account deactivation — `POST /auth/deactivate` set `is_active=FALSE` + revoke all sessions. Reactivate tự động khi OTP login lại.
- [ ] **BE-4** Login history — log mỗi login/OTP (success/fail, IP, UA) vào bảng mới. `GET /auth/login-history`.

### Nhóm 2: Block enforcement & Privacy
- [ ] **BE-5** Full block enforcement — filter blocked users trong: comments, user search, leaderboard, suggested-follows, entity feed. Auto-unfollow khi block. Skip notification cho blocked. Profile trả limited info khi bị block.
- [ ] **BE-6** Blocked users list — `GET /api/blocked-users` + unblock endpoint.
- [ ] **BE-7** Privacy settings — JSONB column (profile_visibility, show_activity, show_saved), CRUD + enforcement trong `get_user_profile`.

### Nhóm 3: Admin API improvements
- [ ] **BE-8** Dashboard alerts endpoint — `GET /admin/dashboard-alerts` scan tất cả queue (moderation, unclassified, images missing), sort by urgency. Dynamic thay 2 alert cứng.
- [ ] **BE-9** Activity feed — `GET /admin/activity-feed` 10 admin actions gần nhất từ audit JSONL.
- [ ] **BE-10** Entity completeness score — `GET /admin/completeness` % entities có summary+images+placeId+source.
- [ ] **BE-11** Audit log rotation — auto-archive JSONL khi >10MB, giữ 5000 entries mới nhất.
- [ ] **BE-12** Batch moderation — `POST /admin/moderation/batch` {post_ids, action, reason}. Xử lý nhiều post cùng lúc.

### Nhóm 4: API optimization
- [ ] **BE-13** Orphan entity detection — `GET /admin/orphans` entities không có relationship nào.
- [ ] **BE-14** Bulk relationship add — `POST /admin/relationships/bulk` cho admin.
- [ ] **BE-15** Entity change history — diff trước khi update entity, lưu vào entity_changes. `GET /admin/entity-history/{id}`.

### Nhóm 5: Image & Media pipeline (GĐ8 backend — KHÔNG cần R2 account)
> Ghi chú: GĐ8.1 (R2 config) cần Track-H (tài khoản). Nhưng các endpoint upload/resize
> có thể code + test với **local filesystem** trước, chuyển sang R2 sau bằng config.

- [ ] **BE-16** Avatar upload — `POST /auth/avatar`: nhận file, resize WebP (400px) bằng Pillow, lưu local `agent/data/uploads/avatars/`, cập nhật `users.avatar_url`. Test: upload → URL trả về → ảnh lấy được.
- [ ] **BE-17** Entity image upload — `POST /admin/entity/{id}/image`: admin upload ảnh cho entity, WebP 3 cỡ (400/800/1600), strip EXIF, ghi vào `entity["images"]`. Guard `require_admin()`.
- [ ] **BE-18** SEO og:image — sửa `seo.py`: `og:image` default toàn site + override per-entity nếu có image. Nâng `image` → `ImageObject` (license) ở JSON-LD.

### Nhóm 6: Cross-cutting endpoints (FE session sẽ consume)
- [ ] **BE-19** Consent timestamp — PG migration `consent_log` (user_id, version, timestamp, ip). Ghi khi user tick consent ở OTP flow. `GET /auth/consent-history`.
- [ ] **BE-20** SSE notification stream — `GET /api/notifications/stream` (EventSource). In-memory `asyncio.Queue` per user. Không cần Redis ở scale <10k.
- [ ] **BE-21** Notification preferences — PG table `notification_preferences` (user_id, prefs JSONB). `GET/PUT /api/notification-preferences`. Gate trong `create_notification`: skip nếu user tắt type đó.

### Nhóm 7: Test coverage mở rộng
- [ ] **BE-22** Test cho mọi endpoint mới (BE-1 → BE-21).
- [ ] **BE-23** Test block enforcement (BE-5): blocked user không thấy posts/comments, không nhận notification.
- [ ] **BE-24** Test privacy settings (BE-7): private profile trả limited info.
- [ ] **BE-25** Test avatar upload (BE-16): upload → resize → URL valid.
- [ ] **BE-26** Test consent logging (BE-19): tick consent → record trong DB.

## 6. Lưu ý kỹ thuật

- Postgres migration: dùng `information_schema.columns` check trước `ALTER TABLE` (xem `database.py:206-217` cho pattern).
- SQLite migration: dùng try/except `sqlite3.OperationalError` cho `ALTER TABLE`.
- Admin endpoints: đặt trong `admin.py`, guard bằng `require_admin()`.
- Auth endpoints: đặt trong `auth.py`, guard bằng `get_current_user()`.
- Social endpoints: đặt trong `social.py`.
- UGC endpoint trên SQLite → trả 503 rõ ràng (`_require_pg` pattern).
- Tất cả endpoint mới cần test trong `agent/tests/`.
