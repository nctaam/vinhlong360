"""
vinhlong360 — Learn NOW (one-shot learning burst).

Chạy NGAY toàn bộ chuỗi tự học, không chờ lịch scheduler — dùng khi muốn
"học nhanh nhất có thể" tại một thời điểm:

  1. continuous-discovery  : GPT 9router tìm site mới (1 chủ đề xoay vòng) + OSM geocode
  2. learning-loop         : feedback → gap learning → enrichment → backfill coords
  3. kb-promotion          : thăng hạng entity provisional đã chứng tỏ hữu ích

Tất cả đều qua guarded_evolve (eval-gated, auto-rollback). An toàn chạy lặp.

Chạy:
  python agent/learn_now.py             # 1 burst đầy đủ
  python agent/learn_now.py --rounds 3  # 3 vòng liên tiếp (3 chủ đề discovery)
"""

import argparse
import os
import sys
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(AGENT_DIR))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(AGENT_DIR.parent / ".env")


def burst(round_no: int):
    print("=" * 64)
    print(f"  LEARN NOW — burst #{round_no}")
    print("=" * 64)

    from self_evolve import guarded_evolve

    # 1. Discovery (next topic in rotation)
    try:
        import discover_province as dp
        s = guarded_evolve("learn-now:discovery", lambda: dp.run_next_rotation(workers=4, apply=True))
        res = s.get("change_result") or {}
        added = res.get("added", "?") if isinstance(res, dict) else "?"
        print(f"  [1/3] discovery   : {s['decision']} | topic={res.get('topic','?') if isinstance(res,dict) else '?'} | +{added} entities")
    except Exception as e:
        print(f"  [1/3] discovery   : ERROR {e}")

    # 2. Learning loop (feedback + gaps + enrichment + geocode backfill)
    try:
        from learn_loop import run_full_cycle
        s = guarded_evolve("learn-now:loop", lambda: run_full_cycle(dry_run=False))
        res = s.get("change_result") or {}
        if isinstance(res, dict):
            print(f"  [2/3] learn-loop  : {s['decision']} | gaps+{res.get('gap_learning',{}).get('entities_added',0)} "
                  f"enrich {res.get('enrichment',{}).get('enriched',0)} "
                  f"geocode {res.get('geocoding',{}).get('geocoded',0)}")
        else:
            print(f"  [2/3] learn-loop  : {s['decision']}")
    except Exception as e:
        print(f"  [2/3] learn-loop  : ERROR {e}")

    # 3. Promotion (provisional → verified for proven entities)
    try:
        import kb_curation
        s = guarded_evolve("learn-now:promotion", lambda: kb_curation.auto_promote_pass(min_hits=3))
        res = s.get("change_result") or {}
        promoted = len(res.get("promoted", [])) if isinstance(res, dict) else "?"
        print(f"  [3/3] promotion   : {s['decision']} | promoted {promoted}")
    except Exception as e:
        print(f"  [3/3] promotion   : ERROR {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="One-shot learning burst")
    ap.add_argument("--rounds", type=int, default=1, help="số burst liên tiếp (mỗi burst 1 chủ đề discovery)")
    args = ap.parse_args()
    for i in range(1, max(1, args.rounds) + 1):
        burst(i)
    print("\nDone. Review queue: GET /admin/provisional")
