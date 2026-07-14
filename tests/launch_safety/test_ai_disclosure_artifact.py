import json
import subprocess
from pathlib import Path, PurePosixPath

import pytest

from scripts.package_launch_release import CANONICAL_ARTIFACTS


REPO_ROOT = Path(__file__).resolve().parents[2]
DISCLOSURE_FILENAME = "ai-disclosure.json"
CANONICAL_DISCLOSURE_PATH = PurePosixPath("config") / DISCLOSURE_FILENAME
DISCLOSURE_PATH = REPO_ROOT / CANONICAL_DISCLOSURE_PATH
CANONICAL_ARTIFACT_PATHS = (
    PurePosixPath("config/launch-indexing-policy.json"),
    CANONICAL_DISCLOSURE_PATH,
)
GIT_ATTRIBUTES_PATH = REPO_ROOT / ".gitattributes"
EXPECTED_GIT_ATTRIBUTES_BYTES = (
    b"config/launch-indexing-policy.json text eol=lf\n"
    b"config/ai-disclosure.json text eol=lf\n"
)
EXPECTED_DISCLOSURE_BYTES = (
    "{\n"
    '  "schema_version": 1,\n'
    '  "revision": "ai-disclosure-v1",\n'
    '  "entity_ai": {\n'
    '    "short_label": "Minh họa AI",\n'
    '    "full_disclosure": "Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ.",\n'
    '    "accessible_description_key": "entity-ai-full"\n'
    "  },\n"
    '  "placeholder": {\n'
    '    "short_label": null,\n'
    '    "full_disclosure": "Minh họa đồ họa — chưa có ảnh riêng cho địa điểm.",\n'
    '    "accessible_description_key": "entity-placeholder-full"\n'
    "  },\n"
    '  "ugc_photo": {\n'
    '    "short_label": "Ảnh người dùng",\n'
    '    "full_disclosure": "Ảnh do người dùng cung cấp.",\n'
    '    "accessible_description_key": "ugc-photo-full"\n'
    "  },\n"
    '  "forbidden_entity_image_claims": [\n'
    '    "ảnh thật",\n'
    '    "real photo",\n'
    '    "documentary photo",\n'
    '    "on-site photo",\n'
    '    "ảnh chụp tại chỗ"\n'
    "  ]\n"
    "}\n"
).encode("utf-8")
DISCLOSURE_FIELDS = {
    "short_label",
    "full_disclosure",
    "accessible_description_key",
}
EXPECTED_DISCLOSURE = {
    "schema_version": 1,
    "revision": "ai-disclosure-v1",
    "entity_ai": {
        "short_label": "Minh họa AI",
        "full_disclosure": "Ảnh minh họa do AI dựng — không phải ảnh chụp tại chỗ.",
        "accessible_description_key": "entity-ai-full",
    },
    "placeholder": {
        "short_label": None,
        "full_disclosure": "Minh họa đồ họa — chưa có ảnh riêng cho địa điểm.",
        "accessible_description_key": "entity-placeholder-full",
    },
    "ugc_photo": {
        "short_label": "Ảnh người dùng",
        "full_disclosure": "Ảnh do người dùng cung cấp.",
        "accessible_description_key": "ugc-photo-full",
    },
    "forbidden_entity_image_claims": [
        "ảnh thật",
        "real photo",
        "documentary photo",
        "on-site photo",
        "ảnh chụp tại chỗ",
    ],
}


def _reject_duplicate_keys(pairs):
    parsed = {}
    for key, value in pairs:
        if key in parsed:
            raise ValueError(f"duplicate JSON key: {key}")
        parsed[key] = value
    return parsed


def _load_disclosure():
    return json.loads(
        DISCLOSURE_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )


def _assert_canonical_disclosure_bytes(path: Path) -> None:
    assert path.read_bytes() == EXPECTED_DISCLOSURE_BYTES


def _find_noncanonical_ai_disclosure_paths(
    paths: list[PurePosixPath],
) -> list[PurePosixPath]:
    return sorted(
        (
            path
            for path in paths
            if path.name.casefold() == DISCLOSURE_FILENAME.casefold()
            and path.as_posix() != CANONICAL_DISCLOSURE_PATH.as_posix()
        ),
        key=PurePosixPath.as_posix,
    )


def _run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        pytest.fail("git is required to verify canonical artifact contracts")
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        pytest.fail(
            f"git {' '.join(args)} failed with exit {result.returncode}: {stderr}"
        )
    return result


def _git_tracked_paths() -> list[PurePosixPath]:
    result = _run_git(REPO_ROOT, "ls-files", "-z")
    return [
        PurePosixPath(raw_path.decode("utf-8"))
        for raw_path in result.stdout.split(b"\0")
        if raw_path
    ]


def _git_text_eol_attributes(
    repo_root: Path, paths: tuple[PurePosixPath, ...]
) -> dict[tuple[PurePosixPath, str], str]:
    result = _run_git(
        repo_root,
        "check-attr",
        "-z",
        "text",
        "eol",
        "--",
        *(path.as_posix() for path in paths),
    )
    fields = [field for field in result.stdout.split(b"\0") if field]
    assert len(fields) % 3 == 0
    return {
        (
            PurePosixPath(fields[index].decode("utf-8")),
            fields[index + 1].decode("ascii"),
        ): fields[index + 2].decode("ascii")
        for index in range(0, len(fields), 3)
    }


def test_ai_disclosure_bytes_match_canonical_utf8_artifact():
    _assert_canonical_disclosure_bytes(DISCLOSURE_PATH)


def test_canonical_artifacts_have_exact_lf_git_attributes():
    expected_attributes = {
        (path, attribute): value
        for path in CANONICAL_ARTIFACT_PATHS
        for attribute, value in (("text", "set"), ("eol", "lf"))
    }

    assert (
        _git_text_eol_attributes(REPO_ROOT, CANONICAL_ARTIFACT_PATHS)
        == expected_attributes
    )
    assert GIT_ATTRIBUTES_PATH.read_text(encoding="ascii").splitlines() == (
        EXPECTED_GIT_ATTRIBUTES_BYTES.decode("ascii").splitlines()
    )


def test_autocrlf_checkout_index_preserves_canonical_artifact_bytes(tmp_path: Path):
    isolated_repo = tmp_path / "repo"
    fresh_checkout = tmp_path / "fresh"
    isolated_repo.mkdir()
    fresh_checkout.mkdir()
    _run_git(isolated_repo, "init", "--quiet")
    _run_git(isolated_repo, "config", "core.autocrlf", "true")
    (isolated_repo / ".gitattributes").write_bytes(EXPECTED_GIT_ATTRIBUTES_BYTES)

    canonical_bytes = {}
    for relative_path in CANONICAL_ARTIFACT_PATHS:
        raw = (REPO_ROOT / relative_path).read_bytes()
        assert raw.endswith(b"\n")
        assert b"\r\n" not in raw
        canonical_bytes[relative_path] = raw
        target = isolated_repo / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)

    _run_git(
        isolated_repo,
        "add",
        "--",
        ".gitattributes",
        *(path.as_posix() for path in CANONICAL_ARTIFACT_PATHS),
    )
    _run_git(
        isolated_repo,
        "checkout-index",
        "--all",
        "--force",
        f"--prefix={fresh_checkout.as_posix()}/",
    )

    for relative_path, expected_bytes in canonical_bytes.items():
        checked_out_bytes = (fresh_checkout / relative_path).read_bytes()
        assert checked_out_bytes == expected_bytes
        assert b"\r\n" not in checked_out_bytes


@pytest.mark.parametrize(
    "mutated_bytes",
    [
        json.dumps(
            EXPECTED_DISCLOSURE, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        + b"\n",
        EXPECTED_DISCLOSURE_BYTES.replace(
            b'  "schema_version": 1,\n  "revision": "ai-disclosure-v1",\n',
            b'  "revision": "ai-disclosure-v1",\n  "schema_version": 1,\n',
        ),
        EXPECTED_DISCLOSURE_BYTES.replace(b"\n", b"\r\n"),
        EXPECTED_DISCLOSURE_BYTES.removesuffix(b"\n"),
        b"\xef\xbb\xbf" + EXPECTED_DISCLOSURE_BYTES,
        json.dumps(EXPECTED_DISCLOSURE, ensure_ascii=True, indent=2).encode("utf-8")
        + b"\n",
    ],
    ids=["minified", "reordered", "crlf", "no-final-lf", "bom", "unicode-escapes"],
)
def test_canonical_byte_guard_rejects_serialization_drift(
    tmp_path: Path, mutated_bytes: bytes
):
    mutated_path = tmp_path / "ai-disclosure.json"
    mutated_path.write_bytes(mutated_bytes)

    with pytest.raises(AssertionError):
        _assert_canonical_disclosure_bytes(mutated_path)


def test_ai_disclosure_contains_exact_reviewed_schema_and_copy():
    disclosure = _load_disclosure()

    assert type(disclosure) is dict
    assert set(disclosure) == {
        "schema_version",
        "revision",
        "entity_ai",
        "placeholder",
        "ugc_photo",
        "forbidden_entity_image_claims",
    }
    assert disclosure == EXPECTED_DISCLOSURE
    assert type(disclosure["schema_version"]) is int
    assert disclosure["schema_version"] == 1
    assert disclosure["revision"] == "ai-disclosure-v1"

    for section_name in ("entity_ai", "placeholder", "ugc_photo"):
        section = disclosure[section_name]
        assert type(section) is dict
        assert set(section) == DISCLOSURE_FIELDS
        assert type(section["full_disclosure"]) is str
        assert type(section["accessible_description_key"]) is str

    assert type(disclosure["entity_ai"]["short_label"]) is str
    assert disclosure["placeholder"]["short_label"] is None
    assert type(disclosure["ugc_photo"]["short_label"]) is str

    for field in DISCLOSURE_FIELDS:
        ugc_value = disclosure["ugc_photo"][field]
        assert ugc_value != disclosure["entity_ai"][field]
        assert ugc_value != disclosure["placeholder"][field]

    forbidden_claims = disclosure["forbidden_entity_image_claims"]
    assert type(forbidden_claims) is list
    assert forbidden_claims == [
        "ảnh thật",
        "real photo",
        "documentary photo",
        "on-site photo",
        "ảnh chụp tại chỗ",
    ]
    assert all(type(claim) is str and claim for claim in forbidden_claims)
    assert len(forbidden_claims) == len(set(forbidden_claims))


def test_ai_disclosure_is_registered_as_a_canonical_release_artifact():
    assert DISCLOSURE_FILENAME in CANONICAL_ARTIFACTS


@pytest.mark.parametrize(
    ("paths", "expected_noncanonical"),
    [
        ([CANONICAL_DISCLOSURE_PATH], []),
        (
            [PurePosixPath("config/AI-Disclosure.json")],
            [PurePosixPath("config/AI-Disclosure.json")],
        ),
        (
            [
                CANONICAL_DISCLOSURE_PATH,
                PurePosixPath("web-nuxt/AI-DISCLOSURE.JSON"),
            ],
            [PurePosixPath("web-nuxt/AI-DISCLOSURE.JSON")],
        ),
    ],
    ids=["exact-canonical", "wrong-case-canonical", "casefold-duplicate"],
)
def test_ai_disclosure_layout_guard_is_case_sensitive_and_excludes_only_canonical(
    paths: list[PurePosixPath], expected_noncanonical: list[PurePosixPath]
):
    assert _find_noncanonical_ai_disclosure_paths(paths) == expected_noncanonical


def test_tracked_sources_contain_exactly_one_canonical_ai_disclosure_path():
    tracked_matches = [
        path
        for path in _git_tracked_paths()
        if path.name.casefold() == DISCLOSURE_FILENAME.casefold()
    ]

    assert tracked_matches == [CANONICAL_DISCLOSURE_PATH]
