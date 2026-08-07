"""Hợp đồng thật của PUT/DELETE /api/comments/{id} — quyền của người dùng với
bình luận của chính họ.

Vì sao có file này: hai endpoint `edit_comment` (agent/social.py:2464) và
`delete_comment` (agent/social.py:2508) có rate-limit, có CSRF, có kiểm quyền,
nhưng frontend chưa từng gọi (grep `/api/comments/` trong web-nuxt/ ra 0 hit).
Trước khi nối nút "Sửa"/"Xoá" lên giao diện phải chứng minh backend thật sự
chặn người-không-phải-tác-giả — nối UI lên một lỗ hổng còn tệ hơn không nối.

Không có assert nào nhìn vào source: mọi kiểm tra gọi endpoint thật qua
TestClient rồi soi status code + trạng thái DB sau đó.

Chạy được khi máy không có Postgres bằng cách nào: social.py là Postgres-only
(CLAUDE.md §1.3) nên test dựng test double `_PgLite` ở TẦNG TRUY VẤN, cùng cách
tests/test_auth_behavior.py đã làm — nhận đúng câu SQL mà social.py phát ra, chỉ
dịch cú pháp riêng của Postgres (NOW(), ::uuid, ::text) rồi thi hành trên SQLite
in-memory. Logic quyền, cửa sổ sửa 24h, soft-delete chạy nguyên vẹn.

Cột của double lấy ĐÚNG từ DDL sản xuất (init.sql + agent/migrations/*.sql) và
`TestDoubleTrungThuc` khoá điều đó lại. Không có Postgres trong test thì DDL LÀ
nguồn duy nhất nói được "cột nào có thật" — double bịa thêm cột là tự tay giấu
đi đúng loại lỗi mà file này phải bắt.

Không phủ được, và cố ý KHÔNG giả xanh: trigger `trg_comment_count` (migration
070) recount comment_count trên UPDATE deleted_at. SQLite double không có
trigger đó nên file này KHÔNG assert comment_count — nhánh ấy cần Postgres thật.
"""
from __future__ import annotations

import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth
import auth_middleware
import social

pytestmark = pytest.mark.integration

_TS_FMT = "%Y-%m-%dT%H:%M:%S.%f+00:00"
_UUID_DEFAULT = (
    "(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' ||"
    " substr(lower(hex(randomblob(2))),2) || '-a' || substr(lower(hex(randomblob(2))),2)"
    " || '-' || lower(hex(randomblob(6))))"
)
_NOW_DEFAULT = "(strftime('%Y-%m-%dT%H:%M:%f','now') || '000+00:00')"


def _ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(_TS_FMT)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────────────────────────────────
#  Schema của double — cột lấy đúng theo DDL sản xuất, không thêm không bớt
# ──────────────────────────────────────────────────────────────────────────

_SCHEMA = f"""
CREATE TABLE users (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    phone TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    display_name TEXT,
    full_name TEXT,
    avatar_url TEXT,
    username TEXT,
    role TEXT DEFAULT 'user',
    is_active INTEGER DEFAULT 1,
    deleted_at TEXT,
    created_at TEXT DEFAULT {_NOW_DEFAULT},
    updated_at TEXT DEFAULT {_NOW_DEFAULT}
);
CREATE TABLE user_sessions (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    user_id TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    user_agent TEXT,
    ip_address TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT DEFAULT {_NOW_DEFAULT}
);
CREATE TABLE posts (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    user_id TEXT NOT NULL,
    entity_id TEXT,
    content TEXT NOT NULL,
    post_type TEXT DEFAULT 'share',
    moderation_status TEXT DEFAULT 'pending',
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    deleted_at TEXT,
    created_at TEXT DEFAULT {_NOW_DEFAULT},
    updated_at TEXT DEFAULT {_NOW_DEFAULT}
);
-- comments: KHÔNG có updated_at. init.sql:224 không khai, và không migration nào
-- ADD COLUMN updated_at cho bảng này (008 mentions, 034 like_count, 068
-- deleted_at là toàn bộ danh sách). TestDoubleTrungThuc canh điều đó.
CREATE TABLE comments (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    post_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    parent_id TEXT,
    content TEXT NOT NULL,
    moderation_status TEXT DEFAULT 'approved',
    mentions TEXT DEFAULT '[]',
    like_count INTEGER DEFAULT 0,
    deleted_at TEXT,
    created_at TEXT DEFAULT {_NOW_DEFAULT}
);
CREATE TABLE notifications (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    ref_type TEXT,
    ref_id TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT {_NOW_DEFAULT}
);
CREATE TABLE blocks (
    blocker_id TEXT NOT NULL,
    blocked_id TEXT NOT NULL,
    created_at TEXT DEFAULT {_NOW_DEFAULT},
    PRIMARY KEY (blocker_id, blocked_id)
);
CREATE TABLE user_mutes (
    id TEXT PRIMARY KEY DEFAULT {_UUID_DEFAULT},
    user_id TEXT NOT NULL,
    muted_id TEXT NOT NULL,
    created_at TEXT DEFAULT {_NOW_DEFAULT}
);
"""

_REPO_ROOT = Path(__file__).resolve().parents[1]

_CREATE_TABLE_RE = re.compile(
    r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)\s*\((.*?)\n\s*\);", re.S | re.I
)
_ADD_COLUMN_RE = re.compile(
    r"ALTER TABLE (?:IF EXISTS )?(\w+)\s+ADD COLUMN (?:IF NOT EXISTS )?(\w+)", re.I
)
_NOT_A_COLUMN = {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT", "EXCLUDE", "LIKE"}


def _columns_from_ddl(text: str) -> dict[str, set[str]]:
    tables: dict[str, set[str]] = {}
    for name, bodyaaa in _CREATE_TABLE_RE.findall(text):
        cols = tables.setdefault(name.lower(), set())
        for line in bodyaaa.splitlines():
            line = line.strip().rstrip(",")
            if not line or line.startswith("--"):
                continue
            first = line.split()[0]
            if first.upper() in _NOT_A_COLUMN:
                continue
            cols.add(first.lower())
    for name, col in _ADD_COLUMN_RE.findall(text):
        tables.setdefault(name.lower(), set()).add(col.lower())
    return tables


def _prod_columns() -> dict[str, set[str]]:
    """Cột thật của Postgres, đọc từ DDL sản xuất: init.sql + agent/migrations/*.sql."""
    tables: dict[str, set[str]] = {}
    files = [_REPO_ROOT / "init.sql"] + sorted((_REPO_ROOT / "agent" / "migrations").glob("*.sql"))
    for path in files:
        if not path.exists():
            continue
        for name, cols in _columns_from_ddl(path.read_text(encoding="utf-8", errors="replace")).items():
            tables.setdefault(name, set()).update(cols)
    return tables


# ──────────────────────────────────────────────────────────────────────────
#  Dịch phương ngữ Postgres → SQLite (chỉ cú pháp, không đụng ý nghĩa)
# ──────────────────────────────────────────────────────────────────────────

_CAST_RE = re.compile(r"::(uuid|text|bigint|int|jsonb)", re.IGNORECASE)
_FOR_UPDATE_RE = re.compile(r"\s+FOR\s+UPDATE(\s+SKIP\s+LOCKED)?", re.IGNORECASE)
_ISO_PARAM_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}")


def _translate(sql: str) -> str:
    out = re.sub(r"NOW\(\)", "'" + _ts(_now()) + "'", sql, flags=re.IGNORECASE)
    out = _CAST_RE.sub("", out)
    out = _FOR_UPDATE_RE.sub("", out)
    if re.search(r"\bOFFSET\b", out, re.IGNORECASE) and not re.search(r"\bLIMIT\b", out, re.IGNORECASE):
        out = re.sub(r"\bOFFSET\b", "LIMIT -1 OFFSET", out, flags=re.IGNORECASE)
    return out.replace("%s", "?")


def _norm_params(params):
    if params is None:
        return ()
    out = []
    for p in params:
        if isinstance(p, datetime):
            out.append(_ts(p))
        elif isinstance(p, bool):
            out.append(1 if p else 0)
        elif isinstance(p, str) and _ISO_PARAM_RE.match(p):
            try:
                out.append(_ts(datetime.fromisoformat(p)))
            except ValueError:
                out.append(p)
        else:
            out.append(p)
    return tuple(out)


class _PgLite:
    """DB double cho social.py — cùng bề mặt với Database (_conn/_execute/...)."""

    _use_pg = True

    def __init__(self):
        self._sql = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
        self._sql.row_factory = sqlite3.Row
        self._sql.executescript(_SCHEMA)
        self._lock = threading.RLock()

    def initialize(self):
        return None

    @property
    def _ph(self) -> str:
        return "%s"

    @contextmanager
    def _conn(self, *, commit_on_success: bool = True):
        with self._lock:
            yield self._sql

    def _execute(self, conn, sql, params=None):
        return conn.execute(_translate(sql), _norm_params(params))

    def _fetchone(self, conn, sql, params=None):
        return self._execute(conn, sql, params).fetchone()

    def _fetchall(self, conn, sql, params=None):
        return self._execute(conn, sql, params).fetchall()

    def _row_to_dict(self, row):
        return None if row is None else dict(row)

    def raw(self, sql, params=()):
        with self._lock:
            return [dict(r) for r in self._sql.execute(sql, params).fetchall()]

    def write(self, sql, params=()):
        with self._lock:
            self._sql.execute(sql, params)

    def columns(self, table: str) -> set[str]:
        return {r["name"] for r in self.raw(f"PRAGMA table_info({table})")}


# ──────────────────────────────────────────────────────────────────────────
#  Fixtures
# ──────────────────────────────────────────────────────────────────────────

class _Api:
    """Bọc TestClient: mỗi request tự quyết định mang token/CSRF nào."""

    def __init__(self, client: TestClient, db: _PgLite):
        self.client = client
        self.db = db
        self._seq = 0

    def call(self, method, path, *, token=None, csrf=True, **kw):
        headers = dict(kw.pop("headers", None) or {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
            if csrf:
                headers["X-CSRF-Token"] = auth_middleware.generate_csrf_token(token)
        return self.client.request(method, path, headers=headers, **kw)

    def get(self, path, **kw):
        return self.call("GET", path, **kw)

    def put(self, path, **kw):
        return self.call("PUT", path, **kw)

    def delete(self, path, **kw):
        return self.call("DELETE", path, **kw)

    # ── dựng dữ liệu ──

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}-0000-4000-a000-{self._seq:012d}"

    def add_user(self, *, display_name="Người dùng", role="user"):
        uid = self._next_id("11111111")
        self._seq_phone = getattr(self, "_seq_phone", 900000000) + 1
        self.db.write(
            "INSERT INTO users (id, phone, display_name, role) VALUES (?, ?, ?, ?)",
            (uid, f"0{self._seq_phone}", display_name, role),
        )
        token = auth._generate_token()
        self.db.write(
            "INSERT INTO user_sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
            (uid, auth._hash_token(token), _ts(_now() + timedelta(days=30))),
        )
        return {"id": uid, "token": token, "display_name": display_name}

    def add_post(self, author_id):
        pid = self._next_id("22222222")
        self.db.write(
            "INSERT INTO posts (id, user_id, content, moderation_status) VALUES (?, ?, ?, 'approved')",
            (pid, author_id, "Bài viết thử ở Vĩnh Long"),
        )
        return pid

    def add_comment(self, post_id, author_id, content="Bình luận gốc", *, parent_id=None, age=timedelta(0)):
        cid = self._next_id("33333333")
        self.db.write(
            "INSERT INTO comments (id, post_id, user_id, parent_id, content, moderation_status, created_at)"
            " VALUES (?, ?, ?, ?, ?, 'approved', ?)",
            (cid, post_id, author_id, parent_id, content, _ts(_now() - age)),
        )
        return cid

    def comment_row(self, comment_id):
        rows = self.db.raw("SELECT * FROM comments WHERE id = ?", (comment_id,))
        return rows[0] if rows else None


@pytest.fixture
def api(monkeypatch):
    fake = _PgLite()
    monkeypatch.setattr(social, "db", fake)
    monkeypatch.setattr(auth, "db", fake)
    monkeypatch.setattr(auth_middleware, "db", fake)

    # Kiểm duyệt nội dung nằm ngoài phạm vi file này: chặn ở biên, mặc định duyệt.
    async def _approve(content, **kwargs):
        return {"status": "approved", "score": 0.0, "reasons": []}

    monkeypatch.setattr(social, "moderate_content_enhanced", _approve)

    import ratelimit
    ratelimit._reset()

    app = FastAPI()
    app.include_router(social.router)
    with TestClient(app) as client:
        yield _Api(client, fake)
    ratelimit._reset()


# ──────────────────────────────────────────────────────────────────────────
#  Double phải trung thực trước đã
# ──────────────────────────────────────────────────────────────────────────

class TestDoubleTrungThuc:
    """Nếu double bịa cột thì mọi test dưới đều vô nghĩa — kiểm nó trước."""

    @pytest.mark.parametrize(
        "table", ["users", "user_sessions", "posts", "comments", "notifications", "blocks", "user_mutes"]
    )
    def test_double_khong_bia_cot_ngoai_prod(self, api, table):
        prod = _prod_columns().get(table, set())
        assert prod, f"Không đọc được DDL sản xuất cho bảng {table}"
        thua = api.db.columns(table) - prod
        assert not thua, (
            f"Double khai cột không có trên Postgres cho {table}: {sorted(thua)}. "
            "Sửa double, đừng sửa assert — cột bịa sẽ giấu đúng loại lỗi file này phải bắt."
        )

    def test_comments_khong_co_cot_updated_at_tren_prod(self):
        """Neo sự thật schema mà bug PUT /api/comments/{id} phụ thuộc vào."""
        assert "updated_at" not in _prod_columns()["comments"]

    def test_phien_dang_nhap_cua_double_dung_duoc(self, api):
        u = api.add_user()
        post = api.add_post(u["id"])
        resp = api.get(f"/api/posts/{post}/comments", token=u["token"])
        assert resp.status_code == 200, resp.text


# ──────────────────────────────────────────────────────────────────────────
#  DELETE /api/comments/{id}
# ──────────────────────────────────────────────────────────────────────────

class TestXoaBinhLuan:

    def test_tac_gia_xoa_duoc_binh_luan_cua_minh(self, api):
        tac_gia = api.add_user(display_name="Tác giả")
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"])

        resp = api.delete(f"/api/comments/{cid}", token=tac_gia["token"])

        assert resp.status_code == 200, resp.text
        assert resp.json() == {"success": True}
        assert api.comment_row(cid)["deleted_at"] is not None

    def test_nguoi_khac_KHONG_xoa_duoc(self, api):
        tac_gia = api.add_user(display_name="Tác giả")
        nguoi_la = api.add_user(display_name="Người lạ")
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"])

        resp = api.delete(f"/api/comments/{cid}", token=nguoi_la["token"])

        assert resp.status_code == 403, resp.text
        assert api.comment_row(cid)["deleted_at"] is None

    def test_khach_chua_dang_nhap_bi_401(self, api):
        tac_gia = api.add_user()
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"])

        resp = api.delete(f"/api/comments/{cid}")

        assert resp.status_code == 401
        assert api.comment_row(cid)["deleted_at"] is None

    def test_thieu_csrf_bi_403(self, api):
        tac_gia = api.add_user()
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"])

        resp = api.delete(f"/api/comments/{cid}", token=tac_gia["token"], csrf=False)

        assert resp.status_code == 403
        assert api.comment_row(cid)["deleted_at"] is None

    def test_admin_xoa_duoc_binh_luan_nguoi_khac(self, api):
        tac_gia = api.add_user()
        admin = api.add_user(display_name="Quản trị", role="admin")
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"])

        resp = api.delete(f"/api/comments/{cid}", token=admin["token"])

        assert resp.status_code == 200, resp.text
        assert api.comment_row(cid)["deleted_at"] is not None

    def test_soft_delete_khong_xoa_vinh_vien_va_keo_theo_reply_con(self, api):
        """Backend soft-delete: hàng vẫn còn (recoverable), reply con cũng bị ẩn."""
        tac_gia = api.add_user()
        nguoi_tra_loi = api.add_user(display_name="Người trả lời")
        post = api.add_post(tac_gia["id"])
        goc = api.add_comment(post, tac_gia["id"], "Bình luận gốc")
        con = api.add_comment(post, nguoi_tra_loi["id"], "Trả lời", parent_id=goc)

        assert api.delete(f"/api/comments/{goc}", token=tac_gia["token"]).status_code == 200

        assert api.comment_row(goc) is not None, "soft-delete phải giữ hàng lại"
        assert api.comment_row(goc)["content"] == "Bình luận gốc"
        assert api.comment_row(con)["deleted_at"] is not None, "reply con phải bị ẩn theo"

    def test_binh_luan_da_xoa_bien_khoi_danh_sach(self, api):
        tac_gia = api.add_user()
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"])

        truoc = api.get(f"/api/posts/{post}/comments").json()["comments"]
        assert [c["id"] for c in truoc] == [cid]

        api.delete(f"/api/comments/{cid}", token=tac_gia["token"])

        sau = api.get(f"/api/posts/{post}/comments").json()["comments"]
        assert sau == []

    def test_xoa_lai_lan_hai_tra_404(self, api):
        tac_gia = api.add_user()
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"])

        assert api.delete(f"/api/comments/{cid}", token=tac_gia["token"]).status_code == 200
        assert api.delete(f"/api/comments/{cid}", token=tac_gia["token"]).status_code == 404

    def test_binh_luan_khong_ton_tai_tra_404(self, api):
        u = api.add_user()
        resp = api.delete("/api/comments/99999999-0000-4000-a000-000000000000", token=u["token"])
        assert resp.status_code == 404


# ──────────────────────────────────────────────────────────────────────────
#  PUT /api/comments/{id}
# ──────────────────────────────────────────────────────────────────────────

class TestSuaBinhLuan:

    def test_tac_gia_sua_duoc_binh_luan_cua_minh(self, api):
        tac_gia = api.add_user(display_name="Tác giả")
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"], "Nội dung cũ")

        resp = api.put(f"/api/comments/{cid}", token=tac_gia["token"],
                       json={"content": "Nội dung mới ở Vĩnh Long"})

        assert resp.status_code == 200, resp.text
        assert resp.json()["comment"]["content"] == "Nội dung mới ở Vĩnh Long"
        assert api.comment_row(cid)["content"] == "Nội dung mới ở Vĩnh Long"

    def test_nguoi_khac_KHONG_sua_duoc(self, api):
        tac_gia = api.add_user()
        nguoi_la = api.add_user(display_name="Người lạ")
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"], "Nội dung cũ")

        resp = api.put(f"/api/comments/{cid}", token=nguoi_la["token"],
                       json={"content": "Bị người lạ sửa"})

        assert resp.status_code == 403, resp.text
        assert api.comment_row(cid)["content"] == "Nội dung cũ"

    def test_admin_cung_KHONG_sua_duoc_binh_luan_nguoi_khac(self, api):
        """Sửa khắt khe hơn xoá: admin xoá được, nhưng KHÔNG mạo danh nội dung."""
        tac_gia = api.add_user()
        admin = api.add_user(display_name="Quản trị", role="admin")
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"], "Nội dung cũ")

        resp = api.put(f"/api/comments/{cid}", token=admin["token"],
                       json={"content": "Admin sửa hộ"})

        assert resp.status_code == 403, resp.text
        assert api.comment_row(cid)["content"] == "Nội dung cũ"

    def test_khach_chua_dang_nhap_bi_401(self, api):
        tac_gia = api.add_user()
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"], "Nội dung cũ")

        resp = api.put(f"/api/comments/{cid}", json={"content": "Khách sửa"})

        assert resp.status_code == 401
        assert api.comment_row(cid)["content"] == "Nội dung cũ"

    def test_thieu_csrf_bi_403(self, api):
        tac_gia = api.add_user()
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"], "Nội dung cũ")

        resp = api.put(f"/api/comments/{cid}", token=tac_gia["token"], csrf=False,
                       json={"content": "Sửa không CSRF"})

        assert resp.status_code == 403
        assert api.comment_row(cid)["content"] == "Nội dung cũ"

    def test_qua_cua_so_24h_thi_tu_choi(self, api):
        tac_gia = api.add_user()
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"], "Nội dung cũ", age=timedelta(hours=25))

        resp = api.put(f"/api/comments/{cid}", token=tac_gia["token"],
                       json={"content": "Sửa muộn"})

        assert resp.status_code == 400, resp.text
        assert api.comment_row(cid)["content"] == "Nội dung cũ"

    def test_binh_luan_da_xoa_khong_sua_duoc(self, api):
        tac_gia = api.add_user()
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"], "Nội dung cũ")
        api.delete(f"/api/comments/{cid}", token=tac_gia["token"])

        resp = api.put(f"/api/comments/{cid}", token=tac_gia["token"],
                       json={"content": "Sửa sau khi xoá"})

        assert resp.status_code == 404

    def test_noi_dung_qua_ngan_bi_tu_choi(self, api):
        tac_gia = api.add_user()
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"], "Nội dung cũ")

        resp = api.put(f"/api/comments/{cid}", token=tac_gia["token"], json={"content": "x"})

        assert resp.status_code == 422
        assert api.comment_row(cid)["content"] == "Nội dung cũ"

    def test_sua_thanh_cho_duyet_thi_bien_khoi_danh_sach(self, api, monkeypatch):
        """Hợp đồng FE phải biết: kiểm duyệt trả 'pending' → bình luận tự ẩn."""
        tac_gia = api.add_user()
        post = api.add_post(tac_gia["id"])
        cid = api.add_comment(post, tac_gia["id"], "Nội dung cũ")

        async def _pending(content, **kwargs):
            return {"status": "pending", "score": 0.5, "reasons": ["test"]}

        monkeypatch.setattr(social, "moderate_content_enhanced", _pending)

        resp = api.put(f"/api/comments/{cid}", token=tac_gia["token"],
                       json={"content": "Nội dung cần duyệt lại"})

        assert resp.status_code == 200, resp.text
        assert api.comment_row(cid)["moderation_status"] == "pending"
        assert api.get(f"/api/posts/{post}/comments").json()["comments"] == []
