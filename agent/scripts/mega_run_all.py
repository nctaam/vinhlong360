#!/usr/bin/env python3
"""MEGA RUN ALL — Master orchestrator that runs ALL research scripts sequentially.

CRITICAL: Only 1 script can use the proxy at a time (concurrency limit).
This script runs them one after another, logging progress.

Usage:
  python -u agent/scripts/mega_run_all.py 2>&1

Skips scripts that are already 100% done (via resume logic in each script).
"""
import os, subprocess, sys, time
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

SCRIPTS_DIR = Path(__file__).resolve().parent
SCRIPTS = [
    # === PHASE 1: Topic-level research (199 topics, ~5h) ===
    ("mega_expert_run.py",      "Expert research (46 topics, 15 categories)"),
    ("mega_persona_run.py",     "Persona journeys, comparisons, hidden gems (68 topics)"),
    ("mega_ultradeep_run.py",   "Ultra-deep: medicine, waterways, archaeology, crafts... (50 topics)"),
    ("mega_narrative_run.py",   "Narratives: essays, food stories, seasonal guides (35 topics)"),
    # === PHASE 2: More topic-level (85 topics, ~2h) ===
    ("mega_itinerary_run.py",   "Itineraries: 45+ detailed trip plans, all durations/themes (45 topics)"),
    ("mega_practical_run.py",   "Practical guides: transport, money, safety, shopping (40 topics)"),
    # === PHASE 3: Entity-level (VERY LONG — 1500+ calls, ~25h+) ===
    ("mega_entity_deep.py --mode all", "Per-entity deep analysis (~1000+ entities)"),
    ("mega_seo_run.py",         "SEO content for all 1816 entities in batches of 5"),
]


def run_script(name, desc):
    parts = name.split()
    script_path = str(SCRIPTS_DIR / parts[0])
    args = parts[1:] if len(parts) > 1 else []

    print(f"\n{'='*60}", flush=True)
    print(f"▶ {desc}", flush=True)
    print(f"  Script: {name}", flush=True)
    print(f"  Started: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"{'='*60}", flush=True)

    t0 = time.time()
    result = subprocess.run(
        [sys.executable, "-u", script_path] + args,
        cwd=str(SCRIPTS_DIR.parent.parent),
        timeout=7200,  # 2h max per script
    )
    elapsed = (time.time() - t0) / 60

    status = "✓ SUCCESS" if result.returncode == 0 else f"✗ FAILED (exit {result.returncode})"
    print(f"\n{status} — {name} ({elapsed:.1f}m)", flush=True)
    return result.returncode == 0


def main():
    print(f"═══ MEGA RUN ALL ═══", flush=True)
    print(f"  Scripts: {len(SCRIPTS)}", flush=True)
    print(f"  Started: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)

    t0 = time.time()
    results = []

    for name, desc in SCRIPTS:
        try:
            ok = run_script(name, desc)
            results.append((name, ok))
        except subprocess.TimeoutExpired:
            print(f"  ✗ TIMEOUT: {name}", flush=True)
            results.append((name, False))
        except Exception as e:
            print(f"  ✗ ERROR: {name} — {e}", flush=True)
            results.append((name, False))

    total_min = (time.time() - t0) / 60
    print(f"\n{'='*60}", flush=True)
    print(f"═══ ALL DONE ({total_min:.1f}m) ═══", flush=True)
    for name, ok in results:
        print(f"  {'✓' if ok else '✗'} {name}", flush=True)


if __name__ == "__main__":
    main()
