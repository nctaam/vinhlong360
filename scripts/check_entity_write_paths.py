#!/usr/bin/env python3
"""Reject direct entity SQL writes outside the frozen Wave 1 inventory."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import Counter
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
ALLOWED_WRITE_SITE_COUNTS = {
    site: 2
    if site
    in {
        ("agent/database.py", "Database._write_entity_row", "insert"),
        ("scripts/sp2_reconcile.py", "_apply_one_local_fix", "attributes-update"),
    }
    else 1
    for site in ALLOWED_WRITE_SITES
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
_UPDATE_CLAUSE_RE = re.compile(r"\b(?:where|returning)\b", re.IGNORECASE)
_ASSIGNMENT_RE = re.compile(
    r'(?:^|,)\s*(?P<column>\{\}|(?:"[^"]+"|[a-z_][a-z0-9_]*)(?:\.(?:"[^"]+"|[a-z_][a-z0-9_]*))?)\s*=',
    re.IGNORECASE,
)
_INTEGRITY_COLUMNS = {
    "attributes",
    "type",
    "address",
    "phone",
    "website",
    "hours",
    "price_range",
    "sub_category",
    "best_time",
    "highlight",
}


def _binary_sql_shape(
    node: ast.BinOp, bindings: dict[str, str | None]
) -> str | None:
    left = _sql_shape(node.left, bindings)
    right = _sql_shape(node.right, bindings)
    if left is not None and right is not None:
        return left + right
    return None


def _joined_sql_shape(
    node: ast.JoinedStr, bindings: dict[str, str | None]
) -> str:
    parts = []
    for part in node.values:
        if isinstance(part, ast.Constant):
            parts.append(part.value)
        elif isinstance(part, ast.FormattedValue):
            parts.append(_sql_shape(part.value, bindings) or "{}")
    return "".join(parts)


def _sql_shape(node: ast.AST, bindings: dict[str, str | None]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return bindings.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _binary_sql_shape(node, bindings)
    if isinstance(node, ast.JoinedStr):
        return _joined_sql_shape(node, bindings)
    return None


def _classify_sql(node: ast.AST, bindings: dict[str, str | None]) -> str | None:
    shape = _sql_shape(node, bindings)
    if shape is None:
        return None
    normalized = " ".join(shape.split())
    if _INSERT_RE.search(normalized):
        return "insert"
    update = _UPDATE_RE.search(normalized)
    if update is None:
        return None
    assignment_text = _UPDATE_CLAUSE_RE.split(normalized[update.end() :], maxsplit=1)[0]
    columns = {
        match.group("column").split(".")[-1].strip('"').lower()
        for match in _ASSIGNMENT_RE.finditer(assignment_text)
    }
    if "attributes" in columns:
        return "attributes-update"
    if "{}" in columns or (not columns and assignment_text.lstrip().startswith("{}")):
        return "dynamic-update"
    if columns & _INTEGRITY_COLUMNS:
        return "integrity-update"
    return None


class _WriteVisitor(ast.NodeVisitor):
    def __init__(self, relative_path: str) -> None:
        self.relative_path = relative_path
        self.scopes: list[str] = []
        self.binding_scopes: list[dict[str, str | None]] = [{}]
        self.sites: list[WriteSite] = []

    def _bindings(self) -> dict[str, str | None]:
        bindings: dict[str, str | None] = {}
        for scope in self.binding_scopes:
            bindings.update(scope)
        return bindings

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_nodes(node.decorator_list)
        self._visit_nodes(node.bases)
        self._visit_nodes(node.keywords)
        self._visit_nodes(getattr(node, "type_params", []))
        self._visit_scope_body(node.name, node.body)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        self._visit_nodes(node.decorator_list)
        self.visit(node.args)
        if node.returns is not None:
            self.visit(node.returns)
        self._visit_nodes(getattr(node, "type_params", []))
        arguments = (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        )
        if node.args.vararg is not None:
            arguments += (node.args.vararg,)
        if node.args.kwarg is not None:
            arguments += (node.args.kwarg,)
        self._visit_scope_body(
            node.name,
            node.body,
            shadowed=(argument.arg for argument in arguments),
        )

    def _visit_nodes(self, nodes: Iterable[ast.AST]) -> None:
        for node in nodes:
            self.visit(node)

    def _visit_scope_body(
        self,
        name: str,
        body: Iterable[ast.AST],
        *,
        shadowed: Iterable[str] = (),
    ) -> None:
        self.scopes.append(name)
        self.binding_scopes.append({binding: None for binding in shadowed})
        self._visit_nodes(body)
        self.binding_scopes.pop()
        self.scopes.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        self.visit(node.value)
        shape = _sql_shape(node.value, self._bindings())
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.binding_scopes[-1][target.id] = shape
            else:
                self.visit(target)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.visit(node.annotation)
        if node.value is not None:
            self.visit(node.value)
        if isinstance(node.target, ast.Name):
            self.binding_scopes[-1][node.target.id] = (
                _sql_shape(node.value, self._bindings())
                if node.value is not None
                else None
            )
        else:
            self.visit(node.target)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self.visit(node.value)
        if isinstance(node.target, ast.Name) and isinstance(node.op, ast.Add):
            current = self._bindings().get(node.target.id)
            addition = _sql_shape(node.value, self._bindings())
            self.binding_scopes[-1][node.target.id] = (
                current + addition
                if current is not None and addition is not None
                else None
            )
        else:
            self.visit(node.target)

    def visit_Call(self, node: ast.Call) -> None:
        bindings = self._bindings()
        kinds = {
            kind
            for argument in [
                *node.args,
                *(keyword.value for keyword in node.keywords),
            ]
            if (kind := _classify_sql(argument, bindings)) is not None
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
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=relative_path)
        except (OSError, SyntaxError, UnicodeError) as error:
            sites.append(
                WriteSite(
                    path=relative_path,
                    function="<module>",
                    kind="parse-error",
                    line=getattr(error, "lineno", 0) or 0,
                )
            )
            continue
        visitor = _WriteVisitor(relative_path)
        visitor.visit(tree)
        sites.extend(visitor.sites)
    return sorted(sites, key=lambda site: (site.path, site.function, site.kind, site.line))


def unapproved_write_sites(root: Path) -> list[WriteSite]:
    occurrences: Counter[tuple[str, str, str]] = Counter()
    unapproved = []
    for site in find_write_sites(root):
        key = (site.path, site.function, site.kind)
        occurrences[key] += 1
        allowed_count = ALLOWED_WRITE_SITE_COUNTS.get(key, 1)
        if key not in ALLOWED_WRITE_SITES or occurrences[key] > allowed_count:
            unapproved.append(site)
    return unapproved


class _CliUsageError(Exception):
    pass


class _RedactedArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise _CliUsageError


def main(argv: Sequence[str] | None = None) -> int:
    parser = _RedactedArgumentParser(
        description="Reject unapproved direct entity SQL writes."
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    try:
        args = parser.parse_args(argv)
    except _CliUsageError:
        print("entity write path check failed: invalid arguments", file=sys.stderr)
        return 2
    sites = unapproved_write_sites(args.root)
    for site in sites:
        print(f"{site.path}|{site.function}|{site.kind}|{site.line}")
    return 1 if sites else 0


if __name__ == "__main__":
    raise SystemExit(main())
