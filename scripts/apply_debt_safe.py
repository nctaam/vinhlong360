"""Sửa nợ dữ liệu AN-TOÀN (không bịa, không che lỗi). DRY-RUN mặc định; --apply để ghi.
  T1. Xoá ghost rác (prov-1, test) + mọi relationship/itinerary-stop trỏ tới chúng.
  T2. attributes.ward: drop nếu == placeId hiện tại (thừa); rename → legacy_ward nếu là
      tên xã ĐÃ GIẢI THỂ (không còn trong tập xã/phường hiện tại); GIỮ NGUYÊN nếu là
      một xã hiện tại KHÁC placeId (nghi placeId sai → để soát, KHÔNG tự xử).
  T3. NFC-normalize attributes.address (gộp khác-biệt do vị trí dấu: hoà/hoá...).
§B1: backup trước. Usage: python scripts/apply_debt_safe.py [--apply]
"""
import json, re, sys, unicodedata, collections
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT/"web/data.json"
APPLY = "--apply" in sys.argv
d = json.load(open(DATA, encoding="utf-8"))
ents = d["entities"]; rels = d["relationships"]; itins = d.get("itineraries", [])
byid = {e["id"]: e for e in ents}
stats = collections.Counter()

def A(e):
    a = e.get("attributes")
    if isinstance(a, str):
        try: a = json.loads(a)
        except (ValueError, json.JSONDecodeError): a = {}
    return a if isinstance(a, dict) else None  # None = không có/không phải dict → bỏ qua

def norm(s):
    s = unicodedata.normalize("NFC", (s or "")).strip().lower()
    s = re.sub(r"^(xã|phường|thị trấn|tt\.?|p\.?)\s+", "", s)
    return s.strip()

cur_wards = {norm(e.get("name")) for e in ents if e.get("type")=="place" and e.get("level") in ("xa","phuong")}

# --- T1: ghost ---
GHOST = {"prov-1", "test"}
present_ghost = [g for g in GHOST if g in byid]
d["entities"] = [e for e in ents if e["id"] not in GHOST]
stats["T1_ghost_removed"] = len(present_ghost)
before_rels = len(rels)
d["relationships"] = [r for r in rels if r.get("from") not in GHOST and r.get("to") not in GHOST]
stats["T1_rels_removed"] = before_rels - len(d["relationships"])
for it in itins:
    stops = it.get("stops") or []
    kept = [s for s in stops if (s.get("entityId") or s.get("id") or s.get("placeId")) not in GHOST]
    if len(kept) != len(stops):
        stats["T1_itin_stops_removed"] += len(stops)-len(kept); it["stops"] = kept

# --- T2 + T3 (lặp lại trên tập entity đã bỏ ghost) ---
for e in d["entities"]:
    a = A(e)
    if a is None: continue
    changed = False
    # T2 ward
    w = a.get("ward")
    if w:
        nw = norm(w); pid = e.get("placeId"); pn = norm(byid.get(pid,{}).get("name")) if pid in byid else ""
        if pn and nw == pn:
            del a["ward"]; stats["T2_ward_dropped_redundant"] += 1; changed = True
        elif nw not in cur_wards:
            a.pop("ward", None); a["legacy_ward"] = w; stats["T2_ward_to_legacy"] += 1; changed = True
        else:
            stats["T2_ward_kept_for_review"] += 1
    # T3 address NFC
    addr = a.get("address")
    if isinstance(addr, str) and addr:
        nfc = unicodedata.normalize("NFC", addr)
        if nfc != addr:
            a["address"] = nfc; stats["T3_address_nfc"] += 1; changed = True
    if changed:
        e["attributes"] = a

print(f"=== APPLY_DEBT_SAFE — {'APPLY' if APPLY else 'DRY-RUN'} ===")
for k, c in sorted(stats.items()): print(f"  {k}: {c}")
print(f"  entities {len(ents)} → {len(d['entities'])} | relationships {before_rels} → {len(d['relationships'])}")
if present_ghost: print(f"  ghost xoá: {present_ghost}")
if APPLY:
    json.dump(d, open(DATA, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  ✅ ĐÃ GHI {DATA}")
else:
    print("  (DRY-RUN — chưa ghi)")
