#!/usr/bin/env python3
"""Repair & Deep-Fill for research_deep pipeline.

Fixes:
  1. Remove empty/broken L4 adversarial entries from thematic JSONL (so re-run picks them up)
  2. Remove empty synthesis entries from asset JSONL
  3. Re-run Phase 1 (thematic) — only processes missing layers
  4. Re-run Phase 2 (assets) — only processes missing angles/adversarial/synthesis
  5. Re-run Phase 3 (crosslink) — rebuilds full confidence matrix for all 62 assets
  6. Deep verification pass — re-check low-confidence assets with extra skeptics

Usage:
  python -u agent/scripts/research_repair.py --all --rps 1.0 --concurrent 2
  python -u agent/scripts/research_repair.py --clean-only          # just remove broken entries
  python -u agent/scripts/research_repair.py --phase 1 --rps 1.0   # repair thematic only
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT_DIR.parent))
OUTPUT_DIR = AGENT_DIR / "data" / "research_deep"


def tprint(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    try:
        print(f"[{ts}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{ts}] {msg.encode('ascii', 'replace').decode()}", flush=True)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def write_jsonl(path: Path, records: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# ─── Step 1: Clean broken entries ────────────────────────────────────────────

def is_entry_empty(rec: dict) -> bool:
    """Check if an entry has no meaningful data (beyond metadata fields)."""
    skip_fields = {"layer", "sub_topic", "theme_id", "timestamp", "asset_id", "angle", "pass"}
    for key, val in rec.items():
        if key in skip_fields:
            continue
        if isinstance(val, str) and len(val) > 10:
            return False
        if isinstance(val, list) and len(val) > 0:
            return False
        if isinstance(val, dict) and len(val) > 0:
            return False
        if isinstance(val, (int, float)) and val > 0:
            return False
    return True


def _clean_thematic_file(rf: Path) -> tuple[int, int]:
    """Clean one thematic research.jsonl. Returns (removed, kept)."""
    records = read_jsonl(rf)
    original_count = len(records)
    cleaned = []
    removed_layers = []
    for rec in records:
        layer = rec.get("layer", "")
        sub = rec.get("sub_topic", "")
        if is_entry_empty(rec):
            removed_layers.append(f"{sub}|{layer}")
        else:
            cleaned.append(rec)
    removed = original_count - len(cleaned)
    if removed > 0:
        write_jsonl(rf, cleaned)
        tprint(f"  {rf.parent.name}: removed {removed}/{original_count} empty entries")
        for rl in removed_layers[:5]:
            tprint(f"    - {rl}")
        if len(removed_layers) > 5:
            tprint(f"    ... and {len(removed_layers) - 5} more")
    return removed, len(cleaned)


def _clean_asset_file(rf: Path) -> tuple[int, int]:
    """Clean one asset research.jsonl. Returns (removed, kept)."""
    records = read_jsonl(rf)
    original_count = len(records)
    cleaned = []
    for rec in records:
        if is_entry_empty(rec):
            pass  # remove
        else:
            cleaned.append(rec)
    removed = original_count - len(cleaned)
    if removed > 0:
        write_jsonl(rf, cleaned)
        tprint(f"  {rf.parent.name}: removed {removed}/{original_count} empty entries")
    return removed, len(cleaned)


def clean_broken_entries():
    """Remove empty entries from thematic and asset JSONL files."""
    tprint("=" * 70)
    tprint("STEP 1: Clean broken/empty entries")
    tprint("=" * 70)

    total_removed = 0
    total_kept = 0

    # Clean thematic research
    thematic_dir = OUTPUT_DIR / "thematic"
    if thematic_dir.exists():
        for rf in thematic_dir.glob("*/research.jsonl"):
            removed, kept = _clean_thematic_file(rf)
            total_removed += removed
            total_kept += kept

    # Clean asset research
    assets_dir = OUTPUT_DIR / "assets"
    if assets_dir.exists():
        for rf in assets_dir.glob("*/research.jsonl"):
            removed, kept = _clean_asset_file(rf)
            total_removed += removed
            total_kept += kept

    tprint(f"Cleaning done: removed {total_removed} empty entries, kept {total_kept}")
    return total_removed


# ─── Step 2: Audit what's missing ────────────────────────────────────────────

def _audit_thematic_dir(td: Path, expected_layers: list[str]) -> int:
    """Count missing layer entries for one thematic dir. Returns missing count."""
    rf = td / "research.jsonl"
    if not rf.exists():
        return 0
    records = read_jsonl(rf)
    subs = set()
    done = set()
    for rec in records:
        st = rec.get("sub_topic", "")
        layer = rec.get("layer", "")
        if st:
            subs.add(st)
        if st and layer:
            done.add(f"{st}|{layer}")
    missing = []
    for st in subs:
        for lyr in expected_layers:
            if f"{st}|{lyr}" not in done:
                missing.append(f"{st}|{lyr}")
    if missing:
        tprint(f"  {td.name}: {len(missing)} missing layers across {len(subs)} sub-topics")
        return len(missing)
    return 0


def _audit_thematic_gaps() -> int:
    """Total missing thematic layer entries across all dirs."""
    thematic_dir = OUTPUT_DIR / "thematic"
    expected_layers = [
        "L1_survey", "L2_extract", "L3_perspectives", "L4_adversarial",
        "L5_academic", "L6_gap_r1", "L7_contradictions", "L8_temporal",
        "L9_counter", "L10_synthesis"
    ]
    thematic_missing = 0
    if thematic_dir.exists():
        for td in sorted(thematic_dir.iterdir()):
            thematic_missing += _audit_thematic_dir(td, expected_layers)
    return thematic_missing


def _audit_asset_dir(ad: Path, expected_angles: list[str],
                     without_synthesis: list[str], without_adversarial: list[str]) -> int:
    """Count missing angle entries for one asset dir; append names to gap lists."""
    rf = ad / "research.jsonl"
    if not rf.exists():
        return 0
    records = read_jsonl(rf)
    done = set()
    for rec in records:
        a = rec.get("angle") or rec.get("pass") or rec.get("layer")
        if a:
            done.add(a)
    asset_missing = 0
    for ang in expected_angles:
        if ang not in done:
            asset_missing += 1
    if "synthesis" not in done:
        without_synthesis.append(ad.name)
    if "adversarial_verify" not in done:
        without_adversarial.append(ad.name)
    return asset_missing


def _audit_asset_gaps() -> tuple[int, list[str], list[str]]:
    """Returns (asset_missing, assets_without_synthesis, assets_without_adversarial)."""
    assets_dir = OUTPUT_DIR / "assets"
    expected_angles = ["history", "architecture", "culture", "tourism", "community", "sensory", "etymology"]
    asset_missing = 0
    assets_without_synthesis: list[str] = []
    assets_without_adversarial: list[str] = []
    if assets_dir.exists():
        for ad in sorted(assets_dir.iterdir()):
            asset_missing += _audit_asset_dir(
                ad, expected_angles, assets_without_synthesis, assets_without_adversarial)
    return asset_missing, assets_without_synthesis, assets_without_adversarial


def _audit_crosslink_count() -> int:
    """Count assets present in the crosslink confidence matrix."""
    matrix_file = OUTPUT_DIR / "crosslink" / "confidence_matrix.csv"
    matrix_count = 0
    if matrix_file.exists():
        matrix_count = len(matrix_file.read_text(encoding="utf-8").strip().split("\n")) - 1
    return matrix_count


def audit_gaps():
    """Report exactly what needs to be re-run."""
    tprint("=" * 70)
    tprint("AUDIT: What's missing?")
    tprint("=" * 70)

    thematic_missing = _audit_thematic_gaps()
    asset_missing, assets_without_synthesis, assets_without_adversarial = _audit_asset_gaps()
    matrix_count = _audit_crosslink_count()

    tprint("\nSUMMARY:")
    tprint(f"  Thematic: {thematic_missing} missing layer entries")
    tprint(f"  Assets: {asset_missing} missing angle entries")
    tprint(f"  Assets without adversarial: {len(assets_without_adversarial)}")
    tprint(f"  Assets without synthesis: {len(assets_without_synthesis)}")
    tprint(f"  Crosslink matrix: {matrix_count}/62 assets")

    return {
        "thematic_missing": thematic_missing,
        "asset_missing": asset_missing,
        "assets_no_adversarial": len(assets_without_adversarial),
        "assets_no_synthesis": len(assets_without_synthesis),
        "crosslink_missing": 62 - matrix_count,
    }


def main():
    ap = argparse.ArgumentParser(description="Research Repair & Deep-Fill")
    ap.add_argument("--clean-only", action="store_true", help="Only clean broken entries, don't re-run")
    ap.add_argument("--audit-only", action="store_true", help="Only audit gaps, don't fix")
    ap.add_argument("--all", action="store_true", help="Clean + re-run all missing phases")
    ap.add_argument("--phase", type=int, choices=[1, 2, 3], help="Re-run specific phase")
    ap.add_argument("--rps", type=float, default=1.0, help="Max requests/sec (default: 1.0 for safety)")
    ap.add_argument("--concurrent", type=int, default=2, help="Parallel workers (default: 2 for safety)")
    ap.add_argument("--model", type=str, default="cx/gpt-5.5")
    args = ap.parse_args()

    if not any([args.clean_only, args.audit_only, args.all, args.phase]):
        ap.print_help()
        return

    start = time.time()

    # Step 1: Audit current state
    gaps = audit_gaps()

    if args.audit_only:
        return

    # Step 2: Clean broken entries
    clean_broken_entries()

    if args.clean_only:
        tprint("\nRe-audit after cleaning:")
        audit_gaps()
        return

    # Step 3: Re-audit after cleaning
    tprint("\nRe-audit after cleaning:")
    gaps = audit_gaps()

    if gaps["thematic_missing"] == 0 and gaps["asset_missing"] == 0 and gaps["assets_no_adversarial"] == 0 and gaps["assets_no_synthesis"] == 0 and gaps["crosslink_missing"] == 0:
        tprint("\n✓ Nothing to repair!")
        return

    # Step 4: Import and run the engine phases
    _run_repair(args, gaps, start)


def _select_phases(args, gaps) -> list[int]:
    """Decide which phases to run based on args and gaps."""
    phases_to_run = []
    if args.all:
        if gaps["thematic_missing"] > 0:
            phases_to_run.append(1)
        if gaps["asset_missing"] > 0 or gaps["assets_no_adversarial"] > 0 or gaps["assets_no_synthesis"] > 0:
            phases_to_run.append(2)
        phases_to_run.append(3)  # always rebuild crosslink
    elif args.phase:
        phases_to_run = [args.phase]
    return phases_to_run


def _execute_phases(phases_to_run, corpus, llm, args, engine):
    """Run the selected engine phases in order."""
    if 1 in phases_to_run:
        tprint("\n>>> PHASE 1: Repairing thematic research (missing layers only)")
        engine["run_thematic_ultra"](corpus, llm, concurrent_themes=args.concurrent,
                                     concurrent_subs=max(1, args.concurrent // 2))
        engine["run_cross_pollination"](llm)

    if 2 in phases_to_run:
        tprint("\n>>> PHASE 2: Repairing asset research (missing angles/adversarial/synthesis)")
        engine["run_asset_ultra"](corpus, llm, concurrent=args.concurrent)

    if 3 in phases_to_run:
        tprint("\n>>> PHASE 3: Rebuilding crosslink matrix (all 62 assets)")
        engine["run_crosslink_ultra"](corpus, llm, concurrent=min(4, args.concurrent))


def _save_repair_usage(elapsed, phases_to_run, gaps, llm):
    """Persist repair usage stats to repair_usage.json."""
    with open(OUTPUT_DIR / "repair_usage.json", "w", encoding="utf-8") as f:
        json.dump({
            "run_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_s": round(elapsed),
            "elapsed_h": round(elapsed / 3600, 1),
            "phases": phases_to_run,
            "gaps_before": gaps,
            **llm.stats()
        }, f, ensure_ascii=False, indent=2)


def _run_repair(args, gaps, start):
    """Import engine, load corpus, run selected phases, and save usage."""
    tprint("\n" + "=" * 70)
    tprint("REPAIR: Re-running missing phases with conservative rate limits")
    tprint(f"Model: {args.model} | RPS: {args.rps} | Concurrent: {args.concurrent}")
    tprint("=" * 70)

    from agent.scripts.research_engine import (
        LLMClient, read_jsonl as engine_read_jsonl,
        run_thematic_ultra, run_cross_pollination,
        run_asset_ultra, run_crosslink_ultra
    )

    llm = LLMClient(model=args.model, rps=args.rps)
    if not llm.available:
        tprint("[WARN] LLM not available — set LLM_API_KEY and LLM_BASE_URL")
        return

    # Load corpus
    cf = OUTPUT_DIR / "corpus" / "full_corpus.jsonl"
    if cf.exists():
        corpus = engine_read_jsonl(cf)
        tprint(f"Loaded corpus: {len(corpus)} sources")
    else:
        tprint("[ERROR] No corpus found — run full pipeline first")
        return

    phases_to_run = _select_phases(args, gaps)
    engine = {
        "run_thematic_ultra": run_thematic_ultra,
        "run_cross_pollination": run_cross_pollination,
        "run_asset_ultra": run_asset_ultra,
        "run_crosslink_ultra": run_crosslink_ultra,
    }
    _execute_phases(phases_to_run, corpus, llm, args, engine)

    elapsed = time.time() - start
    tprint(f"\n{'=' * 70}")
    tprint(f"REPAIR COMPLETE — {elapsed:.0f}s ({elapsed / 3600:.1f}h) — {json.dumps(llm.stats())}")

    _save_repair_usage(elapsed, phases_to_run, gaps, llm)

    # Final audit
    tprint("\nFINAL AUDIT:")
    audit_gaps()


if __name__ == "__main__":
    main()
