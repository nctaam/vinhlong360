from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]

AUTO_LEARN_EXPECTATIONS = (
    ("long hồ", "p-long-ho"),
    ("trà ôn", "p-tra-on"),
    ("tam bình", "p-tam-binh"),
    ("vũng liêm", "p-vung-liem"),
    ("bình tân", "p-tan-quoi"),
    ("mỏ cày", "p-mo-cay"),
    ("tiểu cần", "p-tieu-can"),
    ("càng long", "p-cang-long"),
    ("ba tri", "p-ba-tri"),
    ("bình đại", "p-binh-dai"),
)

CRAWLER_EXPECTATIONS = (
    ("long hồ", "p-long-ho"),
    ("trà ôn", "p-tra-on"),
    ("tam bình", "p-tam-binh"),
    ("vũng liêm", "p-vung-liem"),
    ("bình tân", "p-tan-quoi"),
    ("mỏ cày", "p-mo-cay"),
)

FULL_ADDRESS_EXPECTATIONS = (
    ("Long Hồ, Vĩnh Long", "p-long-ho"),
    ("Mỏ Cày, Bến Tre", "p-mo-cay"),
    ("Cầu Kè, Trà Vinh", "xa-cau-ke"),
)

AUTO_LEARN_CITY_EXPECTATIONS = (
    ("TP Vĩnh Long", "p-long-chau"),
    ("Thành phố Vĩnh Long", "p-long-chau"),
    ("TP Bến Tre", "p-ben-tre"),
    ("Thành phố Bến Tre", "p-ben-tre"),
    ("TP Trà Vinh", "p-tra-vinh"),
)

CRAWLER_CITY_EXPECTATIONS = (
    ("TP Vĩnh Long", "p-long-chau"),
    ("Thành phố Vĩnh Long", "p-long-chau"),
)


def _load_module(path: Path, module_name: str, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def runtime_modules(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, ModuleType]:
    monkeypatch.setenv("LLM_API_KEY", "test-runtime-place-mappings")
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_MODEL_MINI", "test-mini-model")

    auto_learn = _load_module(
        ROOT / "agent" / "auto_learn.py",
        "test_runtime_place_mappings_auto_learn",
        monkeypatch,
    )
    crawler = _load_module(
        ROOT / "agent" / "crawler.py",
        "test_runtime_place_mappings_crawler",
        monkeypatch,
    )
    return auto_learn, crawler


def test_legacy_area_queries_resolve_to_current_units(
    runtime_modules: tuple[ModuleType, ModuleType],
) -> None:
    auto_learn, crawler = runtime_modules

    for query, expected in AUTO_LEARN_EXPECTATIONS:
        assert auto_learn.guess_place_id(query) == expected

    for query, expected in CRAWLER_EXPECTATIONS:
        assert crawler.guess_place_id(query) == expected


def test_specific_legacy_area_beats_province_fallback_in_full_address(
    runtime_modules: tuple[ModuleType, ModuleType],
) -> None:
    auto_learn, crawler = runtime_modules

    for query, expected in FULL_ADDRESS_EXPECTATIONS:
        assert auto_learn.guess_place_id(query) == expected
        assert crawler.guess_place_id(query) == expected

    for query, expected in AUTO_LEARN_CITY_EXPECTATIONS:
        assert auto_learn.guess_place_id(query) == expected

    for query, expected in CRAWLER_CITY_EXPECTATIONS:
        assert crawler.guess_place_id(query) == expected


def test_all_runtime_mapping_targets_belong_to_current_roster(
    runtime_modules: tuple[ModuleType, ModuleType],
) -> None:
    data = json.loads((ROOT / "web" / "data.json").read_text(encoding="utf-8"))
    unit_ids = {
        entity["id"]
        for entity in data["entities"]
        if entity.get("type") == "place" and entity.get("level") in {"phuong", "xa"}
    }
    auto_learn, crawler = runtime_modules

    for module_name, guess_place_id, mapping in (
        ("auto_learn", auto_learn.guess_place_id, auto_learn.PLACE_KEYWORDS),
        ("crawler", crawler.guess_place_id, crawler.PLACE_MAPPING),
    ):
        stale_targets = sorted(set(mapping.values()) - unit_ids)
        assert stale_targets == [], f"{module_name} has stale targets: {stale_targets}"
        assert all(guess_place_id(keyword) in unit_ids for keyword in mapping)
