# -*- coding: utf-8 -*-
"""Chuẩn: MỌI test dựng `Database(...)` phải GHIM backend tường minh.

## Lớp lỗi bị khoá ở đây

`agent/database.py:37-38` tính `DATABASE_URL` + `USE_PG` MỘT LẦN lúc import, và
`Database.__init__` (database.py:539-540) chỉ copy hai hằng đó:

    self._use_pg = USE_PG
    self._dsn = DATABASE_URL if USE_PG else None

Hệ quả phản trực giác:

1. `monkeypatch.delenv("DATABASE_URL")` lúc runtime KHÔNG đổi được backend — hằng
   module đã chốt từ lúc import.
2. Khi `USE_PG` là True, tham số `db_path=` bị **bỏ qua hoàn toàn**. Test tưởng
   mình đang chạy trên SQLite trong `tmp_path` nhưng thực ra nối vào Postgres dùng
   chung của CI.

Tổn thất đã đo được: `tests/test_export_data.py` gọi `replace_from_json` (tự mở cả
hai chốt `ALLOW_DESTRUCTIVE_DB_REPLACE` + `DESTRUCTIVE_OPS_LOCKED`) → `DELETE FROM
entities/relationships/itineraries` chạy 8 lần trên PG dùng chung, xoá 1746 entity,
12060 quan hệ, 33 lịch trình; mọi test chạy sau đó thấy `/api/entities` rỗng.

Test này không phát hiện được trên máy local (không có Postgres) — nó là rào AST
tĩnh nên có răng ở mọi môi trường.

## Rule

Với mỗi lời gọi dựng `Database(...)`, TRONG CÙNG phạm vi hàm/fixture phải có ít
nhất một "ghim backend" tường minh:

* `monkeypatch.setattr(database, "USE_PG", ...)`  — ghim TRƯỚC khi dựng, hoặc
* gán thẳng `obj._use_pg = ...`                    — ghim SAU khi dựng.

Ghim `True` cũng hợp lệ: điều bị cấm là **thừa hưởng ngầm** hằng module, không phải
việc dùng Postgres. Test PG chủ đích (`*_postgres.py`) đều đã ghim `_use_pg = True`
kèm `_dsn` riêng nên qua rule này.

Ngoại lệ hợp lệ thứ hai (cấp file): module tự vô hiệu hoá dưới Postgres bằng
`pytestmark = pytest.mark.skipif(db._use_pg, ...)` — không chạy thì không thể làm
bẩn. `tests/test_database_filters.py` dùng đường này.

ALLOWLIST đang RỖNG và nên giữ rỗng: gặp báo nhầm thì siết rule, đừng nới allowlist.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Thư mục test được quét. `scripts/tests` không nằm trong `testpaths` của pytest.ini
# nhưng vẫn chạy được bằng tay nên vẫn phải tuân chuẩn.
SCAN_ROOTS = ("tests", "agent/tests", "scripts/tests")

# {đường-dẫn-tương-đối: lý do}. Mỗi mục là một lỗ hổng đã biết — phải ghi lý do cụ
# thể, không được dùng để làm im tiếng chuông.
ALLOWLIST: dict[str, str] = {}


def _iter_test_files():
    for scan_root in SCAN_ROOTS:
        base = ROOT / scan_root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if path.name.startswith("test_") or path.name == "conftest.py":
                yield path


def _scope_map(tree: ast.Module) -> dict[int, ast.AST]:
    """node-id -> hàm bao gần nhất (hoặc chính Module nếu ở cấp module)."""
    mapping: dict[int, ast.AST] = {id(tree): tree}

    def walk(node: ast.AST, scope: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                mapping[id(child)] = scope
                walk(child, child)
            else:
                mapping[id(child)] = scope
                walk(child, scope)

    walk(tree, tree)
    return mapping


def _is_database_construction(node: ast.AST) -> bool:
    """`Database(...)` hoặc `<mod>.Database(...)` — KHÔNG khớp FakeDatabase/... ."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "Database"
    if isinstance(func, ast.Attribute):
        return func.attr == "Database"
    return False


def _is_backend_pin(node: ast.AST) -> bool:
    # (a) obj._use_pg = <bất kỳ>  — ghim tường minh sau khi dựng.
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Attribute) and target.attr == "_use_pg":
                return True
    # (b) monkeypatch.setattr(<mod>, "USE_PG", <...>) — ghim trước khi dựng.
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "setattr" and len(node.args) >= 2:
            second = node.args[1]
            if isinstance(second, ast.Constant) and second.value == "USE_PG":
                return True
    return False


def _has_module_level_pg_skip(tree: ast.Module) -> bool:
    """`pytestmark = pytest.mark.skipif(<... _use_pg ...>, ...)` ở cấp module."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "pytestmark"
            for target in node.targets
        ):
            continue
        marks = ast.walk(node.value)
        has_skipif = False
        references_use_pg = False
        for inner in marks:
            if isinstance(inner, ast.Attribute):
                if inner.attr == "skipif":
                    has_skipif = True
                if inner.attr == "_use_pg":
                    references_use_pg = True
        if has_skipif and references_use_pg:
            return True
    return False


def find_unpinned_database_constructions(source: str, label: str) -> list[str]:
    """Trả về danh sách vi phạm dạng `label:lineno`. Rỗng = đạt chuẩn."""
    tree = ast.parse(source)
    if _has_module_level_pg_skip(tree):
        return []

    scopes = _scope_map(tree)
    pinned_scopes = {
        id(scopes[id(node)]) for node in ast.walk(tree) if _is_backend_pin(node)
    }
    violations = []
    for node in ast.walk(tree):
        if not _is_database_construction(node):
            continue
        if id(scopes[id(node)]) not in pinned_scopes:
            violations.append(f"{label}:{node.lineno}")
    return violations


def test_every_test_database_construction_pins_the_backend():
    violations: list[str] = []
    scanned = 0
    for path in _iter_test_files():
        relative = path.relative_to(ROOT).as_posix()
        if relative in ALLOWLIST:
            continue
        scanned += 1
        violations.extend(
            find_unpinned_database_constructions(
                path.read_text(encoding="utf-8"), relative
            )
        )

    assert scanned > 0, "không quét được file test nào — SCAN_ROOTS sai?"
    assert not violations, (
        "Database(...) được dựng mà KHÔNG ghim backend — trên CI (có DATABASE_URL) "
        "db_path bị bỏ qua và test ghi thẳng vào Postgres dùng chung:\n  "
        + "\n  ".join(violations)
        + "\nCách vá (khuôn: agent/tests/conftest.py::isolated_sqlite_db):\n"
        '  monkeypatch.setattr(database, "USE_PG", False)\n'
        '  monkeypatch.setattr(database, "DATABASE_URL", "")\n'
        "  d = database.Database(db_path=str(tmp_path / \"x.db\"))\n"
        "  assert d._use_pg is False and d._dsn is None"
    )


def test_allowlist_entries_are_real_files_with_a_reason():
    for relative, reason in ALLOWLIST.items():
        assert (ROOT / relative).is_file(), f"allowlist trỏ vào file không tồn tại: {relative}"
        assert reason.strip(), f"allowlist thiếu lý do: {relative}"


# ── Self-test: chứng minh rule có răng, không phụ thuộc file thật ──

_UNPINNED = """
def test_bad(tmp_path):
    db = Database(str(tmp_path / "x.db"))
    db.upsert_entity({"id": "e"})
"""

_PINNED_VIA_MONKEYPATCH = """
def test_good(tmp_path, monkeypatch):
    import database
    monkeypatch.setattr(database, "USE_PG", False)
    d = database.Database(db_path=str(tmp_path / "x.db"))
"""

_PINNED_VIA_ATTRIBUTE = """
def test_good(tmp_path):
    d = Database(db_path=str(tmp_path / "x.db"))
    d._use_pg = False
    d._dsn = None
"""

_PINNED_TO_PG_ON_PURPOSE = """
def pg_db():
    adapter = database_module.Database()
    adapter._use_pg = True
    adapter._dsn = TEST_DATABASE_URL
    return adapter
"""

_MODULE_LEVEL_PG_SKIP = """
pytestmark = pytest.mark.skipif(db._use_pg, reason="SQLite-file-isolation")


def _make_db(tmp_path):
    return Database(str(tmp_path / "filters.db"))
"""

_PIN_IN_A_DIFFERENT_FUNCTION = """
def other(d):
    d._use_pg = False


def test_bad(tmp_path):
    db = Database(str(tmp_path / "x.db"))
"""

_NOT_THE_REAL_CLASS = """
def test_ok():
    db = FakeDatabase()
    other = LifecycleDatabase()
"""


def test_rule_flags_unpinned_construction():
    assert find_unpinned_database_constructions(_UNPINNED, "synthetic.py") == [
        "synthetic.py:3"
    ]


def test_rule_flags_pin_that_lives_in_another_function():
    assert find_unpinned_database_constructions(
        _PIN_IN_A_DIFFERENT_FUNCTION, "synthetic.py"
    ) == ["synthetic.py:7"]


@pytest.mark.parametrize(
    "source",
    [
        _PINNED_VIA_MONKEYPATCH,
        _PINNED_VIA_ATTRIBUTE,
        _PINNED_TO_PG_ON_PURPOSE,
        _MODULE_LEVEL_PG_SKIP,
        _NOT_THE_REAL_CLASS,
    ],
)
def test_rule_accepts_every_legitimate_isolation_shape(source):
    assert find_unpinned_database_constructions(source, "synthetic.py") == []
