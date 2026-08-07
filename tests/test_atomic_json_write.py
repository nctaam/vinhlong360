"""Hop dong GHI NGUYEN TU cho 3 module agent tu-ghi-JSON.

Lo da do (2026-08-07) — ca ba ham `_atomic_write` cung mot than xac:

    tmp_path.write_text(content, encoding="utf-8")
    if path.exists():
        path.unlink()          # <-- file dich BIEN MAT o day
    tmp_path.rename(path)      # <-- crash/mat dien o day = mat trang

Ba khiem khuyet that:
  1. `unlink()` roi moi `rename()` — khe giua hai lenh la khe MAT FILE. Khong
     phai "con ban cu", ma la KHONG CON GI. `os.replace` lam viec nay bang MOT
     syscall nguyen tu tren ca POSIX lan Windows.
  2. Khong `flush()` + `os.fsync()` — noi dung con nam trong page cache khi
     rename da commit. Mat dien sau rename = ten file moi tro toi noi dung rong.
  3. Ten tmp co dinh `path.with_suffix(".tmp")` — hai writer cung mot dich dung
     CHUNG mot tmp, giam len nhau; mot ben co the rename tmp dang viet do dang.

Cac test duoi day do dung ba dieu do, khong do chi tiet cai dat: chung chan
BUOC COMMIT (`os.replace` / `os.rename` / `Path.rename`) nen ap dung cho bat ky
hien thuc nao.
"""

from __future__ import annotations

import json
import os
import pathlib
from pathlib import Path

import pytest

import dynamic_agents
import llm_judge
import self_optimizer

MODULES = [dynamic_agents, llm_judge, self_optimizer]
MODULE_IDS = [m.__name__ for m in MODULES]

OLD_PAYLOAD = {"generation": "old", "records": [1, 2, 3]}
NEW_PAYLOAD = {"generation": "new", "records": [4, 5, 6, 7]}


# ---------------------------------------------------------------------------
# Instrumentation — bam vao BUOC COMMIT chung cho moi hien thuc
# ---------------------------------------------------------------------------

# `Path.rename` uy quyen xuong `os.rename` o mot so ban Python va tu goi syscall
# o ban khac; `os.replace` la duong cua ban vá. Chan ca ba de test khong phu
# thuoc vao hien thuc nao dang duoc dung.
_COMMIT_PRIMITIVES = (
    (os, "replace"),
    (os, "rename"),
    (pathlib.Path, "rename"),
)


def _instrument_commit(monkeypatch, events: list, *, fail: bool) -> None:
    """Ghi lai (va tuy chon lam hong) moi buoc commit doi ten file."""
    for owner, name in _COMMIT_PRIMITIVES:
        original = getattr(owner, name)

        def wrapper(*args, _original=original, **kwargs):
            events.append(("commit", os.fspath(args[0])))
            if fail:
                raise OSError("mat dien mo phong ngay tai buoc commit")
            return _original(*args, **kwargs)

        monkeypatch.setattr(owner, name, wrapper)


def _instrument_fsync(monkeypatch, events: list) -> None:
    real_fsync = os.fsync

    def wrapper(fd):
        events.append(("fsync", fd))
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", wrapper)


def _kinds(events: list) -> list[str]:
    return [kind for kind, _ in events]


def _seed(target: Path) -> bytes:
    """Dat mot ban ghi cu hop le tai *target*, tra ve bytes nguyen ban."""
    target.write_text(
        json.dumps(OLD_PAYLOAD, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target.read_bytes()


def _debris(directory: Path, target: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir() if p != target)


# ---------------------------------------------------------------------------
# 1. Khiem khuyet chinh: commit hong = MAT file dich
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", MODULES, ids=MODULE_IDS)
def test_commit_failure_leaves_previous_file_intact(module, tmp_path, monkeypatch):
    """Hong giua chung => file dich con NGUYEN BAN CU, khong mat, khong cut."""
    target = tmp_path / "registry.json"
    original_bytes = _seed(target)

    _instrument_commit(monkeypatch, [], fail=True)
    module._atomic_write(target, NEW_PAYLOAD)

    assert target.exists(), (
        f"{module.__name__}._atomic_write xoa file dich TRUOC khi commit — "
        "hong o khe do la mat trang du lieu, khong con duong lui"
    )
    assert target.read_bytes() == original_bytes, (
        f"{module.__name__}._atomic_write de lai file dich hong sau khi commit that bai"
    )
    assert json.loads(target.read_text(encoding="utf-8")) == OLD_PAYLOAD


@pytest.mark.parametrize("module", MODULES, ids=MODULE_IDS)
def test_commit_failure_leaves_no_temp_debris(module, tmp_path, monkeypatch):
    """Commit hong => don sach tmp, khong bo lai rac cho lan sau doc nham."""
    target = tmp_path / "registry.json"
    _seed(target)

    _instrument_commit(monkeypatch, [], fail=True)
    module._atomic_write(target, NEW_PAYLOAD)

    assert _debris(tmp_path, target) == [], (
        f"{module.__name__}._atomic_write bo lai file tam sau khi commit that bai"
    )


# ---------------------------------------------------------------------------
# 2. Do ben: noi dung phai xuong dia TRUOC khi commit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", MODULES, ids=MODULE_IDS)
def test_fsync_precedes_commit(module, tmp_path, monkeypatch):
    """Khong fsync truoc rename => ten moi co the tro toi noi dung rong."""
    target = tmp_path / "registry.json"
    _seed(target)

    events: list = []
    _instrument_fsync(monkeypatch, events)
    _instrument_commit(monkeypatch, events, fail=False)
    module._atomic_write(target, NEW_PAYLOAD)

    kinds = _kinds(events)
    assert "commit" in kinds, f"{module.__name__}._atomic_write khong commit gi ca"
    assert "fsync" in kinds, (
        f"{module.__name__}._atomic_write khong fsync — noi dung chi nam trong "
        "page cache, mat dien sau rename = file rong mang ten that"
    )
    assert kinds.index("fsync") < kinds.index("commit"), (
        f"{module.__name__}._atomic_write fsync SAU khi commit — vo nghia"
    )


# ---------------------------------------------------------------------------
# 3. Tmp phai duy nhat moi lan ghi (hai writer khong duoc giam len nhau)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", MODULES, ids=MODULE_IDS)
def test_temp_path_is_unique_per_write(module, tmp_path, monkeypatch):
    """Ten tmp co dinh => hai writer cung dich dung chung mot file dang do."""
    target = tmp_path / "registry.json"
    _seed(target)

    events: list = []
    _instrument_commit(monkeypatch, events, fail=False)
    module._atomic_write(target, NEW_PAYLOAD)
    module._atomic_write(target, OLD_PAYLOAD)

    # `Path.rename` uy quyen xuong `os.rename` nen mot lan commit co the sinh
    # nhieu ban ghi; cai can do la SO DUONG DAN TAM RIENG BIET, khong phai so
    # lan goi.
    sources = {payload for kind, payload in events if kind == "commit"}
    assert sources, f"{module.__name__}._atomic_write khong commit gi ca"
    assert len(sources) == 2, (
        f"{module.__name__}._atomic_write dung ten tmp CO DINH ({sorted(sources)!r}) — "
        "hai writer cung mot dich se giam len file tam cua nhau"
    )


# ---------------------------------------------------------------------------
# 4. Chan hoi quy: duong hanh phuc van phai dung
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", MODULES, ids=MODULE_IDS)
def test_successful_write_commits_new_payload(module, tmp_path):
    target = tmp_path / "registry.json"
    _seed(target)

    module._atomic_write(target, NEW_PAYLOAD)

    assert json.loads(target.read_text(encoding="utf-8")) == NEW_PAYLOAD
    assert _debris(tmp_path, target) == [], "con rac .tmp sau khi ghi thanh cong"


@pytest.mark.parametrize("module", MODULES, ids=MODULE_IDS)
def test_write_creates_file_when_absent(module, tmp_path):
    target = tmp_path / "registry.json"

    module._atomic_write(target, NEW_PAYLOAD)

    assert json.loads(target.read_text(encoding="utf-8")) == NEW_PAYLOAD


@pytest.mark.parametrize("module", MODULES, ids=MODULE_IDS)
def test_write_preserves_unicode_unescaped(module, tmp_path):
    """Ba module deu ghi tieng Viet; ensure_ascii=False la mot phan hop dong."""
    target = tmp_path / "registry.json"

    module._atomic_write(target, {"ten": "Vinh Long — coi nguon"})

    assert "Vinh Long — coi nguon" in target.read_text(encoding="utf-8")


@pytest.mark.parametrize("module", MODULES, ids=MODULE_IDS)
def test_list_payload_is_supported(module, tmp_path):
    """llm_judge.LLMJudge._save truyen mot LIST, khong phai dict."""
    target = tmp_path / "evaluations.json"

    module._atomic_write(target, [{"score": 8}, {"score": 9}])

    assert json.loads(target.read_text(encoding="utf-8")) == [{"score": 8}, {"score": 9}]


# ---------------------------------------------------------------------------
# 5. Hop dong "khong nem": 3 module goi tu duong runtime (chat) — loi ghi
#    telemetry khong duoc lam do request. Giu nguyen hanh vi cu.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module", MODULES, ids=MODULE_IDS)
def test_write_failure_is_swallowed_not_raised(module, tmp_path, monkeypatch, caplog):
    target = tmp_path / "registry.json"
    _seed(target)

    _instrument_commit(monkeypatch, [], fail=True)
    with caplog.at_level("ERROR"):
        module._atomic_write(target, NEW_PAYLOAD)  # khong duoc nem

    assert any("Failed to write" in r.message or "Failed to write" in r.getMessage()
               for r in caplog.records), "that bai ghi phai duoc log lai, khong nuot im"
