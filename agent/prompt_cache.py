"""
vinhlong360 — LLM Prompt Caching Module.

Tối ưu hóa việc xây dựng prompt cho Knowledge Agent:
  1. Cache base system prompt + static context (tools, date) — thay đổi ít
  2. Cache proactive context — thay đổi mỗi giờ (mùa vụ, trending)
  3. Dynamic parts (RAG, memory, reflexion) — tính mỗi request

Giảm token cost bằng cách:
  - Tránh rebuild toàn bộ system prompt khi static parts không đổi
  - Ước tính token count chính xác hơn cho Vietnamese text
  - Nén history cũ để giữ context window gọn
  - Theo dõi thống kê tiết kiệm tokens

Thread-safe, stdlib only.
"""

import hashlib
import logging
import re
import time
from threading import Lock
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════
#  TOKEN ESTIMATION
# ══════════════════════════════════════════════════

# Vietnamese text uses ~2 chars/token (nhiều dấu, nhiều âm tiết ngắn)
# English text uses ~4 chars/token
_VIETNAMESE_RANGE = re.compile(
    r"[À-ɏ"       # Latin Extended (Vietnamese diacritics)
    r"Ḁ-ỿ"        # Latin Extended Additional (ắ, ề, ổ, ứ, ỹ...)
    r"̀-ͯ]"       # Combining diacritical marks
)


def _vietnamese_ratio(text: str) -> float:
    """Estimate ratio of Vietnamese characters in text (0.0 - 1.0)."""
    if not text:
        return 0.0
    viet_chars = len(_VIETNAMESE_RANGE.findall(text))
    total = len(text)
    if total == 0:
        return 0.0
    # Vietnamese text typically has ~15-25% diacritical characters.
    # If we detect >5% diacritics, treat the whole text as Vietnamese.
    ratio = viet_chars / total
    if ratio > 0.05:
        return 1.0
    elif ratio > 0.02:
        return 0.5
    return 0.0


def estimate_tokens(text: str) -> int:
    """
    Ước tính token count cho một đoạn text.

    Vietnamese text: ~2 chars/token (do nhiều ký tự dấu, từ ngắn).
    English text:    ~4 chars/token.
    Mixed:           trung bình có trọng số.

    Args:
        text: Đoạn text cần ước tính.

    Returns:
        Số token ước tính.
    """
    if not text:
        return 0
    viet_ratio = _vietnamese_ratio(text)
    chars_per_token = 2.0 * viet_ratio + 4.0 * (1.0 - viet_ratio)
    return max(1, int(len(text) / chars_per_token))


def estimate_messages_tokens(messages: list[dict]) -> int:
    """
    Ước tính tổng token count cho một danh sách messages.

    Bao gồm overhead cho mỗi message (role, formatting ~ 4 tokens).

    Args:
        messages: Danh sách messages theo format OpenAI.

    Returns:
        Tổng số token ước tính.
    """
    total = 0
    for msg in messages:
        # ~4 tokens overhead per message (role, separators)
        total += 4
        content = msg.get("content", "")
        if isinstance(content, str):
            total += estimate_tokens(content)
        elif isinstance(content, list):
            # Multi-part content (text + images)
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += estimate_tokens(part.get("text", ""))
    return total


# ══════════════════════════════════════════════════
#  PROMPT COMPRESSION
# ══════════════════════════════════════════════════

def compress_history(messages: list[dict], max_tokens: int = 4000) -> list[dict]:
    """
    Nén conversation history để fit trong token budget.

    Strategy:
      1. Giữ nguyên system messages.
      2. Giữ nguyên N messages cuối cùng (fit trong max_tokens).
      3. Messages cũ hơn bị truncate (200 chars đầu + "...").

    Args:
        messages:   Danh sách messages đầy đủ.
        max_tokens: Token budget tối đa cho history.

    Returns:
        Danh sách messages đã nén.
    """
    if not messages:
        return []

    # Separate system messages from conversation
    system_msgs = [m for m in messages if m.get("role") == "system"]
    conv_msgs = [m for m in messages if m.get("role") != "system"]

    if not conv_msgs:
        return system_msgs

    # Calculate system tokens (always kept)
    system_tokens = estimate_messages_tokens(system_msgs)
    remaining_budget = max(0, max_tokens - system_tokens)

    # Walk backwards from most recent, keeping messages that fit
    kept_recent = []
    used_tokens = 0

    for msg in reversed(conv_msgs):
        msg_tokens = estimate_tokens(msg.get("content", "")) + 4
        if used_tokens + msg_tokens <= remaining_budget:
            kept_recent.append(msg)
            used_tokens += msg_tokens
        else:
            break

    kept_recent.reverse()

    # Find which older messages were dropped
    kept_count = len(kept_recent)
    older_msgs = conv_msgs[:len(conv_msgs) - kept_count]

    # Summarize older messages (truncate to 200 chars)
    compressed_older = []
    for msg in older_msgs:
        content = msg.get("content", "")
        if len(content) > 200:
            content = content[:200] + "..."
        compressed_older.append({
            "role": msg["role"],
            "content": content,
        })

    # Check if compressed older messages fit in remaining budget
    older_tokens = estimate_messages_tokens(compressed_older)
    final_budget = remaining_budget - used_tokens

    if older_tokens <= final_budget:
        return system_msgs + compressed_older + kept_recent
    else:
        # Even compressed messages don't fit — drop them entirely
        return system_msgs + kept_recent


# ══════════════════════════════════════════════════
#  CACHE ENTRY
# ══════════════════════════════════════════════════

class _CacheEntry:
    """Internal cache entry with TTL."""

    __slots__ = ("content", "tokens", "hash_key", "created_at", "ttl")

    def __init__(self, content: str, tokens: int, hash_key: str, ttl: int):
        self.content = content
        self.tokens = tokens
        self.hash_key = hash_key
        self.created_at = time.time()
        self.ttl = ttl

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) >= self.ttl


# ══════════════════════════════════════════════════
#  PROMPT CACHE
# ══════════════════════════════════════════════════

class PromptCache:
    """
    LLM Prompt Cache cho Knowledge Agent.

    Cache hệ thống system prompt theo 2 layer:
      - Static layer:  base system prompt + tools description + date info
                       → thay đổi chỉ khi reload data hoặc qua ngày mới
      - Proactive layer: mùa vụ, trending, thời gian
                       → thay đổi mỗi giờ

    Dynamic parts (RAG, memory, reflexion) luôn được tính lại mỗi request.

    Usage::

        prompt_cache = PromptCache()

        messages, info = prompt_cache.build_cached_prompt(
            message="Cam sành Tam Bình có gì đặc biệt?",
            history=[...],
            session_id="abc123",
            user_id="user_1",
        )
        # info = {"cached_tokens": 800, "dynamic_tokens": 200, ...}
    """

    # Default TTLs
    STATIC_TTL = 86400    # 24 hours (base prompt, tools)
    PROACTIVE_TTL = 3600  # 1 hour (seasonal, trending, time-of-day)

    def __init__(self):
        self._lock = Lock()
        self._static_cache: _CacheEntry | None = None
        self._proactive_cache: dict[str, _CacheEntry] = {}  # keyed by hour-hash

        # Stats
        self._total_requests = 0
        self._cache_hits = 0
        self._tokens_saved = 0
        self._total_cached_tokens = 0
        self._total_dynamic_tokens = 0
        self._total_prompt_tokens = 0

    # ── Static Layer ──

    def _build_static_content(self, system_prompt: str) -> str:
        """Build the static part of the system prompt (base + date)."""
        now = datetime.now(timezone.utc)
        return (
            system_prompt
            + f"\nHôm nay: {now.strftime('%d/%m/%Y')}. Tháng hiện tại: {now.month}."
        )

    def _get_static(self, system_prompt: str) -> tuple[_CacheEntry, bool]:
        """Get or rebuild the static cache entry.

        Returns:
            Tuple of (entry, was_cache_hit).
        """
        content = self._build_static_content(system_prompt)
        hash_key = hashlib.md5(content.encode("utf-8")).hexdigest()

        if (
            self._static_cache is not None
            and self._static_cache.hash_key == hash_key
            and not self._static_cache.is_expired()
        ):
            return self._static_cache, True

        tokens = estimate_tokens(content)
        entry = _CacheEntry(content, tokens, hash_key, self.STATIC_TTL)
        self._static_cache = entry
        return entry, False

    # ── Proactive Layer ──

    def _get_proactive(self, proactive_content: str) -> tuple[_CacheEntry, bool]:
        """Get or rebuild the proactive cache entry.

        Returns:
            Tuple of (entry, was_cache_hit).
        """
        if not proactive_content:
            return _CacheEntry("", 0, "", self.PROACTIVE_TTL), False

        hash_key = hashlib.md5(proactive_content.encode("utf-8")).hexdigest()

        cached = self._proactive_cache.get(hash_key)
        if cached is not None and not cached.is_expired():
            return cached, True

        tokens = estimate_tokens(proactive_content)
        entry = _CacheEntry(proactive_content, tokens, hash_key, self.PROACTIVE_TTL)

        # Evict expired entries + enforce size cap
        expired_keys = [
            k for k, v in self._proactive_cache.items() if v.is_expired()
        ]
        for k in expired_keys:
            del self._proactive_cache[k]
        while len(self._proactive_cache) >= 200:
            oldest_key = min(self._proactive_cache, key=lambda k: self._proactive_cache[k].created_at)
            del self._proactive_cache[oldest_key]

        self._proactive_cache[hash_key] = entry
        return entry, False

    # ── Build Cached Prompt ──

    def build_cached_prompt(
        self,
        message: str,
        history: list[dict],
        session_id: str = "",
        user_id: str = "",
        *,
        system_prompt: str = "",
        proactive_context: str = "",
        rag_context: str = "",
        realtime_context: str = "",
        memory_context: str = "",
        reflexion_context: str = "",
        max_history_tokens: int = 4000,
    ) -> tuple[list[dict], dict]:
        """
        Xây dựng messages cho LLM, tận dụng cache cho static parts.

        Caller cung cấp các context đã được compute bên ngoài:
          - system_prompt:      Base system prompt (từ tools.SYSTEM_PROMPT)
          - proactive_context:  Output từ proactive.get_proactive_context()
          - rag_context:        Output từ agentic_rag.build_rag_context()
          - realtime_context:   Output từ realtime.get_realtime_context()
          - memory_context:     Output từ memory.memory_manager.build_context()
          - reflexion_context:  Output từ reflexion.reflexion_engine.get_reflection_prompt()

        Args:
            message:            User message hiện tại.
            history:            Conversation history (list of {role, content}).
            session_id:         Session ID (cho memory lookup).
            user_id:            User ID (cho memory lookup).
            system_prompt:      Base system prompt text.
            proactive_context:  Proactive suggestions text.
            rag_context:        RAG routing context text.
            realtime_context:   Realtime (weather, events) context text.
            memory_context:     Memory context text.
            reflexion_context:  Reflexion lessons text.
            max_history_tokens: Max tokens for history compression.

        Returns:
            Tuple of (messages, cache_info) where:
              - messages: List[dict] ready for LLM API call
              - cache_info: Dict with token usage stats
        """
        with self._lock:
            self._total_requests += 1

            # ── Cached layers ──
            static_entry, static_hit = self._get_static(system_prompt)
            proactive_entry, proactive_hit = self._get_proactive(proactive_context)

            # Cache hit = at least the static layer was served from cache
            cache_hit = static_hit

            cached_tokens = static_entry.tokens + proactive_entry.tokens

            # ── Dynamic parts (always recomputed) ──
            dynamic_parts = []
            if rag_context:
                dynamic_parts.append(rag_context)
            if realtime_context:
                dynamic_parts.append(realtime_context)
            if memory_context:
                dynamic_parts.append(memory_context)
            if reflexion_context:
                dynamic_parts.append(reflexion_context)

            dynamic_content = "\n".join(dynamic_parts)
            dynamic_tokens = estimate_tokens(dynamic_content)

            # ── Assemble system prompt ──
            system_parts = [static_entry.content]
            if proactive_entry.content:
                system_parts.append(proactive_entry.content)
            if dynamic_content:
                system_parts.append(dynamic_content)

            system_text = "\n".join(system_parts)
            messages = [{"role": "system", "content": system_text}]

            # ── Compress and add history ──
            if history:
                compressed = compress_history(history, max_tokens=max_history_tokens)
                # Only add non-system messages (system is already included above)
                for m in compressed:
                    if m.get("role") != "system":
                        messages.append(m)

            # ── Add current user message ──
            messages.append({"role": "user", "content": message})

            # ── Token accounting ──
            total_tokens = estimate_messages_tokens(messages)

            # Update stats
            if cache_hit:
                self._cache_hits += 1
                # Tokens saved = cached tokens that didn't need recomputation
                self._tokens_saved += cached_tokens
            self._total_cached_tokens += cached_tokens
            self._total_dynamic_tokens += dynamic_tokens
            self._total_prompt_tokens += total_tokens

            cache_info = {
                "cached_tokens": cached_tokens,
                "dynamic_tokens": dynamic_tokens,
                "total_tokens": total_tokens,
                "cache_hit": cache_hit,
                "static_hash": static_entry.hash_key,
                "proactive_hash": proactive_entry.hash_key,
            }

            return messages, cache_info

    # ── Cache Invalidation ──

    def invalidate(self):
        """
        Xóa toàn bộ cache (gọi sau khi reload data hoặc deploy mới).

        Thread-safe. Không reset stats.
        """
        with self._lock:
            self._static_cache = None
            self._proactive_cache.clear()

    def invalidate_proactive(self):
        """Xóa chỉ proactive cache (khi context thay đổi giữa giờ)."""
        with self._lock:
            self._proactive_cache.clear()

    # ── Stats ──

    def stats(self) -> dict:
        """
        Thống kê prompt cache.

        Returns:
            Dict chứa:
              - total_requests:       Tổng số requests
              - cache_hits:           Số lần cache hit
              - cache_hit_rate:       Tỉ lệ cache hit (0.0 - 1.0)
              - tokens_saved:         Tổng tokens tiết kiệm nhờ cache
              - avg_prompt_tokens:    Kích thước prompt trung bình (tokens)
              - avg_cached_tokens:    Tokens cached trung bình mỗi request
              - avg_dynamic_tokens:   Tokens dynamic trung bình mỗi request
              - static_cache_active:  Static cache còn hiệu lực?
              - proactive_entries:    Số proactive entries trong cache
        """
        with self._lock:
            total = self._total_requests or 1  # avoid div-by-zero
            return {
                "total_requests": self._total_requests,
                "cache_hits": self._cache_hits,
                "cache_hit_rate": round(self._cache_hits / total, 3),
                "tokens_saved": self._tokens_saved,
                "avg_prompt_tokens": round(self._total_prompt_tokens / total),
                "avg_cached_tokens": round(self._total_cached_tokens / total),
                "avg_dynamic_tokens": round(self._total_dynamic_tokens / total),
                "static_cache_active": (
                    self._static_cache is not None
                    and not self._static_cache.is_expired()
                ),
                "proactive_entries": len(self._proactive_cache),
            }

    def reset_stats(self):
        """Reset tất cả thống kê về 0."""
        with self._lock:
            self._total_requests = 0
            self._cache_hits = 0
            self._tokens_saved = 0
            self._total_cached_tokens = 0
            self._total_dynamic_tokens = 0
            self._total_prompt_tokens = 0


# ══════════════════════════════════════════════════
#  MODULE-LEVEL SINGLETON
# ══════════════════════════════════════════════════

prompt_cache = PromptCache()
