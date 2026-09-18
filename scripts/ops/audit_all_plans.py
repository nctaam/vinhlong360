import json
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8")
db = sqlite3.connect("agent/data/vinhlong360.db")
c = db.cursor()

print("=" * 60)
print("BÁO CÁO KIỂM TOÁN VÀ TIẾN ĐỘ THỰC HIỆN CÁC KẾ HOẠCH TỐI ƯU")
print("=" * 60)

# 1. Total entities
total = c.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
print(f"\n1. TỔNG SỐ THỰC THỂ: {total}")

# 2. Verified photos count & by category
verified = 0
unverified_by_type = {}
verified_by_type = {}
for r in c.execute("SELECT id, type, attributes FROM entities").fetchall():
    attrs = json.loads(r[2] or "{}")
    t = r[1]
    if attrs.get("is_verified_photo"):
        verified += 1
        verified_by_type[t] = verified_by_type.get(t, 0) + 1
    else:
        unverified_by_type[t] = unverified_by_type.get(t, 0) + 1

print("\n2. TIẾN ĐỘ CHUẨN HÓA HÌNH ẢNH & E-E-A-T (is_verified_photo):")
print(f"   Đã kiểm chứng: {verified} / {total} ({verified/total*100:.2f}%)")
print(f"   Chưa kiểm chứng: {total - verified} / {total} ({(total-verified)/total*100:.2f}%)")

print("\n   [+] Các phân hệ ĐÃ ĐẠT 100% ĐỘ PHỦ:")
for t in sorted(verified_by_type.keys()):
    if unverified_by_type.get(t, 0) == 0:
        print(f"       * {t}: {verified_by_type[t]} / {verified_by_type[t]} (100.0%)")

print("\n   [-] Các phân hệ ĐANG THỰC HIỆN:")
for t, cnt in sorted(unverified_by_type.items(), key=lambda x: -x[1]):
    v_cnt = verified_by_type.get(t, 0)
    pct = v_cnt / (v_cnt + cnt) * 100
    print(f"       * {t}: {v_cnt}/{v_cnt+cnt} ({pct:.1f}%) | Còn lại: {cnt}")

# 3. Coordinates & Spatial GIS
missing_coords = 0
valid_coords = 0
for r in c.execute("SELECT coordinates, type FROM entities").fetchall():
    if r[1] == 'place':
        continue
    try:
        coords = json.loads(r[0] or "[]")
        if isinstance(coords, list) and len(coords) >= 2 and coords[0] != 0 and coords[1] != 0:
            valid_coords += 1
        elif isinstance(coords, dict) and coords.get("lat") and coords.get("lng"):
            valid_coords += 1
        else:
            missing_coords += 1
    except Exception:
        missing_coords += 1

approx_coords = 0
for r in c.execute("SELECT attributes FROM entities").fetchall():
    attrs = json.loads(r[0] or "{}")
    if attrs.get("coords_approximate"):
        approx_coords += 1

print("\n3. KHÔNG GIAN GIS & TỌA ĐỘ:")
print(f"   * Thực thể ngoài place có tọa độ hợp lệ: {valid_coords}")
print(f"   * Thực thể ngoài place khuyết tọa độ: {missing_coords}")
print(f"   * Thực thể mang cờ tọa độ gần đúng (coords_approximate): {approx_coords}")

# 4. Relationships and Graph topology
total_rels = c.execute("SELECT COUNT(*) FROM relationships").fetchone()[0]
orphan_nodes = c.execute("""
    SELECT COUNT(*) FROM entities
    WHERE id NOT IN (SELECT from_id FROM relationships UNION SELECT to_id FROM relationships)
""").fetchone()[0]
print("\n4. ĐỒ THỊ TRI THỨC (KNOWLEDGE GRAPH):")
print(f"   * Tổng số liên kết quan hệ (relationships): {total_rels}")
print(f"   * Thực thể cô lập (orphan nodes - 0 quan hệ): {orphan_nodes}")

# 5. Itineraries check
total_itins = c.execute("SELECT COUNT(*) FROM itineraries").fetchone()[0]
print("\n5. TUYẾN DU LỊCH & LỘ TRÌNH (ITINERARIES):")
print(f"   * Tổng số tuyến lộ trình: {total_itins}")

# 6. Check for forbidden administrative references (R10.7)
r107_violations = []
for r in c.execute("SELECT id, name, summary, description, address FROM entities").fetchall():
    text = f"{r[1]} {r[2]} {r[3]} {r[4]}"
    if "tỉnh Bến Tre" in text or "tỉnh Trà Vinh" in text:
        r107_violations.append((r[0], r[1]))
print("\n6. RÀ SOÁT TÀN DƯ HÀNH CHÍNH (QUY TẮC R10.7):")
print(f"   * Số thực thể còn chứa cụm 'tỉnh Bến Tre' hoặc 'tỉnh Trà Vinh': {len(r107_violations)}")

# 7. Check AI slop / filler phrases in database
slop_phrases = [
    "tọa lạc tại", "vùng sông nước", "sông nước nam bộ", "điểm đến lý tưởng",
    "thiên đường", "hòa mình", "say đắm", "hút hồn", "níu chân", "bức tranh thủy mặc"
]
slop_hits = {p: 0 for p in slop_phrases}
for r in c.execute("SELECT summary, description FROM entities").fetchall():
    text = f"{r[0]} {r[1]}".lower()
    for p in slop_phrases:
        if p in text:
            slop_hits[p] += 1
print("\n7. RÀ SOÁT TỪ NGỮ AI SLOP:")
total_slop = sum(slop_hits.values())
print(f"   * Tổng số phát hiện từ ngữ sáo rỗng: {total_slop}")
for p, c_cnt in slop_hits.items():
    if c_cnt > 0:
        print(f"       * '{p}': {c_cnt} lần")

print("\n" + "=" * 60)
