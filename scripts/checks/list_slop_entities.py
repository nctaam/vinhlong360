import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

db = sqlite3.connect('agent/data/vinhlong360.db')
rows = db.execute("SELECT id, name, type, summary, description FROM entities").fetchall()

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

count = 0
for r in rows:
    eid, name, ctype, summary, desc = r
    full_text = f"{summary or ''} {desc or ''}".lower()
    matched = [p for p in ai_slop_phrases if p in full_text]
    if matched:
        count += 1
        print(f"{count}. [{eid}] {name} ({ctype}): {matched}")
        if summary:
            print(f"   Summary: {summary[:120]}")
