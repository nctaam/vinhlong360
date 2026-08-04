"""Mọi biến môi trường mang bí mật hoặc mở khoá thao tác nguy hiểm phải có trong .env.example.

Người dựng môi trường mới đọc `.env.example` để biết cần cấp gì. Biến thiếu ở đó
thất bại âm thầm: pipeline ảnh AI không chạy, object storage không ghi được, và
nguy hiểm nhất là TOTP_ENC_KEY — bật 2FA khi chưa đặt khoá này thì người dùng bị
khoá ra ngoài vĩnh viễn.

Test chỉ đòi TÊN biến được liệt kê (dạng comment cũng được), không đòi giá trị.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
AGENT = ROOT / "agent"

SENSITIVE_MARKERS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "_ENC", "ALLOW_DESTRUCTIVE")

ENV_READ_RE = re.compile(
    r"""os\.(?:environ\.get|getenv)\(\s*["']([A-Z][A-Z0-9_]+)["']|os\.environ\[\s*["']([A-Z][A-Z0-9_]+)["']"""
)


def _env_vars_read_by_production_code() -> set[str]:
    found: set[str] = set()
    for path in AGENT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        for a, b in ENV_READ_RE.findall(path.read_text(encoding="utf-8", errors="replace")):
            found.add(a or b)
    return found


def _documented_env_vars() -> set[str]:
    text = (ROOT / ".env.example").read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", text, re.M))


def _sensitive(name: str) -> bool:
    return any(marker in name for marker in SENSITIVE_MARKERS)


@pytest.fixture(scope="module")
def undocumented_sensitive():
    return sorted(v for v in _env_vars_read_by_production_code() - _documented_env_vars() if _sensitive(v))


def test_no_undocumented_secret_env_var(undocumented_sensitive):
    assert undocumented_sensitive == [], (
        "Biến bí mật được code đọc nhưng .env.example không nhắc tới: "
        f"{undocumented_sensitive}. Thêm tên biến (không kèm giá trị) kèm một dòng "
        "giải thích hậu quả khi thiếu."
    )


def test_totp_key_is_documented_because_it_is_a_deploy_gate():
    """Tách riêng vì đây là biến duy nhất mà đặt sai gây mất quyền truy cập không hồi phục."""
    assert "TOTP_ENC_KEY" in _documented_env_vars()
