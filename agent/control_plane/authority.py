"""Fail-closed release authority and evidence freshness checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
import json
from pathlib import Path
import re
import subprocess
from typing import Literal
from urllib.parse import unquote
import unicodedata


AuthorityStatus = Literal["PASS", "STALE", "BLOCKED"]
_HEAD_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
_FINDING_ID = re.compile(r"F-(\d{2})")
_RULE_ROW = re.compile(r"^\s*\|\s*(R[0-9][^|]*)\|", re.MULTILINE)
_BASELINE_COUNT = re.compile(r"baseline(?:\s+hiện\s+tại|\s+current)?\s*[:=]\s*(\d+)\s+fail", re.IGNORECASE)
_MARKDOWN_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)[^\S\r\n]*$", re.MULTILINE)
_HTML_ANCHOR = re.compile(r"<a\b[^>]*\b(?:id|name)\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
_AUDIT_P1_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+P1(?:\s|[-—:]|$)", re.IGNORECASE)
_AUDIT_TABLE_ROW = re.compile(r"^\s*\|\s*(F-\d{2})\s*\|", re.IGNORECASE)


@dataclass(frozen=True)
class ActiveDocument:
    path: str
    last_verified_at: datetime


@dataclass(frozen=True)
class AuthorityRegistry:
    schema_version: str
    authority_id: str
    owner: str
    branch: str
    head_source: str
    baseline_source: str
    rule_index: str
    audit_artifact: str
    max_age_hours: int
    p1_findings: tuple[str, ...]
    active_documents: tuple[ActiveDocument, ...]
    baseline_count: int = 15
    rule_count: int = 38
    last_verified_at: datetime | None = None
    head_sha: str | None = None


@dataclass(frozen=True)
class AuthorityReport:
    status: AuthorityStatus
    tracked_artifacts: tuple[str, ...] = ()
    mismatches: tuple[str, ...] = ()
    expired_documents: tuple[str, ...] = ()


def _parse_timestamp(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be an ISO-8601 timestamp")
    raw = value.strip()
    if len(raw) == 10:
        parsed = datetime.combine(date.fromisoformat(raw), datetime.min.time(), tzinfo=UTC)
    else:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError(f"{field} must include timezone")
        parsed = parsed.astimezone(UTC)
    return parsed


def _document_entries(raw: object) -> tuple[ActiveDocument, ...]:
    if raw is None:
        return ()
    entries: list[ActiveDocument] = []
    if isinstance(raw, dict):
        raw = [{"path": path, "last_verified_at": value} for path, value in raw.items()]
    if not isinstance(raw, list):
        raise ValueError("active_documents must be a list or object")
    for index, item in enumerate(raw):
        if isinstance(item, str):
            # A path-only entry is accepted for compatibility, but cannot pass
            # freshness until it carries an explicit verification timestamp.
            raise ValueError(f"active_documents[{index}] is missing last_verified_at")
        if not isinstance(item, dict):
            raise ValueError(f"active_documents[{index}] must be an object")
        path = item.get("path")
        if not isinstance(path, str) or not path or Path(path).is_absolute():
            raise ValueError(f"active_documents[{index}].path is invalid")
        entries.append(
            ActiveDocument(
                path=path.replace("\\", "/"),
                last_verified_at=_parse_timestamp(
                    item.get("last_verified_at"),
                    field=f"active_documents[{index}].last_verified_at",
                ),
            )
        )
    return tuple(entries)


def load_authority(path: Path) -> AuthorityRegistry:
    """Load and validate the machine-readable release authority registry."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    _validate_registry_payload(payload)
    p1 = payload.get("p1_findings", payload.get("p1_ids", ()))
    active = payload.get("active_documents", payload.get("documents", ()))
    raw_last_verified = payload.get("last_verified_at")
    last_verified = _parse_timestamp(raw_last_verified, field="last_verified_at") if raw_last_verified is not None else None
    raw_head_sha = payload.get("head_sha")
    if raw_head_sha is not None and (not isinstance(raw_head_sha, str) or (raw_head_sha != "git:HEAD" and not _HEAD_SHA.fullmatch(raw_head_sha))):
        raise ValueError("head_sha must be a 40-character SHA or git:HEAD")
    return AuthorityRegistry(
        schema_version="1",
        authority_id=payload["authority_id"],
        owner=payload["owner"],
        branch=payload["branch"],
        head_source=payload["head_source"],
        baseline_source=payload["baseline_source"],
        rule_index=payload["rule_index"],
        audit_artifact=payload["audit_artifact"].replace("\\", "/"),
        max_age_hours=payload["max_age_hours"],
        p1_findings=tuple(p1),
        active_documents=_document_entries(active),
        baseline_count=int(payload.get("baseline_count", 15)),
        rule_count=int(payload.get("rule_count", 38)),
        last_verified_at=last_verified,
        head_sha=raw_head_sha,
    )


def _validate_registry_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise ValueError("authority registry must be a JSON object")
    _require_registry_fields(payload)
    _validate_registry_values(payload)
    _validate_registry_lists(payload)


def _require_registry_fields(payload: dict[str, object]) -> None:
    required = (
        "schema_version", "authority_id", "owner", "branch", "head_source",
        "baseline_source", "rule_index", "audit_artifact", "max_age_hours",
    )
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError("authority registry missing: " + ", ".join(missing))


def _validate_registry_values(payload: dict[str, object]) -> None:
    if payload["schema_version"] != "1":
        raise ValueError("unsupported authority schema_version")
    if type(payload["max_age_hours"]) is not int or payload["max_age_hours"] <= 0:
        raise ValueError("max_age_hours must be a positive integer")
    strings = ("authority_id", "owner", "branch", "head_source", "baseline_source", "rule_index", "audit_artifact")
    if any(not isinstance(payload[field], str) or not payload[field].strip() for field in strings):
        raise ValueError("authority registry string fields must be non-empty")


def _validate_registry_lists(payload: dict[str, object]) -> None:
    p1 = payload.get("p1_findings", payload.get("p1_ids", ()))
    if not isinstance(p1, list) or not all(isinstance(item, str) for item in p1):
        raise ValueError("p1_findings must be a list of strings")


def _git(root: Path, *args: str) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=root, text=True, capture_output=True, check=False,
        )
    except OSError:
        return 127, ""
    return completed.returncode, completed.stdout.strip()


def _tracked(root: Path, path: str) -> bool:
    code, _ = _git(root, "ls-files", "--error-unmatch", "--", path)
    return code == 0


def _read(root: Path, path: str, mismatches: list[str], label: str) -> str:
    candidate = root / path
    try:
        candidate.resolve().relative_to(root.resolve())
        return candidate.read_text(encoding="utf-8")
    except (OSError, ValueError, UnicodeError):
        mismatches.append(f"{label} missing or unreadable: {path}")
        return ""


def _github_slug(heading: str) -> str:
    """Return the stable, accent-insensitive slug used by GitHub headings."""

    # GitHub removes inline markup/punctuation and transliterates Vietnamese
    # characters before collapsing separators. NFKD handles the combining
    # accents; đ is not decomposed by Unicode and therefore needs a mapping.
    text = re.sub(r"<[^>]*>", "", heading).replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(character for character in text if not unicodedata.combining(character))
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"[-\s]+", "-", text).strip("-")


def _markdown_anchors(markdown: str) -> set[str]:
    anchors = {match.group(1).strip().lower() for match in _HTML_ANCHOR.finditer(markdown)}
    seen: dict[str, int] = {}
    for match in _MARKDOWN_HEADING.finditer(markdown):
        heading = match.group(2).strip().rstrip("#").rstrip()
        slug = _github_slug(heading)
        if not slug:
            continue
        suffix = seen.get(slug, 0)
        anchors.add(f"{slug}-{suffix}" if suffix else slug)
        seen[slug] = suffix + 1
    return anchors


def _read_link(root: Path, reference: str, mismatches: list[str], label: str) -> str | None:
    """Read a referenced document while keeping link failures in the report."""

    target, separator, fragment = reference.partition("#")
    candidate = root / target
    if not target or not candidate.is_file():
        mismatches.append(f"{label} link missing: {reference}")
        return None
    try:
        markdown = candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        mismatches.append(f"{label} link unreadable: {reference}")
        return None
    if separator:
        fragment = unquote(fragment).strip().lower()
        if not fragment or fragment not in _markdown_anchors(markdown):
            mismatches.append(f"{label} anchor missing: {reference}")
    return markdown


def _check_link(root: Path, reference: str, mismatches: list[str], label: str) -> None:
    _read_link(root, reference, mismatches, label)


def _baseline_headings(
    lines: list[str], fragment: str,
) -> tuple[list[tuple[int, int, str]], list[int]]:
    headings: list[tuple[int, int, str]] = []
    explicit_anchor_lines: list[int] = []
    seen: dict[str, int] = {}
    for index, line in enumerate(lines):
        for anchor in _HTML_ANCHOR.finditer(line):
            if anchor.group(1).strip().lower() == fragment:
                explicit_anchor_lines.append(index)
        heading = _MARKDOWN_HEADING.match(line)
        if not heading:
            continue
        title = heading.group(2).strip().rstrip("#").rstrip()
        slug = _github_slug(title)
        if not slug:
            continue
        suffix = seen.get(slug, 0)
        resolved = f"{slug}-{suffix}" if suffix else slug
        seen[slug] = suffix + 1
        headings.append((index, len(heading.group(1)), resolved))
    return headings, explicit_anchor_lines


def _baseline_start(
    lines: list[str],
    headings: list[tuple[int, int, str]],
    explicit_anchor_lines: list[int],
    fragment: str,
) -> tuple[int, int] | None:
    matching_heading = next((item for item in headings if item[2] == fragment), None)
    if matching_heading is not None:
        return matching_heading[0], matching_heading[1]
    if not explicit_anchor_lines:
        return None
    anchor_line = explicit_anchor_lines[0]
    next_heading = next((item for item in headings if item[0] > anchor_line), None)
    previous_heading = next((item for item in reversed(headings) if item[0] <= anchor_line), None)
    between = lines[anchor_line + 1 : next_heading[0]] if next_heading else ()
    if next_heading is not None and all(not line.strip() or _HTML_ANCHOR.search(line) for line in between):
        return next_heading[0], next_heading[1]
    if previous_heading is not None:
        return previous_heading[0], previous_heading[1]
    return anchor_line, 1


def _baseline_section_end(
    lines: list[str],
    start: int,
    level: int,
    headings: list[tuple[int, int, str]],
) -> int:
    for heading_line, heading_level, _ in headings:
        if heading_line > start and heading_level <= level:
            return heading_line
    return len(lines)


def _baseline_section(markdown: str, reference: str, mismatches: list[str]) -> str | None:
    """Return only the heading section selected by the baseline fragment."""

    _target, separator, fragment = reference.partition("#")
    if not separator:
        mismatches.append(f"baseline fragment missing: {reference}")
        return None
    fragment = unquote(fragment).strip().lower()
    lines = markdown.splitlines()
    headings, explicit_anchor_lines = _baseline_headings(lines, fragment)
    selected = _baseline_start(lines, headings, explicit_anchor_lines, fragment)
    if selected is None:
        return None
    start, level = selected
    end = _baseline_section_end(lines, start, level, headings)
    return "\n".join(lines[start:end])


def _normalize_now(now: datetime, mismatches: list[str]) -> datetime:
    if not isinstance(now, datetime):
        mismatches.append("now must be a datetime")
        return datetime.now(tz=UTC)
    if now.tzinfo is None:
        mismatches.append("now must include timezone")
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _check_identity(root: Path, registry: AuthorityRegistry, head_sha: str, mismatches: list[str]) -> None:
    if not isinstance(head_sha, str) or not _HEAD_SHA.fullmatch(head_sha):
        mismatches.append("HEAD shape invalid")
    if registry.head_source != "git:HEAD":
        mismatches.append(f"head source mismatch: expected git:HEAD, got {registry.head_source}")
    if registry.head_sha not in (None, "git:HEAD") and registry.head_sha.lower() != head_sha.lower():
        mismatches.append("HEAD does not match registry head_sha")
    _check_repository_head(root, registry, head_sha, mismatches)
    _check_branch(root, registry, mismatches)


def _check_repository_head(root: Path, registry: AuthorityRegistry, head_sha: str, mismatches: list[str]) -> None:
    if registry.head_source != "git:HEAD":
        return
    code, repository_head = _git(root, "rev-parse", "HEAD")
    if code != 0 or not _HEAD_SHA.fullmatch(repository_head):
        mismatches.append("repository HEAD unavailable")
        return
    if _HEAD_SHA.fullmatch(head_sha) and repository_head.lower() != head_sha.lower():
        mismatches.append("HEAD does not match repository HEAD")


def _check_branch(root: Path, registry: AuthorityRegistry, mismatches: list[str]) -> None:
    code, branch = _git(root, "branch", "--show-current")
    if code != 0 or not branch:
        mismatches.append("git branch unavailable")
    elif branch != registry.branch:
        mismatches.append(f"branch mismatch: expected {registry.branch}, got {branch}")


def _check_artifacts(root: Path, registry: AuthorityRegistry, mismatches: list[str]) -> list[str]:
    tracked: list[str] = []
    references = (
        ("config/release-authority.json", "registry"),
        (registry.baseline_source.split("#", 1)[0], "baseline"),
        (registry.rule_index, "rule index"),
        (registry.audit_artifact, "audit artifact"),
    ) + tuple((doc.path, "active document") for doc in registry.active_documents)
    for path, label in references:
        if _tracked(root, path):
            tracked.append(path)
        else:
            mismatches.append(f"untracked {label}: {path}")
        if not (root / path).is_file():
            mismatches.append(f"missing {label}: {path}")
    return list(dict.fromkeys(tracked))


def _check_content(root: Path, registry: AuthorityRegistry, mismatches: list[str]) -> str:
    baseline_text = _read_link(root, registry.baseline_source, mismatches, "baseline")
    if baseline_text is not None:
        baseline_section = _baseline_section(baseline_text, registry.baseline_source, mismatches)
        if baseline_section is not None:
            _check_baseline_count(baseline_section, registry.baseline_count, mismatches)
    rule_text = _read_link(root, registry.rule_index, mismatches, "rule index")
    if rule_text is not None:
        _check_rule_count(rule_text, registry.rule_count, mismatches)
    registry_p1 = _normalized_p1(registry.p1_findings, mismatches)
    audit_text = _read_link(root, registry.audit_artifact, mismatches, "audit artifact")
    if audit_text is None:
        return ""
    _check_audit_findings(audit_text, mismatches)
    _check_p1_parity(audit_text, registry_p1, mismatches)
    return audit_text


def _check_baseline_count(text: str, expected: int, mismatches: list[str]) -> None:
    counts = [int(match.group(1)) for match in _BASELINE_COUNT.finditer(text)]
    if not counts or expected not in counts:
        mismatches.append(f"baseline count mismatch: expected {expected}")


def _check_rule_count(text: str, expected: int, mismatches: list[str]) -> None:
    rule_ids = {match.group(1).strip() for match in _RULE_ROW.finditer(text)}
    if len(rule_ids) != expected:
        mismatches.append(f"rule count mismatch: expected {expected}, got {len(rule_ids)}")


def _normalized_p1(values: tuple[str, ...], mismatches: list[str]) -> set[str]:
    normalized = {finding_id.upper() for finding_id in values}
    if len(normalized) != len(values) or any(not _FINDING_ID.fullmatch(finding_id) for finding_id in values):
        mismatches.append("P1 finding roster contains duplicate or invalid IDs")
    return normalized


def _check_audit_findings(text: str, mismatches: list[str]) -> None:
    finding_ids = {f"F-{int(match.group(1)):02d}" for match in _FINDING_ID.finditer(text)}
    expected = {f"F-{index:02d}" for index in range(1, 74)}
    _append_set_mismatch("audit finding IDs mismatch", finding_ids, expected, mismatches)


def _check_p1_parity(text: str, registry_p1: set[str], mismatches: list[str]) -> None:
    audit_p1 = _audit_p1_ids(text)
    _append_set_mismatch("P1 roster mismatch with audit", audit_p1, registry_p1, mismatches)


def _append_set_mismatch(label: str, actual: set[str], expected: set[str], mismatches: list[str]) -> None:
    if actual == expected:
        return
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    detail = f"missing={','.join(missing)}" if missing else ""
    if extra:
        detail += f" extra={','.join(extra)}"
    mismatches.append(f"{label}: {detail.strip()}")


def _audit_p1_ids(audit_text: str) -> set[str]:
    lines = audit_text.splitlines()
    start: int | None = None
    heading_level = 0
    for index, line in enumerate(lines):
        match = _AUDIT_P1_HEADING.match(line)
        if match:
            start = index + 1
            heading_level = len(match.group(1))
            break
    if start is None:
        return set()
    finding_ids: set[str] = set()
    for line in lines[start:]:
        heading = _MARKDOWN_HEADING.match(line)
        if heading and len(heading.group(1)) <= heading_level:
            break
        row = _AUDIT_TABLE_ROW.match(line)
        if row:
            finding_ids.add(row.group(1).upper())
    return finding_ids


def _check_documents(root: Path, registry: AuthorityRegistry, now: datetime, audit_text: str, mismatches: list[str]) -> list[str]:
    expired: list[str] = []
    if registry.last_verified_at is not None:
        if registry.last_verified_at > now:
            mismatches.append("future verification timestamp: registry last_verified_at")
        elif now - registry.last_verified_at > timedelta(hours=registry.max_age_hours):
            expired.append("config/release-authority.json")
    for doc in registry.active_documents:
        if doc.last_verified_at > now:
            mismatches.append(f"future verification timestamp: {doc.path}")
        elif now - doc.last_verified_at > timedelta(hours=registry.max_age_hours):
            expired.append(doc.path)
        text = _read(root, doc.path, mismatches, "active document")
        if "Authority: config/release-authority.json" not in text:
            mismatches.append(f"authority link missing: {doc.path}")
    if "Authority: config/release-authority.json" not in audit_text:
        mismatches.append(f"authority link missing: {registry.audit_artifact}")
    return expired


def check_authority(root: Path, now: datetime, head_sha: str) -> AuthorityReport:
    """Check branch, tracked evidence, consistency and document freshness."""

    root = Path(root).resolve()
    mismatches: list[str] = []
    try:
        registry = load_authority(root / "config/release-authority.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return AuthorityReport("BLOCKED", (), (f"invalid authority registry: {exc}",), ())
    now = _normalize_now(now, mismatches)
    _check_identity(root, registry, head_sha, mismatches)
    tracked = _check_artifacts(root, registry, mismatches)
    audit_text = _check_content(root, registry, mismatches)
    expired = _check_documents(root, registry, now, audit_text, mismatches)

    if mismatches:
        status: AuthorityStatus = "BLOCKED"
    elif expired:
        status = "STALE"
    else:
        status = "PASS"
    return AuthorityReport(status, tuple(dict.fromkeys(tracked)), tuple(dict.fromkeys(mismatches)), tuple(expired))
