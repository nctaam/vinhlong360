from __future__ import annotations

import pytest

from agent.control_plane.attestation import (
    ROLES,
    SCHEME_HMAC,
    SCHEME_UNSIGNED,
    KeyReference,
    build_attestation,
    evaluate_attestations,
    load_key_references,
    payload_digest,
    resolve_key,
    sign_attestation,
    verify_attestation,
)

DIGEST = "a" * 64
SIGNED_AT = "2026-09-02T00:00:00+00:00"


@pytest.fixture
def references(tmp_path, monkeypatch):
    """Provide one authorised key per role, with owner and CI held off-machine."""

    owner_key = tmp_path / "owner.key"
    owner_key.write_bytes(b"owner-key-material-0123456789abcdefghij")
    # Một runner Actions thật công bố CẢ MỘT BỘ định danh mạch lạc. Chỉ
    # `GITHUB_ACTIONS=true` thì shell nào cũng export được, nên nó không bao giờ
    # phân biệt được custody CI với một tiến trình local — đúng thứ mà
    # `ci-secret` sinh ra để khẳng định.
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "vinhlong360/vinhlong360")
    monkeypatch.setenv("GITHUB_RUN_ID", "1234567890")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setenv(
        "GITHUB_WORKFLOW_REF",
        "vinhlong360/vinhlong360/.github/workflows/ci.yml@refs/heads/main",
    )
    monkeypatch.setenv("TEST_RUNNER_KEY", "runner-key-material-0123456789abcdefghij")
    monkeypatch.setenv("TEST_COUNTERSIGN_KEY", "countersign-key-material-0123456789abcd")
    monkeypatch.setenv("TEST_CI_KEY", "ci-key-material-0123456789abcdefghijklmn")
    return {
        "runner-test": KeyReference("runner-test", "runner", "environment:TEST_RUNNER_KEY"),
        "owner-test": KeyReference("owner-test", "owner", f"offline-owner:{owner_key}"),
        "countersign-test": KeyReference("countersign-test", "countersign", "environment:TEST_COUNTERSIGN_KEY"),
        "ci-test": KeyReference("ci-test", "ci", "ci-secret:TEST_CI_KEY"),
    }


def _full_set(references, digest=DIGEST):
    return [
        build_attestation(
            role=reference.role,
            key_id=reference.key_id,
            custody=reference.custody,
            digest=digest,
            signed_at=SIGNED_AT,
            key=resolve_key(reference.custody),
        )
        for reference in references.values()
    ]


def test_a_complete_signed_set_verifies(references):
    ok, reasons = evaluate_attestations(_full_set(references), digest=DIGEST, references=references)
    assert (ok, reasons) == (True, ())


def test_an_absent_key_produces_an_unsigned_attestation_that_is_refused(references, monkeypatch):
    """A missing key must be recorded and refused, never silently skipped."""

    monkeypatch.delenv("TEST_RUNNER_KEY", raising=False)
    reference = references["runner-test"]
    attestation = build_attestation(
        role=reference.role, key_id=reference.key_id, custody=reference.custody,
        digest=DIGEST, signed_at=SIGNED_AT, key=resolve_key(reference.custody),
    )

    assert attestation["scheme"] == SCHEME_UNSIGNED
    assert attestation["signature"] == ""
    ok, reason = verify_attestation(attestation, digest=DIGEST, references=references)
    assert (ok, reason) == (False, "attestation-unsigned")


def test_verification_fails_closed_when_key_material_disappears(references, monkeypatch):
    """Losing the key must refuse the signature, not bypass the check."""

    attestations = _full_set(references)
    monkeypatch.delenv("TEST_RUNNER_KEY", raising=False)
    runner_attestation = next(item for item in attestations if item["role"] == "runner")

    ok, reason = verify_attestation(runner_attestation, digest=DIGEST, references=references)
    assert (ok, reason) == (False, "attestation-key-material-unavailable")


def test_a_signature_over_a_different_digest_is_refused(references):
    attestations = _full_set(references, digest="b" * 64)
    ok, reasons = evaluate_attestations(attestations, digest=DIGEST, references=references)

    assert not ok
    assert "attestation-payload-digest-mismatch" in reasons


def test_editing_a_signed_field_invalidates_the_signature(references):
    attestation = _full_set(references)[0]
    attestation["signed_at"] = "2026-09-03T00:00:00+00:00"

    ok, reason = verify_attestation(attestation, digest=DIGEST, references=references)
    assert (ok, reason) == (False, "attestation-signature-mismatch")


@pytest.mark.parametrize("role", ROLES)
def test_every_role_is_required(references, role):
    attestations = [item for item in _full_set(references) if item["role"] != role]
    ok, reasons = evaluate_attestations(attestations, digest=DIGEST, references=references)

    assert not ok
    assert f"attestation-role-missing:{role}" in reasons


def test_a_key_the_authority_never_authorised_is_refused(references):
    attestation = _full_set(references)[0]
    attestation["key_id"] = "invented-by-the-bundle"

    ok, reason = verify_attestation(attestation, digest=DIGEST, references=references)
    assert (ok, reason) == (False, "attestation-key-id-not-authorised")


def test_a_key_bound_to_another_role_is_refused(references):
    reference = references["runner-test"]
    attestation = build_attestation(
        role="owner", key_id=reference.key_id, custody=reference.custody,
        digest=DIGEST, signed_at=SIGNED_AT, key=resolve_key(reference.custody),
    )

    ok, reason = verify_attestation(attestation, digest=DIGEST, references=references)
    assert (ok, reason) == (False, "attestation-key-id-bound-to-another-role")


def test_owner_and_ci_custody_must_sit_outside_the_editable_checkout(references, monkeypatch):
    """A local key cannot establish that someone or something else acted."""

    monkeypatch.setenv("TEST_LOCAL_CI_KEY", "local-ci-key-material-0123456789abcdefgh")
    references["ci-test"] = KeyReference("ci-test", "ci", "environment:TEST_LOCAL_CI_KEY")
    ok, reasons = evaluate_attestations(_full_set(references), digest=DIGEST, references=references)

    assert not ok
    assert "attestation-custody-not-independent:ci" in reasons


def test_ci_custody_is_refused_outside_ci(references, monkeypatch):
    """A CI-custody key presented on a laptop is not CI custody."""

    monkeypatch.setenv("GITHUB_ACTIONS", "false")
    assert resolve_key("ci-secret:TEST_CI_KEY") is None


def test_resolve_key_dispatch_preserves_file_and_environment_custody(references, tmp_path, monkeypatch):
    key = tmp_path / "runner.key"
    key.write_bytes(b"runner-key-material-0123456789abcdefghij")
    assert resolve_key(f"file:{key}") == key.read_bytes()
    assert resolve_key("environment:TEST_RUNNER_KEY") == b"runner-key-material-0123456789abcdefghij"


def test_two_roles_may_not_share_one_key_identity(references):
    attestations = _full_set(references)
    runner_attestation = next(item for item in attestations if item["role"] == "runner")
    duplicate = dict(runner_attestation)
    duplicate["role"] = "owner"
    duplicate["signature"] = sign_attestation(duplicate, resolve_key(references["runner-test"].custody))
    attestations = [item for item in attestations if item["role"] != "owner"] + [duplicate]

    ok, reasons = evaluate_attestations(attestations, digest=DIGEST, references=references)
    assert not ok


def test_an_unsupported_scheme_is_refused_by_name(references):
    attestation = _full_set(references)[0]
    attestation["scheme"] = "rot13"

    ok, reason = verify_attestation(attestation, digest=DIGEST, references=references)
    assert (ok, reason) == (False, "attestation-scheme-unsupported")


def test_an_empty_attestation_list_is_refused(references):
    ok, reasons = evaluate_attestations([], digest=DIGEST, references=references)
    assert (ok, reasons) == (False, ("attestations-missing",))


def test_a_short_key_cannot_satisfy_a_signature(monkeypatch):
    """A two-character environment value must not count as key material."""

    monkeypatch.setenv("TEST_TINY_KEY", "x")
    assert resolve_key("environment:TEST_TINY_KEY") is None


def test_unknown_custody_schemes_resolve_to_nothing():
    assert resolve_key("carrier-pigeon:somewhere") is None
    assert resolve_key("environment") is None
    assert resolve_key("environment:") is None


def test_key_references_require_every_role():
    incomplete = [
        {"key_id": "a", "role": "runner", "custody": "environment:A"},
        {"key_id": "b", "role": "owner", "custody": "offline-owner:b.key"},
    ]
    assert load_key_references(incomplete) is None

    complete = incomplete + [
        {"key_id": "c", "role": "countersign", "custody": "environment:C"},
        {"key_id": "d", "role": "ci", "custody": "ci-secret:D"},
    ]
    assert load_key_references(complete) is not None


def test_key_references_reject_duplicate_and_malformed_entries():
    assert load_key_references([{"key_id": "a", "role": "runner"}]) is None
    assert load_key_references("not-a-list") is None
    assert load_key_references([]) is None


def test_payload_digest_is_order_independent_but_content_sensitive():
    assert payload_digest({"a": 1, "b": 2}) == payload_digest({"b": 2, "a": 1})
    assert payload_digest({"a": 1}) != payload_digest({"a": 2})


def test_a_signed_attestation_declares_the_hmac_scheme(references):
    attestation = _full_set(references)[0]
    assert attestation["scheme"] == SCHEME_HMAC
    assert len(attestation["signature"]) == 64


# --- Custody phải được KIỂM, không chỉ được KHAI (đo 2026-09-03) -------------
#
# `INDEPENDENT_CUSTODY` khai rằng `offline-owner` và `ci-secret` là hai lớp
# custody nằm NGOÀI checkout có thể sửa bundle. Trước đây cả hai chỉ là nhãn
# chuỗi: `offline-owner` đọc bằng `Path(reference)` trần (tương đối → phụ thuộc
# cwd, và nằm trong checkout cũng được chấp nhận), còn `ci-secret` chỉ cần
# `GITHUB_ACTIONS=true` — một chuỗi tự khai mà shell nào cũng export được.


def test_offline_owner_custody_refuses_a_relative_reference(tmp_path, monkeypatch):
    """Khoá owner tương đối là một FILE KHÁC NHAU tuỳ chỗ khởi động trình thông dịch."""
    key = tmp_path / "owner.key"
    key.write_bytes(b"owner-key-material-0123456789abcdefghij")
    monkeypatch.chdir(tmp_path)

    assert resolve_key("offline-owner:owner.key") is None
    # Cùng vật liệu đó, khai bằng đường dẫn tuyệt đối ngoài checkout, thì được.
    assert resolve_key(f"offline-owner:{key}") is not None


def test_offline_owner_custody_refuses_material_inside_the_checkout(tmp_path):
    """Khoá nằm CẠNH trình soạn thảo không thể chứng minh sự độc lập với nó."""
    from agent.control_plane.attestation import _REPO_ROOT

    inside = _REPO_ROOT / ".tmp-test-owner-inside.key"
    inside.write_bytes(b"owner-key-material-0123456789abcdefghij")
    try:
        assert resolve_key(f"offline-owner:{inside}") is None
    finally:
        inside.unlink()


def test_file_custody_resolves_relative_to_the_supplied_checkout_root(tmp_path):
    """Alternate checkouts must not resolve file custody against this module's tree."""

    alternate = tmp_path / "alternate-checkout"
    alternate.mkdir()
    key = alternate / "runner.key"
    key.write_bytes(b"alternate-root-key-material-0123456789")

    assert resolve_key("file:runner.key", root=alternate) == key.read_bytes()


def test_offline_owner_custody_uses_the_supplied_checkout_for_containment(tmp_path):
    """An alternate checkout's own files cannot satisfy offline-owner custody."""

    alternate = tmp_path / "alternate-checkout"
    alternate.mkdir()
    inside = alternate / "owner.key"
    inside.write_bytes(b"alternate-owner-key-material-0123456789")
    outside = tmp_path / "external-owner.key"
    outside.write_bytes(b"external-owner-key-material-0123456789")

    assert resolve_key(f"offline-owner:{inside}", root=alternate) is None
    assert resolve_key(f"offline-owner:{outside}", root=alternate) == outside.read_bytes()


def test_ci_custody_is_refused_when_only_the_boolean_flag_is_exported(monkeypatch):
    """Shell nào cũng export được GITHUB_ACTIONS=true; đó không phải custody CI.

    Bổ trợ cho test đã có về GITHUB_ACTIONS="false" — test này phủ chiều NGUY
    HIỂM và trước đây chưa được kiểm: "true" mà đằng sau không có gì.
    """
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("PROBE_CI_KEY", "attacker-chosen-material-0123456789abcdef")
    for name in (
        "GITHUB_REPOSITORY",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_ATTEMPT",
        "GITHUB_SHA",
        "GITHUB_WORKFLOW_REF",
    ):
        monkeypatch.delenv(name, raising=False)

    assert resolve_key("ci-secret:PROBE_CI_KEY") is None


@pytest.mark.parametrize(
    "dropped",
    [
        "GITHUB_REPOSITORY",
        "GITHUB_RUN_ID",
        "GITHUB_RUN_ATTEMPT",
        "GITHUB_SHA",
        "GITHUB_WORKFLOW_REF",
    ],
)
def test_ci_custody_requires_every_provenance_marker(monkeypatch, dropped):
    """Thiếu MỘT dấu hiệu cũng phải từ chối — coi vắng mặt là 'không áp dụng'
    sẽ mở lại lỗ hổng cho ai chỉ cần export ít biến hơn."""
    monkeypatch.setenv("PROBE_CI_KEY", "ci-key-material-0123456789abcdefghijklmn")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "vinhlong360/vinhlong360")
    monkeypatch.setenv("GITHUB_RUN_ID", "1234567890")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setenv(
        "GITHUB_WORKFLOW_REF",
        "vinhlong360/vinhlong360/.github/workflows/ci.yml@refs/heads/main",
    )
    assert resolve_key("ci-secret:PROBE_CI_KEY") is not None, "bộ đầy đủ phải giải được"

    monkeypatch.delenv(dropped)
    assert resolve_key("ci-secret:PROBE_CI_KEY") is None


def test_ci_custody_refuses_malformed_provenance(monkeypatch):
    """Giá trị sai ĐỊNH DẠNG cũng bị từ chối, không chỉ giá trị vắng mặt."""
    monkeypatch.setenv("PROBE_CI_KEY", "ci-key-material-0123456789abcdefghijklmn")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_REPOSITORY", "not-a-repo-slug")
    monkeypatch.setenv("GITHUB_RUN_ID", "not-a-number")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_SHA", "short")
    monkeypatch.setenv("GITHUB_WORKFLOW_REF", "nope")

    assert resolve_key("ci-secret:PROBE_CI_KEY") is None


def test_declared_owner_custody_is_absolute_and_outside_the_checkout():
    """Khai báo custody của owner trong authority phải TỰ NÓ đứng vững.

    Bản khai cũ là `offline-owner:secrets/pilot-owner-signing.key` — một đường
    dẫn TƯƠNG ĐỐI, giải theo thư mục làm việc của tiến trình, và trỏ vào NGAY
    TRONG checkout. Cả hai đều phá vỡ chính tính chất mà `offline-owner` sinh ra
    để khẳng định: vật liệu khoá không nằm cạnh trình soạn thảo có thể sửa
    bundle. Bất kỳ ai sửa được bundle cũng tạo được file 32 byte ở đó rồi đúc ra
    một chữ ký `owner` hợp lệ.

    Test đọc thẳng authority nên nếu ai đó khai lại đường dẫn tương đối thì đỏ.
    """
    import json
    from pathlib import Path, PurePosixPath, PureWindowsPath

    from agent.control_plane.attestation import _REPO_ROOT

    authority = json.loads(
        (_REPO_ROOT / "config" / "release-authority.json").read_text(encoding="utf-8")
    )
    keys = authority["pilot_acceptance"]["attestation_keys"]
    owner = next(k for k in keys if k["role"] == "owner")

    scheme, _, reference = owner["custody"].partition(":")
    assert scheme == "offline-owner", owner["custody"]

    # Tuyệt đối theo BẢN KHAI, không theo nền tảng đang chạy: đích triển khai là
    # Linux còn chỗ soạn thảo là Windows.
    assert (
        PurePosixPath(reference).is_absolute() or PureWindowsPath(reference).is_absolute()
    ), f"owner custody khai đường dẫn phụ thuộc cwd: {reference!r}"

    # Và phải nằm NGOÀI checkout — kể cả checkout production tại /opt/vinhlong360.
    assert not PurePosixPath(reference).is_relative_to(PurePosixPath("/opt/vinhlong360")), (
        f"khoá owner khai bên trong checkout production: {reference!r}"
    )
    resolved = Path(reference).resolve()
    assert _REPO_ROOT != resolved and _REPO_ROOT not in resolved.parents, (
        f"khoá owner khai bên trong checkout này: {reference!r}"
    )


def test_the_declared_owner_key_is_absent_here_so_the_gate_stays_closed():
    """Trên máy này khoá owner PHẢI không giải được.

    Đó là chủ ý của chủ dự án, và là một trong các lý do cổng đứng NO_GO. Test
    tồn tại để nếu có ai đó đặt khoá owner vào máy soạn thảo thì có chỗ đỏ lên —
    vì lúc đó nhãn "offline" thành lời nói dối.
    """
    import json

    from agent.control_plane.attestation import _REPO_ROOT

    authority = json.loads(
        (_REPO_ROOT / "config" / "release-authority.json").read_text(encoding="utf-8")
    )
    owner = next(
        k for k in authority["pilot_acceptance"]["attestation_keys"] if k["role"] == "owner"
    )
    assert resolve_key(owner["custody"]) is None
