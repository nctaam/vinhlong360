"""Classify all event entities into category: le-hoi / su-kien / mua."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")
from database import db
db.initialize()

# ── Lễ hội văn hóa truyền thống ──
LE_HOI = {
    # Tết & lễ lớn
    "tet-nguyen-dan-mien-tay",
    "tet-doan-ngo",
    "le-vu-lan",
    "vu-lan-thang-hoi",
    "le-gio-to-hung-vuong",
    "le-hoi-long-den",  # Trung Thu

    # Đình / miếu / lăng — Kinh
    "le-hoi-ky-yen",
    "le-hoi-ky-yen-ha-dien-dinh-tan-giai",
    "le-hoi-ky-yen-dinh-phu-le",
    "le-ha-dien-dinh-tan-hoa",
    "le-thuong-dien-dinh-tan-ngai",
    "le-ha-dien-va-thuong-dien-dinh-hoa-tinh",
    "le-hoi-van-thanh-mieu",
    "le-cung-mieu",
    "le-hoi-ba-chua-xu",
    "le-via-ba-co-hy",

    # Giỗ danh nhân / lăng ông
    "le-via-quoc-cong-tong-phuoc-hiep",
    "lang-ong-tien-quan-thong-che-dieu-bat-tuong-quan-nguyen-van-",
    "le-gio-nguyen-dinh-chieu",
    "le-gio-phan-thanh-gian-tai-van-thanh-mieu",

    # Khmer
    "chol-chnam-thmay",
    "le-chol-chhnam-thmay",
    "le-hoi-chol-chnam-thmay-tai-chua-ky-son",
    "le-hoi-chol-chnam-thmay-va-sen-dolta",
    "sen-dolta",
    "le-hoi-sene-donta-ok-om-bok",
    "le-hoi-ok-om-bok",
    "le-hoi-ok-om-bok-cua-dong-bao-khmer-tra-cu",
    "le-cung-trang-ok-om-bok",
    "le-hoi-dom-long-neak-ta",

    # Hoa
    "le-hoi-nguyen-tieu",
    "le-hoi-nguyen-tieu-o-tra-cu",
    "le-cung-lau-ba-ram-thang-gieng",

    # Nghinh Ông / cúng biển / cầu ngư
    "le-hoi-nghinh-ong",
    "le-hoi-nghinh-ong-binh-thang",
    "le-hoi-nghinh-ong-duyen-hai",
    "le-hoi-nghinh-ong-lang-con-tau",
    "le-hoi-cau-ngu",
    "le-hoi-ngu-dan-thanh-hai-le-hoi-cau-ngu",
    "le-hoi-cung-bien-my-long",
    "le-cung-bien-dong-cao",

    # Đua ghe ngo truyền thống (gắn Ok Om Bok)
    "hoi-dua-ghe-ngo-soc-trang",
    "hoi-thi-ghe-ngo-mo-rong-tinh-tra-vinh-dua-ghe-ngo-truyen-thong-tra-vinh",
    "giai-dua-ghe-ngo-truyen-thong-tinh-ben-tre-ben-tre",

    # Đờn ca tài tử (di sản VHPVTQG)
    "don-ca-tai-tu-vinh-long",
}

# ── Mùa vụ / tự nhiên ──
MUA = {
    "mua-nuoc-noi-dbscl",
    "mua-trai-cay-chin-roi",
    "cho-hoa-tet",
}

def classify(eid):
    if eid in LE_HOI:
        return "le-hoi"
    if eid in MUA:
        return "mua"
    return "su-kien"


events = db.list_entities(entity_type="event", limit=10000)
counts = {"le-hoi": 0, "su-kien": 0, "mua": 0}

for e in events:
    cat = classify(e["id"])
    counts[cat] += 1
    attrs = e.get("attributes") or {}
    if attrs.get("category") == cat:
        continue
    attrs["category"] = cat
    e["attributes"] = attrs
    db.upsert_entity(e)

print("Classification done:")
for cat, n in counts.items():
    print(f"  {cat}: {n}")
print(f"  Total: {sum(counts.values())}")
