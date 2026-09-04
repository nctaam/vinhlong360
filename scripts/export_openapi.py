"""Export the live FastAPI OpenAPI document deterministically.

This is a contract-tooling command. It imports the application with development
defaults and writes only the generated OpenAPI document; it never contacts a
provider or reads a production environment file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESPONSE_MEDIA_TYPES = ROOT / "contracts" / "response-media-types.json"


def _load_response_media_registry() -> list[dict]:
    try:
        registry = json.loads(RESPONSE_MEDIA_TYPES.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid response media type registry: {RESPONSE_MEDIA_TYPES}") from exc
    schema_version = registry.get("schema_version") if isinstance(registry, dict) else None
    responses = registry.get("responses") if isinstance(registry, dict) else None
    if schema_version != "1" or not isinstance(responses, list):
        raise RuntimeError("response media type registry has an invalid schema")
    if not responses:
        raise RuntimeError("response media type registry must contain at least one response")
    return responses


def _validate_response_media_entry(entry: object, document: dict,
                                   seen: set[tuple[str, str, str]]) -> tuple[str, str, str, str, dict]:
    if not isinstance(entry, dict):
        raise RuntimeError("response media type entries must be objects")
    path, method, status, media_type, schema = (
        entry.get("path"), entry.get("method"), entry.get("status"),
        entry.get("media_type"), entry.get("schema"),
    )
    if not all(isinstance(value, str) and value for value in (path, method, status, media_type)):
        raise RuntimeError("response media type entry has invalid identifiers")
    identity = (method.lower(), path, status)
    if identity in seen:
        raise RuntimeError(f"duplicate response media type entry: {method} {path} {status}")
    seen.add(identity)
    if not isinstance(schema, dict):
        raise RuntimeError("response media type entry schema must be an object")
    operation = document.get("paths", {}).get(path, {}).get(method.lower())
    if not isinstance(operation, dict) or status not in operation.get("responses", {}):
        raise RuntimeError(f"response media type entry does not match OpenAPI route: {method} {path} {status}")
    return path, method.lower(), status, media_type, schema


def _apply_response_media_types(document: dict) -> dict:
    """Overlay response types FastAPI cannot infer from a returned stream."""
    responses = _load_response_media_registry()
    seen: set[tuple[str, str, str]] = set()
    for entry in responses:
        path, method, status, media_type, schema = _validate_response_media_entry(entry, document, seen)
        operation = document["paths"][path][method]
        operation["responses"][status]["content"] = {media_type: {"schema": schema}}
    return document


def build_openapi() -> dict:
    repo_root = Path(__file__).resolve().parents[1]
    agent_root = repo_root / "agent"
    if str(agent_root) not in sys.path:
        sys.path.insert(0, str(agent_root))
    # Contract generation is deterministic and credential-free regardless of
    # the caller's ambient environment.
    os.environ["ENVIRONMENT"] = "development"
    os.environ["VL360_DISABLE_DOTENV"] = "1"
    import dotenv

    dotenv.load_dotenv = lambda *args, **kwargs: False
    from server import app

    return _apply_response_media_types(app.openapi())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    document = build_openapi()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
