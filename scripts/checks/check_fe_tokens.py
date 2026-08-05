# -*- coding: utf-8 -*-
"""R30.3 màu ngoài tokens (HARD-RATCHET) + R30.2 emoji chức năng (SOFT-RATCHET).

Màu hex/rgb trong .vue = nợ (palette sống ở assets/css/tokens.css + biến --*).
Emoji: string-context (SEO/map/option) hợp lệ tồn tại → soft-ratchet, chặn TĂNG.

Cả hai đếm theo TỪNG MATCH (`count_matches=True`), không theo dòng. Mặc định của
`RegexCheck` ghi một violation cho mỗi DÒNG có khớp, nên với một ratchet thì gộp
3 màu cũ vào chung một dòng là mua được 2 suất cho màu cứng mới ở chỗ khác mà
tổng không đổi. Đo 2026-08-05: R30.3 270 dòng ↔ 307 match, R30.2 623 ↔ 687 —
tức 37 và 64 suất ẩn.
"""
from __future__ import annotations

from pathlib import Path

from .common import RegexCheck

_EMOJI = r"[\U0001F300-\U0001FAFF☀-➿⭐❤]"

# app.vue/error.vue nằm ở gốc web-nuxt nên trước đây ngoài tầm quét. Thêm vào tốn
# 0 vi phạm (đã đo) nhưng bịt chỗ trú cho màu cứng mới.
_ROOTS = [
    "web-nuxt/pages", "web-nuxt/components", "web-nuxt/layouts",
    "web-nuxt/app.vue", "web-nuxt/error.vue",
]


def build_checks(root: Path | None = None) -> list:
    return [
        RegexCheck(
            name="fe_colors", level="hard-ratchet", rule="R30.3",
            # rgb/rgba LITERAL = nợ; rgba(var(--x-rgb), a) = DÙNG token (idiomatic, như
            # base.css) → KHÔNG phải nợ, lookahead loại. (Trước đây flag nhầm ~620.)
            # Lookahead phải bao luôn khoảng trắng: viết `\(\s*(?!var\()` thì engine
            # backtrack `\s*` về rỗng, lookahead soi đúng ký tự space nên `rgb( var(--x) )`
            # vẫn bị tính là màu cứng. Đếm theo dòng che lỗi này (cùng dòng đã có
            # match khác); bật count_matches mới lộ ra.
            patterns=[r"#[0-9a-fA-F]{6}\b", r"#[0-9a-fA-F]{3}\b(?![0-9a-fA-F])", r"\brgba?\((?!\s*var\()"],
            globs=["*.vue"], roots=_ROOTS,
            exclude_paths=["web-nuxt/node_modules"],
            neg_context=None, count_matches=True,
            msg="màu ngoài tokens — dùng var(--*) từ tokens.css (R30.3)",
            root=root,
        ),
        RegexCheck(
            name="fe_emoji", level="soft-ratchet", rule="R30.2",
            patterns=[_EMOJI],
            globs=["*.vue"], roots=_ROOTS,
            exclude_paths=["web-nuxt/node_modules"],
            neg_context=None, count_matches=True,
            msg="emoji chức năng — dùng IconLine (R30.2); string-context được phép qua baseline",
            root=root,
        ),
    ]


CHECKS = build_checks()
