# -*- coding: utf-8 -*-
"""R40.3/R10.6/R30.1 — claim khống, provenance ảnh, Tailwind (tầng HARD).

docs-active = docs/ NGOÀI archive/, research/, superpowers/ (plan/spec lịch sử trích dẫn),
standards/ (file chuẩn liệt kê từ cấm) — cùng định nghĩa truth-sync.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .common import RegexCheck, repo_root
try:
    from agent.media_truth_manifest import _load_revoked_legacy_image_ids
except ImportError:  # pragma: no cover - direct script execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from agent.media_truth_manifest import _load_revoked_legacy_image_ids
try:
    from .provenance_evidence_policy import select_affirmative_license_scope
    from .provenance_url_policy import is_public_provenance_url
except ImportError:  # pragma: no cover - direct script execution
    from provenance_evidence_policy import select_affirmative_license_scope
    from provenance_url_policy import is_public_provenance_url

_DOCS_EXCLUDE = [
    "docs/archive", "docs/research", "docs/superpowers", "docs/standards",
]
_DATA_REL = "web/data.json"
_URL_DEBT_REL = "docs/standards/r10.6-image-url-debt.txt"
_LICENSE_DEBT_REL = "docs/standards/r10.6-legacy-image-license-ids.txt"
_GENERIC_URL_REL = "docs/standards/r10.6-legacy-generic-url-ids.txt"
_LICENSE_SNAPSHOT_HEADERS = (
    "# Snapshot: 2026-09-21",
    "# Source: web/data.json",
    "# Source SHA-256: 8ac327de6c4f273c96efe99004f6a1858ba41af43799ebcdae5cd7f31316d92f",
    "# Entity count: 1772",
)
_GENERIC_URL_SNAPSHOT_HEADERS = _LICENSE_SNAPSHOT_HEADERS[:-1] + ("# Entity count: 1264",)
_DOCUMENTARY_TYPES = {"documentary", "journalistic", "official", "press"}
_LEGACY_LICENSE_PREFIXES = (
    "Bản quyền thuộc tác giả và ",
    "Tư liệu báo chí / ",
    "Tư liệu chính thống / ",
)


def _active_legacy_ids(root: Path, ids: list[str]) -> set[str]:
    try:
        revoked = _load_revoked_legacy_image_ids(root)
    except (OSError, ValueError):
        return set()
    return set(ids) - revoked


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _source_url_issue(attrs: dict) -> str | None:
    value = attrs.get("image_source_url")
    if is_public_provenance_url(value):
        return None
    if _nonempty(value):
        return "URL nguồn placeholder"
    return "URL nguồn"


def _load_url_debt(root: Path) -> set[str]:
    path = root / _URL_DEBT_REL
    if not path.exists():
        return set()
    ids = {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    return _active_legacy_ids(root, list(ids))


def _load_legacy_license_ids(root: Path) -> set[str]:
    path = root / _LICENSE_DEBT_REL
    if not path.exists():
        return set()
    lines = path.read_text(encoding="utf-8").splitlines()
    if tuple(lines[:4]) != _LICENSE_SNAPSHOT_HEADERS:
        return set()
    ids = [line.strip() for line in lines[4:] if line.strip()]
    if len(ids) != 1772 or ids != sorted(set(ids)):
        return set()
    return _active_legacy_ids(root, ids)


def _load_legacy_generic_url_ids(root: Path) -> set[str]:
    path = root / _GENERIC_URL_REL
    if not path.exists():
        return set()
    lines = path.read_text(encoding="utf-8").splitlines()
    if tuple(lines[:4]) != _GENERIC_URL_SNAPSHOT_HEADERS:
        return set()
    ids = [line.strip() for line in lines[4:] if line.strip()]
    if len(ids) != 1264 or ids != sorted(set(ids)):
        return set()
    return _active_legacy_ids(root, ids)


def _has_public_generic_citation(entity: dict, attrs: dict) -> bool:
    for collection in (entity.get("source"), attrs.get("source_citations")):
        if not isinstance(collection, list):
            continue
        if any(
            isinstance(item, dict)
            and is_public_provenance_url(item.get("url"), require_path=False)
            for item in collection
        ):
            return True
    return False


def _allows_legacy_missing_source_url(
    entity: dict,
    attrs: dict,
    url_debt: set[str],
    legacy_generic_url_ids: set[str],
) -> bool:
    entity_id = str(entity.get("id") or "<unknown>")
    if entity_id in url_debt:
        return True
    return (
        entity_id in legacy_generic_url_ids
        and _has_public_generic_citation(entity, attrs)
    )


def _documentary_missing(
    entity: dict,
    attrs: dict,
    url_debt: set[str],
    legacy_license_ids: set[str],
    legacy_generic_url_ids: set[str],
) -> list[str]:
    missing = [
        field
        for field in ("image_author", "image_source")
        if not _nonempty(attrs.get(field))
    ]
    license_value = attrs.get("image_license")
    legacy_license_compatible = (
        str(entity.get("id") or "<unknown>") in legacy_license_ids
        and isinstance(license_value, str)
        and license_value.strip().startswith(_LEGACY_LICENSE_PREFIXES)
    )
    if (
        select_affirmative_license_scope([license_value]) is None
        and not legacy_license_compatible
    ):
        missing.append("image_license")
    source_url_issue = _source_url_issue(attrs)
    has_legacy_url_debt = _allows_legacy_missing_source_url(
        entity, attrs, url_debt, legacy_generic_url_ids
    )
    if source_url_issue and (
        source_url_issue != "URL nguồn" or not has_legacy_url_debt
    ):
        missing.append(source_url_issue)
    return missing


def _entity_image_violation(
    entity: object,
    url_debt: set[str],
    legacy_license_ids: set[str],
    legacy_generic_url_ids: set[str],
) -> dict | None:
    if not isinstance(entity, dict) or not entity.get("images"):
        return None
    attrs = entity.get("attributes") if isinstance(entity.get("attributes"), dict) else {}
    image_type = str(attrs.get("image_type") or "").strip().lower()
    verified_photo = attrs.get("is_verified_photo") is True
    entity_id = str(entity.get("id") or "<unknown>")
    if image_type == "ai-generated" and verified_photo:
        return {
            "file": _DATA_REL,
            "line": 0,
            "rule": "R10.6",
            "msg": f"{entity_id}: ảnh AI-generated không được đặt is_verified_photo=true",
        }
    if image_type not in _DOCUMENTARY_TYPES and not verified_photo:
        return None
    missing = _documentary_missing(
        entity, attrs, url_debt, legacy_license_ids, legacy_generic_url_ids
    )
    if not missing:
        return None
    return {
        "file": _DATA_REL,
        "line": 0,
        "rule": "R10.6",
        "msg": f"{entity_id}: ảnh báo chí/tư liệu thiếu {', '.join(missing)}",
    }


class ImageSourcePolicyCheck:
    """Allow press imagery while enforcing attribution and honest classification."""

    name, level, rule = "image_source_policy", "hard-ratchet", "R10.6"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        return self._root or repo_root()

    def _stock_violations(self, files: list[str] | None) -> list[dict]:
        check = RegexCheck(
            name=self.name,
            level=self.level,
            rule=self.rule,
            patterns=[r"Wikimedia|Pexels|Unsplash"],
            globs=["*.vue", "*.ts", "*.py", "*.md"],
            roots=["web-nuxt", "agent", "scripts", "docs"],
            exclude_paths=_DOCS_EXCLUDE + ["scripts/checks", "tests"],
            msg="Nguồn stock/Wikimedia chưa được chính sách ảnh cho phép (CLAUDE.md §1.5)",
            root=self.root,
        )
        return check.run(files)["violations"]

    def _data_violations(self, files: list[str] | None) -> list[dict]:
        normalized_files = {path.replace("\\", "/") for path in files or []}
        policy_inputs = {
            _DATA_REL,
            _URL_DEBT_REL,
            _LICENSE_DEBT_REL,
            _GENERIC_URL_REL,
            "docs/standards/r10.6-legacy-image-revocations.txt",
            "docs/standards/batch-21-media-truth.json",
        }
        if files is not None and normalized_files.isdisjoint(policy_inputs):
            return []
        data_path = self.root / _DATA_REL
        if not data_path.exists():
            return []
        data = json.loads(data_path.read_text(encoding="utf-8"))
        url_debt = _load_url_debt(self.root)
        legacy_license_ids = _load_legacy_license_ids(self.root)
        legacy_generic_url_ids = _load_legacy_generic_url_ids(self.root)
        return [
            violation
            for entity in data.get("entities", [])
            if (
                violation := _entity_image_violation(
                    entity, url_debt, legacy_license_ids, legacy_generic_url_ids
                )
            )
            is not None
        ]

    def run(self, files: list[str] | None = None) -> dict:
        violations = self._stock_violations(files) + self._data_violations(files)
        return {
            "check": self.name,
            "level": self.level,
            "rule": self.rule,
            "count": len(violations),
            "violations": violations,
        }


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
        ImageSourcePolicyCheck(root=root),
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
