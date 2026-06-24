#!/usr/bin/env python3
"""
Comprehensive data normalization analysis for vinhlong360.
Examines web/data.json for inconsistencies, quality issues, and normalization needs.
"""

import json
import re
import sys
import os
from collections import Counter, defaultdict
from difflib import SequenceMatcher

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'web', 'data.json')

def load_data():
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def hr(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def sub_hr(title):
    print(f"\n--- {title} ---\n")

# ============================================================================
# PART 1: Type Classification Audit
# ============================================================================
def part1_type_classification(entities, entity_map):
    hr("PART 1: TYPE CLASSIFICATION AUDIT")

    type_counts = Counter(e['type'] for e in entities)
    print("Entity counts by type:")
    for t, c in type_counts.most_common():
        print(f"  {t:20s}: {c:5d}")
    print(f"  {'TOTAL':20s}: {len(entities):5d}")

    # --- Dishes that are actually restaurants/cafes ---
    sub_hr("DISH type: Restaurants misclassified as dishes")
    dishes = [e for e in entities if e['type'] == 'dish']

    restaurant_patterns = [
        r'(?i)qu[aá]n', r'(?i)nh[aà]\s*h[aà]ng', r'(?i)restaurant',
        r'(?i)b[eê]p', r'(?i)ti[eệ]m', r'(?i)ph[oở]\s', r'(?i)ch[eè]\s',
        r'(?i)l[aẩ]u\s', r'(?i)b[uú]n\s', r'(?i)c[oơ]m\s',
    ]
    cafe_patterns = [
        r'(?i)c[aà]\s*ph[eê]', r'(?i)coffee', r'(?i)highlands',
        r'(?i)ph[uú]c\s*long', r'(?i)trung\s*nguy[eê]n', r'(?i)tea\b',
        r'(?i)tr[aà]\s*s[uữ]a', r'(?i)kem\s', r'(?i)smoothie',
        r'(?i)brownie', r'(?i)catimo', r'(?i)mocha', r'(?i)latte',
    ]
    bakery_patterns = [
        r'(?i)b[aá]nh\s*m[iì]', r'(?i)bakery', r'(?i)pastry',
    ]

    restaurants_in_dish = []
    cafes_in_dish = []
    bakeries_in_dish = []
    actual_dishes = []

    for e in dishes:
        name = e['name']
        is_restaurant = any(re.search(p, name) for p in restaurant_patterns)
        is_cafe = any(re.search(p, name) for p in cafe_patterns)
        is_bakery = any(re.search(p, name) for p in bakery_patterns)

        if is_cafe:
            cafes_in_dish.append(name)
        elif is_restaurant:
            restaurants_in_dish.append(name)
        elif is_bakery:
            bakeries_in_dish.append(name)
        else:
            actual_dishes.append(name)

    print(f"Total dishes: {len(dishes)}")
    print(f"  Likely RESTAURANTS (should be reclassified): {len(restaurants_in_dish)}")
    for n in restaurants_in_dish[:15]:
        print(f"    - {n}")
    if len(restaurants_in_dish) > 15:
        print(f"    ... and {len(restaurants_in_dish)-15} more")

    print(f"\n  Likely CAFES/DRINKS (should be reclassified): {len(cafes_in_dish)}")
    for n in cafes_in_dish[:15]:
        print(f"    - {n}")
    if len(cafes_in_dish) > 15:
        print(f"    ... and {len(cafes_in_dish)-15} more")

    print(f"\n  Likely BAKERIES: {len(bakeries_in_dish)}")
    for n in bakeries_in_dish[:10]:
        print(f"    - {n}")

    print(f"\n  Actual food items (remaining): {len(actual_dishes)}")
    for n in actual_dishes[:10]:
        print(f"    - {n}")

    # --- Products that are services/shops ---
    sub_hr("PRODUCT type: Services or shops misclassified?")
    products = [e for e in entities if e['type'] == 'product']
    service_kw = [r'(?i)d[iị]ch\s*v[uụ]', r'(?i)c[uử]a\s*h[aà]ng', r'(?i)shop',
                  r'(?i)service', r'(?i)massage', r'(?i)spa']
    services_in_product = []
    for e in products:
        name = e['name']
        if any(re.search(p, name) for p in service_kw):
            services_in_product.append(name)
    print(f"Total products: {len(products)}")
    print(f"  Possibly services/shops: {len(services_in_product)}")
    for n in services_in_product[:10]:
        print(f"    - {n}")

    # --- Persons ---
    sub_hr("PERSON type: All persons + relationship counts")
    persons = [e for e in entities if e['type'] == 'person']
    print(f"Total persons: {len(persons)}")
    for e in persons:
        # Count relationships involving this person
        rel_count = sum(1 for r in data['relationships']
                        if r['from'] == e['id'] or r['to'] == e['id'])
        print(f"  {e['name']:40s} rels={rel_count:3d}  area={e.get('area','?')}")

    # --- 5 sample names per type ---
    sub_hr("5 sample names per type")
    for t in sorted(type_counts.keys()):
        ents = [e['name'] for e in entities if e['type'] == t]
        print(f"\n  {t} ({len(ents)} total):")
        for n in ents[:5]:
            print(f"    - {n}")


# ============================================================================
# PART 2: Attribute Schema Analysis Per Type
# ============================================================================
def part2_attribute_schema(entities):
    hr("PART 2: ATTRIBUTE SCHEMA ANALYSIS PER TYPE")

    by_type = defaultdict(list)
    for e in entities:
        by_type[e['type']].append(e)

    for t in sorted(by_type.keys()):
        ents = by_type[t]
        sub_hr(f"Type: {t} ({len(ents)} entities)")

        # Collect all attribute keys and their counts
        attr_counter = Counter()
        for e in ents:
            attrs = e.get('attributes', {}) or {}
            for k in attrs.keys():
                attr_counter[k] += 1

        if not attr_counter:
            print("  (no attributes)")
            continue

        print(f"  {'Attribute key':35s} {'Count':>6s} {'Coverage':>8s}")
        print(f"  {'-'*35} {'-'*6} {'-'*8}")
        for k, c in attr_counter.most_common():
            pct = c / len(ents) * 100
            marker = " *** LOW" if 0 < pct < 50 else ""
            print(f"  {k:35s} {c:6d} {pct:7.1f}%{marker}")

    # --- Check for inconsistent key naming ---
    sub_hr("Inconsistent key naming patterns")
    all_keys = set()
    for e in entities:
        attrs = e.get('attributes', {}) or {}
        all_keys.update(attrs.keys())

    # Group similar keys
    key_groups = {
        'phone': [k for k in all_keys if 'phone' in k.lower() or 'dien_thoai' in k.lower() or 'tel' in k.lower() or 'sdt' in k.lower()],
        'address': [k for k in all_keys if 'address' in k.lower() or 'dia_chi' in k.lower() or 'diachi' in k.lower()],
        'price': [k for k in all_keys if 'price' in k.lower() or 'gia' in k.lower() or 'cost' in k.lower()],
        'rating': [k for k in all_keys if 'rating' in k.lower() or 'score' in k.lower() or 'diem' in k.lower()],
        'coords': [k for k in all_keys if 'coord' in k.lower() or 'lat' in k.lower() or 'lng' in k.lower() or 'lon' in k.lower()],
        'website': [k for k in all_keys if 'web' in k.lower() or 'url' in k.lower() or 'link' in k.lower()],
    }
    for group_name, keys in key_groups.items():
        if len(keys) > 1:
            print(f"  INCONSISTENT [{group_name}]: {keys}")
        elif len(keys) == 1:
            print(f"  OK [{group_name}]: {keys}")
        else:
            print(f"  MISSING [{group_name}]: (none found)")

    print(f"\n  All unique attribute keys ({len(all_keys)}):")
    for k in sorted(all_keys):
        print(f"    - {k}")

    # --- Price format variations ---
    sub_hr("Price format variations")
    price_formats = Counter()
    price_samples = defaultdict(list)
    for e in entities:
        attrs = e.get('attributes', {}) or {}
        for k in ['price', 'gia', 'budget']:
            if k in attrs and attrs[k]:
                val = str(attrs[k])
                # Classify format
                if re.match(r'^\d+$', val):
                    fmt = 'plain_number (e.g. 50000)'
                elif re.search(r'\d+\.\d{3}', val):
                    fmt = 'dot_thousands (e.g. 50.000đ)'
                elif re.search(r'\d+,\d{3}', val):
                    fmt = 'comma_thousands (e.g. 50,000)'
                elif re.search(r'\d+k', val, re.I):
                    fmt = 'k_suffix (e.g. 50k)'
                elif re.search(r'(VND|VNĐ|đ)', val, re.I):
                    fmt = 'with_currency'
                elif re.search(r'[\-–]', val):
                    fmt = 'range'
                else:
                    fmt = 'other'
                price_formats[fmt] += 1
                if len(price_samples[fmt]) < 5:
                    price_samples[fmt].append(f"{e['name']}: {val}")

    for fmt, count in price_formats.most_common():
        print(f"  {fmt}: {count}")
        for s in price_samples[fmt]:
            print(f"    - {s}")


# ============================================================================
# PART 3: Summary Quality Deep Scan
# ============================================================================
def part3_summary_quality(entities):
    hr("PART 3: SUMMARY QUALITY DEEP SCAN")

    # --- English text in summaries ---
    sub_hr("Summaries containing English text (non-trivial)")
    english_words = re.compile(r'\b(the|this|and|for|with|from|that|have|are|was|were|been|being|will|would|could|should|may|might|must|shall|can|about|which|when|where|what|who|how|not|all|each|every|both|few|more|most|other|some|such|only|also|very|often|always|never|just|even|still|already|again|further|then|once|restaurant|coffee|shop|hotel|resort|homestay|village|temple|church|museum|market|bridge|island|river|beach|food|drink|cuisine|traditional|modern|famous|popular|beautiful|delicious|located|situated|established|founded|built|opened|serves|offers|provides|features|includes|district|province|city|town|ward|commune)\b', re.I)

    # Filter out common loanwords that are OK in Vietnamese context
    ok_in_vn = {'coffee', 'hotel', 'resort', 'homestay', 'spa', 'wifi', 'check-in',
                'shop', 'market', 'bar', 'club', 'pizza', 'burger', 'steak'}

    english_summaries = []
    for e in entities:
        s = e.get('summary', '') or ''
        matches = english_words.findall(s.lower())
        # Filter out OK loanwords
        real_english = [m for m in matches if m.lower() not in ok_in_vn]
        if len(real_english) >= 3:
            english_summaries.append((e['name'], e['type'], s[:150], real_english[:5]))

    print(f"Summaries with 3+ English words: {len(english_summaries)}")
    for name, typ, summary, words in english_summaries[:15]:
        print(f"  [{typ}] {name}")
        print(f"    words: {words}")
        print(f"    summary: {summary}...")

    # --- Summaries that are just addresses/phone numbers ---
    sub_hr("Summaries that are just addresses or phone numbers")
    addr_only = []
    for e in entities:
        s = (e.get('summary', '') or '').strip()
        if not s:
            continue
        # Check if summary is mostly an address
        if re.match(r'^[\d\s,./\-]+$', s):
            addr_only.append((e['name'], e['type'], s))
        elif len(s) < 100 and re.search(r'(?:P\.|Phường|Q\.|Quận|Huyện|Thành phố|TP\.)', s) and not re.search(r'[.!?]', s.rstrip('.')):
            # Looks like just an address
            addr_only.append((e['name'], e['type'], s))
        elif re.match(r'^[\d\s\-\+\(\)]+$', s):
            addr_only.append((e['name'], e['type'], s))

    print(f"Summaries that look like just addresses/phones: {len(addr_only)}")
    for name, typ, s in addr_only[:20]:
        print(f"  [{typ}] {name}: {s}")

    # --- Wrong province mentions ---
    sub_hr("Summaries mentioning wrong province")
    wrong_province = []
    for e in entities:
        s = (e.get('summary', '') or '').lower()
        area = (e.get('area', '') or '').lower()
        if not s or not area:
            continue

        if area == 'ben-tre':
            if 'tỉnh vĩnh long' in s or 'tp vĩnh long' in s or 'tp. vĩnh long' in s:
                wrong_province.append((e['name'], area, 'mentions Vĩnh Long', s[:120]))
            if 'tỉnh trà vinh' in s or 'tp trà vinh' in s:
                wrong_province.append((e['name'], area, 'mentions Trà Vinh', s[:120]))
        elif area == 'tra-vinh':
            if 'tỉnh vĩnh long' in s or 'tp vĩnh long' in s:
                wrong_province.append((e['name'], area, 'mentions Vĩnh Long', s[:120]))
            if 'tỉnh bến tre' in s or 'tp bến tre' in s:
                wrong_province.append((e['name'], area, 'mentions Bến Tre', s[:120]))
        elif area == 'vinh-long':
            if 'tỉnh bến tre' in s or 'tp bến tre' in s:
                wrong_province.append((e['name'], area, 'mentions Bến Tre', s[:120]))
            if 'tỉnh trà vinh' in s or 'tp trà vinh' in s:
                wrong_province.append((e['name'], area, 'mentions Trà Vinh', s[:120]))

    print(f"Potential wrong province in summary: {len(wrong_province)}")
    for name, area, issue, s in wrong_province[:20]:
        print(f"  [{area}] {name}: {issue}")
        print(f"    {s}")

    # --- Duplicate/near-duplicate summaries ---
    sub_hr("Duplicate and near-duplicate summaries")
    summary_map = defaultdict(list)
    for e in entities:
        s = (e.get('summary', '') or '').strip()
        if s:
            summary_map[s].append((e['name'], e['type']))

    exact_dupes = {s: names for s, names in summary_map.items() if len(names) > 1}
    print(f"Exact duplicate summaries: {len(exact_dupes)}")
    for s, names in list(exact_dupes.items())[:10]:
        print(f"  Summary: {s[:100]}...")
        for name, typ in names:
            print(f"    - [{typ}] {name}")

    # Near-duplicate check (sample, expensive)
    summaries_list = [(e['name'], e['type'], (e.get('summary', '') or '').strip())
                      for e in entities if (e.get('summary', '') or '').strip()]
    near_dupes = []
    # Only check within same type for performance
    by_type_summaries = defaultdict(list)
    for name, typ, s in summaries_list:
        by_type_summaries[typ].append((name, s))

    for typ, items in by_type_summaries.items():
        if len(items) > 500:
            continue  # Skip very large types for performance
        for i in range(len(items)):
            for j in range(i+1, min(i+50, len(items))):
                ratio = SequenceMatcher(None, items[i][1][:100], items[j][1][:100]).ratio()
                if ratio > 0.85 and items[i][1] != items[j][1]:
                    near_dupes.append((typ, items[i][0], items[j][0], ratio, items[i][1][:80]))

    print(f"\nNear-duplicate summaries (>85% similar): {len(near_dupes)}")
    for typ, n1, n2, ratio, s in near_dupes[:15]:
        print(f"  [{typ}] {n1} <-> {n2} ({ratio:.0%})")
        print(f"    {s}...")

    # --- Short summaries ---
    sub_hr("Summaries shorter than 20 characters")
    short = [(e['name'], e['type'], e.get('summary', ''))
             for e in entities if 0 < len((e.get('summary', '') or '').strip()) < 20]
    print(f"Short summaries (<20 chars): {len(short)}")
    for name, typ, s in short[:20]:
        print(f"  [{typ}] {name}: \"{s}\"")

    # --- Empty/missing summaries ---
    empty = [e for e in entities if not (e.get('summary', '') or '').strip()]
    print(f"\nEmpty/missing summaries: {len(empty)}")
    empty_by_type = Counter(e['type'] for e in empty)
    for t, c in empty_by_type.most_common():
        print(f"  {t}: {c}")

    # --- HTML/markdown in summaries ---
    sub_hr("Summaries with HTML tags or markdown")
    html_md = []
    for e in entities:
        s = e.get('summary', '') or ''
        has_html = bool(re.search(r'<[a-zA-Z][^>]*>', s))
        has_md = bool(re.search(r'(\*\*|__|##|```|\[.*?\]\(.*?\))', s))
        if has_html or has_md:
            html_md.append((e['name'], e['type'], s[:120],
                            'HTML' if has_html else 'Markdown'))
    print(f"Summaries with HTML/Markdown: {len(html_md)}")
    for name, typ, s, kind in html_md[:15]:
        print(f"  [{typ}] {name} ({kind}): {s}...")

    # --- Average summary length per type ---
    sub_hr("Average summary length per type")
    len_by_type = defaultdict(list)
    for e in entities:
        s = (e.get('summary', '') or '').strip()
        if s:
            len_by_type[e['type']].append(len(s))

    print(f"  {'Type':20s} {'Count':>6s} {'Avg len':>8s} {'Min':>6s} {'Max':>6s} {'Median':>8s}")
    for t in sorted(len_by_type.keys()):
        lens = sorted(len_by_type[t])
        avg = sum(lens) / len(lens)
        mid = lens[len(lens)//2]
        print(f"  {t:20s} {len(lens):6d} {avg:8.1f} {lens[0]:6d} {lens[-1]:6d} {mid:8d}")


# ============================================================================
# PART 4: Name Normalization
# ============================================================================
def part4_name_normalization(entities):
    hr("PART 4: NAME NORMALIZATION")

    # --- Trailing/leading whitespace ---
    sub_hr("Names with trailing/leading whitespace")
    whitespace_names = [(e['name'], e['type']) for e in entities
                        if e['name'] != e['name'].strip()]
    print(f"Names with extra whitespace: {len(whitespace_names)}")
    for name, typ in whitespace_names[:20]:
        print(f"  [{typ}] \"{name}\"")

    # --- Internal multiple spaces ---
    multi_space = [(e['name'], e['type']) for e in entities
                   if '  ' in e['name']]
    print(f"\nNames with multiple consecutive spaces: {len(multi_space)}")
    for name, typ in multi_space[:20]:
        print(f"  [{typ}] \"{name}\"")

    # --- ALL CAPS detection ---
    sub_hr("Names with inconsistent capitalization")
    all_caps = [(e['name'], e['type']) for e in entities
                if e['name'] == e['name'].upper() and len(e['name']) > 5
                and re.search(r'[A-ZÀ-Ỹ]', e['name'])]
    print(f"ALL CAPS names: {len(all_caps)}")
    for name, typ in all_caps[:20]:
        print(f"  [{typ}] {name}")

    # Check for mixed VN all-caps words (CHÙA, ĐÌNH, etc.)
    vn_prefix_words = ['CHÙA', 'ĐÌNH', 'MIẾU', 'NHẤT', 'NHÀ', 'CẦU', 'CHỢ', 'TRƯỜNG']
    mixed_caps = []
    for e in entities:
        name = e['name']
        words = name.split()
        for w in words:
            if w in vn_prefix_words and not all(ww.isupper() or not ww.isalpha() for ww in words):
                mixed_caps.append((name, e['type'], w))
                break
    print(f"\nMixed caps with Vietnamese all-caps prefix: {len(mixed_caps)}")
    for name, typ, word in mixed_caps[:15]:
        print(f"  [{typ}] {name} (has '{word}')")

    # --- Exact duplicate names ---
    sub_hr("Duplicate names")
    name_counter = Counter(e['name'] for e in entities)
    exact_dupes = {n: c for n, c in name_counter.items() if c > 1}
    print(f"Exact duplicate names: {len(exact_dupes)}")
    for name, count in sorted(exact_dupes.items(), key=lambda x: -x[1])[:20]:
        dupes = [(e['type'], e['id'], e.get('area', '?')) for e in entities if e['name'] == name]
        print(f"  \"{name}\" x{count}:")
        for typ, eid, area in dupes:
            print(f"    [{typ}] {eid} (area={area})")

    # Near-duplicate names
    sub_hr("Near-duplicate names (>90% similar, different IDs)")
    names_list = [(e['name'], e['type'], e['id']) for e in entities]
    near_dupes = []
    # Group by first 3 chars for efficiency
    by_prefix = defaultdict(list)
    for name, typ, eid in names_list:
        prefix = name[:3].lower() if len(name) >= 3 else name.lower()
        by_prefix[prefix].append((name, typ, eid))

    for prefix, items in by_prefix.items():
        if len(items) > 100:
            continue
        for i in range(len(items)):
            for j in range(i+1, len(items)):
                if items[i][0] != items[j][0]:
                    ratio = SequenceMatcher(None, items[i][0], items[j][0]).ratio()
                    if ratio > 0.90:
                        near_dupes.append((items[i], items[j], ratio))

    print(f"Near-duplicate names: {len(near_dupes)}")
    for (n1, t1, id1), (n2, t2, id2), ratio in sorted(near_dupes, key=lambda x: -x[2])[:25]:
        print(f"  ({ratio:.0%}) [{t1}] \"{n1}\" <-> [{t2}] \"{n2}\"")

    # --- Special characters / encoding issues ---
    sub_hr("Names with special characters or encoding issues")
    special = []
    # Allow: ASCII word chars, Vietnamese diacritics (U+00C0-U+024F, U+1E00-U+1EFF),
    # common punctuation, whitespace
    vn_safe_chars = set()
    # Build set of allowed non-ASCII codepoints
    for cp in range(0xC0, 0x250):  # Latin Extended
        vn_safe_chars.add(cp)
    for cp in range(0x1E00, 0x1F00):  # Vietnamese diacritics
        vn_safe_chars.add(cp)
    for cp in range(0x300, 0x370):  # Combining diacritics
        vn_safe_chars.add(cp)
    for e in entities:
        name = e['name']
        issue = None
        # Check for encoding artifacts (mojibake) - these are specific multi-char patterns
        # that appear when UTF-8 is misread as Latin-1
        if re.search(r'Ã¡|Ã©|Ã­|Ã³|Ã¹|Ã |Ãª|Ã¢|Ã´|Æ°|Ã¼|Ã¶|Ã¤', name):
            issue = 'mojibake encoding artifact'
        # Zero-width chars
        elif re.search(r'[​‌‍﻿]', name):
            issue = 'zero-width character'
        # Non-Vietnamese unusual chars (exclude normal Vietnamese)
        else:
            allowed_punct = set('-–—\'"().,:;!?&/+@# ')
            odd_chars = [c for c in name
                         if not c.isascii()
                         and ord(c) not in vn_safe_chars
                         and c not in allowed_punct]
            if odd_chars:
                issue = f'unusual chars: {[(c, hex(ord(c))) for c in odd_chars]}'
        if issue:
            special.append((name, e['type'], issue))

    print(f"Names with special/encoding issues: {len(special)}")
    for name, typ, issue in special[:20]:
        print(f"  [{typ}] \"{name}\" -> {issue}")

    # --- Double type prefixes ---
    sub_hr("Names with double type prefixes")
    prefix_patterns = [
        (r'(?i)^nhà\s*hàng.*quán', 'nhà hàng + quán'),
        (r'(?i)^quán.*nhà\s*hàng', 'quán + nhà hàng'),
        (r'(?i)^chùa.*chùa', 'chùa repeated'),
        (r'(?i)^đình.*đình', 'đình repeated'),
        (r'(?i)^nhà\s*hàng.*nhà\s*hàng', 'nhà hàng repeated'),
        (r'(?i)^cà\s*phê.*cà\s*phê', 'cà phê repeated'),
        (r'(?i)^khách\s*sạn.*hotel', 'khách sạn + hotel'),
        (r'(?i)^hotel.*khách\s*sạn', 'hotel + khách sạn'),
    ]
    double_prefix = []
    for e in entities:
        for pattern, desc in prefix_patterns:
            if re.search(pattern, e['name']):
                double_prefix.append((e['name'], e['type'], desc))
                break

    print(f"Double prefix names: {len(double_prefix)}")
    for name, typ, desc in double_prefix[:20]:
        print(f"  [{typ}] \"{name}\" ({desc})")


# ============================================================================
# PART 5: OCOP Data Audit
# ============================================================================
def part5_ocop_audit(entities):
    hr("PART 5: OCOP DATA AUDIT")

    ocop_entities = []
    for e in entities:
        attrs = e.get('attributes', {}) or {}
        name_lower = e['name'].lower()
        summary_lower = (e.get('summary', '') or '').lower()

        is_ocop = False
        ocop_info = {}

        # Check attributes
        for k, v in attrs.items():
            if 'ocop' in k.lower():
                is_ocop = True
                ocop_info[k] = v
            if 'star' in k.lower() or 'sao' in k.lower():
                ocop_info[k] = v

        # Check name/summary
        if 'ocop' in name_lower or 'ocop' in summary_lower:
            is_ocop = True

        # Check tags
        tags = attrs.get('tags', []) or []
        if isinstance(tags, list):
            for tag in tags:
                if 'ocop' in str(tag).lower():
                    is_ocop = True

        if is_ocop:
            ocop_entities.append((e, ocop_info))

    print(f"Total OCOP-related entities: {len(ocop_entities)}")
    print(f"By type:")
    ocop_type_counter = Counter(e['type'] for e, _ in ocop_entities)
    for t, c in ocop_type_counter.most_common():
        print(f"  {t}: {c}")

    # --- OCOP rating formats ---
    sub_hr("OCOP rating formats found")
    rating_formats = Counter()
    rating_samples = defaultdict(list)
    missing_rating = []
    missing_year = []

    for e, ocop_info in ocop_entities:
        attrs = e.get('attributes', {}) or {}
        ocop_val = attrs.get('ocop', ocop_info.get('ocop', ''))

        if ocop_val:
            val_str = str(ocop_val)
            if re.match(r'^\d+$', val_str):
                fmt = f'integer ({val_str})'
            elif re.search(r'\d\s*sao', val_str, re.I):
                fmt = 'X sao format'
            elif re.search(r'\d\s*star', val_str, re.I):
                fmt = 'X star format'
            elif re.search(r'★|⭐|🌟', val_str):
                fmt = 'emoji stars'
            elif val_str.lower() in ('true', 'yes', 'có'):
                fmt = 'boolean'
            else:
                fmt = f'other: {val_str[:50]}'
            rating_formats[fmt] += 1
            if len(rating_samples[fmt]) < 5:
                rating_samples[fmt].append(f"{e['name']}: {val_str}")
        else:
            missing_rating.append(e['name'])

        # Check certification year
        has_year = False
        for k, v in attrs.items():
            if 'year' in k.lower() or 'nam' in k.lower() or 'certification' in k.lower():
                has_year = True
                break
        if not has_year:
            # Also check in ocop attribute value itself
            if ocop_val and re.search(r'20[12]\d', str(ocop_val)):
                has_year = True
        if not has_year:
            missing_year.append(e['name'])

    print("Rating formats:")
    for fmt, count in rating_formats.most_common():
        print(f"  {fmt}: {count}")
        for s in rating_samples[fmt]:
            print(f"    - {s}")

    print(f"\nOCOP entities missing star rating: {len(missing_rating)}")
    for n in missing_rating[:15]:
        print(f"  - {n}")

    print(f"\nOCOP entities missing certification year: {len(missing_year)}")
    for n in missing_year[:15]:
        print(f"  - {n}")

    # Show all OCOP entities for review
    sub_hr("All OCOP entities")
    for e, ocop_info in ocop_entities:
        attrs = e.get('attributes', {}) or {}
        print(f"  [{e['type']}] {e['name']}")
        print(f"    area={e.get('area','?')} ocop={attrs.get('ocop','?')} attrs_keys={list(attrs.keys())[:8]}")


# ============================================================================
# PART 6: Address Normalization
# ============================================================================
def part6_address_normalization(entities):
    hr("PART 6: ADDRESS NORMALIZATION")

    with_addr = []
    without_addr = []

    for e in entities:
        attrs = e.get('attributes', {}) or {}
        addr = attrs.get('address', '')
        if addr:
            with_addr.append((e, addr))
        else:
            without_addr.append(e)

    print(f"Entities WITH address:    {len(with_addr)}")
    print(f"Entities WITHOUT address: {len(without_addr)}")
    print(f"\nWithout address, by type:")
    no_addr_type = Counter(e['type'] for e in without_addr)
    for t, c in no_addr_type.most_common():
        print(f"  {t}: {c}")

    # --- Address format patterns ---
    sub_hr("Address format patterns")
    patterns = {
        'has_ward': 0,
        'has_district': 0,
        'has_province': 0,
        'has_tp': 0,
        'has_comma_sep': 0,
        'has_dash_sep': 0,
        'uses_P_dot': 0,  # P. for Phường
        'uses_Q_dot': 0,  # Q. for Quận
        'uses_H_dot': 0,  # H. for Huyện
        'uses_full_phuong': 0,
        'uses_full_huyen': 0,
        'uses_TX': 0,  # Thị xã
    }

    province_patterns = Counter()
    incomplete_addr = []

    for e, addr in with_addr:
        addr_lower = addr.lower()

        if re.search(r'(phường|p\.)\s', addr_lower):
            patterns['has_ward'] += 1
        if re.search(r'(xã)\s', addr_lower):
            patterns['has_ward'] += 1
        if re.search(r'(quận|q\.)\s', addr_lower):
            patterns['has_district'] += 1
        if re.search(r'(huyện|h\.)\s', addr_lower):
            patterns['has_district'] += 1
        if re.search(r'(tỉnh|province)\s', addr_lower):
            patterns['has_province'] += 1
        if re.search(r'(thành phố|tp\.)\s', addr_lower):
            patterns['has_tp'] += 1
        if ',' in addr:
            patterns['has_comma_sep'] += 1
        if ' - ' in addr:
            patterns['has_dash_sep'] += 1
        if re.search(r'\bP\.\s', addr):
            patterns['uses_P_dot'] += 1
        if re.search(r'\bQ\.\s', addr):
            patterns['uses_Q_dot'] += 1
        if re.search(r'\bH\.\s', addr):
            patterns['uses_H_dot'] += 1
        if re.search(r'(?i)\bPhường\s', addr):
            patterns['uses_full_phuong'] += 1
        if re.search(r'(?i)\bHuyện\s', addr):
            patterns['uses_full_huyen'] += 1
        if re.search(r'(?i)(thị xã|TX\.)', addr):
            patterns['uses_TX'] += 1

        # Province name extraction
        for prov in ['Vĩnh Long', 'Bến Tre', 'Trà Vinh']:
            if prov.lower() in addr_lower:
                province_patterns[prov] += 1

        # Check completeness
        has_ward_or_xa = bool(re.search(r'(?i)(phường|p\.|xã)', addr))
        has_district = bool(re.search(r'(?i)(quận|q\.|huyện|h\.|thành phố|tp\.|thị xã|tx)', addr))
        if not has_ward_or_xa or not has_district:
            incomplete_addr.append((e['name'], e['type'], addr, has_ward_or_xa, has_district))

    print("Format pattern counts:")
    for k, v in patterns.items():
        print(f"  {k:25s}: {v:5d} / {len(with_addr)}")

    print(f"\nProvince mentions in addresses:")
    for prov, c in province_patterns.most_common():
        print(f"  {prov}: {c}")

    # --- Inconsistent province names post-merger ---
    sub_hr("Address issues post-merger (3 provinces merging)")
    # Look for old province names or inconsistencies
    print("NOTE: VL+BT+TV merging into one province - check for outdated references")
    old_province_refs = []
    for e, addr in with_addr:
        if re.search(r'(?i)tỉnh\s*(Vĩnh Long|Bến Tre|Trà Vinh)', addr):
            old_province_refs.append((e['name'], e['type'], addr[:100]))
    print(f"Addresses explicitly mentioning 'tỉnh X': {len(old_province_refs)}")
    for name, typ, addr in old_province_refs[:15]:
        print(f"  [{typ}] {name}: {addr}")

    # --- Missing ward/district ---
    sub_hr("Addresses missing ward/district level")
    print(f"Addresses missing ward/xã OR district: {len(incomplete_addr)}")
    for name, typ, addr, has_w, has_d in incomplete_addr[:20]:
        missing = []
        if not has_w:
            missing.append('ward/xã')
        if not has_d:
            missing.append('district')
        print(f"  [{typ}] {name}: missing {','.join(missing)}")
        print(f"    addr: {addr[:120]}")


# ============================================================================
# PART 7: Relationship Quality
# ============================================================================
def part7_relationship_quality(entities, relationships, entity_map):
    hr("PART 7: RELATIONSHIP QUALITY")

    rel_type_counts = Counter(r['type'] for r in relationships)
    print("Relationships by type:")
    for t, c in rel_type_counts.most_common():
        print(f"  {t:25s}: {c:6d}")
    print(f"  {'TOTAL':25s}: {len(relationships):6d}")

    # --- "associated_with" sampling ---
    sub_hr("associated_with relationships: sample 20 for semantic validity")
    associated = [r for r in relationships if r['type'] == 'associated_with']
    import random
    random.seed(42)
    sample = random.sample(associated, min(20, len(associated)))
    for r in sample:
        from_e = entity_map.get(r['from'])
        to_e = entity_map.get(r['to'])
        from_name = from_e['name'] if from_e else f"MISSING({r['from']})"
        to_name = to_e['name'] if to_e else f"MISSING({r['to']})"
        from_type = from_e['type'] if from_e else '?'
        to_type = to_e['type'] if to_e else '?'
        print(f"  [{from_type}] {from_name}  -->  [{to_type}] {to_name}")

    # --- Dangling references ---
    sub_hr("Dangling relationship references (entity not found)")
    entity_ids = set(e['id'] for e in entities)
    dangling_from = [(r['from'], r['to'], r['type']) for r in relationships if r['from'] not in entity_ids]
    dangling_to = [(r['from'], r['to'], r['type']) for r in relationships if r['to'] not in entity_ids]
    print(f"Dangling 'from' references: {len(dangling_from)}")
    for f, t, tp in dangling_from[:10]:
        print(f"  {f} --> {t} ({tp})")
    print(f"Dangling 'to' references: {len(dangling_to)}")
    for f, t, tp in dangling_to[:10]:
        print(f"  {f} --> {t} ({tp})")

    # --- High relationship count entities ---
    sub_hr("Entities with suspiciously high relationship counts (>30)")
    rel_counts = Counter()
    for r in relationships:
        rel_counts[r['from']] += 1
        rel_counts[r['to']] += 1

    high_rel = [(eid, count) for eid, count in rel_counts.most_common(50) if count > 30]
    print(f"Entities with >30 relationships: {len(high_rel)}")
    for eid, count in high_rel[:25]:
        e = entity_map.get(eid)
        name = e['name'] if e else f"UNKNOWN({eid})"
        typ = e['type'] if e else '?'
        print(f"  {count:4d} rels: [{typ}] {name} ({eid})")

    # --- Bidirectional duplicates ---
    sub_hr("Bidirectional duplicates (A->B and B->A same type)")
    edge_set = set()
    bidir_dupes = []
    for r in relationships:
        key = (r['from'], r['to'], r['type'])
        reverse = (r['to'], r['from'], r['type'])
        if reverse in edge_set:
            bidir_dupes.append((r['from'], r['to'], r['type']))
        edge_set.add(key)

    print(f"Bidirectional duplicates: {len(bidir_dupes)}")
    bidir_by_type = Counter(t for _, _, t in bidir_dupes)
    for t, c in bidir_by_type.most_common():
        print(f"  {t}: {c}")

    # Show samples
    for f, t, tp in bidir_dupes[:10]:
        from_e = entity_map.get(f)
        to_e = entity_map.get(t)
        fn = from_e['name'] if from_e else f
        tn = to_e['name'] if to_e else t
        print(f"    [{tp}] {fn} <--> {tn}")

    # --- Exact duplicate relationships ---
    sub_hr("Exact duplicate relationships (same from/to/type)")
    edge_counter = Counter((r['from'], r['to'], r['type']) for r in relationships)
    exact_dup_rels = {k: v for k, v in edge_counter.items() if v > 1}
    print(f"Exact duplicate relationships: {len(exact_dup_rels)}")
    for (f, t, tp), count in sorted(exact_dup_rels.items(), key=lambda x: -x[1])[:15]:
        from_e = entity_map.get(f)
        to_e = entity_map.get(t)
        fn = from_e['name'] if from_e else f
        tn = to_e['name'] if to_e else t
        print(f"  x{count}: [{tp}] {fn} --> {tn}")


# ============================================================================
# PART 8: Source/Provenance Audit
# ============================================================================
def part8_source_audit(entities):
    hr("PART 8: SOURCE/PROVENANCE AUDIT")

    source_types = Counter()
    source_domains = Counter()
    source_formats = Counter()
    no_source = []
    date_formats = Counter()
    date_samples = defaultdict(list)

    for e in entities:
        sources = e.get('source', []) or []
        if not sources:
            no_source.append((e['name'], e['type']))
            source_types['(none)'] += 1
            continue

        for src in sources:
            if isinstance(src, dict):
                # Determine source type
                if 'type' in src:
                    source_types[src['type']] += 1
                elif 'name' in src:
                    source_types[f"name:{src['name']}"] += 1
                elif 'url' in src and src['url']:
                    source_types['has_url_only'] += 1
                elif 'title' in src:
                    source_types['has_title_only'] += 1
                else:
                    source_types['(empty dict)'] += 1

                # Extract URLs and domains
                url = src.get('url', '')
                if url:
                    domain_match = re.search(r'https?://([^/]+)', url)
                    if domain_match:
                        source_domains[domain_match.group(1)] += 1

                # Check date formats
                for date_key in ['scraped_at', 'date', 'crawled_at', 'updated']:
                    if date_key in src and src[date_key]:
                        val = str(src[date_key])
                        if re.match(r'\d{4}-\d{2}-\d{2}T', val):
                            fmt = 'ISO 8601'
                        elif re.match(r'\d{4}-\d{2}-\d{2}$', val):
                            fmt = 'YYYY-MM-DD'
                        elif re.match(r'\d{2}/\d{2}/\d{4}', val):
                            fmt = 'DD/MM/YYYY'
                        else:
                            fmt = f'other: {val[:30]}'
                        date_formats[fmt] += 1
                        if len(date_samples[fmt]) < 3:
                            date_samples[fmt].append(val)

                # Track source dict key structure
                source_formats[str(sorted(src.keys()))] += 1
            elif isinstance(src, str):
                source_types[f'string: {src[:50]}'] += 1

    print("Source types:")
    for t, c in source_types.most_common():
        print(f"  {t:40s}: {c:5d}")

    sub_hr("Source URL domains")
    for d, c in source_domains.most_common():
        print(f"  {d:40s}: {c:5d}")

    sub_hr("Source dict key structures")
    for s, c in source_formats.most_common():
        print(f"  {s:60s}: {c:5d}")

    sub_hr("Date formats in sources")
    for fmt, c in date_formats.most_common():
        print(f"  {fmt}: {c}")
        for sample in date_samples[fmt]:
            print(f"    - {sample}")

    print(f"\nEntities with no source: {len(no_source)}")
    no_src_by_type = Counter(t for _, t in no_source)
    for t, c in no_src_by_type.most_common():
        print(f"  {t}: {c}")


# ============================================================================
# SUMMARY DASHBOARD
# ============================================================================
def summary_dashboard(entities, relationships):
    hr("NORMALIZATION SUMMARY DASHBOARD")

    total = len(entities)
    total_rels = len(relationships)

    # Quick counts
    no_summary = sum(1 for e in entities if not (e.get('summary', '') or '').strip())
    no_coords = sum(1 for e in entities if not e.get('coordinates'))
    no_area = sum(1 for e in entities if not e.get('area'))
    no_attrs = sum(1 for e in entities if not (e.get('attributes') or {}))

    # Confidence distribution
    conf_vals = [e.get('confidence', 0) or 0 for e in entities]
    low_conf = sum(1 for c in conf_vals if c < 0.5)
    med_conf = sum(1 for c in conf_vals if 0.5 <= c < 0.8)
    high_conf = sum(1 for c in conf_vals if c >= 0.8)

    print(f"Total entities:       {total}")
    print(f"Total relationships:  {total_rels}")
    print(f"")
    print(f"Missing summary:      {no_summary:5d} ({no_summary/total*100:.1f}%)")
    print(f"Missing coordinates:  {no_coords:5d} ({no_coords/total*100:.1f}%)")
    print(f"Missing area:         {no_area:5d} ({no_area/total*100:.1f}%)")
    print(f"No attributes:        {no_attrs:5d} ({no_attrs/total*100:.1f}%)")
    print(f"")
    print(f"Confidence distribution:")
    print(f"  Low  (<0.5):  {low_conf:5d} ({low_conf/total*100:.1f}%)")
    print(f"  Med  (0.5-0.8): {med_conf:5d} ({med_conf/total*100:.1f}%)")
    print(f"  High (>=0.8): {high_conf:5d} ({high_conf/total*100:.1f}%)")

    # Area distribution
    area_counts = Counter(e.get('area', '(none)') or '(none)' for e in entities)
    print(f"\nArea distribution:")
    for a, c in area_counts.most_common():
        print(f"  {a:20s}: {c:5d} ({c/total*100:.1f}%)")


# ============================================================================
# MAIN
# ============================================================================
if __name__ == '__main__':
    print("Loading data...")
    data = load_data()
    entities = data['entities']
    relationships = data['relationships']
    entity_map = {e['id']: e for e in entities}
    print(f"Loaded {len(entities)} entities, {len(relationships)} relationships.\n")

    summary_dashboard(entities, relationships)
    part1_type_classification(entities, entity_map)
    part2_attribute_schema(entities)
    part3_summary_quality(entities)
    part4_name_normalization(entities)
    part5_ocop_audit(entities)
    part6_address_normalization(entities)
    part7_relationship_quality(entities, relationships, entity_map)
    part8_source_audit(entities)

    hr("ANALYSIS COMPLETE")
    print("Script finished. Review findings above to plan normalization tasks.")
