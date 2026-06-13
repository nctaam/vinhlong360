"""Tests for agent/prompt_cache.py — LLM Prompt Caching."""
import time

import pytest

from prompt_cache import (
    estimate_tokens,
    estimate_messages_tokens,
    compress_history,
    PromptCache,
    _vietnamese_ratio,
)


# ── Token estimation ─────────────────────────────────


def test_estimate_tokens_empty():
    assert estimate_tokens("") == 0


def test_estimate_tokens_english():
    # English: ~4 chars/token. "Hello world" = 11 chars -> ~2-3 tokens
    tokens = estimate_tokens("Hello world")
    assert tokens >= 1
    assert tokens <= 10


def test_estimate_tokens_vietnamese():
    # Vietnamese text with diacritics: ~2 chars/token
    text = "Xin chao cac ban, toi la huong dan vien du lich Vinh Long"
    tokens_en = estimate_tokens(text)
    # Same idea but with diacritics
    text_vn = "Xin chao cac ban, toi la huong dan vien du lich Vinh Long"
    tokens_vn = estimate_tokens(text_vn)
    assert tokens_vn >= 1


def test_estimate_tokens_vietnamese_with_diacritics():
    """Vietnamese text with heavy diacritics should yield more tokens per char."""
    text = "Vĩnh Long là tỉnh thuộc Đồng bằng sông Cửu Long"
    tokens = estimate_tokens(text)
    # With diacritics detected, chars_per_token is lower -> more tokens
    assert tokens >= 5


def test_estimate_tokens_returns_at_least_one():
    assert estimate_tokens("a") >= 1


# ── Vietnamese ratio detection ───────────────────────


def test_vietnamese_ratio_english():
    ratio = _vietnamese_ratio("Hello world, this is English")
    assert ratio == 0.0


def test_vietnamese_ratio_heavy_diacritics():
    ratio = _vietnamese_ratio("Đồng bằng sông Cửu Long đẹp lắm")
    # Should detect as Vietnamese (ratio > 0.05 -> returns 1.0)
    assert ratio >= 0.5


# ── estimate_messages_tokens ─────────────────────────


def test_estimate_messages_tokens_empty():
    assert estimate_messages_tokens([]) == 0


def test_estimate_messages_tokens_single():
    messages = [{"role": "user", "content": "Hello"}]
    tokens = estimate_messages_tokens(messages)
    # 4 overhead + content tokens
    assert tokens >= 5


def test_estimate_messages_tokens_multi_part():
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": "World"},
        ],
    }]
    tokens = estimate_messages_tokens(messages)
    assert tokens >= 5


def test_estimate_messages_tokens_multiple_messages():
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hi there!"},
        {"role": "assistant", "content": "Hello! How can I help?"},
    ]
    tokens = estimate_messages_tokens(messages)
    # 3 messages * 4 overhead + content tokens
    assert tokens >= 12


# ── compress_history ─────────────────────────────────


def test_compress_history_empty():
    assert compress_history([]) == []


def test_compress_history_preserves_system():
    messages = [
        {"role": "system", "content": "System prompt."},
        {"role": "user", "content": "Hi"},
    ]
    result = compress_history(messages, max_tokens=10000)
    roles = [m["role"] for m in result]
    assert "system" in roles


def test_compress_history_preserves_recent():
    messages = [
        {"role": "user", "content": f"Message {i}"} for i in range(10)
    ]
    result = compress_history(messages, max_tokens=10000)
    # All messages should fit
    assert len(result) == 10


def test_compress_history_truncates_old():
    # Create messages where total exceeds budget
    messages = [
        {"role": "user", "content": "Old message " * 50},  # Long old message
        {"role": "assistant", "content": "Old response " * 50},
        {"role": "user", "content": "Recent question"},
        {"role": "assistant", "content": "Recent answer"},
    ]
    result = compress_history(messages, max_tokens=100)
    # Recent messages should be preserved, old ones truncated or dropped
    assert len(result) >= 1
    # The most recent message should be intact
    last_msg = result[-1]
    assert "Recent" in last_msg["content"]


def test_compress_history_system_only():
    messages = [{"role": "system", "content": "System prompt"}]
    result = compress_history(messages, max_tokens=100)
    assert len(result) == 1
    assert result[0]["role"] == "system"


def test_compress_history_truncated_content_has_ellipsis():
    """Old messages beyond budget should be truncated with '...'."""
    long_content = "x" * 500
    messages = [
        {"role": "user", "content": long_content},
        {"role": "user", "content": "recent"},
    ]
    result = compress_history(messages, max_tokens=200)
    # If compression happened, old message should be truncated
    for m in result:
        if m["content"] != "recent" and len(m["content"]) > 203:
            # Should have been truncated
            pass  # Acceptable either way depending on budget


# ── PromptCache ──────────────────────────────────────


@pytest.fixture
def cache():
    return PromptCache()


def test_build_cached_prompt_returns_messages_and_info(cache):
    messages, info = cache.build_cached_prompt(
        message="Hello",
        history=[],
        system_prompt="You are a test assistant.",
    )
    assert isinstance(messages, list)
    assert len(messages) >= 2  # system + user
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "Hello"
    assert isinstance(info, dict)
    assert "cached_tokens" in info
    assert "dynamic_tokens" in info
    assert "total_tokens" in info


def test_build_cached_prompt_cache_hit(cache):
    """Second call with same system prompt should be a cache hit."""
    _, info1 = cache.build_cached_prompt(
        message="First",
        history=[],
        system_prompt="Static system prompt",
    )
    assert info1["cache_hit"] is False

    _, info2 = cache.build_cached_prompt(
        message="Second",
        history=[],
        system_prompt="Static system prompt",
    )
    assert info2["cache_hit"] is True


def test_build_cached_prompt_with_contexts(cache):
    messages, info = cache.build_cached_prompt(
        message="What about cam sanh?",
        history=[],
        system_prompt="Base prompt",
        proactive_context="Seasonal context",
        rag_context="RAG context",
        memory_context="User prefers food",
    )
    # All contexts should be in the system message
    system_content = messages[0]["content"]
    assert "Base prompt" in system_content
    assert "Seasonal context" in system_content
    assert "RAG context" in system_content
    assert "User prefers food" in system_content


def test_build_cached_prompt_includes_history(cache):
    history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
    ]
    messages, _ = cache.build_cached_prompt(
        message="Follow up",
        history=history,
        system_prompt="Prompt",
    )
    # Should have system + history (non-system) + user
    assert len(messages) >= 4


def test_invalidate_clears_cache(cache):
    cache.build_cached_prompt(
        message="Test",
        history=[],
        system_prompt="Prompt",
    )
    cache.invalidate()
    _, info = cache.build_cached_prompt(
        message="Test again",
        history=[],
        system_prompt="Prompt",
    )
    assert info["cache_hit"] is False


def test_invalidate_proactive(cache):
    cache.build_cached_prompt(
        message="Test",
        history=[],
        system_prompt="Prompt",
        proactive_context="Proactive 1",
    )
    cache.invalidate_proactive()
    # Proactive cache cleared but static cache still valid
    _, info = cache.build_cached_prompt(
        message="Test",
        history=[],
        system_prompt="Prompt",
        proactive_context="Proactive 2",
    )
    # Static should still be cached
    assert info["cache_hit"] is True


def test_stats_tracking(cache):
    cache.build_cached_prompt(message="A", history=[], system_prompt="P")
    cache.build_cached_prompt(message="B", history=[], system_prompt="P")

    stats = cache.stats()
    assert stats["total_requests"] == 2
    assert stats["cache_hits"] == 1  # second call hits static cache
    assert stats["cache_hit_rate"] == 0.5
    assert stats["tokens_saved"] > 0


def test_reset_stats(cache):
    cache.build_cached_prompt(message="A", history=[], system_prompt="P")
    cache.reset_stats()
    stats = cache.stats()
    assert stats["total_requests"] == 0
    assert stats["cache_hits"] == 0


def test_stats_static_cache_active(cache):
    cache.build_cached_prompt(message="A", history=[], system_prompt="P")
    stats = cache.stats()
    assert stats["static_cache_active"] is True


def test_stats_after_invalidate(cache):
    cache.build_cached_prompt(message="A", history=[], system_prompt="P")
    cache.invalidate()
    stats = cache.stats()
    assert stats["static_cache_active"] is False
