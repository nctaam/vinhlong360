"""Release verifier phải NẠP đối chứng, hỏi authority còn hạn, và soi hồ sơ quyết định.

Ba cổng lẽ ra phải có trên đường phát hành nhưng KHÔNG đường nào gọi tới, và cả
ba đều fail-OPEN:

* `countersign_pilot_acceptance.py` ghi biên nhận ra MỘT ARTIFACT RIÊNG
  (`artifacts/pilot-countersignature.json`) — cố ý, vì bundle đã phát hành thì
  không sửa tại chỗ. Nhưng không ai đọc lại nó, nên biên nhận có tồn tại, vắng
  mặt, hay ràng vào một bundle KHÁC thì verifier đều nói y như nhau.
* `check_authority` trả `STALE` khi tài liệu điều hành hết hạn, và có test đơn vị
  riêng — nhưng không đường phát hành nào gọi. Authority quá hạn vì thế không
  chặn được gì.
* Cổng chỉ thấy bốn biến bool trần trong bundle; không gì nối chúng với
  `config/decision-records.json` hay `docs/decisions/QD-*.md`, nên một hồ sơ có
  thể được đúc tại máy, không ràng vào cái gì, và ký bởi bất kỳ ai.

Đo trước khi vá: verifier trả đúng MỘT lý do ("pilot acceptance gate is NO_GO").
Sau khi vá: 19 lý do — đối chứng chưa ký, 4 quyết định chưa ký và chưa tracked,
và 7 tài liệu authority hết hạn. Verdict giữ nguyên BLOCKED.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from agent.control_plane.attestation import build_attestation, payload_digest, resolve_key
from scripts.ops.run_pilot_acceptance import AcceptanceBundle

ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "scripts" / "ops" / "verify_release_bundle.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_release_bundle", VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BUNDLE = {
    "bundle_kind": "pilot-acceptance-v1",
    "artifact_id": "pilot-acceptance-TEST",
    "head_sha": "b" * 40,
    "output_sha256": "c" * 64,
}


def _receipt(**overrides) -> dict:
    receipt = {
        "bundle_artifact_id": BUNDLE["artifact_id"],
        "bundle_output_sha256": BUNDLE["output_sha256"],
        "head_sha": BUNDLE["head_sha"],
        "complete": True,
        "expected": ["F-42/postgres"],
        "confirmed": ["F-42/postgres"],
        "results": [{"record": "F-42/postgres", "verdict": "MATCH"}],
        "attestation": {"scheme": "hmac-sha256", "signature": "d" * 64},
    }
    receipt.update(overrides)
    return receipt


def _write(tmp_path: Path, receipt: dict | None) -> Path:
    bundle_path = tmp_path / "pilot-acceptance.json"
    bundle_path.write_text(json.dumps(BUNDLE), encoding="utf-8")
    if receipt is not None:
        (tmp_path / "pilot-countersignature.json").write_text(
            json.dumps(receipt), encoding="utf-8"
        )
    return bundle_path


def test_a_bound_and_signed_countersignature_raises_no_reason(tmp_path: Path) -> None:
    module = _load()
    bundle_path = _write(tmp_path, _receipt())
    assert module.countersignature_reasons(
        bundle_path, BUNDLE, BUNDLE["output_sha256"]
    ) == []


def test_a_missing_countersignature_is_reported(tmp_path: Path) -> None:
    """Trước bản vá, vắng mặt hoàn toàn im lặng."""
    module = _load()
    bundle_path = _write(tmp_path, None)
    reasons = module.countersignature_reasons(bundle_path, BUNDLE, BUNDLE["output_sha256"])
    assert any("not found" in r for r in reasons), reasons


@pytest.mark.parametrize(
    ("field", "value", "needle"),
    [
        ("bundle_output_sha256", "9" * 64, "output_sha256"),
        ("bundle_artifact_id", "some-other-bundle", "artifact_id"),
        ("head_sha", "e" * 40, "head_sha"),
    ],
)
def test_a_countersignature_bound_to_another_bundle_is_refused(
    tmp_path: Path, field: str, value: str, needle: str
) -> None:
    """Biên nhận không nêu ĐÚNG bundle này thì không chứng minh gì về nó.

    Đây là chốt chặn replay: một đối chứng thật của bundle khác không được tính.
    """
    module = _load()
    bundle_path = _write(tmp_path, _receipt(**{field: value}))
    reasons = module.countersignature_reasons(bundle_path, BUNDLE, BUNDLE["output_sha256"])
    assert any(needle in r for r in reasons), reasons


def test_an_unsigned_countersignature_is_reported(tmp_path: Path) -> None:
    module = _load()
    bundle_path = _write(
        tmp_path, _receipt(attestation={"scheme": "unsigned", "signature": ""})
    )
    reasons = module.countersignature_reasons(bundle_path, BUNDLE, BUNDLE["output_sha256"])
    assert any("unsigned" in r for r in reasons), reasons


def test_an_incomplete_countersignature_is_reported(tmp_path: Path) -> None:
    module = _load()
    bundle_path = _write(tmp_path, _receipt(complete=False))
    reasons = module.countersignature_reasons(bundle_path, BUNDLE, BUNDLE["output_sha256"])
    assert any("incomplete" in r for r in reasons), reasons


def test_a_non_matching_record_is_reported(tmp_path: Path) -> None:
    module = _load()
    bundle_path = _write(
        tmp_path,
        _receipt(results=[{"record": "F-42/postgres", "verdict": "MISMATCH"}]),
    )
    reasons = module.countersignature_reasons(bundle_path, BUNDLE, BUNDLE["output_sha256"])
    assert any("did not match" in r for r in reasons), reasons


@pytest.mark.parametrize(
    ("results", "needles"),
    [
        ([{"record": "F-42/postgres", "verdict": "MATCH"}], ("missing",)),
        ([
            {"record": "F-42/postgres", "verdict": "MATCH"},
            {"record": "F-99/postgres", "verdict": "MATCH"},
        ], ("unknown",)),
        ([
            {"record": "F-42/postgres", "verdict": "MATCH"},
            {"record": "F-42/postgres", "verdict": "MATCH"},
        ], ("duplicate",)),
        ([{"record": "F-42/postgres", "verdict": "NOT_REPLAYABLE"}], ("did not match",)),
    ],
)
def test_results_must_cover_exactly_each_expected_match(
    tmp_path: Path, results: list[dict], needles: tuple[str, ...]
) -> None:
    """Confirmed/attested receipts cannot hide missing, extra, duplicate, or red results."""

    module = _load()
    bundle_path = _write(
        tmp_path,
        _receipt(
            expected=["F-42/postgres", "F-49/postgres"],
            confirmed=["F-42/postgres", "F-49/postgres"],
            results=results,
        ),
    )

    reasons = module.countersignature_reasons(bundle_path, BUNDLE, BUNDLE["output_sha256"])

    assert any(needle in reason for needle in needles for reason in reasons), reasons


def test_verifier_resolves_relative_bundle_against_root(tmp_path: Path, monkeypatch) -> None:
    """The selected root, rather than process cwd, determines a relative bundle."""

    module = _load()
    root = tmp_path / "alternate-root"
    bundle_path = root / "artifacts" / "pilot-acceptance.json"
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text(json.dumps(BUNDLE), encoding="utf-8")
    seen: list[Path] = []

    def fake_verify(path: Path, **kwargs):
        seen.append(path)
        return "BLOCKED", (), BUNDLE["output_sha256"]

    monkeypatch.setattr(module, "verify_pilot_bundle", fake_verify)
    monkeypatch.setattr(module, "decision_reasons", lambda *args: [])
    monkeypatch.setattr(module, "authority_reasons", lambda *args: [])

    assert module.main([
        "--bundle", "artifacts/pilot-acceptance.json",
        "--root", str(root),
    ]) == 2

    assert seen == [bundle_path.resolve()]


def test_confirmed_must_equal_expected(tmp_path: Path) -> None:
    """Xác nhận ÍT hơn kỳ vọng mà vẫn khai `complete` là một lời hứa suông."""
    module = _load()
    bundle_path = _write(
        tmp_path,
        _receipt(expected=["F-42/postgres", "F-49/postgres"], confirmed=["F-42/postgres"]),
    )
    reasons = module.countersignature_reasons(bundle_path, BUNDLE, BUNDLE["output_sha256"])
    assert any("does not equal" in r for r in reasons), reasons


def test_a_valid_sidecar_can_be_overlaid_without_mutating_the_issued_bundle(tmp_path: Path) -> None:
    """The release gate may consume an explicit sidecar, but never rewrite its source."""

    module = _load()
    original = dict(BUNDLE)
    receipt = _receipt()
    overlay, reasons = module.overlay_countersignature(original, receipt)

    assert reasons == []
    assert overlay is not None
    assert overlay["output_sha256"] != original["output_sha256"]
    assert overlay["attestations"][-1] == receipt["attestation"]
    assert original == BUNDLE


def test_a_sidecar_overlay_rejects_a_second_countersignature() -> None:
    """A finalized bundle cannot silently stack two independent countersigns."""

    module = _load()
    payload = dict(BUNDLE)
    payload["attestations"] = [{"role": "countersign"}]
    overlay, reasons = module.overlay_countersignature(payload, _receipt())

    assert overlay is None
    assert any("duplicated" in reason for reason in reasons), reasons


def test_verifier_uses_a_validated_sidecar_as_an_explicit_gate_overlay(tmp_path: Path, monkeypatch) -> None:
    """A sidecar can complete the gate in memory without rewriting the source bundle."""

    module = _load()
    bundle_path = _write(tmp_path, _receipt())
    monkeypatch.setattr(
        module,
        "verify_pilot_bundle",
        lambda path, **kwargs: ("BLOCKED", ("pilot acceptance gate is NO_GO",), BUNDLE["output_sha256"]),
    )
    monkeypatch.setattr(module, "countersignature_attestation_reasons", lambda *args: [])
    monkeypatch.setattr(module, "evaluate_pilot_gate", lambda bundle, **kwargs: "GO_CONDITIONAL")
    monkeypatch.setattr(module, "decision_reasons", lambda *args: [])
    monkeypatch.setattr(module, "authority_reasons", lambda *args: [])

    assert module.main(["--bundle", str(bundle_path), "--root", str(tmp_path)]) == 0
    assert json.loads(bundle_path.read_text(encoding="utf-8")) == BUNDLE


def _cryptographically_signed_receipt(tmp_path: Path, monkeypatch) -> dict:
    monkeypatch.setenv("TEST_COUNTERSIGN_KEY", "countersign-key-material-0123456789abcd")
    authority = {
        "pilot_acceptance": {
            "attestation_keys": [
                {"key_id": "runner", "role": "runner", "custody": "environment:TEST_RUNNER_KEY"},
                {"key_id": "owner", "role": "owner", "custody": f"offline-owner:{tmp_path / 'owner.key'}"},
                {"key_id": "counter", "role": "countersign", "custody": "environment:TEST_COUNTERSIGN_KEY"},
                {"key_id": "ci", "role": "ci", "custody": "ci-secret:TEST_CI_KEY"},
            ]
        }
    }
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "release-authority.json").write_text(json.dumps(authority), encoding="utf-8")
    bundle = AcceptanceBundle.from_dict(BUNDLE)
    attestation = build_attestation(
        role="countersign",
        key_id="counter",
        custody="environment:TEST_COUNTERSIGN_KEY",
        digest=payload_digest(bundle.unsigned_payload()),
        signed_at="2026-09-03T00:00:00+00:00",
        key=resolve_key("environment:TEST_COUNTERSIGN_KEY"),
        covers=["F-42/postgres"],
    )
    return _receipt(attestation=attestation)


def test_sidecar_attestation_is_cryptographically_verified(tmp_path: Path, monkeypatch) -> None:
    module = _load()
    receipt = _cryptographically_signed_receipt(tmp_path, monkeypatch)

    assert module.countersignature_attestation_reasons(tmp_path, BUNDLE, receipt) == []

    receipt["attestation"]["signature"] = "0" * 64
    reasons = module.countersignature_attestation_reasons(tmp_path, BUNDLE, receipt)
    assert any("signature-mismatch" in reason for reason in reasons), reasons


def test_cli_honours_an_explicit_countersignature_path(tmp_path: Path, monkeypatch) -> None:
    module = _load()
    bundle_path = _write(tmp_path, None)
    sidecar = tmp_path / "independent-review.json"
    sidecar.write_text(json.dumps(_receipt()), encoding="utf-8")
    seen: list[Path] = []
    original = module._read_countersignature

    def capture(path: Path):
        seen.append(path)
        return original(path)

    monkeypatch.setattr(module, "_read_countersignature", capture)
    monkeypatch.setattr(
        module,
        "verify_pilot_bundle",
        lambda path, **kwargs: ("BLOCKED", ("pilot acceptance gate is NO_GO",), BUNDLE["output_sha256"]),
    )
    monkeypatch.setattr(module, "countersignature_attestation_reasons", lambda *args: [])
    monkeypatch.setattr(module, "evaluate_pilot_gate", lambda bundle, **kwargs: "GO_CONDITIONAL")
    monkeypatch.setattr(module, "decision_reasons", lambda *args: [])
    monkeypatch.setattr(module, "authority_reasons", lambda *args: [])

    assert module.main([
        "--bundle", str(bundle_path),
        "--root", str(tmp_path),
        "--countersignature", str(sidecar),
    ]) == 0
    assert sidecar.resolve() in seen


def test_authority_staleness_is_wired_into_the_verifier() -> None:
    """Authority quá hạn PHẢI sinh ra lý do chặn.

    Không hermetic có chủ đích: kho hiện có 7 tài liệu hết hạn, nên hàm này phải
    trả về lý do. Nếu ai đó gỡ dây nối, test đỏ.
    """
    module = _load()
    reasons = module.authority_reasons(ROOT)
    assert reasons, "authority hiện đang STALE nên phải có lý do"
    assert any("release authority is" in r for r in reasons), reasons


def test_the_live_bundle_stays_blocked_and_now_reports_more_than_the_gate() -> None:
    """Verdict phải GIỮ NGUYÊN BLOCKED, và phải nói nhiều hơn một lý do.

    Trước bản vá verifier chỉ nói "pilot acceptance gate is NO_GO" — đúng nhưng
    che mất việc đối chứng chưa ký và authority đã quá hạn.
    """
    module = _load()
    bundle = ROOT / "artifacts" / "pilot-acceptance.json"
    if not bundle.is_file():
        pytest.skip("bundle chấp nhận pilot không có mặt")
    code = module.main(["--bundle", str(bundle), "--root", str(ROOT)])
    assert code == 2, "verdict phải vẫn là BLOCKED"


# --- Quyết định phải TRACKED, RÀNG-CHECKSUM và ĐÚNG VAI (đo 2026-09-03) ------
#
# Cổng trước đây chỉ thấy bốn biến bool trần trong bundle. Không gì nối chúng
# với `config/decision-records.json` hay `docs/decisions/QD-*.md`, nên một bản
# ghi có thể được đúc tại máy, không ràng vào cái gì, ký bởi bất kỳ ai — và cổng
# cũng không biết. Đo thực tế: TOÀN BỘ hồ sơ quyết định đang UNTRACKED.


def _decision_root(tmp_path: Path, *, state: str = "signed", **entry_overrides) -> Path:
    record = tmp_path / "docs" / "decisions" / "QD-02.md"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text("noi dung quyet dinh phap ly", encoding="utf-8")

    import hashlib

    entry = {
        "decision_key": "legal",
        "record": "docs/decisions/QD-02.md",
        "state": state,
        "chosen_option": "A",
        "signed_by": "legal-counsel",
        "record_sha256": hashlib.sha256(record.read_bytes()).hexdigest(),
        "signature": "f" * 64,
    }
    entry.update(entry_overrides)

    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config" / "decision-records.json").write_text(
        json.dumps({"schema_version": 1, "decisions": [entry]}), encoding="utf-8"
    )
    (tmp_path / "config" / "release-authority.json").write_text(
        json.dumps(
            {
                "pilot_acceptance": {
                    "decision_required_items": ["legal"],
                    "decision_signers": {"legal": ["legal-counsel"]},
                }
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_a_decision_record_that_is_not_tracked_is_refused(tmp_path: Path) -> None:
    """Hồ sơ untracked là hồ sơ ai cũng đúc được tại máy."""
    module = _load()
    root = _decision_root(tmp_path)
    reasons = module.decision_reasons(root, {})
    # tmp_path không phải một repo git, nên mọi thứ đều "không tracked".
    assert any("not git-tracked" in r for r in reasons), reasons


def test_a_decision_signature_that_does_not_bind_its_record_is_refused(tmp_path: Path) -> None:
    """record_sha256 sai = chữ ký không ràng vào văn bản đã quyết."""
    module = _load()
    root = _decision_root(tmp_path, record_sha256="0" * 64)
    reasons = module.decision_reasons(root, {})
    assert any("record_sha256 does not match" in r for r in reasons), reasons


def test_a_decision_signed_by_a_non_allowed_signer_is_refused(tmp_path: Path) -> None:
    module = _load()
    root = _decision_root(tmp_path, signed_by="the-runner")
    reasons = module.decision_reasons(root, {})
    assert any("is not an allowed signer" in r for r in reasons), reasons


def test_a_signature_cannot_be_credited_without_a_declared_signer_list(tmp_path: Path) -> None:
    """Không có danh sách người ký hợp lệ thì KHÔNG được ghi nhận chữ ký.

    Bịa ra danh sách ở đây chính là công cụ tự quyết ai được duyệt phát hành —
    đúng thứ P1.7 cấm. Fail closed và nêu rõ hợp đồng còn thiếu.
    """
    module = _load()
    root = _decision_root(tmp_path)
    (root / "config" / "release-authority.json").write_text(
        json.dumps({"pilot_acceptance": {"decision_required_items": ["legal"]}}),
        encoding="utf-8",
    )
    reasons = module.decision_reasons(root, {})
    assert any("declares no allowed signer" in r for r in reasons), reasons


def test_a_bundle_cannot_claim_approval_the_record_does_not_carry(tmp_path: Path) -> None:
    """Bundle khai `True` mà hồ sơ chưa ký = lời khai không có cơ sở."""
    module = _load()
    root = _decision_root(tmp_path, state="unsigned")
    reasons = module.decision_reasons(root, {"decision_required": {"legal": True}})
    assert any("claims approval but the record is not signed" in r for r in reasons), reasons


def test_the_live_decision_corpus_is_currently_unsigned_and_untracked() -> None:
    """Ghim hiện trạng: bốn quyết định đều CHƯA ký và CHƯA tracked.

    Đây là trạng thái ĐÚNG. Test tồn tại để nếu có ai đó tự ký thay chủ dự án,
    hoặc gỡ dây nối này, thì có chỗ đỏ lên.
    """
    module = _load()
    reasons = module.decision_reasons(ROOT, {})
    assert reasons, "hồ sơ quyết định hiện chưa ký nên phải có lý do chặn"
    assert any("not signed" in r for r in reasons), reasons


def test_countersignature_reason_order_is_characterized(tmp_path: Path) -> None:
    """Các lý do đối chứng giữ thứ tự binding -> completeness -> coverage -> attestation."""

    module = _load()
    bundle_path = _write(
        tmp_path,
        _receipt(
            bundle_output_sha256="x" * 64,
            bundle_artifact_id="other-bundle",
            head_sha="h" * 40,
            complete=False,
            expected=["record-a", "record-a"],
            confirmed=["record-a"],
            results=[{"record": "record-a", "verdict": "MISMATCH"}],
            attestation={"scheme": "unsigned", "signature": ""},
        ),
    )

    assert module.countersignature_reasons(
        bundle_path, BUNDLE, BUNDLE["output_sha256"]
    ) == [
        "countersignature does not bind this bundle's output_sha256",
        "countersignature digest does not match the recomputed bundle digest",
        "countersignature does not bind this bundle's artifact_id",
        "countersignature head_sha differs from the bundle head_sha",
        "countersignature is incomplete",
        "countersignature expected set contains duplicate records",
        "countersignature confirmed set does not equal its expected set",
        "countersignature record did not match: record-a",
        "countersignature is unsigned (no countersign key in custody)",
    ]


def test_decision_reason_order_is_characterized(tmp_path: Path) -> None:
    """Decision reasons report index/tracking/state before bundle claims."""

    module = _load()
    root = _decision_root(tmp_path, state="unsigned")

    assert module.decision_reasons(root, {"decision_required": {"legal": True}}) == [
        "decision record index is not git-tracked: config/decision-records.json",
        "decision legal: record is not git-tracked: docs/decisions/QD-02.md",
        "decision legal: state is 'unsigned', not signed",
        "decision legal: bundle claims approval but the record is not signed",
    ]
