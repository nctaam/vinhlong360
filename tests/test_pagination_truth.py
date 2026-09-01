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

