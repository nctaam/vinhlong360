"""Cổng kiểm tính toàn vẹn của chỉ mục bằng chứng drill.

`artifacts/runtime-drills/index.json` tự khai `schema_version: 1` nhưng suốt một
thời gian KHÔNG có schema, KHÔNG có validator, KHÔNG có script sinh ra nó. Chỉ
mục không ai soi chính là chỗ bằng chứng trôi: một đường dẫn không còn tồn tại,
một `scope` lặng lẽ nới sang "staging", hai mục bằng chứng thực ra là cùng một
tài liệu đếm hai lần, hay một thư mục drill thất bại nằm im trên đĩa mà không
mục nào ghi nhận.

Test dựng chỉ mục giả trong `tmp_path` để hermetic, cộng một test không-hermetic
ghim rằng chỉ mục THẬT hiện đang sạch.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "ops" / "validate_drill_index.py"


def _load() -> ModuleType:
    assert VALIDATOR.is_file(), "validate_drill_index.py chưa được tạo"
    spec = importlib.util.spec_from_file_location("validate_drill_index", VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_index(root: Path, entries: list[dict], **overrides) -> Path:
    drills = root / "artifacts" / "runtime-drills"
    drills.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        # Xa về tương lai để mtime của evidence không kích hoạt luật lệch giờ.
        "generated_at": "2099-01-01T00:00:00Z",
        "scope": "LOCAL_ONLY",
        "launch_verdict": "NO_GO",
        "entries": entries,
    }
    payload.update(overrides)
    path = drills / "index.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _evidence(root: Path, rel: str, body: str = "{}") -> str:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return rel


def _good_entry(root: Path) -> dict:
    return {
        "id": "ok-drill",
        "status": "PASS_LIMITED",
        "scope": "LOCAL_DISPOSABLE_REHEARSAL_ONLY",
        "evidence": [_evidence(root, "artifacts/runtime-drills/ok/receipt.json")],
        "limitations": ["Disposable local run only."],
    }


def test_a_well_formed_index_validates(tmp_path: Path) -> None:
    module = _load()
    _write_index(tmp_path, [_good_entry(tmp_path)])
    assert module.validate(tmp_path)["problems"] == []


def test_missing_evidence_path_fails(tmp_path: Path) -> None:
    module = _load()
    entry = _good_entry(tmp_path)
    entry["evidence"] = ["artifacts/runtime-drills/ok/does-not-exist.json"]
    _write_index(tmp_path, [entry])
    problems = module.validate(tmp_path)["problems"]
    assert any("does not exist" in p for p in problems), problems


def test_executed_entry_without_scope_fails(tmp_path: Path) -> None:
    """Ghim đúng khoảng trống của ba mục UNAVAILABLE để nó không lặng lẽ quay lại."""
    module = _load()
    entry = _good_entry(tmp_path)
    del entry["scope"]
    _write_index(tmp_path, [entry])
    problems = module.validate(tmp_path)["problems"]
    assert any("no scope" in p for p in problems), problems


def test_unavailable_entry_needs_no_scope_or_evidence(tmp_path: Path) -> None:
    """Drill chưa từng chạy thì không có gì để scope — đòi scope chỉ tổ đẻ ra chuỗi bịa."""
    module = _load()
    _write_index(
        tmp_path,
        [{"id": "ha-failover", "status": "UNAVAILABLE", "missing": ["second host"]}],
    )
    assert module.validate(tmp_path)["problems"] == []


@pytest.mark.parametrize(
    "scope",
    [
        "STAGING_REHEARSAL",
        "LOCAL_THEN_PRODUCTION",
        "LIVE_TRAFFIC_ONLY",
    ],
)
def test_scope_may_never_claim_beyond_local(tmp_path: Path, scope: str) -> None:
    module = _load()
    entry = _good_entry(tmp_path)
    entry["scope"] = scope
    _write_index(tmp_path, [entry])
    problems = module.validate(tmp_path)["problems"]
    assert problems, f"scope {scope!r} phải bị từ chối"


def test_same_document_listed_twice_fails(tmp_path: Path) -> None:
    """Ghim vụ closed-release.json bị đếm hai lần ở hai đường dẫn."""
    module = _load()
    entry = _good_entry(tmp_path)
    body = '{"closed": true}'
    entry["evidence"] = [
        _evidence(tmp_path, "artifacts/runtime-drills/ok/a/closed-release.json", body),
        _evidence(tmp_path, "artifacts/runtime-drills/ok/b/closed-release.json", body),
    ]
    _write_index(tmp_path, [entry])
    problems = module.validate(tmp_path)["problems"]
    assert any("same document" in p for p in problems), problems


def test_identical_before_after_pair_is_not_a_duplicate(tmp_path: Path) -> None:
    """Cặp before/after GIỐNG NHAU là bằng chứng bảo toàn, không phải trùng lặp.

    Luật trùng lặp phải khớp theo (tên file, digest), nếu chỉ theo digest thì nó
    báo động nhầm đúng vào hình dạng mà một phép chứng minh bảo toàn cần có.
    """
    module = _load()
    entry = _good_entry(tmp_path)
    body = '{"runtime.sqlite": {"sha256": "abc", "size": 7}}'
    entry["evidence"] = [
        _evidence(tmp_path, "artifacts/runtime-drills/ok/persistent-before.json", body),
        _evidence(tmp_path, "artifacts/runtime-drills/ok/persistent-after.json", body),
    ]
    _write_index(tmp_path, [entry])
    assert module.validate(tmp_path)["problems"] == []


def test_entry_without_any_stated_limit_fails(tmp_path: Path) -> None:
    module = _load()
    entry = _good_entry(tmp_path)
    del entry["limitations"]
    _write_index(tmp_path, [entry])
    problems = module.validate(tmp_path)["problems"]
    assert any("limitations/missing/reason" in p for p in problems), problems


def test_unknown_status_fails(tmp_path: Path) -> None:
    module = _load()
    entry = _good_entry(tmp_path)
    entry["status"] = "MOSTLY_FINE"
    _write_index(tmp_path, [entry])
    problems = module.validate(tmp_path)["problems"]
    assert any("is not one of" in p for p in problems), problems


def test_unreferenced_drill_directory_is_reported(tmp_path: Path) -> None:
    """Thư mục drill không mục nào trỏ tới = một lần chạy không được ghi nhận."""
    module = _load()
    _write_index(tmp_path, [_good_entry(tmp_path)])
    (tmp_path / "artifacts" / "runtime-drills" / "rollback-orphan").mkdir(parents=True)
    report = module.validate(tmp_path)
    assert "rollback-orphan" in report["orphan_directories"]
    assert any("referenced by no entry" in p for p in report["problems"])


def test_evidence_newer_than_generated_at_is_reported(tmp_path: Path) -> None:
    """generated_at cũ hơn bằng chứng nó dẫn = chỉ mục đã ngừng mô tả lần chạy nó đặt tên."""
    module = _load()
    _write_index(tmp_path, [_good_entry(tmp_path)], generated_at="2000-01-01T00:00:00Z")
    problems = module.validate(tmp_path)["problems"]
    assert any("newer than the index generated_at" in p for p in problems), problems


def test_the_live_index_is_currently_clean() -> None:
    """Không hermetic có chủ đích: ghim rằng chỉ mục THẬT đang sạch.

    Nếu ai đó thêm một mục thiếu scope, trỏ vào đường dẫn chết, hay bỏ quên một
    thư mục drill, test này đỏ ngay — chứ không đợi tới lúc có người đọc lại
    chỉ mục bằng mắt.
    """
    module = _load()
    report = module.validate(ROOT)
    assert report["problems"] == [], report["problems"]
