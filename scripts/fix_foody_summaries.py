"""Fix Foody-scraped template summaries in web/data.json.

Foody-crawled entities have mechanical summaries like:
  "{Name} tại {Address}. Đánh giá X/10 (Y lượt)."

This script rewrites them into natural Vietnamese using type-specific
templates while preserving all factual content (address, rating, count).

Usage:
  python scripts/fix_foody_summaries.py          # dry-run: show samples + count
  python scripts/fix_foody_summaries.py --apply  # write changes to data.json
"""
import argparse
import io
import json
import re
import sys
from pathlib import Path

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "web" / "data.json"

# ---------------------------------------------------------------------------
# Pattern matching for Foody-template summaries
# ---------------------------------------------------------------------------
# Matches: "{Name} tại {Address}. Đánh giá {rating}/10 ({count} lượt)."
# Also matches the variant without rating: "{Name} tại {Address}." (no rating)
FOODY_PATTERN = re.compile(
    r"^(?:Món ăn )?"          # optional "Món ăn " prefix (Mai Bingsu variant)
    r"(.+?)"                  # (1) name
    r"\s+tại\s+"              # " tại "
    r"(.+?)"                  # (2) address
    r"\."                     # period
    r"(?:\s*Đánh giá\s+"     # optional rating block
    r"(\d+(?:\.\d+)?)/10"    # (3) rating
    r"(?:\s*\((\d+)\s*lượt\))?"  # (4) review count (optional)
    r"\.)?"                   # closing period of rating block
    r"\s*$"
)

# Province suffixes to strip for short_address
PROVINCE_SUFFIXES = [
    ", Vĩnh Long",
    ", Bến Tre",
    ", Trà Vinh",
    " , Vĩnh Long",
    " , Bến Tre",
    " , Trà Vinh",
]

AREA_PROVINCE = {
    "vinh-long": "Vĩnh Long",
    "ben-tre": "Bến Tre",
    "tra-vinh": "Trà Vinh",
}


CITY_SUFFIXES = [
    "Thành Phố Vĩnh Long",
    "Thành phố Vĩnh Long",
    "TP. Vĩnh Long",
    "Tp. Vĩnh Long",
    "Thành Phố Bến Tre",
    "Thành phố Bến Tre",
    "TP. Bến Tre",
    "Tp. Bến Tre",
    "Thành Phố Trà Vinh",
    "Thành phố Trà Vinh",
    "TP. Trà Vinh",
    "Tp. Trà Vinh",
    "Thị Xã Bình Minh",
    "Thị xã Bình Minh",
    "Thị Xã Long Mỹ",
    "TX. Bình Minh",
]


def shorten_address(address: str) -> str:
    """Strip province + city name from end, clean extra spaces/commas."""
    short = address
    # Step 1: strip province suffix
    for suffix in PROVINCE_SUFFIXES:
        if short.endswith(suffix):
            short = short[: -len(suffix)]
            break

    # Clean trailing comma/space
    short = re.sub(r"[\s,]+$", "", short)

    # Step 2: strip city suffix (Thành Phố X, Thị Xã Y)
    for city in CITY_SUFFIXES:
        if short.endswith(city):
            short = short[: -len(city)]
            break

    # Clean trailing comma/space again
    short = re.sub(r"[\s,]+$", "", short)
    # Normalize multiple spaces
    short = re.sub(r"\s{2,}", " ", short)
    # Normalize " , " → ", "
    short = re.sub(r"\s*,\s*", ", ", short)
    return short.strip()


def rating_text(rating: float, count: int | None) -> str:
    """Format rating into a natural phrase."""
    if count and count > 0:
        return f"được đánh giá {rating}/10 ({count} lượt đánh giá trên Foody)"
    return f"được đánh giá {rating}/10 trên Foody"


def infer_cuisine_hint(name: str) -> str:
    """Try to infer cuisine/specialty from the entity name.

    Order matters: more specific patterns first, generic ones last.
    """
    name_lower = name.lower()

    # --- Specific dish combos (check before generic ingredients) ---
    # Bún bò Huế
    if "bún bò" in name_lower:
        return "chuyên bún bò Huế"
    # Mì cay / Korean
    if any(k in name_lower for k in ["mì cay", "hàn quốc", "kimchi", "bibimbap", "kimbap"]):
        return "chuyên món Hàn Quốc"
    # Bún đậu mắm tôm
    if "bún đậu" in name_lower:
        return "chuyên bún đậu mắm tôm"
    # Japanese
    if any(k in name_lower for k in ["nhật", "sushi", "sashimi", "ramen"]):
        return "chuyên món Nhật"
    # Bánh xèo
    if "bánh xèo" in name_lower:
        return "chuyên bánh xèo"
    # Bánh canh
    if "bánh canh" in name_lower:
        return "chuyên bánh canh"
    # Bánh tét / bánh tráng / bánh cuốn
    if "bánh tét" in name_lower or "trà cuôn" in name_lower:
        return "chuyên bánh tét Trà Cuôn"
    if "bánh cuốn" in name_lower:
        return "chuyên bánh cuốn"
    # Cơm gà
    if "cơm gà" in name_lower:
        return "chuyên cơm gà"
    # Cơm tấm
    if "cơm tấm" in name_lower:
        return "chuyên cơm tấm"
    # Bò tơ
    if "bò tơ" in name_lower:
        return "chuyên bò tơ"

    # --- Cooking style ---
    # Hotpot + grill combo
    if "lẩu" in name_lower and "nướng" in name_lower:
        return "chuyên lẩu và nướng"
    # Hotpot
    if "lẩu" in name_lower:
        return "chuyên lẩu"
    # BBQ / grill
    if any(k in name_lower for k in ["nướng", "bbq"]):
        return "chuyên nướng"

    # --- Main ingredient ---
    # Chicken
    if "gà" in name_lower:
        return "chuyên các món gà"
    # Beef
    if "bò" in name_lower or "bê" in name_lower:
        return "chuyên các món bò"
    # Frog
    if "ếch" in name_lower:
        return "chuyên cháo ếch"

    # --- Noodles/rice ---
    # Bún (generic)
    if "bún" in name_lower:
        return "chuyên bún"
    # Phở
    if "phở" in name_lower:
        return "chuyên phở"
    # Cháo
    if "cháo" in name_lower:
        return "chuyên cháo"
    # Xôi
    if "xôi" in name_lower:
        return "chuyên xôi"

    # --- Sweets / snacks ---
    if "yogurt" in name_lower:
        return "chuyên yogurt và tráng miệng"
    if "kem" in name_lower:
        return "chuyên kem và tráng miệng"
    if "flan" in name_lower:
        return "chuyên bánh flan"
    if "bánh bao" in name_lower:
        return "chuyên bánh bao"
    if "bánh" in name_lower:
        return "chuyên các loại bánh"

    # --- Drinks ---
    if any(k in name_lower for k in ["trà sữa", "milk tea", "tapi"]):
        return "chuyên trà sữa"

    return ""


def build_new_summary(entity: dict, name: str, address: str,
                      rating: float | None, count: int | None) -> str:
    """Build a natural summary based on entity type."""
    etype = entity.get("type", "restaurant")
    area = entity.get("area", "vinh-long")
    province = AREA_PROVINCE.get(area, "Vĩnh Long")
    short_addr = shorten_address(address)

    cuisine = infer_cuisine_hint(name)
    rating_part = ""
    if rating is not None:
        rating_part = ", " + rating_text(rating, count)

    if etype == "cafe":
        # Cafe template
        base = f"{name} là quán cà phê tại {short_addr} ({province})"
        if cuisine and "trà sữa" in cuisine:
            base = f"{name} là quán trà sữa tại {short_addr} ({province})"
        return f"{base}{rating_part}."

    elif etype == "dish":
        # "dish" type from Foody are actually food shops/stalls, not dishes
        if cuisine:
            base = f"{name} là quán ăn {cuisine} tại {short_addr} ({province})"
        else:
            base = f"{name} là quán ăn tại {short_addr} ({province})"
        return f"{base}{rating_part}."

    elif etype == "accommodation":
        base = f"{name} là cơ sở lưu trú tại {short_addr} ({province})"
        return f"{base}{rating_part}."

    elif etype == "attraction":
        base = f"{name} là điểm tham quan tại {short_addr} ({province})"
        if rating is not None:
            return f"{base}{rating_part}."
        return f"{base}."

    else:
        # restaurant (default)
        if cuisine:
            base = f"{name} là nhà hàng {cuisine} tại {short_addr} ({province})"
        else:
            base = f"{name} là nhà hàng tại {short_addr} ({province})"
        return f"{base}{rating_part}."


def main():
    parser = argparse.ArgumentParser(description="Fix Foody-template summaries")
    parser.add_argument("--apply", action="store_true",
                        help="Write changes to data.json (dry-run by default)")
    args = parser.parse_args()

    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    entities = data["entities"]

    def is_foody_source(ent: dict) -> bool:
        """Check if entity originates from Foody.vn."""
        sources = ent.get("source", [])
        if not sources:
            return False
        for s in sources:
            if isinstance(s, dict):
                name = s.get("name", "") or s.get("title", "")
                if "foody" in name.lower():
                    return True
        return False

    matches = []
    for ent in entities:
        summary = ent.get("summary", "")
        m = FOODY_PATTERN.match(summary)
        if m and is_foody_source(ent):
            matches.append((ent, m))

    print(f"Total entities: {len(entities)}")
    print(f"Foody-template summaries found: {len(matches)}")
    print()

    # Type breakdown
    type_counts: dict[str, int] = {}
    area_counts: dict[str, int] = {}
    for ent, _ in matches:
        t = ent.get("type", "unknown")
        a = ent.get("area", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
        area_counts[a] = area_counts.get(a, 0) + 1

    print("By type:")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {t}: {c}")
    print()
    print("By area:")
    for a, c in sorted(area_counts.items(), key=lambda x: -x[1]):
        print(f"  {a}: {c}")
    print()

    # Build rewrites
    ent_by_id = {e["id"]: e for e in entities}
    rewrites = []
    for ent, m in matches:
        matched_name = m.group(1)
        address = m.group(2)
        rating = float(m.group(3)) if m.group(3) else None
        count = int(m.group(4)) if m.group(4) else None

        new_summary = build_new_summary(ent, ent["name"], address, rating, count)
        rewrites.append({
            "id": ent["id"],
            "old": ent["summary"],
            "new": new_summary,
        })

    # Show diverse samples: pick from each type+area combo
    seen_combos: dict[str, list] = {}
    for rw in rewrites:
        ent = ent_by_id.get(rw["id"])
        if not ent:
            continue
        combo = f"{ent.get('type', '?')}|{ent.get('area', '?')}"
        if combo not in seen_combos:
            seen_combos[combo] = []
        if len(seen_combos[combo]) < 2:
            seen_combos[combo].append(rw)

    samples = []
    for combo_samples in sorted(seen_combos.items()):
        samples.extend(combo_samples[1])
    # Cap at 15
    samples = samples[:15]

    print("=" * 70)
    print(f"Sample transformations ({len(samples)} diverse of {len(rewrites)} total):")
    print("=" * 70)
    for i, rw in enumerate(samples):
        ent = ent_by_id.get(rw["id"])
        tag = f"{ent['type']}|{ent.get('area','?')}" if ent else "?"
        print(f"\n[{i + 1}] ({tag}) {rw['id']}")
        print(f"  OLD: {rw['old']}")
        print(f"  NEW: {rw['new']}")

    print(f"\n{'=' * 70}")
    print(f"Total to rewrite: {len(rewrites)}")

    if not args.apply:
        print("\nDry-run mode. Use --apply to write changes.")
        return

    # Apply changes
    ent_by_id = {e["id"]: e for e in entities}
    applied = 0
    for rw in rewrites:
        if rw["id"] in ent_by_id:
            ent_by_id[rw["id"]]["summary"] = rw["new"]
            applied += 1

    DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nApplied {applied} summary rewrites to {DATA_PATH}")


if __name__ == "__main__":
    main()
