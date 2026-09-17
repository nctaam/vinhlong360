import os
import sqlite3
import json

db = sqlite3.connect('agent/data/vinhlong360.db')
rows = db.execute("SELECT id, name, type, summary, description, attributes FROM entities").fetchall()

unverified = []
for r in rows:
    eid, name, ctype, summary, desc, attrs = r
    attrs_obj = json.loads(attrs or '{}')
    if not attrs_obj.get('is_verified_photo'):
        img_path = f'web-nuxt/public/img/entities/{eid}.webp'
        has_img = os.path.exists(img_path) and os.path.getsize(img_path) > 1024
        unverified.append({
            'id': eid,
            'name': name,
            'type': ctype,
            'summary': summary or '',
            'description': desc or '',
            'attrs': attrs_obj,
            'has_img': has_img
        })

print(f"Total unverified: {len(unverified)}")
events = [x for x in unverified if x['type'] == 'event' and x['has_img']]
print(f"Unverified events with valid image: {len(events)}")

nature = [x for x in unverified if x['type'] == 'nature' and x['has_img']]
print(f"Unverified nature with valid image: {len(nature)}")

attractions = [x for x in unverified if x['type'] == 'attraction' and x['has_img']]
print(f"Unverified attractions with valid image: {len(attractions)}")

import sys
sys.stdout.reconfigure(encoding='utf-8')

# Pick 40 candidates: 40 events / festivals
batch_15_candidates = events[:40]
print(f"\nSelected {len(batch_15_candidates)} candidates for Batch 15:")
for idx, c in enumerate(batch_15_candidates, 1):
    print(f"{idx}. {c['id']} | {c['name']}")
    print(f"   Summary: {c['summary'][:100]}...")
