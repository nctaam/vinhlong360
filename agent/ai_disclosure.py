from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

if __package__:
    from .launch_artifacts import LoadedArtifact, load_artifact
else:
    from launch_artifacts import LoadedArtifact, load_artifact


ARTIFACT_NAME = "ai-disclosure.json"
EXPECTED_SCHEMA_VERSION = 1
EXPECTED_REVISION = "ai-disclosure-v1"
ROOT_KEYS = frozenset(
    {
        "entity_ai",
        "forbidden_entity_image_claims",
        "placeholder",
        "revision",
        "schema_version",
        "ugc_photo",
    }
)
COPY_KEYS = frozenset({"accessible_description_key", "full_disclosure", "short_label"})


@dataclass(frozen=True)
class DisclosureCopy:
    short_label: str | None
    full_disclosure: str
    accessible_description_key: str


CANONICAL_ENTITY_AI = DisclosureCopy(
    short_label="Minh h\u1ecda AI",
    full_disclosure=(
        "\u1ea2nh minh h\u1ecda do AI d\u1ef1ng \u2014 kh\u00f4ng ph\u1ea3i "
        "\u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7."
    ),
    accessible_description_key="entity-ai-full",
)
CANONICAL_PLACEHOLDER = DisclosureCopy(
    short_label=None,
    full_disclosure=(
        "Minh h\u1ecda \u0111\u1ed3 h\u1ecda \u2014 ch\u01b0a c\u00f3 \u1ea3nh ri\u00eang cho "
        "\u0111\u1ecba \u0111i\u1ec3m."
    ),
    accessible_description_key="entity-placeholder-full",
)
CANONICAL_UGC_PHOTO = DisclosureCopy(
    short_label="\u1ea2nh ng\u01b0\u1eddi d\u00f9ng",
    full_disclosure="\u1ea2nh do ng\u01b0\u1eddi d\u00f9ng cung c\u1ea5p.",
    accessible_description_key="ugc-photo-full",
)
CANONICAL_FORBIDDEN_CLAIMS = (
    "\u1ea3nh th\u1eadt",
    "real photo",
    "documentary photo",
    "on-site photo",
    "\u1ea3nh ch\u1ee5p t\u1ea1i ch\u1ed7",
)


def canonical_disclosure_copy() -> dict[str, Any]:
    return {
        "entity_ai": {
            "short_label": CANONICAL_ENTITY_AI.short_label,
            "full_disclosure": CANONICAL_ENTITY_AI.full_disclosure,
            "accessible_description_key": (
                CANONICAL_ENTITY_AI.accessible_description_key
            ),
        },
        "placeholder": {
            "short_label": CANONICAL_PLACEHOLDER.short_label,
            "full_disclosure": CANONICAL_PLACEHOLDER.full_disclosure,
            "accessible_description_key": (
                CANONICAL_PLACEHOLDER.accessible_description_key
            ),
        },
        "ugc_photo": {
            "short_label": CANONICAL_UGC_PHOTO.short_label,
            "full_disclosure": CANONICAL_UGC_PHOTO.full_disclosure,
            "accessible_description_key": (
                CANONICAL_UGC_PHOTO.accessible_description_key
            ),
        },
        "forbidden_entity_image_claims": list(CANONICAL_FORBIDDEN_CLAIMS),
    }


def _plain_record(value: object, label: str) -> dict[str, Any] | MappingProxyType:
    if type(value) is not dict and not isinstance(value, MappingProxyType):
        raise ValueError(f"canonical AI disclosure {label} must be a plain JSON object")
    return value


def _exact_keys(
    value: dict[str, Any] | MappingProxyType,
    expected: frozenset[str],
    label: str,
) -> None:
    keys = list(value.keys())
    if any(type(key) is not str for key in keys) or set(keys) != expected:
        raise ValueError(f"canonical AI disclosure {label} keys mismatch")


def _validated_copy(
    value: object,
    expected: DisclosureCopy,
    label: str,
) -> DisclosureCopy:
    record = _plain_record(value, label)
    _exact_keys(record, COPY_KEYS, label)
    short_label = record["short_label"]
    full_disclosure = record["full_disclosure"]
    accessible_description_key = record["accessible_description_key"]
    if (
        (
            short_label is None
            if expected.short_label is None
            else type(short_label) is str
        )
        and short_label == expected.short_label
        and type(full_disclosure) is str
        and full_disclosure == expected.full_disclosure
        and type(accessible_description_key) is str
        and accessible_description_key == expected.accessible_description_key
    ):
        return DisclosureCopy(
            short_label=expected.short_label,
            full_disclosure=expected.full_disclosure,
            accessible_description_key=expected.accessible_description_key,
        )
    raise ValueError(f"canonical AI disclosure {label} mismatch")


def _validated_claims(value: object) -> tuple[str, ...]:
    if type(value) not in {list, tuple}:
        raise ValueError(
            "canonical AI disclosure forbidden claims must be a plain dense JSON array"
        )
    claims = tuple(claim for claim in value)
    if (
        len(claims) != len(CANONICAL_FORBIDDEN_CLAIMS)
        or any(type(claim) is not str for claim in claims)
        or claims != CANONICAL_FORBIDDEN_CLAIMS
    ):
        raise ValueError("canonical AI disclosure forbidden claims mismatch")
    return tuple(claim for claim in CANONICAL_FORBIDDEN_CLAIMS)


def _validated_components(
    value: object,
) -> tuple[str, DisclosureCopy, DisclosureCopy, DisclosureCopy, tuple[str, ...]]:
    data = _plain_record(value, "root")
    _exact_keys(data, ROOT_KEYS, "root")
    if (
        type(data["schema_version"]) is not int
        or data["schema_version"] != EXPECTED_SCHEMA_VERSION
    ):
        raise ValueError("canonical AI disclosure schema_version mismatch")
    if type(data["revision"]) is not str or data["revision"] != EXPECTED_REVISION:
        raise ValueError("canonical AI disclosure revision mismatch")

    return (
        EXPECTED_REVISION,
        _validated_copy(data["entity_ai"], CANONICAL_ENTITY_AI, "entity_ai"),
        _validated_copy(data["placeholder"], CANONICAL_PLACEHOLDER, "placeholder"),
        _validated_copy(data["ugc_photo"], CANONICAL_UGC_PHOTO, "ugc_photo"),
        _validated_claims(data["forbidden_entity_image_claims"]),
    )


def _copy_matches(value: object, expected: DisclosureCopy) -> bool:
    return (
        type(value) is DisclosureCopy
        and (
            value.short_label is None
            if expected.short_label is None
            else type(value.short_label) is str
        )
        and value.short_label == expected.short_label
        and type(value.full_disclosure) is str
        and value.full_disclosure == expected.full_disclosure
        and type(value.accessible_description_key) is str
        and value.accessible_description_key == expected.accessible_description_key
    )


@dataclass(frozen=True)
class LoadedAiDisclosure:
    artifact: LoadedArtifact
    revision: str
    entity_ai: DisclosureCopy
    placeholder: DisclosureCopy
    ugc_photo: DisclosureCopy
    forbidden_entity_image_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        artifact_components = _validated_components(self.artifact.data)
        if type(self.forbidden_entity_image_claims) not in {list, tuple}:
            raise ValueError("loaded AI disclosure does not match artifact data")
        owned_claims = tuple(claim for claim in self.forbidden_entity_image_claims)
        if (
            type(self.revision) is not str
            or self.revision != artifact_components[0]
            or not _copy_matches(self.entity_ai, artifact_components[1])
            or not _copy_matches(self.placeholder, artifact_components[2])
            or not _copy_matches(self.ugc_photo, artifact_components[3])
            or any(type(claim) is not str for claim in owned_claims)
            or owned_claims != artifact_components[4]
        ):
            raise ValueError("loaded AI disclosure does not match artifact data")
        object.__setattr__(self, "revision", artifact_components[0])
        object.__setattr__(self, "entity_ai", artifact_components[1])
        object.__setattr__(self, "placeholder", artifact_components[2])
        object.__setattr__(self, "ugc_photo", artifact_components[3])
        object.__setattr__(
            self, "forbidden_entity_image_claims", artifact_components[4]
        )


def load_ai_disclosure(
    *,
    release_root: str | Path | None = None,
    fixture_path: str | Path | None = None,
) -> LoadedAiDisclosure:
    artifact = load_artifact(
        ARTIFACT_NAME,
        release_root=release_root,
        fixture_path=fixture_path,
    )
    revision, entity_ai, placeholder, ugc_photo, claims = _validated_components(
        artifact.data
    )
    return LoadedAiDisclosure(
        artifact=artifact,
        revision=revision,
        entity_ai=entity_ai,
        placeholder=placeholder,
        ugc_photo=ugc_photo,
        forbidden_entity_image_claims=claims,
    )
