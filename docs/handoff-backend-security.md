# Session 6: Backend Security — Auth/Moderation Hardening

> Paste toàn bộ nội dung này làm message đầu tiên.

## Bối cảnh

Worktree `C:/Code/vl360-backend-sec`, nhánh `dev/backend-security`. Dự án vinhlong360. **Đọc `CLAUDE.md` + `docs/PARALLEL-BRANCHES.md`.**

## Phạm vi file SỞ HỮU

- `agent/auth_middleware.py` — Request auth middleware
- `agent/middleware.py` — General middleware
- `agent/moderation.py` — Content moderation
- `agent/ratelimit.py` — Rate limiting
- `agent/tests/test_p0_security_hardening.py` — Security tests (đã có 43 tests)
- `agent/tests/test_auth*.py` — Auth tests (thêm mới)

**KHÔNG SỬA:** `auth.py` (thuộc usercp), `social.py`, `admin.py`, `server.py`, `database.py`, FE files.

## Công việc

### Đã xong (đợt trước):
- P0-1/3/4: Token hashing, login rate-limit, comment moderation
- Local spam pattern detection (moderation.py)
- 43 test cases cho security hardening

### Audit tiếp:
- T7: CSRF protection, session fixation prevention
- T7: Input validation audit — tất cả endpoint nhận user input
- T7: Rate limit coverage — endpoint nào chưa có rate limit?
- T7: Auth bypass audit — mọi endpoint protected đúng chưa?
- T10: Security logging — failed auth attempts, suspicious patterns

**Lưu ý:**
- Backend KHÔNG có LLM access trong test → mock LLM calls
- Giữ behavior hiện tại — chỉ thêm guard/validation/logging, không đổi logic
- Mọi thay đổi phải backward-compatible

## Verify

```bash
python -m pytest -q
python -m pytest agent/tests/test_p0_security_hardening.py -v
```

## Commit prefix: `[backend-security]`
