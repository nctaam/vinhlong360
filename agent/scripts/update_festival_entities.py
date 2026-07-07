"""Update two entities to proper traditional cultural festival entries.

1. le-via-quoc-cong-tong-phuoc-hiep — fix summary, dates, attributes
2. lang-ong-tien-quan-thong-che-dieu-bat-tuong-quan-nguyen-van- — change type to event

Lunar 2026: T1=02-17, T6=07-14
  Mùng 2-3 tháng 6 = 07-15 ~ 07-16
  Mùng 3-4 tháng Giêng = 02-19 ~ 02-20
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")
from database import db
db.initialize()

# === 1. Lễ vía Quốc công Tống Phước Hiệp ===
e1 = db.get_entity("le-via-quoc-cong-tong-phuoc-hiep")
if e1:
    e1["summary"] = (
        "Lễ giỗ danh thần Tống Phước Hiệp tổ chức hằng năm vào mùng 2–3 tháng 6 âm lịch "
        "tại Đình Tân Giai, Phường 3, TP Vĩnh Long. Tống Phước Hiệp (?–1776) là Lưu thủ "
        "Long Hồ dinh — vị quan đầu tiên cai quản vùng đất nay là Vĩnh Long, có công lớn "
        "trong việc khai khẩn, ổn định dân sinh và kháng cự ngoại xâm. Chúa Nguyễn truy "
        "phong ông tước Hữu phủ Quốc công. Lễ giỗ đã tổ chức liên tục từ năm 1776 (lần "
        "thứ 247 năm 2023), gồm lễ thỉnh sắc, phơi sắc, lễ Túc Yết, lễ Chánh tế và lễ "
        "Thần Nông cầu mưa thuận gió hòa. Lãnh đạo tỉnh, cựu học sinh trường THPT Tống "
        "Phước Hiệp và người dân địa phương cùng đến dâng hương — là dịp giáo dục lịch sử "
        "khai lập vùng đất Vĩnh Long cho thế hệ trẻ."
    )
    attrs = e1.get("attributes") or {}
    attrs["date_start"] = "2026-07-15"
    attrs["date_end"] = "2026-07-16"
    attrs["lunar_date"] = "Mùng 2–3 tháng 6 âm lịch"
    attrs["highlight"] = "Lễ giỗ gần 250 năm không gián đoạn — truyền thống lâu đời nhất Vĩnh Long, tưởng nhớ vị quan đầu tiên khai lập Long Hồ dinh."
    attrs["address"] = "Đình Tân Giai, Phường 3, TP Vĩnh Long"
    e1["attributes"] = attrs
    e1["season"] = {"months": [7], "peak": [7]}
    db.upsert_entity(e1)
    print(f"✓ Updated: {e1['id']} — date_start={attrs['date_start']}")
else:
    print("✗ NOT FOUND: le-via-quoc-cong-tong-phuoc-hiep")


# === 2. Lăng Ông → đổi type sang event ===
e2 = db.get_entity("lang-ong-tien-quan-thong-che-dieu-bat-tuong-quan-nguyen-van-")
if e2:
    e2["type"] = "event"
    e2["name"] = "Lễ hội Lăng Ông Tiền quân Thống chế Điều bát Nguyễn Văn Tồn"
    e2["summary"] = (
        "Lễ hội truyền thống hằng năm vào mùng 3–4 tháng Giêng âm lịch tại Lăng Ông, "
        "ấp Giồng Thanh Bạch, xã Thiện Mỹ, huyện Trà Ôn, tỉnh Vĩnh Long. Tưởng nhớ "
        "Nguyễn Văn Tồn (Thạch Duồng, 1763–1820), danh tướng gốc Khmer phục vụ chúa "
        "Nguyễn Ánh, được phong Tiền quân Thống chế Điều bát, có công khai khẩn vùng "
        "Trà Ôn–Mân Thít và đào kênh Vĩnh Tế. Lễ hội gồm lễ Túc Yết, lễ Chánh tế, "
        "xây chầu đại bội, hát bội, nhạc ngũ âm Khmer, múa Sa-dăm, múa lân và Tùa Lầu "
        "Cấu — hiếm hoi hội tụ cả ba nền văn hóa Kinh–Hoa–Khmer trong cùng một lễ hội. "
        "Di sản văn hóa phi vật thể quốc gia (QĐ 261/QĐ-BVHTTDL, 22/01/2020). Khu lăng "
        "rộng khoảng 8.000 m², là di tích lịch sử–văn hóa cấp quốc gia từ 1996. Hàng "
        "chục ngàn người từ Vĩnh Long, Trà Vinh và các tỉnh lân cận về dự mỗi năm."
    )
    attrs = e2.get("attributes") or {}
    attrs["date_start"] = "2026-02-19"
    attrs["date_end"] = "2026-02-20"
    attrs["lunar_date"] = "Mùng 3–4 tháng Giêng âm lịch"
    attrs["heritage"] = "Di sản VHPVTQG (QĐ 261/2020); Di tích LSVH cấp QG (1996)"
    attrs["highlight"] = "Lễ hội giao thoa 3 dân tộc Kinh–Hoa–Khmer hiếm có — hát bội, nhạc ngũ âm, múa Sa-dăm và Tùa Lầu Cấu cùng hội ngộ đầu xuân."
    attrs["address"] = "Ấp Giồng Thanh Bạch, xã Thiện Mỹ, huyện Trà Ôn, tỉnh Vĩnh Long"
    attrs["admission"] = "miễn phí"
    e2["attributes"] = attrs
    e2["season"] = {"months": [2], "peak": [2]}
    db.upsert_entity(e2)
    print(f"✓ Updated: {e2['id']} — type=event, date_start={attrs['date_start']}")
else:
    print("✗ NOT FOUND: lang-ong-tien-quan-thong-che-dieu-bat-tuong-quan-nguyen-van-")

print("\nDone.")
