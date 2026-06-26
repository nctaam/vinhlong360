import sqlite3, json, sys, io
from datetime import datetime, date, timedelta
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = sqlite3.connect("agent/data/vinhlong360.db")
cur = conn.cursor()
cur.execute("SELECT id, name, type, season, attributes FROM entities WHERE type='event' ORDER BY id")
rows = cur.fetchall()

today = date.today()
cutoff = today + timedelta(days=30)

print(f"Total events: {len(rows)}")
print(f"Today: {today}, Cutoff: {cutoff}\n")

excluded_mua = []
excluded_month_mismatch = []
upcoming_reliable = []

for r in rows:
    attrs = json.loads(r[4]) if r[4] else {}
    ds = attrs.get("date_start", "")
    cat = attrs.get("category", "")
    m = attrs.get("month", "")
    lunar = attrs.get("lunar_date", "")

    if cat == "mua":
        excluded_mua.append(f"  {r[0]}: {r[1]}")
        continue

    if ds and m and isinstance(m, (int, float)):
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
            if int(m) != d.month:
                excluded_month_mismatch.append(f"  {r[0]}: {r[1]} (month={m}, ds_month={d.month}, ds={ds})")
                continue
        except (ValueError, TypeError):
            pass

    if ds:
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
            if today <= d <= cutoff:
                upcoming_reliable.append(f"  {r[0]}: {r[1]} (ds={ds}, lunar={lunar})")
        except (ValueError, TypeError):
            pass

print(f"=== EXCLUDED: cat=mua ({len(excluded_mua)}) ===")
for x in excluded_mua:
    print(x)

print(f"\n=== EXCLUDED: month mismatch ({len(excluded_month_mismatch)}) ===")
for x in excluded_month_mismatch:
    print(x)

print(f"\n=== UPCOMING (next 30 days, reliable) ({len(upcoming_reliable)}) ===")
for x in upcoming_reliable:
    print(x)

conn.close()
