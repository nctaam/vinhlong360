"""B4 (Phase 0): entities store `source` as a LIST of {title,url,maps}.

Both data_quality.source_info and seo._source_info must read the first element,
and seo.build_entity_jsonld must then emit a citation/sameAs. Guards against the
regression where list-form source silently dropped 877 entities' provenance.
"""

import data_quality
import seo

LIST_ENTITY = {
    "id": "test-list-src",
    "type": "attraction",
    "name": "Bảo tàng Bến Tre",
    "source": [{"title": "Bến Tre Tourism", "url": "https://bentretourism.vn/x", "maps": "https://maps.app.goo.gl/y"}],
}


def test_data_quality_source_info_reads_list():
    info = data_quality.source_info(LIST_ENTITY)
    assert info["url"] == "https://bentretourism.vn/x"
    assert "Bến Tre" in info["title"]


def test_seo_source_info_reads_list():
    title, url = seo._source_info(LIST_ENTITY)
    assert url == "https://bentretourism.vn/x"
    assert title


def test_jsonld_emits_citation_for_list_source():
    ld = seo.build_entity_jsonld(LIST_ENTITY, {})
    assert ld.get("citation", {}).get("url") == "https://bentretourism.vn/x"


def test_empty_or_missing_list_source_is_safe():
    for src in ([], None):
        e = {"id": "x", "type": "attraction", "name": "X", "source": src}
        assert data_quality.source_info(e)["url"] is None
        assert seo._source_info(e)[1] is None
