import copy
import json
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from route_manifest import load_route_manifest, validate_route_manifest_data


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "config" / "launch-indexing-policy.json"


def valid_manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_route_manifest_supports_repository_package_import():
    script = (
        f"import sys; sys.path.insert(0, {str(REPO_ROOT)!r}); "
        "import agent.route_manifest"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_load_route_manifest_preserves_artifact_and_revision(tmp_path):
    fixture = tmp_path / "manifest.json"
    raw = MANIFEST_PATH.read_bytes()
    fixture.write_bytes(raw)

    loaded = load_route_manifest(fixture_path=fixture)

    assert loaded.artifact.path == fixture
    assert loaded.artifact.raw == raw
    assert loaded.revision == "launch-indexing-policy-v1"
    assert loaded.data == valid_manifest()
    with pytest.raises(FrozenInstanceError):
        loaded.revision = "changed"


def test_load_route_manifest_passes_release_root_to_artifact_loader(tmp_path):
    target = tmp_path / "config" / "launch-indexing-policy.json"
    target.parent.mkdir()
    target.write_bytes(MANIFEST_PATH.read_bytes())

    loaded = load_route_manifest(release_root=tmp_path)

    assert loaded.artifact.path == target


def test_validate_route_manifest_returns_a_copy_without_mutating_input():
    candidate = valid_manifest()
    before = copy.deepcopy(candidate)

    parsed = validate_route_manifest_data(candidate)

    assert candidate == before
    assert parsed == before
    assert parsed is not candidate
    assert parsed["normalization"] is not candidate["normalization"]
    assert parsed["exact_routes"] is not candidate["exact_routes"]
    assert parsed["exact_routes"][0] is not candidate["exact_routes"][0]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda data: data["normalization"].pop("query_policy"),
        lambda data: data.update({"extra": True}),
        lambda data: data.update(
            {
                "dynamic_templates": [
                    {
                        "template": "/dia-diem/{entity_id}",
                        "authority": "backend-entity",
                        "sitemap": "backend",
                    },
                    {
                        "template": "/dia-diem/{id}",
                        "authority": "backend-entity",
                        "sitemap": "backend",
                    },
                ]
            }
        ),
        lambda data: data.update(
            {
                "backend_ingress_exceptions": [
                    {"prefix": "/hook", "upstream": "agent", "review_reason": " \t"}
                ]
            }
        ),
    ],
    ids=[
        "missing-normalization-key",
        "extra-root-key",
        "ambiguous-template-signature",
        "blank-ingress-review",
    ],
)
def test_validate_route_manifest_rejects_required_mutation_matrix(mutate):
    candidate = valid_manifest()
    mutate(candidate)

    with pytest.raises(ValueError, match="route manifest"):
        validate_route_manifest_data(candidate)


@pytest.mark.parametrize(
    "field, replacement",
    [
        ("schema_version", True),
        ("schema_version", 1.0),
        ("revision", "launch-indexing-policy-v2"),
        ("canonical_origin", "https://example.com"),
        ("unknown_policy", "indexable-public"),
        ("exact_routes", {}),
    ],
)
def test_validate_route_manifest_rejects_wrong_root_types_and_fixed_values(field, replacement):
    candidate = valid_manifest()
    candidate[field] = replacement

    with pytest.raises(ValueError, match="route manifest"):
        validate_route_manifest_data(candidate)


@pytest.mark.parametrize(
    "field, item",
    [
        ("exact_routes", {"path": "/", "classification": "public", "sitemap": True}),
        (
            "exact_routes",
            {"path": "/", "classification": "indexable-public", "sitemap": 1},
        ),
        (
            "sensitive_prefixes",
            {"prefix": "/admin", "classification": "noindex-follow-public"},
        ),
        (
            "backend_ingress_exceptions",
            {"prefix": "/hook", "upstream": "nuxt", "review_reason": "reviewed"},
        ),
        (
            "backend_ingress_exceptions",
            {"prefix": "/hook", "upstream": "agent", "review_reason": 1},
        ),
        (
            "dynamic_templates",
            {"template": "/foo/{id}", "authority": "backend-entity", "sitemap": False},
        ),
        (
            "dynamic_templates",
            {"template": "/foo/{id}", "authority": "fixed-noindex", "sitemap": "backend"},
        ),
    ],
)
def test_validate_route_manifest_rejects_wrong_item_types_and_relationships(field, item):
    candidate = valid_manifest()
    candidate[field] = [item]

    with pytest.raises(ValueError, match="route manifest"):
        validate_route_manifest_data(candidate)


@pytest.mark.parametrize(
    "path",
    [
        "admin",
        "/admin/",
        "/ad?min",
        "/ad#min",
        "/ad//min",
        "/ad%2Fmin",
        "/ad\\min",
        "/admin/.",
        "/admin/../private",
        "/bad\x00path",
        "/bad\tpath",
        "/bad\x7fpath",
        "/bad path",
        "/bad\u00a0path",
        "/bad{path",
        "/bad}path",
    ],
)
def test_validate_route_manifest_rejects_noncanonical_raw_paths(path):
    candidate = valid_manifest()
    candidate["exact_routes"] = [
        {"path": path, "classification": "indexable-public", "sitemap": True}
    ]

    with pytest.raises(ValueError, match="exact path.*canonical"):
        validate_route_manifest_data(candidate)


@pytest.mark.parametrize("path", ["/release/v1.0", "/-well-known", "/foo~bar", "/foo--bar"])
def test_validate_route_manifest_accepts_reviewed_canonical_neighbors(path):
    candidate = valid_manifest()
    candidate["exact_routes"] = [
        {"path": path, "classification": "indexable-public", "sitemap": True}
    ]

    parsed = validate_route_manifest_data(candidate)

    assert parsed["exact_routes"][0]["path"] == path


def test_validate_route_manifest_matches_typescript_acceptance_of_unicode_nel_path():
    candidate = valid_manifest()
    candidate["exact_routes"] = [
        {"path": "/bad\u0085path", "classification": "indexable-public", "sitemap": True}
    ]

    parsed = validate_route_manifest_data(candidate)

    assert parsed["exact_routes"][0]["path"] == "/bad\u0085path"


def test_validate_route_manifest_matches_typescript_nonblank_unicode_nel_review():
    candidate = valid_manifest()
    candidate["backend_ingress_exceptions"] = [
        {"prefix": "/reviewed-hook", "upstream": "agent", "review_reason": "\u0085"}
    ]

    parsed = validate_route_manifest_data(candidate)

    assert parsed["backend_ingress_exceptions"][0]["review_reason"] == "\u0085"


@pytest.mark.parametrize(
    "template",
    [
        "/dia-diem/{entity_id",
        "/dia-diem/entity_id}",
        "/dia-diem/{}",
        "/dia-diem/{EntityId}",
        "/dia-diem/{1id}",
        "/dia-diem/prefix-{entity_id}",
        "/dia-diem/{entity_id}-suffix",
        "/dia-diem/{entity_id}/{entity_id}",
        "/dia-diem/no-placeholder",
    ],
)
def test_validate_route_manifest_rejects_malformed_placeholders(template):
    candidate = valid_manifest()
    candidate["dynamic_templates"] = [
        {"template": template, "authority": "backend-entity", "sitemap": "backend"}
    ]

    with pytest.raises(ValueError, match="dynamic template"):
        validate_route_manifest_data(candidate)


def test_validate_route_manifest_rejects_overlapping_templates_with_different_signatures():
    candidate = valid_manifest()
    candidate["dynamic_templates"] = [
        {"template": "/foo/{id}/bar", "authority": "fixed-noindex", "sitemap": False},
        {"template": "/foo/baz/{slug}", "authority": "fixed-noindex", "sitemap": False},
    ]

    with pytest.raises(ValueError, match="overlapping dynamic template"):
        validate_route_manifest_data(candidate)


def test_validate_route_manifest_accepts_templates_with_conflicting_literals():
    candidate = valid_manifest()
    candidate["dynamic_templates"] = [
        {"template": "/foo/{id}/bar", "authority": "fixed-noindex", "sitemap": False},
        {"template": "/foo/{slug}/qux", "authority": "fixed-noindex", "sitemap": False},
    ]

    validate_route_manifest_data(candidate)


@pytest.mark.parametrize(
    "field, items, message",
    [
        (
            "exact_routes",
            [
                {"path": "/same", "classification": "indexable-public", "sitemap": True},
                {"path": "/same", "classification": "noindex-follow-public", "sitemap": False},
            ],
            "duplicate exact route",
        ),
        (
            "sensitive_prefixes",
            [
                {"prefix": "/private", "classification": "crawl-blocked-sensitive"},
                {"prefix": "/private", "classification": "crawl-blocked-sensitive"},
            ],
            "duplicate sensitive prefix",
        ),
        (
            "backend_ingress_exceptions",
            [
                {"prefix": "/hook", "upstream": "agent", "review_reason": "first"},
                {"prefix": "/hook", "upstream": "bot-gateway", "review_reason": "second"},
            ],
            "duplicate ingress exception",
        ),
    ],
)
def test_validate_route_manifest_rejects_duplicate_paths_and_prefixes(field, items, message):
    candidate = valid_manifest()
    candidate[field] = items

    with pytest.raises(ValueError, match=message):
        validate_route_manifest_data(candidate)


def test_validate_route_manifest_rejects_ingress_sensitive_segment_overlap():
    candidate = valid_manifest()
    candidate["sensitive_prefixes"] = [
        {"prefix": "/webhook", "classification": "crawl-blocked-sensitive"}
    ]
    candidate["backend_ingress_exceptions"] = [
        {
            "prefix": "/webhook/callback",
            "upstream": "bot-gateway",
            "review_reason": "reviewed callback",
        }
    ]

    with pytest.raises(ValueError, match="ingress/sensitive ambiguity"):
        validate_route_manifest_data(candidate)


def test_validate_route_manifest_does_not_confuse_segment_prefixes():
    candidate = valid_manifest()
    candidate["sensitive_prefixes"] = [
        {"prefix": "/webhook", "classification": "crawl-blocked-sensitive"}
    ]
    candidate["backend_ingress_exceptions"] = [
        {
            "prefix": "/webhook-callback",
            "upstream": "bot-gateway",
            "review_reason": "separate segment",
        }
    ]

    validate_route_manifest_data(candidate)


def test_validate_route_manifest_rejects_exact_template_ambiguity():
    candidate = valid_manifest()
    candidate["exact_routes"].append(
        {"path": "/dia-diem/example", "classification": "indexable-public", "sitemap": True}
    )

    with pytest.raises(ValueError, match="exact/template ambiguity"):
        validate_route_manifest_data(candidate)


@pytest.mark.parametrize("field", ["sensitive_prefixes", "backend_ingress_exceptions"])
def test_validate_route_manifest_rejects_root_prefixes(field):
    candidate = valid_manifest()
    if field == "sensitive_prefixes":
        candidate[field] = [{"prefix": "/", "classification": "crawl-blocked-sensitive"}]
    else:
        candidate[field] = [
            {"prefix": "/", "upstream": "agent", "review_reason": "reviewed"}
        ]

    with pytest.raises(ValueError, match="prefix cannot be root"):
        validate_route_manifest_data(candidate)


def test_validate_route_manifest_rejects_non_plain_direct_containers():
    class ManifestDict(dict):
        pass

    class ManifestList(list):
        pass

    with pytest.raises(ValueError, match="plain JSON object"):
        validate_route_manifest_data(ManifestDict(valid_manifest()))

    candidate = valid_manifest()
    candidate["exact_routes"] = ManifestList(candidate["exact_routes"])
    with pytest.raises(ValueError, match="plain JSON array"):
        validate_route_manifest_data(candidate)
