"""Health-check Postgres phải phủ các bảng mà tính năng đã ship thực sự truy vấn.

`PG_REQUIRED_SCHEMA_VERSION` đã theo kịp migration (74), nhưng `PG_REQUIRED_TABLES`
thì không: nó dừng ở nhóm 059–062. Hệ quả là một DB thiếu bảng 2FA / trusted
devices / achievements vẫn PASS health-check, deploy được coi là thành công, rồi
ném `relation does not exist` ngay lần gọi đầu tới các tính năng đó — đúng vào
DEPLOY GATE 2FA đã ghi trong tài liệu dự án.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
AGENT = ROOT / "agent"
sys.path.insert(0, str(AGENT))


@pytest.fixture(scope="module")
def required_tables():
    from database import PG_REQUIRED_TABLES
    return set(PG_REQUIRED_TABLES)


@pytest.fixture(scope="module")
def migration_tables():
    created = {}
    for path in sorted(AGENT.glob("migrations/*.sql")):
        number = int(path.name.split("_", 1)[0])
        for match in re.finditer(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?([a-z_0-9]+)", path.read_text(encoding="utf-8"), re.I):
            created.setdefault(match.group(1).lower(), number)
    return created


# Bảng của tính năng đã ship và có truy vấn runtime trong agent/*.py.
SHIPPED_FEATURE_TABLES = [
    ("user_2fa", "auth.py — đăng nhập hai lớp"),
    ("pending_2fa", "auth.py — phiên chờ xác thực 2FA"),
    ("user_2fa_recovery_codes", "auth.py — mã khôi phục 2FA"),
    ("trusted_devices", "auth.py, erasure_state.py — thiết bị tin cậy"),
    ("user_achievements", "achievements.py — huy hiệu người dùng"),
    ("profile_views", "social.py — đếm lượt xem hồ sơ"),
]


@pytest.mark.parametrize("table,why", SHIPPED_FEATURE_TABLES)
def test_shipped_feature_table_is_gated_by_health_check(table, why, required_tables):
    assert table in required_tables, (
        f"'{table}' ({why}) do migration tạo và được code truy vấn, nhưng không nằm trong "
        "PG_REQUIRED_TABLES — DB thiếu bảng này vẫn PASS health-check rồi vỡ lúc chạy thật"
    )


@pytest.mark.parametrize("table,_why", SHIPPED_FEATURE_TABLES)
def test_gated_table_is_actually_created_by_a_migration(table, _why, migration_tables):
    """Chiều ngược lại: không được yêu cầu bảng mà migration không hề tạo."""
    assert table in migration_tables, (
        f"'{table}' bị yêu cầu nhưng không migration nào tạo — health-check sẽ chặn deploy oan"
    )


def test_every_required_table_is_created_by_a_migration_within_the_gate(required_tables, migration_tables):
    from database import PG_REQUIRED_SCHEMA_VERSION

    too_new = {
        table: migration_tables[table]
        for table in required_tables
        if table in migration_tables and migration_tables[table] > PG_REQUIRED_SCHEMA_VERSION
    }
    assert too_new == {}, (
        "Bảng bị yêu cầu nhưng chỉ được tạo bởi migration cao hơn ngưỡng schema đang gác: "
        f"{too_new} > {PG_REQUIRED_SCHEMA_VERSION}"
    )
