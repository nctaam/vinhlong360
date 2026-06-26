"""Shared Vietnamese text utilities — slugify, normalize, strip diacritics.

Extracted from 6+ import scripts to eliminate copy-paste duplication.
"""

import re
import unicodedata


def slugify(text: str, max_len: int = 80) -> str:
    """Convert Vietnamese text to a URL-safe slug (ASCII, lowercase, hyphenated)."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"[đĐ]", "d", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text[:max_len]


def strip_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics, keep đ→d."""
    text = re.sub(r"[đĐ]", "d", text)
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def normalize_name(text: str) -> str:
    """Normalize a Vietnamese name for dedup comparison (lowercase, no diacritics, trimmed)."""
    return strip_diacritics((text or "").strip()).lower()
