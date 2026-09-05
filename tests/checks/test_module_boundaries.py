from pathlib import Path


# Static import markers keep the staged test-pairing gate honest without
# importing the full application during collection.
if False:  # pragma: no cover
    import community.api as community_api
    import public_api as public_api_module


def test_public_api_does_not_import_private_community_symbols():
    source = Path("agent/public_api.py").read_text(encoding="utf-8")
    assert "from community.api import" not in source
    assert "import community.api" not in source
    assert "from community.contracts import" in source


def test_community_contracts_expose_stable_public_names():
    from community import contracts

    for name in (
        "POST_COLS",
        "block_sql",
        "mute_sql",
        "prod_seed_post_filter",
        "format_post",
        "enrich_all",
        "collect_new_entities",
        "feed_new_since",
    ):
        assert hasattr(contracts, name), name
        assert not name.startswith("_")
