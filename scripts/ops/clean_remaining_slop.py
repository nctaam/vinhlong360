import json
import sqlite3

db_path = "agent/data/vinhlong360.db"
json_path = "web/data.json"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

json_entities = {e["id"]: e for e in data["entities"]}

# 1. dinh-tan-hoa-w3
row = cur.execute("SELECT description FROM entities WHERE id = 'dinh-tan-hoa-w3'").fetchone()
if row:
    desc = row[0].replace("nhưng có sức níu chân bằng sự trầm mặc", "nhưng tạo ấn tượng sâu sắc bằng sự trầm mặc")
    cur.execute("UPDATE entities SET description = ? WHERE id = 'dinh-tan-hoa-w3'", (desc,))
    if "dinh-tan-hoa-w3" in json_entities:
        json_entities["dinh-tan-hoa-w3"]["description"] = desc

# 2. bun-nuoc-leo-cay-sung-tra-vinh
row = cur.execute("SELECT description FROM entities WHERE id = 'bun-nuoc-leo-cay-sung-tra-vinh'").fetchone()
if row:
    desc = row[0].replace("Bún Nước Lèo Cây Sung níu chân thực khách", "Bún Nước Lèo Cây Sung thu hút thực khách")
    cur.execute("UPDATE entities SET description = ? WHERE id = 'bun-nuoc-leo-cay-sung-tra-vinh'", (desc,))
    if "bun-nuoc-leo-cay-sung-tra-vinh" in json_entities:
        json_entities["bun-nuoc-leo-cay-sung-tra-vinh"]["description"] = desc

conn.commit()
conn.close()

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("Cleaned 2 remaining AI slop occurrences in both DB and JSON!")
