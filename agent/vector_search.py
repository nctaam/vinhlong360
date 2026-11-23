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
import logging
import math
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)

# The application historically imports this module both as ``vector_search``
# and ``agent.vector_search``. Register one object under both names so the
# embedding singleton cannot split across retrieval callers.
_module = sys.modules[__name__]
if __name__ == "vector_search":
    sys.modules.setdefault("agent.vector_search", _module)
elif __name__ == "agent.vector_search":
    sys.modules.setdefault("vector_search", _module)

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

_COMBINING_MARKS_RE = re.compile(r"[\u0300-\u036f]")


@lru_cache(maxsize=8192)
def _strip_vietnamese_diacritics(text: str) -> str:
    """Fold Vietnamese diacritics (including đ/Đ) to ASCII base characters."""
    nfkd = unicodedata.normalize("NFKD", text.replace("đ", "d").replace("Đ", "D"))
    return _COMBINING_MARKS_RE.sub("", nfkd)


_STOP_WORDS_FOLDED = frozenset(_strip_vietnamese_diacritics(w) for w in STOP_WORDS)
_NON_VN_WORD_RE = re.compile(
    r"[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]"
)
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_vietnamese(text: str) -> str:
    """Normalize Vietnamese text for tokenization."""
    text = text.lower().strip()
    # Remove special chars but keep Vietnamese diacritics
    text = _NON_VN_WORD_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text

_normalize_vietnamese = normalize_vietnamese


def _append_folded_tokens(
    tokens: list[str], words: list[str], folded_words: list[str] | None = None
) -> None:
    if folded_words is None:
        folded_words = [_strip_vietnamese_diacritics(w) for w in words]
    if folded_words == words:
        return
    for fw, orig in zip(folded_words, words):
        if fw != orig and len(fw) > 1:
            tokens.append(fw)
    for i in range(len(folded_words) - 1):
        fb = f"{folded_words[i]}_{folded_words[i+1]}"
        if fb != f"{words[i]}_{words[i+1]}":
            tokens.append(fb)


def tokenize(text: str) -> list[str]:
    """
    Tokenize Vietnamese text into unigrams + bigrams + unaccented fallback tokens.
    Bigrams help capture compound words (e.g., 'cù lao', 'bún nước').
    """
    text = normalize_vietnamese(text)
    words: list[str] = []
    folded_words: list[str] = []
    for w in text.split():
        if len(w) <= 1 or w in STOP_WORDS:
            continue
        fw = _strip_vietnamese_diacritics(w)
        if fw in _STOP_WORDS_FOLDED:
            continue
        words.append(w)
        folded_words.append(fw)

    # Unigrams
    tokens = list(words)

    # Bigrams for compound words
    for i in range(len(words) - 1):
        tokens.append(f"{words[i]}_{words[i+1]}")

    _append_folded_tokens(tokens, words, folded_words)
    return tokens

_tokenize = tokenize


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

def _build_docs(entities: dict) -> dict[str, str]:
    """Ghép text nguồn cho mỗi entity (bỏ type 'place'). Verbatim từ build_index."""
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
    return docs


def _compute_idf(doc_tokens: dict[str, list[str]], N: int) -> dict[str, float]:
    """Tính IDF trơn log(N/(1+df))+1 cho từng token. Verbatim từ build_index."""
    doc_freq: Counter = Counter()
    for tokens in doc_tokens.values():
        doc_freq.update(set(tokens))

    idf: dict[str, float] = {}
    for token, freq in doc_freq.items():
        # Smooth IDF: log(N / (1 + df)) + 1
        idf[token] = math.log(N / (1 + freq)) + 1
    return idf


def _build_sparse_vectors(
    doc_tokens: dict[str, list[str]], idf: dict[str, float]
) -> dict[str, dict[str, float]]:
    """Dựng vector TF-IDF THƯA (L2-normalized) cho từng entity. Verbatim từ build_index."""
    vectors: dict[str, dict[str, float]] = {}
    for eid, tokens in doc_tokens.items():
        if not tokens:
            continue
        tf = Counter(tokens)
        max_tf = max(tf.values()) if tf else 1

        vec: dict[str, float] = {}
        for token, count in tf.items():
            # Augmented TF: 0.5 + 0.5 * (tf / max_tf)
            normalized_tf = 0.5 + 0.5 * (count / max_tf)
            vec[token] = normalized_tf * idf.get(token, 1.0)

        # Normalize (L2) — chia cho chuẩn trên các giá trị khác 0
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm > 0:
            vec = {t: v / norm for t, v in vec.items()}

        vectors[eid] = vec
    return vectors


_BM25F_FIELD_SPECS: tuple[tuple[str, float, float], ...] = (
    ("name", 3.0, 0.50),
    ("tags_type", 2.0, 0.50),
    ("summary", 1.0, 0.75),
)
_BM25F_K1 = 1.5
_RRF_K = 60.0
_TRIGRAM_MIN_SIM = 0.35


def _char_trigrams(text: str) -> frozenset[str]:
    """Build padded character 3-grams over Vietnamese-folded tokens for fuzzy recovery."""
    folded = _strip_vietnamese_diacritics(normalize_vietnamese(text))
    grams: set[str] = set()
    for word in folded.split():
        if len(word) < 3:
            continue
        padded = f" {word} "
        for idx in range(len(padded) - 2):
            grams.add(padded[idx : idx + 3])
    return frozenset(grams)


def _entity_field_texts(entity: dict) -> dict[str, str]:
    """Extract structured searchable texts per BM25F field."""
    tags = entity.get("tags") or []
    tags_str = " ".join(str(t) for t in tags) if isinstance(tags, list) else str(tags)
    summary = str(entity.get("summary") or "")
    season = entity.get("season")
    if season:
        summary = f"{summary} mùa {season}".strip()
    return {
        "name": str(entity.get("name") or ""),
        "tags_type": f"{entity.get('type') or ''} {tags_str}".strip(),
        "summary": summary,
    }


def _accumulate_doc_bm25f(
    eid: str,
    fields: dict[str, list[str]],
    avg_lens: dict[str, float],
    bm25f_postings: dict[str, list[tuple[str, float]]],
    bm25f_df: Counter,
) -> None:
    """Populate length-normalized BM25F postings for a single entity document."""
    pseudo_tf: dict[str, float] = defaultdict(float)
    for fname, weight, b_val in _BM25F_FIELD_SPECS:
        toks = fields[fname]
        if not toks:
            continue
        dl_norm = (1.0 - b_val) + b_val * (len(toks) / avg_lens[fname])
        scale = weight / max(dl_norm, 0.25)
        for tok, cnt in Counter(toks).items():
            pseudo_tf[tok] += scale * cnt
    for tok, ptf in pseudo_tf.items():
        bm25f_postings[tok].append((eid, ptf))
        bm25f_df[tok] += 1


def _collect_field_postings(
    entities: dict,
) -> tuple[dict[str, list[tuple[str, float]]], dict[str, int], dict[str, frozenset[str]], dict[str, list[str]]]:
    """Build sparse BM25F inverted postings and character 3-gram postings."""
    per_doc_fields: dict[str, dict[str, list[str]]] = {}
    field_totals: Counter = Counter()
    doc_trigrams: dict[str, frozenset[str]] = {}
    trigram_postings: dict[str, list[str]] = defaultdict(list)

    for eid, entity in entities.items():
        if entity.get("type") == "place":
            continue
        texts = _entity_field_texts(entity)
        fields = {fname: tokenize(ftext) for fname, ftext in texts.items()}
        per_doc_fields[eid] = fields
        for fname, toks in fields.items():
            field_totals[fname] += len(toks)
        tri = _char_trigrams(f"{texts['name']} {texts['tags_type']}")
        if tri:
            doc_trigrams[eid] = tri
            for gram in tri:
                trigram_postings[gram].append(eid)

    n_docs = max(len(per_doc_fields), 1)
    avg_lens = {fname: max(field_totals[fname] / n_docs, 1.0) for fname, _, _ in _BM25F_FIELD_SPECS}
    bm25f_postings: dict[str, list[tuple[str, float]]] = defaultdict(list)
    bm25f_df: Counter = Counter()
    for eid, fields in per_doc_fields.items():
        _accumulate_doc_bm25f(eid, fields, avg_lens, bm25f_postings, bm25f_df)

    return dict(bm25f_postings), dict(bm25f_df), doc_trigrams, dict(trigram_postings)


def _score_trigram_candidates(
    query: str,
    trigram_postings: dict[str, list[str]],
    doc_trigrams: dict[str, frozenset[str]],
    excluded_ids: set[str],
) -> dict[str, float]:
    """Recover near-miss typo matches via asymmetric Tversky trigram similarity."""
    q_tris = _char_trigrams(query)
    if not q_tris or not trigram_postings:
        return {}
    overlap_counts: Counter = Counter()
    for gram in q_tris:
        for eid in trigram_postings.get(gram, ()):
            if eid not in excluded_ids:
                overlap_counts[eid] += 1
    recovered: dict[str, float] = {}
    q_len = len(q_tris)
    for eid, inter in overlap_counts.items():
        d_len = len(doc_trigrams.get(eid, ()))
        denom = inter + 0.8 * max(0, q_len - inter) + 0.2 * min(max(0, d_len - inter), q_len)
        sim = inter / denom if denom > 0 else 0.0
        if sim >= _TRIGRAM_MIN_SIM:
            recovered[eid] = round(min(0.45, 0.45 * sim), 4)
    return recovered


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
        # GĐ11.1: vector THƯA (sparse) — chỉ lưu token có trọng số khác 0 thay vì
        # mảng dày vocab_size (~31k) chiều toàn 0 → embeddings.json & RAM giảm mạnh.
        self._idf: dict[str, float] = {}              # token → IDF score
        self._vectors: dict[str, dict[str, float]] = {}  # entity_id → {token: weight} (L2-normalized)
        self._postings: dict[str, list[tuple[str, float]]] = {}  # token → [(entity_id, weight)]
        self._postings_vec_id: int | None = None
        self._postings_vec_len: int = 0
        self._texts: dict[str, str] = {}              # entity_id → source text
        self._doc_count: int = 0
        # BM25F structured field postings & trigram fuzzy index
        self._bm25f_postings: dict[str, list[tuple[str, float]]] = {}
        self._bm25f_df: dict[str, int] = {}
        self._doc_trigrams: dict[str, frozenset[str]] = {}
        self._trigram_postings: dict[str, list[str]] = {}

    def _rebuild_postings(self) -> None:
        postings: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for eid, vec in self._vectors.items():
            for token, weight in vec.items():
                postings[token].append((eid, weight))
        self._postings = dict(postings)
        self._postings_vec_id = id(self._vectors)
        self._postings_vec_len = len(self._vectors)

    def _load(self):
        """Load cached embeddings from disk."""
        if self._loaded:
            return
        try:
            if EMBEDDINGS_FILE.exists():
                raw = json.loads(EMBEDDINGS_FILE.read_text(encoding="utf-8"))
                if raw.get("type") == "tfidf-sparse":
                    self._idf = raw.get("idf", {})
                    self._vectors = raw.get("vectors", {})
                    self._texts = raw.get("texts", {})
                    self._doc_count = raw.get("doc_count", 0)
                    self._rebuild_postings()
                # Định dạng cũ (dense "tfidf") → KHÔNG nạp (tránh phình RAM 208MB);
                # để build_index() dựng lại dạng sparse ở lần build kế tiếp.
        except Exception:
            logger.warning("Failed to load embeddings from %s", EMBEDDINGS_FILE, exc_info=True)
        self._loaded = True

    def _save(self):
        """Save embeddings to disk."""
        try:
            data = {
                "type": "tfidf-sparse",
                "doc_count": self._doc_count,
                "vocab_size": len(self._idf),
                "entity_count": len(self._vectors),
                "updated_at": time.strftime("%Y-%m-%d %H:%M"),
                "idf": self._idf,
                "vectors": self._vectors,
                "texts": self._texts,
            }
            from versioned_json_store import atomic_write_json

            atomic_write_json(EMBEDDINGS_FILE, data, indent=None)
        except Exception:
            logger.error("Failed to save embeddings to %s", EMBEDDINGS_FILE, exc_info=True)

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
            docs = _build_docs(entities)

            if not docs:
                return {"status": "no_entities", "total": 0}

            # Check if rebuild needed
            if not force and self._texts == docs and self._vectors:
                return {"status": "up_to_date", "total": len(self._vectors)}

            # Step 1: Tokenize all documents
            doc_tokens: dict[str, list[str]] = {}
            for eid, text in docs.items():
                doc_tokens[eid] = tokenize(text)

            # Step 2: Compute IDF (Inverse Document Frequency)
            N = len(docs)
            self._doc_count = N
            self._idf = _compute_idf(doc_tokens, N)

            # Step 3: Compute SPARSE TF-IDF vectors ({token: weight}, chỉ token khác 0)
            self._texts = docs
            self._vectors = _build_sparse_vectors(doc_tokens, self._idf)
            self._rebuild_postings()
            (
                self._bm25f_postings,
                self._bm25f_df,
                self._doc_trigrams,
                self._trigram_postings,
            ) = _collect_field_postings(entities)

            self._save()
            return {
                "status": "built",
                "entities": len(self._vectors),
                "vocab_size": len(self._idf),
                "total": len(self._vectors)
            }

    def _embed_query(self, query: str) -> dict[str, float] | None:
        """Tạo vector THƯA {token: weight} cho query dựa trên IDF đã học."""
        if not self._idf:
            return None

        tokens = tokenize(query)
        if not tokens:
            return None

        tf = Counter(tokens)
        max_tf = max(tf.values()) if tf else 1

        vec: dict[str, float] = {}
        for token, count in tf.items():
            # Chỉ giữ token đã biết (có trong IDF) — token lạ không đóng góp similarity
            if token in self._idf:
                normalized_tf = 0.5 + 0.5 * (count / max_tf)
                vec[token] = normalized_tf * self._idf[token]

        if not vec:
            return None

        # Normalize (L2)
        norm = math.sqrt(sum(v * v for v in vec.values()))
        if norm > 0:
            vec = {t: v / norm for t, v in vec.items()}

        return vec

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Field-weighted BM25F + TF-IDF cosine search with 3-gram typo recovery.

        Returns: [{entity_id, score}, ...] sorted by score descending.
        """
        with self._lock:
            self._load()
            if not self._vectors:
                return []
            if (
                self._postings_vec_id != id(self._vectors)
                or self._postings_vec_len != len(self._vectors)
            ):
                self._rebuild_postings()
            query_vec = self._embed_query(query)
            cos_scores = _score_cosine_query(query_vec, self._postings)
            bm25f_scores = _score_bm25f_query(
                tokenize(query), self._bm25f_postings, self._bm25f_df, self._doc_count
            ) if self._bm25f_postings else {}

            merged_scores = _blend_retrieval_scores(bm25f_scores, cos_scores)
            results = [
                {"entity_id": eid, "score": sc}
                for eid, sc in merged_scores.items()
                if sc > 0.01
            ]
            results.sort(key=lambda x: x["score"], reverse=True)
            if len(results) < top_k and self._trigram_postings:
                matched_ids = {r["entity_id"] for r in results}
                fuzzy = _score_trigram_candidates(
                    query, self._trigram_postings, self._doc_trigrams, matched_ids
                )
                extra = [
                    {"entity_id": eid, "score": round(min(0.25, sc * 0.55), 4)}
                    for eid, sc in fuzzy.items()
                ]
                extra.sort(key=lambda x: x["score"], reverse=True)
                results.extend(extra[: max(0, top_k - len(results))])
            return results[:top_k]

    def stats(self) -> dict:
        with self._lock:
            self._load()
        return {
            "type": "tfidf",
            "vocab_size": len(self._idf),
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

def _score_cosine_query(
    query_vec: dict[str, float] | None,
    postings: dict[str, list[tuple[str, float]]],
) -> dict[str, float]:
    """Accumulate sparse cosine similarity scores from inverted postings."""
    if not query_vec:
        return {}
    acc: dict[str, float] = defaultdict(float)
    for token, qw in query_vec.items():
        for eid, w in postings.get(token, ()):
            acc[eid] += qw * w
    return dict(acc)


def _score_bm25f_query(
    query_tokens: list[str],
    bm25f_postings: dict[str, list[tuple[str, float]]],
    bm25f_df: dict[str, int],
    doc_count: int,
) -> dict[str, float]:
    """Compute normalized BM25F field-weighted scores across candidate docs."""
    if not query_tokens or not bm25f_postings or doc_count <= 0:
        return {}
    acc: dict[str, float] = defaultdict(float)
    for qt in dict.fromkeys(query_tokens):
        plist = bm25f_postings.get(qt)
        if not plist:
            continue
        df = bm25f_df.get(qt, 0)
        idf = math.log((doc_count - df + 0.5) / (df + 0.5) + 1.0)
        for eid, ptf in plist:
            acc[eid] += idf * ((ptf * (_BM25F_K1 + 1.0)) / (_BM25F_K1 + ptf))
    return {eid: raw / (raw + 2.0) for eid, raw in acc.items() if raw > 0.0}


def _blend_retrieval_scores(
    bm25f_scores: dict[str, float],
    cos_scores: dict[str, float],
) -> dict[str, float]:
    """Combine normalized BM25F field scores and sparse TF-IDF cosine."""
    if not bm25f_scores:
        return {eid: round(sc, 4) for eid, sc in cos_scores.items()}
    blended: dict[str, float] = {}
    for eid in set(bm25f_scores) | set(cos_scores):
        sc = 0.70 * bm25f_scores.get(eid, 0.0) + 0.30 * cos_scores.get(eid, 0.0)
        blended[eid] = round(sc, 4)
    return blended


def _rrf_blend(
    keyword_results: list[dict],
    semantic_results: list[dict],
    semantic_weight: float,
) -> list[dict]:
    """Fuse keyword and semantic ranked lists via Weighted RRF."""
    kw = 1.0 - semantic_weight
    sw = semantic_weight
    kw_pos = max(len(keyword_results), 1)
    keyword_ranks: dict[str, tuple[int, float]] = {}
    for rank, e in enumerate(keyword_results, 1):
        eid = e.get("id", e.get("entity_id", ""))
        if eid and eid not in keyword_ranks:
            keyword_ranks[eid] = (rank, 1.0 - ((rank - 1) / kw_pos))
    semantic_ranks = {
        r["entity_id"]: (rank, float(r.get("score") or 0.0))
        for rank, r in enumerate(semantic_results, 1)
    }

    hybrid: list[dict] = []
    for eid in set(keyword_ranks) | set(semantic_ranks):
        kr, ks = keyword_ranks.get(eid, (0, 0.0))
        sr, ss = semantic_ranks.get(eid, (0, 0.0))
        rrf = (kw / (_RRF_K + kr) if kr else 0.0) + (sw / (_RRF_K + sr) if sr else 0.0)
        score = rrf + 1e-4 * (kw * ks + sw * ss)
        hybrid.append({"entity_id": eid, "hybrid_score": round(score, 6)})
    hybrid.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return hybrid


def hybrid_search(
    query: str,
    keyword_results: list[dict],
    semantic_weight: float = 0.3,
    top_k: int = 10,
) -> list[dict]:
    """
    Combine keyword search results with semantic search using Weighted RRF.

    Args:
        query: user query string
        keyword_results: results from knowledge.search_entities()
        semantic_weight: weight for semantic leg (0-1). Keyword weight = 1 - semantic_weight.
        top_k: number of results to return

    Returns: merged and re-ranked list of entities
    """
    semantic_results = embedding_store.search(query, top_k=top_k * 2)
    if not semantic_results:
        return keyword_results[:top_k]

    hybrid = _rrf_blend(keyword_results, semantic_results, semantic_weight)
    entity_map = {e.get("id", e.get("entity_id", "")): e for e in keyword_results}
    merged: list[dict] = []
    for h in hybrid[:top_k]:
        eid = h["entity_id"]
        if eid in entity_map:
            merged.append(entity_map[eid])
            continue
        try:
            import knowledge
            entity = knowledge.get_entity(eid)
            if entity:
                merged.append(entity)
        except Exception:
            logger.debug("Could not fetch entity %s from knowledge", eid, exc_info=True)
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
