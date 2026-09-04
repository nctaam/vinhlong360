"""Keyed attestations for release evidence bundles.

A bundle of SHA-256 checksums proves only that its own fields are mutually
consistent: every digest in it is a keyless function of text the author typed,
so anyone holding the checkout can recompute the whole chain.  This module adds
the missing half — a signature over the canonical unsigned payload, keyed by
material the bundle does not contain.

Four roles sign, and they answer different questions:

``runner``
    Which process emitted this bundle.
``owner``
    Which human accepted it.  Never mintable by an automated agent.
``countersign``
    An independent re-execution observed the same outcomes.  This is the only
    role that tests the claim rather than the claimant, and the only one that
    needs no secret to be meaningful, because it carries the re-observed
    fingerprints as data.
``ci``
    The bundle was produced on hardware the local editor does not control.

Honest limit, stated here because it must not be lost in the runbook: HMAC is
symmetric, so verify capability equals forge capability.  A key readable on the
same machine as the text editor raises the bar and records intent; it is not a
trust anchor against that editor.  Only ``countersign`` (re-execution) and
``ci`` (custody elsewhere) reach further, which is why custody is recorded per
key and why independence is reported rather than assumed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
from typing import Any

# Canonical anchor for custody references.  Derived from this module's own
# location so it is identical no matter which directory the interpreter was
# started from, and independent of any particular checkout's cwd.
_REPO_ROOT = Path(__file__).resolve().parents[2]

ATTESTATION_VERSION = 1
SCHEME_UNSIGNED = "unsigned"
SCHEME_HMAC = "hmac-sha256"
SUPPORTED_SCHEMES = frozenset({SCHEME_HMAC})
ROLES = ("runner", "owner", "countersign", "ci")
# Custody classes whose key material does not sit beside the text editor that
# could rewrite the bundle.  Only these establish independence.
INDEPENDENT_CUSTODY = frozenset({"ci-secret", "offline-owner"})
CUSTODY_SCHEMES = ("environment", "file", "ci-secret", "offline-owner")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_HEX_SIGNATURE = re.compile(r"^[0-9a-f]{64}$")
_MINIMUM_KEY_BYTES = 32

_ATTESTATION_FIELDS = (
    "version",
    "role",
    "scheme",
    "key_id",
    "custody",
    "signed_at",
    "payload_sha256",
    "covers",
    "provenance",
)


@dataclass(frozen=True)
class KeyReference:
    """One authorised signing identity declared by the release authority."""

    key_id: str
    role: str
    custody: str

    @property
    def custody_scheme(self) -> str:
        """Return the custody scheme portion, e.g. ``environment`` or ``ci-secret``."""

        return self.custody.split(":", 1)[0]

    @property
    def is_independent(self) -> bool:
        """Report whether this key lives outside the editable checkout."""

        return self.custody_scheme in INDEPENDENT_CUSTODY


def canonical_json(payload: Any) -> str:
    """Serialise one payload the single way every digest in this system uses."""

    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def payload_digest(payload: Any) -> str:
    """Return the SHA-256 of a canonically serialised payload."""

    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _resolved_offline_owner_path(reference: str, *, root: Path | None = None) -> Path | None:
    """Resolve an ``offline-owner`` reference, or ``None`` when it cannot hold.

    ``offline-owner`` is one of the two custody classes that CLAIM independence
    from the editable checkout (see ``INDEPENDENT_CUSTODY``).  That claim was
    never checked: the reference was read with a bare ``Path(reference)``, so a
    relative declaration resolved against the process working directory, and a
    key sitting inside the checkout satisfied it just as well as one outside.
    Both are refused here so the label cannot outrun the fact.
    """

    # "Absolute" is asked of the DECLARATION, not of the host running it.  The
    # deployment target is Linux (the checkout lives at /opt/vinhlong360) while
    # editing happens on Windows, and `Path("/etc/...").is_absolute()` is False
    # on Windows — a rooted POSIX path has no drive.  Judging with the native
    # flavour alone would reject a correct production declaration for the wrong
    # reason ("malformed") instead of the right one ("the key is not on this
    # machine").  Accept either flavour's notion of absolute, so what is refused
    # is precisely what this rule exists to refuse: a cwd-relative reference,
    # which names a different file per invocation.
    if not (PurePosixPath(reference).is_absolute() or PureWindowsPath(reference).is_absolute()):
        return None
    try:
        resolved = Path(reference).resolve()
    except OSError:
        return None
    # Containment by resolved parents, never by string prefix: a
    # ``startswith(str(root))`` test is the exact Linux-only failure recorded in
    # CLAUDE.md §5b.
    checkout_root = Path(root).resolve() if root is not None else _REPO_ROOT
    if checkout_root == resolved or checkout_root in resolved.parents:
        return None
    return resolved


def _has_coherent_ci_provenance(env: Mapping[str, str]) -> bool:
    """Report whether the environment carries a coherent CI provenance set.

    ``GITHUB_ACTIONS=true`` is a self-asserted string that any shell can export,
    so on its own it never distinguished CI custody from a local process — which
    is precisely the property ``ci-secret`` exists to establish.  A real Actions
    runner also publishes a coherent, well-formed set of run identifiers; this
    demands all of them and validates their shape.

    HONEST LIMIT: this raises the bar, it is not a trust anchor.  A determined
    local actor can still export every variable below.  Only custody on hardware
    the local editor does not control makes the claim true; this check makes an
    accidental or careless local claim fail closed, and nothing more.
    """

    if env.get("GITHUB_ACTIONS", "").lower() != "true":
        return False
    checks = (
        ("GITHUB_REPOSITORY", re.compile(r"^[\w.-]+/[\w.-]+$")),
        ("GITHUB_RUN_ID", re.compile(r"^\d+$")),
        ("GITHUB_RUN_ATTEMPT", re.compile(r"^\d+$")),
        ("GITHUB_SHA", re.compile(r"^[0-9a-f]{40}$")),
        ("GITHUB_WORKFLOW_REF", re.compile(r"^[\w.-]+/[\w.-]+/.+@.+$")),
    )
    # Every marker is required.  Treating an absent one as "not applicable"
    # would re-open the hole for anyone who simply exports fewer variables.
    return all(pattern.match(env.get(name, "") or "") for name, pattern in checks)


def resolve_key(custody: str, *, root: Path | None = None) -> bytes | None:
    """Resolve key material for one custody reference, or ``None`` when absent.

    Absence is never an error here so the caller can report a precise,
    fail-closed reason instead of a traceback.  A short key is refused: a
    two-character environment value must not be able to satisfy a signature.
    """

    if not isinstance(custody, str) or ":" not in custody:
        return None
    scheme, _, reference = custody.partition(":")
    if not reference:
        return None
    if scheme in {"environment", "ci-secret"}:
        if scheme == "ci-secret" and not _has_coherent_ci_provenance(os.environ):
            # A CI-custody key presented outside CI is not CI custody.
            return None
        raw = os.environ.get(reference, "")
        material = raw.encode("utf-8") if raw else b""
    elif scheme == "file":
        # Anchor to the repository, never to the process working directory:
        # a relative reference otherwise resolves to a different file depending
        # on where the interpreter happened to be started.
        path = Path(reference)
        if not path.is_absolute():
            path = (Path(root).resolve() if root is not None else _REPO_ROOT) / path
        try:
            material = path.resolve().read_bytes().strip()
        except OSError:
            return None
    elif scheme == "offline-owner":
        path = _resolved_offline_owner_path(reference, root=root)
        if path is None:
            return None
        try:
            material = path.read_bytes().strip()
        except OSError:
            return None
    else:
        return None
    return material if len(material) >= _MINIMUM_KEY_BYTES else None


def _signing_message(attestation: dict[str, Any]) -> str:
    """Build the exact bytes a signature covers, excluding the signature itself."""

    return canonical_json({field: attestation.get(field) for field in _ATTESTATION_FIELDS})


def sign_attestation(attestation: dict[str, Any], key: bytes) -> str:
    """Return the HMAC-SHA256 signature over one attestation's signed fields."""

    return hmac.new(key, _signing_message(attestation).encode("utf-8"), sha256).hexdigest()


def build_attestation(
    *,
    role: str,
    key_id: str,
    custody: str,
    digest: str,
    signed_at: str,
    key: bytes | None,
    covers: list[str] | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one attestation, unsigned when no key material is available.

    An unsigned attestation is emitted deliberately rather than omitted: it
    records that the role was reached and that its key was absent, which is the
    fact the gate must act on.
    """

    attestation: dict[str, Any] = {
        "version": ATTESTATION_VERSION,
        "role": role,
        "scheme": SCHEME_HMAC if key else SCHEME_UNSIGNED,
        "key_id": key_id,
        "custody": custody,
        "signed_at": signed_at,
        "payload_sha256": digest,
        "covers": sorted(covers) if covers else [],
        "provenance": dict(provenance) if provenance else {},
    }
    attestation["signature"] = sign_attestation(attestation, key) if key else ""
    return attestation


def _check_shape(attestation: Any) -> str:
    """Refuse anything that is not a well-formed, supported attestation."""

    if not isinstance(attestation, dict):
        return "attestation-not-an-object"
    if set(attestation) != set(_ATTESTATION_FIELDS) | {"signature"}:
        return "attestation-field-set-mismatch"
    if type(attestation.get("version")) is not int or attestation["version"] != ATTESTATION_VERSION:
        return "attestation-version-unsupported"
    scheme = attestation.get("scheme")
    if scheme == SCHEME_UNSIGNED:
        return "attestation-unsigned"
    if scheme not in SUPPORTED_SCHEMES:
        return "attestation-scheme-unsupported"
    if attestation.get("role") not in ROLES:
        return "attestation-role-unknown"
    return ""


def _check_identity(attestation: dict[str, Any], references: dict[str, KeyReference]) -> str:
    """Refuse a signing identity the release authority never authorised."""

    key_id = attestation.get("key_id")
    reference = references.get(key_id) if isinstance(key_id, str) else None
    if reference is None:
        return "attestation-key-id-not-authorised"
    if reference.role != attestation.get("role"):
        return "attestation-key-id-bound-to-another-role"
    if attestation.get("custody") != reference.custody:
        return "attestation-custody-mismatch"
    return ""


def _check_payload(attestation: dict[str, Any], digest: str) -> str:
    """Refuse a signature that does not cover the payload being evaluated."""

    declared = attestation.get("payload_sha256")
    if not isinstance(declared, str) or _SHA256.fullmatch(declared) is None:
        return "attestation-payload-digest-malformed"
    if declared != digest:
        return "attestation-payload-digest-mismatch"
    signature = attestation.get("signature")
    if not isinstance(signature, str) or _HEX_SIGNATURE.fullmatch(signature) is None:
        return "attestation-signature-malformed"
    return ""


def verify_attestation(
    attestation: Any,
    *,
    digest: str,
    references: dict[str, KeyReference],
    root: Path | None = None,
) -> tuple[bool, str]:
    """Verify one attestation against the expected payload digest.

    Returns ``(ok, reason)``.  Every failure path is explicit so a caller can
    report which control refused, and an unknown scheme is refused rather than
    treated as legacy-and-allowed.
    """

    for reason in (
        _check_shape(attestation),
        _check_identity(attestation, references) if isinstance(attestation, dict) else "",
        _check_payload(attestation, digest) if isinstance(attestation, dict) else "",
    ):
        if reason:
            return False, reason
    key = resolve_key(references[attestation["key_id"]].custody, root=root)
    if key is None:
        # Never "skip verification when the key is missing": that is the one
        # failure mode that would silently convert a control into a comment.
        return False, "attestation-key-material-unavailable"
    if not hmac.compare_digest(attestation["signature"], sign_attestation(attestation, key)):
        return False, "attestation-signature-mismatch"
    return True, ""


def _collect_verified(
    attestations: list[Any],
    digest: str,
    references: dict[str, KeyReference],
    root: Path | None = None,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Verify each attestation once, keeping at most one per role and key."""

    verified: dict[str, dict[str, Any]] = {}
    reasons: list[str] = []
    seen_key_ids: set[str] = set()
    for attestation in attestations:
        ok, reason = verify_attestation(attestation, digest=digest, references=references, root=root)
        if not ok:
            reasons.append(reason)
            continue
        if attestation["role"] in verified:
            reasons.append("attestation-role-duplicated")
            continue
        if attestation["key_id"] in seen_key_ids:
            reasons.append("attestation-key-id-reused-across-roles")
            continue
        seen_key_ids.add(attestation["key_id"])
        verified[attestation["role"]] = attestation
    return verified, reasons


def evaluate_attestations(
    attestations: Any,
    *,
    digest: str,
    references: dict[str, KeyReference],
    required_roles: tuple[str, ...] = ROLES,
    independent_roles: tuple[str, ...] = ("owner", "ci"),
    root: Path | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Verify a full attestation set and report every reason it is insufficient.

    All required roles must verify and no two roles may share a key identity.
    ``owner`` and ``ci`` must additionally hold their key material outside the
    editable checkout, because those are the roles whose whole claim is that
    someone or something other than the local editor acted.  ``countersign`` is
    deliberately not in that set: its evidential weight comes from the
    re-executed outcomes it carries, which the caller checks against the
    bundle, not from where its key happens to live.
    """

    if not isinstance(attestations, list) or not attestations:
        return False, ("attestations-missing",)
    verified, reasons = _collect_verified(attestations, digest, references, root)
    for role in required_roles:
        if role not in verified:
            reasons.append(f"attestation-role-missing:{role}")
    for role in independent_roles:
        attestation = verified.get(role)
        if attestation is None:
            continue
        reference = references.get(attestation["key_id"])
        if reference is not None and not reference.is_independent:
            # A signature made with material sitting beside the editor cannot
            # establish that anything happened elsewhere.
            reasons.append(f"attestation-custody-not-independent:{role}")
    return (not reasons), tuple(dict.fromkeys(reasons))


def _key_reference(entry: Any, seen: set[str]) -> KeyReference | None:
    """Parse one declared signing identity, or ``None`` when it is malformed."""

    if not isinstance(entry, dict) or set(entry) != {"key_id", "role", "custody"}:
        return None
    key_id, role, custody = entry.get("key_id"), entry.get("role"), entry.get("custody")
    if not isinstance(key_id, str) or not key_id or key_id in seen:
        return None
    if role not in ROLES:
        return None
    if not isinstance(custody, str) or custody.split(":", 1)[0] not in CUSTODY_SCHEMES:
        return None
    return KeyReference(key_id=key_id, role=role, custody=custody)


def load_key_references(entries: Any) -> dict[str, KeyReference] | None:
    """Parse the authority's declared signing identities, or ``None`` if invalid."""

    if not isinstance(entries, list) or not entries:
        return None
    references: dict[str, KeyReference] = {}
    for entry in entries:
        reference = _key_reference(entry, set(references))
        if reference is None:
            return None
        references[reference.key_id] = reference
    if {reference.role for reference in references.values()} != set(ROLES):
        return None
    return references
