"""
vinhlong360 — Embedding-based Semantic Cache & Request Deduplication.

Kiến trúc:
  1. SemanticMatcher: TF-IDF sparse vectors, Vietnamese-aware, cosine similarity
  2. MultiTierCache: L1 in-memory LRU → L2 disk JSON → semantic fallback
  3. RequestDeduplicator: coalesce identical concurrent queries (threading.Event)
  4. CacheWarmer: pre-populate cache with popular / seasonal queries

Persistence: agent/data/semantic_cache/entries.json
Reuses _tokenize / _normalize_vietnamese from vector_search.py.
"""

import hashlib
import json
import logging
import math
import time
from collections import Counter, OrderedDict
from pathlib import Path
from threading import Event, Lock

logger = logging.getLogger(__name__)

# ── Try importing tokenizer from vector_search ──
try:
    from agent.vector_search import tokenize as _tokenize, normalize_vietnamese as _normalize_vietnamese
except ImportError:
    try:
        from vector_search import tokenize as _tokenize, normalize_vietnamese as _normalize_vietnamese
    except ImportError:
        logger.info("vector_search not available — using simple tokenizer fallback")

        def _normalize_vietnamese(text: str) -> str:  # type: ignore[misc]
            return text.lower().strip()

        def _tokenize(text: str) -> list[str]:  # type: ignore[misc]
            words = _normalize_vietnamese(text).split()
            tokens = [w for w in words if len(w) > 1]
            for i in range(len(tokens) - 1):
                tokens.append(f"{tokens[i]}_{tokens[i + 1]}")
            return tokens

# ── Paths ──
DATA_DIR = Path(__file__).resolve().parent / "data" / "semantic_cache"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ENTRIES_FILE = DATA_DIR / "entries.json"


# ══════════════════════════════════════════════════
#  SEMANTIC MATCHER
# ══════════════════════════════════════════════════

class SemanticMatcher:
    """TF-IDF sparse-vector matcher for cached queries."""

    def __init__(self):
        self._lock = Lock()
        # query_key -> sparse vector
        self._vectors: dict[str, dict[str, float]] = {}
        # query_key -> original query text
        self._texts: dict[str, str] = {}
        # token -> document frequency (number of queries containing this token)
        self._df: Counter = Counter()
        self._doc_count: int = 0

    # ── vectorisation ──

    def _vectorize(self, text: str) -> dict[str, float]:
        """Return sparse TF-IDF vector {token: weight} for *text*."""
        tokens = _tokenize(text)
        if not tokens:
            return {}

        tf = Counter(tokens)
        max_tf = max(tf.values())

        vec: dict[str, float] = {}
        for token, count in tf.items():
            # Augmented TF
            ntf = 0.5 + 0.5 * (count / max_tf)
            # IDF: use stored df when available, else treat as rare (idf = log(N))
            df = self._df.get(token, 0)
            if self._doc_count > 0 and df > 0:
                idf = math.log(self._doc_count / (1 + df)) + 1
            else:
                idf = math.log(max(self._doc_count, 1) + 1) + 1
            vec[token] = ntf * idf
        return vec

    @staticmethod
    def _cosine_similarity(v1: dict[str, float], v2: dict[str, float]) -> float:
        """Cosine similarity between two sparse vectors."""
        if not v1 or not v2:
            return 0.0

        # Dot product (only shared keys)
        shared = v1.keys() & v2.keys()
        if not shared:
            return 0.0

        dot = sum(v1[k] * v2[k] for k in shared)
        norm1 = math.sqrt(sum(w * w for w in v1.values()))
        norm2 = math.sqrt(sum(w * w for w in v2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    # ── index management ──

    def add(self, key: str, query: str):
        """Add a query to the matcher index."""
        with self._lock:
            vec = self._vectorize(query)
            if not vec:
                return
            self._vectors[key] = vec
            self._texts[key] = query
            # Update document frequency
            for token in set(vec.keys()):
                self._df[token] += 1
            self._doc_count += 1

    def remove(self, key: str):
        """Remove a query from the matcher index."""
        with self._lock:
            vec = self._vectors.pop(key, None)
            self._texts.pop(key, None)
            if vec:
                for token in set(vec.keys()):
                    self._df[token] = max(0, self._df.get(token, 1) - 1)
                self._doc_count = max(0, self._doc_count - 1)

    def find_similar(self, query: str, threshold: float = 0.88) -> tuple[str | None, float]:
        """
        Find the cached query most similar to *query*.

        Returns (cache_key, similarity) if similarity > threshold, else (None, 0.0).
        """
        with self._lock:
            if not self._vectors:
                return None, 0.0

            qvec = self._vectorize(query)
            if not qvec:
                return None, 0.0

            best_key: str | None = None
            best_sim = 0.0

            for key, vec in self._vectors.items():
                sim = self._cosine_similarity(qvec, vec)
                if sim > best_sim:
                    best_sim = sim
                    best_key = key

            if best_sim >= threshold:
                return best_key, best_sim
            return None, 0.0


# ══════════════════════════════════════════════════
#  MULTI-TIER CACHE
# ══════════════════════════════════════════════════

def _make_key(query: str) -> str:
    """Deterministic cache key from normalised query text."""
    text = _normalize_vietnamese(query).strip().rstrip("?!.").strip()
    return hashlib.md5(text.encode("utf-8")).hexdigest()


class MultiTierCache:
    """
    Two-tier cache with semantic fallback.

    L1: in-memory LRU  (fast, bounded to *l1_max* entries)
    L2: disk JSON       (persistent, bounded to *l2_max* entries)
    Semantic: if neither L1 nor L2 has an exact key, ask SemanticMatcher.
    """

    def __init__(
        self,
        matcher: SemanticMatcher,
        l1_max: int = 200,
        l2_max: int = 2000,
    ):
        self._lock = Lock()
        self._matcher = matcher
        self._l1_max = l1_max
        self._l2_max = l2_max

        # L1: in-memory OrderedDict (LRU)
        self._l1: OrderedDict[str, dict] = OrderedDict()

        # L2: disk-backed
        self._l2: OrderedDict[str, dict] = OrderedDict()
        self._l2_loaded = False

        # Stats
        self.hits_l1: int = 0
        self.hits_l2: int = 0
        self.hits_semantic: int = 0
        self.misses: int = 0
        self.total_queries: int = 0

    # ── L2 persistence ──

    def _load_l2(self):
        if self._l2_loaded:
            return
        try:
            if ENTRIES_FILE.exists():
                raw = json.loads(ENTRIES_FILE.read_text(encoding="utf-8"))
                entries = raw if isinstance(raw, dict) else {}
                self._l2 = OrderedDict(entries)
                # Rebuild semantic matcher from persisted entries
                for key, entry in self._l2.items():
                    query_text = entry.get("query", "")
                    if query_text:
                        self._matcher.add(key, query_text)
        except Exception as exc:
            logger.warning("Failed to load L2 cache: %s", exc)
        self._l2_loaded = True

    def _save_l2(self):
        try:
            tmp = ENTRIES_FILE.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(dict(self._l2), ensure_ascii=False),
                encoding="utf-8",
            )
            tmp.replace(ENTRIES_FILE)
        except Exception as exc:
            logger.warning("Failed to save L2 cache: %s", exc)

    # ── helpers ──

    @staticmethod
    def _is_expired(entry: dict) -> bool:
        ts = entry.get("timestamp", 0)
        ttl = entry.get("ttl", 3600)
        return (time.time() - ts) >= ttl

    def _evict_l1(self):
        while len(self._l1) > self._l1_max:
            self._l1.popitem(last=False)

    def _evict_l2(self):
        while len(self._l2) > self._l2_max:
            removed_key, _ = self._l2.popitem(last=False)
            self._matcher.remove(removed_key)

    def _promote_to_l1(self, key: str, entry: dict):
        """Promote an L2 entry into L1."""
        self._l1[key] = entry
        self._l1.move_to_end(key)
        self._evict_l1()

    # ── public API ──

    def get(self, query: str) -> dict | None:
        """
        Lookup *query* across L1 -> L2 -> semantic match.

        Returns the cached response dict, or None on miss.
        """
        with self._lock:
            self._load_l2()
            self.total_queries += 1
            key = _make_key(query)

            # --- L1 ---
            if key in self._l1:
                entry = self._l1[key]
                if self._is_expired(entry):
                    self._l1.pop(key, None)
                else:
                    self._l1.move_to_end(key)
                    self.hits_l1 += 1
                    logger.debug("Cache L1 hit: %s", query[:60])
                    return entry.get("response")

            # --- L2 ---
            if key in self._l2:
                entry = self._l2[key]
                if self._is_expired(entry):
                    self._l2.pop(key, None)
                    self._matcher.remove(key)
                    self._save_l2()
                else:
                    self._promote_to_l1(key, entry)
                    self.hits_l2 += 1
                    logger.debug("Cache L2 hit (promoted): %s", query[:60])
                    return entry.get("response")

            # --- Semantic match ---
            matched_key, sim = self._matcher.find_similar(query)
            if matched_key is not None:
                # Try L1 first, then L2
                entry = self._l1.get(matched_key) or self._l2.get(matched_key)
                if entry and not self._is_expired(entry):
                    self._promote_to_l1(matched_key, entry)
                    self.hits_semantic += 1
                    logger.debug(
                        "Cache semantic hit (%.2f): %s -> %s",
                        sim,
                        query[:40],
                        entry.get("query", "")[:40],
                    )
                    return entry.get("response")

            self.misses += 1
            return None

    def put(self, query: str, response: dict, ttl: int = 3600):
        """Store *response* for *query* in both L1 and L2."""
        with self._lock:
            self._load_l2()
            key = _make_key(query)

            entry = {
                "query": query,
                "response": response,
                "timestamp": time.time(),
                "ttl": ttl,
            }

            # L1
            self._l1[key] = entry
            self._l1.move_to_end(key)
            self._evict_l1()

            # L2
            self._l2[key] = entry
            self._l2.move_to_end(key)
            self._evict_l2()

            # Semantic index
            self._matcher.add(key, query)

            self._save_l2()
            logger.debug("Cache put: %s (ttl=%ds)", query[:60], ttl)

    def invalidate(self, query: str):
        """Remove exact cache entry for *query*."""
        with self._lock:
            self._load_l2()
            key = _make_key(query)
            self._l1.pop(key, None)
            removed = self._l2.pop(key, None)
            self._matcher.remove(key)
            if removed:
                self._save_l2()
            logger.debug("Cache invalidate: %s", query[:60])

    def invalidate_entity(self, entity_id: str):
        """Remove all cached entries whose response mentions *entity_id*."""
        with self._lock:
            self._load_l2()
            to_remove: list[str] = []

            for key, entry in list(self._l2.items()):
                resp_str = json.dumps(entry.get("response", {}), ensure_ascii=False)
                if entity_id in resp_str:
                    to_remove.append(key)

            for key in to_remove:
                self._l1.pop(key, None)
                self._l2.pop(key, None)
                self._matcher.remove(key)

            if to_remove:
                self._save_l2()
                logger.info(
                    "Invalidated %d cache entries for entity %s",
                    len(to_remove),
                    entity_id,
                )


# ══════════════════════════════════════════════════
#  REQUEST DEDUPLICATOR
# ══════════════════════════════════════════════════

class RequestDeduplicator:
    """
    Coalesce identical concurrent queries.

    The first caller gets ``(True, dedup_key)`` and should compute the result.
    Subsequent callers within the dedup window receive ``(False, dedup_key)``
    and can wait on :meth:`wait_for` until the first caller calls :meth:`resolve`.
    """

    _WINDOW = 2.0    # seconds — identical queries within this window are deduped
    _EXPIRY = 30.0   # seconds — auto-cleanup threshold

    def __init__(self):
        self._lock = Lock()
        # dedup_key -> {query, timestamp, event: Event, result: dict|None}
        self._pending: dict[str, dict] = {}

    _MAX_PENDING = 500

    def _cleanup(self):
        """Remove stale entries older than _EXPIRY seconds + enforce size cap."""
        now = time.time()
        stale = [
            k for k, v in self._pending.items()
            if now - v["timestamp"] > self._EXPIRY
        ]
        for k in stale:
            self._pending.pop(k, None)
        while len(self._pending) > self._MAX_PENDING:
            oldest = min(self._pending, key=lambda k: self._pending[k]["timestamp"])
            self._pending.pop(oldest, None)

    def acquire(self, query: str, timeout: float = 5.0) -> tuple[bool, str]:
        """
        Acquire dedup slot for *query*.

        Returns:
            (True,  dedup_key) — caller is first; compute the result and call resolve().
            (False, dedup_key) — duplicate; call wait_for() to get the result.
        """
        with self._lock:
            self._cleanup()
            key = _make_key(query)
            now = time.time()

            existing = self._pending.get(key)
            if existing and (now - existing["timestamp"]) < self._WINDOW:
                # Duplicate request within window
                return False, key

            # First request — create slot
            self._pending[key] = {
                "query": query,
                "timestamp": now,
                "event": Event(),
                "result": None,
            }
            return True, key

    def resolve(self, dedup_key: str, result: dict):
        """Store the computed result and wake up all waiters."""
        with self._lock:
            slot = self._pending.get(dedup_key)
            if slot is None:
                return
            slot["result"] = result
            slot["event"].set()

    def wait_for(self, dedup_key: str, timeout: float = 30) -> dict | None:
        """Block until the result is available or *timeout* expires."""
        with self._lock:
            slot = self._pending.get(dedup_key)
        if slot is None:
            return None

        slot["event"].wait(timeout=timeout)
        return slot.get("result")


# ══════════════════════════════════════════════════
#  CACHE WARMER
# ══════════════════════════════════════════════════

# Seasonal queries (Vietnamese tourism, Vinh Long / Mekong Delta focus)
_SEASONAL_QUERIES: dict[int, list[str]] = {
    1: [
        "tet nguyen dan vinh long",
        "le hoi dau nam",
        "cho tet vinh long",
        "hoa tet mekong",
    ],
    2: [
        "le hoi trai cay",
        "mua xuan vinh long",
        "du lich sau tet",
    ],
    3: [
        "mua mang cut",
        "du lich sinh thai",
        "vuon trai cay vinh long",
    ],
    4: [
        "du lich le 30 thang 4",
        "nghi le vinh long",
        "homestay cu lao",
    ],
    5: [
        "mua trai cay he",
        "cu lao an binh",
        "song nuoc mekong",
    ],
    6: [
        "trai cay mua he",
        "di dau thang 6",
        "mua xoai",
        "du lich he vinh long",
        "mua chom chom",
        "homestay mua he",
    ],
    7: [
        "mua sau rieng",
        "du lich mua mua",
        "am thuc vinh long",
    ],
    8: [
        "le vu lan vinh long",
        "du lich gia dinh",
        "mua mang cut thang 8",
    ],
    9: [
        "tet trung thu vinh long",
        "mua thu hoach lua",
        "du lich cuoi he",
    ],
    10: [
        "mua nuoc noi",
        "mua lu mekong",
        "cho noi cai be",
    ],
    11: [
        "du lich cuoi nam",
        "mua cam sanh",
        "thoi tiet vinh long",
    ],
    12: [
        "du lich noel vinh long",
        "mua buoi nam roi",
        "tham quan cuoi nam",
        "chuan bi tet",
    ],
}


class CacheWarmer:
    """Pre-populate the semantic cache with popular and seasonal queries."""

    def __init__(self, cache: MultiTierCache):
        self._cache = cache

    @staticmethod
    def get_popular_queries(limit: int = 20) -> list[str]:
        """Return popular query strings from the analytics module."""
        try:
            try:
                from agent.analytics import get_popular_queries as _gpq
            except ImportError:
                from analytics import get_popular_queries as _gpq
            results = _gpq(limit=limit)
            return [r["query"] for r in results if r.get("query")]
        except Exception as exc:
            logger.debug("Could not load popular queries from analytics: %s", exc)
            return []

    @staticmethod
    def get_seasonal_queries(month: int) -> list[str]:
        """Return pre-defined seasonal queries for the given *month* (1-12)."""
        return list(_SEASONAL_QUERIES.get(month, []))

    def warm(self, call_fn, queries: list[str]):
        """
        Pre-populate the cache by invoking *call_fn(query)* for each query
        that is not already cached.

        Args:
            call_fn: callable(query: str) -> dict  (the knowledge agent handler)
            queries: list of query strings to warm
        """
        warmed = 0
        for query in queries:
            try:
                if self._cache.get(query) is not None:
                    continue  # already cached
                result = call_fn(query)
                if result:
                    self._cache.put(query, result)
                    warmed += 1
            except Exception as exc:
                logger.warning("Cache warm failed for '%s': %s", query[:60], exc)
        logger.info("Cache warmer: warmed %d / %d queries", warmed, len(queries))


# ══════════════════════════════════════════════════
#  MODULE SINGLETONS
# ══════════════════════════════════════════════════

semantic_matcher = SemanticMatcher()
multi_tier_cache = MultiTierCache(matcher=semantic_matcher)
deduplicator = RequestDeduplicator()
cache_warmer = CacheWarmer(cache=multi_tier_cache)


# ══════════════════════════════════════════════════
#  CONVENIENCE FUNCTIONS
# ══════════════════════════════════════════════════

def semantic_get(query: str) -> dict | None:
    """
    Try the semantic cache with request deduplication.

    If a duplicate request is already in-flight, wait for its result
    instead of computing a new one.
    """
    # Check cache first (fast path, no dedup needed)
    cached = multi_tier_cache.get(query)
    if cached is not None:
        return cached

    # Dedup check — if someone else is already computing this query, wait
    is_first, dedup_key = deduplicator.acquire(query)
    if not is_first:
        result = deduplicator.wait_for(dedup_key)
        if result is not None:
            return result

    # Caller is first (or dedup timed out) — no cached result available
    return None


def semantic_put(query: str, response: dict):
    """Store a response in the semantic cache and resolve any dedup waiters."""
    multi_tier_cache.put(query, response)
    # Also resolve dedup waiters
    key = _make_key(query)
    deduplicator.resolve(key, response)


def cache_stats() -> dict:
    """Combined stats from all cache tiers."""
    c = multi_tier_cache
    return {
        "hits_l1": c.hits_l1,
        "hits_l2": c.hits_l2,
        "hits_semantic": c.hits_semantic,
        "misses": c.misses,
        "total_queries": c.total_queries,
        "hit_rate": round(
            (c.hits_l1 + c.hits_l2 + c.hits_semantic)
            / max(c.total_queries, 1),
            4,
        ),
        "l1_size": len(c._l1),
        "l2_size": len(c._l2),
        "semantic_index_size": len(semantic_matcher._vectors),
    }
