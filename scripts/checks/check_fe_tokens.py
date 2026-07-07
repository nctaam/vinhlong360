# -*- coding: utf-8 -*-
"""R30.3 màu ngoài tokens (HARD-RATCHET) + R30.2 emoji chức năng (SOFT-RATCHET).

Màu hex/rgb trong .vue = nợ (palette sống ở assets/css/tokens.css + biến --*).
Emoji: string-context (SEO/map/option) hợp lệ tồn tại → soft-ratchet, chặn TĂNG.
"""
from __future__ import annotations

from pathlib import Path

from .common import RegexCheck

_EMOJI = r"[\U0001F300-\U0001FAFF☀-➿⭐❤]"


def build_checks(root: Path | None = None) -> list:
    return [
        RegexCheck(
            name="fe_colors", level="hard-ratchet", rule="R30.3",
            patterns=[r"#[0-9a-fA-F]{6}\b", r"#[0-9a-fA-F]{3}\b(?![0-9a-fA-F])", r"\brgba?\("],
            globs=["*.vue"], roots=["web-nuxt/pages", "web-nuxt/components", "web-nuxt/layouts"],
            exclude_paths=["web-nuxt/node_modules"],
            neg_context=None,
            msg="màu ngoài tokens — dùng var(--*) từ tokens.css (R30.3)",
            root=root,
        ),
        RegexCheck(
            name="fe_emoji", level="soft-ratchet", rule="R30.2",
            patterns=[_EMOJI],
            globs=["*.vue"], roots=["web-nuxt/pages", "web-nuxt/components", "web-nuxt/layouts"],
            exclude_paths=["web-nuxt/node_modules"],
            neg_context=None,
            msg="emoji chức năng — dùng IconLine (R30.2); string-context được phép qua baseline",
            root=root,
        ),
    ]


CHECKS = build_checks()
