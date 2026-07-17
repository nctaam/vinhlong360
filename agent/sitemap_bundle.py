"""Fail-closed Task 17 CLI shell for future complete sitemap publication."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AGENT_DIR.parent
for import_root in (PROJECT_DIR, AGENT_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))


REFRESH_UNAVAILABLE_ERROR = (
    "sitemap refresh unavailable until complete bundle rendering is implemented"
)


class SitemapRefreshUnavailable(RuntimeError):
    """Task 17 cannot activate an incomplete three-document bundle."""


def refresh() -> None:
    raise SitemapRefreshUnavailable(REFRESH_UNAVAILABLE_ERROR)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("refresh",))
    args = parser.parse_args(argv)
    if args.command == "refresh":
        try:
            refresh()
        except SitemapRefreshUnavailable as exc:
            print(str(exc), file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
