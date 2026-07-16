import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
AGENT = ROOT / "agent"
CHECKER_PATH = ROOT / "scripts" / "checks" / "check_policy_http_registry.py"
sys.path.insert(0, str(AGENT))

try:
    import policy_http
except ModuleNotFoundError:
    policy_http = None


def _load_checker():
    if not CHECKER_PATH.exists():
        return None
    spec = importlib.util.spec_from_file_location("check_policy_http_registry", CHECKER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, source: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _codes(findings) -> set[str]:
    return {finding.code for finding in findings}


def test_scanner_rejects_unregistered_policy_route(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "unregistered.py",
        '''
from fastapi import APIRouter
router = APIRouter(prefix="/api")

@router.get("/new-policy")
def new_policy():
    return {"index_policy": {"indexable": False, "policy_revision": "index-policy-v1"}}
''',
    )

    findings = checker.scan_policy_routes([source], policy_http.POLICY_ENDPOINTS)

    assert findings[0].code == "UNREGISTERED_POLICY_ROUTE"


def test_scanner_reports_stale_registry_and_contract_mismatch(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "public_api.py",
        '''
from fastapi import APIRouter
router = APIRouter(prefix="/api")

@router.post("/entities/{entity_id}")
def get_entity(entity_id: str):
    return {"index_policy": {"indexable": False, "policy_revision": "index-policy-v1"}}
''',
    )

    findings = checker.scan_policy_routes([source], policy_http.POLICY_ENDPOINTS)

    assert "POLICY_ROUTE_CONTRACT_MISMATCH" in _codes(findings)
    assert "STALE_POLICY_REGISTRY_ENTRY" in _codes(findings)


def test_scanner_does_not_classify_internal_evidence_or_cache_key_usage(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "seo.py",
        '''
from fastapi import APIRouter
router = APIRouter()

@router.get("/sitemap.xml")
def sitemap():
    evidence = current_policy_evidence()
    cache_key = evidence.policy_fingerprint
    return Response(content="<urlset/>", media_type="application/xml")
''',
    )

    findings = checker.scan_policy_routes(
        [source],
        (),
    )

    assert findings == []


def test_scanner_does_not_classify_marker_strings_or_type_annotations(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None
    source = _write(
        tmp_path / "metrics.py",
        '''
from fastapi import APIRouter
router = APIRouter()

@router.get("/metrics")
def metrics():
    decision: IndexPolicyDecision | None = None
    metric_name = "index_policy"
    log(metric_name, decision)
    return {"ok": True}
''',
    )

    assert checker.scan_policy_routes([source], ()) == []


def test_scanner_classifies_serialized_policy_evidence(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "policy.py",
        '''
from fastapi import APIRouter
router = APIRouter()

@router.get("/serialized")
def serialized():
    evidence = current_policy_evidence()
    return {
        "index_policy": {"indexable": False},
        "policy_fingerprint": evidence.policy_fingerprint,
        "policy_revision": evidence.backend_policy_revision,
    }
''',
    )

    findings = checker.scan_policy_routes([source], ())

    assert _codes(findings) == {"UNREGISTERED_POLICY_ROUTE"}


def test_scanner_joins_imported_router_and_include_prefix(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    routes = _write(
        tmp_path / "routes.py",
        '''
from fastapi import APIRouter
router = APIRouter(prefix="/entities")

@router.get("/{entity_id}")
def get_entity(entity_id: str):
    payload = {"index_policy": {"indexable": False, "policy_revision": "index-policy-v1"}}
    return payload
''',
    )
    server = _write(
        tmp_path / "server.py",
        '''
from fastapi import FastAPI
from routes import router as public_router
app = FastAPI()
app.include_router(public_router, prefix="/api")
''',
    )

    findings = checker.scan_policy_routes(
        [routes, server],
        (policy_http.POLICY_ENDPOINTS[0],),
    )

    assert findings == []


def test_scanner_joins_module_alias_and_keyword_decorator_path(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    routes = _write(
        tmp_path / "routes.py",
        '''
from fastapi import APIRouter
router = APIRouter(prefix="/entities")

@router.get(path="/{entity_id}", name="get_entity")
def detail(entity_id: str):
    return {"index_policy": {"indexable": False, "policy_revision": "index-policy-v1"}}
''',
    )
    server = _write(
        tmp_path / "server.py",
        '''
from fastapi import FastAPI
import routes as public
app = FastAPI()
app.include_router(public.router, prefix="/api")
''',
    )

    assert checker.scan_policy_routes(
        [routes, server],
        (policy_http.POLICY_ENDPOINTS[0],),
    ) == []


def test_scanner_propagates_nested_router_prefixes(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "nested.py",
        '''
from fastapi import APIRouter, FastAPI
api_router = APIRouter(prefix="/api")
entity_router = APIRouter(prefix="/entities")
app = FastAPI()
api_router.include_router(entity_router)
app.include_router(api_router)

@entity_router.get("/{entity_id}", name="get_entity")
def get_entity(entity_id: str):
    return {"index_policy": {"indexable": False, "policy_revision": "index-policy-v1"}}
''',
    )

    assert checker.scan_policy_routes([source], (policy_http.POLICY_ENDPOINTS[0],)) == []


def test_unmounted_exact_route_is_not_accepted_as_resolved_registry_identity(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "public_api.py",
        '''
from fastapi import APIRouter
router = APIRouter(prefix="/api")

@router.get("/entities/{entity_id}", name="get_entity")
def get_entity(entity_id: str):
    return {"index_policy": {"indexable": False, "policy_revision": "index-policy-v1"}}
''',
    )

    findings = checker.scan_policy_routes(
        [source],
        (policy_http.POLICY_ENDPOINTS[0],),
    )

    assert _codes(findings) == {
        "POLICY_ROUTE_CONTRACT_MISMATCH",
        "STALE_POLICY_REGISTRY_ENTRY",
    }


def test_scanner_preserves_fastapi_trailing_slash_route_semantics(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "public_api.py",
        '''
from fastapi import APIRouter, FastAPI
router = APIRouter(prefix="/api")
app = FastAPI()
app.include_router(router)

@router.get("/entities/{entity_id}/", name="get_entity")
def get_entity(entity_id: str):
    return {"index_policy": {"indexable": False, "policy_revision": "index-policy-v1"}}
''',
    )

    findings = checker.scan_policy_routes([source], (policy_http.POLICY_ENDPOINTS[0],))

    assert "POLICY_ROUTE_CONTRACT_MISMATCH" in _codes(findings)
    assert "STALE_POLICY_REGISTRY_ENTRY" in _codes(findings)


def test_fake_include_router_receiver_does_not_mount_policy_router(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "public_api.py",
        '''
from fastapi import APIRouter
router = APIRouter(prefix="/api")
fake_receiver = object()
fake_receiver.include_router(router)

@router.get("/entities/{entity_id}", name="get_entity")
def get_entity(entity_id: str):
    return {"index_policy": {"indexable": False, "policy_revision": "index-policy-v1"}}
''',
    )

    findings = checker.scan_policy_routes([source], (policy_http.POLICY_ENDPOINTS[0],))

    assert "POLICY_ROUTE_CONTRACT_MISMATCH" in _codes(findings)
    assert "STALE_POLICY_REGISTRY_ENTRY" in _codes(findings)


def test_app_name_without_fastapi_constructor_does_not_mount_policy_router(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "public_api.py",
        '''
from fastapi import APIRouter
router = APIRouter(prefix="/api")
app = object()
app.include_router(router)

@router.get("/entities/{entity_id}", name="get_entity")
def get_entity(entity_id: str):
    return {"index_policy": {"indexable": False, "policy_revision": "index-policy-v1"}}
''',
    )

    findings = checker.scan_policy_routes([source], (policy_http.POLICY_ENDPOINTS[0],))

    assert "POLICY_ROUTE_CONTRACT_MISMATCH" in _codes(findings)
    assert "STALE_POLICY_REGISTRY_ENTRY" in _codes(findings)


def test_scanner_resolves_fastapi_constructor_aliases(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "aliased.py",
        '''
from fastapi import APIRouter as Router, FastAPI as Application
router = Router(prefix="/api")
app = Application()
app.include_router(router)

@router.get("/entities/{entity_id}", name="get_entity")
def get_entity(entity_id: str):
    return {"index_policy": {"indexable": False, "policy_revision": "index-policy-v1"}}
''',
    )

    assert checker.scan_policy_routes([source], (policy_http.POLICY_ENDPOINTS[0],)) == []


def test_scanner_resolves_fastapi_module_alias_constructors(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "module_alias.py",
        '''
import fastapi as fa
router = fa.APIRouter(prefix="/api")
app = fa.FastAPI()
app.include_router(router)

@router.get("/entities/{entity_id}", name="get_entity")
def get_entity(entity_id: str):
    return {"index_policy": {"indexable": False, "policy_revision": "index-policy-v1"}}
''',
    )

    assert checker.scan_policy_routes([source], (policy_http.POLICY_ENDPOINTS[0],)) == []


@pytest.mark.parametrize(
    "constructor_source",
    [
        '''
from fake import APIRouter, FastAPI
router = APIRouter(prefix="/api")
app = FastAPI()
''',
        '''
import fake
router = fake.APIRouter(prefix="/api")
app = fake.FastAPI()
''',
    ],
)
def test_non_fastapi_constructor_provenance_fails_closed(
    tmp_path: Path,
    constructor_source: str,
):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "fake_constructor.py",
        constructor_source
        + '''
app.include_router(router)

@router.get("/entities/{entity_id}", name="get_entity")
def get_entity(entity_id: str):
    return {"index_policy": {"indexable": False, "policy_revision": "index-policy-v1"}}
''',
    )

    findings = checker.scan_policy_routes([source], (policy_http.POLICY_ENDPOINTS[0],))

    assert "POLICY_ROUTE_SCAN_ERROR" in _codes(findings)
    assert "STALE_POLICY_REGISTRY_ENTRY" in _codes(findings)


@pytest.mark.parametrize(
    "constructor_source",
    [
        '''
from .fastapi import APIRouter, FastAPI
router = APIRouter(prefix="/api")
app = FastAPI()
''',
        '''
from fastapi import APIRouter, FastAPI
APIRouter = fake.APIRouter
FastAPI = fake.FastAPI
router = APIRouter(prefix="/api")
app = FastAPI()
''',
        '''
import fastapi
fastapi = fake
router = fastapi.APIRouter(prefix="/api")
app = fastapi.FastAPI()
''',
        '''
from fastapi import APIRouter, FastAPI
if True:
    APIRouter = fake.APIRouter
    FastAPI = fake.FastAPI
router = APIRouter(prefix="/api")
app = FastAPI()
''',
        '''
import fastapi
if True:
    fastapi = fake
router = fastapi.APIRouter(prefix="/api")
app = fastapi.FastAPI()
''',
        '''
from fastapi import APIRouter, FastAPI
del APIRouter
del FastAPI
router = APIRouter(prefix="/api")
app = FastAPI()
''',
    ],
)
def test_relative_or_shadowed_fastapi_provenance_fails_closed(
    tmp_path: Path,
    constructor_source: str,
):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "shadowed_constructor.py",
        constructor_source
        + '''
app.include_router(router)

@router.get("/entities/{entity_id}", name="get_entity")
def get_entity(entity_id: str):
    return {"index_policy": {"indexable": False, "policy_revision": "index-policy-v1"}}
''',
    )

    findings = checker.scan_policy_routes([source], (policy_http.POLICY_ENDPOINTS[0],))

    assert "POLICY_ROUTE_SCAN_ERROR" in _codes(findings)
    assert "STALE_POLICY_REGISTRY_ENTRY" in _codes(findings)


def test_unresolved_router_constructor_fails_closed(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None
    source = _write(
        tmp_path / "unresolved.py",
        '''
from fastapi import FastAPI
router = make_router(prefix="/api")
app = FastAPI()
app.include_router(router)

@router.get("/policy")
def policy():
    return {"index_policy": {"indexable": False}}
''',
    )

    findings = checker.scan_policy_routes([source], ())

    assert "POLICY_ROUTE_SCAN_ERROR" in _codes(findings)


def test_scanner_classifies_asdict_typed_policy_and_response_header_sinks(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None
    source = _write(
        tmp_path / "policy.py",
        '''
from dataclasses import asdict
from fastapi import FastAPI, Response
app = FastAPI()

@app.get("/asdict")
def asdict_policy():
    decision: IndexPolicyDecision = IndexPolicyDecision(...)
    return asdict(decision)

@app.get("/headers")
def header_policy():
    headers = {"X-Launch-Indexing-Policy": "failed-open"}
    return Response(content="ok", headers=headers)

@app.get("/cache")
def cache_only():
    cache = {}
    cache["index_policy"] = False
    return {"ok": True}
''',
    )

    findings = checker.scan_policy_routes([source], ())
    unregistered = [finding for finding in findings if finding.code == "UNREGISTERED_POLICY_ROUTE"]

    assert {Path(finding.file).name for finding in unregistered} == {"policy.py"}
    assert len(unregistered) == 2


def test_scanner_classifies_response_header_update_call_sink(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None
    source = _write(
        tmp_path / "header_update.py",
        '''
from fastapi import FastAPI, Response
app = FastAPI()

@app.get("/policy-header")
def policy_header(response: Response):
    response.headers.update({"X-Launch-Indexing-Policy": "failed-open"})
    return {"ok": True}
''',
    )

    findings = checker.scan_policy_routes([source], ())

    assert _codes(findings) == {"UNREGISTERED_POLICY_ROUTE"}


def test_scanner_taints_local_header_dict_into_update_sink(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None
    source = _write(
        tmp_path / "header_update_local.py",
        '''
from fastapi import FastAPI, Response
app = FastAPI()

@app.get("/policy-header-local")
def policy_header_local(response: Response):
    headers = {"X-Launch-Indexing-Policy": "failed-open"}
    response.headers.update(headers)
    return {"ok": True}
''',
    )

    findings = checker.scan_policy_routes([source], ())

    assert _codes(findings) == {"UNREGISTERED_POLICY_ROUTE"}


def test_scanner_supports_api_route_methods_and_exact_header_markers(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None
    source = _write(
        tmp_path / "policy.py",
        '''
from fastapi import FastAPI
app = FastAPI()

@app.api_route("/policy", methods=["GET"], name="policy")
def policy():
    return {"index_policy": {"indexable": False}}

@app.get("/indexing")
def indexing():
    return Response(headers={"X-Launch-Indexing-Policy": "failed-open"})

@app.get("/route-revision")
def route_revision():
    return Response(headers={"X-Launch-Route-Manifest-Revision": "route-v1"})

@app.get("/backend-revision")
def backend_revision():
    return Response(headers={"X-Launch-Backend-Policy-Revision": "backend-v1"})

@app.get("/batch-revision")
def batch_revision():
    return Response(headers={"X-Launch-Sitemap-Batch-Revision": "a" * 64})

@app.get("/requested-batch")
def requested_batch():
    return Response(headers={"X-Launch-Sitemap-Requested-Batch": "a" * 64})

@app.get("/debug-marker")
def debug_marker():
    return {"ok": True, "debug": "index_policy"}
''',
    )

    findings = checker.scan_policy_routes([source], ())

    assert len([finding for finding in findings if finding.code == "UNREGISTERED_POLICY_ROUTE"]) == 6


def test_scanner_fails_closed_on_dynamic_route_path(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None
    source = _write(
        tmp_path / "dynamic.py",
        '''
from fastapi import APIRouter
router = APIRouter()
PATH = get_path()

@router.get(PATH)
def dynamic():
    return {"index_policy": {"indexable": False}}
''',
    )

    findings = checker.scan_policy_routes([source], ())

    assert "POLICY_ROUTE_SCAN_ERROR" in _codes(findings)


def test_future_allowance_does_not_hide_mounted_contract_mismatch(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(
        tmp_path / "internal.py",
        '''
from fastapi import FastAPI
app = FastAPI()

@app.post("/_internal/launch-policy-attestation", name="launch_policy_attestation")
def launch_policy_attestation():
    return {"policy_fingerprint": "a" * 64, "policy_revision": "index-policy-v1"}
''',
    )

    findings = checker.scan_policy_routes(
        [source],
        (policy_http.POLICY_ENDPOINTS[1],),
        allowed_future={"launch_policy_attestation"},
    )

    assert "INVALID_FUTURE_ALLOWANCE" in _codes(findings)
    assert "POLICY_ROUTE_CONTRACT_MISMATCH" in _codes(findings)


def test_hard_check_uses_only_the_two_task12_future_allowances():
    checker = _load_checker()
    assert checker is not None

    result = checker.PolicyHttpRegistryCheck(root=ROOT).run()

    assert result["count"] == 0


def test_public_future_allowance_is_rejected_and_cannot_hide_stale_entry(tmp_path: Path):
    checker = _load_checker()
    assert checker is not None and policy_http is not None
    source = _write(tmp_path / "empty.py", "value = 1\n")

    findings = checker.scan_policy_routes(
        [source],
        (policy_http.POLICY_ENDPOINTS[0],),
        allowed_future={"get_entity"},
    )

    assert "INVALID_FUTURE_ALLOWANCE" in _codes(findings)
    assert "STALE_POLICY_REGISTRY_ENTRY" in _codes(findings)
    assert checker._validate_allow_future(["get_entity"])


def test_current_repository_registry_is_exact_with_only_declared_futures():
    checker = _load_checker()
    assert checker is not None and policy_http is not None

    findings = checker.scan_policy_routes(
        checker.agent_source_files(AGENT),
        policy_http.POLICY_ENDPOINTS,
        allowed_future={"launch_policy_attestation", "launch_sitemap_document"},
    )

    assert findings == []


@pytest.mark.parametrize(
    "args",
    [
        ["--allow-future", "unknown_future"],
        ["--allow-future", "launch_policy_attestation", "--allow-future", "launch_policy_attestation"],
        ["--allow-future", "get_entity"],
    ],
)
def test_cli_rejects_unknown_or_duplicate_future_allowance(args: list[str]):
    assert CHECKER_PATH.exists()
    completed = subprocess.run(
        [sys.executable, str(CHECKER_PATH), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    assert completed.returncode != 0
    assert "INVALID_FUTURE_ALLOWANCE" in completed.stdout + completed.stderr
