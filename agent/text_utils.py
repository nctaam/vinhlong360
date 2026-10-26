"""Shared Vietnamese text utilities — slugify, normalize, strip diacritics.

Extracted from 6+ import scripts to eliminate copy-paste duplication.
Optimized with module-level precompiled regexes and LRU caches for high throughput.
"""

import functools
import re
import unicodedata

_VIETNAMESE_D_RE = re.compile(r"[đĐ]")
_COMBINING_MARKS_RE = re.compile(r"[\u0300-\u036f]")
_SLUG_INVALID_RE = re.compile(r"[^a-z0-9\s-]")
_SLUG_HYPHENS_RE = re.compile(r"[\s-]+")


def slugify(text: str, max_len: int = 80) -> str:
    """Convert Vietnamese text to a URL-safe slug (ASCII, lowercase, hyphenated)."""
    text = unicodedata.normalize("NFD", text)
    text = _COMBINING_MARKS_RE.sub("", text)
    text = text.lower().strip()
    text = _VIETNAMESE_D_RE.sub("d", text)
    text = _SLUG_INVALID_RE.sub("", text)
    text = _SLUG_HYPHENS_RE.sub("-", text).strip("-")
    return text[:max_len]


@functools.lru_cache(maxsize=4096)
def strip_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics, keep đ→d."""
    text = _VIETNAMESE_D_RE.sub("d", text)
    text = unicodedata.normalize("NFD", text)
    return _COMBINING_MARKS_RE.sub("", text)


@functools.lru_cache(maxsize=4096)
def normalize_name(text: str) -> str:
    """Normalize a Vietnamese name for dedup comparison (lowercase, no diacritics, trimmed)."""
    return strip_diacritics((text or "").strip()).lower()
