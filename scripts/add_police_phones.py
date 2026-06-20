"""Thêm SĐT công an xã/phường vào attributes.police_phone cho mỗi entity place.

Nguồn: https://congan.vinhlong.gov.vn/trang/duong-day-nong.html (trích 2026-06-15)
§B1: backup trước khi chạy.
"""
import json, re, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

POLICE_DATA_RAW = """
Công an phường An Hội|02753.829.687
Công an phường Bến Tre|02753.832.066
Công an phường Bình Minh|02703.742.128
Công an phường Cái Vồn|02703.890.325
Công an phường Duyên Hải|02942.216.423
Công an phường Đông Thành|02703.722.999
Công an phường Hoà Thuận|02943.855.107
Công an phường Long Châu|02703.823.536
Công an phường Long Đức|02943.852.497
Công an phường Nguyệt Hoá|02943.842.692
Công an phường Phú Khương|02752.211.334
Công an phường Phú Tân|02753.561.145
Công an phường Phước Hậu|02703.829.463
Công an phường Sơn Đông|0787.878.126
Công an phường Tân Hạnh|02703.811.941
Công an phường Tân Ngãi|02703.822.821
Công an phường Thanh Đức|02703.823.508
Công an phường Trà Vinh|02943.856.505
Công an phường Trường Long Hoà|02943.839.456
Công an xã An Bình|02703.859.245
Công an xã An Định|02753.847.104
Công an xã An Hiệp|02753.859.871
Công an xã An Ngãi Trung|02753.858.397
Công an xã An Phú Tân|0294.3715113
Công an xã An Qui|0275.3889.500
Công an xã An Trường|02943.887.888
Công an xã Ba Tri|02753.850.055
Công an xã Bảo Thạnh|02753.881.315
Công an xã Bình Đại|02753.851.514
Công an xã Bình Phú|02943.880.059
Công an xã Bình Phước|02703.937.233
Công an xã Cái Ngang|02703.717.616
Công an xã Cái Nhum|02703.933.339
Công an xã Càng Long|02943.882.381
Công an xã Cầu Kè|02943.834.046
Công an xã Cầu Ngang|02943.823.893
Công an xã Châu Hòa|02753.887.175
Công an xã Châu Hưng|02753.853.720
Công an xã Châu Thành|02943.872.064
Công an xã Chợ Lách|0275.3871.230
Công an xã Đại An|02943.686.614
Công an xã Đại Điền|0275.3727.113
Công an xã Đôn Châu|02943.776.093
Công an xã Đông Hải|02943.737.342
Công an xã Đồng Khởi|0275.3843.060
Công an xã Giao Long|02753.637.102
Công an xã Giồng Trôm|02753.640.345
Công an xã Hàm Giang|02943.550.387
Công an xã Hiệp Mỹ|02943.820.155
Công an xã Hiếu Phụng|02703.874.354
Công an xã Hiếu Thành|02703.990.888
Công an xã Hòa Bình|02703.722.301
Công an xã Hòa Hiệp|02703.716.198
Công an xã Hoà Minh|02943.899.477
Công an xã Hùng Hoà|02943.640.618
Công an xã Hưng Khánh Trung|02753.692.813
Công an xã Hưng Mỹ|02943.890.539
Công an xã Hưng Nhượng|02753.642.213
Công an xã Hương Mỹ|02753.727.113
Công an xã Long Hiệp|02943.675.286
Công an xã Long Hòa|02943.799.319
Công an xã Long Hồ|02703.851.852
Công an xã Long Hữu|02943.836.346
Công an xã Long Thành|02943.837.349
Công an xã Long Vĩnh|02943.830.068
Công an xã Lộc Thuận|02753.855.533
Công an xã Lục Sĩ Thành|02703.780.708
Công an xã Lương Hòa|02753.862.700
Công an xã Lương Phú|02753.862.387
Công an xã Lưu Nghiệp Anh|02943.871.279
Công an xã Mỏ Cày|02753.843.293
Công an xã Mỹ Chánh Hòa|02753.858.394
Công an xã Mỹ Long|02943.531.700
Công an xã Mỹ Thuận|02703.764.789
Công an xã Ngãi Tứ|02703.720.217
Công an xã Ngũ Lạc|02943.838.428
Công an xã Nhị Long|02943.889.020
Công an xã Nhị Trường|02943.720.070
Công an xã Nhơn Phú|02703.849.614
Công an xã Nhuận Phú Tân|02753.846.122
Công an xã Phong Thạnh|02943.816.656
Công an xã Phú Phụng|02753.871.434
Công an xã Phú Quới|02703.811.090
Công an xã Phú Túc|02753.613.613
Công an xã Phú Thuận|02753.853.991
Công an xã Phước Long|02753.656.269
Công an xã Phước Mỹ Trung|02753.845.550
Công an xã Quới An|02703.993.158
Công an xã Quới Điền|02753.739.609
Công an xã Quới Thiện|02703.980.745
Công an xã Song Lộc|02943.898.006
Công an xã Song Phú|0270.3864.543
Công an xã Tam Bình|02703.860.843
Công an xã Tam Ngãi|02943.950.368
Công an xã Tân An|02943.886.937
Công an xã Tân Hào|02753.863.626
Công an xã Tân Hòa|02943.824.113
Công an xã Tân Long Hội|02703.841.636
Công an xã Tân Lược|02703.754.136
Công an xã Tân Phú|02753.867.955
Công an xã Tân Quới|02703.760.676
Công an xã Tân Thành Bình|02753.840.115
Công an xã Tân Thủy|02753.856.596
Công an xã Tân Xuân|02753.858.811
Công an xã Tập Ngãi|02943.618.641
Công an xã Tập Sơn|02943.877.352
Công an xã Tiên Thủy|02753.868.403
Công an xã Tiểu Cần|02943.614.051
Công an xã Thành Thới|02753.847.240
Công an xã Thạnh Hải|02753.889.274
Công an xã Thạnh Phong|02753.886.303
Công an xã Thạnh Phú|02753.870.805
Công an xã Thạnh Phước|02753.884.016
Công an xã Thạnh Trị|02753.855.510
Công an xã Thới Thuận|02753.852.903
Công an xã Trà Côn|02703.723.327
Công an xã Trà Cú|02943.875.050
Công an xã Trà Ôn|02703.770.268
Công an xã Trung Hiệp|02703.874.200
Công an xã Trung Ngãi|02703.978.456
Công an xã Trung Thành|02703.976.350
Công an xã Vinh Kim|02943.827.888
Công an xã Vĩnh Thành|02753.898.028
Công an xã Vĩnh Xuân|02703.884.213
""".strip()

HOTLINES = {
    "canh_sat_113": "113",
    "bao_chay_114": "114",
    "truc_ban_cong_an_tinh": "02703.823.328",
}

def parse_police_data():
    """Parse raw data → dict {place_name_normalized: phone}"""
    mapping = {}
    for line in POLICE_DATA_RAW.strip().split("\n"):
        parts = line.strip().split("|")
        if len(parts) != 2:
            continue
        label, phone = parts
        name = label.replace("Công an phường ", "Phường ").replace("Công an xã ", "Xã ")
        mapping[name] = phone.strip()
    return mapping


def normalize(name):
    """Normalize Vietnamese for fuzzy matching."""
    return name.lower().replace("hoà", "hòa").replace("hoá", "hóa").strip()


def match_and_update(data_path):
    """Match police phones to entities and update data.js/data.json."""
    police = parse_police_data()
    police_norm = {normalize(k): v for k, v in police.items()}

    with open(data_path, "r", encoding="utf-8") as f:
        raw = f.read()

    if raw.startswith("export default "):
        json_str = raw[len("export default "):]
        if json_str.rstrip().endswith(";"):
            json_str = json_str.rstrip()[:-1]
        data = json.loads(json_str)
        is_js = True
    else:
        data = json.loads(raw)
        is_js = False

    entities = data if isinstance(data, list) else data.get("entities", [])

    matched = 0
    unmatched_police = set(police.keys())

    # Also build alternate names: "Xã X" → try "Phường X" and vice versa
    alt_norm = {}
    for k, v in police_norm.items():
        if k.startswith("xã "):
            alt_norm["phường " + k[3:]] = v
        elif k.startswith("phường "):
            alt_norm["xã " + k[7:]] = v

    for ent in entities:
        if ent.get("type") != "place":
            continue
        name = ent.get("name", "")
        name_norm = normalize(name)
        phone = police_norm.get(name_norm) or alt_norm.get(name_norm)
        if phone:
            if "attributes" not in ent:
                ent["attributes"] = {}
            ent["attributes"]["police_phone"] = phone
            matched += 1
            for orig_name in list(unmatched_police):
                if normalize(orig_name) == name_norm or alt_norm.get(name_norm):
                    unmatched_police.discard(orig_name)

    # Also add hotlines to all place entities
    for ent in entities:
        if ent.get("type") != "place":
            continue
        if "attributes" not in ent:
            ent["attributes"] = {}
        ent["attributes"]["emergency_phones"] = HOTLINES

    out = json.dumps(data, ensure_ascii=False, indent=2)
    if is_js:
        out = "export default " + out + ";\n"
    with open(data_path, "w", encoding="utf-8") as f:
        f.write(out)

    print(f"Matched: {matched}/{len(police)}")
    if unmatched_police:
        print(f"Unmatched from gov data: {sorted(unmatched_police)}")
    return matched


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="web/data.js")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.dry_run:
        police = parse_police_data()
        print(f"Parsed {len(police)} entries")
        for k, v in list(police.items())[:5]:
            print(f"  {k} → {v}")
        sys.exit(0)

    matched = match_and_update(args.data)
    print(f"Done. Updated {args.data}")
