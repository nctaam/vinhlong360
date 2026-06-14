"""Public listing phải quarantine entity provisional/auto-learned (không show công khai)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))

from public_api import _is_public


def test_provisional_and_unverified_excluded():
    assert _is_public({"status": "provisional"}) is False
    assert _is_public({"verified": False}) is False
    assert _is_public({"status": "provisional", "verified": True}) is False


def test_verified_and_legacy_included():
    # Entity verified rõ ràng
    assert _is_public({"status": "verified", "verified": True}) is True
    # Entity từ data.json (không có field status/verified) → coi là public (không loại nhầm)
    assert _is_public({}) is True
    assert _is_public({"name": "Chợ Vĩnh Long"}) is True
    assert _is_public({"verified": True}) is True
