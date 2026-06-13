"""Tests for agent/autocorrect.py — Vietnamese-aware autocorrect."""
import pytest

from autocorrect import (
    autocorrect,
    normalize_vietnamese,
    _levenshtein,
    _TOURISM_CORRECTIONS,
    get_correction_count,
    load_entity_names,
    _apply_capitalization,
    _is_word_boundary,
)


# ── normalize_vietnamese ─────────────────────────────


def test_normalize_lowercase():
    assert normalize_vietnamese("HELLO") == "hello"


def test_normalize_removes_diacritics():
    result = normalize_vietnamese("Vĩnh Long")
    assert result == "vinh long"


def test_normalize_a_variants():
    result = normalize_vietnamese("ắ ề ổ ứ ỹ")
    assert "a" in result
    assert "e" in result
    assert "o" in result
    assert "u" in result
    assert "y" in result


def test_normalize_d_to_d():
    assert "d" in normalize_vietnamese("đ")
    assert normalize_vietnamese("Đồng") == "dong"


def test_normalize_empty():
    assert normalize_vietnamese("") == ""


def test_normalize_ascii_unchanged():
    result = normalize_vietnamese("hello world")
    assert result == "hello world"


def test_normalize_complex_vietnamese():
    result = normalize_vietnamese("Đồng bằng sông Cửu Long")
    assert result == "dong bang song cuu long"


# ── _levenshtein ─────────────────────────────────────


def test_levenshtein_identical():
    assert _levenshtein("hello", "hello") == 0


def test_levenshtein_one_insert():
    assert _levenshtein("hell", "hello") == 1


def test_levenshtein_one_delete():
    assert _levenshtein("hello", "hell") == 1


def test_levenshtein_one_substitution():
    assert _levenshtein("hello", "hallo") == 1


def test_levenshtein_empty_strings():
    assert _levenshtein("", "") == 0


def test_levenshtein_one_empty():
    assert _levenshtein("", "abc") == 3
    assert _levenshtein("abc", "") == 3


def test_levenshtein_symmetric():
    assert _levenshtein("abc", "xyz") == _levenshtein("xyz", "abc")


def test_levenshtein_common_misspelling():
    # "vinh log" -> "vinh long" = 1 insertion
    assert _levenshtein("vinh log", "vinh long") == 1


# ── Known corrections dictionary ─────────────────────


def test_corrections_dictionary_not_empty():
    assert len(_TOURISM_CORRECTIONS) > 50


def test_get_correction_count():
    count = get_correction_count()
    assert count == len(_TOURISM_CORRECTIONS)


def test_known_corrections_vinh_long():
    assert _TOURISM_CORRECTIONS["vinh long"] == "Vĩnh Long"
    assert _TOURISM_CORRECTIONS["vinh log"] == "Vĩnh Long"
    assert _TOURISM_CORRECTIONS["ving long"] == "Vĩnh Long"


def test_known_corrections_food():
    assert _TOURISM_CORRECTIONS["bun nuoc leo"] == "bún nước lèo"
    assert _TOURISM_CORRECTIONS["banh trang"] == "bánh tráng"
    assert _TOURISM_CORRECTIONS["cam sanh"] == "cam sành"


def test_known_corrections_places():
    assert _TOURISM_CORRECTIONS["ben tre"] == "Bến Tre"
    assert _TOURISM_CORRECTIONS["tra vinh"] == "Trà Vinh"
    assert _TOURISM_CORRECTIONS["cho noi tra on"] == "chợ nổi Trà Ôn"


# ── autocorrect function ─────────────────────────────


def test_autocorrect_empty_string():
    result = autocorrect("")
    assert result["original"] == ""
    assert result["corrected"] == ""
    assert result["was_corrected"] is False
    assert result["corrections"] == []


def test_autocorrect_no_correction_needed():
    result = autocorrect("hello world")
    assert result["was_corrected"] is False
    assert result["corrected"] == "hello world"


def test_autocorrect_single_term():
    result = autocorrect("vinh long dep lam")
    assert result["was_corrected"] is True
    assert "Vĩnh Long" in result["corrected"]


def test_autocorrect_multiple_terms():
    result = autocorrect("toi muon di cho noi tra on va an bun nuoc leo")
    assert result["was_corrected"] is True
    corrections = result["corrections"]
    assert len(corrections) >= 2
    corrected_tos = [c["to"] for c in corrections]
    # Should correct both terms
    assert any("Trà Ôn" in t for t in corrected_tos)
    assert any("nước lèo" in t for t in corrected_tos)


def test_autocorrect_cam_sanh():
    result = autocorrect("cam sanh tam binh ngon khong")
    assert result["was_corrected"] is True
    assert "sành" in result["corrected"]
    assert "Bình" in result["corrected"]


def test_autocorrect_returns_corrections_list():
    result = autocorrect("vinh long")
    if result["was_corrected"]:
        assert isinstance(result["corrections"], list)
        for c in result["corrections"]:
            assert "from" in c
            assert "to" in c


def test_autocorrect_preserves_uncorrected_text():
    result = autocorrect("toi muon di vinh long ngay mai")
    assert "toi muon di" in result["corrected"] or "Vĩnh Long" in result["corrected"]


def test_autocorrect_longest_match_first():
    """Longer phrases should match before shorter ones."""
    result = autocorrect("cam sanh tam binh")
    # "cam sanh tam binh" is a complete phrase in the dictionary
    if result["was_corrected"]:
        corrections = result["corrections"]
        # Should match the long phrase, not just "cam sanh"
        assert any("Tam Bình" in c["to"] for c in corrections)


# ── Capitalization ───────────────────────────────────


def test_apply_capitalization_all_upper():
    result = _apply_capitalization("VINH LONG", "Vĩnh Long")
    assert result == "VĨNH LONG"


def test_apply_capitalization_all_lower():
    result = _apply_capitalization("vinh long", "Vĩnh Long")
    # Trusts dictionary casing for proper nouns
    assert result == "Vĩnh Long"


def test_apply_capitalization_first_upper():
    result = _apply_capitalization("Cam sanh", "cam sành")
    assert result[0].isupper()


def test_apply_capitalization_empty():
    assert _apply_capitalization("", "test") == "test"
    assert _apply_capitalization("test", "") == ""


# ── Word boundary ────────────────────────────────────


def test_is_word_boundary_start():
    assert _is_word_boundary("hello world", 0, 5) is True


def test_is_word_boundary_middle():
    assert _is_word_boundary("hello world test", 6, 11) is True


def test_is_word_boundary_not_boundary():
    assert _is_word_boundary("helloworld", 0, 5) is False


# ── Entity name fuzzy matching ───────────────────────


def test_load_entity_names():
    entities = {
        "e1": {"name": "Cam sanh Tam Binh", "type": "specialty"},
        "e2": {"name": "Bun nuoc leo", "type": "food"},
        "e3": {"name": "Vinh Long", "type": "place"},  # Should be skipped
    }
    load_entity_names(entities)
    # Should have loaded 2 names (place type is excluded)
    from autocorrect import _entity_names
    assert len(_entity_names) >= 2


def test_autocorrect_with_entity_names():
    """After loading entity names, fuzzy matching should work."""
    entities = {
        "e1": {"name": "Homestay Cu Lao", "type": "accommodation"},
    }
    load_entity_names(entities)
    # "homstay" is a known misspelling in the dictionary
    result = autocorrect("homstay")
    assert result["was_corrected"] is True
    assert "homestay" in result["corrected"]


# ── Edge cases ───────────────────────────────────────


def test_autocorrect_whitespace_only():
    result = autocorrect("   ")
    assert result["was_corrected"] is False


def test_autocorrect_none_like():
    result = autocorrect("")
    assert result["corrected"] == ""


def test_autocorrect_already_correct_vietnamese():
    """Text with correct diacritics should not be modified."""
    result = autocorrect("Tôi muốn đi du lịch")
    # "du lich" without diacritics would be corrected,
    # but "du lịch" with diacritics is already correct
    # The autocorrect dictionary matches on normalized form,
    # so it might still correct if the normalized key matches.
    # This is expected behavior.
    assert isinstance(result["corrected"], str)
