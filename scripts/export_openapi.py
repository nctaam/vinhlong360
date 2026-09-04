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


def _apply_response_media_types(document: dict) -> dict:
    """Overlay response types FastAPI cannot infer from a returned stream."""
    try:
        registry = json.loads(RESPONSE_MEDIA_TYPES.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid response media type registry: {RESPONSE_MEDIA_TYPES}") from exc
    if registry.get("schema_version") != "1" or not isinstance(registry.get("responses"), list):
        raise RuntimeError("response media type registry has an invalid schema")
    for entry in registry["responses"]:
        if not isinstance(entry, dict):
            raise RuntimeError("response media type entries must be objects")
        path = entry.get("path")
        method = entry.get("method")
        status = entry.get("status")
        media_type = entry.get("media_type")
        schema = entry.get("schema")
        if not all(isinstance(value, str) and value for value in (path, method, status, media_type)):
            raise RuntimeError("response media type entry has invalid identifiers")
        if not isinstance(schema, dict):
            raise RuntimeError("response media type entry schema must be an object")
        operation = document.get("paths", {}).get(path, {}).get(method.lower())
        if not isinstance(operation, dict) or status not in operation.get("responses", {}):
            raise RuntimeError(f"response media type entry does not match OpenAPI route: {method} {path} {status}")
        operation["responses"][status]["content"] = {media_type: {"schema": schema}}
    return document


def build_openapi() -> dict:
    repo_root = Path(__file__).resolve().parents[1]
    agent_root = repo_root / "agent"
    if str(agent_root) not in sys.path:
        sys.path.insert(0, str(agent_root))
    os.environ.setdefault("ENVIRONMENT", "development")
    if os.environ.get("VL360_DISABLE_DOTENV", "1") == "1":
        # Contract generation must not read a developer or production .env.
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
