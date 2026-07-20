"""Fail closed when entity image renderers bypass descriptor disclosure policy."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = Path("web-nuxt/config/entity-image-renderers.json")
SCHEMA_KEYS = frozenset({"schema_version", "renderers"})
ROW_KEYS = frozenset(
    {
        "file",
        "surface",
        "access_path",
        "source_class",
        "descriptor_producer",
        "presentation",
        "accessibility",
        "test_file",
    }
)
SOURCE_CLASSES = frozenset({"ai-generated", "placeholder", "user-uploaded", "none"})
PRESENTATIONS = frozenset({"short", "full", "short-and-full", "none"})
ACCESSIBILITY = frozenset(
    {
        "aria-describedby-full-copy",
        "visible-full-copy",
        "aria-and-visible-full-copy",
        "no-image-invariant",
    }
)
SOURCE_ROOTS = ("components", "pages", "composables", "utils")
SOURCE_SUFFIXES = frozenset({".vue", ".ts", ".js", ".mjs"})
CANONICAL_PRODUCERS = (
    "describeEntityImages",
    "describeEntityPlaceholder",
    "describePostImages",
    "describeReviewImages",
    "describePostPreviewRows",
    "describeReviewPreviewRows",
    "parseGalleryDescriptor",
    "normalizeSavedImageSnapshot",
    "normalizeEntityEditorialUpload",
)
METADATA_PRODUCERS = frozenset(
    {"appendImageDisclosureToShareText", "buildImageMeta", "descriptorToImageObject", "metadata-helpers"}
)
RAW_FIELDS = frozenset({"image", "images", "image_url", "image_urls"})
RAW_ROOT_HINT = re.compile(
    r"(?:entity|event|item|saved|post|review|gallery|place|record|source|preview|form|response|data|row|card|pick|e|p)$",
    re.I,
)
RAW_ACCESS_RE = re.compile(
    r"\b(?P<root>[A-Za-z_$][\w$]*(?:(?:\?\.|\.)value)?)\s*"
    r"(?:(?:\?\.|\.)\s*(?P<dot>images?|image_urls?)(?![\w$])|(?:\?\.)?\[\s*['\"](?P<bracket>images?|image_urls?)['\"]\s*\])",
    re.I,
)
ASSIGNMENT_RE = re.compile(
    r"\b(?:const|let|var)\s+(?P<name>[A-Za-z_$][\w$]*)\s*(?::\s*[^=;\n]+)?=\s*(?P<value>[^;\n]+)",
)
DESTRUCTURE_RE = re.compile(
    r"\b(?:const|let|var)\s*\{(?P<body>[^}]+)\}\s*=\s*(?P<source>[^;<\n]+)",
)
VUE_TAG_RE = re.compile(r"<(?:img|NuxtImg)\b[^>]*>", re.I | re.S)
COMPONENT_SINK_RE = re.compile(
    r"<(?:[\w.-]*(?:Gallery|Lightbox)|ImageLightbox|PhotoGallery)\b[^>]*\s:(?:images?|thumbnail|cover|poster|src)\s*=\s*['\"][^'\"]+['\"][^>]*>",
    re.I | re.S,
)
STYLE_SINK_RE = re.compile(
    r"(?::style\s*=\s*['\"][^'\"]*(?:backgroundImage|background-image|\bbackground\b)[^'\"]*['\"]|"
    r"\.style\.(?:backgroundImage|background)\s*=\s*[^;\n]+|"
    r"(?:backgroundImage|background-image)\s*:\s*[^,}\n]+)",
    re.I | re.S,
)
SCRIPT_SINK_RE = re.compile(
    r"(?:navigator\.share\s*\([^)]*\)|useSeoMeta\s*\([^)]*\)|"
    r"\b(?:ogImage|twitterImage)\s*[:=]\s*[^,;}\n]+|"
    r"\b(?:const|let|var)\s+(?:ld|[A-Za-z_$][\w$]*(?:ld|schema|json)[A-Za-z_$\w]*)\s*=\s*\{[^}]*\bimage\s*:\s*[^,;}\n]+)",
    re.I | re.S,
)
DISCLOSURE_RE = re.compile(r"<ImageDisclosure\b(?P<attrs>[^>]*)>", re.I | re.S)
ATTR_RE = re.compile(r"(?P<name>[:\w-]+)\s*=\s*(['\"])(?P<value>.*?)\2", re.S)


@dataclass(frozen=True)
class Finding:
    code: str
    file: Path | str
    line: int = 1
    message: str = ""


@dataclass(frozen=True)
class _RawAccess:
    expression: str
    root: str
    field: str
    line: int


@dataclass(frozen=True)
class _Sink:
    expression: str
    line: int
    kind: str


def _line(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _finding(code: str, file: Path | str, message: str, line: int = 1) -> Finding:
    return Finding(code=code, file=file, line=line, message=message)


def _valid_relative_path(value: object, *, prefix: str | None = None) -> bool:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or path.parts[0].endswith(":") or any(part in {"", ".", ".."} for part in path.parts):
        return False
    return prefix is None or value.startswith(prefix)


def _registry_shape_error(entry: object, label: str) -> Finding | None:
    if not isinstance(entry, dict) or set(entry) != ROW_KEYS:
        return _finding(
            "INVALID_ENTITY_IMAGE_REGISTRY",
            REGISTRY_PATH,
            f"{label} must contain exactly the eight renderer keys",
        )
    if not all(isinstance(entry[key], str) and entry[key].strip() for key in ROW_KEYS):
        return _finding(
            "INVALID_ENTITY_IMAGE_REGISTRY",
            REGISTRY_PATH,
            f"{label} values must be non-empty strings",
        )
    return None


def _registry_source_error(entry: dict, label: str) -> Finding | None:
    file = entry["file"]
    source_root = file.split("/", 1)[0]
    valid = _valid_relative_path(file) and source_root in SOURCE_ROOTS and Path(file).suffix in SOURCE_SUFFIXES
    if valid:
        return None
    return _finding(
        "INVALID_ENTITY_IMAGE_REGISTRY",
        REGISTRY_PATH,
        f"{label} has an invalid source path: {file}",
    )


def _registry_test_error(entry: dict, label: str) -> Finding | None:
    test_file = entry["test_file"]
    valid = _valid_relative_path(test_file, prefix="tests/") and test_file.endswith((".test.ts", ".spec.ts"))
    if valid:
        return None
    return _finding(
        "INVALID_ENTITY_IMAGE_REGISTRY",
        REGISTRY_PATH,
        f"{label} has an invalid test path: {test_file}",
    )


def _registry_enum_error(entry: dict, label: str) -> Finding | None:
    if entry["source_class"] not in SOURCE_CLASSES:
        return _finding("INVALID_ENTITY_IMAGE_REGISTRY", REGISTRY_PATH, f"{label} has invalid source_class")
    if entry["presentation"] not in PRESENTATIONS or entry["accessibility"] not in ACCESSIBILITY:
        return _finding(
            "INVALID_ENTITY_IMAGE_REGISTRY",
            REGISTRY_PATH,
            f"{label} has invalid presentation/accessibility",
        )
    return None


def _is_no_image_combination(entry: dict) -> bool:
    return (
        entry["access_path"] == "popup"
        and entry["descriptor_producer"] == "no-image-invariant"
        and entry["presentation"] == "none"
        and entry["accessibility"] == "no-image-invariant"
    )


def _registry_combination_error(entry: dict, label: str) -> Finding | None:
    invariant = entry["source_class"] == "none"
    if invariant != _is_no_image_combination(entry):
        return _finding(
            "INVALID_ENTITY_IMAGE_REGISTRY",
            REGISTRY_PATH,
            f"{label} uses an invalid no-image-invariant combination",
        )
    if invariant:
        return None
    expected = {
        "short": {"aria-describedby-full-copy", "aria-and-visible-full-copy"},
        "full": {"visible-full-copy", "aria-and-visible-full-copy"},
        "short-and-full": {"aria-and-visible-full-copy"},
    }.get(entry["presentation"], set())
    if entry["accessibility"] in expected:
        return None
    return _finding(
        "INVALID_ENTITY_IMAGE_REGISTRY",
        REGISTRY_PATH,
        f"{label} has an incompatible presentation/accessibility combination",
    )


def _registry_duplicate_error(entry: dict, seen: set[tuple[str, str, str]]) -> Finding | None:
    identity = (entry["file"], entry["surface"], entry["source_class"])
    duplicate = identity in seen
    seen.add(identity)
    if not duplicate:
        return None
    return _finding(
        "DUPLICATE_ENTITY_IMAGE_RENDERER",
        REGISTRY_PATH,
        f"duplicate renderer identity: {identity}",
    )


def _registered_artifact_findings(root: Path, entry: dict) -> list[Finding]:
    findings: list[Finding] = []
    file, test_file = entry["file"], entry["test_file"]
    if _valid_relative_path(file) and not (root / file).is_file():
        findings.append(_finding("MISSING_RENDERER_SOURCE", file, f"registered source does not exist: {file}"))
    if _valid_relative_path(test_file) and not (root / test_file).is_file():
        findings.append(_finding("MISSING_RENDERER_TEST", test_file, f"registered focused test does not exist: {test_file}"))
    return findings


def _validate_registry_entry(
    root: Path,
    index: int,
    entry: object,
    seen: set[tuple[str, str, str]],
) -> tuple[dict | None, list[Finding]]:
    label = f"registry row {index}"
    shape_error = _registry_shape_error(entry, label)
    if shape_error is not None:
        return None, [shape_error]
    typed_entry = entry
    errors = [
        error
        for error in (
            _registry_source_error(typed_entry, label),
            _registry_test_error(typed_entry, label),
            _registry_enum_error(typed_entry, label),
            _registry_combination_error(typed_entry, label),
            _registry_duplicate_error(typed_entry, seen),
        )
        if error is not None
    ]
    findings = errors + _registered_artifact_findings(root, typed_entry)
    return (None if errors else typed_entry), findings


def _validate_registry_entries(
    root: Path,
    registry: Sequence[dict],
) -> tuple[dict[str, list[dict]], list[Finding]]:
    grouped: dict[str, list[dict]] = {}
    findings: list[Finding] = []
    seen: set[tuple[str, str, str]] = set()
    for index, entry in enumerate(registry):
        validated, entry_findings = _validate_registry_entry(root, index, entry, seen)
        findings.extend(entry_findings)
        if validated is not None:
            grouped.setdefault(validated["file"], []).append(validated)
    return grouped, findings


def group_validated_registry_entries(root: Path, registry: Sequence[dict]) -> list[Finding]:
    """Validate registry rows; retained as a small public seam for guard tests."""
    return _validate_registry_entries(root, registry)[1]


def _load_registry(root: Path) -> tuple[list[dict], list[Finding]]:
    path = root / REGISTRY_PATH
    if not path.is_file():
        return [], [_finding("MISSING_ENTITY_IMAGE_REGISTRY", REGISTRY_PATH, "entity image renderer registry is required")]
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [], [_finding("INVALID_ENTITY_IMAGE_REGISTRY", REGISTRY_PATH, f"registry cannot be loaded: {type(exc).__name__}")]
    if not isinstance(document, dict) or set(document) != SCHEMA_KEYS:
        return [], [_finding("INVALID_ENTITY_IMAGE_REGISTRY", REGISTRY_PATH, "registry top-level keys must be exactly schema_version and renderers")]
    if type(document["schema_version"]) is not int or document["schema_version"] != 1 or not isinstance(document["renderers"], list):
        return [], [_finding("INVALID_ENTITY_IMAGE_REGISTRY", REGISTRY_PATH, "registry requires schema_version=1 and a renderers array")]
    return document["renderers"], []


def iter_frontend_source_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for base in SOURCE_ROOTS:
        directory = root / base
        if not directory.is_dir():
            continue
        paths.extend(
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix in SOURCE_SUFFIXES and "tests" not in path.relative_to(root).parts
        )
    return sorted(set(paths))


def _raw_accesses(text: str) -> list[_RawAccess]:
    accesses: list[_RawAccess] = []
    for match in RAW_ACCESS_RE.finditer(text):
        root = re.sub(r"(?:\?\.|\.)value$", "", match.group("root"), flags=re.I)
        field = (match.group("dot") or match.group("bracket")).lower()
        if "descriptor" in root.lower() or "meta" in root.lower():
            continue
        if field == "image" and not RAW_ROOT_HINT.search(root):
            continue
        accesses.append(_RawAccess(match.group(0), root, field, _line(text, match.start())))
    return accesses


def _destructured_raw_accesses(text: str) -> list[_RawAccess]:
    """Materialize raw accesses hidden behind object destructuring."""
    accesses: list[_RawAccess] = []
    for match in DESTRUCTURE_RE.finditer(text):
        source = match.group("source").strip()
        source_root = re.sub(r"(?:\?\.|\.)value$", "", source)
        if not RAW_ROOT_HINT.search(source_root):
            continue
        for item in match.group("body").split(","):
            parts = [part.strip() for part in item.split(":", 1)]
            field = parts[0].lower()
            if field not in RAW_FIELDS:
                continue
            alias = parts[-1]
            if re.fullmatch(r"[A-Za-z_$][\w$]*", alias):
                accesses.append(_RawAccess(f"{source}.{field}", source_root, field, _line(text, match.start())))
    return accesses


def _contains_name(expression: str, name: str) -> bool:
    return re.search(rf"(?<![\w$]){re.escape(name)}(?![\w$])", expression) is not None


def _has_typed_descriptor_images(text: str) -> bool:
    return bool(
        re.search(r"\bimages\s*[?:]?\s*(?:readonly\s+)?(?:ReadonlyArray<\s*)?ImageDescriptor(?:\s*>|\s*\[\s*\])", text)
    )


def _is_canonical_assignment(assignment: re.Match, typed_descriptor_images: bool) -> bool:
    name, value = assignment.group("name"), assignment.group("value")
    prefix = assignment.group(0).split("=", 1)[0]
    return bool(
        "ImageDescriptor" in prefix
        or any(producer in value for producer in CANONICAL_PRODUCERS)
        or (typed_descriptor_images and re.search(r"\bprops(?:\?\.|\.)images\b", value))
        or "Descriptor" in name
    )


def _canonical_assignment_aliases(assignments: Sequence[re.Match], text: str) -> set[str]:
    typed_descriptor_images = _has_typed_descriptor_images(text)
    return {
        assignment.group("name")
        for assignment in assignments
        if _is_canonical_assignment(assignment, typed_descriptor_images)
    }


def _destructured_aliases(text: str) -> set[str]:
    aliases: set[str] = set()
    for destructure in DESTRUCTURE_RE.finditer(text):
        source = destructure.group("source")
        source_is_raw = bool(_raw_accesses(f"source.images; {source}.images")) or bool(RAW_ROOT_HINT.search(re.sub(r"(?:\?\.|\.)value.*$", "", source.strip())))
        if not source_is_raw:
            continue
        for item in destructure.group("body").split(","):
            parts = [part.strip() for part in item.split(":", 1)]
            field, alias = parts[0], parts[-1]
            if field in RAW_FIELDS and re.fullmatch(r"[A-Za-z_$][\w$]*", alias):
                aliases.add(alias)
    return aliases


def _assignment_is_raw(
    assignment: re.Match,
    raw_aliases: set[str],
    canonical_aliases: set[str],
) -> bool:
    name, value = assignment.group("name"), assignment.group("value")
    if name in raw_aliases or name in canonical_aliases:
        return False
    return bool(_raw_accesses(value)) or any(_contains_name(value, alias) for alias in raw_aliases)


def _propagate_raw_aliases(
    assignments: Sequence[re.Match],
    raw_aliases: set[str],
    canonical_aliases: set[str],
) -> None:
    changed = True
    while changed:
        changed = False
        for assignment in assignments:
            if _assignment_is_raw(assignment, raw_aliases, canonical_aliases):
                raw_aliases.add(assignment.group("name"))
                changed = True


def trace_raw_image_aliases(text: str) -> set[str]:
    assignments = list(ASSIGNMENT_RE.finditer(text))
    raw_aliases = _destructured_aliases(text)
    canonical_aliases = _canonical_assignment_aliases(assignments, text)
    _propagate_raw_aliases(assignments, raw_aliases, canonical_aliases)
    return raw_aliases


def find_image_render_sinks(
    text: str,
    *,
    require_raw_source: bool = False,
    raw_aliases: Iterable[str] = (),
) -> list[_Sink]:
    candidates: list[_Sink] = []
    patterns = ((VUE_TAG_RE, "image"), (COMPONENT_SINK_RE, "gallery"), (STYLE_SINK_RE, "background"), (SCRIPT_SINK_RE, "script"))
    for pattern, kind in patterns:
        for match in pattern.finditer(text):
            candidates.append(_Sink(match.group(0), _line(text, match.start()), kind))
    if not require_raw_source:
        return candidates
    aliases = set(raw_aliases)
    raw: list[_Sink] = []
    for sink in candidates:
        if _raw_accesses(sink.expression) or any(_contains_name(sink.expression, alias) for alias in aliases):
            raw.append(sink)
    return raw


def _entry_matches_access(entry: dict, access: _RawAccess) -> bool:
    path = entry["access_path"].lower().replace("?.", ".").replace(".value", "")
    if path in {"popup", "metadata.image", "native-share.image", "descriptor"}:
        return False
    fields = set(re.findall(r"(?:^|[.|])(images?|image_urls?)(?:$|[.|])", path))
    return access.field in fields


def _attrs(tag_attrs: str) -> dict[str, str]:
    return {match.group("name"): match.group("value") for match in ATTR_RE.finditer(tag_attrs)}


def _normalized_binding(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[\s'\"`:{}()?!]", "", value).replace(".value", "")


def _disclosures(text: str) -> list[dict[str, str]]:
    return [_attrs(match.group("attrs")) for match in DISCLOSURE_RE.finditer(text)]


def _binding(attributes: dict[str, str], *names: str) -> str:
    value = next((attributes[name] for name in names if attributes.get(name)), None)
    return _normalized_binding(value)


def _sink_attributes(text: str) -> list[dict[str, str]]:
    sink_tags = VUE_TAG_RE.findall(text) + COMPONENT_SINK_RE.findall(text)
    return [_attrs(tag) for tag in sink_tags]


def _disclosure_links_sink(disclosure: dict[str, str], sink: dict[str, str]) -> bool:
    disclosure_id = _binding(disclosure, ":id", "id")
    descriptor = _binding(disclosure, ":descriptor", "descriptor")
    aria = _binding(sink, ":aria-describedby", "aria-describedby")
    source = _binding(sink, ":src", "src", ":images", ":image")
    ids_match = bool(disclosure_id and aria and disclosure_id == aria)
    descriptor_matches = bool(descriptor and aria and descriptor.split(".")[0] in source and disclosure_id == aria)
    return ids_match or descriptor_matches


def _linked_aria_proof(text: str) -> bool:
    sinks = _sink_attributes(text)
    return any(_disclosure_links_sink(disclosure, sink) for disclosure in _disclosures(text) for sink in sinks)


def _visible_full_copy(text: str) -> bool:
    return bool(
        re.search(r"\{\{[^}]*\.full_disclosure[^}]*\}\}", text)
        or re.search(r"(?:caption|description)\s*:\s*[^,}\n]*\.full_disclosure", text)
        or re.search(r"(?:ogImageAlt|twitterImageAlt)\s*:\s*[^,}\n]*\.full_disclosure", text)
        or any((item.get("presentation") or item.get(":presentation")) == "full" for item in _disclosures(text))
    )


def has_required_presentation(text: str, presentation: str, source_class: str) -> bool:
    del source_class
    disclosures = _disclosures(text)
    has_short = any((item.get("presentation") or item.get(":presentation")) == "short" for item in disclosures)
    has_full = any((item.get("presentation") or item.get(":presentation")) == "full" for item in disclosures) or _visible_full_copy(text)
    if presentation == "short":
        return has_short
    if presentation == "full":
        return has_full
    if presentation == "short-and-full":
        return has_short and has_full
    return presentation == "none"


def has_accessibility_proof(text: str, accessibility: str) -> bool:
    if accessibility == "aria-describedby-full-copy":
        return _linked_aria_proof(text)
    if accessibility == "visible-full-copy":
        return _visible_full_copy(text)
    if accessibility == "aria-and-visible-full-copy":
        return _linked_aria_proof(text) and _visible_full_copy(text)
    return accessibility == "no-image-invariant"


def _extract_braced_block(text: str, start: int) -> str | None:
    brace = text.find("{", start)
    if brace < 0:
        return None
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(brace, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {"'", '"', "`"}:
            quote = char
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace : index + 1]
    return None


def _map_invariant_ok(text: str) -> bool:
    popup_match = re.search(r"\bfunction\s+popupHTML\b", text)
    popup = _extract_braced_block(text, popup_match.start()) if popup_match else None
    marker = 'data-entity-image-policy="no-image-invariant"'
    if not popup or marker not in popup:
        return False
    policy_body = popup.replace(marker, "")
    if VUE_TAG_RE.search(policy_body) or re.search(r"(?:image|images|image_url|image_urls|backgroundImage|background-image)", policy_body, re.I):
        return False
    calls = list(re.finditer(r"\.setHTML\s*\((?P<value>[^;]+)\)", text, re.S))
    if not calls:
        return False
    return all(re.search(r"\bpopupHTML\s*\(", call.group("value")) for call in calls)


def _metadata_helpers_are_complete(text: str) -> bool:
    required = METADATA_PRODUCERS - {"metadata-helpers"}
    return all(name in text for name in required) and text.count("full_disclosure") >= 3


def _metadata_helper_text(root: Path) -> str:
    helper_path = root / "composables/useSeoHelpers.ts"
    if not helper_path.is_file():
        return ""
    return helper_path.read_text(encoding="utf-8", errors="replace")


def _social_metadata_proof(text: str, helper_text: str) -> tuple[bool, bool]:
    has_social = "ogImage" in text or "twitterImage" in text
    exact_full_copy = bool(re.search(r"(?:ogImageAlt|twitterImageAlt)[^\n]*full_disclosure", text))
    return has_social, exact_full_copy or "buildImageMeta" in helper_text


def _json_metadata_proof(text: str, helper_text: str) -> tuple[bool, bool]:
    has_json_ld = "descriptorToImageObject" in text or bool(
        re.search(r"\b(?:ld|jsonLd|articleLd|adminLd)\b[\s\S]*\bimage\b[\s\S]*full_disclosure", text)
    )
    exact_full_copy = bool(re.search(r"(?:caption|description)[^\n]*full_disclosure", text))
    helper_full_copy = "descriptorToImageObject" in text and "full_disclosure" in helper_text
    return has_json_ld, exact_full_copy or helper_full_copy


def _metadata_states_are_valid(social: tuple[bool, bool], json_ld: tuple[bool, bool]) -> bool:
    has_social, social_full = social
    has_json_ld, json_full = json_ld
    return (not has_social or social_full) and (not has_json_ld or json_full) and (has_social or has_json_ld)


def _metadata_proof(text: str, entry: dict, root: Path) -> bool:
    producer = entry["descriptor_producer"]
    if producer == "appendImageDisclosureToShareText":
        return bool(re.search(r"navigator\.share[\s\S]*appendImageDisclosureToShareText\s*\(", text))
    if producer == "metadata-helpers" or entry["file"].endswith("useSeoHelpers.ts"):
        return _metadata_helpers_are_complete(text)
    if producer not in text:
        return False
    helper_text = _metadata_helper_text(root)
    return _metadata_states_are_valid(
        _social_metadata_proof(text, helper_text),
        _json_metadata_proof(text, helper_text),
    )


def _delegation_proof(text: str, producer: str) -> bool:
    if producer in {"EntityCard", "SavedEntityCard", "PhotoGallery", "ImageLightbox"}:
        return re.search(rf"<{re.escape(producer)}\b", text) is not None
    return producer in text and not find_image_render_sinks(text, require_raw_source=True, raw_aliases=trace_raw_image_aliases(text))


def _is_metadata_entry(entry: dict) -> bool:
    haystack = f"{entry['surface']} {entry['access_path']} {entry['descriptor_producer']}".lower()
    return entry["descriptor_producer"] in METADATA_PRODUCERS or any(token in haystack for token in ("metadata", "native-share", "json-ld", "twitter", "og-image"))


def _is_component_delegation(entry: dict) -> bool:
    return entry["descriptor_producer"] in {"EntityCard", "SavedEntityCard", "PhotoGallery", "ImageLightbox"}


def _has_delegated_presentation(text: str, presentation: str) -> bool:
    if presentation == "full":
        return bool(re.search(r"<(?:Lazy)?(?:PhotoGallery|ImageLightbox)\b", text))
    if presentation == "short":
        return bool(re.search(r"<(?:EntityCard|SavedEntityCard)\b", text))
    return False


def _is_descriptor_producer_module(relative: str, text: str, raw_sinks: Sequence[_Sink]) -> bool:
    if raw_sinks or not relative.startswith("utils/"):
        return False
    return any(re.search(rf"\bexport\s+function\s+{re.escape(name)}\b", text) for name in CANONICAL_PRODUCERS)


@dataclass(frozen=True)
class _SourceAnalysis:
    relative: str
    text: str
    entries: Sequence[dict]
    accesses: Sequence[_RawAccess]
    render_sinks: Sequence[_Sink]
    raw_render_sinks: Sequence[_Sink]


def _analyse_source(root: Path, path: Path, entries: Sequence[dict]) -> _SourceAnalysis:
    text = path.read_text(encoding="utf-8", errors="replace")
    aliases = trace_raw_image_aliases(text)
    return _SourceAnalysis(
        relative=path.relative_to(root).as_posix(),
        text=text,
        entries=entries,
        accesses=_raw_accesses(text) + _destructured_raw_accesses(text),
        render_sinks=find_image_render_sinks(text),
        raw_render_sinks=find_image_render_sinks(text, require_raw_source=True, raw_aliases=aliases),
    )


def _unregistered_access_findings(analysis: _SourceAnalysis) -> list[Finding]:
    if _is_descriptor_producer_module(analysis.relative, analysis.text, analysis.raw_render_sinks):
        return []
    return [
        _finding(
            "UNREGISTERED_ENTITY_IMAGE_RENDERER",
            analysis.relative,
            f"unregistered raw entity image access: {access.expression}",
            access.line,
        )
        for access in analysis.accesses
        if not any(_entry_matches_access(entry, access) for entry in analysis.entries)
    ]


def _raw_sink_findings(analysis: _SourceAnalysis) -> list[Finding]:
    if not analysis.raw_render_sinks:
        return []
    sink = analysis.raw_render_sinks[0]
    return [
        _finding(
            "RAW_DESCRIPTOR_BYPASS",
            analysis.relative,
            f"raw image reaches {sink.kind} sink: {sink.expression.strip()}",
            sink.line,
        )
    ]


def _invariant_entry_findings(analysis: _SourceAnalysis, entry: dict) -> list[Finding]:
    if _map_invariant_ok(analysis.text):
        return []
    return [
        _finding(
            "BROKEN_NO_IMAGE_INVARIANT",
            analysis.relative,
            f"{entry['surface']} must keep popupHTML and every setHTML caller image-free",
        )
    ]


def _metadata_entry_findings(root: Path, analysis: _SourceAnalysis, entry: dict) -> list[Finding]:
    findings: list[Finding] = []
    producer, surface = entry["descriptor_producer"], entry["surface"]
    if producer not in analysis.text and producer != "metadata-helpers":
        findings.append(_finding("MISSING_DESCRIPTOR_PRODUCER", analysis.relative, f"{surface} is missing {producer}"))
    if not _metadata_proof(analysis.text, entry, root):
        findings.append(
            _finding(
                "MISSING_METADATA_DISCLOSURE",
                analysis.relative,
                f"{surface} does not preserve full disclosure in metadata",
            )
        )
    return findings


def _component_entry_findings(analysis: _SourceAnalysis, entry: dict) -> list[Finding]:
    producer, surface = entry["descriptor_producer"], entry["surface"]
    if _delegation_proof(analysis.text, producer):
        return []
    return [
        _finding(
            "MISSING_DELEGATION_PROOF",
            analysis.relative,
            f"{surface} must delegate one hop to {producer}",
        )
    ]


def _adapter_entry_findings(analysis: _SourceAnalysis, entry: dict) -> list[Finding]:
    producer, surface = entry["descriptor_producer"], entry["surface"]
    if _delegation_proof(analysis.text, producer):
        return []
    return [
        _finding(
            "MISSING_DELEGATION_PROOF",
            analysis.relative,
            f"{surface} must prove a descriptor-only adapter boundary",
        )
    ]


def _direct_entry_findings(analysis: _SourceAnalysis, entry: dict) -> list[Finding]:
    findings: list[Finding] = []
    producer, surface = entry["descriptor_producer"], entry["surface"]
    delegated = _has_delegated_presentation(analysis.text, entry["presentation"])
    if producer not in analysis.text:
        findings.append(_finding("MISSING_DESCRIPTOR_PRODUCER", analysis.relative, f"{surface} is missing {producer}"))
    if not has_required_presentation(analysis.text, entry["presentation"], entry["source_class"]) and not delegated:
        findings.append(
            _finding(
                "MISSING_DISCLOSURE_PRESENTATION",
                analysis.relative,
                f"{surface} is missing {entry['presentation']} disclosure",
            )
        )
    if not has_accessibility_proof(analysis.text, entry["accessibility"]) and not delegated:
        findings.append(
            _finding(
                "MISSING_ACCESSIBLE_ASSOCIATION",
                analysis.relative,
                f"{surface} is missing expression-linked {entry['accessibility']} proof",
            )
        )
    return findings


def _entry_findings(root: Path, analysis: _SourceAnalysis, entry: dict) -> list[Finding]:
    if entry["descriptor_producer"] == "no-image-invariant":
        return _invariant_entry_findings(analysis, entry)
    if _is_metadata_entry(entry):
        return _metadata_entry_findings(root, analysis, entry)
    if _is_component_delegation(entry):
        return _component_entry_findings(analysis, entry)
    if not analysis.render_sinks:
        return _adapter_entry_findings(analysis, entry)
    return _direct_entry_findings(analysis, entry)


def _scan_source(root: Path, path: Path, entries: Sequence[dict]) -> list[Finding]:
    analysis = _analyse_source(root, path, entries)
    findings = _unregistered_access_findings(analysis) + _raw_sink_findings(analysis)
    for entry in entries:
        findings.extend(_entry_findings(root, analysis, entry))
    return findings


def scan_entity_image_renderers(root: Path, registry: Sequence[dict]) -> list[Finding]:
    entries_by_file, findings = _validate_registry_entries(root, registry)
    for path in iter_frontend_source_files(root):
        relative = path.relative_to(root).as_posix()
        findings.extend(_scan_source(root, path, entries_by_file.get(relative, [])))
    return findings


class EntityImageRendererCheck:
    name = "entity image renderer registry"
    level = "hard"
    rule = "R20.10"

    def __init__(self, root: Path | None = None):
        self._root = root

    @property
    def root(self) -> Path:
        if self._root is not None:
            return self._root
        from checks.common import repo_root

        return repo_root()

    @staticmethod
    def _relevant(files: Sequence[str]) -> bool:
        checker = "scripts/checks/check_entity_image_renderers.py"
        registry = REGISTRY_PATH.as_posix()
        for value in files:
            rel = value.replace("\\", "/")
            if rel in {checker, registry}:
                return True
            if rel.startswith("web-nuxt/") and Path(rel).suffix in SOURCE_SUFFIXES:
                return True
        return False

    def run(self, files: list[str] | None = None) -> dict:
        if files is not None and not self._relevant(files):
            return {"check": self.name, "level": self.level, "rule": self.rule, "count": 0, "violations": []}
        registry, findings = _load_registry(self.root)
        if not findings:
            frontend_root = self.root / "web-nuxt"
            findings.extend(scan_entity_image_renderers(frontend_root, registry))
        violations = [
            {
                "file": str(finding.file).replace("\\", "/"),
                "line": finding.line,
                "rule": self.rule,
                "code": finding.code,
                "msg": finding.message or finding.code,
            }
            for finding in findings
        ]
        return {"check": self.name, "level": self.level, "rule": self.rule, "count": len(violations), "violations": violations}


CHECKS = [EntityImageRendererCheck()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = EntityImageRendererCheck(root=args.root).run()
    for violation in result["violations"]:
        print(f"{violation['code']} {violation['file']}:{violation['line']} {violation['msg']}")
    return 1 if result["count"] else 0


if __name__ == "__main__":
    sys.exit(main())
