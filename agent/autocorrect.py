"""
vinhlong360 — Vietnamese-aware smart autocorrect.

Sửa lỗi chính tả tiếng Việt cho các thuật ngữ du lịch
Vĩnh Long / Bến Tre / Trà Vinh trước khi đưa vào Knowledge Agent.

Tính năng:
  - Từ điển 60+ thuật ngữ du lịch phổ biến
  - Fuzzy matching (Levenshtein) — pure Python, không phụ thuộc ngoài
  - Chuẩn hóa tiếng Việt (bỏ dấu) để so sánh
  - Thread-safe, pre-compute lookup tables
  - Hỗ trợ input có dấu lẫn không dấu
"""

import logging
import unicodedata
from threading import Lock

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════
#  VIETNAMESE NORMALIZATION
# ══════════════════════════════════════════════════

# Map Vietnamese characters with diacritics to base ASCII.
# Pre-computed for performance — covers all common Vietnamese vowels + đ.
_VN_DIACRITICS_MAP: dict[str, str] = {}


def _build_diacritics_map():
    """Build a lookup table mapping accented Vietnamese chars to ASCII."""
    global _VN_DIACRITICS_MAP
    # We rely on Unicode NFD decomposition for vowels, plus manual đ→d.
    # This is built once at import time.
    _VN_DIACRITICS_MAP = {"đ": "d", "Đ": "D"}


_build_diacritics_map()


def normalize_vietnamese(text: str) -> str:
    """
    Remove Vietnamese diacritics for comparison.

    Converts accented characters to their ASCII equivalents:
      - ă, â, á, à, ả, ã, ạ → a
      - ê, é, è, ẻ, ẽ, ẹ   → e
      - ô, ơ, ó, ò, ỏ, õ, ọ → o
      - ư, ú, ù, ủ, ũ, ụ   → u
      - í, ì, ỉ, ĩ, ị      → i
      - ý, ỳ, ỷ, ỹ, ỵ      → y
      - đ                    → d

    Args:
        text: Input Vietnamese text (with or without diacritics).

    Returns:
        Lowercase ASCII string with all diacritics removed.
    """
    if not text:
        return ""
    s = text.lower()
    # Replace đ/Đ before NFD decomposition (đ does not decompose)
    s = s.replace("đ", "d")
    # NFD decomposes accented chars into base + combining marks
    s = unicodedata.normalize("NFD", s)
    # Strip all combining marks (category M = Mark)
    s = "".join(c for c in s if unicodedata.category(c)[0] != "M")
    return s


# ══════════════════════════════════════════════════
#  LEVENSHTEIN DISTANCE (pure Python)
# ══════════════════════════════════════════════════

def _levenshtein(s1: str, s2: str) -> int:
    """
    Compute the Levenshtein edit distance between two strings.

    Pure Python implementation using a single-row dynamic programming
    approach for O(min(m,n)) memory.

    Args:
        s1: First string.
        s2: Second string.

    Returns:
        Integer edit distance.
    """
    if s1 == s2:
        return 0
    len1, len2 = len(s1), len(s2)
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    # Ensure s1 is the shorter string for memory efficiency
    if len1 > len2:
        s1, s2 = s2, s1
        len1, len2 = len2, len1

    prev_row = list(range(len1 + 1))
    for j in range(1, len2 + 1):
        curr_row = [j] + [0] * len1
        for i in range(1, len1 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            curr_row[i] = min(
                curr_row[i - 1] + 1,       # insertion
                prev_row[i] + 1,            # deletion
                prev_row[i - 1] + cost,     # substitution
            )
        prev_row = curr_row

    return prev_row[len1]


# ══════════════════════════════════════════════════
#  MISSPELLING DICTIONARY
# ══════════════════════════════════════════════════

# Each entry maps a normalized (no-diacritics, lowercase) key to the
# correct Vietnamese form.  Multi-word phrases are supported — the
# matcher scans for longest-match-first.

_TOURISM_CORRECTIONS: dict[str, str] = {
    # ── Địa danh (Place names) ──
    "vinh long": "Vĩnh Long",
    "vinh log": "Vĩnh Long",
    "ving long": "Vĩnh Long",
    "vinlong": "Vĩnh Long",
    "vinh lon": "Vĩnh Long",
    "ben tre": "Bến Tre",
    "ben che": "Bến Tre",
    "bentre": "Bến Tre",
    "tra vinh": "Trà Vinh",
    "tra ving": "Trà Vinh",
    "travinh": "Trà Vinh",
    "tam binh": "Tam Bình",
    "binh minh": "Bình Minh",
    "binh tan": "Bình Tân",
    "tra on": "Trà Ôn",
    "tra ong": "Trà Ôn",
    "vung liem": "Vũng Liêm",
    "vung lim": "Vũng Liêm",
    "mang thit": "Mang Thít",
    "long ho": "Long Hồ",
    "an binh": "An Bình",
    "cho lach": "Chợ Lách",
    "mo cay": "Mỏ Cày",
    "cau ke": "Cầu Kè",
    "duyen hai": "Duyên Hải",
    "my tho": "Mỹ Tho",
    "can tho": "Cần Thơ",
    "my hoa": "Mỹ Hòa",

    # ── Cù lao / đảo ──
    "cu lao": "cù lao",
    "cu lao an binh": "cù lao An Bình",
    "cu lao may": "cù lao Mây",
    "cu lao tan quy": "cù lao Tân Quy",
    "cu lao long tri": "cù lao Long Trị",
    "con phung": "Cồn Phụng",
    "con chim": "Cồn Chim",
    "con cu": "Cồn Cù",

    # ── Ẩm thực (Food & dishes) ──
    "bun nuoc leo": "bún nước lèo",
    "bun nuoc le": "bún nước lèo",
    "bun nuoclao": "bún nước lèo",
    "bun suong": "bún suông",
    "banh trang": "bánh tráng",
    "banh trang cu lao may": "bánh tráng cù lao Mây",
    "banh tet": "bánh tét",
    "banh tet tra cuon": "bánh tét Trà Cuôn",
    "banh dan gian": "bánh dân gian",
    "com nieu": "cơm niêu",
    "com nieu nam bo": "cơm niêu Nam Bộ",
    "com tam": "cơm tấm",
    "pho 91": "Phở 91",
    "ca tai tuong": "cá tai tượng",
    "ca tai tuong chien xu": "cá tai tượng chiên xù",
    "lau ga noi": "lẩu gà nòi",
    "mam song khoai lang": "mắm sống khoai lang",
    "mam tep chua": "mắm tép chua",
    "bun mam": "bún mắm",
    "bun dau mam tom": "bún đậu mắm tôm",
    "lo com": "lò cơm",
    "lo com cuu long": "lò cơm Cửu Long",
    "tau hu ky": "tàu hủ ky",
    "tau hu ky my hoa": "tàu hủ ky Mỹ Hòa",

    # ── Đặc sản / sản phẩm (Products) ──
    "cam sanh": "cam sành",
    "cam sanh tam binh": "cam sành Tam Bình",
    "cam san tam bin": "cam sành Tam Bình",
    "buoi nam roi": "bưởi Năm Roi",
    "buoi nam roi binh minh": "bưởi Năm Roi Bình Minh",
    "buoi da xanh": "bưởi da xanh",
    "buoi da xanh cho lach": "bưởi da xanh Chợ Lách",
    "keo dua": "kẹo dừa",
    "keo dua ben tre": "kẹo dừa Bến Tre",
    "keo dua mo cay": "kẹo dừa Mỏ Cày",
    "mat hoa dua": "mật hoa dừa",
    "dua xieng xanh": "dừa xiêm xanh",
    "dua xiêm xanh": "dừa xiêm xanh",
    "dua sap": "dừa sáp",
    "dua sap cau ke": "dừa sáp Cầu Kè",
    "ruou dua": "rượu dừa",
    "ruou dua ben tre": "rượu dừa Bến Tre",
    "tinh dau dua": "tinh dầu dừa",
    "tinh dau dua ben tre": "tinh dầu dừa Bến Tre",
    "com dep": "cốm dẹp",
    "com dep khmer": "cốm dẹp Khmer",
    "sau rieng": "sầu riêng",
    "sau rieng ri6": "sầu riêng Ri6",
    "chom chom": "chôm chôm",
    "khoai lang tim": "khoai lang tím",
    "khoai lang tim nhat binh tan": "khoai lang tím Nhật Bình Tân",
    "thanh tra": "thanh trà",
    "thanh tra binh minh": "thanh trà Bình Minh",
    "nem vung liem": "nem Vũng Liêm",
    "tom duyen hai": "tôm Duyên Hải",

    # ── Chợ nổi / sông nước ──
    "cho noi": "chợ nổi",
    "cho noi tra on": "chợ nổi Trà Ôn",
    "miet vuon": "miệt vườn",
    "miet vuon an binh": "miệt vườn An Bình",
    "song co chien": "sông Cổ Chiên",
    "song tien": "sông Tiền",
    "song hau": "sông Hậu",
    "mua nuoc noi": "mùa nước nổi",

    # ── Văn hóa / tâm linh ──
    "chua khmer": "chùa Khmer",
    "chua khmer vinh long": "chùa Khmer Vĩnh Long",
    "chua ang": "chùa Âng",
    "chua vam ray": "chùa Vàm Ray",
    "chua phat ngoc xa loi": "chùa Phật Ngọc Xá Lợi",
    "chua phuoc hau": "chùa Phước Hậu",
    "chua tien chau": "chùa Tiên Châu",
    "chua long buu": "chùa Long Bửu",
    "chua hang": "chùa Hang",
    "chua ong met": "chùa Ông Mẹt",
    "chua kompong": "chùa Kompong",
    "chua ba thien hau": "chùa Bà Thiên Hậu",
    "chua co": "chùa Cò",
    "ao ba om": "Ao Bà Om",
    "van thanh mieu": "Văn Thánh Miếu",
    "van thanh mieu vinh long": "Văn Thánh Miếu Vĩnh Long",
    "dinh long thanh": "đình Long Thành",
    "dinh tan hoa": "đình Tân Hòa",
    "dao dua": "Đạo Dừa",
    "thien vien truc lam": "Thiền viện Trúc Lâm",
    "thien vien truc lam tra vinh": "Thiền viện Trúc Lâm Trà Vinh",
    "den tho bac ho": "Đền thờ Bác Hồ",

    # ── Đờn ca tài tử & nghệ thuật ──
    "don ca tai tu": "đờn ca tài tử",
    "don ca tai tu nam bo": "đờn ca tài tử Nam bộ",
    "don ca tai tu vinh long": "đờn ca tài tử Vĩnh Long",
    "hat boi": "hát bội",
    "hat boi vinh long": "hát bội Vĩnh Long",
    "cai luong": "cải lương",
    "mua chan": "múa chằn",
    "dua ghe ngo": "đua ghe Ngo",

    # ── Lễ hội (Festivals) ──
    "ok om bok": "Ok Om Bok",
    "le hoi ok om bok": "Lễ hội Ok Om Bok",
    "sen dolta": "Sen Dolta",
    "chol chnam thmay": "Chôl Chnăm Thmây",
    "le hoi lang ong": "lễ hội Lăng Ông",
    "ngay hoi thanh tra": "Ngày hội Thanh trà",

    # ── Làng nghề (Craft villages) ──
    "lang nghe gach gom mang thit": "làng nghề gạch gốm Mang Thít",
    "lang gach gom": "làng gạch gốm",
    "gach gom mang thit": "gạch gốm Mang Thít",
    "lang tau hu ky": "làng tàu hủ ky",
    "lang keo dua": "làng kẹo dừa",
    "lang banh trang": "làng bánh tráng",
    "nha gom tu buoi": "nhà gốm Tư Bưởi",
    "lo gach gom": "lò gạch gốm",

    # ── Du lịch / trải nghiệm ──
    "du lich sinh thai": "du lịch sinh thái",
    "vuon trai cay": "vườn trái cây",
    "hai chom chom": "hái chôm chôm",
    "hai cam": "hái cam",
    "cheo xuong": "chèo xuồng",
    "dap xe": "đạp xe",
    "lam nong dan": "làm nông dân",
    "thu hoach dua": "thu hoạch dừa",
    "binh minh song co chien": "bình minh sông Cổ Chiên",
    "homestay": "homestay",
    "homstay": "homestay",
    "home stay": "homestay",

    # ── Địa điểm du lịch ──
    "vinh sang": "Vinh Sang",
    "khu du lich vinh sang": "Khu du lịch Vinh Sang",
    "cau my thuan": "Cầu Mỹ Thuận",
    "nha co huynh thuy le": "nhà cổ Huỳnh Thủy Lê",
    "nha co cai cuong": "nhà cổ Cai Cường",
    "bao tang vinh long": "Bảo tàng Vĩnh Long",
    "bao tang khmer": "Bảo tàng Văn hóa dân tộc Khmer",
    "bien ba dong": "biển Ba Động",
    "canh dong dieu": "cánh đồng diều",
    "rung duoc": "rừng đước",
    "peace farm": "Peace Farm",
    "cocohome": "CocoHome",
    "nha dua cocohome": "nhà dừa CocoHome",
    "s'mo farm": "S'Mo Farm",
    "sala": "Sala",

    # ── Nhân vật lịch sử ──
    "vo van kiet": "Võ Văn Kiệt",
    "pham hung": "Phạm Hùng",
    "nguyen dinh chieu": "Nguyễn Đình Chiểu",
    "nguyen thi dinh": "Nguyễn Thị Định",
    "tran dai nghia": "Trần Đại Nghĩa",
    "ut tra on": "Út Trà Ôn",
    "thoai ngoc hau": "Thoại Ngọc Hầu",
    "tong huu dinh": "Tống Hữu Định",

    # ── Thuật ngữ chung ──
    "am thuc": "ẩm thực",
    "van hoa": "văn hóa",
    "lich su": "lịch sử",
    "du lich": "du lịch",
    "le hoi": "lễ hội",
    "dac san": "đặc sản",
    "lang nghe": "làng nghề",
    "mien tay": "miền Tây",
    "nam bo": "Nam Bộ",
    "dong bang song cuu long": "Đồng bằng sông Cửu Long",
    "dbscl": "Đồng bằng sông Cửu Long",
    "ocop": "OCOP",
}

# ══════════════════════════════════════════════════
#  PRE-COMPUTED LOOKUP STRUCTURES
# ══════════════════════════════════════════════════

# Sorted by phrase length descending so longest match wins
_SORTED_KEYS: list[tuple[str, str]] = []

# Normalized key → correction (for fast exact lookup)
_NORM_LOOKUP: dict[str, str] = {}

_init_lock = Lock()
_initialized = False


def _init_lookups():
    """Pre-compute lookup tables from the correction dictionary."""
    global _SORTED_KEYS, _NORM_LOOKUP, _initialized
    with _init_lock:
        if _initialized:
            return
        # Build sorted keys: longest phrases first for greedy matching
        _SORTED_KEYS = sorted(
            _TOURISM_CORRECTIONS.items(),
            key=lambda kv: len(kv[0]),
            reverse=True,
        )
        # Build normalized lookup: normalize both key and value's
        # normalized form so we can match input that already has diacritics
        _NORM_LOOKUP = {}
        for key, val in _TOURISM_CORRECTIONS.items():
            norm_key = normalize_vietnamese(key)
            _NORM_LOOKUP[norm_key] = val
            # Also store the key as-is (it should already be normalized,
            # but be safe)
            if key != norm_key:
                _NORM_LOOKUP[key] = val
        _initialized = True


# Initialize on import
_init_lookups()


# ══════════════════════════════════════════════════
#  ENTITY NAME FUZZY MATCHING
# ══════════════════════════════════════════════════

_entity_names: list[str] = []
_entity_names_normalized: list[tuple[str, str]] = []  # (normalized, original)
_entity_lock = Lock()


def load_entity_names(entities: dict):
    """
    Load entity names from the knowledge base for fuzzy matching.

    Args:
        entities: Dict mapping entity_id to entity dict. Each entity
                  must have a "name" key.  Typically sourced from
                  ``knowledge._entities``.

    Example::

        import knowledge
        knowledge._ensure()
        autocorrect.load_entity_names(knowledge._entities)
    """
    global _entity_names, _entity_names_normalized
    with _entity_lock:
        names = []
        for eid, e in entities.items():
            name = e.get("name", "").strip()
            if name and e.get("type") != "place":
                names.append(name)
        _entity_names = names
        _entity_names_normalized = [
            (normalize_vietnamese(n), n) for n in names
        ]


def _fuzzy_match_entity(word: str, max_distance: int = 2) -> str | None:
    """
    Find the closest entity name for a single word/phrase using Levenshtein.

    Only considers entity names whose normalized length is close to the
    input length (within max_distance) to avoid expensive comparisons.

    Args:
        word: Normalized input word/phrase to match.
        max_distance: Maximum allowed edit distance per word.

    Returns:
        The original (with-diacritics) entity name, or None if no match
        within tolerance.
    """
    if not _entity_names_normalized or not word:
        return None

    best_name = None
    best_dist = max_distance + 1

    word_len = len(word)
    for norm_name, orig_name in _entity_names_normalized:
        # Skip if length difference already exceeds max_distance
        if abs(len(norm_name) - word_len) > max_distance:
            continue
        dist = _levenshtein(word, norm_name)
        if dist < best_dist:
            best_dist = dist
            best_name = orig_name
            if dist == 0:
                break

    return best_name if best_dist <= max_distance else None


def _fuzzy_match_words(text: str, max_distance: int = 2) -> str | None:
    """
    Try to fuzzy-match multi-word input against entity names.

    Strategy: slide a window of 1..4 words across the input and check
    each window against entity names.  Return the best match.

    Args:
        text: Normalized input text.
        max_distance: Maximum Levenshtein distance per match.

    Returns:
        Corrected entity name, or None.
    """
    if not _entity_names_normalized or not text:
        return None

    words = text.split()
    if not words:
        return None

    best_match = None
    best_dist = max_distance + 1

    # Try windows of decreasing size (prefer longer matches)
    max_window = min(len(words), 6)
    for window_size in range(max_window, 0, -1):
        for start in range(len(words) - window_size + 1):
            window_text = " ".join(words[start:start + window_size])
            window_len = len(window_text)

            for norm_name, orig_name in _entity_names_normalized:
                if abs(len(norm_name) - window_len) > max_distance:
                    continue
                dist = _levenshtein(window_text, norm_name)
                if dist < best_dist:
                    best_dist = dist
                    best_match = orig_name
                    if dist == 0:
                        return best_match

    return best_match if best_dist <= max_distance else None


# ══════════════════════════════════════════════════
#  CAPITALIZATION PRESERVATION
# ══════════════════════════════════════════════════

def _apply_capitalization(original: str, replacement: str) -> str:
    """
    Apply the capitalization style of *original* to *replacement*.

    Heuristics:
      - ALL CAPS → return replacement in UPPER
      - all lower → return replacement as-is (trust dictionary casing
        which reflects correct Vietnamese orthography: proper nouns
        like place names stay capitalized)
      - First char upper → capitalize first char of replacement
      - Otherwise → return replacement as-is

    Args:
        original: The original (misspelled) text showing user's casing style.
        replacement: The corrected Vietnamese text.

    Returns:
        Replacement with capitalization adjusted to match original's style.
    """
    if not original or not replacement:
        return replacement
    if original.isupper():
        return replacement.upper()
    if original.islower():
        # Trust the dictionary's casing — it preserves proper nouns
        # (e.g., "cho noi tra on" → "chợ nổi Trà Ôn", not all-lower)
        return replacement
    if original[0].isupper() and not replacement[0].isupper():
        # User typed "Cam sanh" → capitalize first char of replacement
        return replacement[0].upper() + replacement[1:]
    return replacement


# ══════════════════════════════════════════════════
#  MAIN AUTOCORRECT FUNCTION
# ══════════════════════════════════════════════════

def autocorrect(text: str) -> dict:
    """
    Autocorrect Vietnamese tourism terms in the input text.

    Performs three passes:
      1. **Dictionary exact match** (longest-phrase-first, greedy).
      2. **Fuzzy entity match** (Levenshtein on loaded entity names).
      3. Compile corrections list.

    Args:
        text: User input text (may contain misspellings, missing
              diacritics, mixed language, etc.).

    Returns:
        A dict with:
          - ``original`` (str): The input text unchanged.
          - ``corrected`` (str): Text with corrections applied.
          - ``corrections`` (list[dict]): Each correction as
            ``{"from": str, "to": str}``.
          - ``was_corrected`` (bool): Whether any correction was made.

    Example::

        >>> autocorrect("toi muon di cho noi tra on va an bun nuoc leo")
        {
            "original": "toi muon di cho noi tra on va an bun nuoc leo",
            "corrected": "toi muon di chợ nổi Trà Ôn va an bún nước lèo",
            "corrections": [
                {"from": "cho noi tra on", "to": "chợ nổi Trà Ôn"},
                {"from": "bun nuoc leo", "to": "bún nước lèo"},
            ],
            "was_corrected": True,
        }
    """
    if not text or not text.strip():
        return {
            "original": text or "",
            "corrected": text or "",
            "corrections": [],
            "was_corrected": False,
        }

    original = text
    corrected = text
    corrections: list[dict] = []

    # ── Pass 1: Dictionary-based correction (longest match first) ──
    corrected, dict_corrections = _apply_dictionary_corrections(corrected)
    corrections.extend(dict_corrections)

    # ── Pass 2: Fuzzy entity matching on remaining uncorrected segments ──
    if _entity_names_normalized:
        corrected, fuzzy_corrections = _apply_fuzzy_corrections(
            corrected, already_corrected=dict_corrections
        )
        corrections.extend(fuzzy_corrections)

    return {
        "original": original,
        "corrected": corrected,
        "corrections": corrections,
        "was_corrected": len(corrections) > 0,
    }


def _apply_dictionary_corrections(text: str) -> tuple[str, list[dict]]:
    """
    Apply dictionary-based corrections to text.

    Uses normalized (no-diacritics) comparison to match input against
    the correction dictionary.  Longest phrases are tried first so
    "cho noi tra on" matches before "cho noi" alone.

    Returns:
        Tuple of (corrected_text, list_of_corrections).
    """
    corrections: list[dict] = []
    result = text
    # Normalize the full text for scanning
    text_norm = normalize_vietnamese(text)

    # Track which character positions have already been corrected
    # to prevent overlapping replacements.
    corrected_positions: set[int] = set()

    for key, replacement in _SORTED_KEYS:
        norm_key = normalize_vietnamese(key)
        if norm_key not in text_norm:
            continue

        # Find all occurrences in the normalized text
        search_start = 0
        while True:
            idx = text_norm.find(norm_key, search_start)
            if idx == -1:
                break

            end_idx = idx + len(norm_key)

            # Check this is a word boundary match (not mid-word)
            if not _is_word_boundary(text_norm, idx, end_idx):
                search_start = idx + 1
                continue

            # Skip if any position in this range was already corrected
            if corrected_positions & set(range(idx, end_idx)):
                search_start = idx + 1
                continue

            # Extract the original span from the (possibly mixed-case) text
            original_span = result[idx:end_idx]

            # Apply capitalization from the original
            adjusted = _apply_capitalization(original_span, replacement)

            # Replace in both result and tracking
            result = result[:idx] + adjusted + result[end_idx:]
            text_norm = text_norm[:idx] + normalize_vietnamese(adjusted) + text_norm[end_idx:]

            # Mark positions as corrected
            corrected_positions.update(range(idx, idx + len(adjusted)))

            # Record correction only if it actually changed something
            if original_span != adjusted:
                corrections.append({"from": original_span, "to": adjusted})

            # Advance past this replacement
            search_start = idx + len(adjusted)

    return result, corrections


def _is_word_boundary(text: str, start: int, end: int) -> bool:
    """
    Check that positions start..end in text fall on word boundaries.

    A word boundary means the character before *start* (if any) and
    the character after *end* (if any) are not alphanumeric.
    """
    if start > 0 and text[start - 1].isalnum():
        return False
    if end < len(text) and text[end].isalnum():
        return False
    return True


def _apply_fuzzy_corrections(
    text: str,
    already_corrected: list[dict],
    max_distance: int = 2,
) -> tuple[str, list[dict]]:
    """
    Apply fuzzy (Levenshtein) corrections for entity names not caught
    by the dictionary pass.

    This is more conservative: it only corrects multi-word sequences
    that closely match a known entity name.

    Args:
        text: Text after dictionary corrections.
        already_corrected: Corrections already applied (to avoid re-correcting).
        max_distance: Maximum Levenshtein distance.

    Returns:
        Tuple of (corrected_text, list_of_new_corrections).
    """
    text_norm = normalize_vietnamese(text)
    words = text_norm.split()

    if len(words) < 2:
        # Single-word inputs: try direct entity match
        return _fuzzy_correct_single(text, text_norm, max_distance)

    # Slide windows of 2..5 words, try to match entity names
    replaced_spans = _collect_fuzzy_spans(
        text, words, already_corrected, max_distance
    )

    # Apply replacements (from right to left to preserve positions)
    return _apply_fuzzy_replacements(text, replaced_spans)


def _fuzzy_correct_single(
    text: str,
    text_norm: str,
    max_distance: int,
) -> tuple[str, list[dict]]:
    """
    Single-word fuzzy path: try a direct entity match for *text*.

    Extracted verbatim from ``_apply_fuzzy_corrections`` (behavior-preserving).
    """
    corrections: list[dict] = []
    match = _fuzzy_match_entity(text_norm, max_distance=max_distance)
    if match and normalize_vietnamese(match) != text_norm:
        original_span = text.strip()
        adjusted = _apply_capitalization(original_span, match)
        if original_span != adjusted:
            corrections.append({"from": original_span, "to": adjusted})
            text = adjusted
    return text, corrections


def _collect_fuzzy_spans(
    text: str,
    words: list[str],
    already_corrected: list[dict],
    max_distance: int,
) -> list[tuple[int, int, str, str]]:
    """
    Slide windows of 2..5 words over *words* and collect fuzzy-match spans.

    Extracted verbatim from ``_apply_fuzzy_corrections`` (behavior-preserving).

    Returns:
        List of (start_char, end_char, from_text, to_text) spans.
    """
    already_replaced: set[str] = {
        normalize_vietnamese(c["from"]) for c in already_corrected
    }

    max_window = min(len(words), 5)
    replaced_spans: list[tuple[int, int, str, str]] = []  # (start_char, end_char, from, to)

    for window_size in range(max_window, 1, -1):
        for start in range(len(words) - window_size + 1):
            _collect_fuzzy_span_at(
                text, words, start, window_size,
                already_replaced, replaced_spans, max_distance,
            )

    return replaced_spans


def _collect_fuzzy_span_at(
    text: str,
    words: list[str],
    start: int,
    window_size: int,
    already_replaced: set[str],
    replaced_spans: list[tuple[int, int, str, str]],
    max_distance: int,
) -> None:
    """
    Evaluate one window and append its span to *replaced_spans* if matched.

    Extracted verbatim from ``_apply_fuzzy_corrections`` (behavior-preserving).
    Mutates *replaced_spans* in place, preserving the original iteration order.
    """
    window_words = words[start:start + window_size]
    window_text = " ".join(window_words)

    # Skip if this span was already corrected by dictionary pass
    if window_text in already_replaced:
        return

    # Skip if this window overlaps with an already-found fuzzy match
    # (Calculate char positions in text_norm)
    char_start = _word_char_offset(words, start)
    char_end = char_start + len(window_text)
    if any(
        _spans_overlap(char_start, char_end, rs, re_)
        for rs, re_, _, _ in replaced_spans
    ):
        return

    match = _fuzzy_match_entity(
        window_text, max_distance=max_distance
    )
    if match and normalize_vietnamese(match) != window_text:
        # Find the original text span
        original_span = " ".join(text.split()[start:start + window_size])
        adjusted = _apply_capitalization(original_span, match)

        if original_span != adjusted:
            replaced_spans.append((char_start, char_end, original_span, adjusted))


def _apply_fuzzy_replacements(
    text: str,
    replaced_spans: list[tuple[int, int, str, str]],
) -> tuple[str, list[dict]]:
    """
    Apply collected fuzzy *replaced_spans* to *text*, right-to-left.

    Extracted verbatim from ``_apply_fuzzy_corrections`` (behavior-preserving).

    Returns:
        Tuple of (corrected_text, list_of_new_corrections).
    """
    corrections: list[dict] = []
    replaced_spans.sort(key=lambda x: x[0], reverse=True)
    result_words = text.split()
    for _, _, from_text, to_text in replaced_spans:
        # Find the words in result_words that correspond to from_text
        from_words = from_text.split()
        for i in range(len(result_words) - len(from_words) + 1):
            candidate = " ".join(result_words[i:i + len(from_words)])
            if candidate == from_text:
                to_words = to_text.split()
                result_words[i:i + len(from_words)] = to_words
                corrections.append({"from": from_text, "to": to_text})
                break

    return " ".join(result_words), corrections


def _word_char_offset(words: list[str], word_index: int) -> int:
    """Calculate the character offset of word at *word_index* in a space-joined string."""
    offset = 0
    for i in range(word_index):
        offset += len(words[i]) + 1  # +1 for the space
    return offset


def _spans_overlap(s1: int, e1: int, s2: int, e2: int) -> bool:
    """Check if two character spans [s1,e1) and [s2,e2) overlap."""
    return s1 < e2 and s2 < e1


# ══════════════════════════════════════════════════
#  MODULE-LEVEL CONVENIENCE
# ══════════════════════════════════════════════════

def get_correction_count() -> int:
    """Return the number of entries in the correction dictionary."""
    return len(_TOURISM_CORRECTIONS)


def add_corrections(extra: dict[str, str]):
    """
    Add custom corrections at runtime (e.g., from learned entities).

    Args:
        extra: Mapping of normalized-key to correct Vietnamese form.

    Thread-safe; rebuilds lookup tables after adding.
    """
    global _initialized
    with _init_lock:
        _TOURISM_CORRECTIONS.update(extra)
        _initialized = False
    _init_lookups()


# ══════════════════════════════════════════════════
#  SELF-TEST
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    print(f"Correction dictionary: {get_correction_count()} entries\n")

    test_cases = [
        "vinh log",
        "toi muon di cho noi tra on",
        "bun nuoc leo o dau ngon",
        "cam sanh tam binh",
        "don ca tai tu nam bo",
        "keo dua ben tre co ngon khong",
        "chua khmer vinh long",
        "miet vuon an binh",
        "du lich sinh thai vinh long",
        "homstay cu lao an binh",
        "",
        "hello world",
        "VINH LONG dep lam",
        "Banh Trang cu lao may",
        "cam san tam bin",
    ]

    for tc in test_cases:
        result = autocorrect(tc)
        status = "CORRECTED" if result["was_corrected"] else "unchanged"
        print(f"  [{status}] {tc!r}")
        if result["was_corrected"]:
            print(f"         -> {result['corrected']!r}")
            for c in result["corrections"]:
                print(f"            {c['from']!r} -> {c['to']!r}")
        print()
