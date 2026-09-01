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

import asyncio
from contextlib import contextmanager
import hashlib
import json
import logging
import math
import os
import time
from collections import Counter, OrderedDict
from collections.abc import Mapping
from contextvars import ContextVar
from pathlib import Path
from threading import Event, Lock, RLock

from owner_write_gate import owner_write_gate

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


@contextmanager
def _interprocess_file_lock(path: Path):
    """Serialize cache manifest reads/writes across worker processes."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            handle.write(b"0")
            handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


# ══════════════════════════════════════════════════
#  SEMANTIC MATCHER
# ══════════════════════════════════════════════════

class SemanticMatcher:
    """TF-IDF sparse-vector matcher for cached queries."""

    def __init__(self):
        self._lock = RLock()
        # query_key -> sparse vector
        self._vectors: dict[str, dict[str, float]] = {}
        # query_key -> original query text
        self._texts: dict[str, str] = {}
        # query_key -> owner namespace (empty string is the legacy namespace)
        self._owners: dict[str, str] = {}
        # token -> document frequency (number of queries containing this token)
        self._df: Counter = Counter()
        self._doc_count: int = 0
        self.replacements: int = 0

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

    def add(self, key: str, query: str, owner_key: str = ""):
        """Add a query to the matcher index."""
        with self._lock:
            if key in self._vectors:
                # Remove the old document first; otherwise every cache overwrite
                # inflates document frequency and progressively corrupts IDF.
                old_vec = self._vectors.pop(key)
                for token in set(old_vec):
                    self._df[token] = max(0, self._df.get(token, 1) - 1)
                self._doc_count = max(0, self._doc_count - 1)
                self.replacements += 1
                self._texts.pop(key, None)
                self._owners.pop(key, None)
            vec = self._vectorize(query)
            if not vec:
                return
            self._vectors[key] = vec
            self._texts[key] = query
            self._owners[key] = owner_key
            # Update document frequency
            for token in set(vec.keys()):
                self._df[token] += 1
            self._doc_count += 1

    def remove(self, key: str):
        """Remove a query from the matcher index."""
        with self._lock:
            vec = self._vectors.pop(key, None)
            self._texts.pop(key, None)
            self._owners.pop(key, None)
            if vec:
                for token in set(vec.keys()):
                    self._df[token] = max(0, self._df.get(token, 1) - 1)
                self._doc_count = max(0, self._doc_count - 1)

    def rebuild(self, entries: Mapping[str, dict]) -> None:
        """Replace the in-memory index with a merged disk manifest."""
        with self._lock:
            self._vectors.clear()
            self._texts.clear()
            self._owners.clear()
            self._df.clear()
            self._doc_count = 0
            for key, entry in entries.items():
                query_text = entry.get("query", "") if isinstance(entry, dict) else ""
                if query_text:
                    self.add(key, query_text, owner_key=entry.get("owner_key", ""))

    def find_similar(
        self,
        query: str,
        threshold: float = 0.88,
        owner_key: str = "",
    ) -> tuple[str | None, float]:
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
                if self._owners.get(key, "") != owner_key:
                    continue
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

def _make_key(
    query: str,
    owner_key: str = "",
    *,
    entity_id: str | None = None,
    generation: int | None = None,
) -> str:
    """Deterministic cache key from normalised query text."""
    text = _normalize_vietnamese(query).strip().rstrip("?!.").strip()
    key_input = text if not owner_key else f"{owner_key}:{text}"
    if entity_id is not None:
        key_input = f"entity:{entity_id}:generation:{generation if generation is not None else 0}:{key_input}"
    return hashlib.md5(key_input.encode("utf-8")).hexdigest()


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
        # Distinguish a real manifest load from tests/callers that mark the
        # cache loaded to intentionally avoid disk I/O.
        self._l2_loaded_from_disk = False
        self._l2_mtime_ns: int | None = None
        # Deletions are persisted as records so an older worker cannot
        # resurrect a value after another worker invalidates it.
        self._tombstones: dict[str, dict] = {}
        self._known_versions: dict[str, int] = {}
        self._dirty_keys: set[str] = set()
        self._version_counter = time.time_ns()

        # Stats
        self.hits_l1: int = 0
        self.hits_l2: int = 0
        self.hits_semantic: int = 0
        self.misses: int = 0
        self.total_queries: int = 0
        self.replacements: int = 0

    # ── L2 persistence ──

    def _load_l2(self, *, force: bool = False):
        if self._l2_loaded and not force:
            return
        self._l2_loaded_from_disk = True
        try:
            with _interprocess_file_lock(ENTRIES_FILE):
                if ENTRIES_FILE.exists():
                    raw = json.loads(ENTRIES_FILE.read_text(encoding="utf-8"))
                    records = raw if isinstance(raw, dict) else {}
                else:
                    records = {}
                entries = {
                    key: value
                    for key, value in records.items()
                    if isinstance(value, dict) and not value.get("deleted")
                }
                self._tombstones = {
                    key: value
                    for key, value in records.items()
                    if isinstance(value, dict) and value.get("deleted")
                }
                self._known_versions = {
                    key: int(value.get("version", 0) or 0)
                    for key, value in records.items()
                    if isinstance(value, dict)
                }
                self._l2 = OrderedDict(entries)
                # A forced manifest refresh must invalidate any L1 snapshot
                # that is absent or older than the disk record.
                if force and self._l1:
                    for key, entry in list(self._l1.items()):
                        current = entries.get(key)
                        if current is None or current != entry:
                            self._l1.pop(key, None)
                # Rebuild semantic state for both populated and deleted manifests.
                self._matcher.rebuild(self._l2)
                self._l2_mtime_ns = ENTRIES_FILE.stat().st_mtime_ns if ENTRIES_FILE.exists() else None
        except Exception as exc:
            logger.warning("Failed to load L2 cache: %s", exc)
        self._l2_loaded = True

    def _next_version(self) -> int:
        self._version_counter = max(self._version_counter + 1, time.time_ns())
        return self._version_counter

    def _save_l2(self, *, merge_disk: bool = True, deleted_keys: set[str] | None = None):
        try:
            with _interprocess_file_lock(ENTRIES_FILE):
                # Merge with the latest on-disk manifest while holding the lock,
                # preventing one worker from erasing another worker's entry.
                merged: dict[str, dict] = {}
                if merge_disk and self._l2_loaded_from_disk and ENTRIES_FILE.exists():
                    raw = json.loads(ENTRIES_FILE.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        merged.update({k: v for k, v in raw.items() if isinstance(v, dict)})
                elif not self._l2_loaded_from_disk:
                    # Test/local-only caches intentionally bypass disk; retain
                    # their complete in-memory manifest across saves.
                    merged.update(self._l2)
                    merged.update(self._tombstones)

                local_records = dict(self._l2)
                local_records.update(self._tombstones)
                for key in deleted_keys or ():
                    local_records[key] = self._tombstones.get(key, {"deleted": True, "version": self._next_version()})

                # Compare dirty writes against the version observed when this
                # worker loaded the manifest.  A changed remote record wins.
                for key in self._dirty_keys | set(deleted_keys or ()):
                    local = local_records.get(key)
                    remote = merged.get(key)
                    expected = self._known_versions.get(key, 0)
                    remote_version = int(remote.get("version", 0) or 0) if isinstance(remote, dict) else 0
                    # An explicit delete must win when this worker observed
                    # the key as absent, even if another worker created it
                    # before the delete reached the manifest.
                    local_delete_of_unknown_key = bool(
                        local and local.get("deleted") and expected == 0
                    )
                    if (
                        remote_version != expected
                        and (remote is not None or expected != 0)
                        and not local_delete_of_unknown_key
                    ):
                        if remote is None or remote.get("deleted"):
                            self._l2.pop(key, None)
                            if remote is None:
                                self._tombstones[key] = {"deleted": True, "version": remote_version}
                            else:
                                self._tombstones[key] = remote
                            self._l1.pop(key, None)
                            self._matcher.remove(key)
                        else:
                            self._l2[key] = remote
                            self._tombstones.pop(key, None)
                            self._promote_to_l1(key, remote)
                            self._matcher.rebuild(self._l2)
                        continue
                    if local is not None:
                        if "version" not in local:
                            local = {**local, "version": self._next_version()}
                            if local.get("deleted"):
                                self._tombstones[key] = local
                            else:
                                self._l2[key] = local
                        merged[key] = local

                self._l2 = OrderedDict(
                    (key, value)
                    for key, value in merged.items()
                    if isinstance(value, dict) and not value.get("deleted")
                )
                self._tombstones = {
                    key: value for key, value in merged.items()
                    if isinstance(value, dict) and value.get("deleted")
                }
                self._matcher.rebuild(self._l2)
                tmp = ENTRIES_FILE.with_suffix(".tmp")
                records = dict(self._l2)
                records.update(self._tombstones)
                tmp.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
                tmp.replace(ENTRIES_FILE)
                self._l2_mtime_ns = ENTRIES_FILE.stat().st_mtime_ns
                self._known_versions = {
                    key: int(value.get("version", 0) or 0)
                    for key, value in records.items()
                    if isinstance(value, dict)
                }
                self._dirty_keys.clear()
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

    def get(self, query: str, owner_key: str = "", *, entity_id: str | None = None,
            generation: int | None = None) -> dict | None:
        """
        Lookup *query* across L1 -> L2 -> semantic match.

        Returns the cached response dict, or None on miss.
        """
        with self._lock:
            self._load_l2()
            current_mtime = ENTRIES_FILE.stat().st_mtime_ns if ENTRIES_FILE.exists() else None
            if self._l2_loaded_from_disk and current_mtime != self._l2_mtime_ns:
                self._load_l2(force=True)
            self.total_queries += 1
            key = _make_key(query, owner_key=owner_key, entity_id=entity_id, generation=generation)

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
                    self._save_l2(deleted_keys={key})
                else:
                    self._promote_to_l1(key, entry)
                    self.hits_l2 += 1
                    logger.debug("Cache L2 hit (promoted): %s", query[:60])
                    return entry.get("response")

            # --- Semantic match ---
            matched_key, sim = self._matcher.find_similar(
                query,
                owner_key=owner_key,
            )
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

    def put(
        self,
        query: str,
        response: dict,
        ttl: int = 3600,
        owner_key: str = "",
        *,
        entity_id: str | None = None,
        generation: int | None = None,
    ):
        """Store *response* for *query* in both L1 and L2."""
        owner_write_gate.assert_writable(owner_key)
        with self._lock:
            self._load_l2()
            key = _make_key(query, owner_key=owner_key, entity_id=entity_id, generation=generation)

            entry = {
                "query": query,
                "owner_key": owner_key,
                "entity_id": entity_id,
                "generation": generation,
                "response": response,
                "timestamp": time.time(),
                "ttl": ttl,
                "version": self._next_version(),
            }

            # A tombstone or newer remote value observed by _save_l2 wins over
            # this worker's stale write; mark the key so the merge performs CAS.
            self._tombstones.pop(key, None)
            self._dirty_keys.add(key)

            # L1
            self._l1[key] = entry
            self._l1.move_to_end(key)
            self._evict_l1()

            # L2
            self._l2[key] = entry
            self._l2.move_to_end(key)
            self._evict_l2()

            # Semantic index
            self._matcher.add(key, query, owner_key=owner_key)
            self.replacements = self._matcher.replacements

            self._save_l2()
            logger.debug("Cache put: %s (ttl=%ds)", query[:60], ttl)

    def invalidate(self, query: str, owner_key: str = ""):
        """Remove exact cache entry for *query*."""
        with self._lock:
            self._load_l2()
            key = _make_key(query, owner_key=owner_key)
            self._l1.pop(key, None)
            self._l2.pop(key, None)
            self._tombstones[key] = {"deleted": True, "version": self._next_version()}
            self._dirty_keys.add(key)
            self._matcher.remove(key)
            self._save_l2(deleted_keys={key})
            logger.debug("Cache invalidate: %s", query[:60])

    def purge_owner(self, owner_key: str) -> int:
        """Remove an exact owner's logical entries from every cache tier."""
        with self._lock:
            self._load_l2()
            keys = {
                key
                for layer in (self._l1, self._l2)
                for key, entry in layer.items()
                if entry.get("owner_key", "") == owner_key
            }
            with self._matcher._lock:
                keys.update(
                    key
                    for key, stored_owner in self._matcher._owners.items()
                    if stored_owner == owner_key
                )

            removed_l2 = False
            for key in keys:
                self._l1.pop(key, None)
                if self._l2.pop(key, None) is not None:
                    removed_l2 = True
                self._tombstones[key] = {"deleted": True, "version": self._next_version()}
                self._dirty_keys.add(key)
                self._matcher.remove(key)
            if removed_l2 or keys:
                self._save_l2(deleted_keys=keys)
            return len(keys)

    def verify_owner_absent(self, owner_key: str) -> bool:
        """Verify all active and persisted cache tiers lack the exact owner."""
        with self._lock:
            self._load_l2()
            if any(
                entry.get("owner_key", "") == owner_key
                for layer in (self._l1, self._l2)
                for entry in layer.values()
            ):
                return False
            with self._matcher._lock:
                if owner_key in self._matcher._owners.values():
                    return False
            if not ENTRIES_FILE.exists():
                return True
            data = json.loads(ENTRIES_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Invalid semantic cache store")
            return not any(
                isinstance(entry, dict)
                and entry.get("owner_key", "") == owner_key
                for entry in data.values()
            )

    def invalidate_all_namespaces(self, query: str) -> int:
        """Remove an exact query from every owner and legacy namespace."""
        with self._lock:
            self._load_l2()
            keys_to_remove: set[str] = set()

            for layer in (self._l1, self._l2):
                for key, entry in layer.items():
                    owner_key = entry.get("owner_key", "") or ""
                    if key == _make_key(query, owner_key=owner_key):
                        keys_to_remove.add(key)

            removed_l2 = False
            for key in keys_to_remove:
                self._l1.pop(key, None)
                if self._l2.pop(key, None) is not None:
                    removed_l2 = True
                self._tombstones[key] = {"deleted": True, "version": self._next_version()}
                self._dirty_keys.add(key)
                self._matcher.remove(key)

            if removed_l2 or keys_to_remove:
                self._save_l2(deleted_keys=keys_to_remove)
            logger.debug(
                "Cache invalidated across %d namespaces: %s",
                len(keys_to_remove),
                query[:60],
            )
            return len(keys_to_remove)

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
                self._tombstones[key] = {"deleted": True, "version": self._next_version()}
                self._dirty_keys.add(key)
                self._matcher.remove(key)

            if to_remove:
                self._save_l2(deleted_keys=set(to_remove))
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
    Subsequent callers share the unresolved active generation. Resolved slots
    remain reusable within the short dedup window, then roll to a fresh key.
    """

    _WINDOW = 2.0    # seconds — identical queries within this window are deduped
    _EXPIRY = 30.0   # seconds — auto-cleanup threshold

    def __init__(self):
        self._lock = Lock()
        # generation_key -> {base_key, query, timestamp, event, waiters, result}
        self._pending: dict[str, dict] = {}
        self._active: dict[str, str] = {}
        self._generation = 0

    _MAX_PENDING = 500

    def _evict_locked(self, dedup_key: str) -> list[tuple]:
        slot = self._pending.pop(dedup_key, None)
        if slot is None:
            return []
        base_key = slot.get("base_key")
        if base_key and self._active.get(base_key) == dedup_key:
            self._active.pop(base_key, None)
        event = slot.get("event")
        if event is not None:
            event.set()
        async_waiters = list(slot.get("async_waiters", {}).values())
        slot.get("async_waiters", {}).clear()
        return async_waiters

    def _cleanup_locked(self) -> list[tuple]:
        now = time.time()
        stale = [
            k for k, v in self._pending.items()
            if now - v["timestamp"] > self._EXPIRY
        ]
        async_waiters = []
        for k in stale:
            async_waiters.extend(self._evict_locked(k))
        while len(self._pending) > self._MAX_PENDING:
            oldest = min(self._pending, key=lambda k: self._pending[k]["timestamp"])
            async_waiters.extend(self._evict_locked(oldest))
        return async_waiters

    def _notify_async_waiters(self, async_waiters: list[tuple], result):
        for loop, future in async_waiters:
            try:
                loop.call_soon_threadsafe(
                    self._set_async_result,
                    future,
                    result,
                )
            except RuntimeError:
                continue

    def _cleanup(self):
        """Remove stale entries older than _EXPIRY seconds + enforce size cap."""
        with self._lock:
            async_waiters = self._cleanup_locked()
        self._notify_async_waiters(async_waiters, None)

    def purge_owner(self, owner_key: str) -> int:
        """Evict an owner's in-flight generations and wake every waiter."""
        with self._lock:
            keys = [
                key
                for key, slot in self._pending.items()
                if slot.get("owner_key", "") == owner_key
            ]
            async_waiters = []
            for key in keys:
                async_waiters.extend(self._evict_locked(key))
        self._notify_async_waiters(async_waiters, None)
        return len(keys)

    def verify_owner_absent(self, owner_key: str) -> bool:
        with self._lock:
            return not any(
                slot.get("owner_key", "") == owner_key
                for slot in self._pending.values()
            )

    def acquire(
        self,
        query: str,
        timeout: float = 5.0,
        owner_key: str = "",
    ) -> tuple[bool, str]:
        """
        Acquire dedup slot for *query*.

        Returns:
            (True,  dedup_key) — caller is first; compute the result and call resolve().
            (False, dedup_key) — duplicate; call wait_for() to get the result.
        """
        owner_write_gate.assert_writable(owner_key)
        with self._lock:
            async_waiters = self._cleanup_locked()
            base_key = _make_key(query, owner_key=owner_key)
            now = time.time()

            active_key = self._active.get(base_key)
            existing = self._pending.get(active_key) if active_key else None
            if existing and (
                existing.get("result") is None
                or (now - existing["timestamp"]) < self._WINDOW
            ):
                # Duplicate request within window
                outcome = (False, active_key)

            # First request — create slot
            else:
                self._generation += 1
                generation_key = f"{base_key}:{self._generation:x}"
                self._pending[generation_key] = {
                    "base_key": base_key,
                    "query": query,
                    "owner_key": owner_key,
                    "timestamp": now,
                    "event": Event(),
                    "async_waiters": {},
                    "result": None,
                }
                self._active[base_key] = generation_key
                outcome = (True, generation_key)

        self._notify_async_waiters(async_waiters, None)
        return outcome

    def resolve(self, dedup_key: str, result: dict, owner_key: str = ""):
        """Store the computed result and wake up all waiters."""
        owner_write_gate.assert_writable(owner_key)
        with self._lock:
            slot = self._pending.get(dedup_key)
            if slot is None:
                return
            if slot.get("owner_key", "") != owner_key:
                return
            slot["result"] = result
            slot["event"].set()
            async_waiters = list(slot.get("async_waiters", {}).values())
            slot.get("async_waiters", {}).clear()

        self._notify_async_waiters(async_waiters, result)

    def resolve_if_active(
        self,
        dedup_key: str,
        result: dict,
        owner_key: str = "",
    ) -> bool:
        """Resolve only when *dedup_key* is still the active generation."""
        owner_write_gate.assert_writable(owner_key)
        with self._lock:
            slot = self._pending.get(dedup_key)
            if slot is None or slot.get("owner_key", "") != owner_key:
                return False
            if self._active.get(slot.get("base_key")) != dedup_key:
                return False
            slot["result"] = result
            slot["event"].set()
            async_waiters = list(slot.get("async_waiters", {}).values())
            slot.get("async_waiters", {}).clear()

        self._notify_async_waiters(async_waiters, result)
        return True

    def abandon_if_active(self, dedup_key: str, owner_key: str = "") -> bool:
        """Evict one unresolved active generation and wake its waiters."""
        with self._lock:
            slot = self._pending.get(dedup_key)
            if slot is None or slot.get("owner_key", "") != owner_key:
                return False
            if slot.get("result") is not None:
                return False
            if self._active.get(slot.get("base_key")) != dedup_key:
                return False
            async_waiters = self._evict_locked(dedup_key)

        self._notify_async_waiters(async_waiters, None)
        return True

    def resolve_active(
        self,
        base_key: str,
        result: dict,
        owner_key: str = "",
    ) -> bool:
        with self._lock:
            dedup_key = self._active.get(base_key)
        if dedup_key is None:
            return False
        return self.resolve_if_active(dedup_key, result, owner_key=owner_key)

    def publish_if_active(
        self,
        dedup_key: str,
        result: dict,
        publish_fn,
        owner_key: str = "",
    ) -> bool:
        """Validate, publish, and resolve one generation under the slot lock."""
        owner_write_gate.assert_writable(owner_key)
        with self._lock:
            slot = self._pending.get(dedup_key)
            if slot is None or slot.get("owner_key", "") != owner_key:
                return False
            if self._active.get(slot.get("base_key")) != dedup_key:
                return False
            publish_fn()
            slot["result"] = result
            slot["event"].set()
            async_waiters = list(slot.get("async_waiters", {}).values())
            slot.get("async_waiters", {}).clear()

        self._notify_async_waiters(async_waiters, result)
        return True

    def publish_active(
        self,
        base_key: str,
        result: dict,
        publish_fn,
        owner_key: str = "",
    ) -> bool | None:
        """Publish the active generation, or return ``None`` when absent."""
        owner_write_gate.assert_writable(owner_key)
        with self._lock:
            dedup_key = self._active.get(base_key)
            if dedup_key is None:
                return None
            slot = self._pending.get(dedup_key)
            if slot is None or slot.get("owner_key", "") != owner_key:
                return False
            publish_fn()
            slot["result"] = result
            slot["event"].set()
            async_waiters = list(slot.get("async_waiters", {}).values())
            slot.get("async_waiters", {}).clear()

        self._notify_async_waiters(async_waiters, result)
        return True

    @staticmethod
    def _set_async_result(future, result: dict | None):
        if not future.done():
            future.set_result(result)

    def wait_for(self, dedup_key: str, timeout: float = 30) -> dict | None:
        """Block until the result is available or *timeout* expires."""
        with self._lock:
            slot = self._pending.get(dedup_key)
        if slot is None:
            return None

        slot["event"].wait(timeout=timeout)
        return slot.get("result")

    async def wait_for_async(
        self,
        dedup_key: str,
        timeout: float = 30,
    ) -> dict | None:
        """Wait without occupying a thread from the event loop's executor."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        waiter_id = id(future)

        with self._lock:
            slot = self._pending.get(dedup_key)
            if slot is None:
                return None
            if slot.get("result") is not None:
                return slot["result"]
            slot.setdefault("async_waiters", {})[waiter_id] = (loop, future)

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            with self._lock:
                slot = self._pending.get(dedup_key)
                if slot is not None:
                    slot.setdefault("async_waiters", {}).pop(waiter_id, None)


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
_semantic_dedup_lease: ContextVar[tuple[str, str] | None] = ContextVar(
    "semantic_dedup_lease",
    default=None,
)
_DEDUP_KEY_OMITTED = object()


# ══════════════════════════════════════════════════
#  CONVENIENCE FUNCTIONS
# ══════════════════════════════════════════════════

def semantic_get(query: str, owner_key: str = "") -> dict | None:
    """
    Try the semantic cache with request deduplication.

    If a duplicate request is already in-flight, wait for its result
    instead of computing a new one.
    """
    _semantic_dedup_lease.set(None)
    # Check cache first (fast path, no dedup needed)
    cached = multi_tier_cache.get(query, owner_key=owner_key)
    if cached is not None:
        return cached

    # Dedup check — if someone else is already computing this query, wait
    is_first, dedup_key = deduplicator.acquire(query, owner_key=owner_key)
    _semantic_dedup_lease.set((_make_key(query, owner_key=owner_key), dedup_key))
    if not is_first:
        try:
            result = deduplicator.wait_for(dedup_key)
        except BaseException:
            _semantic_dedup_lease.set(None)
            raise
        if result is not None:
            _semantic_dedup_lease.set(None)
            return result

    # Caller is first (or dedup timed out) — no cached result available
    return None


async def semantic_get_async(query: str, owner_key: str = "") -> dict | None:
    """Async semantic lookup that keeps duplicate waits off the event loop."""
    _semantic_dedup_lease.set(None)
    cached = multi_tier_cache.get(query, owner_key=owner_key)
    if cached is not None:
        return cached

    is_first, dedup_key = deduplicator.acquire(query, owner_key=owner_key)
    _semantic_dedup_lease.set((_make_key(query, owner_key=owner_key), dedup_key))
    if not is_first:
        try:
            result = await deduplicator.wait_for_async(dedup_key)
        except BaseException:
            _semantic_dedup_lease.set(None)
            raise
        if result is not None:
            _semantic_dedup_lease.set(None)
            return result

    return None


def semantic_take_dedup_lease(query: str, owner_key: str = "") -> str | None:
    """Take the current lookup's generation lease for deferred publication."""
    base_key = _make_key(query, owner_key=owner_key)
    lease = _semantic_dedup_lease.get()
    _semantic_dedup_lease.set(None)
    if lease is None or lease[0] != base_key:
        return None
    return lease[1]


def semantic_abandon(
    query: str,
    owner_key: str = "",
    dedup_key: str | None = None,
) -> bool:
    """Abandon an exact semantic generation without publishing cache data."""
    base_key = _make_key(query, owner_key=owner_key)
    lease = _semantic_dedup_lease.get()
    if (
        lease is not None
        and lease[0] == base_key
        and (dedup_key is None or lease[1] == dedup_key)
    ):
        _semantic_dedup_lease.set(None)
    if dedup_key is None:
        return False
    return deduplicator.abandon_if_active(dedup_key, owner_key=owner_key)


def semantic_put(
    query: str,
    response: dict,
    owner_key: str = "",
    dedup_key: str | None | object = _DEDUP_KEY_OMITTED,
):
    """Publish only for the active generation and resolve its waiters."""
    owner_write_gate.assert_writable(owner_key)
    base_key = _make_key(query, owner_key=owner_key)
    lease = _semantic_dedup_lease.get()
    _semantic_dedup_lease.set(None)
    if dedup_key is None:
        return False
    if dedup_key is _DEDUP_KEY_OMITTED:
        if lease is not None and lease[0] == base_key:
            dedup_key = lease[1]
        else:
            dedup_key = None

    def publish_fn():
        multi_tier_cache.put(query, response, owner_key=owner_key)
    if dedup_key is not None:
        return deduplicator.publish_if_active(
            dedup_key,
            response,
            publish_fn,
            owner_key=owner_key,
        )

    published = deduplicator.publish_active(
        base_key,
        response,
        publish_fn,
        owner_key=owner_key,
    )
    if published is None:
        publish_fn()
        return True
    return published


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
        "cache_replacements": c.replacements,
    }
