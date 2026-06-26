"""
vinhlong360 — Province-wide Continuous Discovery (multi-topic, multi-stream, LLM + OSM).

Đẩy 1 lệnh để agent tự học LIÊN TỤC, NHIỀU LUỒNG SONG SONG, dữ liệu về:
  - du lịch (điểm/khu du lịch, di tích, biển/cồn, lưu trú)
  - nông sản (trái cây, thủy sản, vùng trồng đặc sản)
  - sản phẩm OCOP (3–5 sao, chủ thể, làng nghề)
trên toàn tỉnh Vĩnh Long mới (Vĩnh Long cũ + Bến Tre + Trà Vinh).

Kiến trúc:
  - Lưới luồng = (3 vùng) × (các loại theo chủ đề) → ThreadPool song song.
  - Mỗi luồng: GPT 9router liệt kê mục CÓ THẬT → lọc ngoài tỉnh → dedup →
    geocode qua OSM (địa điểm: theo tên; nông sản/OCOP: theo vùng trồng) →
    entity provisional (toạ độ KHÔNG do GPT sinh).
  - Gộp → dedup chéo + vs KB → snapshot → ghi provisional → sync data.js + reload.

Chạy:
  # 1 vòng tất cả chủ đề
  python agent/discover_province.py --apply
  # chỉ vài chủ đề
  python agent/discover_province.py --apply --topics agri,ocop
  # CHẠY LIÊN TỤC (daemon), mỗi vòng cách nhau 1h, xoay vòng chủ đề
  python agent/discover_province.py --apply --loop --interval 3600
  # đổi model 9router
  python agent/discover_province.py --apply --model cx/gpt-5.5

Hoặc bật tự động qua scheduler: task "continuous-discovery" (xem scheduler.py).
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = AGENT_DIR.parent
sys.path.insert(0, str(AGENT_DIR))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / ".env")

from openai import OpenAI
import geocode as geo
import kb_curation
import kb_versioning

DATA = PROJECT_DIR / "web" / "data.json"
CURSOR_FILE = AGENT_DIR / "data" / "discovery_cursor.json"

LLM_KEY = os.environ.get("LLM_API_KEY", "")
LLM_URL = os.environ.get("LLM_BASE_URL", "")
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "cx/gpt-5.4")

REGIONS = [
    {"label": "Vĩnh Long (cũ)", "area": "vinh-long"},
    {"label": "Bến Tre (cũ)", "area": "ben-tre"},
    {"label": "Trà Vinh (cũ)", "area": "tra-vinh"},
]

# Topic → list of (category prompt, entity type)
TOPIC_SETS = {
    "tourism": [
        ("điểm/khu du lịch, danh thắng nổi tiếng", "attraction"),
        ("di tích lịch sử - văn hóa, chùa, đình, đền, miếu cổ", "history"),
        ("biển, cồn, cù lao, khu sinh thái miệt vườn", "nature"),
        ("homestay, resort, khu nghỉ dưỡng, lưu trú du lịch", "accommodation"),
    ],
    "agri": [
        ("trái cây đặc sản và vùng trồng nổi tiếng", "product"),
        ("nông sản chủ lực, thủy sản, đặc sản nông nghiệp", "product"),
    ],
    "ocop": [
        ("sản phẩm OCOP 3-5 sao tiêu biểu", "product"),
        ("làng nghề, chủ thể sản xuất đặc sản OCOP", "craft_village"),
    ],
}

# Types that are physical places (geocode by NAME) vs products (geocode by LOCATION)
PLACE_TYPES = {"attraction", "history", "nature", "accommodation", "event"}

# So khớp trên text ĐÃ bỏ dấu → keyword cũng phải ở dạng bỏ dấu (bug cũ:
# keyword có dấu không bao giờ khớp text đã _norm).
# OUTSIDE: chặn nếu xuất hiện trong tên HOẶC địa chỉ.
OUTSIDE = [
    "ninh kieu", "tien giang", "cai be", "my tho", "dong thap",
    "an giang", "soc trang", "hau giang", "kien giang", "bac lieu", "ca mau",
    "long an", "ho chi minh", "sai gon", "ha noi", "da nang", "hue",
    "nha trang", "da lat", "phu quoc", "vung tau",
]
# OUTSIDE_LOC: chỉ chặn khi nằm trong ĐỊA CHỈ (tên hợp lệ vẫn được nhắc tới
# láng giềng, vd "Cầu Cần Thơ" phía bờ Bình Minh - Vĩnh Long).
OUTSIDE_LOC = ["can tho"]


def _norm(s):
    s = unicodedata.normalize("NFD", (s or "").lower())
    return re.sub(r"[̀-ͯ]", "", s).replace("đ", "d")


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", _norm(name)).strip("-")[:60]


def _client():
    return OpenAI(api_key=LLM_KEY, base_url=LLM_URL, timeout=30)


def _district_regions():
    """Build finer per-district regions from KB places' legacyArea (deeper sweep)."""
    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load district data: %s", exc)
        return REGIONS
    seen, out = set(), []
    for e in data["entities"]:
        if e.get("type") != "place":
            continue
        leg, area = e.get("legacyArea"), e.get("area")
        if leg and area and (leg, area) not in seen:
            seen.add((leg, area))
            out.append({"label": f"{leg} (tỉnh Vĩnh Long mới)", "area": area})
    return out or REGIONS


def discover_stream(region, category, etype, model):
    """One parallel stream → list of dicts (or [{'_error':...}])."""
    is_product = etype not in PLACE_TYPES
    loc_word = "vùng trồng/sản xuất (xã/huyện)" if is_product else "xã/phường + huyện"
    prompt = (
        f"Liệt kê các {category} CÓ THẬT và NỔI TIẾNG ở {region['label']} "
        f"(nay thuộc tỉnh Vĩnh Long mới, ĐBSCL Việt Nam). CHỈ liệt kê thứ có thật, không bịa. "
        f"Mỗi mục gồm tên đầy đủ, {loc_word}, và mô tả 1 câu.\n"
        f'Trả về DUY NHẤT một mảng JSON: '
        f'[{{"name":"...","location":"...","summary":"1 câu tiếng Việt"}}]. '
        f"Tối đa 15 mục. Không thêm chữ nào ngoài JSON."
    )
    try:
        resp = _client().chat.completions.create(
            model=model, messages=[{"role": "user", "content": prompt}],
            temperature=0.3, timeout=90)
        text = resp.choices[0].message.content or ""
    except Exception as e:
        return [{"_error": f"{region['area']}/{etype}: {e}"}]

    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []
    try:
        items = json.loads(m.group(0))
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("LLM returned invalid JSON for %s/%s: %s", region.get("area", "?"), etype, exc)
        return []

    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        name = (it.get("name") or "").strip()
        loc = (it.get("location") or "").strip()
        if len(name) < 4:
            continue
        if any(k in _norm(name + " " + loc) for k in OUTSIDE):
            continue
        if any(k in _norm(loc) for k in OUTSIDE_LOC):
            continue
        out.append({"name": name, "location": loc, "summary": (it.get("summary") or "").strip(),
                    "type": etype, "area": region["area"]})
    return out


def _place_for(area, location, places):
    """Trả ward khớp TÊN trong `location`; None nếu không khớp.

    KHÔNG dồn bừa vào ward đầu tiên của khu vực (lỗi cũ): fallback kiểu đó biến
    1 xã thành "thùng chứa" placeId sai (xem scripts/fix_placeid_buckets.py).
    Thà để placeId=None (chưa phân loại) còn hơn gán sai xã.
    """
    loc = _norm(location)
    for p in places:
        if p.get("area") != area:
            continue
        pn = _norm(p["name"]).replace("xa ", "").replace("phuong ", "")
        if pn and pn in loc:
            return p["id"]
    return None


def run_discovery(topics, regions, workers, model, apply, label="manual"):
    """Run one discovery round across the given topics × regions. Returns summary dict."""
    cats = []
    for t in topics:
        cats.extend(TOPIC_SETS.get(t, []))
    if not cats:
        return {"error": "no valid topics", "topics": topics}

    data = json.loads(DATA.read_text(encoding="utf-8"))
    places = [e for e in data["entities"] if e["type"] == "place"]
    existing_ids = {e["id"] for e in data["entities"]}

    streams = [(r, cat, et) for r in regions for (cat, et) in cats]
    found, errors = [], 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(discover_stream, r, cat, et, model) for (r, cat, et) in streams]
        for fut in as_completed(futs):
            res = fut.result()
            errors += sum(1 for x in res if x.get("_error"))
            found.extend([x for x in res if not x.get("_error")])

    # dedup within batch + vs KB (near-dup gate checks BOTH the KB and the
    # candidates already accepted this batch — fixes "Nhà xưa Cai Cường" vs
    # "Khu du lịch Nhà xưa Cai Cường" slipping through together)
    seen, unique, accepted_pseudo = set(), [], []
    for s in found:
        key = _norm(s["name"])
        if key in seen or _slug(s["name"]) in existing_ids:
            continue
        if kb_curation.find_near_duplicate(s["name"], s["type"],
                                           data["entities"] + accepted_pseudo):
            continue
        seen.add(key)
        s["id"] = _slug(s["name"])
        unique.append(s)
        accepted_pseudo.append({"id": s["id"], "name": s["name"], "type": s["type"]})

    # geocode: places by name, products by location (vùng trồng)
    geocoded = 0
    for s in unique:
        q = s["name"] if s["type"] in PLACE_TYPES else (s.get("location") or s["name"])
        c = geo.geocode(q, region=s.get("location") or "Vĩnh Long")
        if c:
            s["coords"] = c
            geocoded += 1

    summary = {"topics": topics, "raw": len(found), "errors": errors,
               "new": len(unique), "geocoded": geocoded, "seconds": round(time.time() - t0),
               "added": 0}

    if not apply:
        summary["sample"] = [{"name": s["name"], "type": s["type"],
                              "coords": s.get("coords")} for s in unique[:12]]
        return summary

    kb_versioning.snapshot(reason=f"discovery:{label}", snapshot_id="snap_discovery_latest")
    for s in unique:
        e = {"id": s["id"], "type": s["type"], "name": s["name"], "summary": s.get("summary", ""),
             "placeId": _place_for(s["area"], s.get("location", ""), places),
             "confidence": 0.45 if s.get("coords") else 0.35,
             "status": "provisional", "verified": False,
             "learned_at": datetime.now().strftime("%Y-%m-%d"),
             "updatedAt": datetime.now().strftime("%Y-%m-%d"),
             "attributes": {}, "season": None, "images": [],
             "source": {"title": f"agent discovery ({model}) + OSM geocode", "method": "llm+nominatim"}}
        if s.get("coords"):
            e["coords"] = s["coords"]
        data["entities"].append(e)
    summary["added"] = len(unique)

    tmp = DATA.with_suffix(".discover.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA)
    # GĐ-audit (B1): ghi entity mới vào DB (nguồn sự thật cho chat); data.json là working copy.
    try:
        from database import db
        for s in unique:
            ent = next((x for x in data["entities"] if x["id"] == s["id"]), None)
            if ent:
                db.upsert_entity(ent)  # upsert nhận alias "coords"->"coordinates"
    except Exception as exc:  # noqa: BLE001
        logger.warning("ghi DB that bai: %s", exc)
    try:
        import scheduler
        scheduler.sync_data_json_to_js()
        import knowledge
        knowledge.reload()
    except Exception as exc:
        logger.warning("Post-discover sync/reload failed: %s", exc)
    return summary


# ── Rotation cursor (for continuous mode) ──

_TOPIC_ORDER = ["tourism", "agri", "ocop"]


def _next_topic():
    """Return the next topic in rotation (persisted cursor)."""
    idx = 0
    try:
        if CURSOR_FILE.exists():
            idx = json.loads(CURSOR_FILE.read_text(encoding="utf-8")).get("idx", 0)
    except Exception as exc:
        logger.debug("Failed to read topic cursor: %s", exc)
        idx = 0
    topic = _TOPIC_ORDER[idx % len(_TOPIC_ORDER)]
    try:
        CURSOR_FILE.write_text(json.dumps({"idx": (idx + 1) % len(_TOPIC_ORDER)}), encoding="utf-8")
    except Exception as exc:
        logger.debug("Failed to write topic cursor: %s", exc)
    return topic


def run_next_rotation(workers=4, model=None, apply=True):
    """Run ONE rotation slice (next topic across all regions). Used by the scheduler
    for continuous, bounded auto-learning."""
    model = model or DEFAULT_MODEL
    topic = _next_topic()
    return {"topic": topic, **run_discovery([topic], REGIONS, workers, model, apply, label=topic)}


def main():
    ap = argparse.ArgumentParser(description="Continuous province-wide discovery")
    ap.add_argument("--topics", type=str, default="tourism,agri,ocop", help="comma list: tourism,agri,ocop")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--model", type=str, default=DEFAULT_MODEL)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--loop", action="store_true", help="run continuously")
    ap.add_argument("--interval", type=int, default=3600, help="seconds between rounds in --loop")
    ap.add_argument("--per-district", action="store_true", help="finer regions = each district (deeper sweep)")
    args = ap.parse_args()
    topics = [t.strip() for t in args.topics.split(",") if t.strip()]
    apply = args.apply and not args.dry_run
    regions = _district_regions() if args.per_district else REGIONS

    def one_round(rnd_topics, label):
        print("=" * 64)
        print(f"  Discovery [{label}] — model={args.model} workers={args.workers} "
              f"topics={rnd_topics} regions={len(regions)}")
        print("=" * 64)
        s = run_discovery(rnd_topics, regions, args.workers, args.model, apply, label=label)
        print(f"  raw={s.get('raw')} new={s.get('new')} geocoded={s.get('geocoded')} "
              f"added={s.get('added')} errors={s.get('errors')} ({s.get('seconds')}s)")
        if not apply and s.get("sample"):
            for x in s["sample"]:
                print(f"    - [{x['type']}] {x['name']} coords={x['coords']}")
        return s

    if args.loop:
        print(f"CONTINUOUS mode: rotating topics every {args.interval}s. Ctrl+C to stop.")
        rnd = 0
        while True:
            topic = _next_topic()
            one_round([topic], f"loop#{rnd}:{topic}")
            rnd += 1
            time.sleep(args.interval)
    else:
        one_round(topics, "manual")


if __name__ == "__main__":
    main()
