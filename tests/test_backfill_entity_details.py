"""Tests GĐ-B bước 3: logic ánh xạ/coercion của backfill (pure, không cần PG).

End-to-end verify là chạy backfill --dry-run/--apply + parity trên prod PG;
đây là guard cho phần thuần logic: tách universal/detail, KEY_MAP, INT guard.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "scripts"))

from backfill_entity_details import KIND_TABLE, UNIVERSAL, typed_values  # noqa: E402
from entity_schemas import ENTITY_SCHEMAS, KIND_OF_TYPE  # noqa: E402


def test_universal_split_from_detail():
    uni, det, skipped = typed_values("product", {
        "address": "Ấp 1, xã A", "ocop_star": "3", "producer": "HTX B",
    })
    assert uni == {"address": "Ấp 1, xã A"}
    assert det == {"ocop_star": 3, "producer": "HTX B"}
    assert not skipped


def test_key_map_view_and_architectural_style():
    _, det_food, _ = typed_values("cafe", {"wifi": "true", "rating": "4.5"})
    assert det_food == {"wifi": True, "rating": 4.5}
    _, det_rest, _ = typed_values("restaurant", {"view": "ven sông"})
    assert det_rest == {"view_note": "ven sông"}
    _, det_hist, _ = typed_values("history", {"architectural_style": "Đình Nam bộ"})
    assert det_hist == {"architecture_style": "Đình Nam bộ"}


def test_int_column_guard_skips_fractional_and_junk():
    _, det, skipped = typed_values("accommodation", {"rooms": "12"})
    assert det == {"rooms": 12} and not skipped
    _, det2, skipped2 = typed_values("accommodation", {"rooms": "mười hai"})
    assert det2 == {} and len(skipped2) == 1
    _, det3, skipped3 = typed_values("nature", {"scenic_rating": "4.5"})
    assert det3 == {} and len(skipped3) == 1  # INT column, giá trị lẻ → ở lại JSONB


def test_tags_coerced_to_list():
    _, det, _ = typed_values("dish", {"ingredients": "dừa, đường, mè"})
    assert det == {"ingredients": ["dừa", "đường", "mè"]}


def test_unknown_and_empty_keys_ignored():
    uni, det, skipped = typed_values("person", {
        "role": "Danh nhân", "sac_phong": "1852", "address": "", "birth_year": None,
    })
    assert det == {"role": "Danh nhân"}   # sac_phong = bespoke tail, không thuộc registry
    assert uni == {} and not skipped


def test_kind_table_covers_all_registry_kinds():
    kinds_in_registry = {KIND_OF_TYPE[t] for t in ENTITY_SCHEMAS} - {"itinerary", "other"}
    assert kinds_in_registry == set(KIND_TABLE.keys())
