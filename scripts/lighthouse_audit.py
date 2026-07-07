"""
Run Lighthouse audit and report Core Web Vitals.

Requires the Lighthouse CLI (npm package 'lighthouse').
Parses JSON output for LCP, INP (FID), CLS, and overall performance score.
Reports pass/fail against configurable thresholds.

Usage:
    python scripts/lighthouse_audit.py                              # audit localhost:3000
    python scripts/lighthouse_audit.py --url https://vinhlong360.vn # audit production
    python scripts/lighthouse_audit.py --json --output report.json  # save JSON report
    python scripts/lighthouse_audit.py --lcp-threshold 3000         # custom threshold
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

# Default thresholds (Google CWV "good" thresholds)
DEFAULT_LCP_MS = 2500       # Largest Contentful Paint (ms)
DEFAULT_CLS = 0.1           # Cumulative Layout Shift
DEFAULT_PERF_SCORE = 80     # Performance score (0-100)
DEFAULT_INP_MS = 200        # Interaction to Next Paint (ms)


def _find_lighthouse() -> str | None:
    """Find the lighthouse CLI binary."""
    # Check PATH
    lh = shutil.which("lighthouse")
    if lh:
        return lh

    # Check common npx locations
    npx = shutil.which("npx")
    if npx:
        # Verify lighthouse is available via npx
        try:
            result = subprocess.run(
                [npx, "lighthouse", "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return f"{npx}|lighthouse"  # special marker for npx invocation
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return None


def _run_lighthouse(
    lighthouse_cmd: str,
    url: str,
    output_path: str,
) -> bool:
    """Run lighthouse and save JSON report. Returns True on success."""
    if "|" in lighthouse_cmd:
        # npx invocation
        npx, pkg = lighthouse_cmd.split("|", 1)
        cmd = [
            npx, pkg,
            url,
            "--output=json",
            f"--output-path={output_path}",
            "--chrome-flags=--headless --no-sandbox --disable-gpu",
            "--quiet",
        ]
    else:
        cmd = [
            lighthouse_cmd,
            url,
            "--output=json",
            f"--output-path={output_path}",
            "--chrome-flags=--headless --no-sandbox --disable-gpu",
            "--quiet",
        ]

    print(f"[lighthouse] running audit on {url} ...")
    print("[lighthouse] this may take 30-60 seconds")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            print(f"[lighthouse] WARNING: lighthouse exited with code {result.returncode}", file=sys.stderr)
            if result.stderr:
                # Only print last few lines of stderr (lighthouse is verbose)
                stderr_lines = result.stderr.strip().splitlines()
                for line in stderr_lines[-5:]:
                    print(f"  {line}", file=sys.stderr)
            # Still try to parse output (lighthouse sometimes exits non-zero but produces valid output)
        return True
    except subprocess.TimeoutExpired:
        print("[lighthouse] FAILED: audit timed out after 300s", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("[lighthouse] FAILED: lighthouse binary not found during execution", file=sys.stderr)
        return False


def _extract_cwv(report: dict) -> dict:
    """Extract Core Web Vitals from a Lighthouse JSON report."""
    audits = report.get("audits", {})
    categories = report.get("categories", {})

    def _get_numeric(audit_id: str) -> float | None:
        audit = audits.get(audit_id, {})
        val = audit.get("numericValue")
        if val is not None:
            return float(val)
        return None

    cwv: dict = {}

    # Performance score (0-1 in report, display as 0-100)
    perf = categories.get("performance", {})
    score = perf.get("score")
    cwv["performance_score"] = round(score * 100) if score is not None else None

    # LCP (Largest Contentful Paint) in ms
    cwv["lcp_ms"] = _get_numeric("largest-contentful-paint")

    # CLS (Cumulative Layout Shift)
    cwv["cls"] = _get_numeric("cumulative-layout-shift")

    # INP / FID (Interaction to Next Paint replaces FID)
    # Try INP first, fallback to FID (older Lighthouse versions)
    inp = _get_numeric("interaction-to-next-paint")
    if inp is None:
        inp = _get_numeric("max-potential-fid")
    cwv["inp_ms"] = inp

    # Additional useful metrics
    cwv["fcp_ms"] = _get_numeric("first-contentful-paint")
    cwv["si_ms"] = _get_numeric("speed-index")
    cwv["tti_ms"] = _get_numeric("interactive")
    cwv["tbt_ms"] = _get_numeric("total-blocking-time")

    return cwv


def _check_thresholds(
    cwv: dict,
    lcp_threshold: float,
    cls_threshold: float,
    perf_threshold: float,
    inp_threshold: float,
) -> list[dict]:
    """Check CWV values against thresholds. Returns list of failures."""
    failures: list[dict] = []

    if cwv["lcp_ms"] is not None and cwv["lcp_ms"] > lcp_threshold:
        failures.append({
            "metric": "LCP",
            "value": cwv["lcp_ms"],
            "threshold": lcp_threshold,
            "unit": "ms",
        })

    if cwv["cls"] is not None and cwv["cls"] > cls_threshold:
        failures.append({
            "metric": "CLS",
            "value": cwv["cls"],
            "threshold": cls_threshold,
            "unit": "",
        })

    if cwv["performance_score"] is not None and cwv["performance_score"] < perf_threshold:
        failures.append({
            "metric": "Performance Score",
            "value": cwv["performance_score"],
            "threshold": perf_threshold,
            "unit": "/100",
            "direction": "below",
        })

    if cwv["inp_ms"] is not None and cwv["inp_ms"] > inp_threshold:
        failures.append({
            "metric": "INP",
            "value": cwv["inp_ms"],
            "threshold": inp_threshold,
            "unit": "ms",
        })

    return failures


def _format_ms(val: float | None) -> str:
    if val is None:
        return "N/A"
    if val >= 1000:
        return f"{val / 1000:.2f}s"
    return f"{val:.0f}ms"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Lighthouse audit and report Core Web Vitals."
    )
    parser.add_argument(
        "--url",
        default="http://localhost:3000",
        help="URL to audit (default: http://localhost:3000)",
    )
    parser.add_argument(
        "--output",
        default="",
        help="save full Lighthouse JSON report to this file",
    )
    parser.add_argument(
        "--lcp-threshold",
        type=float,
        default=DEFAULT_LCP_MS,
        help=f"LCP threshold in ms (default: {DEFAULT_LCP_MS})",
    )
    parser.add_argument(
        "--cls-threshold",
        type=float,
        default=DEFAULT_CLS,
        help=f"CLS threshold (default: {DEFAULT_CLS})",
    )
    parser.add_argument(
        "--perf-threshold",
        type=float,
        default=DEFAULT_PERF_SCORE,
        help=f"performance score threshold 0-100 (default: {DEFAULT_PERF_SCORE})",
    )
    parser.add_argument(
        "--inp-threshold",
        type=float,
        default=DEFAULT_INP_MS,
        help=f"INP threshold in ms (default: {DEFAULT_INP_MS})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="output CWV results as JSON",
    )
    args = parser.parse_args()

    # --- Check lighthouse CLI ---
    lh_cmd = _find_lighthouse()
    if lh_cmd is None:
        print(
            "[lighthouse] ERROR: Lighthouse CLI not found.\n"
            "\n"
            "Install via npm:\n"
            "  npm install -g lighthouse\n"
            "\n"
            "Or use npx (no install):\n"
            "  npx lighthouse <url> --output=json\n"
            "\n"
            "Requires Google Chrome / Chromium to be installed.\n",
            file=sys.stderr,
        )
        return 1

    # --- Run Lighthouse ---
    # Use a temp file if no output specified
    if args.output:
        report_path = args.output
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        report_path = tmp.name
        tmp.close()

    try:
        ok = _run_lighthouse(lh_cmd, args.url, report_path)
        if not ok:
            return 1

        if not os.path.exists(report_path):
            print(f"[lighthouse] ERROR: report file not created at {report_path}", file=sys.stderr)
            return 1

        with open(report_path, encoding="utf-8") as f:
            report = json.load(f)

    except json.JSONDecodeError as exc:
        print(f"[lighthouse] ERROR: failed to parse report JSON: {exc}", file=sys.stderr)
        return 1
    finally:
        # Clean up temp file
        if not args.output and os.path.exists(report_path):
            os.unlink(report_path)

    # --- Extract and check CWV ---
    cwv = _extract_cwv(report)
    failures = _check_thresholds(
        cwv,
        args.lcp_threshold,
        args.cls_threshold,
        args.perf_threshold,
        args.inp_threshold,
    )

    result = {
        "url": args.url,
        "cwv": cwv,
        "thresholds": {
            "lcp_ms": args.lcp_threshold,
            "cls": args.cls_threshold,
            "performance_score": args.perf_threshold,
            "inp_ms": args.inp_threshold,
        },
        "failures": failures,
        "passed": len(failures) == 0,
    }

    # --- Output ---
    if args.json_output:
        print(json.dumps(result, indent=2))
    else:
        overall = "PASS" if result["passed"] else "FAIL"
        print(f"[lighthouse] Core Web Vitals audit: {overall}")
        print(f"  URL: {args.url}")
        print()

        # Table header
        print(f"  {'Metric':<22} {'Value':>10} {'Threshold':>12} {'Status':>8}")
        print(f"  {'─' * 22} {'─' * 10} {'─' * 12} {'─' * 8}")

        # Performance score
        perf = cwv.get("performance_score")
        perf_status = "FAIL" if any(f["metric"] == "Performance Score" for f in failures) else "PASS"
        print(f"  {'Performance Score':<22} {str(perf or 'N/A'):>10} {f'>={args.perf_threshold:.0f}':>12} {perf_status:>8}")

        # LCP
        lcp_status = "FAIL" if any(f["metric"] == "LCP" for f in failures) else "PASS"
        print(f"  {'LCP':<22} {_format_ms(cwv.get('lcp_ms')):>10} {f'<={args.lcp_threshold:.0f}ms':>12} {lcp_status:>8}")

        # CLS
        cls_val = cwv.get("cls")
        cls_str = f"{cls_val:.3f}" if cls_val is not None else "N/A"
        cls_status = "FAIL" if any(f["metric"] == "CLS" for f in failures) else "PASS"
        print(f"  {'CLS':<22} {cls_str:>10} {f'<={args.cls_threshold}':>12} {cls_status:>8}")

        # INP
        inp_status = "FAIL" if any(f["metric"] == "INP" for f in failures) else "PASS"
        print(f"  {'INP':<22} {_format_ms(cwv.get('inp_ms')):>10} {f'<={args.inp_threshold:.0f}ms':>12} {inp_status:>8}")

        # Additional metrics (no thresholds, info only)
        print()
        print("  Additional metrics:")
        print(f"    FCP:   {_format_ms(cwv.get('fcp_ms'))}")
        print(f"    SI:    {_format_ms(cwv.get('si_ms'))}")
        print(f"    TTI:   {_format_ms(cwv.get('tti_ms'))}")
        print(f"    TBT:   {_format_ms(cwv.get('tbt_ms'))}")

        if failures:
            print()
            print(f"  {len(failures)} metric(s) failed thresholds.")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
