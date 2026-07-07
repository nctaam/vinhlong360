"""Cleanup duplicates + fix date anomalies."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")
from database import db
db.initialize()

# ── DELETE duplicates ──
DELETE_IDS = [
    # Nghinh Ông chung — đã có 3 entity cụ thể theo địa phương
    "le-hoi-nghinh-ong",

    # Cúng Trăng Ok Om Bok — là nghi thức trong Ok Om Bok, trùng
    "le-cung-trang-ok-om-bok",

    # "Hội đua ghe ngo Sóc Trăng" nhưng area=tra-vinh — tên sai, trùng hội thi ghe ngo TV
    "hoi-dua-ghe-ngo-soc-trang",

    # Chôl Chnăm Thmây — trùng Lễ Chôl Chhnam Thmây (cùng lễ, tra-vinh)
    "chol-chnam-thmay",

    # Ok Om Bok Trà Cú — trùng Ok Om Bok chung (cùng tỉnh)
    "le-hoi-ok-om-bok-cua-dong-bao-khmer-tra-cu",

    # Lễ hội bánh dân gian — trùng Ngày hội Bánh dân gian Nam Bộ
    "le-hoi-banh-dan-gian",

    # Vu Lan thắng hội — trùng Lễ Vu Lan (cùng dịp, cùng area)
    "vu-lan-thang-hoi",

    # Sene Đônta (Ok Om Bok) — gộp 2 lễ → span 46 ngày, đã có sen-dolta + ok-om-bok riêng
    "le-hoi-sene-donta-ok-om-bok",

    # Hạ điền + Thượng điền Đình Hòa Tịnh — span 168 ngày (gộp 2 lễ cách nhau nửa năm)
    # Đã có le-ha-dien-dinh-tan-hoa riêng; entity này gây nhiễu lịch
    "le-ha-dien-va-thuong-dien-dinh-hoa-tinh",
]

print("=== Deleting duplicates ===")
deleted = 0
for eid in DELETE_IDS:
    e = db.get_entity(eid)
    if not e:
        print(f"  SKIP (not found): {eid}")
        continue
    db.delete_entity(eid)
    deleted += 1
    print(f"  - {eid}: {e['name']}")
print(f"  Deleted: {deleted}")

# ── FIX date anomalies ──
print("\n=== Fixing date anomalies ===")

# Nghinh Ông Bình Thắng: lunar "16 tháng 6 ÂL" = 2026-07-30 DL (not March!)
# Tháng 6 âm lịch 2026: bắt đầu 14/7/2026 DL → ngày 16 = 29-30/7
e = db.get_entity("le-hoi-nghinh-ong-binh-thang")
if e:
    attrs = e.get("attributes") or {}
    old_ds = attrs.get("date_start")
    attrs["date_start"] = "2026-07-29"
    attrs["date_end"] = "2026-07-30"
    e["attributes"] = attrs
    db.upsert_entity(e)
    print(f"  Fixed Nghinh Ông Bình Thắng: {old_ds} → 2026-07-29~07-30 (16 tháng 6 ÂL)")

# Lễ Vía Bà Cố Hỷ: lunar "Rằm tháng 2 ÂL"
# Tháng 2 ÂL 2026: rằm = 2026-04-03 (15 tháng 2 ÂL), NOT 04-10
e = db.get_entity("le-via-ba-co-hy")
if e:
    attrs = e.get("attributes") or {}
    old_ds = attrs.get("date_start")
    attrs["date_start"] = "2026-04-03"
    attrs["date_end"] = "2026-04-03"
    e["attributes"] = attrs
    db.upsert_entity(e)
    print(f"  Fixed Vía Bà Cố Hỷ: {old_ds} → 2026-04-03 (Rằm tháng 2 ÂL)")

# Kỳ Yên Đình Tân Giai: lunar "16–17 tháng 3 ÂL" nhưng date=03-15 (tháng 2 ÂL!)
# Tháng 3 ÂL 2026: ngày 16 = 2026-05-02
e = db.get_entity("le-hoi-ky-yen-ha-dien-dinh-tan-giai")
if e:
    attrs = e.get("attributes") or {}
    old_ds = attrs.get("date_start")
    attrs["date_start"] = "2026-05-02"
    attrs["date_end"] = "2026-05-03"
    e["attributes"] = attrs
    db.upsert_entity(e)
    print(f"  Fixed Kỳ Yên Đình Tân Giai: {old_ds} → 2026-05-02~05-03 (16–17 tháng 3 ÂL)")

# Kỳ Yên Đình Phú Lễ: lunar "18–19 tháng 3 ÂL"
# Tháng 3 ÂL 2026: ngày 18 = 2026-05-04
e = db.get_entity("le-hoi-ky-yen-dinh-phu-le")
if e:
    attrs = e.get("attributes") or {}
    old_ds = attrs.get("date_start")
    attrs["date_start"] = "2026-05-04"
    attrs["date_end"] = "2026-05-05"
    e["attributes"] = attrs
    db.upsert_entity(e)
    print(f"  Fixed Kỳ Yên Đình Phú Lễ: {old_ds} → 2026-05-04~05-05 (18–19 tháng 3 ÂL)")

# Nghinh Ông Duyên Hải: lunar "10–12 tháng 3 ÂL"
# Tháng 3 ÂL 2026: ngày 10 = 2026-04-26
e = db.get_entity("le-hoi-nghinh-ong-duyen-hai")
if e:
    attrs = e.get("attributes") or {}
    old_ds = attrs.get("date_start")
    attrs["date_start"] = "2026-04-26"
    attrs["date_end"] = "2026-04-28"
    e["attributes"] = attrs
    db.upsert_entity(e)
    print(f"  Fixed Nghinh Ông Duyên Hải: {old_ds} → 2026-04-26~04-28 (10–12 tháng 3 ÂL)")

# Nghinh Ông Lăng Cồn Tàu: lunar "10–11 tháng 3 ÂL"
e = db.get_entity("le-hoi-nghinh-ong-lang-con-tau")
if e:
    attrs = e.get("attributes") or {}
    old_ds = attrs.get("date_start")
    attrs["date_start"] = "2026-04-26"
    attrs["date_end"] = "2026-04-27"
    e["attributes"] = attrs
    db.upsert_entity(e)
    print(f"  Fixed Nghinh Ông Lăng Cồn Tàu: {old_ds} → 2026-04-26~04-27 (10–11 tháng 3 ÂL)")

# Lễ giỗ Nguyễn Đình Chiểu: lunar "Mùng 3 tháng 7 ÂL"
# Tháng 7 ÂL (nhuận) 2026: bắt đầu 13/8 DL → mùng 3 = 15/8
# Nhưng wait — 2026 có tháng 6 nhuận. Let me recalc:
# Tháng 6 ÂL: 14/7–12/8; Tháng 6 nhuận: 13/8–10/9; Tháng 7 ÂL: 11/9–10/10
# Mùng 3 tháng 7 ÂL = 13/9/2026
e = db.get_entity("le-gio-nguyen-dinh-chieu")
if e:
    attrs = e.get("attributes") or {}
    old_ds = attrs.get("date_start")
    # Actually the historical date is July 3 DL (ngày mất NĐC = 3/7/1888)
    # But lunar says "mùng 3 tháng 7 ÂL"
    # Tháng 7 ÂL 2026 starts ~11/9/2026 → mùng 3 = 13/9
    # However many sources say the ceremony is on ngày 3 tháng 7 DL
    # Keep as-is (07-03) since it might follow DL tradition at this specific site
    print(f"  Kept Giỗ NĐC: {old_ds} (may follow DL date at the shrine)")

# Final count
events = db.list_entities(entity_type="event", limit=10000)
cats = {}
for e in events:
    cat = (e.get("attributes") or {}).get("category", "su-kien")
    cats[cat] = cats.get(cat, 0) + 1
print(f"\nFinal: {len(events)} events — {cats}")
