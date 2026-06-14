#!/usr/bin/env python3
"""Cập nhật phường An Hội với thông tin nghiên cứu sâu (trước + sau sáp nhập)."""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "web" / "data.json"
sys.stdout.reconfigure(encoding="utf-8")

data = json.load(DATA.open("r", encoding="utf-8-sig"))
by_id = {e["id"]: e for e in data["entities"]}

# ── 1. Cập nhật summary phường An Hội ──
ah = by_id["p-an-hoi"]
ah["summary"] = (
    "Phường An Hội là phường trung tâm và lớn nhất TP Bến Tre (thuộc tỉnh Vĩnh Long mới từ 01/07/2025), "
    "hình thành qua 3 đợt sáp nhập: (1) 01/02/2020 — hợp nhất Phường 1, 2, 3 thành An Hội (NQ 856); "
    "(2) 01/12/2024 — nhập thêm Phường 4, 5 (NQ 1237); "
    "(3) 16/06/2025 — nhập thêm xã Mỹ Thạnh An, Phú Nhuận và Sơn Phú (NQ 1687). "
    "Diện tích 31,9 km², dân số 53.476 người, 32 khu phố, mật độ 1.676 người/km². "
    "Nơi đây tập trung các công trình quan trọng: Hồ Trúc Giang (đào thời Pháp ~1930, 2 ha), "
    "Đình Thần An Hội (giữa TK 19, di tích cấp tỉnh), Chùa Viên Minh (1874, Bắc tông), "
    "Bảo tàng Bến Tre (1981, 2 ha), Công viên An Hội (2015, 3 ha, chợ đêm cuối tuần), "
    "chợ Bến Tre (trăm tuổi), Sense City. "
    "Các tuyến đường chính: Đại lộ Đồng Khởi, Hùng Vương, Nguyễn Đình Chiểu, Nam Kỳ Khởi Nghĩa. "
    "Phần đô thị lõi (P.1-5 cũ) sầm uất; phần mở rộng (Mỹ Thạnh An, Phú Nhuận, Sơn Phú) "
    "vẫn mang đặc trưng nông thôn miệt vườn xứ dừa."
)
ah["attributes"] = ah.get("attributes") or {}
ah["attributes"].update({
    "area_km2": 31.9,
    "population": 53476,
    "density_per_km2": 1676,
    "khu_pho": 32,
    "merge_note": "GĐ1 (2020): P.1+2+3→An Hội; GĐ2 (12/2024): +P.4+5; GĐ3 (06/2025): +xã Mỹ Thạnh An, Phú Nhuận, Sơn Phú",
    "merge_phases": [
        {"date": "2020-02-01", "resolution": "NQ 856/NQ-UBTVQH14", "units": ["Phường 1", "Phường 2", "Phường 3"], "result_area_km2": 0.92, "result_pop": 11502},
        {"date": "2024-12-01", "resolution": "NQ 1237/NQ-UBTVQH15", "units": ["Phường 4", "Phường 5"], "result_area_km2": 1.79, "result_pop": 25516},
        {"date": "2025-06-16", "resolution": "NQ 1687/NQ-UBTVQH15", "units": ["xã Mỹ Thạnh An", "xã Phú Nhuận", "xã Sơn Phú"], "result_area_km2": 31.9, "result_pop": 53476}
    ],
    "pre_merge_units": [
        {"name": "Phường 1", "area_km2": 0.26, "pop": 4456},
        {"name": "Phường 2", "area_km2": 0.22, "pop": 2279},
        {"name": "Phường 3", "area_km2": 0.44, "pop": 4767},
        {"name": "Phường 4", "area_km2": 0.39, "pop": 5768},
        {"name": "Phường 5", "area_km2": 0.49, "pop": 5935},
        {"name": "Xã Mỹ Thạnh An", "area_km2": 10.29, "pop": 12025, "aps": ["An Thạnh A", "An Thạnh B", "An Thuận A", "An Thuận B", "Mỹ An A", "Mỹ An B", "Mỹ An C"]},
        {"name": "Xã Phú Nhuận", "area_km2": 5.07, "pop": 3570, "note": "Từ huyện Giồng Trôm, nhập vào thị xã Bến Tre năm 1984"},
        {"name": "Xã Sơn Phú", "area_km2": 14.02, "pop": 7293, "note": "Từ huyện Giồng Trôm, cách TP Bến Tre 5km, đạt NTM, nông nghiệp miệt vườn"}
    ],
    "boundaries": {
        "east": "Phường Phú Khương, xã Lương Phú",
        "west": "Phường Bến Tre (sông Hàm Luông)",
        "south": "Xã Phước Long",
        "north": "Phường Sơn Đông"
    },
    "headquarters": "96 Tán Kế, Khu phố 6",
    "key_roads": ["Đại lộ Đồng Khởi", "Hùng Vương", "Nguyễn Đình Chiểu", "3 Tháng 2", "Nam Kỳ Khởi Nghĩa", "Trần Quốc Tuấn", "Tỉnh lộ 887"]
})
ah["source"] = {
    "title": "NQ 1687/NQ-UBTVQH15 + Wikipedia + UBND tỉnh",
    "url": "https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-so-1687-nq-ubtvqh15-sap-xep-cac-dvhc-cap-xa-cua-tinh-vinh-long-nam-2025-11925061621323394.htm"
}
ah["confidence"] = 0.95
print("✅ Updated p-an-hoi summary + attributes")

# ── 2. Cập nhật Đình An Hội ──
dinh = by_id.get("dinh-an-hoi")
if dinh:
    dinh["summary"] = (
        "Đình Thần An Hội được xây dựng giữa thế kỷ 19, là di tích lịch sử - văn hóa cấp tỉnh "
        "(QĐ 2253/QĐ-UBND ngày 11/11/2014). Diện tích gần 1.150 m², kiến trúc chữ Nhất (一) "
        "đặc trưng đình làng thời Nguyễn, gồm: võ ca, sân tương, trung điện, chánh điện, hậu đình. "
        "Mái ngói âm dương uốn cong, đầu đao cong vút lấy cảm hứng từ mũi thuyền văn minh sông nước cổ. "
        "Tọa lạc trên đường Nguyễn Đình Chiểu, đối diện trung tâm thương mại, giữa lòng phường An Hội."
    )
    dinh["attributes"] = dinh.get("attributes") or {}
    dinh["attributes"].update({
        "heritage_level": "Di tích cấp tỉnh",
        "heritage_decision": "QĐ 2253/QĐ-UBND ngày 11/11/2014",
        "area_m2": 1150,
        "built": "Giữa thế kỷ 19",
        "architecture": "Chữ Nhất (一), ngói âm dương, đầu đao cong"
    })
    dinh["source"] = {"title": "Báo Đồng Khởi + bentretourism.vn", "url": "https://mia.vn/cam-nang-du-lich/tham-quan-dinh-an-hoi-ben-tre-voi-lich-su-hon-tram-nam-tuoi-10432"}
    dinh["confidence"] = 0.9
    print("✅ Updated dinh-an-hoi")

# ── 3. Cập nhật Chùa Viên Minh ──
chua = by_id.get("chua-vien-minh-ben-tre")
if chua:
    chua["summary"] = (
        "Chùa Viên Minh là ngôi cổ tự thuộc hệ phái Phật giáo Bắc tông, xây dựng năm 1874, "
        "tọa lạc tại số 1 đường Nam Kỳ Khởi Nghĩa, trung tâm phường An Hội. "
        "Diện tích hơn 3.300 m², trùng tu lớn năm 1951 và 2002. "
        "Điểm đặc sắc: hai bức tượng Thích Ca và A Di Đà có cốt nan tre, "
        "Phật đài Thích Ca cao 7 mét, tượng Quan Thế Âm 3 mét có hạc chầu hai bên. "
        "Là điểm sinh hoạt tôn giáo lớn, thu hút hàng nghìn tín đồ vào các dịp Vu Lan, Phật Đản, Tết."
    )
    chua["attributes"] = chua.get("attributes") or {}
    chua["attributes"].update({
        "built": "1874",
        "area_m2": 3300,
        "sect": "Phật giáo Bắc tông",
        "address": "Số 1 Nam Kỳ Khởi Nghĩa, P. An Hội",
        "renovated": "1951, 2002"
    })
    chua["confidence"] = 0.9
    print("✅ Updated chua-vien-minh-ben-tre")

# ── 4. Cập nhật Bảo tàng Bến Tre ──
bt = by_id.get("bao-tang-ben-tre")
if bt:
    bt["summary"] = (
        "Bảo tàng Bến Tre thành lập năm 1981, diện tích 20.000 m² (2 ha), "
        "tọa lạc tại 146 Hùng Vương, phường An Hội. "
        "Trưng bày hiện vật, tranh ảnh về lịch sử tự nhiên và xã hội vùng đất xứ dừa. "
        "Điểm nhấn: Nhà Dừa — ngôi nhà ba gian dựng hoàn toàn bằng gỗ dừa, "
        "thờ Chủ tịch Hồ Chí Minh và anh hùng Phạm Ngọc Thảo. "
        "Mở cửa 7h00 – 17h00 các ngày trong tuần. Miễn phí tham quan."
    )
    bt["attributes"] = bt.get("attributes") or {}
    bt["attributes"].update({
        "established": 1981,
        "area_m2": 20000,
        "address": "146 Hùng Vương, P. An Hội",
        "hours": "07:00–17:00",
        "admission": "Miễn phí"
    })
    bt["confidence"] = 0.9
    print("✅ Updated bao-tang-ben-tre")

# ── 5. Cập nhật Hồ Trúc Giang ──
ho = by_id.get("ho-truc-giang")
if ho:
    ho["summary"] = (
        "Hồ Trúc Giang là hồ nước nhân tạo rộng khoảng 2 ha nằm giữa trung tâm phường An Hội, "
        "được đào vào thời Pháp thuộc (~1930) để lấy đất lấp vùng Phường 3 cũ. "
        "Ban đầu chỉ 1 ha, mở rộng lên 2 ha qua các dự án nâng cấp thập niên 1970 và 1990. "
        "Được mệnh danh 'viên ngọc xanh giữa lòng thành phố', hồ bao quanh bởi hàng cây tỏa bóng mát, "
        "là không gian cộng đồng tổ chức sự kiện, lễ hội, đờn ca tài tử và giải đua SUP. "
        "Liền kề Công viên An Hội và chợ đêm Bến Tre."
    )
    ho["attributes"] = ho.get("attributes") or {}
    ho["attributes"].update({
        "area_ha": 2,
        "built": "~1930 (thời Pháp)",
        "expanded": "Thập niên 1970, 1990"
    })
    ho["confidence"] = 0.9
    print("✅ Updated ho-truc-giang")

# ── 6. Cập nhật Công viên An Hội ──
cv = by_id.get("cong-vien-an-hoi")
if cv:
    cv["summary"] = (
        "Công viên An Hội xây dựng từ năm 2015, diện tích khoảng 30.000 m² (3 ha), "
        "tổng vốn đầu tư hơn 80 tỷ đồng, kết nối mở rộng từ các công viên Đồng Khởi, Hoàng Lam, Cái Cối. "
        "Là trung tâm văn hóa - giải trí - giáo dục môi trường của phường An Hội. "
        "Mỗi cuối tuần, công viên biến thành Chợ đêm Bến Tre (từ 2012) với gian hàng thủ công, "
        "ẩm thực dừa, sản phẩm xanh và chương trình đờn ca tài tử. "
        "Tổ chức nhiều sự kiện lớn: Chợ quê xứ Dừa, Ngày hội Văn hóa Ẩm thực, Giải đua SUP."
    )
    cv["attributes"] = cv.get("attributes") or {}
    cv["attributes"].update({
        "area_m2": 30000,
        "built": "2015",
        "investment": "80 tỷ VND",
        "events": ["Chợ đêm Bến Tre (cuối tuần)", "Chợ quê xứ Dừa", "Ngày hội Văn hóa Ẩm thực xứ Dừa"]
    })
    cv["confidence"] = 0.9
    print("✅ Updated cong-vien-an-hoi")

# ── 7. Cập nhật/thêm Chợ Bến Tre ──
cho = by_id.get("cho-ben-tre")
if cho:
    cho["summary"] = (
        "Chợ Bến Tre là ngôi chợ trăm năm tuổi, xây cuối thế kỷ 19 thời Pháp thuộc, "
        "tọa lạc tại 30 Hùng Vương, phường An Hội. Một mặt hướng sông Bến Tre, "
        "mặt kia giáp đường Nguyễn Đình Chiểu. "
        "Đặc biệt: chia thành 'chợ Phường 2' và 'chợ Phường 3' nối bằng cầu qua sông. "
        "Cấu trúc như mê cung, nổi tiếng với ẩm thực địa phương: bánh tráng, kẹo dừa, bánh canh."
    )
    cho["attributes"] = cho.get("attributes") or {}
    cho["attributes"].update({
        "built": "Cuối thế kỷ 19",
        "address": "30 Hùng Vương, P. An Hội"
    })
    cho["confidence"] = 0.9
    print("✅ Updated cho-ben-tre")

# ── Save ──
with DATA.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=None, separators=(",", ":"))

print(f"\n✅ Saved: {len(data['entities'])} entities, {len(data['relationships'])} rels")
