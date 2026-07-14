from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

from ai_disclosure import (
    DisclosureCopy,
    LoadedAiDisclosure,
    canonical_disclosure_copy,
    load_ai_disclosure,
)
from launch_artifacts import LoadedArtifact


REPO_ROOT = Path(__file__).resolve().parents[2]
DISCLOSURE_PATH = REPO_ROOT / "config" / "ai-disclosure.json"
CORPUS_PATH = REPO_ROOT / "tests" / "fixtures" / "ai-disclosure-validator-corpus.json"
MUTATION_OPERATIONS = frozenset({"append", "delete", "reverse", "set"})
DANGEROUS_POINTER_TOKENS = frozenset({"__proto__", "constructor", "prototype"})
CANONICAL_ARRAY_INDEX = re.compile(r"^(0|[1-9][0-9]*)$")

EXPECTED_CORPUS = [
    {
        "name": "wrong-revision",
        "operation": "set",
        "pointer": "/revision",
        "value": "ai-disclosure-v0",
        "error": "revision",
    },
    {
        "name": "extra-root-key",
        "operation": "set",
        "pointer": "/extra",
        "value": True,
        "error": "root keys",
    },
    {
        "name": "missing-ugc",
        "operation": "delete",
        "pointer": "/ugc_photo",
        "error": "root keys",
    },
    {
        "name": "altered-ai-short",
        "operation": "set",
        "pointer": "/entity_ai/short_label",
        "value": "AI",
        "error": "entity_ai",
    },
    {
        "name": "altered-ai-full",
        "operation": "set",
        "pointer": "/entity_ai/full_disclosure",
        "value": "altered",
        "error": "entity_ai",
    },
    {
        "name": "altered-placeholder-full",
        "operation": "set",
        "pointer": "/placeholder/full_disclosure",
        "value": "altered",
        "error": "placeholder",
    },
    {
        "name": "altered-ugc-short",
        "operation": "set",
        "pointer": "/ugc_photo/short_label",
        "value": "photo",
        "error": "ugc_photo",
    },
    {
        "name": "altered-ugc-full",
        "operation": "set",
        "pointer": "/ugc_photo/full_disclosure",
        "value": "altered",
        "error": "ugc_photo",
    },
    {
        "name": "altered-accessibility-key",
        "operation": "set",
        "pointer": "/entity_ai/accessible_description_key",
        "value": "wrong",
        "error": "entity_ai",
    },
    {
        "name": "reordered-forbidden-claims",
        "operation": "reverse",
        "pointer": "/forbidden_entity_image_claims",
        "error": "forbidden claims",
    },
    {
        "name": "wrong-forbidden-type",
        "operation": "set",
        "pointer": "/forbidden_entity_image_claims",
        "value": "real photo",
        "error": "forbidden claims",
    },
    {
        "name": "added-forbidden-claim",
        "operation": "append",
        "pointer": "/forbidden_entity_image_claims",
        "value": "current entity photo",
        "error": "forbidden claims",
    },
    {
        "name": "wrong-entity-scalar-type",
        "operation": "set",
        "pointer": "/entity_ai",
        "value": "entity-ai",
        "error": "entity_ai",
    },
    {
        "name": "wrong-placeholder-array-type",
        "operation": "set",
        "pointer": "/placeholder",
        "value": [],
        "error": "placeholder",
    },
    {
        "name": "wrong-ugc-short-object-type",
        "operation": "set",
        "pointer": "/ugc_photo/short_label",
        "value": {"label": "user photo"},
        "error": "ugc_photo",
    },
]

EXACT_LOADER_ERRORS = {
    "wrong-revision": "canonical AI disclosure revision mismatch",
    "extra-root-key": "canonical AI disclosure root keys mismatch",
    "missing-ugc": "canonical AI disclosure root keys mismatch",
    "altered-ai-short": "canonical AI disclosure entity_ai mismatch",
    "altered-ai-full": "canonical AI disclosure entity_ai mismatch",
    "altered-placeholder-full": "canonical AI disclosure placeholder mismatch",
    "altered-ugc-short": "canonical AI disclosure ugc_photo mismatch",
    "altered-ugc-full": "canonical AI disclosure ugc_photo mismatch",
    "altered-accessibility-key": "canonical AI disclosure entity_ai mismatch",
    "reordered-forbidden-claims": "canonical AI disclosure forbidden claims mismatch",
    "wrong-forbidden-type": (
        "canonical AI disclosure forbidden claims must be a plain dense JSON array"
    ),
    "added-forbidden-claim": "canonical AI disclosure forbidden claims mismatch",
    "wrong-entity-scalar-type": (
        "canonical AI disclosure entity_ai must be a plain JSON object"
    ),
    "wrong-placeholder-array-type": (
        "canonical AI disclosure placeholder must be a plain JSON object"
    ),
    "wrong-ugc-short-object-type": "canonical AI disclosure ugc_photo mismatch",
}


def _valid_disclosure() -> dict[str, Any]:
    return json.loads(DISCLOSURE_PATH.read_text(encoding="utf-8"))


def _pointer_parts(pointer: str) -> list[str]:
    if not pointer.startswith("/"):
        raise AssertionError(
            f'AI disclosure corpus pointer must start with "/": {pointer}'
        )
    parts = []
    for part in pointer[1:].split("/"):
        if re.search(r"~(?:[^01]|$)", part):
            raise AssertionError(
                f"AI disclosure corpus pointer has invalid escape: {pointer}"
            )
        decoded = part.replace("~1", "/").replace("~0", "~")
        if decoded in DANGEROUS_POINTER_TOKENS:
            raise AssertionError(
                f"AI disclosure corpus pointer contains forbidden token: {pointer}"
            )
        parts.append(decoded)
    return parts


def _validate_mutation(raw: object, label: str) -> dict[str, Any]:
    if type(raw) is not dict:
        raise AssertionError(
            f"AI disclosure corpus {label} must be a plain JSON object"
        )
    row = raw
    if type(row.get("name")) is not str or not row["name"]:
        raise AssertionError(
            f"AI disclosure corpus {label} name must be a non-empty string"
        )
    operation = row.get("operation")
    if type(operation) is not str or operation not in MUTATION_OPERATIONS:
        raise AssertionError(
            f"AI disclosure corpus operation is unsupported: {operation}"
        )
    if type(row.get("pointer")) is not str:
        raise AssertionError(f"AI disclosure corpus {label} pointer must be a string")
    if type(row.get("error")) is not str or not row["error"]:
        raise AssertionError(
            f"AI disclosure corpus {label} error must be a non-empty string"
        )

    requires_value = operation in {"append", "set"}
    if ("value" in row) != requires_value:
        raise AssertionError(
            f"AI disclosure corpus {label} value presence mismatch for {operation}"
        )
    expected_keys = {"error", "name", "operation", "pointer"}
    if requires_value:
        expected_keys.add("value")
    if set(row) != expected_keys or any(type(key) is not str for key in row):
        raise AssertionError(f"AI disclosure corpus {label} keys mismatch")
    _pointer_parts(row["pointer"])
    return copy.deepcopy(row)


def _load_mutations() -> list[dict[str, Any]]:
    raw = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    if type(raw) is not list:
        raise AssertionError("AI disclosure corpus must be a plain dense JSON array")
    mutations = []
    names: set[str] = set()
    for index, row in enumerate(raw):
        mutation = _validate_mutation(row, f"row[{index}]")
        if mutation["name"] in names:
            raise AssertionError(
                f"AI disclosure corpus row[{index}] name must be unique"
            )
        names.add(mutation["name"])
        mutations.append(mutation)
    return mutations


def _pointer_container(value: object, pointer: str) -> dict[str, Any] | list[Any]:
    if type(value) not in {dict, list}:
        raise AssertionError(
            f"AI disclosure corpus pointer parent is not an object: {pointer}"
        )
    return value


def _existing_pointer_key(
    container: dict[str, Any] | list[Any],
    token: str,
    pointer: str,
    *,
    allow_missing: bool = False,
) -> str:
    if type(container) is list:
        if not CANONICAL_ARRAY_INDEX.fullmatch(token):
            raise AssertionError(
                f"AI disclosure corpus pointer index is invalid: {pointer}"
            )
        if int(token) >= len(container):
            raise AssertionError(
                f"AI disclosure corpus pointer index is out of range: {pointer}"
            )
        return token
    if token not in container:
        if allow_missing:
            return token
        raise AssertionError(
            f"AI disclosure corpus pointer target does not exist: {pointer}"
        )
    return token


def _pointer_value(container: dict[str, Any] | list[Any], key: str) -> object:
    return container[int(key)] if type(container) is list else container[key]


def _pointer_parent(
    document: object,
    pointer: str,
    *,
    allow_missing_final_target: bool = False,
) -> tuple[dict[str, Any] | list[Any], str]:
    parts = _pointer_parts(pointer)
    current = document
    for part in parts[:-1]:
        container = _pointer_container(current, pointer)
        key = _existing_pointer_key(container, part, pointer)
        current = _pointer_value(container, key)
    parent = _pointer_container(current, pointer)
    key = _existing_pointer_key(
        parent,
        parts[-1],
        pointer,
        allow_missing=allow_missing_final_target,
    )
    return parent, key


def _apply_mutation(document: object, raw_mutation: object) -> None:
    mutation = _validate_mutation(raw_mutation, "mutation")
    allow_create = mutation == EXPECTED_CORPUS[1]
    parent, key = _pointer_parent(
        document,
        mutation["pointer"],
        allow_missing_final_target=allow_create,
    )
    operation = mutation["operation"]
    if operation == "delete":
        if type(parent) is list:
            del parent[int(key)]
        else:
            del parent[key]
        return
    if operation == "set":
        value = copy.deepcopy(mutation["value"])
        if type(parent) is list:
            parent[int(key)] = value
        else:
            parent[key] = value
        return

    target = _pointer_value(parent, key)
    if type(target) is not list:
        raise AssertionError(
            f"AI disclosure corpus {operation} target must be an array: "
            f"{mutation['pointer']}"
        )
    if operation == "reverse":
        target.reverse()
    else:
        target.append(copy.deepcopy(mutation["value"]))


def _write_fixture(tmp_path: Path, name: str, data: object) -> Path:
    fixture = tmp_path / f"{name}.json"
    fixture.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return fixture


def _constructor_kwargs(artifact: object) -> dict[str, Any]:
    canonical = canonical_disclosure_copy()
    return {
        "artifact": artifact,
        "revision": "ai-disclosure-v1",
        "entity_ai": DisclosureCopy(**canonical["entity_ai"]),
        "placeholder": DisclosureCopy(**canonical["placeholder"]),
        "ugc_photo": DisclosureCopy(**canonical["ugc_photo"]),
        "forbidden_entity_image_claims": list(
            canonical["forbidden_entity_image_claims"]
        ),
    }


def test_ai_disclosure_supports_repository_package_import():
    script = (
        f"import sys; sys.path.insert(0, {str(REPO_ROOT)!r}); "
        "import agent.ai_disclosure"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_loads_exact_canonical_copy_with_immutable_artifact_snapshot():
    disclosure = load_ai_disclosure()
    raw = DISCLOSURE_PATH.read_bytes()

    assert disclosure.artifact.path == DISCLOSURE_PATH
    assert disclosure.artifact.raw == raw
    assert disclosure.artifact.sha256 == hashlib.sha256(raw).hexdigest()
    assert isinstance(disclosure.artifact.data, MappingProxyType)
    assert disclosure.revision == "ai-disclosure-v1"
    assert disclosure.entity_ai == DisclosureCopy(
        short_label="Minh h\u1ecda AI",
        full_disclosure=(
            "\u1ea2nh minh h\u1ecda do AI d\u1ef1ng \u2014 kh\u00f4ng ph\u1ea3i "
            "\u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7."
        ),
        accessible_description_key="entity-ai-full",
    )
    assert disclosure.placeholder.short_label is None
    assert disclosure.ugc_photo.full_disclosure == (
        "\u1ea2nh do ng\u01b0\u1eddi d\u00f9ng cung c\u1ea5p."
    )
    assert disclosure.forbidden_entity_image_claims == (
        "\u1ea3nh th\u1eadt",
        "real photo",
        "documentary photo",
        "on-site photo",
        "\u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7",
    )
    assert disclosure.artifact.data["forbidden_entity_image_claims"] == (
        disclosure.forbidden_entity_image_claims
    )
    with pytest.raises(TypeError):
        disclosure.artifact.data["revision"] = "changed"
    with pytest.raises(FrozenInstanceError):
        disclosure.revision = "changed"


def test_loads_fixture_and_release_root_without_changing_exact_bytes(tmp_path: Path):
    raw = DISCLOSURE_PATH.read_bytes()
    fixture = tmp_path / "fixture.json"
    fixture.write_bytes(raw)
    release_path = tmp_path / "release" / "config" / "ai-disclosure.json"
    release_path.parent.mkdir(parents=True)
    release_path.write_bytes(raw)

    fixture_loaded = load_ai_disclosure(fixture_path=fixture)
    release_loaded = load_ai_disclosure(release_root=tmp_path / "release")

    assert fixture_loaded.artifact.path == fixture
    assert fixture_loaded.artifact.raw == raw
    assert release_loaded.artifact.path == release_path
    assert release_loaded.artifact.raw == raw


def test_rejects_altered_copy(tmp_path: Path):
    candidate = _valid_disclosure()
    candidate["entity_ai"]["full_disclosure"] = "altered"
    fixture = _write_fixture(tmp_path, "altered-copy", candidate)

    with pytest.raises(ValueError) as error:
        load_ai_disclosure(fixture_path=fixture)

    assert type(error.value) is ValueError
    assert str(error.value) == "canonical AI disclosure entity_ai mismatch"


def test_release_root_and_fixture_path_are_mutually_exclusive(tmp_path: Path):
    with pytest.raises(ValueError) as error:
        load_ai_disclosure(
            release_root=tmp_path,
            fixture_path=tmp_path / "ai.json",
        )

    assert type(error.value) is ValueError
    assert str(error.value) == "release_root and fixture_path are mutually exclusive"


def test_python_applies_the_shared_strict_disclosure_corpus(tmp_path: Path):
    mutations = _load_mutations()

    assert mutations == EXPECTED_CORPUS
    assert set(EXACT_LOADER_ERRORS) == {mutation["name"] for mutation in mutations}
    for mutation in mutations:
        candidate = _valid_disclosure()
        before = copy.deepcopy(candidate)
        load_ai_disclosure(
            fixture_path=_write_fixture(
                tmp_path, f"valid-{mutation['name']}", candidate
            )
        )
        assert candidate == before

        _apply_mutation(candidate, mutation)
        fixture = _write_fixture(tmp_path, mutation["name"], candidate)
        with pytest.raises(ValueError) as error:
            load_ai_disclosure(fixture_path=fixture)

        assert type(error.value) is ValueError
        assert str(error.value) == EXACT_LOADER_ERRORS[mutation["name"]]


@pytest.mark.parametrize(
    "pointer, expected_message",
    [
        (
            "revision",
            'AI disclosure corpus pointer must start with "/": revision',
        ),
        (
            "/entity_ai/~2",
            "AI disclosure corpus pointer has invalid escape: /entity_ai/~2",
        ),
        (
            "/__proto__",
            "AI disclosure corpus pointer contains forbidden token: /__proto__",
        ),
        (
            "/entity_ai/misspelled",
            "AI disclosure corpus pointer target does not exist: /entity_ai/misspelled",
        ),
        (
            "/forbidden_entity_image_claims/01",
            "AI disclosure corpus pointer index is invalid: "
            "/forbidden_entity_image_claims/01",
        ),
        (
            "/forbidden_entity_image_claims/9",
            "AI disclosure corpus pointer index is out of range: "
            "/forbidden_entity_image_claims/9",
        ),
    ],
)
def test_mutation_helper_rejects_unsafe_or_misspelled_pointers(
    pointer: str,
    expected_message: str,
):
    candidate = _valid_disclosure()
    before = copy.deepcopy(candidate)
    mutation = {
        "name": "unsafe-pointer",
        "operation": "set",
        "pointer": pointer,
        "value": "changed",
        "error": "unused",
    }

    with pytest.raises(AssertionError) as error:
        _apply_mutation(candidate, mutation)

    assert type(error.value) is AssertionError
    assert str(error.value) == expected_message
    assert candidate == before


@pytest.mark.parametrize(
    "name, mutate, expected_message",
    [
        (
            "schema-bool",
            lambda data: data.update(schema_version=True),
            "canonical AI disclosure schema_version mismatch",
        ),
        (
            "missing-entity-key",
            lambda data: data["entity_ai"].pop("accessible_description_key"),
            "canonical AI disclosure entity_ai keys mismatch",
        ),
        (
            "extra-placeholder-key",
            lambda data: data["placeholder"].update(extra=True),
            "canonical AI disclosure placeholder keys mismatch",
        ),
        (
            "placeholder-short-not-null",
            lambda data: data["placeholder"].update(short_label="placeholder"),
            "canonical AI disclosure placeholder mismatch",
        ),
    ],
)
def test_rejects_exact_schema_nested_keys_and_placeholder_null(
    tmp_path: Path,
    name: str,
    mutate,
    expected_message: str,
):
    candidate = _valid_disclosure()
    mutate(candidate)

    with pytest.raises(ValueError) as error:
        load_ai_disclosure(fixture_path=_write_fixture(tmp_path, name, candidate))

    assert type(error.value) is ValueError
    assert str(error.value) == expected_message


def test_canonical_copy_returns_fresh_owned_data():
    first = canonical_disclosure_copy()
    second = canonical_disclosure_copy()

    assert (
        first
        == second
        == {
            key: value
            for key, value in _valid_disclosure().items()
            if key not in {"schema_version", "revision"}
        }
    )
    assert first is not second
    assert first["entity_ai"] is not second["entity_ai"]
    assert (
        first["forbidden_entity_image_claims"]
        is not second["forbidden_entity_image_claims"]
    )
    first["entity_ai"]["short_label"] = "changed"
    first["forbidden_entity_image_claims"].append("changed")
    assert canonical_disclosure_copy() == second


def test_loaded_constructor_owns_claims_and_rejects_artifact_divergence():
    canonical = canonical_disclosure_copy()
    claims = list(canonical["forbidden_entity_image_claims"])
    entity_ai = DisclosureCopy(**canonical["entity_ai"])
    placeholder = DisclosureCopy(**canonical["placeholder"])
    ugc_photo = DisclosureCopy(**canonical["ugc_photo"])
    loaded = LoadedAiDisclosure(
        artifact=load_ai_disclosure().artifact,
        revision="ai-disclosure-v1",
        entity_ai=entity_ai,
        placeholder=placeholder,
        ugc_photo=ugc_photo,
        forbidden_entity_image_claims=claims,
    )

    assert loaded.entity_ai is not entity_ai
    assert loaded.placeholder is not placeholder
    assert loaded.ugc_photo is not ugc_photo
    claims.reverse()
    object.__setattr__(entity_ai, "short_label", "changed through retained alias")
    object.__setattr__(placeholder, "full_disclosure", "changed through retained alias")
    object.__setattr__(ugc_photo, "accessible_description_key", "changed-alias")
    assert loaded.entity_ai == DisclosureCopy(**canonical["entity_ai"])
    assert loaded.placeholder == DisclosureCopy(**canonical["placeholder"])
    assert loaded.ugc_photo == DisclosureCopy(**canonical["ugc_photo"])
    assert loaded.forbidden_entity_image_claims == tuple(
        canonical["forbidden_entity_image_claims"]
    )
    with pytest.raises(AttributeError):
        loaded.forbidden_entity_image_claims.append("changed")
    with pytest.raises(FrozenInstanceError):
        loaded.entity_ai = DisclosureCopy(**canonical["entity_ai"])

    divergent_entity = DisclosureCopy(
        short_label="AI",
        full_disclosure=canonical["entity_ai"]["full_disclosure"],
        accessible_description_key="entity-ai-full",
    )
    with pytest.raises(ValueError) as error:
        LoadedAiDisclosure(
            artifact=loaded.artifact,
            revision=loaded.revision,
            entity_ai=divergent_entity,
            placeholder=loaded.placeholder,
            ugc_photo=loaded.ugc_photo,
            forbidden_entity_image_claims=loaded.forbidden_entity_image_claims,
        )

    assert type(error.value) is ValueError
    assert str(error.value) == "loaded AI disclosure does not match artifact data"


def test_loaded_constructor_rejects_fake_and_subclass_artifacts():
    canonical_artifact = load_ai_disclosure().artifact

    class MissingIntegrityArtifact:
        data = canonical_artifact.data

    class InvalidIntegrityArtifact:
        path = canonical_artifact.path
        raw = b"{}"
        data = canonical_artifact.data
        sha256 = "0" * 64

    class UnsupportedLoadedArtifact(LoadedArtifact):
        pass

    subclass_artifact = UnsupportedLoadedArtifact(
        path=canonical_artifact.path,
        raw=canonical_artifact.raw,
        data=canonical_artifact.data,
        sha256=canonical_artifact.sha256,
    )
    for artifact in (
        MissingIntegrityArtifact(),
        InvalidIntegrityArtifact(),
        subclass_artifact,
    ):
        with pytest.raises(TypeError) as error:
            LoadedAiDisclosure(**_constructor_kwargs(artifact))

        assert type(error.value) is TypeError
        assert str(error.value) == (
            "loaded AI disclosure artifact must be an exact LoadedArtifact"
        )


def test_loaded_constructor_reconstructs_and_owns_artifact(tmp_path: Path):
    input_artifact = load_ai_disclosure().artifact
    loaded = LoadedAiDisclosure(**_constructor_kwargs(input_artifact))
    owned_path = loaded.artifact.path
    owned_raw = loaded.artifact.raw
    owned_data = loaded.artifact.data
    owned_sha256 = loaded.artifact.sha256

    assert (
        loaded.artifact is input_artifact,
        loaded.artifact.path is input_artifact.path,
        loaded.artifact.raw is input_artifact.raw,
        loaded.artifact.data is input_artifact.data,
        loaded.artifact.path,
        loaded.artifact.raw,
        loaded.artifact.data,
        loaded.artifact.sha256,
    ) == (
        False,
        False,
        False,
        False,
        input_artifact.path,
        input_artifact.raw,
        input_artifact.data,
        input_artifact.sha256,
    )

    object.__setattr__(input_artifact, "path", tmp_path / "changed.json")
    object.__setattr__(input_artifact, "raw", b"{}")
    object.__setattr__(
        input_artifact,
        "data",
        MappingProxyType({"schema_version": 1}),
    )
    object.__setattr__(input_artifact, "sha256", "0" * 64)

    assert (
        loaded.artifact.path,
        loaded.artifact.raw,
        loaded.artifact.data,
        loaded.artifact.sha256,
    ) == (owned_path, owned_raw, owned_data, owned_sha256)


@pytest.mark.parametrize(
    "field, value, expected_message",
    [
        (
            "sha256",
            "0" * 64,
            "artifact SHA-256 does not match raw bytes",
        ),
        (
            "raw",
            b"{}",
            "artifact SHA-256 does not match raw bytes",
        ),
        (
            "data",
            MappingProxyType({"schema_version": 1}),
            "artifact data does not match raw bytes",
        ),
    ],
)
def test_loaded_constructor_revalidates_artifact_raw_data_and_sha(
    field: str,
    value: object,
    expected_message: str,
):
    artifact = load_ai_disclosure().artifact
    object.__setattr__(artifact, field, value)

    with pytest.raises(ValueError) as error:
        LoadedAiDisclosure(**_constructor_kwargs(artifact))

    assert type(error.value) is ValueError
    assert str(error.value) == expected_message


def test_low_level_artifact_loader_has_no_domain_import_cycle():
    source = (REPO_ROOT / "agent" / "launch_artifacts.py").read_text(encoding="utf-8")
    for forbidden_import in (
        "import route_manifest",
        "from route_manifest",
        "from .route_manifest",
        "import agent.route_manifest",
        "import ai_disclosure",
        "from ai_disclosure",
        "from .ai_disclosure",
        "import agent.ai_disclosure",
    ):
        assert forbidden_import not in source

    scripts = (
        (
            f"import sys; sys.path.insert(0, {str(REPO_ROOT / 'agent')!r}); "
            "import launch_artifacts"
        ),
        (
            f"import sys; sys.path.insert(0, {str(REPO_ROOT)!r}); "
            "import agent.launch_artifacts"
        ),
    )
    for script in scripts:
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                script
                + "; assert 'route_manifest' not in sys.modules"
                + "; assert 'ai_disclosure' not in sys.modules"
                + "; assert 'agent.route_manifest' not in sys.modules"
                + "; assert 'agent.ai_disclosure' not in sys.modules",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
