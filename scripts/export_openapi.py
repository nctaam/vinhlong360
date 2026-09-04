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

    return app.openapi()


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
