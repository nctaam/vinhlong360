"""
normalize_data.py — Comprehensive data normalization for data.json.

12 normalization passes:
  N1.  Reclassify mistyped dishes → restaurant / cafe
  N2.  Fix wrong province in summaries (BT/TV entities saying "tỉnh Vĩnh Long")
  N3.  Delete nonsemantic dish→craft_village associated_with rels
  N4.  Delete "near" relationships with distance > 15km
  N5.  Remove bidirectional duplicate relationships
  N6.  Normalize OCOP ratings to standard format
  N7.  Fix address-only summaries (prepend type context)
  N8.  Fix English dates in summaries
  N9.  Clear out-of-bbox coordinates
  N10. Auto-assign placeId from address ward matching
  N11. Normalize address abbreviations (P. → Phường, etc.)
  N12. Normalize price formats to "X.000 đ" style

Usage:
  python scripts/normalize_data.py              # dry-run
  python scripts/normalize_data.py --apply      # apply

§B1: ALWAYS run scripts/backup_data.py BEFORE --apply.
"""

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "web" / "data.json"
DRY_RUN = "--apply" not in sys.argv

RESTAURANT_PATTERNS = [
    r"\bquán\b", r"\bnhà hàng\b", r"\brestaurant\b", r"\bbuffet\b",
    r"\blẩu\b", r"\bcơm tấm\b", r"\btiệm ăn\b", r"\bquán ăn\b",
    r"\bhải sản\b", r"\bẩm thực\b", r"\bgrill\b", r"\bbbq\b",
    r"\bhotpot\b",
]
CAFE_PATTERNS = [
    r"\bcà phê\b", r"\bcafe\b", r"\bcoffee\b", r"\bhighlands\b",
    r"\bphúc long\b", r"\btrung nguyên\b", r"\btrà sữa\b",
    r"\bmilk tea\b", r"\bboba\b", r"\bstarbucks\b", r"\bthe coffee\b",
]
FOOD_SIGNALS = [
    "bánh", "chè", "mứt", "kẹo", "rượu", "nước mắm", "trái", "cá",
    "tôm", "gà", "vịt", "heo", "bò", "nem", "chả", "xôi", "cháo",
    "mắm", "khô", "dừa", "bưởi", "sầu riêng", "măng cụt",
]


def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _matches_any(text, patterns):
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False


def _haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def n1_reclassify_dishes(entities):
    fixes = []
    for e in entities:
        if e.get("type") != "dish":
            continue
        name = e.get("name", "")
        attrs = e.get("attributes") or {}
        has_biz = bool(attrs.get("address")) and bool(attrs.get("phone") or attrs.get("rating"))

        if _matches_any(name, CAFE_PATTERNS):
            fixes.append((e["id"], "cafe", name))
        elif _matches_any(name, RESTAURANT_PATTERNS):
            fixes.append((e["id"], "restaurant", name))
        elif has_biz and not any(s in name.lower() for s in FOOD_SIGNALS):
            fixes.append((e["id"], "restaurant", name))
    return fixes


def n2_fix_wrong_province_summary(entities):
    fixes = []
    area_province = {"ben-tre": "tỉnh Bến Tre", "tra-vinh": "tỉnh Trà Vinh"}
    for e in entities:
        area = e.get("area", "")
        if area not in area_province:
            continue
        summary = e.get("summary", "")
        if not summary:
            continue
        if re.search(r"tỉnh Vĩnh Long", summary):
            new_summary = re.sub(r"tỉnh Vĩnh Long", area_province[area], summary)
            fixes.append((e["id"], e.get("name", ""), summary[:60], new_summary[:60]))
            e["_n2_summary"] = new_summary
    return fixes


def n3_delete_dish_craft_village_rels(rels, entity_map):
    to_delete = []
    for i, r in enumerate(rels):
        if r["type"] != "associated_with":
            continue
        ef = entity_map.get(r.get("from"))
        et = entity_map.get(r.get("to"))
        if not ef or not et:
            continue
        pair = {ef.get("type"), et.get("type")}
        if pair == {"dish", "craft_village"} or pair == {"restaurant", "craft_village"} or pair == {"cafe", "craft_village"}:
            to_delete.append(i)
    return to_delete


def n4_delete_far_near_rels(rels, entity_map, skip_indices):
    to_delete = []
    for i, r in enumerate(rels):
        if r["type"] != "near" or i in skip_indices:
            continue
        e1 = entity_map.get(r.get("from"))
        e2 = entity_map.get(r.get("to"))
        if not e1 or not e2:
            continue
        c1, c2 = e1.get("coordinates"), e2.get("coordinates")
        if not (isinstance(c1, list) and len(c1) >= 2 and isinstance(c2, list) and len(c2) >= 2):
            continue
        if _haversine_km(c1[0], c1[1], c2[0], c2[1]) > 15:
            to_delete.append(i)
    return to_delete


def n5_remove_bidirectional_dupes(rels, skip_indices):
    seen = {}
    to_delete = []
    for i, r in enumerate(rels):
        if i in skip_indices:
            continue
        key = tuple(sorted([r.get("from", ""), r.get("to", "")])) + (r["type"],)
        if key in seen:
            to_delete.append(i)
        else:
            seen[key] = i
    return to_delete


def n6_normalize_ocop(entities):
    fixes = []
    for e in entities:
        attrs = e.get("attributes") or {}
        tags = e.get("tags") or []
        name = e.get("name", "")
        summary = e.get("summary", "")

        ocop_val = attrs.get("ocop_rating") or attrs.get("ocop") or attrs.get("ocop_star")
        star = None

        for src in [str(ocop_val or ""), name, summary] + [str(t) for t in tags]:
            m = re.search(r"(?:OCOP\s*)?(\d)\s*sao", src, re.IGNORECASE)
            if m:
                star = int(m.group(1))
                break
            m = re.search(r"(\d)\s*sao\s*OCOP", src, re.IGNORECASE)
            if m:
                star = int(m.group(1))
                break

        if star and 1 <= star <= 5:
            if attrs.get("ocop_star") != star:
                new_attrs = dict(attrs)
                new_attrs["ocop_star"] = star
                for old_key in ["ocop_rating", "ocop"]:
                    new_attrs.pop(old_key, None)
                fixes.append((e["id"], e.get("name", ""), star, new_attrs))
        elif any("ocop" in str(v).lower() for v in [*attrs.values(), *tags, name]):
            if "ocop_star" not in attrs and "ocop_certified" not in attrs:
                new_attrs = dict(attrs)
                new_attrs["ocop_certified"] = True
                fixes.append((e["id"], e.get("name", ""), None, new_attrs))
    return fixes


def n7_fix_address_only_summaries(entities):
    type_labels = {
        "accommodation": "Cơ sở lưu trú", "restaurant": "Nhà hàng",
        "cafe": "Quán cà phê", "dish": "Món ăn", "attraction": "Điểm tham quan",
        "product": "Sản phẩm", "craft_village": "Làng nghề",
    }
    fixes = []
    for e in entities:
        if "_n2_summary" in e:
            continue
        summary = (e.get("summary") or "").strip()
        if not summary or len(summary) > 120:
            continue
        addr = ((e.get("attributes") or {}).get("address") or "").strip()
        if not addr:
            continue
        name = e.get("name", "")
        s_low = summary.lower().replace(",", " ").replace(".", " ").split()
        a_low = addr.lower().replace(",", " ").replace(".", " ").split()
        overlap = len(set(s_low) & set(a_low)) / max(len(set(s_low)), 1)
        if overlap > 0.7 and len(summary) < len(addr) + len(name) + 30:
            label = type_labels.get(e.get("type", ""), "Địa điểm")
            new_summary = f"{label} {name} tại {addr}."
            if new_summary != summary:
                fixes.append((e["id"], name, summary[:50], new_summary[:80]))
                e["_n7_summary"] = new_summary
    return fixes


def n8_fix_english_dates(entities):
    month_map = {
        "Jan": "Tháng 1", "Feb": "Tháng 2", "Mar": "Tháng 3", "Apr": "Tháng 4",
        "May": "Tháng 5", "Jun": "Tháng 6", "Jul": "Tháng 7", "Aug": "Tháng 8",
        "Sep": "Tháng 9", "Oct": "Tháng 10", "Nov": "Tháng 11", "Dec": "Tháng 12",
        "January": "Tháng 1", "February": "Tháng 2", "March": "Tháng 3",
        "April": "Tháng 4", "June": "Tháng 6", "July": "Tháng 7",
        "August": "Tháng 8", "September": "Tháng 9", "October": "Tháng 10",
        "November": "Tháng 11", "December": "Tháng 12",
    }
    pattern = re.compile(
        r"\b(January|February|March|April|June|July|August|September|October|November|December|"
        r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s*(\d{4})\b"
    )
    fixes = []
    for e in entities:
        if "_n2_summary" in e or "_n7_summary" in e:
            continue
        summary = e.get("summary", "")
        if not summary:
            continue
        m = pattern.search(summary)
        if m:
            month_vi = month_map.get(m.group(1), m.group(1))
            vi_date = f"ngày {m.group(2)} {month_vi} {m.group(3)}"
            new_summary = summary[:m.start()] + vi_date + summary[m.end():]
            fixes.append((e["id"], e.get("name", ""), m.group(0), vi_date))
            e["_n8_summary"] = new_summary
    return fixes


def n9_clear_bad_coordinates(entities):
    LAT_MIN, LAT_MAX = 9.5, 10.8
    LNG_MIN, LNG_MAX = 105.4, 107.0
    fixes = []
    for e in entities:
        coords = e.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            continue
        lat, lng = coords[0], coords[1]
        if lat < LAT_MIN or lat > LAT_MAX or lng < LNG_MIN or lng > LNG_MAX:
            fixes.append((e["id"], e.get("name", ""), coords))
    return fixes


def n10_auto_assign_placeid(entities, entity_map):
    wards = {}
    for e in entities:
        if e.get("type") == "place" and e.get("level") in ("xa", "phuong"):
            name_lower = e["name"].lower()
            area = e.get("area", "")
            wards[(area, name_lower)] = e["id"]
            for prefix in ["phường ", "xã ", "thị trấn "]:
                if name_lower.startswith(prefix):
                    wards[(area, name_lower[len(prefix):])] = e["id"]

    fixes = []
    for e in entities:
        if e.get("placeId") or e.get("type") == "place":
            continue
        addr = ((e.get("attributes") or {}).get("address") or "").lower()
        area = e.get("area", "")
        if not addr or not area:
            continue

        matched_pid = None
        m = re.search(r"(?:p\.|phường)\s*(\d+)", addr)
        if m:
            num = m.group(1)
            for (a, wname), pid in wards.items():
                if a == area and ("phường " + num == wname or wname.endswith(num)):
                    matched_pid = pid
                    break

        if not matched_pid:
            m = re.search(r"(?:xã|tt\.|thị trấn)\s+([^,]+)", addr, re.IGNORECASE)
            if m:
                xa_name = m.group(1).strip().lower()
                for (a, wname), pid in wards.items():
                    if a == area and xa_name in wname:
                        matched_pid = pid
                        break

        if matched_pid:
            fixes.append((e["id"], e.get("name", ""), matched_pid))
    return fixes


def n11_normalize_addresses(entities):
    abbrevs = [
        (r"\bP\.\s*", "Phường "), (r"\bQ\.\s*", "Quận "),
        (r"\bTP\.\s*", "Thành phố "), (r"\bTp\.\s*", "Thành phố "),
        (r"\bTT\.\s*", "Thị trấn "), (r"\bTX\.\s*", "Thị xã "),
    ]
    fixes = []
    for e in entities:
        attrs = e.get("attributes") or {}
        addr = attrs.get("address", "")
        if not addr:
            continue
        original = addr
        for pat, repl in abbrevs:
            addr = re.sub(pat, repl, addr)
        addr = re.sub(r"\s{2,}", " ", addr).strip()
        area = e.get("area", "")
        if area == "ben-tre":
            addr = re.sub(r"[Tt]ỉnh Vĩnh Long$", "tỉnh Bến Tre", addr)
        elif area == "tra-vinh":
            addr = re.sub(r"[Tt]ỉnh Vĩnh Long$", "tỉnh Trà Vinh", addr)
        if addr != original:
            fixes.append((e["id"], e.get("name", "")[:30], original[:50], addr[:50]))
            e["_n11_addr"] = addr
    return fixes


def n12_normalize_prices(entities):
    fixes = []
    for e in entities:
        attrs = e.get("attributes") or {}
        for key in ["price", "price_range"]:
            val = attrs.get(key)
            if not val or not isinstance(val, str):
                continue
            original = val
            new_val = val
            new_val = re.sub(r"(\d)(\d{3})(\d{3})\b", r"\1.\2.\3", new_val)
            new_val = re.sub(r"(\d{2,3})(\d{3})\b(?!\.\d)", r"\1.\2", new_val)
            new_val = re.sub(r"\s*VND\b", " đ", new_val)
            new_val = re.sub(r"\s*VNĐ\b", " đ", new_val)
            new_val = re.sub(r"\s*vnđ\b", " đ", new_val)
            new_val = re.sub(r"\s*vnd\b", " đ", new_val)
            new_val = re.sub(r"\s*đồng\b", " đ", new_val)
            new_val = re.sub(r"(\d)đ\b", r"\1 đ", new_val)
            new_val = new_val.strip()
            if new_val != original:
                fixes.append((e["id"], key, original, new_val))
                if "_n12_attrs" not in e:
                    e["_n12_attrs"] = dict(attrs)
                e["_n12_attrs"][key] = new_val
    return fixes


def main():
    data = load_data()
    entities = data["entities"]
    rels = data["relationships"]
    entity_map = {e["id"]: e for e in entities}

    mode = "DRY RUN" if DRY_RUN else "APPLYING"
    print(f"{'=' * 60}")
    print(f"  DATA NORMALIZATION — {mode}")
    print(f"  {len(entities)} entities, {len(rels)} relationships")
    print(f"{'=' * 60}\n")

    all_del = set()

    # N1
    n1 = n1_reclassify_dishes(entities)
    tc = Counter(t for _, t, _ in n1)
    print(f"N1. Reclassify dishes: {len(n1)} ({tc.get('restaurant', 0)} restaurant, {tc.get('cafe', 0)} cafe)")
    for _, t, nm in n1[:5]:
        print(f"    {nm[:45]} → {t}")
    if len(n1) > 5:
        print(f"    ... +{len(n1) - 5} more")

    # N2
    n2 = n2_fix_wrong_province_summary(entities)
    print(f"\nN2. Fix wrong province in summaries: {len(n2)}")
    for _, nm, old, new in n2[:3]:
        print(f"    {nm[:30]}: ...{old[-30:]} → ...{new[-30:]}")

    # N3
    n3 = n3_delete_dish_craft_village_rels(rels, entity_map)
    all_del.update(n3)
    print(f"\nN3. Delete dish↔craft_village associated_with: {len(n3)}")

    # N4
    n4 = n4_delete_far_near_rels(rels, entity_map, all_del)
    all_del.update(n4)
    print(f"\nN4. Delete near rels > 15km: {len(n4)}")

    # N5
    n5 = n5_remove_bidirectional_dupes(rels, all_del)
    all_del.update(n5)
    print(f"\nN5. Remove bidirectional duplicates: {len(n5)}")

    # N6
    n6 = n6_normalize_ocop(entities)
    print(f"\nN6. Normalize OCOP: {len(n6)}")
    stars = Counter(s for _, _, s, _ in n6 if s)
    for s, c in sorted(stars.items()):
        print(f"    {s} sao: {c}")
    ns = sum(1 for _, _, s, _ in n6 if not s)
    if ns:
        print(f"    certified (no star): {ns}")

    # N7
    n7 = n7_fix_address_only_summaries(entities)
    print(f"\nN7. Fix address-only summaries: {len(n7)}")
    for _, nm, old, new in n7[:3]:
        print(f"    {nm[:25]}: \"{old[:40]}\" → \"{new[:50]}\"")

    # N8
    n8 = n8_fix_english_dates(entities)
    print(f"\nN8. Fix English dates: {len(n8)}")
    for _, nm, od, nd in n8[:5]:
        print(f"    {nm[:30]}: {od} → {nd}")

    # N9
    n9 = n9_clear_bad_coordinates(entities)
    print(f"\nN9. Clear out-of-bbox coords: {len(n9)}")
    for _, nm, c in n9[:5]:
        print(f"    {nm[:35]}: [{c[0]:.4f}, {c[1]:.4f}]")

    # N10
    n10 = n10_auto_assign_placeid(entities, entity_map)
    print(f"\nN10. Auto-assign placeId: {len(n10)}")
    for _, nm, pid in n10[:5]:
        print(f"     {nm[:35]} → {pid}")

    # N11
    n11 = n11_normalize_addresses(entities)
    print(f"\nN11. Normalize addresses: {len(n11)}")
    for _, nm, old, new in n11[:3]:
        print(f"     {nm}: \"{old}\" → \"{new}\"")

    # N12
    n12 = n12_normalize_prices(entities)
    print(f"\nN12. Normalize prices: {len(n12)}")
    for _, k, old, new in n12[:5]:
        print(f"     {k}: \"{old}\" → \"{new}\"")

    total_del = len(all_del)
    print(f"\n{'=' * 60}")
    print(f"  SUMMARY")
    print(f"  Rels deleted:    {total_del} (N3:{len(n3)} + N4:{len(n4)} + N5:{len(n5)})")
    print(f"  Entity fixes:    N1:{len(n1)} N2:{len(n2)} N6:{len(n6)} N7:{len(n7)}")
    print(f"                   N8:{len(n8)} N9:{len(n9)} N10:{len(n10)} N11:{len(n11)} N12:{len(n12)}")
    print(f"  Net rels:        {len(rels) - total_del}")
    print(f"{'=' * 60}")

    if DRY_RUN:
        print(f"\n  → DRY RUN. Run with --apply to save.")
        return

    print("\nApplying...")
    eid_map = {e["id"]: e for e in entities}

    for eid, new_type, _ in n1:
        if eid in eid_map:
            eid_map[eid]["type"] = new_type

    for e in entities:
        for key in ("_n2_summary", "_n7_summary", "_n8_summary"):
            if key in e:
                e["summary"] = e.pop(key)
                break

    for i in sorted(all_del, reverse=True):
        del rels[i]

    for eid, _, star, new_attrs in n6:
        if eid in eid_map:
            eid_map[eid]["attributes"] = new_attrs

    for eid, _, _ in n9:
        if eid in eid_map:
            eid_map[eid]["coordinates"] = None

    for eid, _, pid in n10:
        if eid in eid_map:
            eid_map[eid]["placeId"] = pid

    for e in entities:
        if "_n11_addr" in e:
            if not e.get("attributes"):
                e["attributes"] = {}
            e["attributes"]["address"] = e.pop("_n11_addr")

    for e in entities:
        if "_n12_attrs" in e:
            e["attributes"] = e.pop("_n12_attrs")

    for e in entities:
        for k in list(e.keys()):
            if k.startswith("_n"):
                del e[k]

    data["relationships"] = rels
    save_data(data)
    print(f"\nSaved: {len(entities)} entities, {len(rels)} relationships")
    print("Run: python scripts/validate_data.py to verify.")


if __name__ == "__main__":
    main()
