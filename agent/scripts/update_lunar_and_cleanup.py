"""
Add lunar_date to traditional festivals + delete unclear/duplicate events.
Run on both local SQLite and Postgres (VPS).
"""
import sys
import io
import json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")
from database import db
db.initialize()

# ── 1. Lunar dates for traditional festivals ──
# Format: entity_id → lunar_date string
LUNAR_DATES = {
    # Tết
    "tet-nguyen-dan-mien-tay": "Mùng 1 tháng Giêng âm lịch",
    "tet-doan-ngo": "Mùng 5 tháng 5 âm lịch",

    # Đình / miếu / lăng — Kinh
    "le-hoi-ky-yen": "16–17 tháng 2 âm lịch",
    "le-hoi-ky-yen-ha-dien-dinh-tan-giai": "16–17 tháng 3 âm lịch",
    "le-hoi-ky-yen-dinh-phu-le": "18–19 tháng 3 âm lịch",
    "le-ha-dien-dinh-tan-hoa": "16 tháng 4 âm lịch",
    "le-thuong-dien-dinh-tan-ngai": "16–17 tháng 10 âm lịch",
    "le-ha-dien-va-thuong-dien-dinh-hoa-tinh": "Hạ điền: 16/4 ÂL, Thượng điền: 16/10 ÂL",
    "le-hoi-van-thanh-mieu": "Rằm tháng 2 âm lịch",
    "le-cung-mieu": "16–18 tháng Giêng âm lịch",
    "le-hoi-ba-chua-xu": "23–27 tháng 3 âm lịch",
    "le-via-ba-co-hy": "Rằm tháng 2 âm lịch",

    # Giỗ danh nhân
    "le-via-quoc-cong-tong-phuoc-hiep": "Mùng 2–3 tháng 6 âm lịch",
    "lang-ong-tien-quan-thong-che-dieu-bat-tuong-quan-nguyen-van-": "Mùng 3–4 tháng Giêng âm lịch",
    "le-gio-nguyen-dinh-chieu": "Mùng 3 tháng 7 âm lịch",
    "le-gio-phan-thanh-gian-tai-van-thanh-mieu": "15 tháng 6 âm lịch",

    # Nguyên Tiêu (Hoa)
    "le-hoi-nguyen-tieu": "Rằm tháng Giêng âm lịch",
    "le-hoi-nguyen-tieu-o-tra-cu": "Rằm tháng Giêng âm lịch",
    "le-cung-lau-ba-ram-thang-gieng": "Rằm tháng Giêng âm lịch",

    # Nghinh Ông / cúng biển / cầu ngư
    "le-hoi-nghinh-ong": "16 tháng 6 âm lịch",
    "le-hoi-nghinh-ong-binh-thang": "16 tháng 6 âm lịch",
    "le-hoi-nghinh-ong-duyen-hai": "10–12 tháng 3 âm lịch",
    "le-hoi-nghinh-ong-lang-con-tau": "10–11 tháng 3 âm lịch",
    "le-hoi-cau-ngu": "Rằm tháng 2 âm lịch",
    "le-hoi-ngu-dan-thanh-hai-le-hoi-cau-ngu": "15–16 tháng 2 âm lịch",
    "le-hoi-cung-bien-my-long": "11–12 tháng 5 âm lịch",
    "le-cung-bien-dong-cao": "11–12 tháng 5 âm lịch",

    # Vu Lan
    "le-vu-lan": "Rằm tháng 7 âm lịch",
    "vu-lan-thang-hoi": "25–28 tháng 7 âm lịch",

    # Trung Thu
    "le-hoi-long-den": "Rằm tháng 8 âm lịch",

    # Khmer
    "chol-chnam-thmay": "13–16 tháng 4 dương lịch (cố định)",
    "le-chol-chhnam-thmay": "13–16 tháng 4 dương lịch (cố định)",
    "le-hoi-chol-chnam-thmay-tai-chua-ky-son": "13–15 tháng 4 dương lịch (cố định)",
    "le-hoi-chol-chnam-thmay-va-sen-dolta": "Chol Chnam Thmay: 13–16/4 DL; Sen Dolta: 29/8–1/9 ÂL",
    "sen-dolta": "29 tháng 8 – 1 tháng 9 âm lịch",
    "le-hoi-sene-donta-ok-om-bok": "Sen Dolta: 29/8–1/9 ÂL; Ok Om Bok: Rằm tháng 10 ÂL",
    "le-hoi-ok-om-bok": "Rằm tháng 10 âm lịch",
    "le-hoi-ok-om-bok-cua-dong-bao-khmer-tra-cu": "Rằm tháng 10 âm lịch",
    "le-cung-trang-ok-om-bok": "Rằm tháng 10 âm lịch",
    "le-hoi-dom-long-neak-ta": "Cuối tháng 3 – đầu tháng 4 âm lịch",

    # Đua ghe ngo
    "hoi-dua-ghe-ngo-soc-trang": "Rằm tháng 10 âm lịch (dịp Ok Om Bok)",
    "hoi-thi-ghe-ngo-mo-rong-tinh-tra-vinh-dua-ghe-ngo-truyen-thong-tra-vinh": "Rằm tháng 10 âm lịch (dịp Ok Om Bok)",
    "giai-dua-ghe-ngo-truyen-thong-tinh-ben-tre-ben-tre": "Rằm tháng 10 âm lịch (dịp Ok Om Bok)",

    # Giỗ Tổ Hùng Vương
    "le-gio-to-hung-vuong": "Mùng 10 tháng 3 âm lịch",

    # Đờn ca tài tử
    "don-ca-tai-tu-vinh-long": "Quanh năm",
}

# ── 2. Events to DELETE (duplicates or unclear time) ──
DELETE_IDS = [
    # Festival Gạch Gốm Đỏ — 3 entities cho cùng 1 sự kiện, giữ lại cái đầy đủ nhất
    "festival-gach-gom-do-kinh-te-xanh-vinh-long",          # duplicate
    "le-hoi-kinh-te-xanh-gach-do-mang-thit",                # duplicate

    # Hội chợ ĐBSCL — 2 entities trùng
    "hoi-cho-dac-san-vung-mien-khu-vuc-dbscl-tai-phuong-9",  # duplicate

    # Festival Dừa — 2 entities trùng
    "le-hoi-dua-ben-tre-ben-tre",                             # duplicate (giữ festival-dua-ben-tre)

    # Liên hoan ĐCTT VL "năm 2017" — tên sai, ngày không rõ
    "lien-hoan-don-ca-tai-tu-tinh-vinh-long-nam-2017",
]

# ── Execute ──
print("=== Adding lunar_date ===")
updated = 0
for eid, lunar in LUNAR_DATES.items():
    e = db.get_entity(eid)
    if not e:
        print(f"  SKIP (not found): {eid}")
        continue
    attrs = e.get("attributes") or {}
    if attrs.get("lunar_date") == lunar:
        continue
    attrs["lunar_date"] = lunar
    e["attributes"] = attrs
    db.upsert_entity(e)
    updated += 1
    print(f"  + {eid}: {lunar}")
print(f"  Updated: {updated}")

print("\n=== Deleting duplicates/unclear ===")
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

# Final count
events = db.list_entities(entity_type="event", limit=10000)
cats = {}
for e in events:
    cat = (e.get("attributes") or {}).get("category", "su-kien")
    cats[cat] = cats.get(cat, 0) + 1
print(f"\nFinal: {len(events)} events — {cats}")
