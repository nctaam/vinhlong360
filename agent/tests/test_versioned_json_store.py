import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from versioned_json_store import mutate_json


def test_mutation_leaves_no_adjacent_lock_or_temp_artifacts(tmp_path):
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps({"count": 0}), encoding="utf-8")

    result = mutate_json(data_path, lambda data: (True, data.update(count=1) or "saved"))

    assert result == "saved"
    assert json.loads(data_path.read_text(encoding="utf-8")) == {"count": 1}
    assert list(tmp_path.glob(".data.json.*.tmp")) == []
    assert not (tmp_path / ".data.json.lock").exists()


def test_failed_mutation_releases_lock_without_write_artifacts(tmp_path):
    data_path = tmp_path / "data.json"
    data_path.write_text(json.dumps({"count": 0}), encoding="utf-8")

    def fail(_data):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        mutate_json(data_path, fail)

    result = mutate_json(data_path, lambda data: (True, data.update(count=1) or "recovered"))

    assert result == "recovered"
    assert json.loads(data_path.read_text(encoding="utf-8")) == {"count": 1}
    assert list(tmp_path.glob(".data.json.*.tmp")) == []
    assert not (tmp_path / ".data.json.lock").exists()
