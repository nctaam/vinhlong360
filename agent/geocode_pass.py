"""
Geocode pass: bổ sung GPS từ OSM Nominatim cho entities thiếu coords.
Chạy: python agent/geocode_pass.py
Có thể chạy song song với server (chỉ đọc data.json, ghi checkpoint riêng).
Ghi kết quả vào agent/geocode_results.json, import sau bằng --apply.
"""
import json, sys, time, os, logging, re, unicodedata
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON = ROOT / "web" / "data.json"
OUT = Path(__file__).resolve().parent / "geocode_results.json"
LOG_FILE = Path(__file__).resolve().parent / "geocode.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

CHECKPOINT_EVERY = 10
RATE_LIMIT_SLEEP = 1.0   # 1s between entities
BETWEEN_QUERY_SLEEP = 1.0
RETRY_SLEEP = 3.0

def _strip_diacritics(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"đ", "d", text, flags=re.IGNORECASE)
    return text


def geocode_photon(query: str, retries: int = 2):
    """Photon geocoder (komoot.io) — OSM-based, no API key, generous rate limit."""
    try:
        import httpx
    except ImportError:
        return None
    # Strip diacritics: Photon URL encoding issues with Vietnamese chars
    query = _strip_diacritics(query)
    # Ensure "Vietnam" in query so results are scoped
    if "vietnam" not in query.lower():
        query = query + ", Vietnam"
    for attempt in range(retries):
        try:
            r = httpx.get(
                "https://photon.komoot.io/api/",
                params={"q": query, "limit": 5},
                headers={"User-Agent": "vinhlong360-geocode/1.0"},
                timeout=12,
            )
            if r.status_code == 429:
                time.sleep(30)
                continue
            if r.status_code == 200:
                data = r.json()
                feats = data.get("features", [])
                # Filter to Vietnam (lon ~102-110, lat ~8-24)
                for feat in feats:
                    c = feat["geometry"]["coordinates"]
                    lon, lat = float(c[0]), float(c[1])
                    if 102 <= lon <= 110 and 8 <= lat <= 24:
                        return [lat, lon]
                return None
        except Exception as e:
            log.warning(f"photon attempt {attempt+1}: {e}")
            time.sleep(RETRY_SLEEP)
    return None


def geocode_nominatim(query: str, retries: int = 2):
    """Nominatim fallback — strict 1req/s limit, use sparingly."""
    try:
        import httpx
    except ImportError:
        return None
    for attempt in range(retries):
        try:
            r = httpx.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": query, "format": "json", "limit": 1, "countrycodes": "vn"},
                headers={"User-Agent": "vinhlong360-geocode/1.0 contact:admin@vinhlong360.vn"},
                timeout=12,
            )
            if r.status_code == 429:
                wait = 60 * (attempt + 1)
                log.warning(f"Nominatim 429 — sleeping {wait}s")
                time.sleep(wait)
                continue
            if r.status_code == 200:
                data = r.json()
                if data:
                    d = data[0]
                    return [float(d["lat"]), float(d["lon"])]
                return None
        except Exception as e:
            log.warning(f"nominatim attempt {attempt+1}: {e}")
            time.sleep(RETRY_SLEEP)
    return None


def geocode_with_fallback(queries: list) -> list | None:
    """Try Photon for each query strategy. No Nominatim (currently rate-limited)."""
    for q in queries:
        coords = geocode_photon(q)
        if coords:
            return coords
        time.sleep(BETWEEN_QUERY_SLEEP)
    return None


def save_checkpoint(results: dict):
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(OUT)


def main():
    apply = "--apply" in sys.argv

    log.info("═══ Geocode Pass vinhlong360 ═══")

    with open(DATA_JSON, encoding="utf-8") as f:
        data = json.load(f)

    # Load existing checkpoint
    existing_results: dict = {}
    if OUT.exists():
        with open(OUT, encoding="utf-8") as f:
            existing_results = json.load(f)
        log.info(f"Loaded {len(existing_results)} existing geocode results")

    if apply:
        updated = 0
        for e in data["entities"]:
            if e["id"] in existing_results:
                e["coords"] = existing_results[e["id"]]
                updated += 1
        with open(DATA_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info(f"Applied {updated} GPS coords to data.json")
        return

    # Filter entities missing coords AND not already in checkpoint
    missing = [
        e for e in data["entities"]
        if not (e.get("coords") or e.get("coordinates"))
        and e["id"] not in existing_results
    ]
    total_already_done = len(existing_results)
    log.info(f"Entities thiếu GPS: {len(missing)} chưa geocode / {len(data['entities'])} total")
    log.info(f"Checkpoint hiện tại: {total_already_done} đã có kết quả")

    if not missing:
        log.info("Không còn entity nào cần geocode!")
        return

    results = dict(existing_results)
    success = 0
    fail = 0

    for i, e in enumerate(missing):
        eid = e["id"]
        name = e.get("name", "")
        attrs = e.get("attributes") or {}
        addr = attrs.get("address", "")
        district = attrs.get("district", "")
        province = attrs.get("province_old", "Vĩnh Long")

        queries = []
        if addr and len(addr) > 10:
            queries.append(f"{name}, {addr}, Việt Nam")
        if district:
            queries.append(f"{name}, {district}, {province}, Việt Nam")
        queries.append(f"{name}, {province}, Việt Nam")
        if name:
            queries.append(f"{name}, Vietnam")

        coords = geocode_with_fallback(queries)

        if coords:
            results[eid] = coords
            success += 1
            log.info(f"[{i+1}/{len(missing)}] OK  {name[:40]} → {coords}")
        else:
            fail += 1
            log.info(f"[{i+1}/{len(missing)}] FAIL {name[:40]}")

        # Save checkpoint every N entities
        if (i + 1) % CHECKPOINT_EVERY == 0:
            save_checkpoint(results)
            log.info(f"  Checkpoint saved: {len(results)} total | +{success} ok / {fail} fail this run")

        time.sleep(RATE_LIMIT_SLEEP)

    # Final save
    save_checkpoint(results)
    log.info(f"\nGeocoding xong: {success} tìm được, {fail} thất bại")
    log.info(f"Total checkpoint: {len(results)} entries")
    log.info(f"Kết quả lưu tại: {OUT}")
    log.info("Chạy với --apply để import vào data.json (cần stop server trước)")


if __name__ == "__main__":
    main()
