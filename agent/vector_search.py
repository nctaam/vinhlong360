"""
vinhlong360 — Vector Search (Semantic Similarity).

Kiến trúc:
  1. TF-IDF local embeddings (không cần API, hoạt động offline)
  2. Vietnamese-aware tokenization (unidecode fallback + bigrams)
  3. Cache embeddings locally (agent/data/embeddings.json)
  4. Tại query time: embed query → cosine similarity → top-K results
  5. Hybrid search: kết hợp keyword score + semantic score

Ưu điểm TF-IDF local:
  - Không phụ thuộc API → zero cost, instant, offline
  - Tối ưu cho domain-specific tourism vocabulary
  - Tự động cập nhật khi knowledge base thay đổi
"""

import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from threading import Lock

# ── Config ──

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
EMBEDDINGS_FILE = DATA_DIR / "embeddings.json"

# Vietnamese stop words (common words that don't carry meaning)
STOP_WORDS = {
    "là", "và", "của", "có", "được", "trong", "một", "các", "với", "cho",
    "này", "đã", "từ", "để", "những", "không", "theo", "tại", "khi", "về",
    "hay", "người", "đến", "nhiều", "như", "cũng", "rất", "còn", "nên",
    "lại", "qua", "sau", "nơi", "bởi", "do", "trên", "dưới", "giữa",
    "vào", "ra", "đó", "ở", "hơn", "cả", "mà", "bị", "đi", "đây",
    "thì", "sẽ", "tới", "nào", "mỗi", "vì", "nếu", "ngay", "lên",
    "the", "and", "of", "in", "a", "to", "is", "for", "with", "on",
}


# ══════════════════════════════════════════════════
#  VIETNAMESE TEXT PROCESSING
# ══════════════════════════════════════════════════

def _normalize_vietnamese(text: str) -> str:
    """Normalize Vietnamese text for tokenization."""
    text = text.lower().strip()
    # Remove special chars but keep Vietnamese diacritics
    text = re.sub(r'[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def _tokenize(text: str) -> list[str]:
    """
    Tokenize Vietnamese text into unigrams + bigrams.
    Bigrams help capture compound words (e.g., 'cù lao', 'bún nước').
    """
    text = _normalize_vietnamese(text)
    words = [w for w in text.split() if w not in STOP_WORDS and len(w) > 1]

    # Unigrams
    tokens = list(words)

    # Bigrams for compound words
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]}_{words[i+1]}")

    return tokens


# ══════════════════════════════════════════════════
#  LIGHTWEIGHT VECTOR MATH (no numpy needed)
# ══════════════════════════════════════════════════

def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    na, nb = _norm(a), _norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return _dot(a, b) / (na * nb)


# ══════════════════════════════════════════════════
#  TF-IDF EMBEDDING STORE
# ══════════════════════════════════════════════════

class TFIDFStore:
    """
    Local TF-IDF vector store for semantic search.

    Uses TF-IDF (Term Frequency - Inverse Document Frequency) to create
    sparse vectors, then computes cosine similarity for search.

    Vietnamese-aware: handles diacritics, compound words via bigrams.
    """

    def __init__(self):
        self._lock = Lock()
        self._loaded = False
        # Core data
        self._vocab: dict[str, int] = {}       # token → index
        self._idf: dict[str, float] = {}       # token → IDF score
        self._vectors: dict[str, list[float]] = {}  # entity_id → TF-IDF vector
        self._texts: dict[str, str] = {}        # entity_id → source text
        self._doc_count: int = 0

    def _load(self):
        """Load cached embeddings from disk."""
        if self._loaded:
            return
        try:
            if EMBEDDINGS_FILE.exists():
                raw = json.loads(EMBEDDINGS_FILE.read_text(encoding="utf-8"))
                if raw.get("type") == "tfidf":
                    self._vocab = raw.get("vocab", {})
                    self._idf = raw.get("idf", {})
                    self._vectors = raw.get("vectors", {})
                    self._texts = raw.get("texts", {})
                    self._doc_count = raw.get("doc_count", 0)
        except Exception:
            pass
        self._loaded = True

    def _save(self):
        """Save embeddings to disk."""
        try:
            data = {
                "type": "tfidf",
                "doc_count": self._doc_count,
                "vocab_size": len(self._vocab),
                "entity_count": len(self._vectors),
                "updated_at": time.strftime("%Y-%m-%d %H:%M"),
                "vocab": self._vocab,
                "idf": self._idf,
                "vectors": self._vectors,
                "texts": self._texts,
            }
            EMBEDDINGS_FILE.write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass

    def build_index(self, entities: dict, force: bool = False):
        """
        Build/update TF-IDF index for all entities.

        Args:
            entities: dict of entity_id -> entity dict
            force: if True, rebuild everything from scratch
        """
        with self._lock:
            self._load()

            # Prepare documents
            docs: dict[str, str] = {}
            for eid, e in entities.items():
                if e.get("type") == "place":
                    continue
                text = f"{e.get('name', '')}. {e.get('summary', '')}"
                # Add type and tags for richer context
                if e.get("type"):
                    text += f" {e['type']}"
                if e.get("tags"):
                    text += " " + " ".join(e["tags"])
                if e.get("season"):
                    text += f" mùa {e['season']}"
                docs[eid] = text

            if not docs:
                return {"status": "no_entities", "total": 0}

            # Check if rebuild needed
            if not force and self._texts == docs and self._vectors:
                return {"status": "up_to_date", "total": len(self._vectors)}

            # Step 1: Tokenize all documents
            doc_tokens: dict[str, list[str]] = {}
            for eid, text in docs.items():
                doc_tokens[eid] = _tokenize(text)

            # Step 2: Build vocabulary
            all_tokens = set()
            for tokens in doc_tokens.values():
                all_tokens.update(tokens)
            self._vocab = {token: idx for idx, token in enumerate(sorted(all_tokens))}

            # Step 3: Compute IDF (Inverse Document Frequency)
            N = len(docs)
            self._doc_count = N
            doc_freq: Counter = Counter()
            for tokens in doc_tokens.values():
                unique_tokens = set(tokens)
                doc_freq.update(unique_tokens)

            self._idf = {}
            for token, freq in doc_freq.items():
                # Smooth IDF: log(N / (1 + df)) + 1
                self._idf[token] = math.log(N / (1 + freq)) + 1

            # Step 4: Compute TF-IDF vectors (sparse → dense)
            self._vectors = {}
            self._texts = docs
            vocab_size = len(self._vocab)

            for eid, tokens in doc_tokens.items():
                if not tokens:
                    continue
                tf = Counter(tokens)
                max_tf = max(tf.values()) if tf else 1

                # Build sparse vector then convert to dense
                vec = [0.0] * vocab_size
                for token, count in tf.items():
                    if token in self._vocab:
                        idx = self._vocab[token]
                        # Augmented TF: 0.5 + 0.5 * (tf / max_tf)
                        normalized_tf = 0.5 + 0.5 * (count / max_tf)
                        vec[idx] = normalized_tf * self._idf.get(token, 1.0)

                # Normalize vector (L2)
                norm = _norm(vec)
                if norm > 0:
                    vec = [v / norm for v in vec]

                self._vectors[eid] = vec

            self._save()
            return {
                "status": "built",
                "entities": len(self._vectors),
                "vocab_size": vocab_size,
                "total": len(self._vectors)
            }

    def _embed_query(self, query: str) -> list[float] | None:
        """Create TF-IDF vector for a query using existing vocabulary."""
        if not self._vocab:
            return None

        tokens = _tokenize(query)
        if not tokens:
            return None

        tf = Counter(tokens)
        max_tf = max(tf.values()) if tf else 1
        vocab_size = len(self._vocab)

        vec = [0.0] * vocab_size
        matched = 0
        for token, count in tf.items():
            if token in self._vocab:
                idx = self._vocab[token]
                normalized_tf = 0.5 + 0.5 * (count / max_tf)
                vec[idx] = normalized_tf * self._idf.get(token, 1.0)
                matched += 1

        if matched == 0:
            return None

        # Normalize
        norm = _norm(vec)
        if norm > 0:
            vec = [v / norm for v in vec]

        return vec

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Semantic search: TF-IDF query → cosine similarity against all entities.

        Returns: [{entity_id, score}, ...] sorted by score descending.
        """
        with self._lock:
            self._load()

        if not self._vectors:
            return []

        query_vec = self._embed_query(query)
        if query_vec is None:
            return []

        # Calculate similarities (sparse dot product optimization)
        scores = []
        for eid, vec in self._vectors.items():
            sim = _dot(query_vec, vec)  # Vectors already normalized → dot = cosine
            if sim > 0.01:  # Skip near-zero
                scores.append({"entity_id": eid, "score": round(sim, 4)})

        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

    def stats(self) -> dict:
        with self._lock:
            self._load()
        return {
            "type": "tfidf",
            "vocab_size": len(self._vocab),
            "total_embeddings": len(self._vectors),
            "doc_count": self._doc_count,
            "file_exists": EMBEDDINGS_FILE.exists(),
            "file_size_kb": round(EMBEDDINGS_FILE.stat().st_size / 1024, 1) if EMBEDDINGS_FILE.exists() else 0,
        }


# Singleton
embedding_store = TFIDFStore()


# ══════════════════════════════════════════════════
#  HYBRID SEARCH
# ══════════════════════════════════════════════════

def hybrid_search(
    query: str,
    keyword_results: list[dict],
    semantic_weight: float = 0.3,
    top_k: int = 10,
) -> list[dict]:
    """
    Combine keyword search results with semantic search.

    Args:
        query: user query string
        keyword_results: results from knowledge.search_entities()
        semantic_weight: weight for semantic score (0-1). Keyword weight = 1 - semantic_weight.
        top_k: number of results to return

    Returns: merged and re-ranked list of entities
    """
    # Get semantic results
    semantic_results = embedding_store.search(query, top_k=top_k * 2)

    if not semantic_results:
        # Fallback: semantic search unavailable, return keyword results as-is
        return keyword_results[:top_k]

    # Build score maps
    keyword_scores = {}
    for i, e in enumerate(keyword_results):
        eid = e.get("id", e.get("entity_id", ""))
        # Normalize rank to 0-1 score (first result = 1.0)
        keyword_scores[eid] = 1.0 - (i / max(len(keyword_results), 1))

    semantic_scores = {}
    for r in semantic_results:
        semantic_scores[r["entity_id"]] = r["score"]

    # Merge all candidate IDs
    all_ids = set(keyword_scores.keys()) | set(semantic_scores.keys())

    # Calculate hybrid scores
    hybrid = []
    kw = 1 - semantic_weight
    sw = semantic_weight
    for eid in all_ids:
        ks = keyword_scores.get(eid, 0)
        ss = semantic_scores.get(eid, 0)
        score = kw * ks + sw * ss
        hybrid.append({"entity_id": eid, "hybrid_score": round(score, 4),
                        "keyword_score": round(ks, 4), "semantic_score": round(ss, 4)})

    hybrid.sort(key=lambda x: x["hybrid_score"], reverse=True)

    # Re-attach full entity data from keyword results
    entity_map = {e.get("id", e.get("entity_id", "")): e for e in keyword_results}

    merged = []
    for h in hybrid[:top_k]:
        eid = h["entity_id"]
        if eid in entity_map:
            merged.append(entity_map[eid])
        else:
            # Entity found by semantic search but not keyword — fetch from knowledge
            try:
                import knowledge
                e = knowledge.get_entity(eid)
                if e:
                    merged.append(e)
            except Exception:
                pass

    return merged


# ══════════════════════════════════════════════════
#  CLI: Build embeddings
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    import knowledge
    knowledge._ensure()

    force = "--force" in sys.argv

    print("Building TF-IDF vector index...")
    print(f"  Entities: {len(knowledge._entities)}")
    print(f"  Force: {force}")
    print()

    result = embedding_store.build_index(knowledge._entities, force=force)
    print(f"Result: {json.dumps(result, indent=2)}")
    print(f"Saved to: {EMBEDDINGS_FILE}")

    if result.get("total", 0) > 0:
        # Quick test
        test_queries = [
            "du lịch sinh thái",
            "đặc sản ẩm thực",
            "chùa Khmer Trà Vinh",
            "cù lao miệt vườn",
        ]
        print("\n-- Quick search test --")
        for q in test_queries:
            results = embedding_store.search(q, top_k=5)
            print(f"\n  Q: {q}")
            for r in results[:3]:
                text = embedding_store._texts.get(r["entity_id"], "")[:60]
                print(f"    {r['score']:.3f}  {r['entity_id']}: {text}")
