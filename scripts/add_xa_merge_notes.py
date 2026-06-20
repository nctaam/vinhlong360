#!/usr/bin/env python3
"""Thêm merge_note attribute cho TẤT CẢ 105 xã theo NQ 1687/NQ-UBTVQH15.
Chỉ thêm/cập nhật merge_note, KHÔNG sửa summary hay field khác.
4 xã không sáp nhập ghi merge_note = "Không sáp nhập (giữ nguyên)".
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data.json"
sys.stdout.reconfigure(encoding="utf-8")

NQ_XA = {
    "xa-cai-nhum": "Xã An Phước (H. Mang Thít) + xã Chánh An + TT Cái Nhum",
    "xa-tan-long-hoi": "Xã Tân An Hội + Tân Long + Tân Long Hội",
    "xa-nhon-phu": "Xã Mỹ An (H. Mang Thít) + Mỹ Phước + Nhơn Phú",
    "xa-binh-phuoc": "Xã Long Mỹ (H. Mang Thít) + Hòa Tịnh + Bình Phước",
    "xa-an-binh": "Xã Hòa Ninh + Bình Hòa Phước + Đồng Phú + An Bình",
    "xa-long-ho": "TT Long Hồ + xã Long An + Long Phước",
    "xa-phu-quoi": "Xã Lộc Hòa + Hòa Phú + Thạnh Quới + Phú Quới",
    "xa-quoi-thien": "Xã Thanh Bình + Quới Thiện",
    "xa-trung-thanh": "TT Vũng Liêm + xã Trung Hiếu + Trung Thành",
    "xa-trung-ngai": "Xã Trung Thành Đông + Trung Nghĩa + Trung Ngãi",
    "xa-quoi-an": "Xã Trung Thành Tây + Tân Quới Trung + Quới An",
    "xa-trung-hiep": "Xã Tân An Luông + Trung Chánh + Trung Hiệp",
    "xa-hieu-phung": "Xã Hiếu Thuận + Trung An + Hiếu Phụng",
    "xa-hieu-thanh": "Xã Hiếu Nhơn + Hiếu Nghĩa + Hiếu Thành",
    "xa-luc-si-thanh": "Xã Phú Thành + Lục Sĩ Thành",
    "xa-tra-on": "Xã Tích Thiện + một phần TT Trà Ôn",
    "xa-tra-con": "Xã Nhơn Bình + Trà Côn + Tân Mỹ + một phần TT Tam Bình",
    "xa-vinh-xuan": "Xã Hựu Thành + Thuận Thới + Vĩnh Xuân",
    "xa-hoa-binh": "Xã Xuân Hiệp + Thới Hòa + Hòa Bình",
    "xa-hoa-hiep": "Xã Hòa Thạnh + Hòa Lộc + Hòa Hiệp",
    "xa-tam-binh": "Xã Mỹ Thạnh Trung + phần còn lại TT Tam Bình",
    "xa-ngai-tu": "Xã Loan Mỹ + Bình Ninh + một phần xã Ngãi Tứ + phần còn lại TT Trà Ôn",
    "xa-song-phu": "Xã Tân Phú (H. Tam Bình) + Long Phú + Phú Thịnh + Song Phú",
    "xa-cai-ngang": "Xã Mỹ Lộc + Tân Lộc + Hậu Lộc + Phú Lộc",
    "xa-tan-quoi": "Xã Tân Bình (H. Bình Tân) + Thành Lợi + TT Tân Quới",
    "xa-tan-luoc": "Xã Tân Thành + Tân An Thạnh + Tân Lược",
    "xa-my-thuan": "Xã Thành Trung + Nguyễn Văn Thảnh + Mỹ Thuận",
    "xa-long-huu": "Xã Hiệp Thạnh + Long Hữu",
    "xa-cang-long": "TT Càng Long + xã Mỹ Cẩm + Nhị Long Phú",
    "xa-an-truong": "Xã Tân Bình (H. Càng Long) + An Trường A + An Trường",
    "xa-tan-an": "Xã Huyền Hội + Tân An",
    "xa-nhi-long": "Xã Đại Phước + Đức Mỹ + Nhị Long",
    "xa-binh-phu": "Xã Bình Phú (H. Càng Long) + Đại Phúc + Phương Thạnh",
    "xa-chau-thanh": "TT Châu Thành (H. Châu Thành, TV) + xã Mỹ Chánh + Thanh Mỹ + Đa Lộc",
    "xa-song-loc": "Xã Lương Hòa (H. Châu Thành) + Lương Hòa A + Song Lộc",
    "xa-hung-my": "Xã Hòa Lợi (H. Châu Thành) + Phước Hảo + Hưng Mỹ",
    "xa-cau-ke": "TT Cầu Kè + xã Hòa Ân + Châu Điền",
    "xa-phong-thanh": "Xã Ninh Thới + Phong Phú + Phong Thạnh",
    "xa-an-phu-tan": "Xã Hòa Tân + An Phú Tân",
    "xa-tam-ngai": "Xã Thông Hòa + Thạnh Phú + Tam Ngãi",
    "xa-tieu-can": "TT Tiểu Cần + xã Phú Cần + Hiếu Trung",
    "xa-tan-hoa": "Xã Long Thới (H. Tiểu Cần) + Tân Hòa + TT Cầu Quan",
    "xa-hung-hoa": "Xã Ngãi Hùng + Tân Hùng + Hùng Hòa",
    "xa-tap-ngai": "Xã Hiếu Tử + Tập Ngãi",
    "xa-cau-ngang": "Xã Mỹ Hòa (H. Cầu Ngang) + Thuận Hòa + TT Cầu Ngang",
    "xa-my-long": "TT Mỹ Long + xã Mỹ Long Bắc + Mỹ Long Nam",
    "xa-vinh-kim": "Xã Kim Hòa + Vinh Kim",
    "xa-nhi-truong": "Xã Hiệp Hòa + Trường Thọ + Nhị Trường",
    "xa-hiep-my": "Xã Long Sơn + Hiệp Mỹ Đông + Hiệp Mỹ Tây",
    "xa-tra-cu": "TT Trà Cú + xã Ngãi Xuyên + Thanh Sơn",
    "xa-dai-an": "TT Định An + xã Định An + Đại An",
    "xa-luu-nghiep-anh": "Xã An Quảng Hữu + Lưu Nghiệp Anh",
    "xa-ham-giang": "Xã Hàm Tân + Kim Sơn + Hàm Giang",
    "xa-long-hiep": "Xã Ngọc Biên + Tân Hiệp + Long Hiệp",
    "xa-tap-son": "Xã Tân Sơn + Phước Hưng + Tập Sơn",
    "xa-long-thanh": "TT Long Thành + xã Long Khánh",
    "xa-don-chau": "Xã Đôn Xuân + Đôn Châu",
    "xa-ngu-lac": "Xã Thạnh Hòa Sơn + Ngũ Lạc",
    "xa-phu-tuc": "TT Châu Thành (H. Châu Thành, BT) + xã Tân Thạch + Tường Đa + Phú Túc",
    "xa-giao-long": "Xã An Phước (H. Châu Thành, BT) + Quới Sơn + Giao Long",
    "xa-tien-thuy": "TT Tiên Thủy + xã Thành Triệu + Quới Thành",
    "xa-tan-phu": "Xã Tân Phú (H. Châu Thành, BT) + Tiên Long + Phú Đức",
    "xa-phu-phung": "Xã Sơn Định + Vĩnh Bình + Phú Phụng",
    "xa-cho-lach": "Xã Long Thới (H. Chợ Lách) + Hòa Nghĩa + TT Chợ Lách",
    "xa-vinh-thanh": "Xã Phú Sơn + Tân Thiềng + Vĩnh Thành",
    "xa-hung-khanh-trung": "Xã Vĩnh Hòa (H. Chợ Lách) + Hưng Khánh Trung A + Hưng Khánh Trung B",
    "xa-phuoc-my-trung": "TT Phước Mỹ Trung + xã Phú Mỹ + Thạnh Ngãi + Tân Phú Tây",
    "xa-tan-thanh-binh": "Xã Tân Bình (H. Mỏ Cày Bắc) + Thành An + Hòa Lộc + Tân Thành Bình",
    "xa-nhuan-phu-tan": "Xã Khánh Thạnh Tân + Tân Thanh Tây + Nhuận Phú Tân",
    "xa-dong-khoi": "Xã Định Thủy + Phước Hiệp + Bình Khánh",
    "xa-mo-cay": "TT Mỏ Cày + xã An Thạnh (H. Mỏ Cày Nam) + Tân Hội + Đa Phước Hội",
    "xa-thanh-thoi": "Xã An Thới + Thành Thới A + Thành Thới B",
    "xa-an-dinh": "Xã Tân Trung + Minh Đức + An Định",
    "xa-huong-my": "Xã Ngãi Đăng + Cẩm Sơn + Hương Mỹ",
    "xa-dai-dien": "Xã Phú Khánh + Tân Phong + Thới Thạnh + Đại Điền",
    "xa-quoi-dien": "Xã Hòa Lợi (H. Thạnh Phú) + Mỹ Hưng + Quới Điền",
    "xa-thanh-phu": "TT Thạnh Phú + xã An Thạnh (H. Thạnh Phú) + Bình Thạnh + Mỹ An",
    "xa-an-qui": "Xã An Thuận + An Nhơn + An Qui",
    "xa-thanh-hai": "Xã An Điền + Thạnh Hải",
    "xa-thanh-phong": "Xã Giao Thạnh + Thạnh Phong",
    "xa-tan-thuy": "TT Tiệm Tôm + xã An Hòa Tây + Tân Thủy",
    "xa-bao-thanh": "Xã Bảo Thuận + Bảo Thạnh",
    "xa-ba-tri": "TT Ba Tri + xã Vĩnh Hòa (H. Ba Tri) + An Đức + Vĩnh An + An Bình Tây",
    "xa-tan-xuan": "Xã Phú Lễ + Phước Ngãi + Tân Xuân",
    "xa-my-chanh-hoa": "Xã Mỹ Hòa + Mỹ Chánh (H. Ba Tri) + Mỹ Nhơn",
    "xa-an-ngai-trung": "Xã Mỹ Thạnh (H. Ba Tri) + An Phú Trung + An Ngãi Trung",
    "xa-an-hiep": "Xã Tân Hưng + An Ngãi Tây + An Hiệp",
    "xa-hung-nhuong": "Xã Tân Thanh + Hưng Lễ + Hưng Nhượng",
    "xa-giong-trom": "TT Giồng Trôm + xã Bình Hòa + Bình Thành",
    "xa-tan-hao": "Xã Tân Lợi Thạnh + Thạnh Phú Đông + Tân Hào",
    "xa-phuoc-long": "Xã Long Mỹ (H. Giồng Trôm) + Hưng Phong + Phước Long",
    "xa-luong-phu": "Xã Mỹ Thạnh (H. Giồng Trôm) + Thuận Điền + Lương Phú",
    "xa-chau-hoa": "Xã Châu Bình + Lương Quới + Châu Hòa",
    "xa-luong-hoa": "Xã Lương Hòa (H. Giồng Trôm) + Phong Nẫm",
    "xa-thoi-thuan": "Xã Thừa Đức + Thới Thuận",
    "xa-thanh-phuoc": "Xã Đại Hòa Lộc + Thạnh Phước",
    "xa-binh-dai": "TT Bình Đại + xã Bình Thới + Bình Thắng",
    "xa-thanh-tri": "Xã Định Trung + Phú Long + Thạnh Trị",
    "xa-loc-thuan": "Xã Vang Quới Đông + Vang Quới Tây + Lộc Thuận",
    "xa-chau-hung": "Xã Long Hòa (H. Bình Đại) + Thới Lai + Châu Hưng",
    "xa-phu-thuan": "Xã Long Định + Tam Hiệp + Phú Thuận",
    # 4 xã không sáp nhập
    "xa-long-hoa": "Không sáp nhập (giữ nguyên)",
    "xa-dong-hai": "Không sáp nhập (giữ nguyên)",
    "xa-long-vinh": "Không sáp nhập (giữ nguyên)",
    "xa-hoa-minh": "Không sáp nhập (giữ nguyên)",
}

data = json.load(DATA.open("r", encoding="utf-8-sig"))
by_id = {e["id"]: e for e in data["entities"]}

updated = 0
missing = 0
for eid, merge_note in NQ_XA.items():
    e = by_id.get(eid)
    if not e:
        print(f"  NOT FOUND: {eid}")
        missing += 1
        continue
    attrs = e.get("attributes") or {}
    e["attributes"] = attrs
    old = attrs.get("merge_note", "")
    if old != merge_note:
        attrs["merge_note"] = merge_note
        updated += 1
        if old:
            print(f"  UPD {eid}: «{old}» → «{merge_note}»")
        else:
            print(f"  ADD {eid}: «{merge_note}»")

with DATA.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=None, separators=(",", ":"))

print(f"\n✅ Updated {updated} xã merge_notes, {missing} not found")
print(f"Total entries: {len(NQ_XA)} (101 sáp nhập + 4 không sáp nhập)")
