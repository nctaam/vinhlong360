import sys


def test_semantic_cache_and_features_share_vector_singleton():
    import features
    import semantic_cache

    assert features.embedding_store is semantic_cache.embedding_store
    assert features.embedding_store is sys.modules["agent.vector_search"].embedding_store


def test_vector_search_does_not_split_module_singleton():
    import agent.vector_search as package_vector
    import vector_search as legacy_vector

    assert package_vector is legacy_vector
    assert package_vector.embedding_store is legacy_vector.embedding_store
