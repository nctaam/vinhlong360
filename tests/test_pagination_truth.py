"""Pagination truth contract independent of a concrete database backend."""

from dataclasses import dataclass

from search_contract import SearchFilters, search_public_entities


@dataclass
class _Catalog:
    rows: list[dict]

    def list_entities(self, **kwargs):
        return list(self.rows)

    def count_entities_filtered(self, **kwargs):
        return len(self.rows)


def test_page_reports_truncated_only_for_explicit_bounded_mode():
    catalog = _Catalog([{"id": str(i), "type": "dish", "name": f"Dish {i}" } for i in range(4)])

    page = search_public_entities("", offset=0, limit=2, filters=SearchFilters(), database=catalog)

    assert [item["id"] for item in page.items] == ["0", "1"]
    assert page.total == 4
    assert page.truncated is False


def test_canonical_page_can_filter_a_catalog_larger_than_500_before_slicing():
    rows = [
        {"id": f"entity-{i:04d}", "type": "dish", "name": "Dừa Sáp" if i == 599 else f"Dish {i}"}
        for i in range(600)
    ]
    catalog = _Catalog(rows)

    page = search_public_entities("dua sap", offset=0, limit=5, filters=SearchFilters(), database=catalog)

    assert page.items[0]["id"] == "entity-0599"
    assert page.total == 1
    assert page.truncated is False
