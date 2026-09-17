import sqlite3
import json
from collections import Counter
import sys

sys.stdout.reconfigure(encoding='utf-8')

db = sqlite3.connect('agent/data/vinhlong360.db')
rows = db.execute('SELECT id, name, type, summary, description, attributes, images FROM entities').fetchall()

total = len(rows)
verified_photo = 0
unverified_photo = 0
by_type_unverified = Counter()
by_type_total = Counter()
thin_desc = 0
dup_desc_summary = 0

ai_slop_phrases = [
    'miền tây sông nước',
    'sông nước nam bộ',
    'vùng sông nước',
    'điểm đến lý tưởng',
    'không thể bỏ lỡ',
    'thơ mộng, bình yên',
    'hãy đến và cảm nhận',
    'tọa lạc tại',
    'đậm đà bản sắc',
    'hiền hoà mến khách',
    'thuần khiết nhất vùng'
]
slop_matches = Counter()
entities_with_slop = []

for r in rows:
    eid, name, ctype, summary, desc, attrs_str, imgs_str = r
    attrs = json.loads(attrs_str or '{}')
    by_type_total[ctype] += 1

    if attrs.get('is_verified_photo'):
        verified_photo += 1
    else:
        unverified_photo += 1
        by_type_unverified[ctype] += 1

    full_text = f"{summary or ''} {desc or ''}".lower()
    matched_phrases = []
    for phrase in ai_slop_phrases:
        if phrase in full_text:
            slop_matches[phrase] += 1
            matched_phrases.append(phrase)

    if matched_phrases:
        entities_with_slop.append((eid, name, ctype, matched_phrases))

    words = len((desc or '').split())
    if words < 30:
        thin_desc += 1
    if summary and desc and summary.strip() == desc.strip():
        dup_desc_summary += 1

print(f"Total entities: {total}")
print(f"Verified photo: {verified_photo}")
print(f"Unverified photo: {unverified_photo}")
print(f"Thin descriptions (<30 words): {thin_desc}")
print(f"Duplicate summary==desc: {dup_desc_summary}")
print("\nUnverified breakdown by type:")
for t, c in by_type_unverified.most_common():
    print(f"  - {t}: {c} / {by_type_total[t]}")

print("\nAI Slop phrase occurrences across DB:")
for p, c in slop_matches.most_common():
    print(f"  - '{p}': {c}")

print(f"\nTotal entities containing AI slop phrases: {len(entities_with_slop)}")
print("Sample entities with slop (first 10):")
for eid, name, ctype, phrases in entities_with_slop[:10]:
    print(f"  - [{eid}] ({ctype}) {name}: matched {phrases}")
