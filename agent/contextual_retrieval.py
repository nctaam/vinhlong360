"""
vinhlong360 -- Contextual Retrieval & Enhanced Ranking.

Implements three retrieval improvements over the base vector_search:

1. Contextual Embeddings (Anthropic pattern)
   - Enrich entity text with relationship/area context before embedding
   - Produces better vectors than bare entity name + summary

2. BM25 (Okapi) scoring
   - Standard text retrieval scoring with term saturation + length normalization
   - Replaces raw TF-IDF for the keyword leg of hybrid search

3. LLM Reranking
   - Uses the LLM to reorder top candidates by relevance
   - Applied only when rerank=True (expensive)

4. enhanced_hybrid_search()
   - Combines BM25 + TF-IDF semantic + contextual relevance
   - Optional LLM reranking on top results
"""

import json
import math
import os
import re
import time
import logging
from collections import Counter
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

# ── Paths ──

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
CONTEXTUAL_FILE = DATA_DIR / "contextual_texts.json"

# ── Reuse Vietnamese tokenizer from vector_search ──

try:
    from vector_search import tokenize as _tokenize, normalize_vietnamese as _normalize_vietnamese, STOP_WORDS
except ImportError:
    try:
        from agent.vector_search import tokenize as _tokenize, normalize_vietnamese as _normalize_vietnamese, STOP_WORDS
    except ImportError:
        # Inline fallback so module still works standalone
        STOP_WORDS = {
            "la", "va", "cua", "co", "duoc", "trong", "mot", "cac", "voi", "cho",
            "nay", "da", "tu", "de", "nhung", "khong", "theo", "tai", "khi", "ve",
            "hay", "nguoi", "den", "nhieu", "nhu", "cung", "rat", "con", "nen",
            "the", "and", "of", "in", "a", "to", "is", "for", "with", "on",
        }

        def _normalize_vietnamese(text: str) -> str:
            text = text.lower().strip()
            text = re.sub(
                r'[^\w\sà-ưẠ-ỹĐđ]', ' ', text
            )
            return re.sub(r'\s+', ' ', text)

        def _tokenize(text: str) -> list[str]:
            text = _normalize_vietnamese(text)
            words = [w for w in text.split() if w not in STOP_WORDS and len(w) > 1]
            tokens = list(words)
            for i in range(len(words) - 1):
                tokens.append(f"{words[i]}_{words[i + 1]}")
            return tokens


# Reuse TF-IDF store for semantic scores
try:
    from vector_search import embedding_store, cosine_similarity
except ImportError:
    try:
        from agent.vector_search import embedding_store, cosine_similarity
    except ImportError:
        embedding_store = None
        cosine_similarity = None


# =====================================================================
#  1. CONTEXTUAL EMBEDDINGS  (Anthropic Contextual Retrieval pattern)
# =====================================================================

class ContextualRetrieval:
    """
    Implements Anthropic's Contextual Retrieval pattern:
    Before embedding, each entity gets augmented with contextual information
    derived from its relationships and the broader knowledge base.
    """

    def __init__(self):
        self._lock = Lock()
        self._cache: dict[str, str] = {}
        self._loaded = False

    # ── persistence ──

    def _load_cache(self):
        if self._loaded:
            return
        try:
            if CONTEXTUAL_FILE.exists():
                raw = json.loads(CONTEXTUAL_FILE.read_text(encoding="utf-8"))
                self._cache = raw.get("texts", {})
        except Exception as exc:
            logger.warning("contextual cache load failed: %s", exc, exc_info=True)
        self._loaded = True

    def _save_cache(self):
        try:
            data = {
                "updated_at": time.strftime("%Y-%m-%d %H:%M"),
                "count": len(self._cache),
                "texts": self._cache,
            }
            tmp = CONTEXTUAL_FILE.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(CONTEXTUAL_FILE)
        except Exception as exc:
            logger.warning("contextual cache save failed: %s", exc)

    # ── core ──

    def build_contextual_text(
        self, entity: dict, relationships: list
    ) -> str:
        """
        Produce enriched text for a single entity.

        Includes: name, summary, type, related entities, area context.
        Example output:
            "Cam sanh Tam Binh la dac san (product) tai Xa Tam Binh,
             thuoc vung Tam Binh - Tra On. Lien quan den: Vuon cam sanh
             Cai Be, OCOP 4 sao, Mua thu hoach thang 10-12.
             Gan: Cu Lao An Binh, Cho noi Cai Be."
        """
        eid = entity.get("id", "")
        name = entity.get("name", eid)
        summary = entity.get("summary", "")
        etype = entity.get("type", "")
        tags = entity.get("tags", [])
        attrs = entity.get("attributes", {})
        season = entity.get("season")
        location = entity.get("location", {})

        # --- base text ---
        parts: list[str] = []
        loc_name = location.get("name", "") if isinstance(location, dict) else ""
        if loc_name:
            parts.append(f"{name} la {etype} tai {loc_name}.")
        else:
            parts.append(f"{name} ({etype}).")

        if summary:
            parts.append(summary)

        # --- tags ---
        if tags:
            parts.append("Tags: " + ", ".join(tags) + ".")

        # --- OCOP / special attributes ---
        ocop = attrs.get("ocop")
        if ocop:
            parts.append(f"OCOP {ocop} sao.")

        # --- season ---
        if season:
            peak = season.get("peak", [])
            months = season.get("months", [])
            if peak:
                parts.append(
                    "Mua thu hoach (peak): thang " + ", ".join(str(m) for m in peak) + "."
                )
            elif months:
                parts.append(
                    "Mua: thang " + ", ".join(str(m) for m in months) + "."
                )

        # --- relationships ---
        related_names: list[str] = []
        nearby_names: list[str] = []
        for rel in relationships:
            src = rel.get("source", "")
            tgt = rel.get("target", "")
            rtype = rel.get("type", "")
            label = rel.get("label", "")

            partner_id = ""
            if src == eid:
                partner_id = tgt
            elif tgt == eid:
                partner_id = src
            else:
                continue

            display = label if label else partner_id
            if rtype in ("near", "nearby", "adjacent"):
                nearby_names.append(display)
            else:
                related_names.append(display)

        if related_names:
            parts.append("Lien quan den: " + ", ".join(related_names[:8]) + ".")
        if nearby_names:
            parts.append("Gan: " + ", ".join(nearby_names[:6]) + ".")

        return " ".join(parts)

    def build_all_contextual(
        self, entities: dict, relationships: list
    ) -> dict[str, str]:
        """
        Build contextual text for ALL entities and cache to disk.

        Args:
            entities: dict of entity_id -> entity dict
            relationships: list of relationship dicts

        Returns:
            dict of entity_id -> contextual_text
        """
        with self._lock:
            self._load_cache()

            texts: dict[str, str] = {}
            for eid, entity in entities.items():
                if entity.get("type") == "place":
                    continue
                texts[eid] = self.build_contextual_text(entity, relationships)

            self._cache = texts
            self._save_cache()

        return texts

    def get(self, entity_id: str) -> str | None:
        """Return cached contextual text for an entity."""
        with self._lock:
            self._load_cache()
            return self._cache.get(entity_id)


# =====================================================================
#  2. BM25 SCORING
# =====================================================================

class BM25:
    """
    BM25 (Okapi) scoring -- the standard for text retrieval.
    Better than raw TF-IDF because it handles term saturation
    and document length normalization.

    Parameters:
        k1: term frequency saturation (default 1.5)
        b:  document length normalization (default 0.75)
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._lock = Lock()

        # Index state
        self._doc_tokens: dict[str, list[str]] = {}
        self._doc_lens: dict[str, int] = {}
        self._doc_tf: dict[str, Counter] = {}  # GĐ11.3: precompute TF/doc (bỏ Counter() mỗi query)
        self._avg_dl: float = 0.0
        self._df: dict[str, int] = {}   # document frequency per token
        self._N: int = 0                 # total number of documents
        self._built = False

    def build_index(self, documents: dict[str, str]):
        """
        Build BM25 index from document texts.

        Args:
            documents: dict of doc_id -> text content
        """
        with self._lock:
            self._doc_tokens = {}
            self._doc_lens = {}
            self._doc_tf = {}
            df: dict[str, int] = {}
            total_len = 0

            for doc_id, text in documents.items():
                tokens = _tokenize(text)
                self._doc_tokens[doc_id] = tokens
                self._doc_lens[doc_id] = len(tokens)
                self._doc_tf[doc_id] = Counter(tokens)  # GĐ11.3: precompute 1 lần
                total_len += len(tokens)

                unique = set(tokens)
                for t in unique:
                    df[t] = df.get(t, 0) + 1

            self._N = len(documents)
            self._avg_dl = total_len / max(self._N, 1)
            self._df = df
            self._built = True

        logger.info("BM25 index built: %d docs, avg_dl=%.1f", self._N, self._avg_dl)

    def _idf(self, token: str) -> float:
        """IDF with Robertson-Sparck Jones formula."""
        df = self._df.get(token, 0)
        return math.log((self._N - df + 0.5) / (df + 0.5) + 1.0)

    def score(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Score all documents against query using BM25.

        Returns:
            list of {entity_id, score} sorted descending.
        """
        if not self._built:
            return []

        q_tokens = _tokenize(query)
        if not q_tokens:
            return []

        results: list[dict] = []

        with self._lock:
            for doc_id, doc_tf in self._doc_tf.items():  # GĐ11.3: dùng TF precompute
                dl = self._doc_lens.get(doc_id, 0)
                if dl == 0:
                    continue

                s = 0.0
                for qt in q_tokens:
                    if qt not in doc_tf:
                        continue
                    tf = doc_tf[qt]
                    idf = self._idf(qt)
                    # BM25 formula
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (
                        1 - self.b + self.b * (dl / self._avg_dl)
                    )
                    s += idf * (numerator / denominator)

                if s > 0.001:
                    results.append({"entity_id": doc_id, "score": round(s, 4)})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]


# =====================================================================
#  3. LLM RERANKER
# =====================================================================

class LLMReranker:
    """
    Uses the LLM to rerank search results based on query relevance.
    Only applied to top candidates (expensive, so limit to top 10-20).
    """

    def __init__(self):
        self._client = None
        self._model: str = ""

    def _ensure_client(self):
        """Lazy-init the OpenAI-compatible client."""
        if self._client is not None:
            return
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package required for LLM reranking")

        api_key = os.environ.get("LLM_API_KEY", "")
        base_url = os.environ.get("LLM_BASE_URL", "")
        self._model = os.environ.get("LLM_MODEL_MINI", "cx/gpt-5.4-mini")

        if not api_key or not base_url:
            raise RuntimeError("LLM_API_KEY and LLM_BASE_URL must be set for reranking")

        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=15)

    def rerank(
        self, query: str, candidates: list[dict], top_k: int = 5
    ) -> list[dict]:
        """
        Rerank candidates using the LLM.

        Args:
            query: the user query
            candidates: list of entity dicts (must have 'id' and 'name')
            top_k: number of results to return

        Returns:
            reranked list of entity dicts, best first
        """
        if not candidates:
            return []
        if len(candidates) <= 1:
            return candidates[:top_k]

        try:
            self._ensure_client()
        except RuntimeError as exc:
            logger.warning("LLM reranker unavailable: %s", exc)
            return candidates[:top_k]

        # Build candidate list for prompt
        lines: list[str] = []
        for i, c in enumerate(candidates):
            name = c.get("name", c.get("id", f"item_{i}"))
            summary = c.get("summary", "")[:120]
            etype = c.get("type", "")
            lines.append(f"{i + 1}. [{etype}] {name}: {summary}")

        candidate_block = "\n".join(lines)

        prompt = (
            f"Given this user query about Vinh Long tourism:\n"
            f'  "{query}"\n\n'
            f"Rank the following search results from MOST to LEAST relevant. "
            f"Return ONLY a comma-separated list of numbers (e.g. 3,1,5,2,4). "
            f"No explanation.\n\n"
            f"Results:\n{candidate_block}"
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=100,
                timeout=15,  # P1-2: rerank — tránh treo
            )
            ranking_text = response.choices[0].message.content.strip()

            # Parse ordering
            indices = []
            for tok in re.split(r'[,\s]+', ranking_text):
                tok = tok.strip().rstrip(".")
                if tok.isdigit():
                    idx = int(tok) - 1  # 1-based -> 0-based
                    if 0 <= idx < len(candidates) and idx not in indices:
                        indices.append(idx)

            # Any candidates not mentioned go at the end in original order
            for i in range(len(candidates)):
                if i not in indices:
                    indices.append(i)

            reranked = [candidates[i] for i in indices]
            return reranked[:top_k]

        except Exception as exc:
            logger.warning("LLM rerank failed, using original order: %s", exc)
            return candidates[:top_k]


# =====================================================================
#  4. ENHANCED HYBRID SEARCH
# =====================================================================

def enhanced_hybrid_search(
    query: str,
    keyword_results: list[dict],
    entities: dict,
    relationships: list,
    *,
    bm25_weight: float = 0.4,
    semantic_weight: float = 0.3,
    contextual_weight: float = 0.3,
    rerank: bool = False,
    top_k: int = 10,
) -> list[dict]:
    """
    Enhanced hybrid search combining three signal sources:

      - BM25 score      (term-level relevance with saturation)
      - TF-IDF semantic  (cosine similarity from vector_search)
      - Contextual score  (similarity on enriched contextual texts)

    Optionally applies LLM reranking on the merged top results.

    Falls back gracefully if any component is unavailable.

    Args:
        query: user query string
        keyword_results: results from knowledge.search_entities()
        entities: full entity dict (id -> entity)
        relationships: list of relationship dicts
        bm25_weight: weight for BM25 score
        semantic_weight: weight for TF-IDF semantic score
        contextual_weight: weight for contextual relevance
        rerank: if True, apply LLM reranking on merged results
        top_k: number of results to return

    Returns:
        list of entity dicts, ranked by combined score
    """
    candidate_pool = top_k * 3  # fetch more candidates for merging

    # ── 1. BM25 scores ──
    bm25_scores: dict[str, float] = {}
    try:
        if bm25._built:
            bm25_raw = bm25.score(query, top_k=candidate_pool)
            if bm25_raw:
                max_bm25 = bm25_raw[0]["score"] if bm25_raw else 1.0
                for r in bm25_raw:
                    # Normalize to 0-1
                    bm25_scores[r["entity_id"]] = r["score"] / max(max_bm25, 0.001)
    except Exception as exc:
        logger.debug("BM25 unavailable: %s", exc)

    # ── 2. TF-IDF semantic scores ──
    semantic_scores: dict[str, float] = {}
    try:
        if embedding_store is not None:
            sem_raw = embedding_store.search(query, top_k=candidate_pool)
            for r in sem_raw:
                semantic_scores[r["entity_id"]] = r["score"]
    except Exception as exc:
        logger.debug("Semantic search unavailable: %s", exc)

    # ── 3. Contextual scores ──
    ctx_scores: dict[str, float] = {}
    try:
        ctx_texts = contextual._cache
        if ctx_texts:
            q_tokens = set(_tokenize(query))
            if q_tokens:
                for eid, ctx_text in ctx_texts.items():
                    doc_tokens = set(_tokenize(ctx_text))
                    if not doc_tokens:
                        continue
                    # Jaccard-like overlap on enriched text
                    overlap = len(q_tokens & doc_tokens)
                    if overlap > 0:
                        union = len(q_tokens | doc_tokens)
                        ctx_scores[eid] = overlap / max(union, 1)
    except Exception as exc:
        logger.debug("Contextual scoring unavailable: %s", exc)

    # ── 4. Keyword results as positional scores ──
    keyword_scores: dict[str, float] = {}
    for i, e in enumerate(keyword_results):
        eid = e.get("id", e.get("entity_id", ""))
        keyword_scores[eid] = 1.0 - (i / max(len(keyword_results), 1))

    # ── Merge all candidate IDs ──
    all_ids = (
        set(keyword_scores.keys())
        | set(bm25_scores.keys())
        | set(semantic_scores.keys())
        | set(ctx_scores.keys())
    )

    # ── Determine effective weights ──
    # If a signal source is empty, redistribute its weight
    available_weight = 0.0
    has_bm25 = bool(bm25_scores)
    has_semantic = bool(semantic_scores)
    has_ctx = bool(ctx_scores)

    if has_bm25:
        available_weight += bm25_weight
    if has_semantic:
        available_weight += semantic_weight
    if has_ctx:
        available_weight += contextual_weight

    if available_weight <= 0:
        # None of the enhanced signals available -- fall back to keyword
        return keyword_results[:top_k]

    # Scale weights so they sum to 1
    scale = 1.0 / available_weight
    w_bm25 = (bm25_weight * scale) if has_bm25 else 0
    w_sem = (semantic_weight * scale) if has_semantic else 0
    w_ctx = (contextual_weight * scale) if has_ctx else 0

    # ── Compute hybrid scores ──
    hybrid: list[dict] = []
    for eid in all_ids:
        s = 0.0
        s += w_bm25 * bm25_scores.get(eid, 0)
        s += w_sem * semantic_scores.get(eid, 0)
        s += w_ctx * ctx_scores.get(eid, 0)

        hybrid.append({
            "entity_id": eid,
            "hybrid_score": round(s, 4),
            "bm25_score": round(bm25_scores.get(eid, 0), 4),
            "semantic_score": round(semantic_scores.get(eid, 0), 4),
            "contextual_score": round(ctx_scores.get(eid, 0), 4),
        })

    hybrid.sort(key=lambda x: x["hybrid_score"], reverse=True)

    # ── Re-attach full entity data ──
    entity_map = {e.get("id", e.get("entity_id", "")): e for e in keyword_results}
    # Also include entities from the full entities dict
    for eid in all_ids:
        if eid not in entity_map and eid in entities:
            entity_map[eid] = entities[eid]

    merged: list[dict] = []
    for h in hybrid[:candidate_pool]:
        eid = h["entity_id"]
        if eid in entity_map:
            merged.append(entity_map[eid])

    # ── Optional LLM reranking ──
    reranked = False
    if rerank and len(merged) > 1:
        try:
            merged = reranker.rerank(query, merged, top_k=top_k)
            reranked = True
        except Exception as exc:
            logger.warning("Reranking failed, using score-based order: %s", exc)
            merged = merged[:top_k]
    else:
        merged = merged[:top_k]

    # Attach degradation metadata so callers know which signals contributed.
    for item in merged:
        item["_search_meta"] = {
            "has_bm25": has_bm25,
            "has_semantic": has_semantic,
            "has_contextual": has_ctx,
            "reranked": reranked,
        }

    return merged


# =====================================================================
#  5. MODULE SINGLETONS
# =====================================================================

contextual = ContextualRetrieval()
bm25 = BM25()
reranker = LLMReranker()  # lazy, only calls LLM when rerank=True


def search_health() -> dict:
    """Quick readiness probe for the search pipeline."""
    return {
        "bm25_ready": bm25._built,
        "bm25_doc_count": len(bm25._doc_lengths) if bm25._built else 0,
        "contextual_loaded": contextual._loaded,
        "contextual_doc_count": len(contextual._cache) if contextual._loaded else 0,
        "embedding_store_ready": embedding_store is not None,
    }


# =====================================================================
#  CLI TEST
# =====================================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    import knowledge
    knowledge._ensure()

    entities = knowledge._entities
    relationships = knowledge._relationships

    print("=" * 60)
    print("  Contextual Retrieval - Build & Test")
    print("=" * 60)

    # ── 1. Build contextual texts ──
    print("\n[1] Building contextual texts...")
    ctx_texts = contextual.build_all_contextual(entities, relationships)
    print(f"    Built {len(ctx_texts)} contextual texts")
    print(f"    Cached to: {CONTEXTUAL_FILE}")

    # Show a few examples
    for eid in list(ctx_texts.keys())[:3]:
        text = ctx_texts[eid]
        print(f"\n    {eid}:")
        print(f"      {text[:150]}...")

    # ── 2. Build BM25 index ──
    print("\n[2] Building BM25 index...")
    docs = {}
    for eid, e in entities.items():
        if e.get("type") == "place":
            continue
        ctx = ctx_texts.get(eid, "")
        if ctx:
            docs[eid] = ctx
        else:
            docs[eid] = f"{e.get('name', '')}. {e.get('summary', '')}"
    bm25.build_index(docs)
    print(f"    Indexed {bm25._N} documents, avg_dl={bm25._avg_dl:.1f}")

    # ── 3. Test queries ──
    test_queries = [
        "du lich sinh thai",
        "dac san am thuc Vinh Long",
        "chua Khmer",
        "cu lao miet vuon",
        "cam sanh",
    ]

    print("\n[3] BM25 search tests:")
    for q in test_queries:
        results = bm25.score(q, top_k=5)
        print(f"\n  Q: {q}")
        for r in results[:3]:
            name = entities.get(r["entity_id"], {}).get("name", r["entity_id"])
            print(f"    {r['score']:.3f}  {name}")

    # ── 4. Enhanced hybrid search ──
    print("\n[4] Enhanced hybrid search tests:")
    # Build TF-IDF index if not built
    try:
        from vector_search import embedding_store as es
        es.build_index(entities)
    except Exception:
        pass

    for q in test_queries[:3]:
        # Simulate keyword results (take first few entities as placeholder)
        kw_results = list(entities.values())[:20]
        results = enhanced_hybrid_search(
            q, kw_results, entities, relationships,
            rerank=False, top_k=5,
        )
        print(f"\n  Q: {q}")
        for r in results[:3]:
            print(f"    {r.get('name', r.get('id', '?'))}")

    # ── 5. LLM Reranker (only if env is set) ──
    if os.environ.get("LLM_API_KEY"):
        print("\n[5] LLM Reranker test:")
        q = "cho noi Vinh Long"
        kw_results = list(entities.values())[:10]
        results = enhanced_hybrid_search(
            q, kw_results, entities, relationships,
            rerank=True, top_k=5,
        )
        print(f"  Q: {q}")
        for r in results[:3]:
            print(f"    {r.get('name', r.get('id', '?'))}")
    else:
        print("\n[5] LLM Reranker: skipped (LLM_API_KEY not set)")

    print("\nDone.")
