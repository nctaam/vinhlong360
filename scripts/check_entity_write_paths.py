#!/usr/bin/env python3
"""Reject direct entity SQL writes outside the frozen Wave 1 inventory."""

from __future__ import annotations

import argparse
import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class WriteSite:
    path: str
    function: str
    kind: str
    line: int


ALLOWED_WRITE_SITES = {
    # Canonical database insert paths.
    ("agent/database.py", "Database._write_entity_row", "insert"),
    ("agent/database.py", "Database._bulk_insert_rows", "insert"),
    # Universal-column mirrors used by runtime sync and explicit backfill.
    ("agent/entity_details.py", "sync_entity_details", "dynamic-update"),
    ("scripts/backfill_entity_details.py", "_apply_universal", "dynamic-update"),
    # Frozen offline cleanup, reconciliation, and repair inventory.
    ("scripts/cleanup_entity_jsonb.py", "_process_entity", "attributes-update"),
    ("scripts/sp2_reconcile.py", "_apply_one_local_fix", "attributes-update"),
    ("scripts/sp2_reconcile.py", "_apply_one_local_fix", "dynamic-update"),
    ("scripts/sp2_reconcile.py", "_prod_patch_one", "attributes-update"),
    ("scripts/sp2_reconcile.py", "_prod_patch_one", "dynamic-update"),
    ("scripts/sp2_reconcile.py", "_prod_insert", "insert"),
    ("scripts/sp6_fill_required.py", "_apply_sqlite", "attributes-update"),
    ("scripts/sp6_fill_required.py", "_apply_pg", "attributes-update"),
    (
        "scripts/import_enrichment_tips.py",
        "_apply_enrichment_row",
        "attributes-update",
    ),
    ("scripts/fix_tinh_moi.py", "apply_sqlite", "dynamic-update"),
    ("scripts/fix_tinh_moi.py", "apply_pg", "attributes-update"),
    ("scripts/fix_tinh_moi.py", "apply_pg", "dynamic-update"),
}

_IGNORED_DIRECTORIES = {
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "cache",
    "generated",
    "migration",
    "migrations",
    "test",
    "tests",
}
_INSERT_RE = re.compile(r"\binsert\s+into\s+entities\b", re.IGNORECASE)
_UPDATE_RE = re.compile(r"\bupdate\s+entities\s+set\s+", re.IGNORECASE)
_ATTRIBUTES_ASSIGNMENT_RE = re.compile(r"attributes\b\s*=", re.IGNORECASE)
_DYNAMIC_ASSIGNMENT_RE = re.compile(
    r'(?:\{\}|"\{\}"|`\{\}`|\[\{\}\])\s*=',
    re.IGNORECASE,
)


def _sql_shape(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(
            part.value if isinstance(part, ast.Constant) else "{}"
            for part in node.values
        )
    return None


def _classify_sql(node: ast.AST) -> str | None:
    shape = _sql_shape(node)
    if shape is None:
        return None
    normalized = " ".join(shape.split())
    if _INSERT_RE.search(normalized):
        return "insert"
    update = _UPDATE_RE.search(normalized)
    if update is None:
        return None
    first_assignment = normalized[update.end() :].lstrip()
    if _ATTRIBUTES_ASSIGNMENT_RE.match(first_assignment):
        return "attributes-update"
    if _DYNAMIC_ASSIGNMENT_RE.match(first_assignment):
        return "dynamic-update"
    return None


class _WriteVisitor(ast.NodeVisitor):
    def __init__(self, relative_path: str) -> None:
        self.relative_path = relative_path
        self.scopes: list[str] = []
        self.sites: list[WriteSite] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_scope(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_scope(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_scope(node)

    def _visit_scope(
        self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        self.scopes.append(node.name)
        self.generic_visit(node)
        self.scopes.pop()

    def visit_Call(self, node: ast.Call) -> None:
        kinds = {
            kind
            for argument in [
                *node.args,
                *(keyword.value for keyword in node.keywords),
            ]
            if (kind := _classify_sql(argument)) is not None
        }
        function = ".".join(self.scopes) or "<module>"
        for kind in sorted(kinds):
            self.sites.append(
                WriteSite(
                    path=self.relative_path,
                    function=function,
                    kind=kind,
                    line=node.lineno,
                )
            )
        self.generic_visit(node)


def _python_files(root: Path) -> Iterable[Path]:
    source_roots = [path for name in ("agent", "scripts") if (path := root / name).is_dir()]
    if not source_roots:
        source_roots = [root]
    for source_root in source_roots:
        for path in sorted(source_root.rglob("*.py")):
            relative = path.relative_to(root)
            if not any(part in _IGNORED_DIRECTORIES for part in relative.parts[:-1]):
                yield path


def find_write_sites(root: Path) -> list[WriteSite]:
    root = root.resolve()
    sites: list[WriteSite] = []
    for path in _python_files(root):
        relative_path = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative_path)
        visitor = _WriteVisitor(relative_path)
        visitor.visit(tree)
        sites.extend(visitor.sites)
    return sorted(sites, key=lambda site: (site.path, site.function, site.kind, site.line))


def unapproved_write_sites(root: Path) -> list[WriteSite]:
    return [
        site
        for site in find_write_sites(root)
        if (site.path, site.function, site.kind) not in ALLOWED_WRITE_SITES
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Reject unapproved direct entity SQL writes."
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    args = parser.parse_args(argv)
    sites = unapproved_write_sites(args.root)
    for site in sites:
        print(f"{site.path}|{site.function}|{site.kind}|{site.line}")
    return 1 if sites else 0


if __name__ == "__main__":
    raise SystemExit(main())
