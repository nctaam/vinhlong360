#!/usr/bin/env python3
"""Release quality budgets for data trust and regression control."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import validate_data  # noqa: E402


@dataclass
class BudgetResult:
    key: str
    actual: float
    expected: float
    op: str
    severity: str
    ok: bool


DEFAULT_MAX = {
    "out_of_bounds_coordinates": 0,
    "broken_relationships": 0,
    "boilerplate_summary": 0,
    "text_repeated_sentence": 0,
    "text_bad_sentence_join": 0,
    "text_excessive_length": 0,
    "coordinate_clusters_precise": 0,
    "summary_truncated": 0,
    "image_missing_credit": 0,
    "image_missing_license": 0,
    "image_missing_source": 0,
    "duplicate_source_urls": 150,
    "self_citation_pct": 25.0,
}

DEFAULT_MIN = {
    "quality_score_avg": 85.0,
    "place_coords_coverage_pct": 99.0,
    # Media coverage is intentionally non-blocking until the licensed media pipeline is populated.
    "image_coverage_pct": 0.0,
}


def _load_json(path: Path) -> dict[str, Any]:
    return validate_data._load_json(path)  # type: ignore[attr-defined]


def _iter_source_urls(data: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for entity in data.get("entities", []):
        if not isinstance(entity, dict):
            continue
        source = entity.get("source")
        if not isinstance(source, list):
            continue
        for item in source:
            if isinstance(item, dict):
                url = item.get("url")
            elif isinstance(item, str):
                url = item
            else:
                url = None
            if isinstance(url, str) and url.strip():
                urls.append(url.strip())
    return urls


def _self_citation_pct(data: dict[str, Any]) -> float:
    urls = _iter_source_urls(data)
    if not urls:
        return 0.0
    self_hosts = ("vinhlong360.vn", "localhost", "127.0.0.1")
    count = 0
    for url in urls:
        host = (urlparse(url).hostname or "").lower()
        if any(host == self_host or host.endswith("." + self_host) for self_host in self_hosts):
            count += 1
    return round(100 * count / len(urls), 2)


def evaluate(
    data: dict[str, Any],
    data_path: Path,
    max_budget: dict[str, float] | None = None,
    min_budget: dict[str, float] | None = None,
) -> tuple[list[BudgetResult], dict[str, Any], list[dict[str, Any]]]:
    issues, stats = validate_data.validate(data, data_path)
    enriched = dict(stats)
    enriched["self_citation_pct"] = _self_citation_pct(data)
    max_budget = {**DEFAULT_MAX, **(max_budget or {})}
    min_budget = {**DEFAULT_MIN, **(min_budget or {})}

    results: list[BudgetResult] = []
    for key, expected in max_budget.items():
        actual = float(enriched.get(key, 0) or 0)
        results.append(BudgetResult(key, actual, float(expected), "<=", "error", actual <= float(expected)))
    for key, expected in min_budget.items():
        actual = float(enriched.get(key, 0) or 0)
        results.append(BudgetResult(key, actual, float(expected), ">=", "error", actual >= float(expected)))

    return results, enriched, [issue.__dict__ for issue in issues]


def _parse_budget_items(items: list[str], op_name: str) -> dict[str, float]:
    parsed: dict[str, float] = {}
    for item in items:
        if "=" not in item:
            raise argparse.ArgumentTypeError(f"{op_name} item must be key=value: {item}")
        key, value = item.split("=", 1)
        parsed[key.strip()] = float(value)
    return parsed


def print_report(results: list[BudgetResult], stats: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    print("VinhLong360 quality budget")
    print("==========================")
    print(f"entities: {stats.get('entities')}")
    print(f"quality_score_avg: {stats.get('quality_score_avg')}")
    print(f"image_coverage_pct: {stats.get('image_coverage_pct')}")
    print(f"image_total: {stats.get('image_total')}")
    print(f"image_missing_credit: {stats.get('image_missing_credit')}")
    print(f"image_missing_license: {stats.get('image_missing_license')}")
    print(f"image_missing_source: {stats.get('image_missing_source')}")
    print(f"duplicate_source_urls: {stats.get('duplicate_source_urls')}")
    print(f"self_citation_pct: {stats.get('self_citation_pct')}")
    print("\nBudgets:")
    for result in results:
        status = "OK" if result.ok else "FAIL"
        print(f"  [{status}] {result.key}: {result.actual} {result.op} {result.expected}")
    if issues:
        blocking = [issue for issue in issues if issue.get("severity") == "error"]
        print(f"\nValidator issues: {len(issues)} ({len(blocking)} blocking)")

def _metric_unit(key: str) -> str:
    if key.endswith("_pct"):
        return "percent"
    if "score" in key:
        return "score"
    if key.endswith("_avg"):
        return "average"
    return "count"

def _numeric_metrics(stats: dict[str, Any], results: list[BudgetResult]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for key, value in stats.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            metrics[key] = float(value)
    for result in results:
        metrics.setdefault(result.key, float(result.actual))
    return metrics

def record_db_snapshots(
    database_url: str,
    stats: dict[str, Any],
    results: list[BudgetResult],
    issues: list[dict[str, Any]],
    *,
    data_path: Path,
    source: str = "quality_budget",
) -> int:
    """Append quality budget metrics to Postgres for AdminCP trend charts."""
    if not database_url:
        raise ValueError("DATABASE_URL is required for --record-db")
    try:
        import psycopg2  # type: ignore
        from psycopg2.extras import Json  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"cannot import psycopg2 for quality snapshot recording: {exc}") from exc

    budget_by_key = {result.key: result for result in results}
    metrics = _numeric_metrics(stats, results)
    created_at = datetime.now(timezone.utc)
    issue_count = len(issues)
    blocking_issue_count = sum(1 for issue in issues if issue.get("severity") == "error")
    rows = []
    for key, value in sorted(metrics.items()):
        result = budget_by_key.get(key)
        metadata: dict[str, Any] = {
            "data_path": str(data_path),
            "issue_count": issue_count,
            "blocking_issue_count": blocking_issue_count,
        }
        if result:
            metadata["budget"] = {
                "expected": result.expected,
                "op": result.op,
                "severity": result.severity,
                "ok": result.ok,
            }
        rows.append((key, value, _metric_unit(key), source, Json(metadata), created_at))

    if not rows:
        return 0
    with psycopg2.connect(database_url, connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO quality_metric_snapshots
                    (metric_key, metric_value, metric_unit, source, metadata, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                rows,
            )
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "web" / "data.json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max", action="append", default=[], help="Override max budget, e.g. duplicate_source_urls=120")
    parser.add_argument("--min", action="append", default=[], help="Override min budget, e.g. image_coverage_pct=50")
    parser.add_argument("--record-db", action="store_true", help="Append numeric metrics to quality_metric_snapshots.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""), help="Postgres DSN for --record-db.")
    parser.add_argument("--source", default="quality_budget", help="Snapshot source label.")
    args = parser.parse_args()

    data = _load_json(args.data)
    results, stats, issues = evaluate(
        data,
        args.data,
        max_budget=_parse_budget_items(args.max, "--max"),
        min_budget=_parse_budget_items(args.min, "--min"),
    )
    failures = [result for result in results if not result.ok]
    if args.json:
        print(json.dumps({
            "stats": stats,
            "budgets": [result.__dict__ for result in results],
            "issues": issues,
        }, ensure_ascii=False, indent=2))
    else:
        print_report(results, stats, issues)
    if args.record_db:
        inserted = record_db_snapshots(
            args.database_url,
            stats,
            results,
            issues,
            data_path=args.data,
            source=args.source,
        )
        if not args.json:
            print(f"\nRecorded quality_metric_snapshots: {inserted}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
