# Account and Control-Plane Security Implementation Plan

> STATUS: active

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent lower-privilege administrators from banning peer/superior accounts and prevent authentication authorized before password recovery from creating a post-reset session.

**Architecture:** Add one fail-closed role-rank guard in `agent/admin.py`, use locked validation-before-mutation for single and bulk bans, and add password-hash snapshot checks at challenge/session creation in `agent/auth.py`. Password reset uses one locked transaction to update the credential and revoke sessions plus pending 2FA challenges; no schema migration is required.

**Tech Stack:** Python 3.14, FastAPI, PostgreSQL transaction semantics, pytest, Ruff.

---

## File Map

- Create `agent/tests/test_account_control_plane_security.py`: focused behavioral regressions for role hierarchy, zero-side-effect denial, all-or-nothing bulk behavior, password snapshot checks, and reset ordering.
- Modify `agent/admin.py`: canonical role ranks, shared actor-target guard, locked single-ban flow, and two-pass locked bulk-ban flow.
- Modify `agent/auth.py`: locked credential snapshot helper, guarded challenge/session creation, legacy-rehash snapshot refresh, and atomic password-reset helper.
- Modify `docs/superpowers/specs/2026-07-13-account-control-plane-design.md`: final implementation evidence and verified status.
- Modify `docs/superpowers/plans/2026-07-12-security-remediation-30-60-90.md`: close Workstream 4 only after every verification gate passes.

## Task 1: Canonical Administrative Role Policy

**Files:**
- Create: `agent/tests/test_account_control_plane_security.py`
- Modify: `agent/admin.py:92-96`

- [ ] **Step 1: Write the failing role-matrix tests**

Create the focused test file with the shared imports, IDs, request helper, and role-policy tests:

```python
import asyncio
import inspect
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import admin
import auth


ADMIN_ID = "00000000-0000-0000-0000-000000000001"
PEER_ID = "00000000-0000-0000-0000-000000000002"
SUPER_ID = "00000000-0000-0000-0000-000000000003"
USER_ID = "00000000-0000-0000-0000-000000000004"


def _request(actor):
    return SimpleNamespace(state=SimpleNamespace(admin_user=actor))


@pytest.mark.parametrize(
    ("actor_role", "target_role"),
    [
        ("moderator", "user"),
        ("admin", "moderator"),
        ("admin", "user"),
        ("superadmin", "admin"),
        ("superadmin", "moderator"),
        ("superadmin", "user"),
    ],
)
def test_actor_can_manage_only_lower_roles(actor_role, target_role):
    admin._assert_actor_can_manage_target({"role": actor_role}, target_role)


@pytest.mark.parametrize(
    ("actor_role", "target_role"),
    [
        ("user", "user"),
        ("moderator", "moderator"),
        ("admin", "admin"),
        ("admin", "superadmin"),
        ("superadmin", "superadmin"),
        ("unknown", "user"),
        ("admin", "unknown"),
        ("", "user"),
    ],
)
def test_actor_cannot_manage_equal_higher_or_unknown_roles(actor_role, target_role):
    with pytest.raises(HTTPException) as exc:
        admin._assert_actor_can_manage_target({"role": actor_role}, target_role)
    assert exc.value.status_code == 403


def test_admin_key_can_manage_superadmin():
    admin._assert_actor_can_manage_target(None, "superadmin")
```

- [ ] **Step 2: Run the role-policy tests to verify RED**

Run:

```powershell
python -m pytest agent/tests/test_account_control_plane_security.py -q
```

Expected: collection succeeds and the tests fail with `AttributeError: module 'admin' has no attribute '_assert_actor_can_manage_target'`.

- [ ] **Step 3: Implement the minimal canonical guard**

Add immediately after `ADMIN_ROLE_SCOPES` in `agent/admin.py`:

```python
ADMIN_ROLE_RANKS: dict[str, int] = {
    "user": 0,
    "moderator": 1,
    "admin": 2,
    "superadmin": 3,
}


def _assert_actor_can_manage_target(admin_user: dict | None, target_role: str | None) -> None:
    """Allow account control only when a session actor strictly outranks the target."""
    if admin_user is None:
        return
    actor_role = str(admin_user.get("role") or "")
    normalized_target = str(target_role or "")
    actor_rank = ADMIN_ROLE_RANKS.get(actor_role)
    target_rank = ADMIN_ROLE_RANKS.get(normalized_target)
    if actor_rank is None or target_rank is None or actor_rank <= target_rank:
        raise HTTPException(403, "Khong du quyen thao tac tai khoan nay")
```

- [ ] **Step 4: Run the role-policy tests to verify GREEN**

Run:

```powershell
python -m pytest agent/tests/test_account_control_plane_security.py -q
```

Expected: `15 passed`.

- [ ] **Step 5: Commit the role policy**

```powershell
git add agent/admin.py agent/tests/test_account_control_plane_security.py
git commit -m "fix(admin): centralize account role hierarchy"
```

## Task 2: Transactional Single-User Ban

**Files:**
- Modify: `agent/tests/test_account_control_plane_security.py`
- Modify: `agent/admin.py:4840-4863`

- [ ] **Step 1: Add a recording admin database and failing single-ban tests**

Append to the focused test file:

```python
class _AdminDB:
    _ph = "%s"

    def __init__(self, users):
        self.users = {uid: dict(row) for uid, row in users.items()}
        self.fetches = []
        self.executes = []

    @contextmanager
    def _conn(self):
        yield object()

    def _fetchone(self, _conn, sql, params=()):
        self.fetches.append((sql, params))
        if "FROM users" in sql:
            return self.users.get(str(params[0]))
        return None

    def _execute(self, _conn, sql, params=()):
        self.executes.append((sql, params))

    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row else None


def _install_admin_db(monkeypatch, users):
    fake = _AdminDB(users)
    monkeypatch.setattr(admin, "db", fake)
    monkeypatch.setattr(admin, "require_pg", lambda: None)
    return fake


@pytest.mark.parametrize("target_role", ["admin", "superadmin"])
def test_single_ban_denies_peer_or_superior_without_side_effects(monkeypatch, target_role):
    fake = _install_admin_db(
        monkeypatch,
        {SUPER_ID: {"id": SUPER_ID, "role": target_role, "is_active": True}},
    )
    logs = []
    monkeypatch.setattr(admin, "_log_mod_action", lambda *args: logs.append(args))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(admin.ban_user(SUPER_ID, _request({"id": ADMIN_ID, "role": "admin"})))

    assert exc.value.status_code == 403
    assert fake.executes == []
    assert logs == []
    assert any("FOR UPDATE" in sql for sql, _ in fake.fetches)


@pytest.mark.parametrize(
    ("actor", "target_role"),
    [
        ({"id": ADMIN_ID, "role": "superadmin"}, "admin"),
        (None, "superadmin"),
    ],
)
def test_single_ban_allows_superior_or_admin_key(monkeypatch, actor, target_role):
    fake = _install_admin_db(
        monkeypatch,
        {SUPER_ID: {"id": SUPER_ID, "role": target_role, "is_active": True}},
    )
    logs = []
    monkeypatch.setattr(admin, "_log_mod_action", lambda *args: logs.append(args))

    result = asyncio.run(admin.ban_user(SUPER_ID, _request(actor)))

    assert result == {"success": True}
    assert any("UPDATE users SET is_active = FALSE" in sql for sql, _ in fake.executes)
    assert any("DELETE FROM user_sessions" in sql for sql, _ in fake.executes)
    assert len(logs) == 1
```

- [ ] **Step 2: Run the single-ban tests to verify RED**

Run:

```powershell
python -m pytest agent/tests/test_account_control_plane_security.py -q -k "single_ban"
```

Expected: denial tests fail because `ban_user` neither selects `role` nor calls the shared hierarchy guard.

- [ ] **Step 3: Replace the single-ban handler with locked authorization-before-mutation**

Implement this flow in `agent/admin.py`:

```python
async def ban_user(user_id: str, request: Request):
    require_pg()
    user_id = validate_path_id(user_id, "user_id")
    admin_user = getattr(request.state, "admin_user", None)
    if admin_user and str(admin_user.get("id")) == user_id:
        raise HTTPException(400, "Khong the tu ban chinh minh")

    def _query():
        ph = db._ph
        with db._conn() as conn:
            target = db._fetchone(conn, f"""
                SELECT id, is_active, role FROM users
                WHERE id::text = {ph} FOR UPDATE
            """, (user_id,))
            if not target:
                raise HTTPException(404, "Khong tim thay nguoi dung")
            target_data = db._row_to_dict(target)
            _assert_actor_can_manage_target(admin_user, target_data.get("role"))
            db._execute(conn, f"UPDATE users SET is_active = FALSE WHERE id::text = {ph}", (user_id,))
            db._execute(conn, f"DELETE FROM user_sessions WHERE user_id = {ph}::uuid", (user_id,))

    await asyncio.to_thread(_query)
    _log_mod_action("user", user_id, "ban")
    return {"success": True}
```

Keep the repository's existing Vietnamese response strings if they differ only by encoding; do not change the public error meaning.

- [ ] **Step 4: Run focused and owning single-ban regressions**

Run:

```powershell
python -m pytest agent/tests/test_account_control_plane_security.py agent/tests/test_session_be.py agent/tests/test_upgrade_round2.py -q -k "single_ban or ban_user or Phase8BanHardening or Phase11AdminHardening"
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit the single-ban boundary**

```powershell
git add agent/admin.py agent/tests/test_account_control_plane_security.py
git commit -m "fix(admin): enforce hierarchy before single ban"
```

## Task 3: All-or-Nothing Bulk Ban

**Files:**
- Modify: `agent/tests/test_account_control_plane_security.py`
- Modify: `agent/admin.py:4889-4921`

- [ ] **Step 1: Add failing mixed-target and ordering tests**

Append:

```python
def test_bulk_ban_rejects_mixed_superior_batch_without_any_write(monkeypatch):
    fake = _install_admin_db(
        monkeypatch,
        {
            USER_ID: {"id": USER_ID, "role": "user", "is_active": True},
            SUPER_ID: {"id": SUPER_ID, "role": "superadmin", "is_active": True},
        },
    )
    logs = []
    monkeypatch.setattr(admin, "_log_mod_action", lambda *args: logs.append(args))

    body = admin.BulkUserAction(user_ids=[USER_ID, SUPER_ID], reason="security")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(admin.bulk_ban_users(body, _request({"id": ADMIN_ID, "role": "admin"})))

    assert exc.value.status_code == 403
    assert fake.executes == []
    assert logs == []


def test_bulk_ban_deduplicates_skips_missing_and_preserves_response_order(monkeypatch):
    fake = _install_admin_db(
        monkeypatch,
        {
            USER_ID: {"id": USER_ID, "role": "user", "is_active": True},
            PEER_ID: {"id": PEER_ID, "role": "moderator", "is_active": True},
        },
    )
    monkeypatch.setattr(admin, "_log_mod_action", lambda *_args: None)
    missing = "00000000-0000-0000-0000-000000000099"
    body = admin.BulkUserAction(user_ids=[PEER_ID, missing, USER_ID, PEER_ID])

    result = asyncio.run(
        admin.bulk_ban_users(body, _request({"id": ADMIN_ID, "role": "admin"}))
    )

    assert result["banned_ids"] == [PEER_ID, USER_ID]
    assert result["banned_count"] == 2
    first_write = next(i for i, (sql, _) in enumerate(fake.executes) if "UPDATE users" in sql)
    assert len(fake.fetches) == 3
    assert first_write == 0
    locked_ids = [str(params[0]) for sql, params in fake.fetches if "FOR UPDATE" in sql]
    assert locked_ids == sorted(set([PEER_ID, missing, USER_ID]))
```

- [ ] **Step 2: Run the bulk tests to verify RED**

Run:

```powershell
python -m pytest agent/tests/test_account_control_plane_security.py -q -k "bulk_ban"
```

Expected: mixed-target denial and deduplication tests fail against the current mutate-as-you-iterate loop.

- [ ] **Step 3: Implement deterministic two-pass bulk authorization**

Replace the body of `bulk_ban_users` after rate limiting with:

```python
    admin_user = getattr(request.state, "admin_user", None)
    admin_id = str(admin_user.get("id")) if admin_user else None
    ids = list(dict.fromkeys(validate_path_id(uid, "user_id") for uid in body.user_ids))
    if admin_id and admin_id in ids:
        raise HTTPException(400, "Khong the tu ban chinh minh")

    def _query():
        ph = db._ph
        targets = {}
        with db._conn() as conn:
            for uid in sorted(ids):
                row = db._fetchone(conn, f"""
                    SELECT id, is_active, role FROM users
                    WHERE id::text = {ph} FOR UPDATE
                """, (uid,))
                if row:
                    targets[uid] = db._row_to_dict(row)

            for uid in ids:
                target = targets.get(uid)
                if target:
                    _assert_actor_can_manage_target(admin_user, target.get("role"))

            banned = []
            for uid in ids:
                if uid not in targets:
                    continue
                db._execute(conn, f"UPDATE users SET is_active = FALSE WHERE id::text = {ph}", (uid,))
                db._execute(conn, f"DELETE FROM user_sessions WHERE user_id = {ph}::uuid", (uid,))
                banned.append(uid)
        return banned
```

Retain the existing post-transaction logging and response construction.

- [ ] **Step 4: Run focused and owning bulk-ban regressions**

Run:

```powershell
python -m pytest agent/tests/test_account_control_plane_security.py agent/tests/test_upgrade_round2.py -q -k "bulk_ban"
```

Expected: all selected tests pass with no partial writes.

- [ ] **Step 5: Commit the bulk boundary**

```powershell
git add agent/admin.py agent/tests/test_account_control_plane_security.py
git commit -m "fix(admin): make bulk bans hierarchy atomic"
```

## Task 4: Credential Snapshot Guards for Challenges and Sessions

**Files:**
- Modify: `agent/tests/test_account_control_plane_security.py`
- Modify: `agent/auth.py:243-257`
- Modify: `agent/auth.py:524-560`
- Modify: `agent/auth.py:739-743`
- Modify: `agent/auth.py:817-832`
- Modify: `agent/auth.py:1752-1761`

- [ ] **Step 1: Add failing stale-snapshot tests**

Append:

```python
class _AuthDB:
    _ph = "%s"

    def __init__(self, user):
        self.user = dict(user)
        self.pending = []
        self.sessions = []
        self.fetches = []
        self.executes = []

    @contextmanager
    def _conn(self):
        yield object()

    def _fetchone(self, _conn, sql, params=()):
        self.fetches.append((sql, params))
        if "FROM users" in sql:
            return dict(self.user)
        return None

    def _execute(self, _conn, sql, params=()):
        self.executes.append((sql, params))
        if "INSERT INTO pending_2fa" in sql:
            self.pending.append(params)
        if "INSERT INTO user_sessions" in sql:
            self.sessions.append(params)

    @staticmethod
    def _row_to_dict(row):
        return dict(row) if row else None


def test_pending_challenge_rejects_stale_password_snapshot(monkeypatch):
    fake = _AuthDB(
        {"id": USER_ID, "password_hash": "new-hash", "is_active": True, "deleted_at": None}
    )
    monkeypatch.setattr(auth, "db", fake)

    with pytest.raises(HTTPException) as exc:
        auth._create_pending_2fa(USER_ID, "127.0.0.1", "pytest", "old-hash")

    assert exc.value.status_code == 401
    assert fake.pending == []
    assert any("FOR UPDATE" in sql for sql, _ in fake.fetches)


def test_session_creation_rejects_stale_password_snapshot(monkeypatch):
    fake = _AuthDB(
        {"id": USER_ID, "password_hash": "new-hash", "is_active": True, "deleted_at": None}
    )
    monkeypatch.setattr(auth, "db", fake)

    with pytest.raises(HTTPException) as exc:
        auth._create_session_atomic(
            USER_ID, "token-hash", "pytest", "127.0.0.1", "2099-01-01T00:00:00+00:00", "old-hash"
        )

    assert exc.value.status_code == 401
    assert fake.sessions == []


def test_login_paths_forward_password_snapshot():
    assert "user.get(\"password_hash\")" in inspect.getsource(auth.verify_otp)
    assert "user.get(\"password_hash\")" in inspect.getsource(auth.login_password)
    assert "user.get(\"password_hash\")" in inspect.getsource(auth._finish_login)
```

- [ ] **Step 2: Run snapshot tests to verify RED**

Run:

```powershell
python -m pytest agent/tests/test_account_control_plane_security.py -q -k "snapshot or login_paths"
```

Expected: signature/wiring tests fail because challenge and session creation do not validate the authenticated password state.

- [ ] **Step 3: Add one locked snapshot assertion helper**

Add before `_create_session_atomic` in `agent/auth.py`:

```python
def _password_snapshot_matches(expected: str | None, current: str | None) -> bool:
    if expected is None or current is None:
        return expected is current
    return hmac.compare_digest(str(expected), str(current))


def _assert_current_auth_snapshot(conn, user_id: str, expected_password_hash: str | None) -> dict:
    row = db._fetchone(conn, f"""
        SELECT id, password_hash, is_active, deleted_at FROM users
        WHERE id::text = {db._ph} FOR UPDATE
    """, (user_id,))
    user = db._row_to_dict(row) if row else None
    if (
        not user
        or not user.get("is_active")
        or user.get("deleted_at") is not None
        or not _password_snapshot_matches(expected_password_hash, user.get("password_hash"))
    ):
        raise HTTPException(401, "Thong tin dang nhap da thay doi. Vui long dang nhap lai.")
    return user
```

- [ ] **Step 4: Guard session and challenge creation and wire all callers**

Change `_create_session_atomic` to accept `expected_password_hash` as its final argument and call `_assert_current_auth_snapshot` before the session insert:

```python
def _create_session_atomic(uid, token_hash, ua, ip, expires_iso, expected_password_hash):
    from auth_middleware import MAX_CONCURRENT_SESSIONS
    with db._conn() as conn:
        _assert_current_auth_snapshot(conn, uid, expected_password_hash)
        db._execute(conn, f"""
            INSERT INTO user_sessions (user_id, token, user_agent, ip_address, expires_at)
            VALUES ({db._ph}::uuid, {db._ph}, {db._ph}, {db._ph}, {db._ph})
        """, (uid, token_hash, ua, ip, expires_iso))
        db._execute(conn, f"""
            DELETE FROM user_sessions WHERE id IN (
                SELECT id FROM user_sessions
                WHERE user_id::text = {db._ph} AND expires_at > NOW()
                ORDER BY created_at DESC OFFSET {db._ph}
            )
        """, (uid, MAX_CONCURRENT_SESSIONS))
```

Pass `user.get("password_hash")` as the final argument from `_finish_login`.

Change `_create_pending_2fa` to:

```python
def _create_pending_2fa(user_id: str, ip: str, ua: str, expected_password_hash: str | None) -> str:
    raw = _generate_token()
    expires = datetime.now(timezone.utc) + timedelta(minutes=PENDING_2FA_EXPIRE_MINUTES)
    with db._conn() as conn:
        _assert_current_auth_snapshot(conn, user_id, expected_password_hash)
        db._execute(conn, f"""
            INSERT INTO pending_2fa (user_id, token_hash, ip, user_agent, expires_at)
            VALUES ({db._ph}::uuid, {db._ph}, {db._ph}, {db._ph}, {db._ph})
        """, (user_id, _hash_token(raw), ip, ua[:500], expires.isoformat()))
    return raw
```

Pass `user.get("password_hash")` from both `verify_otp` and `login_password`. After legacy password rehash succeeds, refresh the local snapshot:

```python
        await asyncio.to_thread(_rehash)
        user = dict(user)
        user["password_hash"] = new_hash
```

- [ ] **Step 5: Run auth snapshot and existing session/2FA tests**

Run:

```powershell
python -m pytest agent/tests/test_account_control_plane_security.py agent/tests/test_wave4.py agent/tests/test_wave3.py agent/tests/test_session_be.py -q -k "snapshot or login_paths or pending_2fa or twofa or session or legacy"
```

Expected: all selected tests pass; existing atomic challenge consumption remains green.

- [ ] **Step 6: Commit credential snapshot guards**

```powershell
git add agent/auth.py agent/tests/test_account_control_plane_security.py
git commit -m "fix(auth): bind challenges and sessions to credential state"
```

## Task 5: Atomic Password Reset Revocation

**Files:**
- Modify: `agent/tests/test_account_control_plane_security.py`
- Modify: `agent/auth.py:873-916`

- [ ] **Step 1: Add failing reset transaction and serial-order tests**

Extend `_AuthDB._execute` in the focused test so it updates in-memory state:

```python
        if "UPDATE users SET password_hash" in sql:
            self.user["password_hash"] = params[0]
        if "DELETE FROM user_sessions" in sql:
            self.sessions.clear()
        if "DELETE FROM pending_2fa" in sql:
            self.pending.clear()
```

Append these tests:

```python
def test_reset_password_state_revokes_sessions_and_pending_challenges(monkeypatch):
    fake = _AuthDB(
        {
            "id": USER_ID,
            "phone": "0901234567",
            "password_hash": "old-hash",
            "is_active": True,
            "deleted_at": None,
        }
    )
    fake.sessions.append(("existing",))
    fake.pending.append(("existing",))
    monkeypatch.setattr(auth, "db", fake)
    monkeypatch.setattr(auth, "_consume_verified_otp", lambda *_args: None)
    monkeypatch.setattr(auth, "_hash_password", lambda _password: "new-hash")

    user = auth._reset_password_state("0901234567", "otp-hash", "NewPass1")

    assert user["id"] == USER_ID
    assert fake.user["password_hash"] == "new-hash"
    assert fake.sessions == []
    assert fake.pending == []
    statements = [sql for sql, _ in fake.executes]
    assert next(i for i, sql in enumerate(statements) if "UPDATE users" in sql) < next(
        i for i, sql in enumerate(statements) if "DELETE FROM pending_2fa" in sql
    )
    assert any("FOR UPDATE" in sql for sql, _ in fake.fetches)


def test_reset_then_old_challenge_and_session_are_rejected(monkeypatch):
    fake = _AuthDB(
        {
            "id": USER_ID,
            "phone": "0901234567",
            "password_hash": "old-hash",
            "is_active": True,
            "deleted_at": None,
        }
    )
    monkeypatch.setattr(auth, "db", fake)
    monkeypatch.setattr(auth, "_consume_verified_otp", lambda *_args: None)
    monkeypatch.setattr(auth, "_hash_password", lambda _password: "new-hash")
    auth._reset_password_state("0901234567", "otp-hash", "NewPass1")

    with pytest.raises(HTTPException):
        auth._create_pending_2fa(USER_ID, "127.0.0.1", "pytest", "old-hash")
    with pytest.raises(HTTPException):
        auth._create_session_atomic(
            USER_ID, "token", "pytest", "127.0.0.1", "2099-01-01T00:00:00+00:00", "old-hash"
        )
    assert fake.pending == []
    assert fake.sessions == []


def test_pre_reset_challenge_and_session_are_removed(monkeypatch):
    fake = _AuthDB(
        {
            "id": USER_ID,
            "phone": "0901234567",
            "password_hash": "old-hash",
            "is_active": True,
            "deleted_at": None,
        }
    )
    monkeypatch.setattr(auth, "db", fake)
    monkeypatch.setattr(auth, "_consume_verified_otp", lambda *_args: None)
    monkeypatch.setattr(auth, "_hash_password", lambda _password: "new-hash")
    auth._create_pending_2fa(USER_ID, "127.0.0.1", "pytest", "old-hash")
    auth._create_session_atomic(
        USER_ID, "token", "pytest", "127.0.0.1", "2099-01-01T00:00:00+00:00", "old-hash"
    )

    auth._reset_password_state("0901234567", "otp-hash", "NewPass1")

    assert fake.pending == []
    assert fake.sessions == []
```

Make `_AuthDB._fetchone` return the user for both `id::text` and `phone` user queries.

- [ ] **Step 2: Run reset tests to verify RED**

Run:

```powershell
python -m pytest agent/tests/test_account_control_plane_security.py -q -k "reset"
```

Expected: tests fail because `_reset_password_state` does not exist and reset does not delete `pending_2fa`.

- [ ] **Step 3: Extract the atomic reset helper**

Add before the reset endpoint:

```python
def _reset_password_state(phone: str, hashed_code: str, new_password: str) -> dict:
    with db._conn() as conn:
        _consume_verified_otp(conn, phone, hashed_code)
        row = db._fetchone(conn, f"""
            SELECT u.* FROM users u WHERE u.phone = {db._ph} FOR UPDATE
        """, (phone,))
        user = db._row_to_dict(row) if row else None
        if not user:
            raise HTTPException(404, "Khong tim thay tai khoan voi so dien thoai nay")
        pw_hash = _hash_password(new_password)
        uid = str(user["id"])
        db._execute(conn, f"UPDATE users SET password_hash = {db._ph} WHERE id::text = {db._ph}", (pw_hash, uid))
        db._execute(conn, f"DELETE FROM user_sessions WHERE user_id::text = {db._ph}", (uid,))
        db._execute(conn, f"DELETE FROM pending_2fa WHERE user_id::text = {db._ph}", (uid,))
        return user
```

Replace the nested `_verify_and_reset` function and call with:

```python
    user = await asyncio.to_thread(
        _reset_password_state, phone, hashed_code, body.new_password
    )
```

Leave login-history, streak, achievements, cookie clearing, and the response body in the endpoint unchanged.

- [ ] **Step 4: Run focused reset and auth regressions**

Run:

```powershell
python -m pytest agent/tests/test_account_control_plane_security.py agent/tests/test_upgrade_round2.py agent/tests/test_wave3.py agent/tests/test_wave4.py agent/tests/test_writepaths_auth.py -q -k "reset_password or reset or pending_2fa or session_creation"
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit atomic reset revocation**

```powershell
git add agent/auth.py agent/tests/test_account_control_plane_security.py
git commit -m "fix(auth): revoke pending challenges during reset"
```

## Task 6: Full Verification and Workstream Closure

**Files:**
- Modify: `docs/superpowers/specs/2026-07-13-account-control-plane-design.md`
- Modify: `docs/superpowers/plans/2026-07-12-security-remediation-30-60-90.md`

- [ ] **Step 1: Run the complete focused security suite**

```powershell
python -m pytest agent/tests/test_account_control_plane_security.py agent/tests/test_wave3.py agent/tests/test_wave4.py agent/tests/test_session_be.py agent/tests/test_upgrade_round2.py agent/tests/test_writepaths_auth.py agent/tests/test_wave3_security.py -q
```

Expected: all selected tests pass with only repository-known skips/warnings.

- [ ] **Step 2: Run static verification**

```powershell
python -m ruff check agent/admin.py agent/auth.py agent/tests/test_account_control_plane_security.py
python -m py_compile agent/admin.py agent/auth.py agent/tests/test_account_control_plane_security.py
git diff --check
```

Expected: Ruff reports `All checks passed!`; the remaining commands exit `0` without output.

- [ ] **Step 3: Run the full backend suite**

```powershell
python -m pytest -q
```

Expected baseline shape: at least `6102 passed, 39 skipped, 78 deselected, 1 xfailed`, with no new failure. Restore only `web/data.js` to `HEAD` if and only if the suite generates that known artifact and `git diff` proves no other unexpected change.

- [ ] **Step 4: Run an independent specification review**

Give the reviewer the approved design spec, this implementation plan, and the
complete Workstream 4 diff. Require a finding-first response that checks every
role, transaction, error, compatibility, and race invariant. Do not continue
while any Critical or Important specification mismatch remains open; fix the
finding and rerun Steps 1-3 before requesting a fresh review.

- [ ] **Step 5: Run an independent code-quality review**

Only after specification review passes, review the same final diff for logic
bugs, transaction misuse, deadlocks, stale-snapshot bypasses, test weakness,
and unrelated scope expansion. Do not continue while any Critical or Important
quality finding remains open; fix it and rerun Steps 1-4 before requesting a
fresh quality review.

- [ ] **Step 6: Update the design evidence**

Change the spec header to:

```markdown
> STATUS: implemented and verified
```

Append an `Implementation Evidence` section recording exact commit hashes, focused/full test counts, Ruff/compile/diff results, independent review results, and any verified residuals.

- [ ] **Step 7: Close Workstream 4 in the 30/60/90 roadmap**

Replace its unchecked bullets with checked evidence-backed bullets:

```markdown
- [x] Add RED tests for admin-to-superadmin single/bulk ban and pending 2FA after password reset.
- [x] Centralize actor-target role comparison and revoke all pending authentication challenges during reset.
- [x] Acceptance: denied hierarchy operations have zero target database/session side effects; pre-reset challenges cannot create sessions.
- [x] Completed on branch `codex/account-control-plane`; findings `REVIEW-01-005`, `REVIEW-01-006`, and `REVIEW-08-001` have regression-backed closure.
```

- [ ] **Step 8: Run documentation and final diff checks**

```powershell
rg -n "T[B]D|T[O]DO|F[I]XME|P[L]ACEHOLDER" docs/superpowers/specs/2026-07-13-account-control-plane-design.md docs/superpowers/plans/2026-07-13-account-control-plane.md
git diff --check
git status --short
```

Expected: placeholder search returns no matches, diff check exits `0`, and status lists only intended Workstream 4 files.

- [ ] **Step 9: Commit verified closure documentation**

```powershell
git add docs/superpowers/specs/2026-07-13-account-control-plane-design.md docs/superpowers/plans/2026-07-12-security-remediation-30-60-90.md
git commit -m "docs: close account control-plane workstream"
```

- [ ] **Step 10: Preserve the branch for user-directed integration**

Do not merge, push, deploy, rotate secrets, or modify production data. Report the clean branch HEAD, exact verification evidence, rollback statement, and any residual risk to the user.
