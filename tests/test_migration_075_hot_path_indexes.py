"""Guard cho migration 075 (NỢ 4): index đường nóng + trần thời gian phiên.

§B4 — một thay đổi schema = một test. Test này là guard TĨNH (không cần PG): nó
kiểm chuỗi migration còn hợp lệ, tên index không đụng nhau, cột được index có thật,
và giữ lại ràng buộc đắt nhất của đợt này — phần THỰC THI của 075 không được xây
index kiểu concurrent, vì runner chạy cả chuỗi trong một transaction.

Mọi khẳng định "không chứa X" đều chạy trên SQL ĐÃ BÓC COMMENT: bản thân 075 giải
thích trong comment vì sao không dùng cách đó, nên so chuỗi trên nguyên file sẽ bắt
nhầm chính lời giải thích.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "agent" / "migrations"
MIGRATION_NAME = "075_hot_path_indexes_and_session_timeouts.sql"
MIGRATION = MIGRATIONS / MIGRATION_NAME
SQL = MIGRATION.read_text(encoding="utf-8")
INIT_SQL = (ROOT / "init.sql").read_text(encoding="utf-8")

RUNNER_FILENAME_RE = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")

# (index, bảng, cột dẫn đầu) — cột dẫn đầu quyết định index có dùng được hay không.
EXPECTED_INDEXES = [
    ("idx_likes_post_created", "likes", "post_id"),
    ("idx_bookmarks_post", "bookmarks", "post_id"),
    ("idx_blocks_blocked", "blocks", "blocked_id"),
    ("idx_comments_parent", "comments", "parent_id"),
    ("idx_posts_pinned_comment", "posts", "pinned_comment_id"),
    ("idx_user_mutes_muted", "user_mutes", "muted_id"),
]


def _strip_comments(sql: str) -> str:
    return "\n".join(line.split("--")[0] for line in sql.splitlines())


EXEC_SQL = _strip_comments(SQL)


def _load_script(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _schema_corpus() -> str:
    parts = [INIT_SQL]
    parts += [p.read_text(encoding="utf-8") for p in sorted(MIGRATIONS.glob("*.sql"))]
    return "\n".join(parts)


def _column_is_declared(corpus: str, table: str, column: str) -> bool:
    """Cột có trong CREATE TABLE <table>(...) hoặc được ALTER TABLE <table> thêm vào."""
    for block in re.findall(
        rf"CREATE TABLE IF NOT EXISTS {table}\s*\((.*?)\n\);", corpus, re.S
    ):
        if re.search(rf"^\s*{column}\s", block, re.M):
            return True
    return bool(
        re.search(
            rf"ALTER TABLE (?:IF EXISTS )?{table}\s+ADD COLUMN(?: IF NOT EXISTS)? {column}\b",
            corpus,
        )
    )


def test_075_filename_matches_runner_convention_and_chain_has_no_gap():
    assert MIGRATION.exists()
    match = RUNNER_FILENAME_RE.fullmatch(MIGRATION_NAME)
    assert match, f"{MIGRATION_NAME} không khớp quy ước ^\\d{{3}}_[a-z0-9_]+\\.sql$"
    assert int(match.group(1)) == 75

    prefixes = sorted(
        int(RUNNER_FILENAME_RE.fullmatch(path.name).group(1))
        for path in MIGRATIONS.glob("*.sql")
        if RUNNER_FILENAME_RE.fullmatch(path.name)
    )
    assert len(prefixes) == len(set(prefixes)), f"trùng số thứ tự migration: {prefixes}"
    assert prefixes == list(range(prefixes[0], prefixes[-1] + 1)), "chuỗi migration đứt số"
    # KHÔNG khẳng định 075 là mới nhất nữa: hợp `codex/np1-identity-location-trust`
    # vào main thêm 076-078 (ba migration của nhánh đó, đánh số lại từ 071-073 vì
    # trunk đã dùng ba số ấy cho việc khác). Cái đáng khoá ở đây là chuỗi KHÔNG ĐỨT
    # SỐ và không trùng số — hai thứ đó mới làm runner chạy sai thứ tự.
    assert prefixes[-1] >= 75, "075 phải nằm trong chuỗi"


def test_075_records_schema_version_75_monotonically():
    assert f"VALUES ('agent', 75, '{MIGRATION_NAME}'" in EXEC_SQL
    assert "GREATEST(schema_version.version, EXCLUDED.version)" in EXEC_SQL


def test_075_creates_every_expected_index_with_the_right_leading_column():
    assert EXEC_SQL.count("CREATE INDEX IF NOT EXISTS") == len(EXPECTED_INDEXES)
    for index_name, table, column in EXPECTED_INDEXES:
        assert EXEC_SQL.count(index_name) == 1, f"{index_name} phải xuất hiện đúng 1 lần"
        statement = re.search(
            rf"CREATE INDEX IF NOT EXISTS {index_name}\s+ON\s+(\w+)\(([^)]*)\)", EXEC_SQL
        )
        assert statement, f"thiếu CREATE INDEX IF NOT EXISTS {index_name}"
        assert statement.group(1) == table
        assert statement.group(2).split(",")[0].strip() == column, (
            f"{index_name} phải dẫn đầu bằng {column} thì mới dùng được"
        )


def test_075_index_names_do_not_collide_with_existing_schema():
    """Trùng tên ⇒ IF NOT EXISTS im lặng bỏ qua và index mới không bao giờ ra đời."""
    declared = re.findall(
        r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF NOT EXISTS\s+)?(\w+)", _schema_corpus()
    )
    for index_name, _table, _column in EXPECTED_INDEXES:
        assert declared.count(index_name) == 1, (
            f"{index_name} đã được khai báo ở nơi khác — đổi tên hoặc bỏ khỏi 075"
        )


def test_075_indexes_reference_columns_that_actually_exist():
    corpus = _schema_corpus()
    for index_name, table, column in EXPECTED_INDEXES:
        assert _column_is_declared(corpus, table, column), (
            f"{index_name}: không tìm thấy khai báo cột {table}.{column} trong schema"
        )


def test_075_avoids_concurrent_index_build_because_runner_is_transactional():
    """Xây index kiểu concurrent không chạy được trong transaction block.

    Runner mở transaction (psycopg2 để autocommit=False) và chỉ commit một lần ở
    cuối, nên cách đó sẽ làm hỏng cả chuỗi. Giữ hai vế cạnh nhau để ai "tối ưu"
    sau này thấy ngay vì sao không được.
    """
    forbidden = "CONCURRENT" + "LY"
    assert forbidden not in EXEC_SQL.upper()

    runner_source = (ROOT / "scripts" / "apply_migrations.py").read_text(encoding="utf-8")
    assert "with psycopg2.connect(database_url" in runner_source
    assert "conn.commit()" in runner_source
    assert "autocommit" not in runner_source


def test_075_is_replay_safe_and_non_destructive():
    runner = _load_script("apply_migrations")
    runner.ensure_no_destructive_sql([MIGRATION])
    assert "IF NOT EXISTS" in EXEC_SQL
    assert "ON CONFLICT (component) DO UPDATE" in EXEC_SQL


def test_075_sets_session_timeouts_on_the_application_role_only_when_allowed():
    assert "ALTER ROLE %I SET statement_timeout" in EXEC_SQL
    assert "ALTER ROLE %I SET idle_in_transaction_session_timeout" in EXEC_SQL
    assert "app_role CONSTANT TEXT := 'vl360'" in EXEC_SQL
    # Không có role / không đủ quyền ⇒ cảnh báo, không làm hỏng chuỗi migration.
    assert "FROM pg_catalog.pg_roles WHERE rolname = app_role" in EXEC_SQL
    assert "rolsuper OR rolcreaterole" in EXEC_SQL
    assert EXEC_SQL.count("RAISE WARNING") == 2
    # lock_timeout ở tầng role làm DDL về sau thất bại ngẫu nhiên — cố ý không đặt.
    assert "lock_timeout" not in EXEC_SQL


def test_migration_gate_still_passes_after_075():
    """Cổng migration phải sạch, và số mới nhất phải khớp tên file mới nhất.

    Bản đầu ghim `latest == 075`; sau khi hợp NP-1 thì 078 mới là mới nhất. Ghim tên
    cứng làm test đỏ mỗi lần thêm migration vì một lý do vô nghĩa — nay suy ra từ
    chính thư mục, và vẫn khoá được điều thật sự quan trọng: gate không có lỗi, và
    `latest_schema_version` khớp với số trong TÊN file mới nhất (đúng cái bẫy đã sập
    một lần: đổi tên file mà quên đổi số bên trong file SQL).
    """
    gate = _load_script("check_migration_gate")
    issues, stats = gate.validate_static(MIGRATIONS)

    assert [issue for issue in issues if issue.severity == "error"] == []
    newest = max(
        (path for path in MIGRATIONS.glob("*.sql") if RUNNER_FILENAME_RE.fullmatch(path.name)),
        key=lambda path: int(RUNNER_FILENAME_RE.fullmatch(path.name).group(1)),
    )
    assert stats["latest"] == newest.name
    assert stats["latest_schema_version"] == int(RUNNER_FILENAME_RE.fullmatch(newest.name).group(1))
