# -*- coding: utf-8 -*-
"""R40.3/R10.6/R30.1 — claim xác-minh khống, nguồn ảnh cấm, Tailwind (tầng HARD).

docs-active = docs/ NGOÀI archive/, research/, superpowers/ (plan/spec lịch sử trích dẫn),
standards/ (file chuẩn liệt kê từ cấm) — cùng định nghĩa truth-sync.
"""
from __future__ import annotations

from pathlib import Path

from .common import RegexCheck

_DOCS_EXCLUDE = [
    "docs/archive", "docs/research", "docs/superpowers", "docs/standards",
]


def build_checks(root: Path | None = None) -> list:
    return [
        RegexCheck(
            name="banned_claims", level="hard", rule="R40.3",
            patterns=[r"đã (được )?xác minh"],
            globs=["*.vue", "*.ts", "*.md"],
            roots=["web-nuxt", "docs"],
            exclude_paths=_DOCS_EXCLUDE + ["web-nuxt/node_modules", "tests"],
            msg="CẤM claim 'đã xác minh' — verifiedAt ~0 (CLAUDE.md §1.7)",
            root=root,
        ),
        RegexCheck(
            name="banned_image_sources", level="hard", rule="R10.6",
            patterns=[r"Wikimedia|Pexels|Unsplash"],
            globs=["*.vue", "*.ts", "*.py", "*.md"],
            roots=["web-nuxt", "agent", "scripts", "docs"],
            exclude_paths=_DOCS_EXCLUDE + ["scripts/checks", "tests"],
            msg="Ảnh CHỈ AI-gen — nguồn stock/Wikimedia bị cấm (CLAUDE.md §1.5)",
            root=root,
        ),
        RegexCheck(
            name="no_tailwind", level="hard", rule="R30.1",
            patterns=[r"(?i)tailwind"],
            globs=["*.vue", "*.ts", "*.json", "*.css"],
            roots=["web-nuxt"],
            exclude_paths=["web-nuxt/node_modules", "web-nuxt/package-lock.json"],
            msg="CSS thuần + tokens — KHÔNG Tailwind (design system đã chốt)",
            root=root,
        ),
    ]


CHECKS = build_checks()
