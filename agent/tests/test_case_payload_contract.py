"""What the routes send, against what the frontend is typed to receive.

Two of the most expensive defects of this pilot were the same shape: a payload
and a TypeScript interface that disagreed, with nothing between them. The
composable posted snake_case at models that accept only camelCase, so every
submission 422'd. The workbench payload carried no change_set, so the page could
only post an empty id and the whole publication chain was dead.

Neither side was wrong on its own — they were wrong about each other, and no
test in either language could see both. This one reads the live payload from the
running route and the field list out of the .ts file, and requires them to
match: a field the frontend expects and the route omits renders as undefined to
a person waiting on an answer, and a key the route sends that the frontend never
declared is either dead weight or a type that lies.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _pg_test_database import pg_only  # noqa: E402

WEB = ROOT / "web-nuxt"


def interface_fields(source: Path, name: str) -> dict[str, bool]:
    """Top-level fields of one TS interface, mapped to whether they are optional.

    Deliberately shallow. Nested shapes are the frontend's own business; what
    has actually broken here is the top-level agreement about which keys exist.
    """
    text = source.read_text(encoding="utf-8")
    match = re.search(rf"export interface {name} \{{(.*?)\n\}}", text, re.DOTALL)
    if match is None:
        raise AssertionError(f"{name} is not declared in {source.name}")
    fields: dict[str, bool] = {}
    for line in match.group(1).split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "*", "/*")):
            continue
        declaration = re.match(r"([A-Za-z_][A-Za-z0-9_]*)(\??):", stripped)
        if declaration:
            fields[declaration.group(1)] = declaration.group(2) == "?"
    return fields


def test_the_interface_reader_actually_reads_something():
    fields = interface_fields(WEB / "types" / "cases.ts", "CaseStatus")

    # A reader that quietly matches nothing would make every comparison below
    # vacuously true, which is the failure mode this whole file is about.
    assert len(fields) >= 8
    assert fields["publicReference"] is False
    assert "itemDecisions" in fields


def test_an_undeclared_interface_is_an_error_not_an_empty_set():
    with pytest.raises(AssertionError, match="not declared"):
        interface_fields(WEB / "types" / "cases.ts", "NoSuchInterfaceExists")


@pg_only
def test_the_status_payload_and_its_typescript_type_agree(client):
    """The reporter's status page, field for field."""
    from test_correction_http_journey import _body, _headers, ORIGIN

    created = client.post("/api/cases/corrections", json=_body(), headers=_headers())
    receipt = created.json()
    client.post(
        "/api/cases/access",
        json={"publicReference": receipt["publicReference"],
              "capability": receipt["capability"]},
        headers={"Origin": ORIGIN, "Sec-Fetch-Site": "same-origin"},
    )
    payload = client.get("/api/cases/status").json()

    declared = interface_fields(WEB / "types" / "cases.ts", "CaseStatus")
    required = {name for name, optional in declared.items() if not optional}

    missing = sorted(required - set(payload))
    assert not missing, f"the page expects fields the route never sends: {missing}"
    undeclared = sorted(set(payload) - set(declared))
    assert not undeclared, f"the route sends fields the page never declared: {undeclared}"


@pg_only
def test_the_receipt_payload_and_its_typescript_type_agree(client):
    from test_correction_http_journey import _body, _headers

    payload = client.post(
        "/api/cases/corrections", json=_body(), headers=_headers(),
    ).json()

    declared = interface_fields(WEB / "types" / "cases.ts", "CaseReceipt")
    required = {name for name, optional in declared.items() if not optional}

    # capability lives here and nowhere else: it is shown once and never stored,
    # so the type and the payload agreeing is what keeps it out of state objects.
    assert not sorted(required - set(payload))
    assert not sorted(set(payload) - set(declared))


@pg_only
def test_the_workbench_payload_and_its_typescript_type_agree(operator):
    """The operator's case detail — the payload whose missing key killed publishing."""
    from test_correction_admin_http import _seed

    client, adapter, _ = operator
    case_id, _ = _seed(adapter)
    payload = client.get(f"/admin/cases/{case_id}").json()

    declared = interface_fields(WEB / "composables" / "useAdminCases.ts", "AdminCaseDetail")
    required = {name for name, optional in declared.items() if not optional}

    missing = sorted(required - set(payload))
    assert not missing, f"the workbench expects fields the route never sends: {missing}"
    undeclared = sorted(set(payload) - set(declared))
    assert not undeclared, f"the route sends fields the workbench never declared: {undeclared}"
    # The specific key, named: it is the difference between a page that can
    # publish and one that can only post an empty id.
    assert "change_set" in declared


@pg_only
def test_the_queue_payload_and_its_typescript_type_agree(operator):
    from test_correction_admin_http import _seed

    client, adapter, _ = operator
    _seed(adapter)
    rows = client.get("/admin/cases").json()["items"]
    assert rows, "the queue returned nothing, so this comparison proves nothing"

    declared = interface_fields(WEB / "composables" / "useAdminCases.ts", "AdminQueueItem")
    required = {name for name, optional in declared.items() if not optional}

    for row in rows[:5]:
        assert not sorted(required - set(row)), f"queue row missing fields: {row.keys()}"
        assert not sorted(set(row) - set(declared)), f"queue row has undeclared keys: {row.keys()}"


@pg_only
def test_a_deliberately_wrong_expectation_is_caught(client):
    """The guard, guarded: a field the route does not send must fail loudly."""
    from test_correction_http_journey import _body, _headers

    payload = client.post(
        "/api/cases/corrections", json=_body(), headers=_headers(),
    ).json()
    pretend_declared = {"publicReference": False, "totallyInventedField": False}

    required = {name for name, optional in pretend_declared.items() if not optional}
    missing = sorted(required - set(payload))

    assert missing == ["totallyInventedField"]


@pytest.fixture
def client(monkeypatch):
    from test_correction_http_journey import client as journey_client

    yield from journey_client.__wrapped__(monkeypatch)


@pytest.fixture
def operator(monkeypatch):
    from test_correction_admin_http import operator as admin_operator

    yield from admin_operator.__wrapped__(monkeypatch)

